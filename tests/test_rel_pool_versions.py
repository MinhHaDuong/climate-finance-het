"""Dedup version 2, step 5: a working paper and its published article are one work (ticket 2048).

Author decisions of 2026-10-09: one work; article year minus working-paper
year within -1..+5; an explicit lane link overrides the window; never two
published versions in one work. Version 1 stays as it was.
"""

import csv
import json
import os

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
    def greedy(rows, uf, norm, words, idx=None, pairs=None, oa_dups=False):
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


# ── Stage B1 (2026-10-09): tightening, OpenAlex duplicates, naming, enrichment ──


def r2(first_author="", **kw):
    return {**r(**kw), "first_author": first_author}


@pytest.mark.parametrize("doi, doc_type, wp", [
    ("10.5281/zenodo.1", "dataset", False), ("10.5281/zenodo.1", "software", False),
    ("10.6084/m9.figshare.1", "Dataset", False), ("10.5281/zenodo.1", "", True),
    ("10.6084/m9.figshare.1", "", True), ("10.5281/zenodo.1", "report", True)])
def test_repository_doi_is_a_working_paper_unless_a_dataset_or_software(doi, doc_type, wp):
    assert rv.is_working_paper({"doi": doi, "doc_type": doc_type}) is wp


def test_short_title_needs_the_first_authors_to_agree():
    """Review of PR 1745: 'Climate Change Governance', HAL 2022 (Torre-Schaub)
    and CUP 2021 (Green), was a false merge."""
    title = "Climate Change Governance"
    rows = [r2("Torre-Schaub, M.", doc_type="report", title=title, year="2022", rid="hal"),
            r2("Green, J.", doi="10.1017/9781108", title=title, year="2021")]
    assert not joined(rows, 0, 1)
    stats = {}
    rd.cluster(rows, stats, version=2)
    assert stats["versions"]["pairs_short_title_refused"] == 1
    rows[1]["first_author"] = "Marta Torre-Schaub"
    assert joined(rows, 0, 1), "same first author: one work"
    rows[1]["first_author"] = ""
    assert not joined(rows, 0, 1), "an unknown author does not agree"
    rows[0]["version_hint"] = "10.1017/9781108"
    assert joined(rows, 0, 1), "a lane link needs no author"


def test_four_word_titles_need_no_author():
    rows = [r2("A, B.", doi="10.2139/ssrn.1", title="Climate change governance today", year="2010"),
            r2("C, D.", doi="10.1016/j.a", title="Climate change governance today", year="2011")]
    assert joined(rows, 0, 1)


def test_pairs_on_the_report_mark_alone_and_links_of_two_articles_are_counted():
    rows = [r(oa="W1", doc_type="report", year="2010"), r(doi="10.1016/j.a", year="2011"),
            r(doi="10.1016/j.b", title="Another title of an article here", year="2012",
              hint="10.1016/j.c"),
            r(doi="10.1016/j.c", title="The same article under an alias", year="2012")]
    stats = {}
    roots = rd.cluster(rows, stats, version=2)
    assert roots[0] == roots[1] and roots[2] == roots[3]
    v = stats["versions"]
    assert (v["pairs_accepted"], v["pairs_accepted_on_report_alone"]) == (1, 1)
    assert (v["hint_unions"], v["hint_unions_two_published"]) == (1, 1)


OA_TITLE = "Green bonds and the cost of capital"


def joined_oa(rows, a, b, oa_dups=True):
    roots = rd.cluster(rows, version=2, oa_dups=oa_dups)
    return roots[a] == roots[b]


def test_two_openalex_only_records_join_on_title_and_year_behind_the_switch():
    rows = [r(oa="W1", title=OA_TITLE, year="2019", doc_type="article"),
            r(oa="W2", title=OA_TITLE, year="2019", doc_type="article")]
    assert joined_oa(rows, 0, 1)
    assert not joined_oa(rows, 0, 1, oa_dups=False), "off by default"
    assert not joined(rows, 0, 1, version=1)
    rows[1]["year"] = "2020"
    assert not joined_oa(rows, 0, 1), "the year must be the same"


def test_openalex_duplicates_need_four_title_words():
    rows = [r(oa="W1", title="Green bonds pricing", year="2019"),
            r(oa="W2", title="Green bonds pricing", year="2019")]
    assert not joined_oa(rows, 0, 1)


def test_openalex_only_joins_the_one_doi_work_and_none_of_two():
    rows = [r(oa="W1", title=OA_TITLE, year="2019"), r(doi="10.1016/j.a", title=OA_TITLE, year="2019"),
            r(oa="W2", title=OA_TITLE, year="2019")]
    roots = rd.cluster(rows, version=2, oa_dups=True)
    assert len(set(roots)) == 1
    rows.append(r(doi="10.1007/b", title=OA_TITLE, year="2019"))
    stats = {}
    roots = rd.cluster(rows, stats, version=2, oa_dups=True)
    assert roots[0] == roots[2], "the two OpenAlex-only records still join each other"
    assert roots[0] not in (roots[1], roots[3]) and roots[1] != roots[3]
    assert stats["versions"]["oa_groups_two_doi"] == 1


