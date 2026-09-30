"""CLACSO institutional repository (Biblioteca Virtual), DSpace 7 search (ticket 1653).

The repository at biblioteca-repositorio.clacso.edu.ar replaced the old
Biblioteca Virtual (biblioteca.clacso.edu.ar). Its robots.txt asks
``Crawl-delay: 10``, so requests here are spaced by at least 10 s.
"""

from rel_sud_sources import latam_dspace

BASE = "https://biblioteca-repositorio.clacso.edu.ar"
CRAWL_DELAY = 10.0

SOURCE = {
    "name": "clacso",
    "region": "latin_america_caribbean",
    "languages": ["es", "pt"],
    "route": "api",
    "endpoint": f"{BASE}/server/api/discover/search/objects",
    "terms": "1530 lexicon, es and pt",
}


def plan(cfg):
    return latam_dspace.lexicon_plan(SOURCE, cfg["lexicon"])


def fetch(spec, delay, **kw):
    yield from latam_dspace.search(BASE, spec, max(delay, CRAWL_DELAY), **kw)
