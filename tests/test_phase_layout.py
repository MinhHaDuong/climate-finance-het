"""Ticket 0219 — layout mirrors dataflow phase: no Phase-2 output under data/catalogs/.

`data/` is split by pipeline phase: `data/catalogs/` (+ pool/exports/syllabi) is
Phase-1 corpus (DVC-managed), `data/derived/` is Phase-2 derived data (gitignored,
regenerable). Two Phase-2 outputs used to leak into the Phase-1 corpus dir:
`semantic_clusters.csv` (analyze_embeddings.py) and `het_mostcited_50.csv`
(build_het_core.py). This guard pins them out of `data/catalogs/` so the layout
keeps mirroring the phase — a re-introduced `$(DATA_DIR)/...` or
`os.path.join(CATALOGS_DIR, "<name>")` for these basenames fails the test.

Grep-ratchet style (like ticket 0208's guard): a stale hardcoded path is lexically
stable, so a line-level scan is a durable regression guard.
"""

import glob
import os

import pytest

# Grep-ratchet guard — belongs to the mechanical adherence gate (`pytest -m adherence`).
pytestmark = pytest.mark.adherence

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
MAKEFILE = os.path.join(PROJECT_ROOT, "Makefile")

# Phase-2 outputs evicted from data/catalogs/ by ticket 0219.
PHASE2_OUTPUTS = [
    "semantic_clusters.csv",
    "het_mostcited_50.csv",
]


def _bad_patterns(basename):
    """Path constructions that resolve `basename` under the Phase-1 corpus dir.

    Anchored on the basename so a legit Phase-1 read on the same line (e.g.
    refined_works.csv from CATALOGS_DIR) does not trip the guard.
    """
    return [
        f"data/catalogs/{basename}",                 # literal repo path (Make + docstrings)
        f"$DATA/catalogs/{basename}",                # $DATA/catalogs/<name> docstrings
        f'CATALOGS_DIR, "{basename}"',               # os.path.join(CATALOGS_DIR, name)
        f"CATALOGS_DIR, '{basename}'",
        f"$(DATA_DIR)/{basename}",                   # Makefile constant under Phase 1
    ]
    # Note: bare `catalogs/<name>` is intentionally NOT matched — it would catch the
    # scoped-out smoke fixture `tests/fixtures/smoke/catalogs/<name>` (a self-contained
    # test mirror, ticket 0219 § Scope out), not the production Phase-1 corpus dir.


def _scan(path):
    """Return list of (lineno, line) in `path` matching any bad pattern."""
    hits = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            for basename in PHASE2_OUTPUTS:
                if any(pat in line for pat in _bad_patterns(basename)):
                    hits.append((i, line.rstrip()))
                    break
    return hits


def _production_files():
    """Makefile + scripts/*.py. Excludes tests/fixtures/ (self-contained mirrors)."""
    files = [MAKEFILE]
    files += glob.glob(os.path.join(SCRIPTS_DIR, "*.py"))
    return files


def test_no_phase2_output_under_catalogs():
    offenders = {}
    for path in _production_files():
        hits = _scan(path)
        if hits:
            offenders[os.path.relpath(path, PROJECT_ROOT)] = hits
    assert not offenders, (
        "Phase-2 outputs must live under data/derived/, not data/catalogs/ "
        "(ticket 0219). Offending lines:\n"
        + "\n".join(
            f"  {f}:{ln}: {txt}"
            for f, hits in offenders.items()
            for ln, txt in hits
        )
    )
