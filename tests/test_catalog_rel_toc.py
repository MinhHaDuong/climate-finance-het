"""REL tables of contents (ticket 1650): normalisation, matching, register."""

import csv
import os

import _rel_toc_core as toc
import pytest

pytestmark = pytest.mark.domain_corpus

ROOT = os.path.dirname(os.path.dirname(__file__))


def test_normalize_title_strips_markup_accents_and_punctuation():
    raw = "<i>Carbon</i> Pricing: Évidence from <mml:math>CO<sub>2</sub></mml:math> Markets!"
    assert toc.normalize_title(raw) == "carbon pricing evidence from co2 markets"
    assert toc.normalize_title(None) == ""


@pytest.mark.parametrize("name,expected", [
    ("Christine Wörlen", "worlen"),
    ("Wörlen, Christine", "worlen"),
    ("van der Berg", "berg"),
    ("", ""),
    (None, ""),
])
def test_surname_key(name, expected):
    assert toc.surname_key(name) == expected


@pytest.mark.parametrize("title,expected", [
    ("Front Matter", "front-back-matter"),
    ("Issue Information", "front-back-matter"),
    ("Editorial Board", "front-back-matter"),
    ("Book Reviews", "book-review"),
    ("Books Received", "book-review"),
    ("Erratum: Carbon Taxes", "erratum"),
    ("Corrigendum to “Carbon taxes”", "erratum"),
    ("Editorial", "editorial"),
    ("Report of the Treasurer", "society-report"),
    ("Climate finance and the cost of capital", "article"),
    ("", "untitled"),
])
def test_classify_item_records_the_type_instead_of_dropping(title, expected):
    assert toc.classify_item(title) == expected


@pytest.mark.parametrize("title", [
    # real articles that prefix patterns sent to excluded.csv (gaze round 1, PR 1615)
    "Index-based insurance for climate risk management and rural development in Syria",
    "Index insurance and basis risk: A reconsideration",
    "Covered Interest Parity Arbitrage",
    "Coverage and framing of climate change adaptation in the media",
    "Corrections of Systematic Errors in the Padova series",
    "Contents and determinants of climate pledges",
    "Announcement effects of green bond issuance",
    "Subscription models for solar home systems",
    "Retraction of climate pledges and the credibility of policy",
    "Review of carbon pricing evidence across countries",
])
def test_classify_item_keeps_articles_that_start_like_notices(title):
    assert toc.classify_item(title) == "article"


@pytest.mark.parametrize("title", [
    "Index", "Author Index", "Subject index", "Index to Volume 12", "Cover 2/Editorial Board",
    "Contents", "Contents of Volume 30", "ANNOUNCEMENTS", "Announcement - call for abstracts",
    "Subscription information", "Instructions for Authors", "Masthead",
    # second review of PR 1615: notices delivered as articles
    "Recent Referees", "Back Cover", "Cover", "Contents page", "Cover page", "Volume contents",
    "Volume information", "Inside front cover - Editorial Board", "Title page", "Front cover",
    "Editorial advisory board", "List of Reviewers", "Acknowledgement to reviewers",
])
def test_classify_item_front_matter_shapes(title):
    assert toc.classify_item(title) == "front-back-matter"


@pytest.mark.parametrize("title", [
    "Erratum", "ERRATUM", "Corrigendum to “Carbon taxes”", "Correction", "Correction to: Carbon taxes",
    "Retraction notice to “Carbon taxes”", "Expression of concern: Carbon taxes",
    "Carbon taxes: Erratum", "Publisher Correction: Carbon taxes",
])
def test_classify_item_erratum_shapes(title):
    assert toc.classify_item(title) == "erratum"


@pytest.mark.parametrize("title", ["Editor’s note", "Editor's Introduction", "Editors’ note"])
def test_classify_item_editor_note_survives_the_apostrophe(title):
    assert toc.classify_item(title) == "editorial"


def test_editor_note_never_matches_the_pool_by_title():
    pool = toc.PoolIndex([{"doi": "", "title": "Editor’s note on climate finance", "first_author": "",
                           "year": "2022", "openalex_id": ""}])
    rec = {"doi": "10.1/x", "title": "Editor's note on climate finance",
           "first_author_surname": "", "year": 2022}
    assert pool.match(rec) == ""


