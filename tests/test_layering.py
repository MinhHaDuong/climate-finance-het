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
clustering plotters. Ticket 0250 severed the second violation by relocating the
shared analysis helper `build_pre2007_traditions` out of `plot_fig_traditions.py`
into the neutral module `_pre2007_traditions.py`, which both the plot and the
compute layer import. The allowlist is now empty.
"""

import ast

import pytest
from _script_discovery import all_script_files

pytestmark = pytest.mark.adherence

# Known, pre-existing compute → plot violations awaiting their own relocation
# ticket. Each entry MUST cite the tracking ticket. Remove an entry the moment
# its violation is fixed — see test_no_stale_layering_allowlist.
LAYERING_ALLOWLIST: dict[str, str] = {}


def _compute_scripts():
    """Every `compute_*.py` script, recursively (archive excluded).

    Routed through the shared recursive enumerator (ticket 0260) so a wave-1
    move of a `compute_*` entry point into `scripts/analysis/` cannot silently
    drop it from this compute↛plot guard. Returns full paths.
    """
    return [p for p in all_script_files() if p.name.startswith("compute_")]


def _imported_plot_modules(path):
    """Return the sorted set of `plot_*` module names imported by a script."""
    with open(path) as fh:
        tree = ast.parse(fh.read(), filename=path.name)
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
    for path in _compute_scripts():
        if path.name in LAYERING_ALLOWLIST:
            continue
        plots = _imported_plot_modules(path)
        if plots:
            violators[path.name] = plots
    assert not violators, (
        "compute → plot backward arrow (architecture rule 4). "
        "A compute module must not import a plotter:\n"
        + "\n".join(f"  {k} imports {v}" for k, v in sorted(violators.items()))
    )


def test_no_stale_layering_allowlist():
    """Every allowlisted violation still offends — remove it once fixed."""
    by_name = {p.name: p for p in _compute_scripts()}
    stale = [
        name
        for name in LAYERING_ALLOWLIST
        if name in by_name and not _imported_plot_modules(by_name[name])
    ]
    assert not stale, (
        "These scripts no longer import a plotter — remove them from "
        f"LAYERING_ALLOWLIST: {stale}"
    )
