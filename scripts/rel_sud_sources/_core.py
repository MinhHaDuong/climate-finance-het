"""CORE (core.ac.uk) API v3: whole data-provider harvests standing in for
sources closed to robots (ticket 1790).

The author's rule of 2026-09-30 declares dead a source no automated browser
can reach within its robots.txt and terms. Where an aggregator harvests that
source with its consent, the aggregator's copy is read instead. CORE is one:
its data providers include the University of the South Pacific repository
(USP's own site: robots.txt disallows ``/cgi/`` and Cloudflare answers 403),
CyberLeninka (its ``/oai`` answers a reCAPTCHA) and Shodhganga (robots.txt
``Disallow: /``).

Route probed 2026-09-30: ``/v3/search/works`` accepts no provider filter
(``dataProviders is not a searchable field``), but ``/v3/search/outputs``
takes ``q=repositories.id:<provider>`` and pages by ``offset``. Its phrase
search is loose, so a provider is read whole (a listing route) and the local
1530 lexicon on title and abstract selects the candidates, as for the OAI
harvests. A provider CORE holds nothing of answers ``totalHits: 0``, a
complete answer, recorded as such.

CORE sends Python's default User-Agent a Cloudflare 403: requests carry the
lane's name. The key (``CORE_API_KEY`` in ``~/.config/keys/core.env``) is
read in process and never logged.
"""

import time

import requests
from pipeline_keystore import read_credential

from rel_sud_sources._common import empty_record, find_year
from rel_sud_sources._listing import listing_query, matcher

API = "https://api.core.ac.uk/v3/search/outputs"
USER_AGENT = "ClimateFinancePipeline/1.0 (climate-finance-het, CNRS research)"
PAGE = 100
MIN_DELAY = 7.0  # CORE answers X-RateLimit-Limit 150; stay far below

# (CORE data-provider id, name, the dead source it stands for, lexicon languages)
PROVIDERS = [
    (373, "University of the South Pacific Electronic Research Repository",
     "usp_repository", ["en", "fr"]),
    (1252, "CyberLeninka - Russian open access scientific library",
     "cyberleninka", ["ru", "en"]),
    (8818, "Shodhganga@INFLIBNET", "shodhganga", ["en", "hi"]),
]

SOURCE = {
    "name": "core",
    "region": "Pacific, Russia, South Asia (by data provider)",
    "languages": sorted({lang for *_, langs in PROVIDERS for lang in langs}),
    "route": "listing",
    "endpoint": API,
    "terms": "https://core.ac.uk/terms (API v3 with a registered key)",
}


def core_get(url, params=None, delay=0):
    time.sleep(max(delay, MIN_DELAY))
    key = read_credential("core", "CORE_API_KEY")
    return requests.get(url, params=params, timeout=120,
                        headers={"Authorization": f"Bearer {key}", "User-Agent": USER_AGENT})


GET = core_get  # tests replace this


def plan(cfg):
    return [{"query_id": f"L-core-{pid}",
             "query_string": listing_query(
                 f"CORE v3 {API}?q=repositories.id:{pid} ({name}; stands in for {dead}), "
                 f"every page of {PAGE}", langs),
             "provider": pid, "venue": name, "match": matcher(cfg, langs)}
            for pid, name, dead, langs in PROVIDERS]


def to_record(x, venue, match):
    ids = x.get("identifiers") or {}
    urls = x.get("sourceFulltextUrls") or [u.get("url", "") for u in x.get("urls") or []]
    title = (x.get("title") or "").strip()
    abstract = (x.get("abstract") or "").strip()
    lang = x.get("language") or {}
    return empty_record(
        record_id=str(x["id"]),
        url=next((u for u in urls if u), f"https://core.ac.uk/outputs/{x['id']}"),
        doi=(x.get("doi") or ids.get("doi") or "").strip(),
        title=title,
        authors="; ".join(a.get("name", "") for a in x.get("authors") or [] if a.get("name")),
        year=find_year([x.get("yearPublished") or "", x.get("publishedDate") or ""]),
        language=lang.get("code", "") if isinstance(lang, dict) else str(lang),
        venue=venue,
        doc_type=x.get("documentType") or "; ".join(x.get("tags") or []),
        abstract=abstract[:3000],
        matched_terms="; ".join(match(title + " " + abstract)))


def fetch(spec, delay, get=None):
    get = get or GET
    offset, total = 0, None
    while total is None or offset < total:
        params = {"q": f"repositories.id:{spec['provider']}", "limit": PAGE, "offset": offset}
        try:
            resp = get(API, params=params, delay=delay)
        except Exception as exc:  # network failure
            yield ("end", f"error: {type(exc).__name__} at offset {offset}")
            return
        if resp.status_code != 200:
            yield ("end", f"http {resp.status_code} at offset {offset}")
            return
        try:
            body = resp.json()
            results, hits = body["results"], int(body["totalHits"])
        except (ValueError, KeyError, TypeError):
            yield ("end", f"error: bad body at offset {offset}")
            return
        if total is None:
            total = hits
            yield ("meta", total)
        for x in results:
            if x.get("id") is None or not (x.get("title") or "").strip():
                continue
            yield ("work", to_record(x, spec["venue"], spec["match"]))
        if not results:
            break
        offset += len(results)
    yield ("end", "" if offset >= (total or 0) else f"short: {offset} of {total}")
