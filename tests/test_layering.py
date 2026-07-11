"""Layering guard: compute scripts must not import plotters.

Architecture rule 4 (`.claude/rules/architecture.md`): "Compute / Plot / Include
are separate. A compute script produces a table. A plot script reads a table and
produces a figure ... Never mix." The dependency arrow runs compute → plot only,
never back: a `compute_*` module that imports a `plot_*` module is a backward
arrow that couples the analysis layer to the presentation layer.

This standing guard parses every `compute_*.py` module's imports and fails if any
of them import a `plot_*` module. Adherence tier — runs under `make lint`, not the
fast inner loop.

Ticket 0242 severed `compute_clustering_comparison.py`'s import of the two
clustering plotters. `compute_null_separation.py` retains a second, distinct
violation (it imports the analysis helper `build_pre2007_traditions`, which is
misplaced inside `plot_fig_traditions.py`); relocating that helper is separate
work tracked by ticket 0250 and is allowlisted below until then.
"""

import ast
import os

import pytest

pytestmark = pytest.mark.adherence

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO, "scripts")

# Known, pre-existing compute → plot violations awaiting their own relocation
# ticket. Each entry MUST cite the tracking ticket. Remove an entry the moment
# its violation is fixed — see test_no_stale_layering_allowlist.
LAYERING_ALLOWLIST = {
    # compute_null_separation.py imports build_pre2007_traditions() from
    # plot_fig_traditions.py — a misplaced shared analysis helper. Ticket 0250
    # relocates it to a neutral module.
    "compute_null_separation.py": "0250",
}


def _compute_scripts():
    """Top-level `compute_*.py` scripts under scripts/ (archive excluded)."""
    result = []
    for f in os.listdir(SCRIPTS_DIR):
        if f.startswith("compute_") and f.endswith(".py"):
            result.append(f)
    return sorted(result)


def _imported_plot_modules(name):
    """Return the sorted set of `plot_*` module names imported by a script."""
    with open(os.path.join(SCRIPTS_DIR, name)) as fh:
        tree = ast.parse(fh.read(), filename=name)
    hits = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith("plot_"):
                hits.add(mod)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("plot_"):
                    hits.add(alias.name)
    return sorted(hits)


def test_no_compute_imports_plotter():
    """No compute_*.py imports a plot_* module (allowlist excepted)."""
    violators = {}
    for name in _compute_scripts():
        if name in LAYERING_ALLOWLIST:
            continue
        plots = _imported_plot_modules(name)
        if plots:
            violators[name] = plots
    assert not violators, (
        "compute → plot backward arrow (architecture rule 4). "
        "A compute module must not import a plotter:\n"
        + "\n".join(f"  {k} imports {v}" for k, v in sorted(violators.items()))
    )


def test_no_stale_layering_allowlist():
    """Every allowlisted violation still offends — remove it once fixed."""
    stale = [
        name
        for name in LAYERING_ALLOWLIST
        if name in _compute_scripts() and not _imported_plot_modules(name)
    ]
    assert not stale, (
        "These scripts no longer import a plotter — remove them from "
        f"LAYERING_ALLOWLIST: {stale}"
    )
