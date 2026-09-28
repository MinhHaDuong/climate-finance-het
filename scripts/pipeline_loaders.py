"""Configuration and data loaders for the literature indexing pipeline.

Owns all path constants and provides functions to load config YAMLs,
corpus DataFrames, embeddings, and citation edges.

Exports
-------
BASE_DIR, CONFIG_DIR, DATA_DIR, CATALOGS_DIR, EXPORTS_DIR, RAW_DIR, POOL_DIR
    Canonical project-level path constants.
EMBEDDINGS_PATH, EMBEDDINGS_CACHE_DIR, EMBEDDINGS_CACHE_PATH
    Paths to embeddings artifacts.
REFINED_WORKS_PATH, REFINED_EMBEDDINGS_PATH, REFINED_CITATIONS_PATH
    Phase 1 → Phase 2 contract artifacts.
load_collect_config
    Load config/corpus_collect.yaml (Phase 1 collection parameters).
load_analysis_config
    Load config/analysis.yaml (Phase 2 analysis parameters).
load_analysis_periods
    Derive period tuples and labels from config/analysis.yaml.
load_cluster_labels
    Load cluster_labels.json with fallback to generic labels.
work_key
    Stable key for a work: DOI preferred, then source_id, then title hash.
load_embeddings
    Load embedding vectors from the .npz cache (legacy path).
load_refined_embeddings
    Load embedding vectors aligned 1:1 with refined_works.csv.
load_refined_works
    Load refined_works.csv (Feather-first) with type coercion, no filtering.
load_refined_citations
    Load citation edges restricted to refined_works.csv source DOIs.
load_analysis_corpus
    Load refined_works.csv with standard filtering + optional embeddings.
load_rel_review_corpus
    Load the REL review window with complete/partial-year labels.
"""

import json
import logging
import os

import pandas as pd
from dotenv import load_dotenv

_log = logging.getLogger("pipeline.loaders")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load non-secret machine settings from the repo root (gitignored). Credentials
# are read from ~/.config/keys by the individual API consumers that need them.
load_dotenv(os.path.join(BASE_DIR, ".env"))

CONFIG_DIR = os.path.join(BASE_DIR, "config")

# Data lives in <repo>/data/ (managed by DVC).
# Override with CLIMATE_FINANCE_DATA env var for smoke tests / worktrees.
_data_override = os.environ.get("CLIMATE_FINANCE_DATA")
DATA_DIR = _data_override or os.path.join(BASE_DIR, "data")
CATALOGS_DIR = os.path.join(DATA_DIR, "catalogs")
EXPORTS_DIR = os.path.join(DATA_DIR, "exports")
RAW_DIR = os.path.join(DATA_DIR, "raw")
POOL_DIR = os.path.join(DATA_DIR, "pool")

# Analysis-side scratch dir for large Phase-2 intermediates consumed only by
# other Phase-2 scripts (not writing deliverables): kept out of content/tables/
# so that directory holds only byte-stable writing outputs (ticket 0208).
# Regenerable — NOT a DVC output; DVC stays scoped to genuine corpus data.
DERIVED_TABLES_DIR = os.path.join(DATA_DIR, "derived", "tables")

# Embeddings live in a separate .npz rather than as columns in refined_works.csv:
# - Size: 1024 floats × 30k rows as CSV text ≈ 1.3 GB vs. ~120 MB compressed binary
# - Incremental cache: stores keys + text hashes + model config so only new/changed
#   works are re-encoded on each run (~16 min full, seconds incremental)
# - Load speed: numpy reads the array in one shot; no parsing of 11M float strings
EMBEDDINGS_PATH = os.path.join(CATALOGS_DIR, "embeddings.npz")

# Incremental embedding cache lives in enrich_cache/ — NOT a DVC output.
# DVC deletes stage outputs before re-running; keeping the cache separate
# means re-runs skip already-computed vectors instead of starting from scratch.
EMBEDDINGS_CACHE_DIR = os.path.join(CATALOGS_DIR, "enrich_cache")
EMBEDDINGS_CACHE_PATH = os.path.join(EMBEDDINGS_CACHE_DIR, "embeddings_cache.npz")

