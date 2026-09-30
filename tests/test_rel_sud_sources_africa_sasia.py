"""REL south sources, Africa / South Asia lane (ticket 1653): canned responses only.

Each adapter must report the listing size, yield only lexicon matches (the
runner keeps every record of a non-OAI route), and end incomplete whenever a
page was lost.
"""

import json

import catalog_rel_sud_sources as runner
import pytest
from rel_sud_sources import adb_ewp, ajol, ceew, cpd, ersa, listing, south_centre

pytestmark = pytest.mark.domain_corpus

T = '"climate finance" OR "loss and damage"'
LEXICON = {
    "en": {"T1": T},
    "fr": {"T1": '"finance climat"'},
    "es": {"T1": '"financiamiento climático"'},
    "pt": {"T1": '"financiamento climático"'},
    "ar": {"T1": '"تمويل المناخ"'},
    "hi": {"T1": '"जलवायु वित्त"'},
    "bn": {"T1": '"জলবায়ু অর্থায়ন"'},
}
CFG = {"lexicon": LEXICON}


class Resp:
    def __init__(self, body="", status=200, headers=None):
        self.status_code = status
        self.text = body if isinstance(body, str) else json.dumps(body)
        self.content = self.text.encode("utf-8")
        self.headers = headers or {}

    def json(self):
        return json.loads(self.text)