def test_openalex_duplicates_never_chain_two_dois():
    """W1 sits next to one DOI work under one title and another under a second
    title: the cluster would gather two DOIs, so it joins nothing."""
    other = "Carbon markets in emerging economies revisited"
    rows = [r(oa="W1", title=OA_TITLE, year="2019"), r(doi="10.1016/j.a", title=OA_TITLE, year="2019"),
            r(oa="W1", title=other, year="2019", rid="w1-alt"),
            r(doi="10.1007/b", title=other, year="2019")]
    stats = {}
    roots = rd.cluster(rows, stats, version=2, oa_dups=True)
    assert len(set(roots)) == 3 and roots[1] != roots[3]
    assert stats["versions"]["oa_clusters_refused"] == 1


def test_step_5c_does_not_depend_on_row_order():
    rows = _version_rows() + [
        r(oa="W1", title=OA_TITLE, year="2019"), r(oa="W2", title=OA_TITLE, year="2019"),
        r(doi="10.1016/j.g", title=OA_TITLE, year="2019"),
        r(oa="W3", title="Adaptation finance flows", year="2019")]
    assert _order_independent(lambda rs: rd.cluster(rs, version=2, oa_dups=True), rows)


def test_openalex_pairs_are_reported_with_their_kind():
    pairs = []
    rows = [r(oa="W1", title=OA_TITLE, year="2019"), r(oa="W2", title=OA_TITLE, year="2019"),
            r(doi="10.1016/j.a", title=OA_TITLE, year="2019")]
    rd.cluster(rows, None, version=2, pairs=pairs, oa_dups=True)
    recs = rv.pair_records(rows, pairs)
    assert sorted((p["pair_id"], p["kind"]) for p in recs) == [
        ("D00000", "openalex_doi"), ("D00001", "openalex_doi"), ("O00000", "openalex")]


def test_published_article_names_the_work():
    import corpus_rel_pool as cp
    lane = "t1651-gavard-schoch"
    wp = r(doi="10.2139/ssrn.3799872", oa="W3134128683", year="2021", doc_type="report", origin=lane)
    art = r(doi="10.1017/s1355770x26100679", oa="W7212000826", year="2026",
            doc_type="journalArticle", origin=lane, hint="10.2139/ssrn.3799872")
    rows = [{c: "" for c in cp.META_COLUMNS} | x | {"catalogue_source": ""} for x in (wp, art)]
    lanes = {lane: 0}
    (p,) = cp.build_pool(rows, rd.cluster(rows, version=2), lanes, version=2)
    assert (p["work_key"], p["openalex_id"], p["doi"]) == (
        "openalex:W7212000826", "W7212000826", "10.1017/s1355770x26100679")
    rows[1]["openalex_id"] = ""
    (p,) = cp.build_pool(rows, rd.cluster(rows, version=2), lanes, version=2)
    assert p["work_key"] == "doi:10.1017/s1355770x26100679"
    assert rv.published_ids([rows[1]]) is None, "no working paper: default naming"
    # OpenAlex types the SSRN record (no DOI) as an article: the DOI-bearing article names the work.
    ssrn_oa = r(oa="W3144616097", doc_type="article", origin="catalogue")
    assert rv.published_ids([ssrn_oa, wp, art]) == ("W7212000826", "10.1017/s1355770x26100679")


def test_labels_keyed_by_either_version_1_key_map_to_the_article(tmp_path, monkeypatch):
    cfg, cat, intake = _fixture(tmp_path)
    _delivery(intake, "t1651-gs", "2026-09-30", [
        {"record_id": "1651-GS01", "query_id": "q1", "platform": "zotero",
         "retrieved_at": "2026-09-30", "title": "Climate finance and emission reductions: WP",
         "year": "2021", "doi": "10.2139/ssrn.3799872", "openalex_id": "W3134128683",
         "doc_type": "report", "version_hint": "1651-GS02"},
        {"record_id": "1651-GS02", "query_id": "q1", "platform": "zotero",
         "retrieved_at": "2026-09-30", "title": "International climate finance and emission",
         "year": "2026", "doi": "10.1017/s1355770x26100679", "openalex_id": "W7212000826",
         "doc_type": "journalArticle", "version_hint": "1651-GS01"}])
    report, _, _, table = _v2(tmp_path, monkeypatch, (cfg, cat, intake))
    pairs = {(t["old_work_key"], t["new_work_key"]) for t in table}
    assert ("openalex:W3134128683", "openalex:W7212000826") in pairs
    assert {n for o, n in pairs if o == "openalex:W7212000826"} <= {"openalex:W7212000826"}, \
        "the article keeps its key"
    nb = report["versions"]["named_by_published"]
    assert (nb["works"], nb["wp_key_rekeyed"]) == (1, 1)
    t = report["totals"]
    assert t["v1_keys_gone"] > 0
    assert (t["v1_keys_gone_not_in_table"], t["table_new_keys_not_in_v2"]) == (0, 0)


