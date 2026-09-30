"""University of the West Indies repository (UWISpace), DSpace 7 search (ticket 1653).

UWISpace at uwispace.sta.uwi.edu (handle prefix 2139) is the university-wide
repository; the search covers all its communities.
"""

from rel_sud_sources import latam_dspace

BASE = "https://uwispace.sta.uwi.edu"

SOURCE = {
    "name": "uwi",
    "region": "latin_america_caribbean",
    "languages": ["en"],
    "route": "api",
    "endpoint": f"{BASE}/server/api/discover/search/objects",
    "terms": "1530 lexicon, en",
}


def plan(cfg):
    return latam_dspace.lexicon_plan(SOURCE, cfg["lexicon"])


def fetch(spec, delay, **kw):
    yield from latam_dspace.search(BASE, spec, delay, **kw)
