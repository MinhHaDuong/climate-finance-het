"""South Centre Research Papers, read from the category RSS feed.

The WordPress REST API is closed (``/wp-json/wp/v2/posts`` and
``/categories``: HTTP 401 ``itsec_rest_api_access_restricted``, 2026-09-30);
only ``/wp-json/wp/v2/search`` answers, and it returns titles without dates or
abstracts. The category feed ``/category/research-papers/feed/`` pages with
``?paged=N`` and carries the real title (``description``; the item title is
only "Research Paper 226, 12 November 2025"), tags and full body, so the whole
series is read there and matched locally. RePEc lists no South Centre series.
robots.txt asks ``Crawl-delay: 10``: requests are spaced 10 s at least.
Papers are published in English with French, Spanish and Portuguese
translations, so the Portuguese lexicon is matched too.
"""

import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from pipeline_io import polite_get

from rel_sud_sources._common import empty_record, find_year, xml_clean
from rel_sud_sources._listing import emit, html_text, listing_query, matcher, soft

FEED = "https://www.southcentre.int/category/research-papers/feed/"
LANGUAGES = ["en", "fr", "es", "pt"]
CRAWL_DELAY = 10.0
MAX_PAGES = 200  # a runaway guard: the series has about 30 feed pages
NS_CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"
NS_DC = "{http://purl.org/dc/elements/1.1/}creator"

SOURCE = {
    "name": "south_centre",
    "region": "Global South (intergovernmental, Geneva)",
    "languages": LANGUAGES,
    "route": "listing",
    "endpoint": FEED,
    "terms": "https://www.southcentre.int/robots.txt",
}


def plan(cfg):
    return [{"query_id": "S-south_centre-rp",
             "query_string": listing_query(f"GET {FEED}?paged=1..N (RSS 2.0)", LANGUAGES,
                                           "matched on title, subtitle, tags and body"),
             "match": matcher(cfg, LANGUAGES)}]


def parse_feed(content):
    """``[item dict]`` of one RSS page."""
    channel = ET.fromstring(xml_clean(content)).find("channel")
    return [] if channel is None else channel.findall("item")


# The item title names the series in the language of the version.
LABEL_LANGUAGE = [("Research Paper", "en"), ("Document de recherche", "fr"),
                  ("Documento de investigación", "es"), ("Artigo de investigação", "pt")]


def label_language(label):
    low = label.casefold()
    return next((lang for prefix, lang in LABEL_LANGUAGE
                 if low.startswith(prefix.casefold())), "")


def to_record(item, match):
    label = (item.findtext("title") or "").strip()
    # some descriptions open with the theme's "Read more" link text
    subtitle = re.sub(r"^Read more\s*", "", html_text(item.findtext("description") or ""))
    body = html_text(item.findtext(NS_CONTENT) or "")
    tags = [c.text.strip() for c in item.findall("category") if c.text]
    title = f"{subtitle} [{label}]" if subtitle else label
    try:
        posted = str(parsedate_to_datetime(item.findtext("pubDate") or "").year)
    except (TypeError, ValueError):
        posted = ""
    return empty_record(
        record_id=(item.findtext("guid") or item.findtext("link") or "").strip(),
        url=(item.findtext("link") or "").strip(), title=title,
        authors="; ".join(c.text.strip() for c in item.findall(NS_DC) if c.text),
        year=find_year([label, posted]), language=label_language(label),
        venue="South Centre Research Paper",
        doc_type="research paper", abstract=body[:3000],
        matched_terms="; ".join(match(" ".join([title, " ".join(tags), body]))))


def fetch(spec, delay, get=polite_get):
    get = soft(get)
    delay = max(delay, CRAWL_DELAY)
    items, seen, error = [], set(), ""
    for page in range(1, MAX_PAGES + 1):
        try:
            resp = get(FEED, params={"paged": page}, delay=delay)
        except Exception as exc:  # network failure after retries
            error = f"error: {type(exc).__name__} on page {page}"
            break
        if resp.status_code == 404 and page > 1:
            break  # past the last page
        if resp.status_code != 200:
            error = f"http {resp.status_code} on page {page}"
            break
        try:
            batch = parse_feed(resp.content)
        except ET.ParseError:
            error = f"error: bad xml on page {page}"
            break
        if not batch:
            break
        new = [it for it in batch if (it.findtext("guid") or it.findtext("link")) not in seen]
        if not new:
            break  # a cache serving an earlier page again: nothing more to read
        seen.update(it.findtext("guid") or it.findtext("link") for it in new)
        items.extend(new)
    else:
        error = "page guard reached"
    yield from emit((to_record(it, spec["match"]) for it in items), len(items), error)
