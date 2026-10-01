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
journals) is out of a 3-hour budget: only the categories in ``CATEGORIES``
are harvested, and that restriction is written into every query string.

AJOL sits behind an AWS WAF whose rate rule answers HTTP 202 with an empty
body and ``x-amzn-waf-action: challenge`` (a JavaScript challenge, never
solved here). Seen on 2026-09-30 at one request per 2 s; hence 4 s between
requests, a pause and retry on a challenge, and once the challenge persists
across ``MAX_CHALLENGED`` journals in a row the remaining journals are
skipped (registered incomplete) instead of pressing on.

Requests go through ``_common.oai_get``: the ``mailto`` query parameter that
``polite_get`` appends makes OJS answer ``badArgument``. Characters XML
forbids (U+FFFE in an abstract) are removed by ``_common.oai_list_records``
before parsing; otherwise one of them loses the rest of a journal.
"""

import re
import time
from datetime import datetime, timezone

from utils import get_logger

from rel_sud_sources._common import dc_to_record, oai_get, oai_list_records
from rel_sud_sources._listing import matcher

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
    while page <= n_pages:  # n_pages only grows: a page without the count keeps it
        try:
            resp = get(f"{SITE}/ajol/browseBy/category", delay=delay,
                       params={"category": slug, "journalsPage": page})
        except Exception as exc:  # network failure after retries
            return paths, f"{slug} page {page}: {type(exc).__name__}"
        if resp.status_code != 200 or not resp.text:
            return paths, f"{slug} page {page}: http {resp.status_code}"
        paths.extend(JOURNAL_RE.findall(resp.text))
        m = PAGES_RE.search(resp.text)
        n_pages = max(n_pages, int(m.group(1))) if m else n_pages
        page += 1
    if not paths:
        return paths, f"{slug}: no journal on the category pages"
    return list(dict.fromkeys(paths)), ""


# The getter used when none is passed. The runner's ``--browser`` swaps in a
# headless-Chromium getter (``_browser.BrowserGet``) that passes the WAF's
# JavaScript challenge (ticket 1790).
GET = oai_get


def plan(cfg, get=None):
    """One query per journal of the chosen categories (network: category pages).

    A category whose journal list cannot be read becomes one incomplete row
    (``error``) and the other categories still run. ``cfg['deadline']`` (ISO
    datetime, optional) is carried in every spec: a journal not started by
    then ends "skipped: time budget", never silently absent."""
    get = get or GET
    match = matcher(cfg, LANGUAGES)
    deadline = cfg.get("deadline")
    journals, failed = {}, []
    for slug in CATEGORIES:
        paths, error = category_journals(slug, patient(get), MIN_DELAY)
        if error:
            failed.append({"query_id": f"S-ajol-{slug}-journals",
                           "endpoint": f"{SITE}/ajol/browseBy/category?category={slug}",
                           "query_string": f"AJOL category {slug}: journal list",
                           "error": f"error: journal list: {error}"})
        for p in paths:
            journals.setdefault(p, []).append(slug)
    return failed + [{"query_id": f"S-ajol-{path}",
             "endpoint": f"{SITE}/{path}/oai",
             "query_string": (f"OAI-PMH ListRecords metadataPrefix=oai_dc at {SITE}/{path}/oai "
                              f"(whole journal; AJOL categories {', '.join(cats)}; harvest "
                              f"restricted to categories {', '.join(CATEGORIES)}); candidates "
                              f"selected by the local 1530 lexicon ({'/'.join(LANGUAGES)}) "
                              f"on title+abstract (no year window: the pool applies it)"),
             "match": match, "deadline": deadline}
            for path, cats in journals.items()]  # insertion order = category priority



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


def past(deadline):
    """Whether an ISO deadline has passed; a deadline without offset is UTC."""
    if not deadline:
        return False
    when = datetime.fromisoformat(deadline)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) >= when


def fetch(spec, delay, get=None, sleep=time.sleep):
    get = get or GET
    if spec.get("error"):
        yield ("end", spec["error"])
        return
    if past(spec.get("deadline")):
        yield ("end", "skipped: time budget reached before this journal")
        return
    # The skip state lives for the process: once the challenge has persisted,
    # no later journal of the run is requested.
    if _state["challenged_in_a_row"] >= MAX_CHALLENGED:
        yield ("end", "skipped: WAF challenge persisted on previous journals")
        return
    stream = oai_list_records(spec["endpoint"], delay=max(delay, MIN_DELAY),
                              get=patient(get, sleep))
    for kind, val in stream:
        if kind == "end":
            hit = val == "http 202"
            _state["challenged_in_a_row"] = _state["challenged_in_a_row"] + 1 if hit else 0
            yield ("end", "http 202 (WAF challenge)" if hit else val)
            return
        if kind == "dc":
            if val.get("_deleted"):
                continue
            yield ("work", dc_to_record(val, spec["match"]))
        else:
            yield (kind, val)
