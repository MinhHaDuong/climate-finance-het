"""AJOL (African Journals Online), per-journal OAI-PMH harvest.

AJOL runs OJS 3. The site-level endpoint ``/index.php/index/oai`` answers but
holds nothing (``earliestDatestamp`` = now, ``ListRecords set=ajol:ART``:
``noRecordsMatch``, 2026-09-30); every journal has its own endpoint
``/index.php/<journal>/oai``. Search and the REST API are closed to robots
(robots.txt: ``Disallow: /index.php/*/search/``, ``/index.php/*/api/``), so
the route is harvest-then-match.

The journals are listed from AJOL's subject categories
(``/index.php/ajol/browseBy/category?category=<slug>&journalsPage=N``). OJS
serves 20 records per OAI page, so the whole of AJOL (about 1000 journal
sitemaps) is out of a 3-hour budget: only the categories in ``CATEGORIES``
are harvested, and that restriction is written into every query string.

AJOL sits behind an AWS WAF whose rate rule answers HTTP 202 with an empty
body and ``x-amzn-waf-action: challenge`` (a JavaScript challenge, never
solved here). Seen on 2026-09-30 at one request per 2 s; hence 4 s between
requests, a pause and retry on a challenge, and once the challenge persists
across ``MAX_CHALLENGED`` journals in a row the remaining journals are
skipped (registered incomplete) instead of pressing on.

Requests go through ``listing.no_mailto_get``: the ``mailto`` query parameter
that ``polite_get`` appends makes OJS answer ``badArgument``.
Characters XML forbids (U+FFFE in an abstract) are removed before parsing
(``listing.xml_clean``); otherwise one of them loses the rest of a journal.
"""

import re
import time

from utils import get_logger

from rel_sud_sources.common import dc_to_record, oai_list_records
from rel_sud_sources.listing import matcher, no_mailto_get, xml_clean

log = get_logger("rel_sud_sources")

SITE = "https://www.ajol.info/index.php"
LANGUAGES = ["en", "fr", "pt", "ar"]
MIN_DELAY = 4.0
CHALLENGE_PAUSES = (120, 300)  # seconds to wait before each retry
MAX_CHALLENGED = 3
CATEGORIES = [
    "economics-and-development", "finance-and-management", "environmental-sciences",
    "political-science-and-law", "earth-sciences",
]  # in priority order: journals are harvested category by category
YEARS = (1990, 2026)

SOURCE = {
    "name": "ajol",
    "region": "Africa",
    "languages": LANGUAGES,
    "route": "oai-pmh",
    "endpoint": f"{SITE}/<journal>/oai",
    "terms": "https://www.ajol.info/robots.txt",
}

JOURNAL_RE = re.compile(r'href="https://www\.ajol\.info/index\.php/([a-z0-9_-]+)" class="journalMenu"')
PAGES_RE = re.compile(r"of (\d+) pages")


def category_journals(slug, get, delay):
    """Journal paths of one AJOL category, every page; ``(paths, error)``."""
    paths, page, n_pages = [], 1, 1
    while page <= n_pages:
        try:
            resp = get(f"{SITE}/ajol/browseBy/category", delay=delay,
                       params={"category": slug, "journalsPage": page})
        except Exception as exc:  # network failure after retries
            return paths, f"{slug} page {page}: {type(exc).__name__}"
        if resp.status_code != 200 or not resp.text:
            return paths, f"{slug} page {page}: http {resp.status_code}"
        paths.extend(JOURNAL_RE.findall(resp.text))
        m = PAGES_RE.search(resp.text)
        n_pages = int(m.group(1)) if m else 1
        page += 1
    return paths, ""


def plan(cfg, get=no_mailto_get):
    """One query per journal of the chosen categories (network: category pages)."""
    match = matcher(cfg, LANGUAGES)
    journals = {}
    for slug in CATEGORIES:
        paths, error = category_journals(slug, patient(get), MIN_DELAY)
        if error:
            raise RuntimeError(f"AJOL journal list incomplete: {error}")
        for p in paths:
            journals.setdefault(p, []).append(slug)
    return [{"query_id": f"S-ajol-{path}",
             "endpoint": f"{SITE}/{path}/oai",
             "query_string": (f"OAI-PMH ListRecords metadataPrefix=oai_dc at {SITE}/{path}/oai "
                              f"(whole journal; AJOL categories {', '.join(cats)}; harvest "
                              f"restricted to categories {', '.join(CATEGORIES)}); candidates "
                              f"selected by the local 1530 lexicon ({'/'.join(LANGUAGES)}) "
                              f"on title+abstract, years {YEARS[0]}-{YEARS[1]}"),
             "match": match}
            for path, cats in journals.items()]  # insertion order = category priority


def in_window(rec):
    return rec["year"] is None or YEARS[0] <= rec["year"] <= YEARS[1]


def challenged(resp):
    return resp.status_code == 202 and resp.headers.get("x-amzn-waf-action") == "challenge"


def patient(get, sleep=time.sleep):
    """``get`` that waits out a WAF challenge (``CHALLENGE_PAUSES``), then gives up."""
    def wrapped(url, params=None, delay=0):
        resp = get(url, params=params, delay=delay)
        for pause in CHALLENGE_PAUSES:
            if not challenged(resp):
                break
            log.warning("WAF challenge on %s %s; waiting %d s", url, params, pause)
            sleep(pause)
            resp = get(url, params=params, delay=delay)
        return resp
    return wrapped


_state = {"challenged_in_a_row": 0}


def fetch(spec, delay, get=no_mailto_get, sleep=time.sleep):
    if _state["challenged_in_a_row"] >= MAX_CHALLENGED:
        yield ("end", "skipped: WAF challenge persisted on previous journals")
        return
    stream = oai_list_records(spec["endpoint"], delay=max(delay, MIN_DELAY),
                              get=xml_clean(patient(get, sleep)))
    for kind, val in stream:
        if kind == "end":
            hit = val == "http 202"
            _state["challenged_in_a_row"] = _state["challenged_in_a_row"] + 1 if hit else 0
            yield ("end", "http 202 (WAF challenge)" if hit else val)
            return
        if kind == "dc":
            if val.get("_deleted"):
                continue
            rec = dc_to_record(val, spec["match"])
            if not in_window(rec):
                rec["matched_terms"] = ""
            yield ("work", rec)
        else:
            yield (kind, val)
