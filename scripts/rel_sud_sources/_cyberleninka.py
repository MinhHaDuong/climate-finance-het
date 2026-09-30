"""CyberLeninka (Russian open-access library), substitute for eLIBRARY.ru.

eLIBRARY is closed to automated access (user agreement forbids robots and
automated search; its API is a contract product), so CyberLeninka runs in its
place under its own name.

Route probed 2026-09-30: ``robots.txt`` disallows ``/search`` and ``/api/``, so
the site search is out of bounds; ``/oai`` (OAI-PMH 2.0, ``oai_dc`` only) is
not disallowed. Its records carry title, creators, publisher and URL only: no
abstract, no publication date (datestamps are ingest dates, 2014 onwards), and
ten records per page with no ``completeListSize``.

The index sets are no discipline filter: the first 9,830 records of ``repec``
(run 2026-09-30, ``cyberleninka-b``) were physics, medicine and engineering. So
the harvest targets journal sets (``journal_N``, about 3,900) whose names
contain a finance, climate, sustainability, economics or ecology root
(``JOURNAL_TIERS``), most specific tier first. Candidates are selected locally
by the Russian and English lexicon on titles only. One registry row per
journal; a page budget shared by all journals bounds the run, and every journal
it leaves unharvested or cut short is recorded incomplete, never silently full.

Rate limit: after about 980 pages (repec run, 20 minutes at one request a
second) ``/oai`` began answering its HTML captcha page. The adapter detects it
and ends the query "blocked", without solving it; a blocked ListSets yields a
single blocked registry row. A sustained harvest needs the operator's consent
(OAI adminEmail in Identify).
"""

import re
import types
import xml.etree.ElementTree as ET

from pipeline_io import polite_get

from rel_sud_sources._common import (
    NS,
    dc_to_record,
    lexicon_terms,
    oai_list_records,
    term_matcher,
)

ENDPOINT = "https://cyberleninka.ru/oai"
LANGUAGES = ["ru", "en"]
PAGE_BUDGET = 8000  # 10 records a page, shared across journals

# Journal-name roots, most specific first; a journal takes its first tier.
JOURNAL_TIERS = [
    r"климат|финанс|устойчив|climat|financ|sustainab",
    r"эконом|природопольз|econom",
    r"эколог|ecolog|environment",
]

SOURCE = {
    "name": "cyberleninka",
    "region": "Russia",
    "languages": LANGUAGES,
    "route": "oai-pmh",
    "endpoint": ENDPOINT,
    "terms": "https://cyberleninka.ru/robots.txt (Disallow /search, /api/; /oai allowed)",
}

get = polite_get  # tests replace this

# XML 1.0 forbids these control characters; stripped defensively.
_BAD_XML = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# After about 980 pages at one request a second (2026-09-30), /oai answered
# HTTP 200 with an HTML captcha page ("Вы точно человек?") instead of XML.
_CAPTCHA = re.compile("Вы точно человек|captcha".encode(), re.IGNORECASE)


class PageBudget(Exception):
    """Raised by the counting getter once the page budget is spent."""


class Captcha(Exception):
    """Raised when the server answers with its captcha page; never solved."""


def _checked(resp):
    if resp.status_code == 200 and not resp.content.lstrip().startswith(b"<?xml") \
            and _CAPTCHA.search(resp.content):
        raise Captcha
    return types.SimpleNamespace(status_code=resp.status_code,
                                 content=_BAD_XML.sub(b"", resp.content))


def list_journal_sets(delay=1.0):
    """``[(setSpec, setName)]`` of the journal sets, in server order."""
    resp = _checked(get(ENDPOINT, params={"verb": "ListSets"}, delay=delay))
    if resp.status_code != 200:
        raise RuntimeError(f"ListSets: http {resp.status_code}")
    root = ET.fromstring(resp.content)
    out = []
    for s in root.iterfind("oai:ListSets/oai:set", NS):
        spec = s.findtext("oai:setSpec", "", NS)
        if spec.startswith("journal_"):
            out.append((spec, (s.findtext("oai:setName", "", NS) or "").strip()))
    return out


def select_journals(sets):
    """Journal sets matching a tier, ordered by tier then server order."""
    chosen = []
    for tier, rx in enumerate(JOURNAL_TIERS, 1):
        pat = re.compile(rx, re.IGNORECASE)
        seen = {c[0] for c in chosen}
        chosen += [(spec, name, tier) for spec, name in sets
                   if spec not in seen and pat.search(name)]
    return chosen


def plan(cfg):
    terms = lexicon_terms(cfg["lexicon"], LANGUAGES)
    budget = {"left": cfg.get("cyberleninka_page_budget", PAGE_BUDGET)}
    try:
        journals = select_journals(list_journal_sets())
    except Captcha:
        return [{"query_id": "S-cyberleninka-listsets",
                 "query_string": "OAI-PMH ListSets (journal-set selection)",
                 "blocked": True}]
    specs = []
    for spec, name, tier in journals:
        specs.append({
            "query_id": f"S-cyberleninka-{spec}",
            "query_string": (f"OAI-PMH ListRecords metadataPrefix=oai_dc set={spec} "
                             f"({name}; journal-name tier {tier}); no date window "
                             f"(records carry no publication date); candidates "
                             f"selected by the local lexicon of languages "
                             f"{', '.join(LANGUAGES)} on titles only (no abstracts)"),
            "set": spec,
            "terms": terms,
            "budget": budget,  # shared, mutable: one budget for the whole run
        })
    return specs


def fetch(spec, delay):
    if spec.get("blocked"):
        yield ("end", "blocked: captcha page (not solved)")
        return
    match = term_matcher(spec["terms"])
    budget = spec["budget"]

    def counting_get(url, params=None, delay=0):
        if budget["left"] <= 0:
            raise PageBudget
        budget["left"] -= 1
        return _checked(get(url, params=params, delay=delay))

    for kind, val in oai_list_records(ENDPOINT, set_spec=spec["set"], delay=delay,
                                      get=counting_get):
        if kind == "dc":
            if not val.get("_deleted"):
                yield ("work", dc_to_record(val, match))
        elif kind == "end" and val == "error: PageBudget":
            yield ("end", "page budget reached")
        elif kind == "end" and val == "error: Captcha":
            yield ("end", "blocked: captcha page (not solved)")
        else:
            yield (kind, val)