def test_untitled_item_is_front_matter_only_when_it_is_an_issue_record():
    assert toc.exclusion_reason({"item_class": "untitled", "crossref_type": "journal-issue"}) \
        == "front_matter"
    assert toc.exclusion_reason({"item_class": "untitled", "crossref_type": "journal-article"}) \
        == "not_retrievable"


def test_merge_toc_takes_the_openalex_title_when_crossref_has_none():
    (rec,) = toc.merge_toc([_crrec(title="", item_class="untitled")],
                           [_oa(doi="10.1/a", title="Carbon pricing works")])
    assert rec["title"] == "Carbon pricing works"
    assert rec["item_class"] == "article"


def _cr(**kw):
    item = {"DOI": "10.1257/AER.1", "title": ["A title"], "type": "journal-article",
            "author": [{"given": "Ann", "family": "Smith"}, {"given": "Bo", "family": "Li"}],
            "volume": "80", "issue": "2", "published-print": {"date-parts": [[1990, 5]]},
            "issued": {"date-parts": [[1990, 5]]}}
    item.update(kw)
    return item


def test_crossref_record_parses_issue_and_authors():
    rec = toc.crossref_record(_cr(), journal_key="aer", issn="0002-8282")
    assert rec["doi"] == "10.1257/aer.1"
    assert (rec["volume"], rec["issue"], rec["year"]) == ("80", "2", 1990)
    assert rec["first_author_surname"] == "smith"
    assert rec["authors"] == "Smith, Ann; Li, Bo"
    assert rec["online_first"] is False


def test_crossref_record_without_volume_is_online_first_dated_online():
    item = _cr(volume=None, issue=None)
    del item["published-print"]
    item["published-online"] = {"date-parts": [[2026, 9, 1]]}
    item["issued"] = {"date-parts": [[2026, 9, 1]]}
    rec = toc.crossref_record(item, journal_key="aer", issn="0002-8282")
    assert rec["online_first"] is True
    assert rec["year"] == 2026
    assert toc.issue_key(rec) == ("aer", 2026, "", "online-first")


def _pool():
    return toc.PoolIndex([
        {"doi": "10.1/X", "title": "Carbon pricing works", "first_author": "Ann Smith",
         "year": "2001.0", "openalex_id": "W1"},
        {"doi": "", "title": "No author paper", "first_author": "", "year": "2005",
         "openalex_id": ""},
    ])


def test_match_by_doi_first():
    rec = {"doi": "10.1/x", "title": "Other", "first_author_surname": "zz", "year": 1990}
    assert _pool().match(rec) == "doi"


def test_match_by_openalex_id():
    rec = {"doi": "", "title": "Other", "first_author_surname": "zz", "year": 1990,
           "openalex_id": "W1"}
    assert _pool().match(rec) == "openalex_id"


def test_match_by_title_surname_year_tolerates_one_year():
    rec = {"doi": "10.9/other", "title": "Carbon Pricing Works!", "first_author_surname": "smith",
           "year": 2002}
    assert _pool().match(rec) == "title_author_year"
    rec["year"] = 2003
    assert _pool().match(rec) == ""
    rec["year"], rec["first_author_surname"] = 2001, "jones"
    assert _pool().match(rec) == ""


def test_title_year_match_only_when_pool_entry_has_no_author():
    rec = {"doi": "", "title": "No author paper", "first_author_surname": "smith", "year": 2005}
    assert _pool().match(rec) == "title_year_noauthor"


def test_generic_title_never_matches_by_title():
    pool = toc.PoolIndex([{"doi": "", "title": "Front Matter", "first_author": "",
                           "year": "2014", "openalex_id": ""}])
    rec = {"doi": "10.1257/x", "title": "Front Matter", "first_author_surname": "", "year": 2014}
    assert pool.match(rec) == ""


