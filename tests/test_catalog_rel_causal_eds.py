"""Request building of the bibCNRS EDS lane (ticket 1652); offline only."""

import json

import catalog_rel_causal_eds as eds
import pytest

pytestmark = pytest.mark.domain_corpus


def test_econlit_date_becomes_the_eds_year_range_in_the_query_text():
    term, y0, y1 = eds.eds_term('(TI ("a") OR AB ("a")) AND DT 199001-202612')
    assert term == '(TI ("a") OR AB ("a")) AND DT 1990-2026'
    assert (y0, y1) == (1990, 2026)
    assert eds.eds_term('TI ("a")') == ('TI ("a")', None, None)


def test_field_codes_stay_in_the_term_and_the_provider_is_a_facet():
    p = eds.build_params('TI ("a")', "RePEc", 2, 50)
    q = json.loads(p["queries"])
    assert q == [{"boolean": "AND", "field": None, "term": 'TI ("a")'}]
    assert json.loads(p["activeFacets"]) == {"ContentProvider": ["RePEc"]}
    assert (p["currentPage"], p["resultsPerPage"]) == (2, 50)
    assert eds.provider_filter("ECONIS", 1990, 2026) == (
        "ContentProvider=ECONIS; DT 1990-2026 in the query text")


def test_first_form_is_parsed_without_a_third_party_parser():
    html = ('<html><form action="/idp/login" method="post">'
            '<input name="j_username" value=""><input name="csrf" value="t">'
            '<input type="submit"></form><form action="/other"><input name="x"></form>')
    action, data = eds.parse_first_form(html, "https://janus.example.org/idp/page")
    assert action == "https://janus.example.org/idp/login"
    assert data == {"j_username": "", "csrf": "t"}
    assert eds.parse_first_form("<p>no form</p>", "https://x.org/") is None


def test_slim_record_keeps_provenance_fields():
    rec = eds.slim_eds({"an": "edsrep.x", "dbId": "edsrep", "doi": "https://doi.org/10.1/AB",
                        "title": "T", "publicationDate": "2024-05-01T00:00:00.000Z",
                        "languages": ["English"], "publicationType": "Report",
                        "source": "S", "abstract": None})
    assert rec["eds_an"] == "edsrep.x" and rec["doi"] == "10.1/ab"
    assert rec["year"] == 2024 and rec["language"] == "English" and rec["abstract"] == ""


def test_working_paper_rows_are_not_replayed():
    rows = [{"econlit_string": "x", "formulation": f} for f in ("IM", "SI", "JEL", "WP")]
    assert [r["formulation"] for r in eds.eds_rows(rows)] == ["IM", "SI", "JEL"]


def test_slim_record_keeps_authors_ids_urls_and_the_whole_abstract():
    long_abstract = "word " * 600
    rec = eds.slim_eds({
        "an": "EDSZBW1", "dbId": "edszbw", "title": "T", "abstract": long_abstract,
        "authors": ["Li, Zirong", "Li, Hong"], "subjects": ["a"],
        "articleLinks": {"urls": [{"name": "Availability", "url": "https://ideas.repec.org/a/x/y/z.html"}]},
        "exportLinks": {"bibtex": "https://w.example/c?issn=0305-750X&isbn=9789819628605&volume=106"
                                  "&pages=1-14&doctype=Journal%20Article"}})
    assert rec["abstract"] == long_abstract and rec["authors"] == ["Li, Zirong", "Li, Hong"]
    assert rec["issn"] == "0305-750X" and rec["isbn"] == "9789819628605"
    assert (rec["volume"], rec["pages"], rec["doctype"]) == ("106", "1-14", "Journal Article")
    assert rec["urls"] == ["https://ideas.repec.org/a/x/y/z.html"]
    # the RePEc placeholder is no ISSN; a null author list and missing links are tolerated
    bare = eds.slim_eds({"an": "edsrep.p.a.b.c", "authors": None, "articleLinks": None,
                         "exportLinks": {"bibtex": "https://w.example/c?issn=edsr-ep"}})
    assert bare["issn"] == "" and bare["authors"] == [] and bare["urls"] == []