class FakeGet:
    """Serves ``routes[(url, frozenset(params))]`` or ``routes[url]``; logs calls."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, url, params=None, delay=0):
        self.calls.append((url, dict(params or {}), delay))
        key = (url, tuple(sorted((params or {}).items())))
        if key in self.routes:
            return self.routes[key]
        if url in self.routes:
            return self.routes[url]
        return Resp("", 404)


def events(mod, get, spec=None):
    spec = spec or mod.plan(CFG)[0]
    return list(mod.fetch(spec, 0, get=get))


def works(evs):
    return [v for k, v in evs if k == "work"]


# ---------------------------------------------------------------------------
# WordPress REST listings: ERSA, CPD
# ---------------------------------------------------------------------------

def wp_item(i, title, body, **kw):
    return {"id": i, "date": "2019-03-01T00:00:00", "link": f"https://x/{i}",
            "title": {"rendered": title}, "content": {"rendered": body}, **kw}


def test_wp_listing_follows_pages_and_reports_a_lost_page():
    url = "https://x/wp-json/wp/v2/things"
    ok = FakeGet({
        (url, (("page", 1), ("per_page", 100))): Resp([{"id": 1}], headers={"X-WP-TotalPages": "2"}),
        (url, (("page", 2), ("per_page", 100))): Resp([{"id": 2}], headers={"X-WP-TotalPages": "2"}),
    })
    assert listing.wp_listing(ok, url, {}, 0) == ([{"id": 1}, {"id": 2}], "")
    broken = FakeGet({
        (url, (("page", 1), ("per_page", 100))): Resp([{"id": 1}], headers={"X-WP-TotalPages": "2"}),
        (url, (("page", 2), ("per_page", 100))): Resp("", 500),
    })
    assert listing.wp_listing(broken, url, {}, 0) == ([{"id": 1}], "http 500 on page 2")


def test_ersa_yields_matches_only_with_listing_size_and_author_names():
    page = [wp_item(1, "Climate finance in South Africa", "<p><strong>Working Paper 9</strong></p>"
                    "<p>Abstract.</p>", **{"author-name": [7]}),
            wp_item(2, "Tax incidence", "<p>Nothing relevant.</p>", **{"author-name": [8]})]
    get = FakeGet({f"{ersa.BASE}/publications": Resp(page, headers={"X-WP-TotalPages": "1"}),
                   f"{ersa.BASE}/author-name": Resp([{"id": 7, "name": "Doe, J."}])})
    evs = events(ersa, get)
    assert evs[0] == ("meta", 2) and evs[-1] == ("end", "")
    [rec] = works(evs)
    assert rec["matched_terms"] == "climate finance"
    assert rec["authors"] == "Doe, J." and rec["year"] == 2019
    assert "Working Paper 9" in rec["abstract"]
    # only the matched record's authors are resolved
    assert get.calls[-1][1]["include"] == "7"


def test_cpd_takes_publication_year_and_matches_bengali():
    page = [wp_item(5, "জলবায়ু অর্থায়ন ও বাংলাদেশ", "<p>...</p>",
                    excerpt={"rendered": ""}, publication_year=[31], publication_type=[40]),
            wp_item(6, "Trade note", "<p>tariffs</p>", excerpt={"rendered": "<p>x</p>"})]
    one = {"X-WP-TotalPages": "1"}
    get = FakeGet({cpd.SOURCE["endpoint"]: Resp(page, headers=one),
                   f"{cpd.BASE}/publication_year": Resp([{"id": 31, "name": "2011"}], headers=one),
                   f"{cpd.BASE}/publication_type": Resp([{"id": 40, "name": "Working Paper"}],
                                                        headers=one)})
    evs = events(cpd, get)
    assert evs[0] == ("meta", 2)
    [rec] = works(evs)
    assert rec["year"] == 2011 and rec["language"] == "bn"
    assert rec["doc_type"] == "Working Paper" and rec["matched_terms"] == "জলবায়ু অর্থায়ন"


# ---------------------------------------------------------------------------
# South Centre RSS
# ---------------------------------------------------------------------------

def rss(items):
    body = "".join(
        f"<item><title>{label}</title><link>https://sc/{i}</link><guid>sc:{i}</guid>"
        f"<pubDate>Tue, 14 Jul 2026 16:18:04 +0000</pubDate><category>Climate Change</category>"
        f"<description>{sub}</description>"
        f"<content:encoded><![CDATA[<p>{body}</p>]]></content:encoded></item>"
        for i, (label, sub, body) in enumerate(items))
    return ('<?xml version="1.0"?><rss version="2.0" '
            'xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>'
            f"{body}</channel></rss>")


def test_south_centre_reads_every_feed_page_at_crawl_delay():
    p1 = rss([("Research Paper 180, 12 May 2023", "Loss and damage finance", "abstract"),
              ("Research Paper 181, 1 June 2023", "Patents", "TRIPS")])
    p2 = rss([("Documento de Investigación 180, 12 de mayo de 2023",
               "Read moreFinanciamiento climático y pérdidas", "resumen")])
    feed = south_centre.FEED
    get = FakeGet({(feed, (("paged", 1),)): Resp(p1), (feed, (("paged", 2),)): Resp(p2)})
    evs = events(south_centre, get)
    assert evs[0] == ("meta", 3) and evs[-1] == ("end", "")
    recs = works(evs)
    assert [r["language"] for r in recs] == ["en", "es"]
    assert recs[0]["title"] == "Loss and damage finance [Research Paper 180, 12 May 2023]"
    assert recs[0]["year"] == 2023  # from the label, not the 2026 post date
    assert recs[1]["title"].startswith("Financiamiento climático")
    assert all(d >= south_centre.CRAWL_DELAY for _, _, d in get.calls)


def test_a_raised_404_past_the_last_page_ends_a_listing_complete():
    """polite_get raises HTTPError on 4xx; the listing must still see the 404."""
    import requests

    feed = south_centre.FEED
    inner = FakeGet({(feed, (("paged", 1),)): Resp(rss([("Research Paper 1", "Climate finance", "")]))})

    def raising(url, params=None, delay=0):
        resp = inner(url, params, delay)
        if resp.status_code >= 400:
            raise requests.HTTPError(response=resp)
        return resp

    evs = list(south_centre.fetch(south_centre.plan(CFG)[0], 0, get=raising))
    assert evs[0] == ("meta", 1) and evs[-1] == ("end", "")


def test_south_centre_first_page_error_is_incomplete():
    get = FakeGet({(south_centre.FEED, (("paged", 1),)): Resp("", 503)})
    assert events(south_centre, get)[-1] == ("end", "http 503 on page 1")


# ---------------------------------------------------------------------------
# ADB Economics Working Papers via IDEAS
# ---------------------------------------------------------------------------

IDEAS_LIST = """<ul>
<LI class="list-group-item downfree">  <B>861 <A HREF="/p/ris/adbewp/0001.html">Climate Finance &amp; Asia</A></B><BR><I>by</I> A. One & B. Two
<LI class="list-group-item downfree">  <B>860 <A HREF="/p/ris/adbewp/0002.html">Trade costs</A></B><BR><I>by</I> C. Three
</ul><A HREF="/p/ris/adbewp/0232.html">By citations</A>"""

IDEAS_PAPER = """<META NAME="handle" CONTENT="RePEc:ris:adbewp:0002">
<META NAME="citation_title" content="Trade costs">
<META NAME="citation_abstract" content="We study loss and damage in ports.">
<META NAME="citation_publication_date" content="2021/05/01">"""


def test_adb_parses_listing_and_matches_on_the_abstract():
    get = FakeGet({f"{adb_ewp.SERIES}.html": Resp(IDEAS_LIST),
                   f"{adb_ewp.IDEAS}/p/ris/adbewp/0002.html": Resp(IDEAS_PAPER)})
    evs = events(adb_ewp, get)
    assert evs[0] == ("meta", 2)
    recs = works(evs)
    # 0001's page is missing: matched on its listing title, and the run says so
    assert [r["record_id"] for r in recs] == ["RePEc:ris:adbewp:0001", "RePEc:ris:adbewp:0002"]
    assert recs[0]["authors"] == "A. One; B. Two"
    assert recs[1]["year"] == 2021 and recs[1]["matched_terms"] == "loss and damage"
    assert evs[-1] == ("end", "1 paper pages failed (matched on title only)")


# ---------------------------------------------------------------------------
# CEEW sitemap
# ---------------------------------------------------------------------------

SITEMAP = """<urlset>
<url><loc>https://www.ceew.in/publications/myth-private-finance</loc></url>
<url><loc>https://www.ceew.in/hindi-publications/niji-vitt</loc></url>
<url><loc>https://www.ceew.in/gfc/publications/brief</loc></url>
<url><loc>https://www.ceew.in/publications</loc></url>
<url><loc>https://www.ceew.in/blogs/climate-finance-post</loc></url>
</urlset>"""

CEEW_PAGE = """<html><head><meta property="og:title" content="The Myth of Climate Finance" />
<meta property="article:published_time" content="2024-01-02T00:00:00+05:30" />
<script>var x = "Overview";</script></head><body>
<h1>The Myth of Climate Finance</h1> Manon Fortemps May 2023 | Sustainable Finance
Overview This paper examines private capital. Key Highlights Many.</body></html>"""


def test_ceew_lists_publication_pages_only():
    assert ceew.publication_urls(SITEMAP) == [
        "https://www.ceew.in/publications/myth-private-finance",
        "https://www.ceew.in/hindi-publications/niji-vitt",
        "https://www.ceew.in/gfc/publications/brief",
    ]


def test_ceew_reads_title_overview_and_display_year():
    hindi = CEEW_PAGE.replace("The Myth of Climate Finance", "जलवायु वित्त के मिथक")
    get = FakeGet({ceew.SITEMAP: Resp(SITEMAP),
                   "https://www.ceew.in/publications/myth-private-finance": Resp(CEEW_PAGE),
                   "https://www.ceew.in/hindi-publications/niji-vitt": Resp(hindi)})
    evs = events(ceew, get)
    assert evs[0] == ("meta", 3)
    en, hi = works(evs)
    assert en["abstract"] == "This paper examines private capital."
    assert en["year"] == 2023  # the display date, not the upload timestamp
    assert hi["language"] == "hi" and hi["matched_terms"] == "जलवायु वित्त"
    assert evs[-1] == ("end", "1 of 3 pages failed")


# ---------------------------------------------------------------------------
# AJOL per-journal OAI-PMH
# ---------------------------------------------------------------------------

def category_page(paths, n_pages):
    links = "".join(f'<a href="https://www.ajol.info/index.php/{p}" class="journalMenu">View</a>'
                    f'<a href="https://www.ajol.info/index.php/{p}/issue/current" '
                    f'class="journalMenu">Current</a>' for p in paths)
    return f"{links} of {n_pages} pages"


def test_ajol_plan_lists_every_category_page_once_per_journal(monkeypatch):
    monkeypatch.setattr(ajol, "CATEGORIES", ["economics-and-development", "earth-sciences"])
    url = f"{ajol.SITE}/ajol/browseBy/category"
    get = FakeGet({
        (url, (("category", "economics-and-development"), ("journalsPage", 1))):
            Resp(category_page(["eje", "ajer"], 2)),
        (url, (("category", "economics-and-development"), ("journalsPage", 2))):
            Resp(category_page(["gje"], 2)),
        (url, (("category", "earth-sciences"), ("journalsPage", 1))):
            Resp(category_page(["eje"], 1)),
    })
    specs = ajol.plan(CFG, get=get)
    # category priority order, each journal once
    assert [s["query_id"] for s in specs] == ["S-ajol-eje", "S-ajol-ajer", "S-ajol-gje"]
    eje = specs[0]
    assert eje["endpoint"] == f"{ajol.SITE}/eje/oai"
    assert "economics-and-development, earth-sciences" in eje["query_string"]


def test_ajol_plan_refuses_a_partial_journal_list(monkeypatch):
    monkeypatch.setattr(ajol, "CATEGORIES", ["earth-sciences"])
    with pytest.raises(RuntimeError, match="incomplete"):
        ajol.plan(CFG, get=FakeGet({}))


OAI = """<?xml version="1.0"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><ListRecords>
<record><header><identifier>oai:ajol.info:article/1</identifier></header><metadata>
<oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
 xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>Climate finance in Ghana</dc:title><dc:date>2015-01-01</dc:date>
