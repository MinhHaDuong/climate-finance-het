"""Helpers for listing routes: whole series fetched, candidates matched locally.

Ticket 1653, Africa / South Asia lane. A working-paper series or an institute
catalogue is small (hundreds to a few thousand items): the adapter fetches its
full listing and the 1530 lexicon selects candidates locally, the way the
OAI-PMH harvest routes do.

A listing adapter yields every listed item with ``matched_terms`` set, and
declares ``route: "listing"``: the runner treats it as a harvest route,
archives the whole listing in ``raw/`` and keeps the matches as candidates.
``n_expected`` is the size of the listing, ``n_received`` the items read and
``n_matched`` the local selection. The query string says so.

No ``SOURCE`` here: the runner's discovery skips this module.
"""

import html
import re

import requests

from rel_sud_sources._common import lexicon_terms, term_matcher

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
         f"lexicon ({'/'.join(languages)}) on title+abstract; the whole listing is "
         f"archived, n_matched counts the selection")
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

    Pages until ``X-WP-TotalPages``; ``error`` is ``''`` only when the last
    page was read and, where ``X-WP-Total`` is sent, every item arrived. A
    missing page count is an error, never a one-page listing. Items are
    deduplicated by ``id`` (a post published mid-crawl shifts the offsets).
    """
    items, seen, page = [], set(), 1
    while True:
        try:
            resp = get(url, params={**params, "per_page": per_page, "page": page},
                       delay=delay)
        except Exception as exc:  # network failure after retries
            return items, f"error: {type(exc).__name__} on page {page}"
        if resp.status_code != 200:
            return items, f"http {resp.status_code} on page {page}"
        pages_header = resp.headers.get("X-WP-TotalPages")
        if pages_header is None or not str(pages_header).isdigit():
            return items, f"error: no X-WP-TotalPages header on page {page}"
        batch = resp.json()
        for it in batch:
            key = it.get("id") if isinstance(it, dict) else None
            if key is None or key not in seen:
                seen.add(key)
                items.append(it)
        if not batch or page >= int(pages_header):
            total = str(resp.headers.get("X-WP-Total", ""))
            if total.isdigit() and len(items) < int(total):
                return items, f"short: {len(items)} of {total}"
            return items, ""
        page += 1


def emit(records, n_listing, error):
    """Runner protocol over built records: listing size, every record, end.

    An empty listing without an error is reported as one: a series with no
    item at all means the listing call went wrong, not that it is complete."""
    if not n_listing and not error:
        error = "error: empty listing"
    yield ("meta", n_listing)
    for rec in records:
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