def _oa(**kw):
    rec = {"journal_key": "j", "openalex_id": "W9", "doi": "", "title": "Carbon pricing works",
           "item_class": "article", "openalex_type": "article", "authors": "Ann Smith",
           "first_author_surname": "smith", "year": 1995, "pub_date": "1995-03-01",
           "volume": "85", "issue": "1", "abstract": "abs"}
    rec.update(kw)
    return rec


def _crrec(**kw):
    rec = {"journal_key": "j", "issn": "x", "journal": "J", "doi": "10.1/a",
           "title": "Carbon pricing works", "item_class": "article",
           "crossref_type": "journal-article", "authors": "Smith, Ann",
           "first_author_surname": "smith", "year": 1995, "pub_date": "1995-3",
           "volume": "85", "issue": "1", "online_first": False, "abstract": "",
           "openalex_id": ""}
    rec.update(kw)
    return rec


def test_merge_toc_links_same_doi_and_fills_abstract():
    (rec,) = toc.merge_toc([_crrec()], [_oa(doi="10.1/a")])
    assert rec["openalex_id"] == "W9"
    assert rec["in_openalex"] is True
    assert rec["abstract"] == "abs"
    assert rec["toc_source"] == "crossref"


def test_merge_toc_folds_doi_alias_by_title_author_year():
    recs = toc.merge_toc([_crrec()], [_oa(doi="10.3763/alias")])
    assert len(recs) == 1
    assert recs[0]["openalex_id"] == "W9"
    assert recs[0]["alias_dois"] == "10.3763/alias"


def test_merge_toc_joins_several_aliases_with_semicolons():
    # version_hint cells are ";"-separated (docs/rel-intake-contract.md).
    recs = toc.merge_toc([_crrec()], [_oa(doi="10.3763/alias"), _oa(doi="10.3763/other")])
    assert recs[0]["alias_dois"] == "10.3763/alias;10.3763/other"


def test_merge_toc_keeps_openalex_only_item_without_doi():
    (rec,) = toc.merge_toc([], [_oa(title="An old JSTOR article", volume="80", issue="2")])
    assert rec["toc_source"] == "openalex-only"
    assert rec["online_first"] is False
    assert toc.issue_key(rec) == ("j", 1995, "80", "2")


def test_merge_toc_openalex_only_adopts_crossref_issue_year():
    recs = toc.merge_toc([_crrec(year=1996)], [_oa(title="Another paper", doi="10.9/b")])
    other = [r for r in recs if r["toc_source"] == "openalex-only"][0]
    assert other["year"] == 1996


def test_merge_toc_redates_misdated_openalex_item_by_annual_volume():
    # OpenAlex dates many JSTOR-era AER works 2016-01-01; volume 62 is 1972.
    cr = [_crrec(volume="89", year=1999, doi="10.1/a"),
          _crrec(volume="90", year=2000, doi="10.1/b", title="Other paper here")]
    recs = toc.merge_toc(cr, [_oa(title="Behavior of the firm", volume="62", issue="5",
                                  year=2016)])
    old = [r for r in recs if r["toc_source"] == "openalex-only"][0]
    assert old["year"] == 1972
    assert old["year_source"] == "volume-offset"
    assert not toc.in_window(old)


def test_merge_toc_never_redates_from_an_absurd_volume():
    cr = [_crrec(volume="89", year=1999, doi="10.1/a"),
          _crrec(volume="90", year=2000, doi="10.1/b", title="Other paper here")]
    recs = toc.merge_toc(cr, [_oa(title="Odd record", volume="11420", issue="", year=2021)])
    odd = [r for r in recs if r["toc_source"] == "openalex-only"][0]
    assert (odd["year"], odd["year_source"]) == (2021, "openalex")


def test_thematic_pass_is_one_ored_issn_filter_per_query():
    import _rel_toc_plan as cli

    mega = cli.load_manifest("thematic")
    queries = cli.thematic_queries(mega)
    assert [q["query_id"] for q in queries] == [
        "MJ-en-T1", "MJ-en-T2", "MJ-en-T3", "MJ-en-T4", "MJ-en-gap-fill"]
    all_issns = {i for j in mega for i in cli.issns(j)}
    for q in queries:
        issn_part = q["filter"].split("primary_location.source.issn:")[1]
        assert set(issn_part.split("|")) == all_issns
        assert "title_and_abstract.search:" in q["filter"]


