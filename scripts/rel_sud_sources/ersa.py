"""ERSA Working Papers (Economic Research Southern Africa), WordPress REST.

ERSA is not a RePEc archive (IDEAS ``/s/rza/wpaper`` 404), and its site offers
no search API beyond WordPress's own. The series (``publication-types`` =
working-paper, about 1000 items) is small, so the whole listing is read from
``/wp-json/wp/v2/publications`` and matched locally on title + abstract.
robots.txt (checked 2026-09-30) disallows only ``/wp-admin/``.
"""

from pipeline_io import polite_get

from rel_sud_sources.common import empty_record, find_year
from rel_sud_sources.listing import emit, html_text, listing_query, matcher, wp_listing

BASE = "https://econrsa.org/wp-json/wp/v2"
WORKING_PAPER = 7139  # publication-types term id, slug 'working-paper'
LANGUAGES = ["en"]

SOURCE = {
    "name": "ersa",
    "region": "Southern Africa",
    "languages": LANGUAGES,
    "route": "export",
    "endpoint": f"{BASE}/publications?publication-types={WORKING_PAPER}",
    "terms": "https://econrsa.org/robots.txt",
}

FIELDS = "id,date,link,title,content,author-name"


def plan(cfg):
    return [{"query_id": "S-ersa-wp",
             "query_string": listing_query(
                 f"GET {SOURCE['endpoint']}&_fields={FIELDS} (all pages)", LANGUAGES),
             "match": matcher(cfg, LANGUAGES)}]


def to_record(item, match, authors):
    title = html_text(item["title"]["rendered"])
    abstract = html_text(item["content"]["rendered"])[:3000]
    names = [authors[i] for i in item.get("author-name", []) if i in authors]
    return empty_record(
        record_id=f"ersa:{item['id']}", url=item["link"], title=title,
        authors="; ".join(names), year=find_year([item.get("date", "")]),
        language="en", venue="ERSA Working Paper", doc_type="working paper",
        abstract=abstract, matched_terms="; ".join(match(title + " " + abstract)))


def author_names(ids, delay, get):
    """``{term id: name}`` for the author-name terms, 100 ids per request."""
    ids, out = sorted(ids), {}
    for i in range(0, len(ids), 100):
        try:
            resp = get(f"{BASE}/author-name", delay=delay,
                       params={"include": ",".join(map(str, ids[i:i + 100])),
                               "per_page": 100, "_fields": "id,name"})
        except Exception:  # names are a convenience, never a stop reason
            continue
        if resp.status_code == 200:
            out.update({t["id"]: html_text(t["name"]) for t in resp.json()})
    return out


def fetch(spec, delay, get=polite_get):
    items, error = wp_listing(get, f"{BASE}/publications",
                              {"publication-types": WORKING_PAPER, "_fields": FIELDS},
                              delay)
    match = spec["match"]
    recs = [to_record(it, match, {}) for it in items]
    ids = {a for it, r in zip(items, recs) if r["matched_terms"]
           for a in it.get("author-name", [])}
    names = author_names(ids, delay, get) if ids else {}
    recs = [to_record(it, match, names) if r["matched_terms"] else r
            for it, r in zip(items, recs)]
    yield from emit(recs, len(items), error)
