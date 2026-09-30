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
"""

import re

from pipeline_io import polite_get

from rel_sud_sources.common import dc_to_record, oai_list_records
from rel_sud_sources.listing import matcher

SITE = "https://www.ajol.info/index.php"
LANGUAGES = ["en", "fr", "pt", "ar"]
MIN_DELAY = 2.0
CATEGORIES = [
    "economics-and-development", "environmental-sciences", "finance-and-management",
    "political-science-and-law", "earth-sciences",
]
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


def plan(cfg, get=polite_get):
    """One query per journal of the chosen categories (network: category pages)."""
    match = matcher(cfg, LANGUAGES)
    journals = {}
    for slug in CATEGORIES:
        paths, error = category_journals(slug, get, MIN_DELAY)
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
            for path, cats in sorted(journals.items())]


def in_window(rec):
    return rec["year"] is None or YEARS[0] <= rec["year"] <= YEARS[1]


def fetch(spec, delay, get=polite_get):
    for kind, val in oai_list_records(spec["endpoint"], delay=max(delay, MIN_DELAY), get=get):
        if kind == "dc":
            if val.get("_deleted"):
                continue
            rec = dc_to_record(val, spec["match"])
            if not in_window(rec):
                rec["matched_terms"] = ""
            yield ("work", rec)
        else:
            yield (kind, val)