</oai_dc:dc></metadata></record>
<record><header><identifier>oai:ajol.info:article/2</identifier></header><metadata>
<oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
 xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>Climate finance, a 1985 view</dc:title><dc:date>1985</dc:date>
</oai_dc:dc></metadata></record>
<record><header status="deleted"><identifier>oai:ajol.info:article/3</identifier></header></record>
<resumptionToken completeListSize="3"></resumptionToken>
</ListRecords></OAI-PMH>"""


def test_ajol_fetch_keeps_the_window_and_the_runner_keeps_matches(monkeypatch):
    monkeypatch.setattr(ajol, "_state", {"challenged_in_a_row": 0})
    spec = {"query_id": "S-ajol-eje", "endpoint": "https://oai", "query_string": "q",
            "match": listing.matcher(CFG, ajol.LANGUAGES)}
    evs = events(ajol, FakeGet({"https://oai": Resp(OAI)}), spec)
    assert evs[0] == ("meta", 3) and evs[-1] == ("end", "")
    recs = works(evs)
    assert [r["matched_terms"] for r in recs] == ["climate finance", ""]  # 1985 out of window
    assert all(runner.keep(ajol.SOURCE["route"], r) == bool(r["matched_terms"]) for r in recs)


def test_ajol_waits_out_a_waf_challenge_then_skips_once_it_persists(monkeypatch):
    monkeypatch.setattr(ajol, "_state", {"challenged_in_a_row": 0})
    waf = Resp("", 202, {"x-amzn-waf-action": "challenge"})
    spec = {"endpoint": "https://oai", "match": listing.matcher(CFG, ajol.LANGUAGES)}
    pauses = []

    class Flaky(FakeGet):  # challenged once, then served
        def __call__(self, url, params=None, delay=0):
            super().__call__(url, params, delay)
            return waf if len(self.calls) == 1 else Resp(OAI)

    evs = list(ajol.fetch(spec, 0, get=Flaky({}), sleep=pauses.append))
    assert pauses == [120] and evs[-1] == ("end", "")
    blocked = FakeGet({"https://oai": waf})
    for _ in range(ajol.MAX_CHALLENGED):
        evs = list(ajol.fetch(spec, 0, get=blocked, sleep=pauses.append))
        assert evs[-1] == ("end", "http 202 (WAF challenge)")
    n = len(blocked.calls)
    evs = list(ajol.fetch(spec, 0, get=blocked, sleep=pauses.append))
    assert evs == [("end", "skipped: WAF challenge persisted on previous journals")]
    assert len(blocked.calls) == n  # no request once the challenge persists


def test_oai_requests_carry_no_mailto_argument(monkeypatch):
    """OJS answers badArgument to the mailto parameter polite_get appends."""
    import openalex_corpus.crawl as crawl

    sent = []

    def fake_requests_get(url, params=None, headers=None, timeout=None):
        sent.append((dict(params or {}), headers))
        return Resp(OAI)

    monkeypatch.setattr(crawl.requests, "get", fake_requests_get)
    listing.no_mailto_get("https://oai", params={"verb": "ListRecords"}, delay=0)
    assert sent[0][0] == {"verb": "ListRecords"}
    assert "mailto:" in sent[0][1]["User-Agent"]
    assert ajol.fetch.__defaults__[0] is listing.no_mailto_get


def test_ajol_survives_a_character_xml_forbids(monkeypatch):
    monkeypatch.setattr(ajol, "_state", {"challenged_in_a_row": 0})
    dirty = OAI.replace("Climate finance in Ghana", "Climate finance in Ghana\ufffe")
    spec = {"endpoint": "https://oai", "match": listing.matcher(CFG, ajol.LANGUAGES)}
    evs = events(ajol, FakeGet({"https://oai": Resp(dirty)}), spec)
    assert evs[-1] == ("end", "")
    assert works(evs)[0]["title"] == "Climate finance in Ghana"


def test_every_adapter_honours_the_contract():
    for mod in (ajol, adb_ewp, ceew, cpd, ersa, south_centre):
        src = mod.SOURCE
        assert src["route"] in {"api", "oai-pmh", "export"}
        assert set(src["languages"]) <= set(LEXICON)
        assert src["name"] in runner.discover()
    assert "listing" not in runner.discover()
