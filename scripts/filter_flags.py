"""Flag functions and protection for corpus filtering.

Each flag function takes (df, config, **kwargs) and returns pd.Series[bool].
The orchestrator (corpus_filter.py) calls each directly — no registry, no loop.
Exceptions signal genuine errors; the orchestrator catches them.

Flag 6 (LLM relevance) lives in filter_flags_llm.py — re-exported here for
backward compatibility with corpus_filter.py and calibrate_reranker.py.
"""

import os
import re

import numpy as np
import pandas as pd
import yaml
from utils import CONFIG_DIR, get_logger, normalize_doi_safe, work_key

log = get_logger("filter_flags")


# ============================================================
# Config loading
# ============================================================

def _load_config(path=None):
    """Load config from YAML. Defaults to config/corpus_filter.yaml."""
    if path is None:
        path = os.path.join(CONFIG_DIR, "corpus_filter.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


# ============================================================
# Private helpers
# ============================================================

def work_keys(frame):
    """work_key() for every row, tolerating frames that lack the fallback columns.

    work_key reads doi, then source_id, then a hash of title. Test frames and
    slim intermediates carry only some of those, so fill the absent ones rather
    than making every caller build a full frame.
    """
    filled = frame
    missing = [c for c in ("doi", "source_id", "title") if c not in frame.columns]
    if missing:
        filled = frame.copy()
        for col in missing:
            filled[col] = None
    if len(filled) == 0:
        return pd.Series([], dtype=object, index=frame.index)
    return filled.apply(work_key, axis=1)


def _has_safe_words(title, safe_words):
    """Check if title contains any safe/relevant words."""
    if not title:
        return False
    t = title.lower()
    return any(s in t for s in safe_words)


def _text_has_concept_groups(text, groups, min_groups):
    """Check if text mentions at least min_groups concept groups."""
    if not text:
        return False
    words = set(re.findall(r'[a-z]{3,}', text.lower()))
    groups_hit = sum(1 for gw in groups.values() if words & set(gw))
    return groups_hit >= min_groups


def _is_from_teaching(df):
    """Return boolean mask for works originating from teaching sources.

    Uses the from_teaching column set by catalog_merge.py during deduplication.
    """
    if "from_teaching" not in df.columns:
        return pd.Series(False, index=df.index)
    return pd.to_numeric(df["from_teaching"], errors="coerce").fillna(0) == 1


# ============================================================
# Flag 1: Missing metadata
# ============================================================

def flag_missing_metadata(df, config):
    """Flag papers with missing title/author/year (rescued by safe title words).

    Returns pd.Series[bool] aligned with df.index.
    """
    safe_words = config["safe_title"]

    title_s = df["title"].fillna("").astype(str).str.strip()
    author_s = df["first_author"].fillna("").astype(str).str.strip()
    year_s = df["year"].fillna("").astype(str).str.strip()

    miss_title = (title_s == "") | (title_s == "nan")
    miss_author = (author_s == "") | (author_s == "nan")
    miss_year = (year_s == "") | (year_s == "nan")

    title_lower = title_s.str.lower()
    safe_pattern = "|".join(re.escape(s) for s in safe_words)
    title_has_safe = title_lower.str.contains(safe_pattern, na=False)

    # Missing title -> always flag; missing author/year -> only if title lacks safe words
    mask = miss_title | ((miss_author | miss_year) & ~title_has_safe)
    return mask


# ============================================================
# Flag 2: No abstract + irrelevant title
# ============================================================

def flag_no_abstract(df, config):
    """Flag papers with no/short abstract and no safe words in title.

    Returns pd.Series[bool] aligned with df.index.
    """
    safe_words = config["safe_title"]

    title_lower = df["title"].fillna("").astype(str).str.strip().str.lower()
    safe_pattern = "|".join(re.escape(s) for s in safe_words)
    title_has_safe = title_lower.str.contains(safe_pattern, na=False)

    abstract_s = df["abstract"].fillna("").astype(str).str.strip()
    has_abstract = abstract_s.str.len() > 50

    return ~has_abstract & ~title_has_safe


# ============================================================
# Flag 3: Title blacklist
# ============================================================

def flag_title_blacklist(df, config):
    """Flag papers whose title matches noise words but not safe words,
    or whose title exactly matches journal front/back matter.

    Returns pd.Series[bool] aligned with df.index.
    """
    noise_words = config["noise_title"]
    safe_words = config["safe_title"]

    title_lower = df["title"].fillna("").astype(str).str.strip().str.lower()
    noise_pattern = "|".join(re.escape(n) for n in noise_words)
    safe_pattern = "|".join(re.escape(s) for s in safe_words)

    title_has_noise = title_lower.str.contains(noise_pattern, na=False)
    title_has_safe = title_lower.str.contains(safe_pattern, na=False)

    noise_match = title_has_noise & ~title_has_safe

    # Exact-match titles (journal front/back matter)
    exact_noise = config.get("noise_title_exact", [])
    if exact_noise:
        exact_set = {t.lower().strip() for t in exact_noise}
        exact_match = title_lower.isin(exact_set)
        noise_match = noise_match | exact_match

    return noise_match


# ============================================================
# Flag 4: Citation isolation
# ============================================================

def flag_citation_isolated(df, config, *, citations_df):
    """Flag old papers with DOI that are neither cited nor citing in the corpus.

    Returns pd.Series[bool] aligned with df.index.
    Raises ValueError if citations_df is None.
    """
    if citations_df is None:
        raise ValueError("citations_df is required for citation isolation flag")

    max_year = config["citation_isolation"]["max_year"]

    # Ensure doi_norm exists
    if "doi_norm" not in df.columns:
        doi_norm = df["doi"].apply(normalize_doi_safe)
    else:
        doi_norm = df["doi_norm"]

    cited_dois = set()
    citing_dois = set()
    if len(citations_df) > 0:
        cited_dois = set(citations_df["ref_doi"].dropna())
        citing_dois = set(citations_df["source_doi"].dropna())

    year_num = pd.to_numeric(df["year"], errors="coerce")
    is_old = year_num.notna() & (year_num <= max_year)
    has_doi = doi_norm != ""
    is_cited = doi_norm.isin(cited_dois)
    is_citing = doi_norm.isin(citing_dois)

    return is_old & has_doi & ~is_cited & ~is_citing


# ============================================================
# Flag 5: Semantic outlier
# ============================================================

# Below this many works a language cannot locate its own centroid: the mean of
# a handful of vectors is dominated by whichever few works happen to be there,
# and every one of them then reports as typical. Such a language falls back to
# the corpus centroid — the same refusal as ``min_coverage``, which will not
# score a rump of the corpus against a centroid built from that rump.
DEFAULT_MIN_LANGUAGE_COUNT = 30

# Diagnostic, not filter, is the fallback when config states no mode. Flag 5's
# only threshold (`sigma: 2`) was calibrated on a smaller corpus under a
# different embedding model and was never validated against anything it
# produced, so an absent key must not resurrect 361 removals (ticket 0361).
DEFAULT_SEMANTIC_MODE = "diagnostic"
DEFAULT_SEMANTIC_CENTROID = "per_language"

SEMANTIC_MODES = ("diagnostic", "filter")
SEMANTIC_CENTROIDS = ("global", "per_language")


def _centroid_distances(embeddings, rows):
    """Cosine distance from each row in ``rows`` to the centroid of ``rows``.

    ``rows`` is an array of positional indices into ``embeddings``; the return
    value is aligned with it, not with ``embeddings``.
    """
    block = embeddings[rows]
    centroid = block.mean(axis=0)
    norms = np.linalg.norm(block, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    normed = block / norms
    centroid_normed = centroid / max(np.linalg.norm(centroid), 1e-10)
    return 1 - (normed @ centroid_normed)


def _language_strata(emb_df, min_count):
    """Positional row groups for languages large enough to own a centroid.

    Returns ``{language: positional index array}``. A frame with no
    ``language`` column yields nothing, so the caller degrades to the global
    centroid rather than failing — test fixtures and slim intermediates
    predate the column.
    """
    if "language" not in emb_df.columns:
        log.warning("  Flag 5: no 'language' column — the per-language "
                    "centroid degrades to the global one for every work")
        return {}
    codes = emb_df["language"].fillna("").astype(str).str.strip().str.lower()
    positions = np.arange(len(emb_df))
    strata = {}
    for lang, rows in pd.Series(positions).groupby(codes.to_numpy()):
        if lang and len(rows) >= min_count:
            strata[lang] = rows.to_numpy()
    return strata


def flag_semantic_outlier(df, config, *, embeddings, emb_df):
    """Score each candidate's distance from its semantic centroid.

    Two config keys under ``semantic_outlier`` decide what that means:

    ``mode``
        ``diagnostic`` (default) computes and returns the distances but flags
        nothing — the mask is all-False. ``filter`` compares each distance
        against ``mean + sigma * std`` of its own stratum and flags what
        exceeds it; it requires an explicit ``sigma``.
    ``centroid``
        ``per_language`` (default) measures each work against the centroid of
        its own language, falling back to the corpus centroid below
        ``min_language_count`` works. ``global`` uses one corpus-wide centroid.

    The per-language centroid is the lever on the language gradient, and sigma
    is not: a corpus that is 91.6% English builds a centroid whose distance
    partly measures *not written in English*, so the extreme tail of that
    distribution is almost entirely non-English and raising sigma makes the
    bias worse (global sigma=4 removed Spanish works at 14.7x the baseline
    rate, sigma=2 at 4.1x; per-language sigma=2 at 1.1x). Mean-centring within
    language is the documented correction for this embedding geometry
    (Libovicky et al., arXiv:1911.03310).

    Returns (pd.Series[bool], pd.Series[float]) aligned with df.index.
    Raises ValueError if embeddings or emb_df is None, on a size mismatch, or
    on an unreadable config setting.
    """
    if embeddings is None or emb_df is None:
        raise ValueError("embeddings and emb_df are required for semantic outlier flag")

    if len(embeddings) != len(emb_df):
        raise ValueError(
            f"embedding size mismatch ({len(embeddings)} vs {len(emb_df)})"
        )

    cfg = config["semantic_outlier"]
    mode = cfg.get("mode", DEFAULT_SEMANTIC_MODE)
    if mode not in SEMANTIC_MODES:
        raise ValueError(
            f"semantic_outlier.mode is {mode!r}; expected one of {SEMANTIC_MODES}"
        )
    scope = cfg.get("centroid", DEFAULT_SEMANTIC_CENTROID)
    if scope not in SEMANTIC_CENTROIDS:
        raise ValueError(
            f"semantic_outlier.centroid is {scope!r}; expected one of "
            f"{SEMANTIC_CENTROIDS}"
        )

    all_rows = np.arange(len(embeddings))
    global_dist = _centroid_distances(embeddings, all_rows)
    cos_dist = np.array(global_dist, dtype=float)

    strata = {}
    if scope == "per_language":
        min_count = cfg.get("min_language_count", DEFAULT_MIN_LANGUAGE_COUNT)
        strata = _language_strata(emb_df, min_count)
        for rows in strata.values():
            cos_dist[rows] = _centroid_distances(embeddings, rows)
        n_own = sum(len(rows) for rows in strata.values())
        log.info("  Flag 5 centroid: per-language for %d of %d candidates in "
                 "%d language(s) with >= %d works; corpus centroid for the "
                 "remaining %d", n_own, len(emb_df), len(strata), min_count,
                 len(emb_df) - n_own)

    # Put each distance back on the row it was computed for, by index. emb_df
    # is a slice of df carrying df's own index, so membership needs no
    # re-derivation — and re-deriving it is what kept going wrong: a DOI-keyed
    # map dropped every DOI-less work's distance while that work still set the
    # centroid, then a normalised-DOI map and finally an exact-work_key map
    # each handed a candidate's distance to whatever non-candidate happened to
    # share the key (ticket 0336, review rounds 1-3). Index membership cannot
    # collide, so the class closes here rather than shrinking again.
    unknown = emb_df.index.difference(df.index)
    if len(unknown):
        raise ValueError(
            f"emb_df has {len(unknown)} rows absent from df — it must be a "
            "slice of df so distances can be assigned by index"
        )
    outlier_dists = pd.Series(np.nan, index=df.index, dtype=float)
    outlier_dists.loc[emb_df.index] = cos_dist

    if mode == "diagnostic":
        # The distance ships; the removals do not. Returning a real
        # measurement next to an empty mask is the point of the mode, so this
        # early return sits after the computation, never in place of it.
        return pd.Series(False, index=df.index), outlier_dists

    if "sigma" not in cfg:
        raise ValueError(
            "semantic_outlier.mode is 'filter' but no sigma is configured. "
            "Flag 5 will not invent a threshold: set semantic_outlier.sigma "
            "to a value calibrated against this corpus and this embedding "
            "model, or leave the flag in diagnostic mode (ticket 0361)."
        )
    sigma = cfg["sigma"]

    # Each stratum is judged against its own moments. Sharing one corpus-wide
    # mean and SD would put the whole per-language correction back: a language
    # sitting off the corpus centre would clear the global threshold wholesale
    # however well its own works agree with each other.
    thresholds = np.full(
        len(embeddings), global_dist.mean() + sigma * global_dist.std())
    for rows in strata.values():
        block = cos_dist[rows]
        thresholds[rows] = block.mean() + sigma * block.std()

    over = pd.Series(np.nan, index=df.index, dtype=float)
    over.loc[emb_df.index] = cos_dist - thresholds
    flag_mask = over.notna() & (over > 0)

    return flag_mask, outlier_dists


# ============================================================
# Flag 6: LLM relevance (delegated to filter_flags_llm.py)
# ============================================================

# Re-export for backward compatibility — corpus_filter.py and tests import from here
from filter_flags_llm import (  # noqa: F401
    _cache_key,
    flag_llm_irrelevant,
    flag_llm_irrelevant_streaming,
)

# ============================================================
# Protection
# ============================================================

def compute_protection(df, config, *, citations_df):
    """Mark papers as protected based on citations, sources, teaching canon.

    Returns (pd.Series[bool], pd.Series[str]) for (protected, protect_reason).
    """
    prot_cfg = config["protection"]
    min_cited_by = prot_cfg["min_cited_by"]
    min_source_count = prot_cfg["min_source_count"]

    cites = pd.to_numeric(df["cited_by_count"], errors="coerce")
    sc = pd.to_numeric(df["source_count"], errors="coerce")

    high_cites = cites.notna() & (cites >= min_cited_by)
    multi_src = sc.notna() & (sc >= min_source_count)

    # Ensure doi_norm exists
    if "doi_norm" not in df.columns:
        doi_norm = df["doi"].apply(normalize_doi_safe)
    else:
        doi_norm = df["doi_norm"]

    ref_dois = set()
    if citations_df is not None:
        ref_dois = set(citations_df["ref_doi"].dropna())
    cited_in_corpus = doi_norm.isin(ref_dois) & (doi_norm != "")

    in_teaching = _is_from_teaching(df)

    # Curated key-documents layer (ticket 0288): official documents carry no
    # citation counts and one source, so every other channel misses them.
    curated = pd.Series(False, index=df.index)
    for src in prot_cfg.get("curated_sources", []):
        col = f"from_{src}"
        if col in df.columns:
            hit = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(bool)
            curated |= hit

    protected = high_cites | multi_src | cited_in_corpus | in_teaching | curated

    # Build reason strings
    reasons = pd.Series("", index=df.index)
    for i in protected[protected].index:
        r = []
        if high_cites.at[i]:
            r.append(f"cited_by={int(cites.at[i])}")
        if multi_src.at[i]:
            r.append(f"multi_source={int(sc.at[i])}")
        if cited_in_corpus.at[i]:
            r.append("cited_in_corpus")
        if in_teaching.at[i]:
            r.append("from_teaching")
        if curated.at[i]:
            r.append("curated_source")
        reasons.at[i] = "; ".join(r)

    return protected, reasons