def test_table_check_reads_the_written_file_and_sees_a_missing_key(tmp_path):
    """Positive control: a table that lost the working paper's row is caught."""
    path = tmp_path / rm.MIGRATION_FILE
    pool1 = [{"work_key": "openalex:Wwp"}, {"work_key": "openalex:Wart"}]
    pool2 = [{"work_key": "openalex:Wart"}]
    rows = [{"from_version": "1", "to_version": "2", "inputs_md5": "m", "old_work_key": "openalex:Wwp",
             "new_work_key": "openalex:Wart", "change": "merge", "cause": "versions"}]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rm.MIGRATION_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    assert rm.check_table(path, pool1, pool2, "m")["v1_keys_gone_not_in_table"] == 0
    assert rm.check_table(path, pool1, pool2, "other build")["v1_keys_gone_not_in_table"] == 1


@pytest.mark.parametrize("a, b, same", [
    ("Wei Zhang", "Wei Li", False), ("Zhang, Wei", "Li, Wei", False),
    ("Wei Zhang", "Zhang, W.", True), ("Marta Torre-Schaub", "Torre-Schaub, M.", True),
    ("Claire Gavard", "C. Gavard", True), ("", "Gavard, C.", False)])
def test_first_authors_agree_on_the_surname_never_the_given_name(a, b, same):
    assert rv.same_first_author(a, b) is same


def test_short_title_test_does_not_depend_on_row_order():
    """One title key holds 'debt bonds' (4 words) and 'debtbonds' (3): the
    test reads the fewest words of both sides, whichever row comes first."""
    wp4 = r2("Acosta, A.", doi="10.2139/ssrn.7", title="Ecuadorian sovereign debt bonds", year="2010")
    wp3 = r2("Acosta, A.", doi="10.2139/ssrn.7", title="Ecuadorian sovereign debtbonds", year="2010",
             rid="alt")
    art = r2("Borja, B.", doi="10.1016/j.e", title="Ecuadorian sovereign debt bonds", year="2011")
    for rows in ([wp4, wp3, art], [wp3, wp4, art]):
        roots = rd.cluster(rows, version=2)
        assert roots[0] == roots[1] != roots[2], "three words on one side: authors must agree"


def test_openalex_duplicates_switch_is_parsed_strictly(tmp_path, monkeypatch):
    import corpus_rel_pool as cp
    from _rel_pool_report import RelPoolError
    cfg, cat, intake = _fixture(tmp_path)
    with pytest.raises(RelPoolError, match="openalex_duplicates"):
        cp.run({**cfg, "openalex_duplicates": "false"}, str(cat), str(intake),
               str(tmp_path / "out"), 2, str(tmp_path / "mig"))


def test_write_pool_refuses_the_production_pool_directory(tmp_path):
    import corpus_rel_pool as cp
    from _rel_pool_report import RelPoolError
    cfg, cat, intake = _fixture(tmp_path)
    for out in ("data/rel_pool", "data/rel_pool/v2"):
        with pytest.raises(RelPoolError, match="production pool"):
            cp.run(cfg, str(cat), str(intake), os.path.join(cp.ROOT, out), 2,
                   str(tmp_path / "mig"), write_pool=True)


def test_enriched_type_reaches_the_working_paper_mark_before_clustering():
    import _rel_pool_enrich as en
    rows = [r(oa="W9", year="2009"), r(doi="10.1016/j.a", year="2011", doc_type="article"),
            r(doi="10.1/typed", title="A typed row keeps its own type here", doc_type="article")]
    assert not joined(rows, 0, 1), "two published records"
    t = {"label": "rel_doc_types", "doi": "doi", "oa": "openalex_id", "fills": {"doc_type": "t"},
         "sha256": "x", "rows": [{"doi": "", "openalex_id": "https://openalex.org/W9", "t": "preprint"},
                                 {"doi": "10.1/typed", "openalex_id": "", "t": "preprint"}]}
    assert en.mark_doc_types(rows, [t]) == 1
    assert rows[0]["doc_type"] == "" and rows[0]["enriched_doc_type"] == "preprint"
    assert "enriched_doc_type" not in rows[2], "a row's own type wins"
    assert joined(rows, 0, 1)


def test_version_2_writes_the_production_shaped_pool_when_asked(tmp_path, monkeypatch):
    import corpus_rel_pool as cp
    cfg, cat, intake = _fixture(tmp_path)
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1780000000")
    out = tmp_path / "rel_pool"
    report = cp.run(cfg, str(cat), str(intake), str(out), 2, str(tmp_path / "migration"),
                    write_pool=True)
    with open(out / "pool.csv", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        pool = list(reader)
    assert reader.fieldnames == cp.POOL_COLUMNS
    assert len(pool) == report["totals"]["works_v2"]
    assert "repec:nbr:nberwo:35497" in {p["work_key"] for p in pool}
    assert json.loads((out / "merge_report.json").read_text())["dedup_version"] == 2
