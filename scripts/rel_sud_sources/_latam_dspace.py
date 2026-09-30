"""DSpace 7 REST search shared by the CLACSO, Ipea and UWI adapters (ticket 1653).

No ``SOURCE`` here: the runner skips this module. DSpace 7 exposes its Solr
discovery as ``/server/api/discover/search/objects``. robots.txt (checked
2026-09-30): Ipea and UWI disallow the ``/search`` user interface; CLACSO
disallows only authn, eperson and statistics under ``/server/api``; none
disallows ``/server/api/discover``.
The lexicon string (``"a" OR "b"``) is sent verbatim as ``query``: the
discovery index accepts quoted phrases and ``OR``. No server-side date filter:
``f.dateIssued`` silently drops items without an issue date (31 -> 23 on a
CLACSO probe), so the year stays a column for the screen.
"""

from pipeline_io import polite_get

from rel_sud_sources._common import (
    empty_record,
    find_doi,
    find_year,
    lexicon_terms,
    term_matcher,
)

PAGE_SIZE = 100
# Where a publication date sits when dc.date.issued is empty. CLACSO carries
# plain ``dc.date`` on many items (hdl CLACSO/34982: dc.date 2012, no
# dc.date.issued; 2026-09-30). Never dc.date.accessioned/available: those are
# deposit dates.
PUBLICATION_DATE_KEYS = ("dc.date", "dcterms.issued", "dc.date.created")


def lexicon_plan(source, lexicon, extra_params=None):
    """One spec per language x theme, ``query_string`` the exact parameters sent.

    ``terms`` (every phrase of the source's languages) lets ``fetch`` flag
    ``matched_terms`` on title and abstract: a search route keeps every hit,
    the flag only helps the screen tell a title hit from a full-text one.
    """
    terms = lexicon_terms(lexicon, source["languages"])
    specs = []
    for lang in source["languages"]:
        for theme, query in sorted(lexicon[lang].items()):
            params = {"query": query, "dsoType": "ITEM", **(extra_params or {})}
            specs.append({
                "query_id": f"S-{source['name']}-{lang}-{theme}",
                # Unencoded for the reader; requests encodes on the wire.
                "query_string": "&".join(f"{k}={v}" for k, v in params.items()),
                "params": params,
                "terms": terms,
            })
    return specs


def _values(md, key):
    return [m.get("value", "") for m in md.get(key, []) if m.get("value")]


def item_to_record(obj, base_url, match=None):
    """Normalized record from one DSpace ``indexableObject`` (an item)."""
    md = obj.get("metadata", {})
    handle = obj.get("handle") or ""
    uris = _values(md, "dc.identifier.uri")
    ids = _values(md, "dc.identifier.doi") + _values(md, "dc.identifier") + uris
    title = " / ".join(_values(md, "dc.title"))
    abstract = " ".join(_values(md, "dc.description.abstract")
                        + _values(md, "dc.description.abstractalternative"))
    return empty_record(
        record_id=f"hdl:{handle}" if handle else obj.get("uuid", ""),
        url=uris[0] if uris else (f"{base_url}/handle/{handle}" if handle else ""),
        doi=find_doi(ids),
        title=title,
        authors="; ".join(_values(md, "dc.contributor.author") + _values(md, "dc.creator")),
        year=(find_year(_values(md, "dc.date.issued"))
              or find_year([v for k in PUBLICATION_DATE_KEYS for v in _values(md, k)])),
        language="; ".join(_values(md, "dc.language.iso") + _values(md, "dc.language")),
        venue="; ".join(_values(md, "dc.relation.ispartofseries")
                        + _values(md, "dc.relation.ispartof")
                        + _values(md, "dc.publisher")[:1]),
        doc_type="; ".join(_values(md, "dc.type")),
        abstract=abstract[:3000],
        matched_terms="; ".join(match(title + " " + abstract)) if match else "",
    )


def search(base_url, spec, delay, get=polite_get):
    """Page through one discovery query; the fetch protocol of the adapters.

    ``base_url`` is the site root (``https://host``); the API sits under
    ``/server/api``. The end reason is ``''`` only when every announced item
    arrived; a short count, a page without its counts, or a result that is not
    an item is reported, never passed off as complete.
    """
    endpoint = f"{base_url}/server/api/discover/search/objects"
    match = term_matcher(spec["terms"]) if spec.get("terms") else None
    page, total, received, empty = 0, None, 0, 0
    while True:
        params = {**spec["params"], "page": page, "size": PAGE_SIZE}
        try:
            resp = get(endpoint, params=params, delay=delay)
        except Exception as exc:  # network failure after retries
            yield ("end", f"error: {type(exc).__name__}")
            return
        if resp.status_code != 200:
            yield ("end", f"http {resp.status_code}")
            return
        try:
            result = resp.json()["_embedded"]["searchResult"]
        except (ValueError, KeyError, TypeError):
            yield ("end", "error: bad json")
            return
        info = result.get("page", {})
        try:
            total_pages = int(info["totalPages"])
            if total is None:
                total = int(info["totalElements"])
                yield ("meta", total)
        except (KeyError, TypeError, ValueError):
            yield ("end", "error: no page counts")
            return
        objects = result.get("_embedded", {}).get("objects", [])
        for o in objects:
            obj = o.get("_embedded", {}).get("indexableObject") or {}
            received += 1
            if not obj.get("metadata"):
                empty += 1
                continue
            yield ("work", item_to_record(obj, base_url, match))
        page += 1
        if not objects or page >= total_pages:
            break
    if received < total:
        yield ("end", f"short: {received} of {total}")
    else:
        yield ("end", f"{empty} results without item metadata" if empty else "")
