"""GARUDA (Garba Rujukan Digital, Indonesian ministry of higher education).

Route probed 2026-09-30: no OAI-PMH (``/oai`` 404), no documented JSON API,
``robots.txt`` absent (404, so nothing disallowed). The public search page
``/documents`` is server-rendered HTML, ten records per page, with a record
count ("Found N documents"), a field selector (``select=title|abstract``) and a
year filter (``from``/``to``). That page is the search route used here.

The server matches all words of ``q`` in one field, not the phrase, and ignores
double quotes (``"pendanaan iklim"`` and ``pendanaan iklim`` both return 7
titles), so it has no ``OR``: each lexicon phrase is one query, sent against the
title field and against the abstract field. Every record the server returns is
kept (search route); ``matched_terms`` records which lexicon phrases the title
or abstract actually contains, for the screen.
"""

import html
import re

from catalog_rel_sud_search import split_terms
from pipeline_io import polite_get

from rel_sud_sources._common import (
    empty_record,
    find_doi,
    find_year,
    lexicon_terms,
    term_matcher,
)

ENDPOINT = "https://garuda.kemdiktisaintek.go.id/documents"
BASE = "https://garuda.kemdiktisaintek.go.id"
LANGUAGES = ["id", "en"]
FIELDS = ["title", "abstract"]
YEAR_FROM, YEAR_TO = 1990, 2026

SOURCE = {
    "name": "garuda",
    "region": "Southeast Asia (Indonesia)",
    "languages": LANGUAGES,
    "route": "api",
    "endpoint": ENDPOINT,
    "terms": "https://garuda.kemdiktisaintek.go.id/ (no terms page; robots.txt 404)",
}

FOUND_RE = re.compile(r"Found\s+([\d.,]+)\s+documents?")
ITEM_SPLIT = '<div class="article-item">'
DETAIL_RE = re.compile(r'class="title-article"\s+href="(/documents/detail/(\d+))"\s*>\s*<xmp>(.*?)</xmp>', re.S)
AUTHOR_RE = re.compile(r'class="author-article"[^>]*><xmp>(.*?)</xmp>', re.S)
SUBTITLE_RE = re.compile(r'<xmp class="subtitle-article">(.*?)</xmp>', re.S)
ABSTRACT_RE = re.compile(r'<xmp class="abstract-article">(.*?)</xmp>', re.S)
SOURCE_RE = re.compile(r'href="([^"]+)"[^>]*>\s*Original Source', re.S)
DOI_LINK_RE = re.compile(r'href="(https?://(?:dx\.)?doi\.org/[^"]+)"')
YEAR_IN_PAREN_RE = re.compile(r"\((?:[^()]*?\b)?((?:19|20)\d{2})\)")

get = polite_get  # tests replace this


def _clean(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()


def plan(cfg):
    lex = cfg["lexicon"]
    terms = lexicon_terms(lex, LANGUAGES)
    specs = []
    for lang in LANGUAGES:
        for theme, query in sorted(lex[lang].items()):
            for i, phrase in enumerate(split_terms(query), 1):
                for field in FIELDS:
                    params = {"select": field, "q": phrase,
                              "from": YEAR_FROM, "to": YEAR_TO}
                    specs.append({
                        "query_id": f"S-garuda-{lang}-{theme}-{i:02d}-{field}",
                        "query_string": (f"select={field}&q={phrase}&from={YEAR_FROM}"
                                         f"&to={YEAR_TO} (server matches all words, "
                                         f"not the phrase)"),
                        "params": params,
                        "terms": terms,
                    })
    return specs


def parse_page(text, match):
    """``(n_found or None, [records])`` from one result page."""
    m = FOUND_RE.search(text)
    n_found = int(re.sub(r"[.,]", "", m.group(1))) if m else None
    records = []
    for block in text.split(ITEM_SPLIT)[1:]:
        d = DETAIL_RE.search(block)
        if not d:
            continue
        title = _clean(d.group(3))
        subtitles = [_clean(s) for s in SUBTITLE_RE.findall(block)]
        venue = subtitles[0] if subtitles else ""
        ym = YEAR_IN_PAREN_RE.search(venue)
        abstract = _clean(" ".join(ABSTRACT_RE.findall(block)))
        src = SOURCE_RE.search(block)
        dois = DOI_LINK_RE.findall(block)
        records.append(empty_record(
            record_id=f"garuda:{d.group(2)}",
            url=_clean(src.group(1)) if src else BASE + d.group(1),
            doi=find_doi(dois),
            title=title,
            authors="; ".join(_clean(a) for a in AUTHOR_RE.findall(block)),
            year=int(ym.group(1)) if ym else find_year([venue]),
            venue="; ".join(s for s in subtitles if s),
            doc_type="article",
            abstract=abstract[:3000],
            matched_terms="; ".join(match(title + " " + abstract)),
        ))
    return n_found, records


def fetch(spec, delay):
    """Pages to the announced count. Records are counted once by id (the sort
    is not guaranteed stable across pages), and a result block the parser
    cannot read ends the query incomplete, never complete."""
    match = term_matcher(spec["terms"])
    page, n_found, seen, unparsed = 1, None, set(), 0
    while True:
        params = {**spec["params"], "page": page}
        try:
            resp = get(ENDPOINT, params=params, delay=delay)
        except Exception as exc:  # network failure after retries
            yield ("end", f"error: {type(exc).__name__}")
            return
        if resp.status_code != 200:
            yield ("end", f"http {resp.status_code}")
            return
        text = resp.content.decode("utf-8", "replace")
        found, records = parse_page(text, match)
        unparsed += text.count(ITEM_SPLIT) - len(records)
        if page == 1:
            if found is None:
                yield ("end", "error: no result count on page 1")
                return
            n_found = found
            yield ("meta", n_found)
        for rec in records:
            if rec["record_id"] not in seen:
                seen.add(rec["record_id"])
                yield ("work", rec)
        if len(seen) >= n_found:
            yield ("end", f"{unparsed} result blocks not parsed" if unparsed else "")
            return
        if not records:
            yield ("end", f"empty page {page} before {n_found} records")
            return
        page += 1


# The detail page states the publication date ("Publish Date <br>01 Jul 2023")
# where the search page's venue line carries no year (about 100 records). fetch
# does not read it: the intake exporter's enrich-years step calls publish_year.
PUBLISH_DATE_RE = re.compile(r"Publish Date\s*<br\s*/?>\s*([^<]+?)\s*<", re.I)


def detail_url(record_id):
    """Detail page of a ``garuda:<id>`` record."""
    return f"{BASE}/documents/detail/{record_id.split(':', 1)[1]}"


def publish_year(text):
    """Year of the "Publish Date" of one detail page, or None."""
    m = PUBLISH_DATE_RE.search(text or "")
    return find_year([m.group(1)]) if m else None
