"""REL south sources, Latin America lane (ticket 1653): adapters on canned responses."""

import json
import types

import pytest
from rel_sud_sources import (
    _clacso as clacso,
)
from rel_sud_sources import (
    _ipea as ipea,
)
from rel_sud_sources import (
    _latam_dspace as latam_dspace,
)
from rel_sud_sources import (
    _redalyc as redalyc,
)
from rel_sud_sources import (
    _scielo as scielo,
)
from rel_sud_sources import (
    _uwi as uwi,
)

pytestmark = pytest.mark.domain_corpus

LEXICON = {
    "en": {"T1": '"climate finance" OR "Green Climate Fund"', "T4": '"climate justice"'},
    "es": {"T1": '"financiamiento climático"', "T4": '"justicia climática"'},
    "pt": {"T1": '"financiamento climático"', "T4": '"justiça climática"'},
}


def resp(body, status=200):
    content = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
    return types.SimpleNamespace(status_code=status, content=content,
                                 json=lambda: json.loads(content.decode("utf-8")))


def recorder(pages):
    calls = []
    it = iter(pages)

    def get(url, params=None, delay=0):
        calls.append((url, dict(params or {}), delay))
        return next(it)
    return get, calls


def dspace_item(handle, title, year="2019-05", abstract="", doi=None):
    md = {"dc.title": [{"value": title}],
          "dc.date.issued": [{"value": year}],
          "dc.contributor.author": [{"value": "Silva, A."}, {"value": "Souza, B."}],
          "dc.identifier.uri": [{"value": f"https://repo.example/handle/{handle}"}],
          "dc.language.iso": [{"value": "por"}],
          "dc.type": [{"value": "Working paper"}]}
    if abstract:
        md["dc.description.abstract"] = [{"value": abstract}]
    if doi:
        md["dc.identifier.doi"] = [{"value": doi}]
    return {"_embedded": {"indexableObject": {"type": "item", "uuid": "u-" + handle,
                                              "handle": handle, "metadata": md}}}


def dspace_page(objects, number, total_pages, total):
    return {"_embedded": {"searchResult": {
        "page": {"number": number, "size": 100, "totalPages": total_pages,
                 "totalElements": total},
        "_embedded": {"objects": objects}}}}


# ---------------------------------------------------------------------------
# Plans: one query per language x theme, exact string recorded
# ---------------------------------------------------------------------------

def test_plans_cover_every_language_theme_with_readable_query_strings():
    cfg = {"lexicon": LEXICON}
    ids = [s["query_id"] for s in ipea.plan(cfg)]
    assert ids == ["S-ipea-pt-T1", "S-ipea-pt-T4", "S-ipea-en-T1", "S-ipea-en-T4"]
    spec = ipea.plan(cfg)[0]
    assert spec["query_string"] == (
        'query="financiamento climático"&dsoType=ITEM&scope=' + ipea.TD_COLLECTION)
    assert [s["query_id"] for s in clacso.plan(cfg)][0] == "S-clacso-es-T1"
    assert [s["query_id"] for s in uwi.plan(cfg)] == ["S-uwi-en-T1", "S-uwi-en-T4"]
    r = redalyc.plan(cfg)
    assert len(r) == 6 and r[0]["query_id"] == "S-redalyc-es-T1"
    assert r[0]["query_string"].endswith('getArticles/"financiamiento climático"/<page>/200/1/default')


# ---------------------------------------------------------------------------
# DSpace 7 discovery
# ---------------------------------------------------------------------------

def test_dspace_pages_to_the_end_and_normalizes_items():
    spec = ipea.plan({"lexicon": LEXICON})[0]
    get, calls = recorder([
        resp(dspace_page([dspace_item("11058/1", "Financiamento climático no Brasil",
                                      doi="https://doi.org/10.38116/TD2900")], 0, 2, 2)),
        resp(dspace_page([dspace_item("11058/2", "Outra coisa")], 1, 2, 2)),
    ])
    events = list(ipea.fetch(spec, 1.0, get=get))
    assert events[0] == ("meta", 2)
    assert events[-1] == ("end", "")
    recs = [v for k, v in events if k == "work"]
    assert recs[0]["record_id"] == "hdl:11058/1"
    assert recs[0]["doi"] == "10.38116/td2900"
    assert recs[0]["year"] == 2019
    assert recs[0]["authors"] == "Silva, A.; Souza, B."
    assert recs[0]["url"] == "https://repo.example/handle/11058/1"
    assert recs[0]["matched_terms"] == "financiamento climático"
    assert recs[1]["matched_terms"] == ""
    assert [c[1]["page"] for c in calls] == [0, 1]
    assert calls[0][1]["scope"] == ipea.TD_COLLECTION
    assert calls[0][1]["query"] == '"financiamento climático"'


def test_dspace_short_count_and_http_error_are_incomplete():
    spec = uwi.plan({"lexicon": LEXICON})[0]
    get, _ = recorder([resp(dspace_page([dspace_item("2139/1", "x")], 0, 1, 3))])
    assert list(uwi.fetch(spec, 0, get=get))[-1] == ("end", "short: 1 of 3")
    get, _ = recorder([resp({}, status=503)])
    assert list(uwi.fetch(spec, 0, get=get)) == [("end", "http 503")]


