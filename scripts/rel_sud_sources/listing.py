"""Helpers for listing routes: whole series fetched, candidates matched locally.

Ticket 1653, Africa / South Asia lane. A working-paper series or an institute
catalogue is small (hundreds to a few thousand items): the adapter fetches its
full listing and the 1530 lexicon selects candidates locally, the way the
OAI-PMH harvest routes do.

The runner keeps every record of a non-OAI route, so a listing adapter yields
only the records that matched (``yield_matches``). ``n_expected`` in the
registry is then the size of the listing, ``n_received`` the number of matches:
the gap is the local selection, not a loss. The query string says so.

No ``SOURCE`` here: the runner's discovery skips this module.
"""

import html
import re

import requests
from openalex_corpus import retry_get
from pipeline_io import MAILTO, POLITE_MAX_RETRIES

from rel_sud_sources.common import lexicon_terms, term_matcher

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def html_text(s):
    """Plain text of an HTML fragment."""
    return SPACE_RE.sub(" ", html.unescape(TAG_RE.sub(" ", s or ""))).strip()


def matcher(cfg, languages):
    return term_matcher(lexicon_terms(cfg["lexicon"], languages))


def listing_query(what, languages, extra=""):
    """The query string of a listing route: what was fetched, how selected."""
    s = (f"{what}; full listing fetched, candidates selected by the local 1530 "
         f"lexicon ({'/'.join(languages)}) on title+abstract; only matches are "
         f"yielded, so n_expected is the listing size and n_received the matches")
    return s + (f"; {extra}" if extra else "")


def script_language(text, default="en"):
    """Language guess from script alone: Devanagari hi, Bengali bn, Arabic ar."""
    for lo, hi, lang in ((0x0900, 0x097F, "hi"), (0x0980, 0x09FF, "bn"),
                         (0x0600, 0x06FF, "ar")):
        if any(lo <= ord(c) <= hi for c in text or ""):
            return lang
    return default


def wp_listing(get, url, params, delay, per_page=100):
    """Every item of a WordPress REST collection: ``(items, error)``.

    Pages until ``X-WP-TotalPages``; ``error`` is ``''`` when the last page was
    read, else the reason the listing stopped short.
    """
    items, page = [], 1
    while True:
        try:
            resp = get(url, params={**params, "per_page": per_page, "page": page},
                       delay=delay)
        except Exception as exc:  # network failure after retries
            return items, f"error: {type(exc).__name__} on page {page}"
        if resp.status_code != 200:
            return items, f"http {resp.status_code} on page {page}"
        batch = resp.json()
        items.extend(batch)
        total_pages = int(resp.headers.get("X-WP-TotalPages", "0") or 0)
        if not batch or page >= total_pages:
            return items, ""
        page += 1


def emit(records, n_listing, error):
    """Runner protocol over built records: listing size, matches only, end."""
    yield ("meta", n_listing)
    for rec in records:
        if rec.get("matched_terms"):
            yield ("work", rec)
    yield ("end", error)


def soft(get):
    """``get`` that returns a 4xx response instead of raising it.

    ``polite_get`` raises ``HTTPError`` on any 4xx; a listing needs to see the
    404 that marks the page past the last one, as distinct from a failure.
    """
    def wrapped(url, params=None, delay=0):
        try:
            return get(url, params=params, delay=delay)
        except requests.HTTPError as exc:
            if exc.response is None:
                raise
            return exc.response
    return wrapped


def no_mailto_get(url, params=None, delay=1.0):
    """``polite_get`` without the ``mailto`` query parameter.

    ``polite_get`` appends ``mailto=...`` to every request (an OpenAlex
    courtesy). An OAI-PMH server must reject unknown arguments, and OJS does:
    ``badArgument`` on every AJOL journal (2026-09-30). Same retries, same
    identifying User-Agent, no extra parameter.
    """
    return retry_get(url, params=params, delay=delay, max_retries=POLITE_MAX_RETRIES,
                     timeout=30, mailto=None,
                     user_agent=f"ClimateFinancePipeline/1.0 (mailto:{MAILTO})")


# Characters XML 1.0 forbids; OJS lets them through from pasted abstracts
# (U+FFFE inside an AJOL abstract broke a whole OAI page, 2026-09-30).
XML_INVALID_RE = re.compile("[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]")


class _Cleaned:
    def __init__(self, resp):
        self.status_code, self.headers, self.url = resp.status_code, resp.headers, getattr(resp, "url", "")
        text = resp.content.decode("utf-8", errors="replace")
        self.text = XML_INVALID_RE.sub("", text)
        self.content = self.text.encode("utf-8")


def xml_clean(get):
    """``get`` whose 200 responses have XML-forbidden characters removed.

    ``common.oai_list_records`` parses the raw bytes, and one forbidden
    character makes the whole page (and the rest of the journal) unreadable.
    """
    def wrapped(url, params=None, delay=0):
        resp = get(url, params=params, delay=delay)
        return _Cleaned(resp) if resp.status_code == 200 else resp
    return wrapped
