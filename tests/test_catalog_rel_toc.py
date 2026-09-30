"""REL tables of contents (ticket 1650): normalisation, matching, register."""

import csv
import os

import catalog_rel_toc as toc
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
