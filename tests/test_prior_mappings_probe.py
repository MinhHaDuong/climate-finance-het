"""Unit tests for the prior-mappings overlap probe (ticket 0289).

The probe replicates published search queries of prior climate/green finance
bibliometric mappings against OpenAlex and reports what share of each
retrieved population is present in refined_works. These tests cover the
offline logic — DOI/title normalization, matching, coverage summary — on
fixture lists; no network, no real corpus.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBE = (
    ROOT
    / "deliverables"
    / "data-paper"
    / "revision-rdj26561"
    / "probe_prior_mappings_overlap.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("probe_prior_mappings", PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_norm_doi_variants_collapse():
    m = _load()
    variants = [
        "https://doi.org/10.1016/J.RIBAF.2023.101886",
        "http://dx.doi.org/10.1016/j.ribaf.2023.101886",
        "doi:10.1016/j.ribaf.2023.101886",
        "10.1016/j.ribaf.2023.101886",
    ]
    assert {m.norm_doi(v) for v in variants} == {"10.1016/j.ribaf.2023.101886"}


def test_match_records_doi_then_title_then_miss():
    m = _load()
    corpus_dois = {"10.1000/a", "10.1000/b"}
    corpus_titles = {m.norm_title("Climate Finance: A Review"): {2020}}
    records = [
        {"doi": "https://doi.org/10.1000/A", "title": "irrelevant"},
        {"doi": None, "title": "Climate finance — a review!",
         "publication_year": 2020},
        {"doi": "10.9999/miss", "title": "Nothing like the corpus"},
        {"doi": None, "title": None},
    ]
    how = [m.match_record(r, corpus_dois, corpus_titles) for r in records]
    assert how == ["doi", "title", None, None]


def test_title_match_is_year_constrained():
    """A title collision across distant years must not count as a match."""
    m = _load()
    corpus_titles = {m.norm_title("Climate finance"): {2005}}
    far = {"doi": None, "title": "Climate finance", "publication_year": 2019}
    near = {"doi": None, "title": "Climate finance", "publication_year": 2006}
    no_year = {"doi": None, "title": "Climate finance"}
    assert m.match_record(far, set(), corpus_titles) is None
    assert m.match_record(near, set(), corpus_titles) == "title"
    assert m.match_record(no_year, set(), corpus_titles) == "title"


def test_summarize_coverage_counts():
    m = _load()
    rows = [
        {"doi": "10.1000/a", "title": "x"},  # doi hit
        {"doi": None, "title": "climate finance a review",
         "publication_year": 2021},  # title hit
        {"doi": "10.9999/miss", "title": "zzz"},  # miss
        {"doi": None, "title": None},  # unmatchable
    ]
    corpus_dois = {"10.1000/a"}
    corpus_titles = {m.norm_title("climate finance a review"): {2021}}
    s = m.summarize("test_study", rows, corpus_dois, corpus_titles)
    assert s["study"] == "test_study"
    assert s["retrieved"] == 4
    assert s["matched_doi"] == 1
    assert s["matched_title"] == 1
    assert s["matched"] == 2
    assert s["coverage_pct"] == 50.0


def test_classify_miss_filtered_vs_not_captured():
    """A miss found in the extended (pre-filter) corpus is 'filtered_out';
    one absent from it was never captured by any source."""
    m = _load()
    ext_dois = {"10.1000/dropped"}
    ext_titles = {m.norm_title("Dropped by policy"): {2019}}
    audit = {"10.1000/dropped": {"action": "remove",
                                 "flags": "citation_isolated_old",
                                 "cited_by_count": "3"}}
    dropped = {"doi": "10.1000/dropped", "title": "x"}
    unseen = {"doi": "10.2000/unseen", "title": "Never retrieved"}
    a = m.classify_miss(dropped, ext_dois, ext_titles, audit)
    b = m.classify_miss(unseen, ext_dois, ext_titles, audit)
    assert a["status"] == "filtered_out"
    assert a["audit_flags"] == "citation_isolated_old"
    assert b["status"] == "not_captured"
    assert b["audit_flags"] == ""


def test_studies_cover_the_three_cited_mappings():
    m = _load()
    keys = {s["key"] for s in m.STUDIES}
    # the three prior mappings cited in manuscript.qmd / data-paper.qmd
    assert {"care_weber2023", "shang_jin2023", "maria_etal2023"} <= keys
    for s in m.STUDIES:
        assert s["reported_n"] > 0
        assert s["search"], f"{s['key']} has no search string"
        assert s["db"] in {"Scopus", "Web of Science"}
