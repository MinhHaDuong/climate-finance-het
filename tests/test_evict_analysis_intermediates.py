"""Tickets 0208 + 0218 + 0231 — analysis intermediates evicted from deliverables/_shared/tables/.

`deliverables/_shared/tables/` conflates small byte-stable *writing deliverables* (the `.md`
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
   ratchet. Every `deliverables/_shared/tables/tab_*.csv` that appears as a Make **target**
   in the TOP-LEVEL `Makefile` must be a declared deliverable (a
   `!deliverables/_shared/tables/...` negation in `.gitignore`). A brand-new `tab_*.csv`
   intermediate landing in `deliverables/_shared/tables/` — even one nobody added to
   `EVICTED` — fails here.

   The ratchet is deliberately scoped to the `tab_*.csv` naming class (ticket
   0218 Test spec). The `*.json` intermediates it also evicts
   (`cluster_labels*.json`) stay covered by the fixed `EVICTED` literal-scan
   above; other deliverables/_shared/tables `*_report.json` QA outputs
   (`qa_citations_report.json`, `multilingual_report.json`) are a distinct
   class, out of 0218's scope, and are neither flagged nor moved here.

Scope (ticket 0231): the class ratchet scans the top-level `Makefile` AND every
sub-Makefile under `scripts/analysis/` (`divergence.mk`, `zoo-figures.mk`,
`multilayer-detection.mk`, `venues.mk`, `separation.mk`; relocated by 0239).
Those subsystems route their `tab_*` targets through a per-subsystem directory
variable (`DIV_TABLES`, `ZOO_TABLES`, `COMP_TABLES`, `VENUE_TABLE`), so a target
line reads `$(DIV_TABLES)/tab_div_$(m).csv`, not a literal `deliverables/_shared/tables/...`
path. The ratchet therefore resolves Make variable references before matching:
it expands `$(VAR)` from the assignments collected across all makefiles, then
flags any target whose *resolved* path lands under `deliverables/_shared/tables/`. Flipping a
`*_TABLES` variable back to `deliverables/_shared/tables` re-reddens the whole subsystem —
which is the regression this guard exists to catch (0218 evicted the top-level
literal set; 0231 evicted the variable-routed sub-Makefile class).
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
    """Path constructions that resolve `basename` under deliverables/_shared/tables/.

    Anchored on the basename so a legit deliverables/_shared/tables/ deliverable elsewhere
    on the same line (e.g. a tab_venues.md target that *reads* the evicted
    file from $(DERIVED)) does not trip the guard.
    """
    return [
        f"deliverables/_shared/tables/{basename}",          # literal path (Make + docstrings)
        f'TABLES_DIR, "{basename}"',            # os.path.join(TABLES_DIR, "…")
        f"TABLES_DIR, '{basename}'",
        f'"tables", "{basename}"',              # os.path.join(BASE_DIR, "deliverables", "_shared", "tables", "…")
        f"'tables', '{basename}'",
    ]


def _makefiles():
    paths = [os.path.join(PROJECT_ROOT, "Makefile")]
    paths += glob.glob(os.path.join(PROJECT_ROOT, "*.mk"))
    # Phase-2 analysis concern .mk moved under scripts/analysis/ (ticket 0239);
    # keep scanning them so the eviction guard still covers the moved fragments.
    paths += glob.glob(os.path.join(SCRIPTS_DIR, "analysis", "*.mk"))
    return paths


def _scripts():
    # Top-level scripts only — archived/ variants are frozen and not built.
    return glob.glob(os.path.join(SCRIPTS_DIR, "*.py"))


def _offending_lines(path, basename):
    """Lines in `path` that place `basename` under a deliverables/_shared/tables marker.

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
        "Evicted intermediates still resolve under deliverables/_shared/tables/ in Make:\n"
        + "\n".join(offenders)
    )


def test_scripts_do_not_place_evicted_under_content_tables():
    offenders = []
    for path in _scripts():
        for basename in EVICTED:
            for lineno, line in _offending_lines(path, basename):
                offenders.append(f"{os.path.relpath(path, PROJECT_ROOT)}:{lineno}: {line}")
    assert not offenders, (
        "Evicted intermediates still resolve under deliverables/_shared/tables/ in scripts:\n"
        + "\n".join(offenders)
    )


# --- Class ratchet (ticket 0218) -------------------------------------------

