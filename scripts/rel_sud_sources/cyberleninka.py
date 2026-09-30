"""CyberLeninka (Russian open-access library), substitute for eLIBRARY.ru.

eLIBRARY is closed to automated access (user agreement forbids robots and
automated search; its API is a contract product), so CyberLeninka runs in its
place under its own name.

Route probed 2026-09-30: ``robots.txt`` disallows ``/search`` and ``/api/``, so
the site search is out of bounds; ``/oai`` (OAI-PMH 2.0, ``oai_dc`` only) is
not disallowed. Its records carry title, creators, publisher and URL only: no
abstract, no publication date (datestamps are ingest dates, 2014 onwards), and
ten records per page with no ``completeListSize``. There is no discipline set;
the closest is ``repec`` (journals indexed in RePEc, i.e. economics), harvested
here. Candidates are selected locally by the Russian and English lexicon on
titles only. A page budget bounds the run (about three hours at one request a
second); reaching it leaves the query incomplete, never silently full.
"""

from pipeline_io import polite_get

from rel_sud_sources.common import (
    dc_to_record,
    lexicon_terms,
    oai_list_records,
    term_matcher,
)

ENDPOINT = "https://cyberleninka.ru/oai"
LANGUAGES = ["ru", "en"]
SETS = ["repec"]
PAGE_BUDGET = 8000  # 10 records a page

SOURCE = {
    "name": "cyberleninka",
    "region": "Russia",
    "languages": LANGUAGES,
    "route": "oai-pmh",
    "endpoint": ENDPOINT,
    "terms": "https://cyberleninka.ru/robots.txt (Disallow /search, /api/; /oai allowed)",
}

get = polite_get  # tests replace this


class PageBudget(Exception):
    """Raised by the counting getter once the page budget is spent."""


def plan(cfg):
    terms = lexicon_terms(cfg["lexicon"], LANGUAGES)
    return [{
        "query_id": f"S-cyberleninka-{s}",
        "query_string": (f"OAI-PMH ListRecords metadataPrefix=oai_dc set={s} "
                         f"(no date window: records carry no publication date); "
                         f"candidates selected by the local lexicon of languages "
                         f"{', '.join(LANGUAGES)} on titles only (no abstracts); "
                         f"page budget {PAGE_BUDGET} x 10 records"),
        "set": s,
        "terms": terms,
        "page_budget": PAGE_BUDGET,
    } for s in SETS]


def fetch(spec, delay):
    match = term_matcher(spec["terms"])
    budget = spec.get("page_budget", PAGE_BUDGET)
    calls = {"n": 0}

    def counting_get(url, params=None, delay=0):
        if calls["n"] >= budget:
            raise PageBudget
        calls["n"] += 1
        return get(url, params=params, delay=delay)

    for kind, val in oai_list_records(ENDPOINT, set_spec=spec["set"], delay=delay,
                                      get=counting_get):
        if kind == "dc":
            if not val.get("_deleted"):
                yield ("work", dc_to_record(val, match))
        elif kind == "end" and val == "error: PageBudget":
            yield ("end", f"page budget {budget} reached")
        else:
            yield (kind, val)
