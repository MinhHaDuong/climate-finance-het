"""REL south sources, lane China-Russia-Southeast Asia-Pacific (ticket 1653).

Canned responses only, no network: GARUDA's HTML search pages and CyberLeninka's
OAI-PMH pages.
"""

import types

import pytest
from rel_sud_sources import common, cyberleninka, garuda

pytestmark = pytest.mark.domain_corpus

LEXICON = {
    "id": {"T1": '"pendanaan iklim" OR "Green Climate Fund"', "T2": '"pasar karbon"',
           "T3": '"REDD"', "T4": '"keadilan iklim"'},
    "en": {"T1": '"climate finance"', "T2": '"carbon market"', "T3": '"REDD"',
           "T4": '"loss and damage"'},
    "ru": {"T1": '"климатическое финансирование"', "T2": '"углеродный рынок"',
           "T3": '"REDD"', "T4": '"климатический долг"'},
}


def _item(num, title, venue, abstract="", doi=""):
    doi_link = (f'| <a class="title-citation" target="_blank" href="https://doi.org/{doi}">'
                f"DOI: {doi}</a>") if doi else ""
    return f"""
<div class="article-item">
  <a class="title-article" href="/documents/detail/{num}">
    <xmp>{title} </xmp>
  </a>
  <a class="author-article" href="/author/view/1"><xmp>Nurfatriani, Fitri</xmp></a>;
  <a class="author-article" href="/author/view/2"><xmp>Salminah, Mimi</xmp></a><br>
  <xmp class="subtitle-article"> {venue} </xmp><br>
  <i class="subtitle-article">Publisher : </i><xmp class="subtitle-article">UGM </xmp>
  <p class="action-article">
    | <i><a class="title-citation" href="https://jurnal.example/{num}" target="_blank">
        Original Source</a></i>
    {doi_link}
  </p>
  <div class="abstract-article"><xmp class="abstract-article">{abstract}</xmp></div>
</div>
<div class="ui divider"></div>"""


def _page(found, items):
    return ("<html><body><h2>Found " + str(found) + " documents</h2>"
            + "".join(items) + "</body></html>").encode()


def fake_get(pages, calls=None):
    it = iter(pages)

    def get(url, params=None, delay=0):
        if calls is not None:
            calls.append(dict(params or {}))
        body = next(it)
        if isinstance(body, int):
            return types.SimpleNamespace(status_code=body, content=b"")
        return types.SimpleNamespace(status_code=200, content=body)
    return get


# ---------------------------------------------------------------- GARUDA


def test_garuda_plan_is_one_query_per_phrase_and_field():
    specs = garuda.plan({"lexicon": LEXICON})
    # id: 5 phrases, en: 4 phrases; two fields each
    assert len(specs) == (5 + 4) * 2
    ids = [s["query_id"] for s in specs]
    assert len(set(ids)) == len(ids)
    first = specs[0]
    assert first["query_id"] == "S-garuda-id-T1-01-title"
    assert first["params"] == {"select": "title", "q": "pendanaan iklim",
                               "from": 1990, "to": 2026}
    assert first["query_string"].startswith("select=title&q=pendanaan iklim&from=1990&to=2026")
    assert "ru" not in {s["query_id"].split("-")[2] for s in specs}


def test_garuda_parse_page_extracts_fields_and_local_matches():
    match = common.term_matcher(["pendanaan iklim", "REDD"])
    html = _page(2, [
        _item(3461444, "Opsi Skema Pendanaan Iklim di Sektor Kehutanan",
              "Jurnal Ilmu Kehutanan Vol 13, No 1 (2019)",
              abstract="Skema REDD+ &amp; jasa lingkungan.", doi="10.22146/jik.46210"),
        _item(3912393, "Pengaruh pajak karbon", "Jurnal Ekonomi Vol. 23, No. 2, 2022"),
    ]).decode()
    n, recs = garuda.parse_page(html, match)
    assert n == 2 and len(recs) == 2
    r = recs[0]
    assert r["record_id"] == "garuda:3461444"
    assert r["title"] == "Opsi Skema Pendanaan Iklim di Sektor Kehutanan"
    assert r["authors"] == "Nurfatriani, Fitri; Salminah, Mimi"
    assert r["year"] == 2019
    assert r["doi"] == "10.22146/jik.46210"
    assert r["url"] == "https://jurnal.example/3461444"
    assert r["abstract"] == "Skema REDD+ & jasa lingkungan."
    assert r["venue"].startswith("Jurnal Ilmu Kehutanan") and "UGM" in r["venue"]
    assert r["matched_terms"] == "REDD; pendanaan iklim"
    # year without parentheses still read; no lexicon phrase -> empty match
    assert recs[1]["year"] == 2022 and recs[1]["matched_terms"] == ""
    assert recs[1]["doi"] == ""


