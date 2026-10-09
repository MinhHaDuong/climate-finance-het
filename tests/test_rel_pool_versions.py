"""Dedup version 2, step 5: a working paper and its published article are one work (ticket 2048).

Author decisions of 2026-10-09: one work; article year minus working-paper
year within -1..+5; an explicit lane link overrides the window; never two
published versions in one work. Version 1 stays as it was.
"""

import csv

import _rel_pool_dedup as rd
import _rel_pool_migration as rm
import _rel_pool_versions as rv
import pytest
from _rel_title_key import title_key, title_words
from test_rel_pool_dedup_v2 import _delivery, _fixture, _order_independent, _v2

pytestmark = pytest.mark.domain_corpus

TITLE = "Climate finance and emission reductions in developing countries"


def r(doi="", oa="", title=TITLE, year="2010", doc_type="", hint="", origin="l", rid=None):
    return {"origin": origin, "delivery": f"{origin}/1", "record_id": f"{origin}/1:{rid or doi or oa}",
            "doi": doi, "openalex_id": oa, "handle": "", "repec": "", "title": title, "year": year,
            "doc_type": doc_type, "version_hint": hint}


def joined(rows, a, b, version=2):
    roots = rd.cluster(rows, version=version)
    return roots[a] == roots[b]


def test_gavard_schoch_pair_is_one_work_through_its_lane_link():
    """Recall: ZEW DP 2021 (SSRN DOI) and the 2026 article, linked by the 1651
    lane's version_link; titles differ and the gap is +5."""
    rows = [r(doi="10.2139/ssrn.3799872", oa="W3134128683", year="2021", doc_type="report",
              title="Climate Finance and Emission Reductions: What Do the Last Twenty Years Tell Us?",
              hint="1651-GS02", origin="t1651-gavard-schoch", rid="1651-GS01"),
            r(doi="10.1017/s1355770x26100679", oa="W7212000826", year="2026", doc_type="journalArticle",
              title="International climate finance and emission reductions: what do the last "
                    "twenty years tell us?", hint="1651-GS01", origin="t1651-gavard-schoch",
              rid="1651-GS02")]
    assert joined(rows, 0, 1)
    assert not joined(rows, 0, 1, version=1)
    unlinked = [{**x, "version_hint": ""} for x in rows]
    assert not joined(unlinked, 0, 1), "titles differ: only the lane link joins them"


def test_alias_doi_hint_joins_and_unresolved_hint_does_nothing():
    rows = [r(doi="10.1111/j.1468-0262.2008.00834.x", doc_type="journal-article",
              hint="10.1111/j.0012-9682.2008.00834.x"),
            r(doi="10.1111/j.0012-9682.2008.00834.x", title="Other title words entirely here"),
            r(doi="10.1111/x", title="A third work with a dangling hint", hint="10.9999/absent")]
    roots = rd.cluster(rows, version=2)
    assert roots[0] == roots[1] and roots[2] != roots[0]


@pytest.mark.parametrize("gap, expected", [(-2, False), (-1, True), (0, True), (5, True), (6, False)])
def test_window_edges(gap, expected):
    rows = [r(doi="10.2139/ssrn.1", year="2010"), r(doi="10.1016/j.a", year=str(2010 + gap))]
    assert joined(rows, 0, 1) is expected
    assert not joined(rows, 0, 1, version=1)


@pytest.mark.parametrize("wp", [
    {"doi": "10.21203/rs.3.rs-1/v1"}, {"doi": "10.3386/w33624"}, {"doi": "10.5281/zenodo.1"},
    {"doi": "10.31219/osf.io/x"}, {"doi": "10.31235/osf.io/y"}, {"doi": "10.48550/arxiv.1"},
    {"doi": "10.1787/oecd-wp", "doc_type": "working-paper"},
    {"doc_type": "Working paper"}, {"doc_type": "posted-content"}, {"doc_type": "preprint"},
    {"oa": "W5", "doc_type": "report"}])
def test_each_working_paper_mark_joins_its_article(wp):
    rows = [r(**{"year": "2009", **wp}), r(doi="10.1016/j.a", year="2011", doc_type="article")]
    assert joined(rows, 0, 1)


def test_two_published_versions_never_join():
    """Two articles, same title, distinct DOIs, no working-paper mark: two works."""
    rows = [r(doi="10.1016/j.a", year="2010"), r(doi="10.1007/b", year="2011")]
    assert not joined(rows, 0, 1)


def test_generic_title_never_joins():
    """Precision: two distinct works with a generic title and nearby years."""
    rows = [r(doi="10.2139/ssrn.9", title="Introduction", year="2010"),
            r(doi="10.1016/j.intro", title="Introduction", year="2011")]
    assert not joined(rows, 0, 1)


def test_working_paper_fitting_two_articles_joins_neither():
    rows = [r(doi="10.2139/ssrn.1", year="2010"), r(doi="10.1016/j.a", year="2011"),
            r(doi="10.1007/b", year="2012")]
    roots = rd.cluster(rows, version=2)
    assert len(set(roots)) == 3, "a working paper never chains two published versions"
    rows[2]["year"] = "2020"
    roots = rd.cluster(rows, version=2)
    assert roots[0] == roots[1] != roots[2], "the second article is out of the window"


def test_lane_link_then_title_never_brings_a_second_article():
    """The hint makes the working paper part of a published work; a second
    article with the working paper's title stays apart."""
    rows = [r(doi="10.2139/ssrn.1", year="2010", hint="10.1016/j.a"),
            r(doi="10.1016/j.a", year="2012", title="The published title differs"),
            r(doi="10.1007/b", year="2011")]
    roots = rd.cluster(rows, version=2)
    assert roots[0] == roots[1] != roots[2]


