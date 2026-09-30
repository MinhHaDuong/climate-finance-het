"""CEEW (Council on Energy, Environment and Water, India) publications.

CEEW offers no API or feed for its catalogue, and robots.txt (2026-09-30)
disallows its search (``/search/``) and paged listings (``/*/page/``,
``/*?page=``). It does publish ``/sitemap.xml``, which lists every
publication page (``/publications/...``, ``/hindi-publications/...`` and the
centre sub-sites). Each page is read for its title (``og:title``), date and
"Overview" paragraph, and matched locally. robots.txt asks ``Crawl-delay: 10``
and signals ``search=yes, ai-input=yes``: requests are spaced 10 s at least.
"""

import re

from pipeline_io import polite_get

from rel_sud_sources._common import empty_record, find_year
from rel_sud_sources._listing import html_text, listing_query, matcher, script_language

SITEMAP = "https://www.ceew.in/sitemap.xml"
LANGUAGES = ["en", "hi"]
CRAWL_DELAY = 10.0
# robots.txt disallows /cop26/publications/ and query strings on listings.
PUB_PATH = re.compile(
    r"^https://www\.ceew\.in/(?!cop26/)(?:[a-z0-9-]+/)?(?:hindi-)?publications/[^/?#]+$")
SITE_SUFFIX_RE = re.compile(r"\s*[|–-]\s*CEEW\s*$")

SOURCE = {
    "name": "ceew",
    "region": "South Asia (India)",
    "languages": LANGUAGES,
    "route": "listing",
    "endpoint": SITEMAP,
    "terms": "https://www.ceew.in/robots.txt",
}

LOC_RE = re.compile(r"<loc>([^<]+)</loc>")
META_RE = re.compile(r'<meta (?:property|name)="([^"]+)" content="([^"]*)"', re.I)
# The <head> goes too: its <title> repeats the page title, and a date searched
# after the first occurrence of the title then lands in the navigation menu and
# falls back to the upload timestamp (ticket 1790: "Negotiating around
# Trade-offs", December 2010, read as 2010 by 1653 and as 2021 by the first
# 1790 run: the menu differs between loads).
DROP_RE = re.compile(r"<(head|script|style|noscript)\b.*?</\1>", re.I | re.S)
MONTH_YEAR_RE = re.compile(r"\b(?:January|February|March|April|May|June|July|August|"
                           r"September|October|November|December) ((?:19|20)\d{2})\b")


def plan(cfg):
    return [{"query_id": "S-ceew-sitemap",
             "query_string": listing_query(
                 f"GET {SITEMAP}, then every publication page it lists "
                 "(/publications/, /hindi-publications/, /<centre>/publications/)",
                 LANGUAGES, "matched on title and Overview"),
             "match": matcher(cfg, LANGUAGES)}]


def publication_urls(sitemap_xml):
    urls = [u.strip() for u in LOC_RE.findall(sitemap_xml)]
    return list(dict.fromkeys(u for u in urls if PUB_PATH.match(u)))


def parse_page(text):
    """``(title, meta dict, plain text)`` of one publication page."""
    meta = {}
    for k, v in META_RE.findall(text):
        meta.setdefault(k.lower(), html_text(v))
    title = SITE_SUFFIX_RE.sub("", meta.get("og:title", ""))
    return title, meta, html_text(DROP_RE.sub(" ", text))


def overview(title, text):
    """The Overview paragraph, else the page text from the title heading on."""
    m = re.search(r"\bOverview\b(.*?)(?:\bKey Highlights\b|\bDownload\b|$)", text, re.S)
    if m and m.group(1).strip():
        return m.group(1).strip()[:3000]
    i = text.find(title) if title else -1
    return text[i:i + 3000] if i >= 0 else ""


def to_record(url, title, meta, text, match):
    abstract = overview(title, text)
    head = text[text.find(title):][:600] if title and title in text else ""
    year = MONTH_YEAR_RE.search(head)
    return empty_record(
        record_id=url, url=url, title=title,
        year=int(year.group(1)) if year else find_year([meta.get("article:published_time", "")]),
        language=script_language(title), venue="CEEW",
        doc_type="report", abstract=abstract,
        matched_terms="; ".join(match(title + " " + abstract)))


def fetch(spec, delay, get=polite_get):
    delay = max(delay, CRAWL_DELAY)
    try:
        resp = get(SITEMAP, delay=delay)
    except Exception as exc:  # network failure after retries
        yield ("end", f"error: {type(exc).__name__} on sitemap")
        return
    if resp.status_code != 200:
        yield ("end", f"http {resp.status_code} on sitemap")
        return
    urls = publication_urls(resp.text)
    if not urls:
        yield ("end", "error: no publication page in the sitemap")
        return
    yield ("meta", len(urls))
    failed = []
    for url in urls:
        rec = _read(url, get, delay, spec["match"])
        if rec is None:
            failed.append(url)
        else:
            yield ("work", rec)
    # One more pass over the failed pages: a transient error (a timeout, an
    # interstitial) cost 13 pages on 2026-09-30 (ticket 1790).
    lost = 0
    for url in failed:
        rec = _read(url, get, delay, spec["match"])
        if rec is None:
            lost += 1
        else:
            yield ("work", rec)
    yield ("end", f"{lost} of {len(urls)} pages failed" if lost else "")


def _read(url, get, delay, match):
    """The record of one publication page, or None when the page is lost."""
    try:
        page = get(url, delay=delay)
    except Exception:  # network failure after retries
        return None
    if page.status_code != 200:
        return None
    title, meta, text = parse_page(page.text)
    if not title:  # an interstitial or error page served with 200
        return None
    return to_record(url, title, meta, text, match)
