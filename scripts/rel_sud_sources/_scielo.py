"""SciELO, per-journal OAI-PMH harvest of social-science journals (ticket 1653).

Routes tried, 2026-09-30:

- search.scielo.org: robots.txt ``User-agent: * / Disallow: /`` and a Bunny
  Shield proof-of-work challenge (HTTP 403) in front of every query. No
  server-side search is reachable without circumventing it.
- ArticleMeta API (articlemeta.scielo.org/api/v1): open, but lists identifiers
  and serves one article per request; no text search. Used here only for the
  journal list and subject areas of each collection.
- Per-collection OAI-PMH (``/oai/scielo-oai.php``, sets = journal ISSN, no
  subject sets). Reachable, with no robots.txt forbidding it, for Mexico,
  Venezuela, Bolivia, Costa Rica and Paraguay. Brazil (www.scielo.br, 565k
  documents) answers 404 there; Argentina and Colombia time out; Cuba refuses
  the connection; Chile (scielo.conicyt.cl) and Peru answer but their
  robots.txt disallows every agent but the major search engines.

So this adapter harvests, in the reachable collections, the journals that
ArticleMeta files under "Applied Social Sciences" or whose WoS/CNPq subject
names economics, environment, development, politics, international relations
or planning, and keeps the records whose title or abstract matches the es, pt
and en lexicon. The OAI ``from`` argument is a datestamp, not a publication
date, so no date window is sent; the year stays a column for the screen.
"""

from pipeline_io import polite_get

from rel_sud_sources._common import (
    dc_to_record,
    lexicon_terms,
    oai_list_records,
    term_matcher,
)

ARTICLEMETA = "https://articlemeta.scielo.org/api/v1/journal/"
COLLECTIONS = {
    "mex": "https://www.scielo.org.mx/oai/scielo-oai.php",
    "ven": "https://ve.scielo.org/oai/scielo-oai.php",
    "bol": "https://www.scielo.org.bo/oai/scielo-oai.php",
    "cri": "https://www.scielo.sa.cr/oai/scielo-oai.php",
    "pry": "https://scielo.iics.una.py/oai/scielo-oai.php",
}
AREA = "Applied Social Sciences"
SUBJECT_KEYS = ("ECONOM", "ENVIRON", "AMBIENT", "DEVELOPMENT", "DESARROLLO",
                "POLITIC", "INTERNATIONAL", "PLANNING")
LANGUAGES = ["es", "pt", "en"]

SOURCE = {
    "name": "scielo",
    "region": "latin_america_caribbean",
    "languages": LANGUAGES,
    "route": "oai-pmh",
    "endpoint": "per-collection /oai/scielo-oai.php (" + ", ".join(COLLECTIONS) + ")",
    "terms": "1530 lexicon, es, pt and en, matched locally",
}


def _text(journal, *fields):
    return " ".join(v.get("_", "") for f in fields for v in journal.get(f, []))


def selected(journal):
    """Social-science journal by ArticleMeta subject area or WoS/CNPq subject."""
    return (AREA in _text(journal, "v441")
            or any(k in _text(journal, "v854", "v440").upper() for k in SUBJECT_KEYS))


def journals(collection, get=polite_get, delay=1.0):
    """``[(issn, title)]`` of the selected journals of one collection."""
    resp = get(ARTICLEMETA, params={"collection": collection}, delay=delay)
    resp.raise_for_status()
    return [(j["code"], _text(j, "v100")) for j in resp.json() if selected(j)]


def plan(cfg, get=polite_get):
    terms = lexicon_terms(cfg["lexicon"], LANGUAGES)
    specs = []
    for col, endpoint in COLLECTIONS.items():
        for issn, title in journals(col, get=get):
            specs.append({
                "query_id": f"H-scielo-{col}-{issn}",
                "query_string": (f"ListRecords metadataPrefix=oai_dc set={issn} ({title}); "
                                 f"selection by local lexicon of languages {', '.join(LANGUAGES)}"),
                "endpoint": endpoint,
                "set": issn,
                "terms": terms,
            })
    return specs


def fetch(spec, delay, get=polite_get):
    match = term_matcher(spec["terms"])
    for kind, val in oai_list_records(spec["endpoint"], set_spec=spec["set"],
                                      delay=delay, get=get):
        if kind == "dc":
            if not val.get("_deleted"):
                yield ("work", dc_to_record(val, match))
        else:
            yield (kind, val)