# Phase 1 → Phase 2 aligned canonical artifacts (produced by corpus-align step).
# refined_embeddings.npz rows are 1:1 with refined_works.csv rows.
# refined_citations.csv source_doi values are a subset of refined_works.csv DOIs.
REFINED_WORKS_PATH = os.path.join(CATALOGS_DIR, "refined_works.csv")
REFINED_EMBEDDINGS_PATH = os.path.join(CATALOGS_DIR, "refined_embeddings.npz")
REFINED_CITATIONS_PATH = os.path.join(CATALOGS_DIR, "refined_citations.csv")


# Phase 2 reads Feather for speed (20–50× faster than CSV). The Makefile
# handoff target converts CSV → Feather; loaders fall back to CSV if missing.
REFINED_WORKS_FEATHER = os.path.join(CATALOGS_DIR, "refined_works.feather")
REFINED_CITATIONS_FEATHER = os.path.join(CATALOGS_DIR, "refined_citations.feather")

_CLUSTER_LABELS_PATH = os.path.join(DERIVED_TABLES_DIR, "cluster_labels.json")


# ---------------------------------------------------------------------------
# Config loaders
# ---------------------------------------------------------------------------


def load_collect_config():
    """Load config/corpus_collect.yaml (Phase 1 collection parameters).

    Returns dict with keys: year_min, year_max, queries.
    Raises FileNotFoundError if the config is missing.
    """
    import yaml

    path = os.path.join(CONFIG_DIR, "corpus_collect.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"corpus_collect.yaml not found at {path}. "
            "This file defines year bounds for API queries."
        )
    with open(path) as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg.get("year_min"), int) or not isinstance(
        cfg.get("year_max"), int
    ):
        raise ValueError(
            "year_min and year_max must be integers in corpus_collect.yaml"
        )
    if cfg["year_min"] > cfg["year_max"]:
        raise ValueError(
            f"year_min ({cfg['year_min']}) > year_max ({cfg['year_max']}) "
            "in corpus_collect.yaml"
        )
    return cfg


def load_analysis_config():
    """Load config/analysis.yaml (Phase 2 analysis parameters).

    Returns dict with keys: periodization, clustering.
    """
    import yaml

    path = os.path.join(CONFIG_DIR, "analysis.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"analysis.yaml not found at {path}. "
            "This file defines Phase 2 analysis parameters."
        )
    with open(path) as f:
        return yaml.safe_load(f)


def load_rel_review_config():
    """Load the dated REL review window independently of analysis.yaml."""
    from datetime import date

    import yaml

    path = os.path.join(CONFIG_DIR, "rel_review.yaml")
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    search_date = date.fromisoformat(str(cfg["search_date"]))
    years = (cfg["year_min"], cfg["last_complete_year"], cfg["partial_year"])
    if not all(type(year) is int for year in years):
        raise ValueError("REL year bounds must be integers")
    if not (years[0] <= years[1] < years[2] == search_date.year):
        raise ValueError("REL window must end in the partial search year")
    if years[2] > load_collect_config()["year_max"]:
        raise ValueError("REL window exceeds the collection window")
    return cfg


def classify_rel_review_works(works, config=None):
    """Assign each work a dated REL window disposition.

    Publication dates later than the search are excluded. Year-only 2026
    records are quarantined until their release date is verified.
    Journal articles and working papers follow the same rule.
    """
    from datetime import date

    cfg = config or load_rel_review_config()
    search_date = date.fromisoformat(str(cfg["search_date"]))
    year = pd.to_numeric(works["year"], errors="coerce")
    has_title = works["title"].notna() & works["title"].astype(str).str.strip().ne("")
    disposition = pd.Series("include", index=works.index)
    disposition.loc[~has_title] = "exclude_missing_title"
    in_window = year.ge(cfg["year_min"]) & year.le(cfg["partial_year"])
    disposition.loc[~in_window] = "exclude_outside_year_window"
    date_precision = pd.Series("year_only", index=works.index)
    dated = pd.Series(False, index=works.index)
    if "publication_date" in works:
        raw_date = works["publication_date"].astype("string").str.strip()
        full_date = raw_date.str.fullmatch(r"\d{4}-\d{2}-\d{2}").fillna(False)
        published = pd.to_datetime(raw_date.where(full_date),
                                   format="%Y-%m-%d", errors="coerce")
        dated = published.notna()
        year_only = raw_date.str.fullmatch(r"\d{4}").fillna(False)
        unsupported = raw_date.notna() & raw_date.ne("") & ~dated & ~year_only
        date_precision.loc[dated] = "full_date"
        disposition.loc[unsupported] = "quarantine_invalid_date"
        disposition.loc[dated & published.dt.date.gt(search_date)] = "exclude_future_date"
    if cfg["require_full_date_for_partial_year"]:
        unverified = year.eq(cfg["partial_year"]) & ~dated
        disposition.loc[unverified & disposition.eq("include")] = (
            "quarantine_unverified_partial_date")
    classified = works.copy()
    classified["rel_disposition"] = disposition
    classified["rel_year_status"] = year.apply(
        lambda value: "partial" if value == cfg["partial_year"]
        else "complete" if pd.notna(value) and value <= cfg["last_complete_year"]
        else "outside")
    classified["rel_date_precision"] = date_precision
    classified["rel_search_date"] = search_date.isoformat()
    return classified


