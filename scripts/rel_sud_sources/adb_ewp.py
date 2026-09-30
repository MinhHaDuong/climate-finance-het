"""ADB Economics Working Paper Series, through its RePEc listing on IDEAS.

adb.org answers every automated request, robots.txt included, with a
Cloudflare JavaScript challenge (HTTP 403 "Just a moment...", 2026-09-30), so
the publisher is out of reach without a browser. The series is RePEc
``ris:adbewp`` (about 870 papers): the IDEAS series pages list every paper,
and each paper page carries the abstract and date in ``citation_*`` meta tags.
IDEAS robots.txt disallows only ``/cgi-bin/`` and a few service paths.
"""

import html
import re

from pipeline_io import polite_get

from rel_sud_sources.common import empty_record, find_year
from rel_sud_sources.listing import listing_query, matcher, soft

IDEAS = "https://ideas.repec.org"
SERIES = f"{IDEAS}/s/ris/adbewp"
LANGUAGES = ["en"]
MAX_PAGES = 50  # runaway guard: the series fills 5 listing pages

SOURCE = {
    "name": "adb_ewp",
    "region": "Asia-Pacific (ADB)",
    "languages": LANGUAGES,
    "route": "listing",
    "endpoint": f"{SERIES}.html",
    "terms": "https://ideas.repec.org/robots.txt",
}

ITEM_RE = re.compile(
    r'<LI class="list-group-item[^"]*">\s*<B>\s*\d*\s*<A HREF="(/p/ris/adbewp/[^"]+)">'
    r"(.*?)</A></B>(?:<BR><I>by</I>([^<]*))?", re.I | re.S)
META_RE = re.compile(r'<META NAME="([a-z_]+)" CONTENT="([^"]*)"', re.I)


def plan(cfg):
    return [{"query_id": "S-adb_ewp-repec",
             "query_string": listing_query(
                 f"GET {SERIES}.html, {SERIES}2.html... then each paper page "
                 "(RePEc ris:adbewp on IDEAS)", LANGUAGES),
             "match": matcher(cfg, LANGUAGES)}]


def parse_listing(text):
    """``[(path, title, authors)]`` of one IDEAS series page."""
    return [(p, html.unescape(re.sub(r"<[^>]+>", "", t)).strip(),
             html.unescape(a or "").strip().replace(" & ", "; "))
            for p, t, a in ITEM_RE.findall(text)]


def parse_paper(text):
    """``{meta name: content}`` of one IDEAS paper page (first value wins)."""
    out = {}
    for k, v in META_RE.findall(text):
        out.setdefault(k.lower(), html.unescape(v))
    return out


def to_record(path, title, authors, meta, match):
    title = meta.get("citation_title") or title
    abstract = meta.get("citation_abstract", "")
    return empty_record(
        record_id=meta.get("handle") or "RePEc:ris:adbewp:" + path.rsplit("/", 1)[-1][:-5],
        url=IDEAS + path, title=title,
        authors=(meta.get("citation_authors") or authors),
        year=find_year([meta.get("citation_publication_date", ""), meta.get("date", "")]),
        language="en", venue="ADB Economics Working Paper Series",
        doc_type="working paper", abstract=abstract[:3000],
        matched_terms="; ".join(match(" ".join([title, abstract,
                                                meta.get("keywords", "")]))))


def listing(get, delay):
    items = []
    for page in range(1, MAX_PAGES + 1):
        url = f"{SERIES}.html" if page == 1 else f"{SERIES}{page}.html"
        try:
            resp = get(url, delay=delay)
        except Exception as exc:  # network failure after retries
            return items, f"error: {type(exc).__name__} on listing page {page}"
        if resp.status_code == 404 and page > 1:
            return items, ""
        if resp.status_code != 200:
            return items, f"http {resp.status_code} on listing page {page}"
        batch = parse_listing(resp.text)
        if not batch:
            return items, ""
        items.extend(batch)
    return items, "page guard reached"


def fetch(spec, delay, get=polite_get):
    get = soft(get)
    items, error = listing(get, delay)
    seen = set()
    items = [i for i in items if not (i[0] in seen or seen.add(i[0]))]
    yield ("meta", len(items))
    failed = 0
    for path, title, authors in items:
        meta = {}
        try:
            resp = get(IDEAS + path, delay=delay)
            if resp.status_code == 200:
                meta = parse_paper(resp.text)
            else:
                failed += 1
        except Exception:  # one paper page lost: matched on its title alone
            failed += 1
        yield ("work", to_record(path, title, authors, meta, spec["match"]))
    if failed and not error:
        error = f"{failed} paper pages failed (matched on title only)"
    yield ("end", error)
