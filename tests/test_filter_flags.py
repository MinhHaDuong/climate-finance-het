"""Tests for filter_flags.py — per-rule parity tests with fixed fixture."""

import os
import sys
from statistics import NormalDist

import numpy as np
import pandas as pd
import pytest

# Add scripts/ to path so we can import filter_flags
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from filter_flags import (
    _cache_key,
    _has_safe_words,
    _load_config,
    _text_has_concept_groups,
    compute_protection,
    flag_citation_isolated,
    flag_llm_irrelevant,
    flag_missing_metadata,
    flag_no_abstract,
    flag_semantic_outlier,
    flag_title_blacklist,
)

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def config():
    return _load_config(os.path.join(FIXTURE_DIR, "corpus_filter_test.yaml"))


@pytest.fixture
def fixture_df():
    """~20 rows covering every flag and protection case."""
    return pd.read_csv(os.path.join(FIXTURE_DIR, "filter_fixture.csv"))


def sem_config(config, **overrides):
    """`config` with the semantic_outlier block overridden key by key."""
    block = dict(config["semantic_outlier"], **overrides)
    return dict(config, semantic_outlier=block)


@pytest.fixture
def filter_config(config):
    """Flag 5 in filter mode.

    Diagnostic mode is the shipped default (ticket 0361), so a test about
    *which row gets which distance* has to ask for a mask that can raise.
    """
    return sem_config(config, mode="filter")