def test_dspace_empty_answer_is_complete():
    spec = uwi.plan({"lexicon": LEXICON})[0]
    get, _ = recorder([resp(dspace_page([], 0, 0, 0))])
    assert list(uwi.fetch(spec, 0, get=get)) == [("meta", 0), ("end", "")]


def test_clacso_honours_its_crawl_delay():
    spec = clacso.plan({"lexicon": LEXICON})[0]
    get, calls = recorder([resp(dspace_page([], 0, 0, 0))])
    list(clacso.fetch(spec, 1.0, get=get))
    assert calls[0][2] == clacso.CRAWL_DELAY


def test_dspace_year_falls_back_to_dc_date_never_to_deposit_dates():
    md = {"dc.title": [{"value": "T"}], "dc.date": [{"value": "2012"}],
          "dc.date.accessioned": [{"value": "2022-03-16T20:52:09Z"}]}
    assert latam_dspace.item_to_record({"metadata": md}, "https://h")["year"] == 2012
    del md["dc.date"]
    assert latam_dspace.item_to_record({"metadata": md}, "https://h")["year"] is None


def test_dspace_item_without_handle_or_date():
    rec = latam_dspace.item_to_record({"uuid": "abc", "metadata": {
        "dc.title": [{"value": "T"}]}}, "https://h")
    assert rec["record_id"] == "abc" and rec["year"] is None and rec["url"] == ""


# ---------------------------------------------------------------------------
# Redalyc search service
# ---------------------------------------------------------------------------

def redalyc_art(cve, title, doi=" ", year="2023"):
    return {"cveArticulo": cve, "titulo": title, "doiTitulo": doi, "anioArticulo": year,
            "autores": "Ana Pérez, Juan Díaz", "idiomaArticulo": "Español",
            "nomRevista": "Estado & comunes", "resumen": "es: Sobre la justicia climática."}


def test_redalyc_decodes_utf8_pages_until_total_and_encodes_the_path():
    spec = redalyc.plan({"lexicon": LEXICON})[0]
    p1 = {"totalResultados": "3", "resultados": [redalyc_art("1", "Financiamiento climático"),
                                                  redalyc_art("2", "B", doi="10.1234/X.9")]}
    p2 = {"totalResultados": "3", "resultados": [redalyc_art("3", "C")]}
    get, calls = recorder([resp(json.dumps(p1, ensure_ascii=False).encode("utf-8")),
                           resp(json.dumps(p2, ensure_ascii=False).encode("utf-8"))])
    events = list(redalyc.fetch(spec, 1.0, get=get))
    assert events[0] == ("meta", 3) and events[-1] == ("end", "")
    recs = [v for k, v in events if k == "work"]
    assert len(recs) == 3
    assert recs[0]["url"] == "https://www.redalyc.org/articulo.oa?id=1"
    assert recs[0]["authors"] == "Ana Pérez, Juan Díaz"
    assert recs[0]["doi"] == "" and recs[1]["doi"] == "10.1234/x.9"
    assert recs[0]["matched_terms"] == "financiamiento climático; justicia climática"
    assert recs[2]["matched_terms"] == "justicia climática"
    assert calls[0][0].endswith("/%22financiamiento%20clim%C3%A1tico%22/1/200/1/default")
    assert calls[1][0].endswith("/2/200/1/default")


# ---------------------------------------------------------------------------
# SciELO: journal selection, then per-journal OAI harvest matched locally
# ---------------------------------------------------------------------------

def am_journal(code, title, area="", wos=""):
    j = {"code": code, "v100": [{"_": title}]}
    if area:
        j["v441"] = [{"_": area}]
    if wos:
        j["v854"] = [{"_": wos}]
    return j


SCIELO_OAI = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><ListRecords>
<record><header><identifier>oai:scielo:S0301-70362019000100001</identifier></header>
<metadata><oai-dc:dc xmlns:oai-dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
 xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title><![CDATA[El financiamiento climático en México]]></dc:title>
