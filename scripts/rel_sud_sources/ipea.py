"""Ipea "Texto para Discussão" series, DSpace 7 search scoped to the series (ticket 1653).

The collection (handle 11058/17462) holds the Portuguese TDs and their English
versions; the search is scoped to it by UUID.
"""

from rel_sud_sources import latam_dspace

BASE = "https://repositorio.ipea.gov.br"
TD_COLLECTION = "869e6292-9b50-4001-937d-28a96293d50b"  # hdl 11058/17462

SOURCE = {
    "name": "ipea",
    "region": "latin_america_caribbean",
    "languages": ["pt", "en"],
    "route": "api",
    "endpoint": f"{BASE}/server/api/discover/search/objects",
    "terms": "1530 lexicon, pt and en",
}


def plan(cfg):
    return latam_dspace.lexicon_plan(SOURCE, cfg["lexicon"], {"scope": TD_COLLECTION})


def fetch(spec, delay, **kw):
    yield from latam_dspace.search(BASE, spec, delay, **kw)