def test_garuda_fetch_pages_until_count_and_reports_completion(monkeypatch):
    calls = []
    p1 = _page(3, [_item(1, "a", "V (2010)"), _item(2, "b", "V (2011)")])
    p2 = _page(3, [_item(3, "c", "V (2012)")])
    monkeypatch.setattr(garuda, "get", fake_get([p1, p2], calls))
    spec = garuda.plan({"lexicon": LEXICON})[0]
    events = list(garuda.fetch(spec, 0))
    assert events[0] == ("meta", 3)
    assert [v["record_id"] for k, v in events if k == "work"] == \
        ["garuda:1", "garuda:2", "garuda:3"]
    assert events[-1] == ("end", "")
    assert [c["page"] for c in calls] == [1, 2]
    assert calls[0]["select"] == "title" and calls[0]["from"] == 1990


def test_garuda_http_error_or_short_pages_are_incomplete(monkeypatch):
    spec = garuda.plan({"lexicon": LEXICON})[0]
    monkeypatch.setattr(garuda, "get", fake_get([503]))
    assert list(garuda.fetch(spec, 0)) == [("end", "http 503")]
    monkeypatch.setattr(garuda, "get", fake_get([_page(5, [_item(1, "a", "V")]), _page(5, [])]))
    assert list(garuda.fetch(spec, 0))[-1] == ("end", "empty page 2 before 5 records")
    monkeypatch.setattr(garuda, "get", fake_get([b"<html>maintenance</html>"]))
    assert list(garuda.fetch(spec, 0)) == [("end", "error: no result count on page 1")]


def test_garuda_detail_page_gives_the_publish_year():
    page = ('<h4 class="ui header">Article Info</h4>\n'
            "<p>Publish Date <br>01 Jul 2023</p></div><p>&copy; 2018</p>")
    assert garuda.publish_year(page) == 2023
    assert garuda.publish_year("<p>&copy; 2018</p>") is None
    assert garuda.detail_url("garuda:3912393") == (
        "https://garuda.kemdiktisaintek.go.id/documents/detail/3912393")


def test_garuda_zero_hits_is_complete(monkeypatch):
    spec = garuda.plan({"lexicon": LEXICON})[0]
    monkeypatch.setattr(garuda, "get", fake_get([_page(0, [])]))
    assert list(garuda.fetch(spec, 0)) == [("meta", 0), ("end", "")]


# ---------------------------------------------------------------- CyberLeninka

def _oai(titles, token):
    recs = "".join(f"""
<record><header><identifier>https://cyberleninka.ru/article/n/{i}</identifier>
<datestamp>2014-05-20T06:11:15Z</datestamp><setSpec>repec</setSpec></header>
<metadata><oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
 xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>{t}</dc:title><dc:creator>Иванов И. И.</dc:creator><dc:type>text</dc:type>
<dc:publisher>Издательство</dc:publisher>
<dc:identifier>https://cyberleninka.ru/article/n/{i}</dc:identifier>
</oai_dc:dc></metadata></record>""" for i, t in titles)
    tok = f'<resumptionToken cursor="10">{token}</resumptionToken>' if token else "<resumptionToken/>"
    return (f'<?xml version="1.0"?><OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">'
            f"<ListRecords>{recs}{tok}</ListRecords></OAI-PMH>").encode()


PAGES = [
    _oai([("a", "Климатическое финансирование в России"), ("b", "Рынок зерна")], "tok1"),
    _oai([("c", "Green bonds and climate finance")], ""),
]


