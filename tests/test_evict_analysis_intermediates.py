"""Ticket 0208 — analysis intermediates evicted from content/tables/.

`content/tables/` conflates small byte-stable *writing deliverables* with large
*analysis intermediates* consumed only by other Phase-2 scripts. This guard
pins the eviction of the heavy intermediates to an analysis-side derived dir:
no producer/consumer target or script may resolve them back under
`content/tables/`.

Mirrors the arch-compliance grep-ratchet style: a stale hardcoded path is
lexically stable, so a line-level scan is a durable regression guard.
"""

import glob
import os

import pytest

# Grep-ratchet guard — belongs to the mechanical adherence gate (`pytest -m adherence`).
pytestmark = pytest.mark.adherence

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

# The heavy intermediates evicted by ticket 0208.
EVICTED = [
    "tab_lexical_tfidf.csv",
    "tab_pole_papers.csv",
    "tab_pole_papers_core.csv",
    "qa_type_report.csv",
]

def _bad_patterns(basename):
    """Path constructions that resolve `basename` under content/tables/.

    Anchored on the basename so a legit content/tables/ deliverable elsewhere
    on the same line (e.g. a tab_venues.md target that *reads* the evicted
    file from $(DERIVED)) does not trip the guard.
    """
    return [
        f"content/tables/{basename}",          # literal path (Make + docstrings)
        f'TABLES_DIR, "{basename}"',            # os.path.join(TABLES_DIR, "…")
        f"TABLES_DIR, '{basename}'",
        f'"tables", "{basename}"',              # os.path.join(BASE_DIR, "content", "tables", "…")
        f"'tables', '{basename}'",
    ]


def _makefiles():
    paths = [os.path.join(PROJECT_ROOT, "Makefile")]
    paths += glob.glob(os.path.join(PROJECT_ROOT, "*.mk"))
    return paths


def _scripts():
    # Top-level scripts only — archived/ variants are frozen and not built.
    return glob.glob(os.path.join(SCRIPTS_DIR, "*.py"))


def _offending_lines(path, basename):
    """Lines in `path` that place `basename` under a content/tables marker.

    The derived-dir constant `DERIVED_TABLES_DIR` is the *correct* destination,
    so its occurrences are masked before matching (it superstring-contains the
    `TABLES_DIR` marker).
    """
    patterns = _bad_patterns(basename)
    hits = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            probe = line.replace("DERIVED_TABLES_DIR", "")
            if any(pat in probe for pat in patterns):
                hits.append((i, line.rstrip()))
    return hits


def test_makefiles_do_not_place_evicted_under_content_tables():
    offenders = []
    for path in _makefiles():
        for basename in EVICTED:
            for lineno, line in _offending_lines(path, basename):
                offenders.append(f"{os.path.relpath(path, PROJECT_ROOT)}:{lineno}: {line}")
    assert not offenders, (
        "Evicted intermediates still resolve under content/tables/ in Make:\n"
        + "\n".join(offenders)
    )


def test_scripts_do_not_place_evicted_under_content_tables():
    offenders = []
    for path in _scripts():
        for basename in EVICTED:
            for lineno, line in _offending_lines(path, basename):
                offenders.append(f"{os.path.relpath(path, PROJECT_ROOT)}:{lineno}: {line}")
    assert not offenders, (
        "Evicted intermediates still resolve under content/tables/ in scripts:\n"
        + "\n".join(offenders)
    )
