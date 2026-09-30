"""CPD (Centre for Policy Dialogue, Bangladesh) publications, WordPress REST.

The catalogue is the ``publication`` post type (about 700 items: working
papers, policy briefs, research reports, books). WordPress search does no
Bengali phrase matching worth the name (``"জলবায়ু অর্থায়ন"``: 0 hits,
2026-09-30), so the whole catalogue is read and matched locally on title,
excerpt and body. News and op-eds (``posts``) are outside the catalogue.
robots.txt (checked 2026-09-30) disallows only the login path.
"""

from pipeline_io import polite_get

from rel_sud_sources.common import empty_record, find_year
from rel_sud_sources.listing import (
    emit,
    html_text,
    listing_query,
    matcher,
    script_language,
    wp_listing,
)

BASE = "https://cpd.org.bd/wp-json/wp/v2"
LANGUAGES = ["en", "bn"]

SOURCE = {
    "name": "cpd",
    "region": "South Asia (Bangladesh)",
    "languages": LANGUAGES,
    "route": "export",
    "endpoint": f"{BASE}/publication",
    "terms": "https://cpd.org.bd/robots.txt",
}

FIELDS = "id,date,link,title,excerpt,content,publication_type,publication_year"


def plan(cfg):
    return [{"query_id": "S-cpd-publications",
             "query_string": listing_query(
                 f"GET {SOURCE['endpoint']}?_fields={FIELDS} (all pages, all publication types)",
                 LANGUAGES),
             "match": matcher(cfg, LANGUAGES)}]


def to_record(item, match, terms):
    """Record of one publication; the year is the ``publication_year`` term
    when set (the post date is the upload date), else the post date."""
    title = html_text(item["title"]["rendered"])
    excerpt = html_text(item.get("excerpt", {}).get("rendered", ""))
    body = html_text(item.get("content", {}).get("rendered", ""))
    year = find_year([terms.get(t, "") for t in item.get("publication_year", [])]
                     + [item.get("date", "")])
    return empty_record(
        record_id=f"cpd:{item['id']}", url=item["link"], title=title, year=year,
        language=script_language(title + " " + excerpt),
        venue="Centre for Policy Dialogue",
        doc_type="; ".join(types_names(item, terms)),
        abstract=(body or excerpt)[:3000],
        matched_terms="; ".join(match(" ".join([title, excerpt, body]))))


def types_names(item, terms):
    return [terms[t] for t in item.get("publication_type", []) if t in terms]


def term_names(get, delay):
    """``{term id: name}`` over the two small taxonomies used in records."""
    out = {}
    for tax in ("publication_year", "publication_type"):
        items, _ = wp_listing(get, f"{BASE}/{tax}", {"_fields": "id,name"}, delay)
        out.update({t["id"]: html_text(t["name"]) for t in items})
    return out


def fetch(spec, delay, get=polite_get):
    items, error = wp_listing(get, SOURCE["endpoint"], {"_fields": FIELDS}, delay)
    terms = term_names(get, delay) if items else {}
    yield from emit((to_record(it, spec["match"], terms) for it in items),
                    len(items), error)