def select_rel_review_works(works, config=None):
    """Return included works; use classify_rel_review_works for exclusions."""
    classified = classify_rel_review_works(works, config=config)
    selected = classified.loc[classified["rel_disposition"].eq("include")].copy()
    selected["year"] = pd.to_numeric(selected["year"]).astype(int)
    return selected.reset_index(drop=True)


def load_rel_review_corpus():
    """Load the refined corpus under REL's own dated review window."""
    return select_rel_review_works(load_refined_works())


def pre2007_cutoff_year(cfg):
    """Last year of Act I (pre-crystallisation): first break - 1.

    Single source of truth for the pre-2007 slice boundary. Derived from
    config periodization (breaks[0] - 1 = 2006), so plot_fig_traditions and
    compute_pre2007_coverage share one definition rather than a hardcoded
    constant.
    """
    return int(cfg["periodization"]["breaks"][0]) - 1


def load_analysis_periods(config_dir=None):
    """Derive period tuples and labels from config/analysis.yaml.

    Returns (periods, labels) where:
      periods = [(1990, 2006), (2007, 2014), (2015, 2024)]
      labels  = ["1990\u20132006", "2007\u20132014", "2015\u20132024"]

    If config_dir is given, reads analysis.yaml (and optionally
    corpus_collect.yaml) from that directory instead of CONFIG_DIR.

    Emits a UserWarning if the analysis year range exceeds the collection
    range defined in corpus_collect.yaml. Skips the check gracefully if
    corpus_collect.yaml does not exist.
    """
    import warnings

    import yaml

    cdir = config_dir or CONFIG_DIR
    analysis_path = os.path.join(cdir, "analysis.yaml")
    with open(analysis_path) as f:
        cfg = yaml.safe_load(f)

    p = cfg["periodization"]
    year_min = p["year_min"]
    year_max = p["year_max"]
    breaks = p["breaks"]

    # Build period tuples: [year_min, break-1], [break, next_break-1], ..., [last_break, year_max]
    boundaries = [year_min] + breaks + [year_max + 1]
    periods = []
    labels = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1] - 1
        periods.append((start, end))
        labels.append(f"{start}\u2013{end}")

    # Check against collection range if corpus_collect.yaml exists
    collect_path = os.path.join(cdir, "corpus_collect.yaml")
    if os.path.exists(collect_path):
        with open(collect_path) as f:
            collect_cfg = yaml.safe_load(f)
        c_min = collect_cfg.get("year_min")
        c_max = collect_cfg.get("year_max")
        msgs = []
        if c_min is not None and year_min < c_min:
            msgs.append(
                f"analysis year_min ({year_min}) < collection year_min ({c_min})"
            )
        if c_max is not None and year_max > c_max:
            msgs.append(
                f"analysis year_max ({year_max}) > collection year_max ({c_max})"
            )
        if msgs:
            warnings.warn(
                "Analysis range exceeds collection range: " + "; ".join(msgs),
                UserWarning,
                stacklevel=2,
            )

    return periods, labels


# ---------------------------------------------------------------------------
# Corpus / embeddings / citations loaders
# ---------------------------------------------------------------------------


def load_cluster_labels(n_clusters=6):
    """Load cluster labels from cluster_labels.json.

    Returns dict with int keys: {0: "term1 / term2 / term3", ...}.
    Falls back to generic "Cluster N" labels with a warning.
    """
    import warnings

    if os.path.exists(_CLUSTER_LABELS_PATH):
        with open(_CLUSTER_LABELS_PATH) as f:
            raw = json.load(f)
        return {int(k): v for k, v in raw.items()}

    warnings.warn(
        f"cluster_labels.json not found at {_CLUSTER_LABELS_PATH}. "
        "Run: uv run python scripts/analysis/compute_clusters.py",
        stacklevel=2,
    )
    return {i: f"Cluster {i}" for i in range(n_clusters)}