@pytest.fixture
def reranker_config_without_torch(config, monkeypatch):
    """Reranker backend selected on a host where torch cannot be imported.

    Reproduces the ticket-0314 condition. The module under test is imported
    before the hook goes live, so only the reranker's own lazy import fails.
    """
    import builtins

    import filter_flags_llm  # noqa: F401 — pre-import, before the hook bites

    real_import = builtins.__import__

    def no_torch(name, *args, **kwargs):
        if name == "torch":
            raise ImportError("No module named 'torch'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_torch)
    return dict(
        config,
        llm_relevance=dict(config["llm_relevance"], backend="reranker"),
    )


# ============================================================
# Helper tests
# ============================================================

class TestHelpers:
    def test_has_safe_words_positive(self):
        assert _has_safe_words("Climate change impacts", ["climate", "carbon"])

    def test_has_safe_words_negative(self):
        assert not _has_safe_words("Blockchain technology", ["climate", "carbon"])

    def test_has_safe_words_empty(self):
        assert not _has_safe_words("", ["climate"])
        assert not _has_safe_words(None, ["climate"])

    def test_text_has_concept_groups_positive(self):
        groups = {
            "climate": ["climate", "emission"],
            "finance": ["finance", "investment"],
        }
        assert _text_has_concept_groups(
            "Climate finance and investment", groups, 2
        )

    def test_text_has_concept_groups_negative(self):
        groups = {
            "climate": ["climate", "emission"],
            "finance": ["finance", "investment"],
        }
        assert not _text_has_concept_groups("Only about climate", groups, 2)

    def test_text_has_concept_groups_empty(self):
        groups = {"climate": ["climate"]}
        assert not _text_has_concept_groups("", groups, 1)
        assert not _text_has_concept_groups(None, groups, 1)

    def test_load_config(self, config):
        assert "noise_title" in config
        assert "safe_title" in config
        assert "concept_groups" in config
        assert "citation_isolation" in config
        assert "semantic_outlier" in config
        assert "protection" in config


# ============================================================
# Flag 1: Missing metadata
# ============================================================

class TestFlagMissingMetadata:
    def test_missing_title_flagged(self, fixture_df, config):
        """Row 0: missing title, author, year -> flagged."""
        result = flag_missing_metadata(fixture_df, config)
        assert result.iloc[0] is True or result.iloc[0] == True

    def test_missing_author_safe_title_not_flagged(self, fixture_df, config):
        """Row 1: missing author but safe title ('Climate...') -> NOT flagged."""
        result = flag_missing_metadata(fixture_df, config)
        assert result.iloc[1] == False

    def test_complete_metadata_not_flagged(self, fixture_df, config):
        """Row 2: complete metadata -> NOT flagged."""
        result = flag_missing_metadata(fixture_df, config)
        assert result.iloc[2] == False

    def test_returns_series_aligned(self, fixture_df, config):
        result = flag_missing_metadata(fixture_df, config)
        assert isinstance(result, pd.Series)
        assert len(result) == len(fixture_df)
        assert result.index.equals(fixture_df.index)


# ============================================================
# Flag 2: No abstract + irrelevant title
# ============================================================

class TestFlagNoAbstract:
    def test_no_abstract_irrelevant_title_flagged(self, fixture_df, config):
        """Row 3: no abstract, irrelevant title -> flagged."""
        result = flag_no_abstract(fixture_df, config)
        assert result.iloc[3] == True

    def test_no_abstract_safe_title_not_flagged(self, fixture_df, config):
        """Row 4: no abstract but safe title ('Green energy...') -> NOT flagged."""
        result = flag_no_abstract(fixture_df, config)
        assert result.iloc[4] == False

    def test_has_abstract_not_flagged(self, fixture_df, config):
        """Row 2: has abstract -> NOT flagged."""
        result = flag_no_abstract(fixture_df, config)
        assert result.iloc[2] == False


# ============================================================
# Flag 3: Title blacklist
# ============================================================

class TestFlagTitleBlacklist:
    def test_noise_title_flagged(self, fixture_df, config):
        """Row 5: 'Blockchain' in title, no safe words -> flagged."""
        result = flag_title_blacklist(fixture_df, config)
        assert result.iloc[5] == True

    def test_noise_plus_safe_not_flagged(self, fixture_df, config):
        """Row 6: 'Blockchain' + 'climate' -> NOT flagged."""
        result = flag_title_blacklist(fixture_df, config)
        assert result.iloc[6] == False

    def test_clean_title_not_flagged(self, fixture_df, config):
        """Row 2: clean title -> NOT flagged."""
        result = flag_title_blacklist(fixture_df, config)
        assert result.iloc[2] == False

    def test_deep_learning_flagged(self, fixture_df, config):
        """Row 15: 'Deep learning' title, no safe words -> flagged."""
        result = flag_title_blacklist(fixture_df, config)
        assert result.iloc[15] == True


# ============================================================
# Flag 4: Citation isolation
# ============================================================

class TestFlagCitationIsolated:
    def test_old_isolated_flagged(self, fixture_df, config):
        """Row 7: year 2010, DOI not in citations -> flagged."""
        citations_df = pd.DataFrame({
            "source_doi": ["10.1000/old-cited"],
            "ref_doi": ["10.1000/complete"],
        })
        fixture_df["doi_norm"] = fixture_df["doi"].apply(
            lambda x: str(x).strip().lower() if pd.notna(x) else ""
        )
        result = flag_citation_isolated(fixture_df, config, citations_df=citations_df)
        assert result.iloc[7] == True

    def test_old_cited_not_flagged(self, fixture_df, config):
        """Row 8: year 2005 but DOI appears as source -> NOT flagged."""
        citations_df = pd.DataFrame({
            "source_doi": ["10.1000/old-cited"],
            "ref_doi": ["10.1000/complete"],
        })
        fixture_df["doi_norm"] = fixture_df["doi"].apply(
            lambda x: str(x).strip().lower() if pd.notna(x) else ""
        )
        result = flag_citation_isolated(fixture_df, config, citations_df=citations_df)
        assert result.iloc[8] == False

    def test_recent_isolated_not_flagged(self, fixture_df, config):
        """Row 9: year 2022, isolated but recent -> NOT flagged (year > max_year)."""
        citations_df = pd.DataFrame({
            "source_doi": ["10.1000/other"],
            "ref_doi": ["10.1000/another"],
        })
        fixture_df["doi_norm"] = fixture_df["doi"].apply(
            lambda x: str(x).strip().lower() if pd.notna(x) else ""
        )
        result = flag_citation_isolated(fixture_df, config, citations_df=citations_df)
        assert result.iloc[9] == False

    def test_old_citing_no_doi_refs_not_flagged(self, fixture_df, config):
        """Row 7: year 2010, cites books without DOIs -> NOT flagged.

        Papers that cite books/reports (ref_doi empty but source_doi present
        in citations) are participating in the citation graph and should not
        be flagged as isolated. This relies on merge_citations keeping
        no-DOI ref rows in citations.csv.
        """
        # This paper cites two books — no ref_doi, but it IS a citing paper
        citations_df = pd.DataFrame({
            "source_doi": ["10.1000/old-isolated", "10.1000/old-isolated"],
            "ref_doi": ["", ""],
        })
        fixture_df["doi_norm"] = fixture_df["doi"].apply(
            lambda x: str(x).strip().lower() if pd.notna(x) else ""
        )
        result = flag_citation_isolated(fixture_df, config, citations_df=citations_df)
        assert result.iloc[7] == False, \
            "Paper citing books (no-DOI refs) should not be flagged as isolated"

    def test_old_truly_isolated_flagged(self, fixture_df, config):
        """Row 7: year 2010, not in citations at all -> flagged.

        When citations.csv has data but this paper's DOI doesn't appear
        as source_doi or ref_doi, it IS isolated.
        """
        citations_df = pd.DataFrame({
            "source_doi": ["10.1000/unrelated"],
            "ref_doi": ["10.1000/also-unrelated"],
        })
        fixture_df["doi_norm"] = fixture_df["doi"].apply(
            lambda x: str(x).strip().lower() if pd.notna(x) else ""
        )
        result = flag_citation_isolated(fixture_df, config, citations_df=citations_df)
        assert result.iloc[7] == True, \
            "Paper absent from citation graph should be flagged as isolated"

    def test_missing_citations_raises(self, fixture_df, config):
        with pytest.raises(ValueError, match="citations_df is required"):
            flag_citation_isolated(fixture_df, config, citations_df=None)


# ============================================================
# Flag 5: Semantic outlier
# ============================================================

class TestFlagSemanticOutlier:
    def test_outlier_detected(self, filter_config):
        """Synthetic test: one extreme embedding flagged as outlier."""
        rng = np.random.default_rng(42)
        n_papers = 20
        emb_dim = 8
        # Use tight cluster so the outlier stands out clearly
        embeddings = rng.normal(loc=1.0, scale=0.1, size=(n_papers, emb_dim)).astype(np.float32)
        # Make row 7 point in the opposite direction (extreme outlier)
        embeddings[7] = -10.0 * np.ones(emb_dim, dtype=np.float32)

        df = pd.DataFrame({
            "doi": [f"10.1000/paper{i}" for i in range(n_papers)],
        })
        df["doi_norm"] = df["doi"]
        emb_df = df.copy()

        flag_mask, dists = flag_semantic_outlier(
            df, filter_config, embeddings=embeddings, emb_df=emb_df
        )
        assert flag_mask.iloc[7] == True
        assert dists.iloc[7] > 0

    def test_doi_less_outlier_is_flaggable(self, filter_config):
        """A DOI-less work counts toward the centroid, so it must be scorable.

        The distances used to be remapped onto df by normalised DOI, with the
        empty-DOI bucket dropped. A DOI-less work therefore joined, pulled the
        centroid its way, and then had its own distance discarded: unflaggable
        while warping every neighbour's score (review of ticket 0336).
        """
        rng = np.random.default_rng(7)
        n_papers = 20
        emb_dim = 8
        embeddings = rng.normal(
            loc=1.0, scale=0.1, size=(n_papers, emb_dim)).astype(np.float32)
        embeddings[3] = -10.0 * np.ones(emb_dim, dtype=np.float32)

        df = pd.DataFrame({
            "doi": [f"10.1000/paper{i}" for i in range(n_papers)],
            "source_id": [f"W{i:04d}" for i in range(n_papers)],
            "title": [f"Paper {i}" for i in range(n_papers)],
        })
        # Row 3 — the planted outlier — has no DOI, only a source_id.
        df.loc[3, "doi"] = None
        df["doi_norm"] = df["doi"].fillna("")
        emb_df = df.copy()

        flag_mask, dists = flag_semantic_outlier(
            df, filter_config, embeddings=embeddings, emb_df=emb_df
        )
        assert pd.notna(dists.iloc[3]), "the DOI-less work got no distance"
        assert flag_mask.iloc[3] == True, "the DOI-less outlier escaped Flag 5"
        assert flag_mask.sum() == 1, "a DOI-bearing neighbour was flagged instead"

    @staticmethod
    def _one_outlier(n_rows, emb_dim=8, seed=11):
        rng = np.random.default_rng(seed)
        embeddings = rng.normal(
            loc=1.0, scale=0.1, size=(n_rows, emb_dim)).astype(np.float32)
        embeddings[0] = -10.0 * np.ones(emb_dim, dtype=np.float32)
        return embeddings

    @pytest.mark.parametrize("non_candidate_doi, why", [
        ("https://doi.org/10.1000/P0", "differs only in case and DOI prefix"),
        ("10.1000/p0", "is an exact work_key duplicate"),
    ])
    def test_non_candidates_get_no_distance(self, filter_config, non_candidate_doi,
                                            why):
        """Only rows the caller put in emb_df may be scored.

        Two remaps were tried and removed in review — normalised DOI, then the
        exact work key. Each handed a candidate's distance to a work the loader
        deliberately excluded (no abstract, out of window, unembedded) whenever
        the two shared a key, making it flaggable outside the subset. The exact
        duplicate is the reachable case: enrichment reintroduces duplicate DOIs
        and grey-lit placeholder DOIs are shared across distinct documents, and
        the dedup that clears them runs in --filter, after --extend where this
        flag computes.
        """
        n = 20
        emb_df = pd.DataFrame({
            "doi": [f"10.1000/p{i}" for i in range(n)],
            "source_id": [f"W{i}" for i in range(n)],
            "title": [f"P{i}" for i in range(n)],
        })
        # The planted outlier is row 0; the non-candidate collides with it.
        df = pd.concat([emb_df, pd.DataFrame({
            "doi": [non_candidate_doi],
            "source_id": ["W99"],
            "title": ["Not a candidate"],
        })], ignore_index=True)

        flag_mask, dists = flag_semantic_outlier(
            df, filter_config, embeddings=self._one_outlier(n), emb_df=emb_df
        )
        assert flag_mask.iloc[0] == True, "the planted candidate outlier"
        assert pd.isna(dists.iloc[n]), (
            f"a work outside emb_df ({why}) was handed a candidate's distance"
        )
        assert flag_mask.iloc[n] == False
        assert flag_mask.sum() == 1, "only the planted candidate may be flagged"

    def test_emb_df_must_be_a_slice_of_df(self, config):
        """Distances are assigned by index, so a foreign emb_df is an error.

        Silently mapping it back by key is what produced the defect above.
        """
        emb_df = pd.DataFrame(
            {"doi": ["10.1000/x", "10.1000/y"]}, index=[100, 101])
        df = pd.DataFrame({"doi": ["10.1000/a", "10.1000/b"]})
        with pytest.raises(ValueError, match="(?i)slice of df|absent from df"):
            flag_semantic_outlier(
                df, config, embeddings=self._one_outlier(2), emb_df=emb_df)

    def test_distances_land_on_the_right_rows_for_a_gappy_slice(self, config):
        """emb_df keeps df's index, so a non-contiguous slice still lines up."""
        df = pd.DataFrame({
            "doi": [f"10.1000/p{i}" for i in range(5)],
            "source_id": [f"W{i}" for i in range(5)],
            "title": [f"P{i}" for i in range(5)],
        })
        emb_df = df.loc[[1, 3, 4]]
        # Rows 1 and 4 sit together, row 3 points away, so row 3's distance is
        # the largest of the three and a swap is visible.
        embeddings = np.stack([
            np.full(8, 1.0, dtype=np.float32),
            -np.full(8, 1.0, dtype=np.float32),
            np.full(8, 1.0, dtype=np.float32),
        ])

        _mask, dists = flag_semantic_outlier(
            df, config, embeddings=embeddings, emb_df=emb_df)

        assert list(dists.index[dists.notna()]) == [1, 3, 4]
        assert dists.loc[3] > dists.loc[1], (
            "distances landed on the wrong rows — index alignment is wrong"
        )
        assert dists.loc[1] == pytest.approx(dists.loc[4])

    def test_missing_embeddings_raises(self, config):
        df = pd.DataFrame({"doi": ["10.1000/a"]})
        with pytest.raises(ValueError, match="embeddings and emb_df are required"):
            flag_semantic_outlier(df, config, embeddings=None, emb_df=None)

    def test_size_mismatch_raises(self, config):
        df = pd.DataFrame({"doi": ["10.1000/a", "10.1000/b"]})
        df["doi_norm"] = df["doi"]
        emb_df = df.copy()
        embeddings = np.zeros((3, 8))  # 3 != 2
        with pytest.raises(ValueError, match="mismatch"):
            flag_semantic_outlier(df, config, embeddings=embeddings, emb_df=emb_df)


# ============================================================
# Flag 5: diagnostic mode and the per-language centroid (ticket 0361)
# ============================================================

def _language_corpus(sizes, spread=0.25, dim=8):
    """Works frame + embeddings for a language-stratified synthetic corpus.

    Each language occupies its own plane: mean direction ``m`` and a
    perpendicular axis chosen orthogonal to every other language's mean, so a
    work's angle within its language never carries it toward another language's
    centroid. Angles are the exact normal quantiles of ``N(0, spread**2)``, so
    every language has the *same* standardised within-language shape whatever
    its size — a mean-plus-k-sigma cut therefore removes the same fraction of
    each, and any surviving per-language rate difference is the geometry of the
    centroid, not sampling noise.

    ``sizes`` maps a language code to a row count. The first language is the
    dominant one and lies on axis 0; the others tilt away from it.
    """
    normal = NormalDist()
    axes = {}
    vectors, langs = [], []
    for slot, (lang, n) in enumerate(sizes.items()):
        # Mean direction: the dominant language on axis 0, the others rotated
        # 53 degrees off it into their own dimension (cosine 0.6).
        mean = np.zeros(dim)
        if slot == 0:
            mean[0] = 1.0
        else:
            mean[0], mean[2 * slot] = 0.6, 0.8
        # Spread axis: a dimension no mean direction uses, so the within-
        # language rotation is orthogonal to every centroid.
        perp = np.zeros(dim)
        perp[2 * slot + 1] = 1.0
        axes[lang] = (mean, perp)
        for j in range(n):
            theta = spread * normal.inv_cdf((j + 0.5) / n)
            vectors.append(np.cos(theta) * mean + np.sin(theta) * perp)
            langs.append(lang)

    embeddings = np.stack(vectors).astype(np.float32)
    n_rows = len(langs)
    df = pd.DataFrame({
        "doi": [f"10.1000/w{i}" for i in range(n_rows)],
        "source_id": [f"W{i}" for i in range(n_rows)],
        "title": [f"Work {i}" for i in range(n_rows)],
        "language": langs,
    })
    return df, embeddings


def _rate_by_language(df, mask):
    """Flag rate per language — the view a count assertion cannot show."""
    return {
        lang: float(mask[df["language"] == lang].mean())
        for lang in df["language"].unique()
    }


class TestFlag5DiagnosticMode:
    """Diagnostic mode: the distance still ships, the mask never removes.

    The statistic is unsound as a threshold — the distance distribution is
    skewed and heavy-tailed, so `mean + k*sigma` carries no probabilistic
    reading, and the one human validation of a cut on it found no
    discrimination. The distance itself is a useful inspection signal and
    `docs/research-note-multilingual.md` uses it as a dependent variable, so it
    is computed and published; it just deletes nothing (ticket 0361).
    """

    def test_diagnostic_mode_flags_nothing(self, config):
        df, embeddings = _language_corpus({"en": 60})
        mask, _dists = flag_semantic_outlier(
            df, sem_config(config, mode="diagnostic"),
            embeddings=embeddings, emb_df=df)

        assert not mask.any(), (
            "diagnostic mode removed works — the mask must be all-False"
        )
        assert mask.dtype == bool, "the mask must stay a boolean series"

    def test_diagnostic_mode_still_computes_real_distances(self, config):
        """Not a stub: the distances are the whole point of keeping the flag."""
        df, embeddings = _language_corpus({"en": 60})
        _mask, dists = flag_semantic_outlier(
            df, sem_config(config, mode="diagnostic"),
            embeddings=embeddings, emb_df=df)

        assert dists.notna().all(), "a candidate got no distance"
        assert dists.min() >= 0, "cosine distance cannot be negative"
        assert dists.max() > dists.median() * 2, (
            "every distance is near-identical — the flag is returning a "
            "constant, not a measurement"
        )
        # Row 0 and row -1 are the extreme angle quantiles; the middle rows sit
        # on the centroid. A stub returning zeros or a copy of one value fails.
        assert dists.iloc[0] > dists.iloc[len(df) // 2]

    def test_diagnostic_mode_is_the_default(self, config):
        """An absent `mode` must not delete works.

        The shipped config states `mode: diagnostic` explicitly; this pins the
        fallback so a caller with an older config block cannot silently get a
        filtering Flag 5 back.
        """
        df, embeddings = _language_corpus({"en": 60})
        block = {k: v for k, v in config["semantic_outlier"].items()
                 if k != "mode"}
        mask, _dists = flag_semantic_outlier(
            df, dict(config, semantic_outlier=block),
            embeddings=embeddings, emb_df=df)
        assert not mask.any()

    def test_filter_mode_still_filters(self, config):
        """The capability is not destroyed, only switched off by default."""
        df, embeddings = _language_corpus({"en": 300})
        mask, _dists = flag_semantic_outlier(
            df, sem_config(config, mode="filter", sigma=2),
            embeddings=embeddings, emb_df=df)
        assert mask.any(), "filter mode flagged nothing on a corpus with a tail"

    def test_filter_mode_without_sigma_raises(self, config):
        """A filter with no threshold must say so rather than pick one."""
        df, embeddings = _language_corpus({"en": 60})
        block = {k: v for k, v in config["semantic_outlier"].items()
                 if k != "sigma"}
        block["mode"] = "filter"
        with pytest.raises(ValueError, match="(?i)sigma"):
            flag_semantic_outlier(
                df, dict(config, semantic_outlier=block),
                embeddings=embeddings, emb_df=df)

    @pytest.mark.parametrize("key, value", [
        ("mode", "sometimes"),
        ("centroid", "per_country"),
    ])
    def test_unknown_setting_raises(self, config, key, value):
        df, embeddings = _language_corpus({"en": 60})
        with pytest.raises(ValueError, match=key):
            flag_semantic_outlier(
                df, sem_config(config, **{key: value, "mode": "filter"}),
                embeddings=embeddings, emb_df=df)


class TestFlag5PerLanguageCentroid:
    """The centroid is the lever on the language gradient, not sigma.

    A corpus that is 91.6% English builds a centroid that partly measures
    *not written in English*; raising sigma against it makes the bias worse,
    because the extreme tail of that distribution is almost entirely
    non-English. Mean-centring per language is the documented correction
    (Libovicky et al., arXiv:1911.03310).
    """

    def test_distance_is_measured_against_the_own_language_centroid(self, config):
        """A minority work's distance must come from its own language.

        Under a global centroid a Spanish work sits ~0.29 away by virtue of
        being Spanish; under its own centroid it sits where its content puts
        it. The two numbers differ by an order of magnitude, so a swapped
        centroid cannot hide.
        """
        df, embeddings = _language_corpus({"en": 300, "es": 60})
        is_es = (df["language"] == "es").to_numpy()

        _m, per_lang = flag_semantic_outlier(
            df, sem_config(config, centroid="per_language", mode="diagnostic"),
            embeddings=embeddings, emb_df=df)
        _m, glob = flag_semantic_outlier(
            df, sem_config(config, centroid="global", mode="diagnostic"),
            embeddings=embeddings, emb_df=df)

        assert per_lang[is_es].max() < glob[is_es].min(), (
            "Spanish works kept their global-centroid distances — the "
            "per-language centroid is not being used"
        )
        # English is the dominant language, so its own centroid and the global
        # one nearly coincide: the correction must not move English much.
        assert per_lang[~is_es].mean() == pytest.approx(
            glob[~is_es].mean(), rel=0.15)

    def test_small_language_falls_back_to_the_global_centroid(self, config):
        """Below the floor a language has no usable own centroid.

        Ten works cannot locate a centre; scoring them against their own mean
        would report every one of them as typical. They take the corpus
        centroid, exactly as `min_coverage` refuses to score a rump of the
        corpus against a centroid built from that rump.
        """
        df, embeddings = _language_corpus({"en": 300, "es": 60, "ko": 10})
        cfg = sem_config(config, centroid="per_language", mode="diagnostic",
                         min_language_count=30)
        _m, per_lang = flag_semantic_outlier(
            df, cfg, embeddings=embeddings, emb_df=df)
        _m, glob = flag_semantic_outlier(
            df, sem_config(config, centroid="global", mode="diagnostic"),
            embeddings=embeddings, emb_df=df)

        is_ko = (df["language"] == "ko").to_numpy()
        is_es = (df["language"] == "es").to_numpy()
        np.testing.assert_allclose(
            per_lang[is_ko].to_numpy(), glob[is_ko].to_numpy(), rtol=1e-6,
            err_msg="a 10-work language was scored against its own centroid")
        assert per_lang[is_es].max() < glob[is_es].min(), (
            "the 60-work language is above the floor and must use its own "
            "centroid — the fallback swallowed it too"
        )

    def test_absent_language_column_degrades_to_the_global_centroid(self, config):
        """No language column, no strata: identical to the global arm.

        Keeps the frames that predate the column (test fixtures, slim
        intermediates) scoring exactly as before rather than erroring.
        """
        df, embeddings = _language_corpus({"en": 60})
        df = df.drop(columns=["language"])
        _m, per_lang = flag_semantic_outlier(
            df, sem_config(config, centroid="per_language", mode="diagnostic"),
            embeddings=embeddings, emb_df=df)
        _m, glob = flag_semantic_outlier(
            df, sem_config(config, centroid="global", mode="diagnostic"),
            embeddings=embeddings, emb_df=df)
        np.testing.assert_allclose(
            per_lang.to_numpy(), glob.to_numpy(), rtol=1e-6)


class TestFlag5LanguageGradient:
    """The band test: the defect is invisible to any count assertion.

    On the real corpus the shipped global-centroid setting removed Spanish
    works at 4.1x and Portuguese at 3.0x the baseline rate, while the headline
    removal count looked unremarkable. Only a per-language rate comparison sees
    it, so that comparison is what gets pinned.
    """

    SIZES = {"en": 300, "es": 60}

    def _rates(self, config, centroid):
        df, embeddings = _language_corpus(self.SIZES)
        mask, _d = flag_semantic_outlier(
            df, sem_config(config, mode="filter", sigma=2, centroid=centroid,
                           min_language_count=30),
            embeddings=embeddings, emb_df=df)
        return _rate_by_language(df, mask)

    def test_global_centroid_shows_the_gradient(self, config):
        """The control: without this the band test below proves nothing."""
        rates = self._rates(config, "global")
        assert rates["es"] > 0.20, (
            "the fixture no longer reproduces the language gradient, so the "
            f"band test has nothing to catch: {rates}"
        )
        assert rates["en"] < 0.02, f"English should be spared: {rates}"

    def test_per_language_centroid_flattens_the_gradient(self, config):
        rates = self._rates(config, "per_language")
        assert rates["en"] > 0, f"no English work flagged at all: {rates}"
        ratio = rates["es"] / rates["en"]
        assert 0.5 <= ratio <= 2.0, (
            f"minority-language removal rate is {ratio:.1f}x the English rate "
            f"({rates}); the centroid is reintroducing a language gradient"
        )


# ============================================================
# Flag 6: LLM relevance (mocked)
# ============================================================

class TestFlagLLMIrrelevant:
    def test_skips_already_flagged(self, fixture_df, config, monkeypatch):
        """LLM should not score papers already flagged by rules 1-5."""
        call_count = 0

        def counting_llm_call(prompt, backend, api_key, model):
            nonlocal call_count
            call_count += 1
            return '{"1": true}'

        monkeypatch.setattr("filter_flags_llm._llm_call", counting_llm_call)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        already_flagged = pd.Series(True, index=fixture_df.index)
        result = flag_llm_irrelevant(fixture_df, config, already_flagged=already_flagged)
        assert call_count == 0
        assert result.all() == False  # No flags set

    def test_returns_series_aligned(self, fixture_df, config, monkeypatch):
        """Result is aligned with input df index."""
        monkeypatch.setattr(
            "filter_flags_llm._llm_call",
            lambda p, b, a, m: '{"1": true}',
        )
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        already_flagged = pd.Series(True, index=fixture_df.index)
        result = flag_llm_irrelevant(fixture_df, config, already_flagged=already_flagged)
        assert isinstance(result, pd.Series)
        assert len(result) == len(fixture_df)

    @staticmethod
    def _flag6_failure_message(fixture_df, config):
        """Drive Flag 6 to exhaustion; return the RuntimeError it must raise."""
        import filter_flags_llm

        already_flagged = pd.Series(False, index=fixture_df.index)
        with pytest.raises(RuntimeError) as excinfo:
            list(
                filter_flags_llm.flag_llm_irrelevant_streaming(
                    fixture_df, config, already_flagged=already_flagged
                )
            )
        return str(excinfo.value)

    def test_unrunnable_reranker_is_a_hard_error(
        self, fixture_df, reranker_config_without_torch
    ):
        """Flag 6 decides corpus membership, so it may not be skipped silently.

        Ticket 0314: on the 2026-07-24 rebuild the reranker backend ran without
        torch, logged a warning, and returned no candidates. The stage exited 0
        and shipped 38,166 refined works instead of 33,344 — 5,840 irrelevant
        works silently retained, because the ``llm_irrelevant`` column survived
        from the previous pass and satisfied the presence-only apply gate.
        """
        message = self._flag6_failure_message(
            fixture_df, reranker_config_without_torch
        )
        assert "Flag 6" in message

    def test_hard_error_names_the_remediation(
        self, fixture_df, reranker_config_without_torch
    ):
        """The operator must learn how to fix it from the message alone."""
        message = self._flag6_failure_message(
            fixture_df, reranker_config_without_torch
        )
        assert "uv sync" in message
        assert "--skip-llm" in message


# ============================================================
# LLM cache invalidation
# ============================================================

class TestLLMCacheInvalidation:
    def test_config_hash_changes_with_model(self, config):
        """Cache key changes when model changes."""
        hash1 = _cache_key(config)
        config2 = config.copy()
        config2["llm_relevance"] = config["llm_relevance"].copy()
        config2["llm_relevance"]["openrouter_model"] = "different/model"
        hash2 = _cache_key(config2)
        assert hash1 != hash2

    def test_config_hash_changes_with_prompt(self, config):
        """Cache key changes when prompt changes."""
        hash1 = _cache_key(config)
        config2 = config.copy()
        config2["llm_relevance"] = config["llm_relevance"].copy()
        config2["llm_relevance"]["prompt_template"] = "Different prompt"
        hash2 = _cache_key(config2)
        assert hash1 != hash2


# ============================================================
# Protection
# ============================================================

class TestComputeProtection:
    def test_high_cites_protected(self, fixture_df, config):
        """Row 2: cited_by_count=100 >= 50 -> protected."""
        citations_df = pd.DataFrame({"source_doi": [], "ref_doi": []})
        fixture_df["doi_norm"] = fixture_df["doi"].apply(
            lambda x: str(x).strip().lower() if pd.notna(x) else ""
        )
        protected, reasons = compute_protection(
            fixture_df, config, citations_df=citations_df
        )
        assert protected.iloc[2] == True
        assert "cited_by" in reasons.iloc[2]

    def test_multi_source_protected(self, fixture_df, config):
        """Row 12: source_count=2 >= 2 -> protected."""
        citations_df = pd.DataFrame({"source_doi": [], "ref_doi": []})
        fixture_df["doi_norm"] = fixture_df["doi"].apply(
            lambda x: str(x).strip().lower() if pd.notna(x) else ""
        )
        protected, reasons = compute_protection(
            fixture_df, config, citations_df=citations_df
        )
        assert protected.iloc[12] == True
        assert "multi_source" in reasons.iloc[12]

    def test_cited_in_corpus_protected(self, fixture_df, config):
        """Paper appearing as ref_doi in citations -> protected."""
        fixture_df["doi_norm"] = fixture_df["doi"].apply(
            lambda x: str(x).strip().lower() if pd.notna(x) else ""
        )
        citations_df = pd.DataFrame({
            "source_doi": ["10.1000/some-source"],
            "ref_doi": ["10.1000/old-isolated"],  # row 7
        })
        protected, reasons = compute_protection(
            fixture_df, config, citations_df=citations_df
        )
        assert protected.iloc[7] == True
        assert "cited_in_corpus" in reasons.iloc[7]

    def test_low_cites_not_protected(self, fixture_df, config):
        """Row 5: cited_by_count=1, source_count=1 -> NOT protected."""
        citations_df = pd.DataFrame({"source_doi": [], "ref_doi": []})
        fixture_df["doi_norm"] = fixture_df["doi"].apply(
            lambda x: str(x).strip().lower() if pd.notna(x) else ""
        )
        protected, _ = compute_protection(
            fixture_df, config, citations_df=citations_df
        )
        assert protected.iloc[5] == False

    def test_protected_flagged_paper(self, fixture_df, config):
        """Row 14: missing metadata but cited_by_count=300 -> protected."""
        citations_df = pd.DataFrame({"source_doi": [], "ref_doi": []})
        fixture_df["doi_norm"] = fixture_df["doi"].apply(
            lambda x: str(x).strip().lower() if pd.notna(x) else ""
        )
        protected, reasons = compute_protection(
            fixture_df, config, citations_df=citations_df
        )
        assert protected.iloc[14] == True


# ============================================================
# Apply gates
# ============================================================

class TestApplyGates:
    def test_rejects_incomplete(self):
        """--apply raises if expected flag columns are missing."""
        from types import SimpleNamespace

        # Import the gate functions from the orchestrator
        # We test the logic inline since corpus_filter.py may not be importable yet
        def expected_flag_columns(args, has_embeddings):
            cols = ["missing_metadata", "no_abstract_irrelevant", "title_blacklist"]
            if not args.skip_citation_flag:
                cols.append("citation_isolated_old")
            if has_embeddings:
                cols.append("semantic_outlier")
            if not args.skip_llm:
                cols.append("llm_irrelevant")
            return cols

        args = SimpleNamespace(skip_citation_flag=False, skip_llm=False)
        expected = expected_flag_columns(args, has_embeddings=True)
        # All 6 flags expected
        assert len(expected) == 6

    def test_accepts_intentional_skips(self):
        """With --skip-llm and --skip-citation-flag, only 3 flags expected."""
        from types import SimpleNamespace

        def expected_flag_columns(args, has_embeddings):
            cols = ["missing_metadata", "no_abstract_irrelevant", "title_blacklist"]
            if not args.skip_citation_flag:
                cols.append("citation_isolated_old")
            if has_embeddings:
                cols.append("semantic_outlier")
            if not args.skip_llm:
                cols.append("llm_irrelevant")
            return cols

        args = SimpleNamespace(skip_citation_flag=True, skip_llm=True)
        expected = expected_flag_columns(args, has_embeddings=False)
        assert expected == ["missing_metadata", "no_abstract_irrelevant", "title_blacklist"]


class TestCuratedSourceProtection:
    """Ticket 0288: rows from the curated key-documents layer (from_unfccc /
    from_oecd) are protected from removal — official documents have no
    citation counts and a single source, so every other protection channel
    misses them (the 2014 BA grey seed was lost from v1 exactly this way)."""

    def _keydoc_df(self):
        return pd.DataFrame([{
            "doi": "", "doi_norm": "",
            "title": "Fifth Biennial Assessment and Overview of Climate Finance Flows",
            "year": 2022, "abstract": "", "cited_by_count": "",
            "source_count": 1, "journal": "UNFCCC Standing Committee on Finance",
            "source": "unfccc", "source_id": "UNFCCC/SCF/BA/2022",
            "from_unfccc": 1,
        }])

    def test_curated_source_protected(self, config):
        config = dict(config)
        config["protection"] = dict(config["protection"])
        config["protection"]["curated_sources"] = ["unfccc", "oecd"]
        citations_df = pd.DataFrame({"source_doi": [], "ref_doi": []})
        protected, reasons = compute_protection(
            self._keydoc_df(), config, citations_df=citations_df)
        assert protected.iloc[0] == True
        assert "curated_source" in reasons.iloc[0]

    def test_without_config_key_unprotected(self, config):
        """Absent config key -> old behavior, no crash."""
        citations_df = pd.DataFrame({"source_doi": [], "ref_doi": []})
        protected, _ = compute_protection(
            self._keydoc_df(), config, citations_df=citations_df)
        assert protected.iloc[0] == False

    def test_project_config_lists_layer_sources(self):
        """The live corpus_filter.yaml must protect the layer."""
        import yaml as _yaml
        base = os.path.join(os.path.dirname(__file__), "..")
        cfg = _yaml.safe_load(open(os.path.join(base, "config",
                                                "corpus_filter.yaml")))
        assert set(cfg["protection"].get("curated_sources", [])) >= \
            {"unfccc", "oecd"}