def test_openalex_filter_uses_every_issn():
    import _rel_toc_plan as cli

    flt = cli.openalex_filter({"pissn": "0944-1344", "eissn": "1614-7499"})
    assert flt.startswith("primary_location.source.issn:0944-1344|1614-7499,")


def test_crossref_filter_queries_both_issns():
    # ESPR deposits 2023+ under its eISSN only: 13,125 works a pISSN sweep misses.
    flt = toc.crossref_filter({"pissn": "0944-1344", "eissn": "1614-7499"})
    assert flt.startswith("issn:0944-1344,issn:1614-7499,from-pub-date:1990-01-01")
    assert toc.crossref_filter({"pissn": "", "eissn": "2071-1050"}).startswith("issn:2071-1050,")


def _reg(**kw):
    rec = {"journal_key": "j", "year": 2001, "volume": "1", "issue": "1", "online_first": False,
           "in_pool": "", "doi": "10.1/x", "item_class": "article", "toc_source": "crossref"}
    rec.update(kw)
    return rec


def test_register_counts_per_toc_unit():
    recs = [_reg(in_pool="doi", doi="10.1/a"), _reg(doi="10.1/b"),
            _reg(item_class="front-back-matter", doi="10.1/c"),
            _reg(toc_source="openalex-only", doi="", openalex_id="W1"),
            _reg(issue="2", doi="10.1/d")]
    rows = {r["query_id"]: r for r in toc.build_register(recs)}
    one = rows["TOC-j-2001-v1-i1"]
    assert (one["expected"], one["scanned"], one["in_pool"]) == (4, 4, 1)
    assert one["front_matter"] == 1
    assert one["candidates"] == 2  # absent from the pool and not front matter
    assert one["unresolved"] == 1  # OpenAlex-only, no DOI
    assert rows["TOC-j-2001-v1-i2"]["candidates"] == 1


def test_unit_id_for_online_first_and_volume_only():
    assert toc.unit_id(_reg(online_first=True, volume="", issue="online-first")) == \
        "TOC-j-2001-online-first"
    assert toc.unit_id(_reg(issue="")) == "TOC-j-2001-v1-ina"


@pytest.mark.parametrize("item_class,reason", [
    ("front-back-matter", "front_matter"), ("erratum", "front_matter"),
    ("untitled", "not_retrievable"), ("book-review", ""), ("editorial", ""),
    ("society-report", ""), ("article", ""),
])
def test_only_non_items_are_excluded(item_class, reason):
    assert toc.exclusion_reason({"item_class": item_class}) == reason


def test_lane_status_is_information():
    assert toc.lane_status({"in_pool": "doi"}) == "already_in_pool"
    assert toc.lane_status({"in_pool": ""}) == "candidate"


def test_record_id_prefers_doi():
    assert toc.record_id({"doi": "10.1/a", "openalex_id": "W1"}) == "doi:10.1/a"
    assert toc.record_id({"doi": "", "openalex_id": "W1"}) == "openalex:W1"


def test_manifest_is_frozen_with_ranks_and_six_thematic_titles():
    with open(os.path.join(ROOT, "config", "rel_toc_manifest.csv"), encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 63  # 61 + AEA P&P + AER: Insights
    assert len({r["journal_key"] for r in rows}) == 63
    assert {r["journal_key"] for r in rows if r["sweep_mode"] == "thematic"} == {
        "sustainability", "energies", "environmental-science-and-pollution-research",
        "journal-of-cleaner-production", "journal-of-environmental-management",
        "applied-energy"}
    for r in rows:
        assert r["provenance"], r["title"]
        assert r["rank_sources"], r["title"]
        assert r["pissn"] or r["eissn"], r["title"]
        assert r["manifest_status"].startswith("frozen"), r["title"]
    by = {r["journal_key"]: r for r in rows}
    assert by["aer"]["cnrs37_2020_rank"] == "1e"
    assert by["aer"]["abdc_2025_rating"] == "A*"
