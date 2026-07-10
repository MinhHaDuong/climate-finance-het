"""Tickets 0208 + 0218 — analysis intermediates evicted from content/tables/.

`content/tables/` conflates small byte-stable *writing deliverables* (the `.md`
`{{< include >}}` fragments and a few pinned `.csv`) with *analysis
intermediates* consumed only by other Phase-2 scripts. Ticket 0208 evicted the
four heavy ones; ticket 0218 finishes the class and adds a standing guard so a
re-introduced intermediate is caught.

Two guards, complementary:

1. `test_*_do_not_place_evicted_under_content_tables` — a lexical grep-ratchet
   over the fixed `EVICTED` basename list (0208 + 0218). A stale hardcoded path
   is lexically stable, so a line-level scan is a durable regression guard for
   the *known* evictees (producer, consumer, or docstring reference).

2. `test_content_tables_targets_are_declared_deliverables` — the *class*
   ratchet. Every `content/tables/tab_*.csv` that appears as a Make **target**
   in the TOP-LEVEL `Makefile` must be a declared deliverable (a
   `!content/tables/...` negation in `.gitignore`). A brand-new `tab_*.csv`
   intermediate landing in `content/tables/` — even one nobody added to
   `EVICTED` — fails here.

   The ratchet is deliberately scoped to the `tab_*.csv` naming class (ticket
   0218 Test spec). The `*.json` intermediates it also evicts
   (`cluster_labels*.json`) stay covered by the fixed `EVICTED` literal-scan
   above; other content/tables `*_report.json` QA outputs
   (`qa_citations_report.json`, `multilingual_report.json`) are a distinct
   class, out of 0218's scope, and are neither flagged nor moved here.

Scope boundary (ticket 0218, scoping finding 2): the class ratchet scans the
top-level `Makefile` ONLY. The sub-Makefiles (`divergence.mk`, `zoo.mk`,
`multilayer-detection.mk`, `venues.mk`) route ~70 more `tab_*` targets to
`content/tables/` via their own `*_TABLES` dir variable; scanning them would go
RED on all ~70 pre-existing targets — a false-positive storm, not a regression.
Widening the guard to those subsystems is ticket 0231 (blocked by this one).
"""

import glob
import os
import re

import pytest

# Grep-ratchet guard — belongs to the mechanical adherence gate (`pytest -m adherence`).
pytestmark = pytest.mark.adherence

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

# Intermediates evicted to $(DERIVED) — 0208 (heavy four) + 0218 (the residual class).
EVICTED = [
    # 0208
    "tab_lexical_tfidf.csv",
    "tab_pole_papers.csv",
    "tab_pole_papers_core.csv",
    "qa_type_report.csv",
    # 0218
    "tab_bimodality.csv",
    "tab_bimodality_core.csv",
    "tab_axis_detection.csv",
    "tab_axis_detection_core.csv",
    "tab_breakpoints.csv",
    "tab_breakpoints_core.csv",
    "tab_breakpoints_censor2.csv",
    "tab_breakpoint_robustness.csv",
    "tab_breakpoint_robustness_core.csv",
    "tab_breakpoint_robustness_censor2.csv",
    "tab_alluvial.csv",
    "tab_alluvial_core.csv",
    "cluster_labels.json",
    "cluster_labels_core.json",
    "tab_core_shares.csv",
    "tab_lineages.csv",
    "tab_k_sensitivity.csv",
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


# --- Class ratchet (ticket 0218) -------------------------------------------

# The intermediate naming class the ratchet guards: content/tables/tab_*.csv
# (0218 Test spec). json intermediates ride the fixed EVICTED literal-scan.
_CONTENT_TABLE_DATA = re.compile(r"content/tables/(tab_[\w.-]*\.csv)")


def _logical_lines(path):
    """Yield Makefile logical lines, joining backslash continuations.

    Grouped targets span several physical lines (`a.csv b.json \\` then
    `c.csv &:`), so the `:` / `&:` rule separator is only visible after the
    join. Recipe lines (leading TAB) are preserved as-is and skipped by callers.
    """
    out, buf = [], ""
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if line.endswith("\\"):
                buf += line[:-1] + " "
            else:
                out.append(buf + line)
                buf = ""
    if buf:
        out.append(buf)
    return out


def _content_table_targets(makefile_path):
    """Basenames of content/tables/tab_*.csv appearing as a Make target.

    The *target* is the text left of the `:` / `&:` rule separator on a
    non-recipe logical line; prerequisites and recipe arguments are ignored.
    """
    basenames = set()
    for line in _logical_lines(makefile_path):
        if line.startswith("\t"):          # recipe line
            continue
        sep = "&:" if "&:" in line else (":" if ":" in line else None)
        if sep is None:
            continue
        lhs = line.split(sep, 1)[0]
        if ":=" in line and sep == ":":    # variable assignment, not a rule
            continue
        for token in lhs.split():
            m = _CONTENT_TABLE_DATA.search(token)
            if m:
                basenames.add(os.path.basename(m.group(1)))
    return basenames


def _gitignore_deliverable_whitelist():
    """content/tables/*.csv basenames negated (kept) in .gitignore."""
    whitelisted = set()
    path = os.path.join(PROJECT_ROOT, ".gitignore")
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("!content/tables/"):
                base = os.path.basename(line[len("!") :])
                if base.endswith(".csv"):
                    whitelisted.add(base)
    return whitelisted


def test_content_tables_targets_are_declared_deliverables():
    """No un-whitelisted tab_*.csv intermediate may be a content/tables/ target.

    Every `content/tables/tab_*.csv` produced by the top-level Makefile must be
    a declared deliverable (a `!content/tables/...` negation in `.gitignore`).
    Anything else is a Phase-2 intermediate that belongs under `$(DERIVED)`
    (data/derived/tables).
    """
    makefile = os.path.join(PROJECT_ROOT, "Makefile")
    targets = _content_table_targets(makefile)
    whitelist = _gitignore_deliverable_whitelist()
    offenders = sorted(targets - whitelist)
    assert not offenders, (
        "content/tables/ data-table targets that are neither a declared "
        "deliverable (.gitignore negation) nor evicted to $(DERIVED):\n"
        + "\n".join(offenders)
        + "\n\nEither move the producer output to $(DERIVED) (intermediate) or "
        "add a `!content/tables/<name>` negation to .gitignore (deliverable)."
    )
