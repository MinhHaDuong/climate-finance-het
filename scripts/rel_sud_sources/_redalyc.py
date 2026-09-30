"""Redalyc, through the search service of its own article finder (ticket 1653).

Two routes exist. The documented one is OAI-PMH (http://148.215.1.70/redalyc/oai,
announced at https://www.redalyc.org/redalyc/acerca-de/oai-pmh.html), but it has
no subject sets (journal ISSN, country, institution only) and holds 775,205
records at 100 per page: about 5.5 h of full harvest for a local lexicon match.
The article finder (busquedaArticuloFiltros.oa) calls a JSON service,
``/service/r2020/getArticles/<query>/<page>/<size>/1/default``; robots.txt of
www.redalyc.org does not disallow it and it accepts quoted phrases and ``OR``.
It is undocumented, so the lexicon runs there: 12 queries instead of 7,800
harvest pages. The service searches full text, not just title and abstract;
``matched_terms`` flags the hits the lexicon finds in title or abstract.
"""

import json
from urllib.parse import quote

from pipeline_io import polite_get

from rel_sud_sources._common import (
    empty_record,
    find_doi,
    find_year,
    lexicon_terms,
    term_matcher,
)

BASE = "https://www.redalyc.org/service/r2020/getArticles/"
PAGE_SIZE = 200

SOURCE = {
    "name": "redalyc",
    "region": "latin_america_caribbean",
    "languages": ["es", "pt", "en"],
    "route": "api",
    "endpoint": BASE,
    "terms": "1530 lexicon, es, pt and en",
}


def page_url(query, page):
    return f"{BASE}{quote(query, safe='')}/{page}/{PAGE_SIZE}/1/default"


def plan(cfg):
    terms = lexicon_terms(cfg["lexicon"], SOURCE["languages"])
    return [{"query_id": f"S-redalyc-{lang}-{theme}",
             # Unencoded for the reader; the path segment is percent-encoded.
             "query_string": f"{BASE}{query}/<page>/{PAGE_SIZE}/1/default",
             "query": query, "terms": terms}
            for lang in SOURCE["languages"]
            for theme, query in sorted(cfg["lexicon"][lang].items())]


def to_record(art, match=None):
    cve = str(art.get("cveArticulo", "")).strip()
    title = (art.get("titulo") or "").strip()
    abstract = (art.get("resumen") or "").strip()
    return empty_record(
        record_id=f"redalyc:{cve}",
        url=f"https://www.redalyc.org/articulo.oa?id={cve}" if cve else "",
        doi=find_doi([art.get("doiTitulo") or ""]),
        title=title,
        authors=(art.get("autores") or "").strip(),
        year=find_year([art.get("anioArticulo") or ""]),
        language=(art.get("idiomaArticulo") or "").strip(),
        venue=(art.get("nomRevista") or "").strip(),
        doc_type="article",
        abstract=abstract[:3000],
        matched_terms="; ".join(match(title + " " + abstract)) if match else "",
    )


def fetch(spec, delay, get=polite_get):
    match = term_matcher(spec["terms"]) if spec.get("terms") else None
    page, total, received = 1, None, 0
    while True:
        try:
            resp = get(page_url(spec["query"], page), delay=delay)
        except Exception as exc:  # network failure after retries
            yield ("end", f"error: {type(exc).__name__}")
            return
        if resp.status_code != 200:
            yield ("end", f"http {resp.status_code}")
            return
        try:
            # Served as text/plain without charset; the body is UTF-8.
            data = json.loads(resp.content.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            yield ("end", "error: bad json")
            return
        if total is None:
            total = int(data.get("totalResultados") or 0)
            yield ("meta", total)
        arts = data.get("resultados") or []
        for art in arts:
            received += 1
            yield ("work", to_record(art, match))
        if not arts or received >= total:
            break
        page += 1
    yield ("end", "" if received >= total else f"short: {received} of {total}")