def work_key(row):
    """Stable key for a work: DOI preferred, then source_id, then title hash.

    Used by both enrich_embeddings.py and analyze_embeddings.py to align
    works with their embedding vectors. Must be identical across scripts.
    """
    import hashlib

    if pd.notna(row["doi"]):
        return str(row["doi"])
    if pd.notna(row["source_id"]):
        return str(row["source_id"])
    return "title:" + hashlib.md5(str(row["title"]).encode()).hexdigest()


def load_embeddings():
    """Load embedding vectors from the .npz cache.

    Returns the (N, 1024) float32 array. Raises FileNotFoundError if missing.
    Also supports legacy .npy files for backwards compatibility.
    """
    import numpy as np

    if os.path.exists(EMBEDDINGS_PATH):
        return np.load(EMBEDDINGS_PATH)["vectors"]
    # Legacy fallback
    legacy = os.path.join(CATALOGS_DIR, "embeddings.npy")
    if os.path.exists(legacy):
        return np.load(legacy)
    raise FileNotFoundError(f"No embeddings found at {EMBEDDINGS_PATH}")


def load_refined_embeddings():
    """Load embedding vectors aligned 1:1 with refined_works.csv rows.

    Returns the (N, D) float32 array where N == len(refined_works.csv).
    Raises FileNotFoundError with a remediation hint if the file is missing.
    Run ``make corpus-align`` (or ``uv run python scripts/harvest/corpus_align.py``)
    to produce this file.
    """
    import numpy as np

    if not os.path.exists(REFINED_EMBEDDINGS_PATH):
        raise FileNotFoundError(
            f"refined_embeddings.npz not found at {REFINED_EMBEDDINGS_PATH}. "
            "Run: uv run python scripts/harvest/corpus_align.py"
        )
    return np.load(REFINED_EMBEDDINGS_PATH)["vectors"]


def _handoff_cache_is_current(feather_path, csv_path):
    """True when the Feather handoff cache may stand in for its CSV.

    The cache is a speed layer, not a source of truth: the Makefile rebuilds
    it from the CSV (``make corpus-handoff``) whenever the CSV is newer. Any
    invocation that skips that dependency — a script run directly, as the
    module docstrings advertise — used to read the cache on mere existence,
    and so silently served the previous corpus.

    That is not hypothetical. After the 2026-07-27 rebuild the cache was three
    days old: it had no ``language_provenance`` column at all and still
    carried the pre-0297 ``language`` values, leaving 1,350 rows disagreeing
    with the corpus and ``lang_english_pct`` at 89.86 against a measured 93.79
    (ticket 0323). A rebuild that does not move the numbers defeats the whole
    point of driving prose from vars.

    An absent CSV is not staleness — reproducibility archives may ship either
    file — so the cache is trusted when there is nothing to compare it to.

    One limit: under a DVC ``cache.type`` of ``symlink`` or ``hardlink`` the
    checkout shares the cache object's mtime — resolved through the link, or
    read from the one inode both names point at — so the CSV reports its
    add-time rather than the checkout's. The comparison then fails toward
    false-fresh: a re-materialized CSV looks older than the Feather and the
    stale cache is served anyway, which is the one error this function exists
    to prevent. The committed default is ``copy``, so the comparison is honest
    here; a project switching link types to save disk needs a content check
    instead of an mtime one.
    """
    if not os.path.exists(csv_path):
        return True
    if os.path.getmtime(feather_path) >= os.path.getmtime(csv_path):
        return True
    _log.warning(
        "%s is older than %s — reading the CSV instead. Run `make "
        "corpus-handoff` to refresh the cache.",
        os.path.basename(feather_path),
        os.path.basename(csv_path),
    )
    return False