def test_several_working_papers_join_one_article():
    rows = [r(doi="10.2139/ssrn.1", year="2009"), r(doi="10.3386/w1", year="2010"),
            r(doc_type="working-paper", year="2010", rid="repec-wp"),
            r(doi="10.1016/j.a", year="2012")]
    assert len(set(rd.cluster(rows, version=2))) == 1


def _version_rows():
    return [r(doi="10.2139/ssrn.1", year="2010"), r(doi="10.1016/j.a", year="2011"),
            r(doi="10.1007/b", year="2012"),
            r(doi="10.2139/ssrn.2", year="2014", title="Carbon pricing in emerging economies"),
            r(doi="10.1016/j.c", year="2016", title="Carbon pricing in emerging economies"),
            r(doc_type="working-paper", year="2015", title="Carbon pricing in emerging economies",
              rid="wp-c"),
            r(doi="10.21203/rs.3", year="2019", title="Adaptation finance flows",
              hint="10.1016/j.e"),
            r(doi="10.1016/j.e", year="2025", title="Adaptation finance flows revisited")]


def test_step_5_does_not_depend_on_row_order():
    rows = _version_rows()
    roots = rd.cluster(rows, version=2)
    assert len({roots[i] for i in (3, 4, 5)}) == 1 and roots[6] == roots[7]
    assert len({roots[i] for i in (0, 1, 2)}) == 3
    assert _order_independent(lambda rs: rd.cluster(rs, version=2), rows)


def test_order_test_catches_a_greedy_step_5(monkeypatch):
    """Positive control: a step 5 that joins a working paper to the first
    article it meets is order-dependent, and the same test sees it."""
    def greedy(rows, uf, norm, words, idx=None, pairs=None):
        done = set()
        for i, a in enumerate(rows):
            if not rv.is_working_paper(a) or i in done:
                continue
            for j, b in enumerate(rows):
                if rv.is_published(b) and norm(a["title"]) == norm(b["title"]) \
                        and -1 <= int(b["year"]) - int(a["year"]) <= 5:
                    uf.union(i, j)
                    done.add(i)
                    break
        return {}
    monkeypatch.setattr(rd, "version_unions", greedy)
    assert not _order_independent(lambda rs: rd.cluster(rs, version=2), _version_rows())


def test_pairs_report_the_accepted_title_pairs():
    pairs = []
    rows = _version_rows()
    rd.cluster_with(rows, None, title_key, repec=True, guard=True, versions=True, pairs=pairs)
    got = sorted((p["kind"], rows[p["a_row"]]["doi"] or rows[p["a_row"]]["record_id"],
                  rows[p["b_row"]]["doi"], p["gap"]) for p in pairs)
    assert got == [("link", "10.21203/rs.3", "10.1016/j.e", ""),
                   ("window", "10.2139/ssrn.2", "10.1016/j.c", 2),
                   ("window", "l/1:wp-c", "10.1016/j.c", 1)]


def test_recall_on_known_multi_doi_works():
    rows = [r(doi="10.2139/ssrn.1", year="2010"), r(doi="10.1016/j.a", year="2011"),
            r(doi="10.1016/j.b", year="2011"), r(doi="10.1007/c", year="2012")]
    out = rv.recall_on_known(rows, [[0, 1], [2, 3]], "doi", title_key, title_words, rd.UnionFind)
    assert (out["works"], out["rejoined"], out["missed_by_reason"]) == (
        2, 1, {"no_working_paper": 1})


def test_version_2_report_counts_step_5(tmp_path, monkeypatch):
    cfg, cat, intake = _fixture(tmp_path)
    _delivery(intake, "t1651-gs", "2026-09-30", [
        {"record_id": "1651-GS01", "query_id": "q1", "platform": "zotero",
         "retrieved_at": "2026-09-30", "title": "Climate finance and emission reductions: WP",
         "year": "2021", "doi": "10.2139/ssrn.3799872", "doc_type": "report",
         "version_hint": "1651-GS02"},
        {"record_id": "1651-GS02", "query_id": "q1", "platform": "zotero",
         "retrieved_at": "2026-09-30", "title": "International climate finance and emission",
         "year": "2026", "doi": "10.1017/s1355770x26100679", "doc_type": "journalArticle",
         "version_hint": "1651-GS01"}])
    report, _, mig, table = _v2(tmp_path, monkeypatch, (cfg, cat, intake))
    assert report["versions"]["works_made_by_step_5"] == 1
    assert report["counts"]["versions_merged"]["total"] == 1
    assert report["stats"]["v2"]["versions"]["hint_unions"] == 1
    assert any(t["change"] == "merge" and t["cause"] == "versions" for t in table)
    assert "## Step 5" in (mig / "dedup_v2_report.md").read_text(encoding="utf-8")
    with open(mig / rm.PAIRS_FILE, encoding="utf-8", newline="") as fh:
        pairs = list(csv.DictReader(fh))
    assert [(p["pair_id"], p["kind"], p["b_doi"]) for p in pairs] == [
        ("L00000", "link", "10.1017/s1355770x26100679")]


def test_a_sici_doi_counts_as_one_doi():
    """The multi-DOI count split ``all_dois`` on every ``;``; a SICI DOI holds one."""
    import _rel_pool_migration as rm
    sici = "10.1002/(sici)1099-1328(199801)7:1<45::aid-jae38>3.0.co;2-d"
    assert rm.dois_of(sici) == [sici]
    assert rm.dois_of(f"10.1016/j.a;{sici}") == ["10.1016/j.a", sici]
    assert rm.dois_of("") == []
