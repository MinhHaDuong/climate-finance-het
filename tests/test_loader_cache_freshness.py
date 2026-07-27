"""The Feather handoff cache may not outrank a newer CSV (ticket 0323).

`refined_works.feather` is a Phase-1→2 speed layer: the Makefile rebuilds it
from `refined_works.csv` whenever the CSV is newer. The loaders, though, read
it whenever it merely *exists*, so any invocation that skips Make's dependency
silently reads the previous corpus.

That happened. After the 2026-07-27 rebuild the cache was three days old: it
lacked `language_provenance` entirely and still carried the pre-0297
`language` column, so 1,350 rows disagreed with the corpus and
`lang_english_pct` computed to 89.86 against a measured 93.79. A rebuild that
does not move the numbers is the failure the vars-driven-prose rule exists to
prevent, and here the cache was swallowing it downstream of every guard.
"""

import os

import pandas as pd
import pytest

import _source_roots  # noqa: F401  (puts scripts/ on sys.path)
import pipeline_loaders

WORKS = {
    "doi": ["10.1/a", "10.1/b"],
    "year": [2001, 2002],
    "cited_by_count": [1, 2],
}


def _pair(tmp_path, csv_frame, feather_frame, csv_newer):
    """Write a CSV/Feather pair, ordering their mtimes explicitly."""
    csv_path = tmp_path / "refined_works.csv"
    feather_path = tmp_path / "refined_works.feather"
    pd.DataFrame(csv_frame).to_csv(csv_path, index=False)
    pd.DataFrame(feather_frame).to_feather(feather_path)
    old, new = 1_600_000_000, 1_700_000_000
    csv_t, feather_t = (new, old) if csv_newer else (old, new)
    os.utime(csv_path, (csv_t, csv_t))
    os.utime(feather_path, (feather_t, feather_t))
    return csv_path, feather_path


@pytest.fixture
def paths(tmp_path, monkeypatch):
    def _install(csv_frame, feather_frame, csv_newer):
        csv_path, feather_path = _pair(tmp_path, csv_frame, feather_frame, csv_newer)
        monkeypatch.setattr(pipeline_loaders, "REFINED_WORKS_PATH", str(csv_path))
        monkeypatch.setattr(
            pipeline_loaders, "REFINED_WORKS_FEATHER", str(feather_path)
        )
        return csv_path, feather_path

    return _install


def test_a_cache_older_than_the_corpus_is_not_served(paths):
    """The defect: a column added by a rebuild is invisible behind the cache."""
    paths(
        {**WORKS, "language_provenance": ["source", "detected:langdetect"]},
        WORKS,
        csv_newer=True,
    )
    works = pipeline_loaders.load_refined_works()
    assert "language_provenance" in works.columns


def test_a_cache_newer_than_the_corpus_is_still_served(paths):
    """The cache exists for speed; a correctness fix that disables it always
    is a performance regression, not a fix."""
    paths(WORKS, {**WORKS, "sentinel": ["from", "feather"]}, csv_newer=False)
    works = pipeline_loaders.load_refined_works()
    assert "sentinel" in works.columns


def test_a_cache_with_no_corpus_beside_it_is_served(paths, monkeypatch):
    """Reproducibility archives may ship one or the other. An absent CSV is
    not evidence that the cache is stale."""
    _csv_path, feather_path = paths(
        WORKS, {**WORKS, "sentinel": ["from", "feather"]}, csv_newer=True
    )
    monkeypatch.setattr(
        pipeline_loaders, "REFINED_WORKS_PATH", str(feather_path) + ".absent"
    )
    works = pipeline_loaders.load_refined_works()
    assert "sentinel" in works.columns


def test_the_same_rule_covers_the_citations_cache(tmp_path, monkeypatch):
    """Both handoff caches come off one Makefile pattern, so a guard on one
    of them is a guard the next rebuild walks around."""
    csv_path = tmp_path / "refined_citations.csv"
    feather_path = tmp_path / "refined_citations.feather"
    pd.DataFrame({"source_doi": ["10.1/a"], "ref_doi": ["10.2/b"]}).to_csv(
        csv_path, index=False
    )
    pd.DataFrame({"source_doi": ["10.1/a"]}).to_feather(feather_path)
    os.utime(feather_path, (1_600_000_000, 1_600_000_000))
    os.utime(csv_path, (1_700_000_000, 1_700_000_000))
    monkeypatch.setattr(pipeline_loaders, "REFINED_CITATIONS_PATH", str(csv_path))
    monkeypatch.setattr(
        pipeline_loaders, "REFINED_CITATIONS_FEATHER", str(feather_path)
    )
    assert "ref_doi" in pipeline_loaders.load_refined_citations().columns
