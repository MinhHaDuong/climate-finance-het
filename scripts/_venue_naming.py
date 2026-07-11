"""Venue-name canonicalization helpers: shared library module.

Maps a raw venue string to its canonical name, its type
(journal / working-paper / report / repository / missing), and its
institutional owner. These are pure string-classification helpers with no I/O:
`summarize_core_venues.py` (the entry point that renders the core-venue tables),
`compute_venue_concentration.py`, and `export_core_venues_markdown.py` all reuse
them.

It lives in a neutral flat `_`-module so the entry point can move by phase while
the shared helpers stay on the flat library surface (ticket 0254; the 0250
pattern). The rules and function bodies are relocated verbatim from
`summarize_core_venues.py` — output is byte-identical by construction.
"""

import re

# Each entry is (matcher, canonical_name).
# matcher is either a substring str or a callable(low: str) -> bool.
# More specific patterns must precede more general ones within the same family.
_VENUE_RULES: list[tuple] = [
    # Exact-match edge case
    (lambda s: s == "mf policy paper", "IMF Policy Paper"),
    # World Bank — most specific first
    (lambda s: "world bank" in s and ("ebook" in s or "publication" in s or "washington, dc" in s),
     "World Bank eBooks"),
    ("world bank policy research working paper", "World Bank Policy Research Working Paper"),
    ("world bank", "World Bank"),
    # OECD — most specific first
    ("oecd/iea climate change expert group papers", "OECD/IEA Climate Change Expert Group Papers"),
    (lambda s: "oecd" in s and "working paper" in s, "OECD Working Papers"),
    (lambda s: "oecd" in s and "paper" in s, "OECD Papers"),
    (lambda s: s.startswith("oecd"), "OECD"),
    # IMF — most specific first
    ("imf working paper", "IMF Working Paper"),
    ("imf staff climate notes", "IMF Staff Climate Notes"),
    ("imf staff country reports", "IMF Staff Country Reports"),
    (lambda s: "imf" in s and ("discussion note" in s or "staff" in s), "IMF Staff Notes"),
    ("imf", "IMF"),
    # Repositories and indexes
    ("ssrn", "SSRN Electronic Journal"),
    ("repec", "RePEc"),
    ("depositonce", "DepositOnce"),
    ("zenodo", "Zenodo"),
    ("figshare", "Figshare"),
    ("preprints", "Preprints"),
]


def canonical_venue(name):
    v = str(name or "").strip()
    low = v.lower()
    if not low:
        return "[missing]"
    for matcher, canonical in _VENUE_RULES:
        matched = matcher(low) if callable(matcher) else (matcher in low)
        if matched:
            return canonical
    return v


def venue_type(name):
    low = str(name or "").lower()
    if not low or low == "[missing]":
        return "missing"

    if low == "climate finance and the usd 100 billion goal":
        return "report_series"

    wp_pattern = re.compile(r"working paper|working papers|discussion paper|policy research working paper|\bwp\b")
    report_pattern = re.compile(
        r"ebook|ebooks|report|reports|publications|world bank|oecd|imf|unfccc|climate policy initiative|\bcpi\b"
    )
    non_journal_pattern = re.compile(
        r"ssrn|repec|zenodo|figshare|preprints|open science framework|depositonce|research online"
    )

    if wp_pattern.search(low):
        return "working_paper_series"
    if report_pattern.search(low):
        return "report_series"
    if non_journal_pattern.search(low):
        return "repository_or_index"
    return "journal"


def institution_group(name):
    low = str(name or "").lower()
    if "oecd" in low:
        return "OECD"
    if "world bank" in low:
        return "World Bank"
    if "imf" in low:
        return "IMF"
    return "Other/None"