# The intermediate naming class the ratchet guards: deliverables/_shared/tables/tab_*.csv
# (0218 Test spec). json intermediates ride the fixed EVICTED literal-scan.
_CONTENT_TABLE_DATA = re.compile(r"deliverables/_shared/tables/(tab_[\w.-]*\.csv)")


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


_ASSIGN = re.compile(r"^\s*([A-Za-z_][\w]*)\s*[:?]?=\s*(.*?)\s*$")
_VARREF = re.compile(r"\$[({]([A-Za-z_][\w]*)[)}]")


def _variable_map(paths):
    """Collect `NAME = value` / `:=` / `?=` assignments across all makefiles.

    Make variables are global across `-include`d sub-Makefiles, so the map is
    built from the union. Later assignments win (matches Make's last-wins for
    the simple `:=`/`=` used here). Recipe lines (leading TAB) are skipped.
    """
    varmap = {}
    for path in paths:
        for line in _logical_lines(path):
            if line.startswith("\t") or line.lstrip().startswith("#"):
                continue
            m = _ASSIGN.match(line)
            if m and ":" not in m.group(2).split("#", 1)[0]:
                # Guard against matching a rule like `target: dep` as NAME=value:
                # a real assignment's RHS holds no rule separator. `:=`/`?=` are
                # handled by the optional `[:?]?=` in the pattern.
                varmap[m.group(1)] = m.group(2)
    return varmap


def _resolve(token, varmap, _depth=0):
    """Expand `$(VAR)`/`${VAR}` references in `token` using `varmap`.

    Bounded recursion; unknown or loop variables (e.g. a `$(m)` foreach index)
    are left verbatim, which is sufficient — we only need the *directory* prefix
    to resolve to decide whether a target lands under deliverables/_shared/tables/.
    """
    if _depth > 10 or "$" not in token:
        return token
    return _VARREF.sub(
        lambda mo: _resolve(varmap.get(mo.group(1), mo.group(0)), varmap, _depth + 1),
        token,
    )


def _content_table_targets(makefile_path, varmap):
    """Basenames of deliverables/_shared/tables/tab_*.csv appearing as a Make target.

    The *target* is the text left of the `:` / `&:` rule separator on a
    non-recipe logical line; prerequisites and recipe arguments are ignored.
    Each target token is variable-expanded first, so a subsystem target written
    as `$(DIV_TABLES)/tab_div_$(m).csv` is judged by where `$(DIV_TABLES)`
    resolves, not by its literal text.
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
            resolved = _resolve(token, varmap)
            m = _CONTENT_TABLE_DATA.search(resolved)
            if m:
                basenames.add(os.path.basename(m.group(1)))
    return basenames


def _gitignore_deliverable_whitelist():
    """deliverables/_shared/tables/*.csv basenames negated (kept) in .gitignore."""
    whitelisted = set()
    path = os.path.join(PROJECT_ROOT, ".gitignore")
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("!deliverables/_shared/tables/"):
                base = os.path.basename(line[len("!") :])
                if base.endswith(".csv"):
                    whitelisted.add(base)
    return whitelisted


def test_content_tables_targets_are_declared_deliverables():
    """No un-whitelisted tab_*.csv intermediate may be a deliverables/_shared/tables/ target.

    Every `deliverables/_shared/tables/tab_*.csv` produced by the top-level `Makefile` or any
    sub-Makefile must be a declared deliverable (a `!deliverables/_shared/tables/...` negation
    in `.gitignore`). Anything else is a Phase-2 intermediate that belongs under
    `$(DERIVED)` (data/derived/tables). Sub-Makefile targets routed through a
    `*_TABLES` directory variable are variable-expanded before the check, so the
    verdict follows where the variable resolves.
    """
    makefiles = _makefiles()
    varmap = _variable_map(makefiles)
    targets = set()
    for path in makefiles:
        targets |= _content_table_targets(path, varmap)
    whitelist = _gitignore_deliverable_whitelist()
    offenders = sorted(targets - whitelist)
    assert not offenders, (
        "deliverables/_shared/tables/ data-table targets that are neither a declared "
        "deliverable (.gitignore negation) nor evicted to $(DERIVED):\n"
        + "\n".join(offenders)
        + "\n\nEither move the producer output to $(DERIVED) (intermediate) or "
        "add a `!deliverables/_shared/tables/<name>` negation to .gitignore (deliverable)."
    )