LISTSETS = """<?xml version="1.0"?><OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
<ListSets>
<set><setSpec>repec</setSpec><setName>Research Papers in Economics</setName></set>
<set><setSpec>journal_1</setSpec><setName>Экология человека</setName></set>
<set><setSpec>journal_2</setSpec><setName>Клиническая офтальмология</setName></set>
<set><setSpec>journal_3</setSpec><setName>Экономическое развитие России</setName></set>
<set><setSpec>journal_4</setSpec><setName>Финансы и кредит</setName></set>
</ListSets></OAI-PMH>""".encode()

CAPTCHA = "<!DOCTYPE html><html><title>Вы точно человек?</title>captcha</html>".encode()


def _plan(monkeypatch, pages=(), calls=None, budget=None):
    monkeypatch.setattr(cyberleninka, "get", fake_get([LISTSETS, *pages], calls))
    cfg = {"lexicon": LEXICON}
    if budget is not None:
        cfg["cyberleninka_page_budget"] = budget
    return cyberleninka.plan(cfg)


def test_cyberleninka_plan_selects_journal_sets_by_tier(monkeypatch):
    specs = _plan(monkeypatch)
    # finance first (tier 1), economics (2), ecology (3); index sets and
    # unrelated journals left out
    assert [s["set"] for s in specs] == ["journal_4", "journal_3", "journal_1"]
    assert specs[0]["query_id"] == "S-cyberleninka-journal_4"
    qs = specs[0]["query_string"]
    assert "set=journal_4" in qs and "Финансы и кредит" in qs and "tier 1" in qs
    assert "ru, en" in qs and "titles only" in qs
    assert "климатическое финансирование" in specs[0]["terms"]
    assert "climate finance" in specs[0]["terms"]
    assert specs[0]["budget"] is specs[2]["budget"]  # one budget for the run


def test_cyberleninka_harvest_matches_titles_and_completes(monkeypatch):
    calls = []
    spec = _plan(monkeypatch, PAGES, calls)[0]
    events = list(cyberleninka.fetch(spec, 0))
    assert events[0] == ("meta", "")
    works = [v for k, v in events if k == "work"]
    assert [w["matched_terms"] for w in works] == \
        ["климатическое финансирование", "", "climate finance"]
    assert works[0]["url"] == "https://cyberleninka.ru/article/n/a"
    assert works[0]["year"] is None  # CyberLeninka oai_dc carries no date
    assert events[-1] == ("end", "")
    assert calls[1]["set"] == "journal_4" and calls[2] == {"verb": "ListRecords",
                                                           "resumptionToken": "tok1"}


def test_cyberleninka_shared_page_budget_leaves_queries_incomplete(monkeypatch):
    specs = _plan(monkeypatch, PAGES, budget=1)
    events = list(cyberleninka.fetch(specs[0], 0))
    assert len([e for e in events if e[0] == "work"]) == 2
    assert events[-1] == ("end", "page budget reached")
    # the next journal gets nothing and says so
    assert list(cyberleninka.fetch(specs[1], 0)) == [("end", "page budget reached")]


def test_cyberleninka_captcha_page_is_a_block_not_bad_xml(monkeypatch):
    spec = _plan(monkeypatch, [PAGES[0], CAPTCHA])[0]
    events = list(cyberleninka.fetch(spec, 0))
    assert len([e for e in events if e[0] == "work"]) == 2
    assert events[-1] == ("end", "blocked: captcha page (not solved)")


def test_cyberleninka_blocked_listsets_is_one_blocked_row(monkeypatch):
    monkeypatch.setattr(cyberleninka, "get", fake_get([CAPTCHA]))
    (spec,) = cyberleninka.plan({"lexicon": LEXICON})
    assert spec["query_id"] == "S-cyberleninka-listsets"
    assert list(cyberleninka.fetch(spec, 0)) == [("end", "blocked: captcha page (not solved)")]


def test_cyberleninka_strips_xml_invalid_control_characters(monkeypatch):
    bad = _oai([("a", "Климатическое\x0b финансирование")], "")  # raw 0x0B byte
    assert b"\x0b" in bad
    spec = _plan(monkeypatch, [bad])[0]
    events = list(cyberleninka.fetch(spec, 0))
    assert events[-1] == ("end", "")
    assert [v["title"] for k, v in events if k == "work"] == ["Климатическое финансирование"]
