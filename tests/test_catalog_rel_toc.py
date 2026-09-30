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


def test_crossref_filter_queries_both_issns():
    # ESPR deposits 2023+ under its eISSN only: 13,125 works a pISSN sweep misses.
    flt = toc.crossref_filter({"pissn": "0944-1344", "eissn": "1614-7499"})
    assert flt.startswith("issn:0944-1344,issn:1614-7499,from-pub-date:1990-01-01")
    assert toc.crossref_filter({"pissn": "", "eissn": "2071-1050"}).startswith("issn:2071-1050,")


def test_register_never_counts_a_needs_human_issue_as_scanned():
    recs = [
        {"journal_key": "j", "year": 2001, "volume": "1", "issue": "1", "online_first": False,
         "in_pool": "doi", "doi": "a"},
        {"journal_key": "j", "year": 2001, "volume": "1", "issue": "1", "online_first": False,
         "in_pool": "", "doi": "b"},
        {"journal_key": "j", "year": 2001, "volume": "1", "issue": "2", "online_first": False,
         "in_pool": "", "doi": "c"},
    ]
    checks = {("j", 2001, "1", "1"): {"status": "verified", "reason": "", "toc_source": "pub",
                                      "publisher_n": 2, "publisher_only": 0},
              ("j", 2001, "1", "2"): {"status": "needs-human", "reason": "http 403",
                                      "toc_source": "pub", "publisher_n": "",
                                      "publisher_only": ""}}
    rows = {(r["volume"], r["issue"]): r for r in toc.build_register(recs, checks)}
    assert rows[("1", "1")]["expected"] == 2
    assert rows[("1", "1")]["scanned"] == 2
    assert rows[("1", "1")]["in_pool"] == 1
    assert rows[("1", "1")]["candidates"] == 1
    assert rows[("1", "2")]["scanned"] == 0
    assert rows[("1", "2")]["status"] == "needs-human"
    assert rows[("1", "2")]["reason"] == "http 403"


def test_register_marks_unchecked_issue_not_scanned():
    recs = [{"journal_key": "j", "year": 2001, "volume": "1", "issue": "3",
             "online_first": False, "in_pool": "", "doi": "d"}]
    (row,) = toc.build_register(recs, {})
    assert row["status"] == "not-checked"
    assert row["scanned"] == 0


def test_manifest_has_61_unique_titles_with_provenance_and_rank_scale():
    with open(os.path.join(ROOT, "config", "rel_toc_manifest.csv"), encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 61
    assert len({r["journal_key"] for r in rows}) == 61
    for r in rows:
        assert r["provenance"], r["title"]
        assert r["rank_scale"], r["title"]
        assert r["pissn"] or r["eissn"], r["title"]