def load_refined_works():
    """Load refined_works.csv (Feather-first) with standard type coercion.

    Returns the full DataFrame with no row filtering. Year is coerced to
    numeric, cited_by_count is coerced and NaN-filled to 0.

    Use ``load_analysis_corpus()`` when you need year-range or core filtering.
    """
    if os.path.exists(REFINED_WORKS_FEATHER) and _handoff_cache_is_current(
        REFINED_WORKS_FEATHER, REFINED_WORKS_PATH
    ):
        works = pd.read_feather(REFINED_WORKS_FEATHER)
    else:
        if not os.path.exists(REFINED_WORKS_PATH):
            raise FileNotFoundError(
                f"refined_works not found at {REFINED_WORKS_FEATHER} or "
                f"{REFINED_WORKS_PATH}. "
                "Run: make corpus-handoff"
            )
        works = pd.read_csv(REFINED_WORKS_PATH, low_memory=False)
    works["year"] = pd.to_numeric(works["year"], errors="coerce")
    works["cited_by_count"] = pd.to_numeric(
        works["cited_by_count"], errors="coerce"
    ).fillna(0)
    return works


def load_refined_citations():
    """Load citation edges restricted to refined_works.csv source DOIs.

    Returns a DataFrame whose ``source_doi`` values are all members of
    ``normalize_doi(refined_works.csv.doi)``.
    Raises FileNotFoundError with a remediation hint if the file is missing.
    Run ``make corpus-align`` (or ``uv run python scripts/harvest/corpus_align.py``)
    to produce this file.
    """
    if os.path.exists(REFINED_CITATIONS_FEATHER) and _handoff_cache_is_current(
        REFINED_CITATIONS_FEATHER, REFINED_CITATIONS_PATH
    ):
        return pd.read_feather(REFINED_CITATIONS_FEATHER)
    if not os.path.exists(REFINED_CITATIONS_PATH):
        raise FileNotFoundError(
            f"refined_citations not found at {REFINED_CITATIONS_FEATHER} or "
            f"{REFINED_CITATIONS_PATH}. "
            "Run: make corpus-handoff (or uv run python scripts/harvest/corpus_align.py)"
        )
    return pd.read_csv(REFINED_CITATIONS_PATH, low_memory=False)


def load_analysis_corpus(
    core_only=False, with_embeddings=True, cite_threshold=None, v1_only=False
):
    """Load refined_works.csv with standard filtering + optional embeddings.

    Applies: year coercion, title-present filter, year in [year_min, year_max]
    (from config/analysis.yaml), optional core filtering (cited_by_count >= cite_threshold).

    If v1_only=True, restricts to rows with in_v1==1 (the v1.0-submission
    corpus). Use this for manuscript figures to ensure stability against
    corpus expansion.

    If cite_threshold is None, the value is read from config/analysis.yaml
    (clustering.cite_threshold) so there is a single source of truth.

    Returns (df, embeddings) where embeddings is None if with_embeddings=False.
    """

    cfg = load_analysis_config()
    if cite_threshold is None:
        cite_threshold = cfg["clustering"]["cite_threshold"]
    year_min = cfg["periodization"]["year_min"]
    year_max = cfg["periodization"]["year_max"]

    works = load_refined_works()

    has_title = works["title"].notna() & (works["title"].str.len() > 0)
    in_range = (works["year"] >= year_min) & (works["year"] <= year_max)
    keep_mask = has_title & in_range
    if v1_only:
        if "in_v1" not in works.columns:
            raise RuntimeError(
                "v1_only=True but 'in_v1' column missing from refined_works.csv. "
                "Re-run: uv run python scripts/harvest/corpus_filter.py --apply"
            )
        keep_mask = keep_mask & (works["in_v1"] == 1)
        _log.info("v1_only: restricting to %d / %d rows", keep_mask.sum(), len(works))
    keep_mask = keep_mask.values
    df = works[keep_mask].copy().reset_index(drop=True)

    embeddings = None
    if with_embeddings:
        all_embeddings = load_refined_embeddings()
        if len(all_embeddings) != len(works):
            raise RuntimeError(
                f"Embedding/refined_works row count mismatch "
                f"({len(all_embeddings)} vs {len(works)}). "
                "Re-run: uv run python scripts/harvest/corpus_align.py"
            )
        embeddings = all_embeddings[keep_mask]

    if core_only:
        core_mask = df["cited_by_count"] >= cite_threshold
        core_indices = df.index[core_mask].values
        df = df.loc[core_mask].reset_index(drop=True)
        if embeddings is not None:
            embeddings = embeddings[core_indices]
            assert len(df) == len(embeddings), (
                "Embedding alignment error after core filtering"
            )

    return df, embeddings