<dc:creator><![CDATA[Pérez,Ana]]></dc:creator><dc:date>2019-03-01</dc:date>
<dc:identifier>http://www.scielo.org.mx/scielo.php?script=sci_arttext&amp;pid=S0301-70362019000100001</dc:identifier>
<dc:relation>10.22201/iiec.20078951e.2019.196.1</dc:relation>
</oai-dc:dc></metadata></record>
<record><header status="deleted"><identifier>oai:scielo:gone</identifier></header></record>
<record><header><identifier>oai:scielo:S2</identifier></header>
<metadata><oai-dc:dc xmlns:oai-dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Poesía</dc:title></oai-dc:dc></metadata></record>
<resumptionToken completeListSize="3"></resumptionToken>
</ListRecords></OAI-PMH>""".encode("utf-8")


def test_scielo_selects_social_science_journals_one_spec_per_set():
    listing = [am_journal("0301-7036", "Problemas del desarrollo", area="Applied Social Sciences"),
               am_journal("1111-1111", "Revista de poesía", area="Linguistics, Letters and Arts"),
               am_journal("2222-2222", "Ambiente y Desarrollo", wos="ENVIRONMENTAL STUDIES")]
    seen = []

    def get(url, params=None, delay=0):
        seen.append(params["collection"])
        return types.SimpleNamespace(status_code=200, json=lambda: listing,
                                     raise_for_status=lambda: None)
    specs = scielo.plan({"lexicon": LEXICON}, get=get)
    assert seen == list(scielo.COLLECTIONS)
    mex = [s for s in specs if s["query_id"].startswith("H-scielo-mex-")]
    assert [s["set"] for s in mex] == ["0301-7036", "2222-2222"]
    assert mex[0]["endpoint"] == scielo.COLLECTIONS["mex"]
    assert "set=0301-7036 (Problemas del desarrollo)" in mex[0]["query_string"]
    assert "local lexicon of languages es, pt, en" in mex[0]["query_string"]


def test_scielo_fetch_matches_locally_and_drops_deleted():
    spec = {"endpoint": "http://x/oai", "set": "0301-7036",
            "terms": ["financiamiento climático", "REDD"]}
    get, calls = recorder([resp(SCIELO_OAI)])
    events = list(scielo.fetch(spec, 1.0, get=get))
    assert events[0] == ("meta", 3) and events[-1] == ("end", "")
    recs = [v for k, v in events if k == "work"]
    assert len(recs) == 2
    assert recs[0]["matched_terms"] == "financiamiento climático"
    assert recs[0]["doi"] == "10.22201/iiec.20078951e.2019.196.1"
    assert recs[1]["matched_terms"] == ""
    assert calls[0][1]["set"] == "0301-7036"


def test_redalyc_empty_page_before_total_is_incomplete():
    spec = redalyc.plan({"lexicon": LEXICON})[0]
    get, _ = recorder([resp({"totalResultados": "5", "resultados": [redalyc_art("1", "A")]}),
                       resp({"totalResultados": "5", "resultados": []})])
    assert list(redalyc.fetch(spec, 0, get=get))[-1] == ("end", "short: 1 of 5")


# ---------------------------------------------------------------------------
# Review fixes (#1624): answers that must never read as complete
# ---------------------------------------------------------------------------

def test_redalyc_missing_count_is_an_error_not_an_empty_complete_answer():
    spec = redalyc.plan({"lexicon": LEXICON})[0]
    get, _ = recorder([resp({"error": "service down"})])
    assert list(redalyc.fetch(spec, 0, get=get)) == [("end", "error: no result count")]
    get, _ = recorder([resp({"totalResultados": "0", "resultados": []})])
    assert list(redalyc.fetch(spec, 0, get=get)) == [("meta", 0), ("end", "")]


def test_redalyc_non_string_fields_and_articles_without_id():
    spec = redalyc.plan({"lexicon": LEXICON})[0]
    arts = [redalyc_art(7, "A", year=2019), redalyc_art("", "No id")]
    get, _ = recorder([resp({"totalResultados": 2, "resultados": arts})])
    events = list(redalyc.fetch(spec, 0, get=get))
    [rec] = [v for k, v in events if k == "work"]
    assert rec["record_id"] == "redalyc:7" and rec["year"] == 2019
    assert events[-1] == ("end", "1 articles without cveArticulo")


def test_dspace_page_without_counts_or_items_without_metadata_are_incomplete():
    spec = latam_dspace.lexicon_plan(clacso.SOURCE, LEXICON)[0]
    no_counts = {"_embedded": {"searchResult": {"_embedded": {"objects": []}}}}
    get, _ = recorder([resp(no_counts)])
    assert list(latam_dspace.search("https://h", spec, 0, get=get)) == [
        ("end", "error: no page counts")]
    page = dspace_page([dspace_item("1", "A"), {"_embedded": {}}], 0, 1, 2)
    get, _ = recorder([resp(page)])
    events = list(latam_dspace.search("https://h", spec, 0, get=get))
    assert len([e for e in events if e[0] == "work"]) == 1
    assert events[-1] == ("end", "1 results without item metadata")


def test_dspace_unparseable_issue_date_still_falls_back_to_dc_date():
    md = {"dc.title": [{"value": "T"}], "dc.date.issued": [{"value": "s.f."}],
          "dc.date": [{"value": "2012"}]}
    assert latam_dspace.item_to_record({"metadata": md}, "https://h")["year"] == 2012


def test_scielo_one_failing_collection_is_one_incomplete_row():
    def get(url, params=None, delay=0):
        if params["collection"] == "ven":
            raise ConnectionError("down")
        return types.SimpleNamespace(
            status_code=200, raise_for_status=lambda: None,
            json=lambda: [am_journal("0301-7036", "P", area="Applied Social Sciences")])
    specs = scielo.plan({"lexicon": LEXICON}, get=get)
    [bad] = [s for s in specs if s["query_id"] == "H-scielo-ven-journals"]
    assert list(scielo.fetch(bad, 0)) == [("end", "error: journal list: ConnectionError")]
    assert len(specs) == len(scielo.COLLECTIONS)  # one row per collection either way
