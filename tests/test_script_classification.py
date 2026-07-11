"""Entry-point / library classification gate (ticket 0254).

The `scripts/` reorg (epic 0240) moves only **Tier-3 pure entry points** into
`scripts/<phase>/`; **Tier-2 library modules** (imported by another script) stay
flat at `scripts/` root. The load-bearing invariant the wave-1 moves (0255–0258)
rely on: **no Tier-3 file is imported by another top-level script** — i.e. the
moving set is import-leaf on the flat library surface. Move a file that another
module imports by flat name and the importer's `from <name> import …` breaks.

This test pins the flat library surface. It parses every top-level `scripts/*.py`
for cross-script imports and asserts that every imported module is either a
`_`-private module or one of the two explicit Tier-2 allowlists below. A new
`from <entry_point> import …` between two scripts fails the test, forcing the
author to resolve the dual-role hazard first (extract the helper to a neutral
`_`-module, the 0250/0254 pattern, or reclassify the file Tier-2 here) — exactly
the contract `docs/repo-layout.md` § "Definitive Tier-2 / Tier-3 classification"
publishes for the move tickets.

Adherence tier — runs under `make lint`, not the fast inner loop.
"""

import ast
import os

import pytest

pytestmark = pytest.mark.adherence

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO, "scripts")

# Tier-2 named libraries (no __main__; imported as a library surface).
NAMED_LIBRARIES = {
    "clustering_methods", "filter_flags", "filter_flags_llm", "openalex_pool",
    "pipeline_io", "pipeline_loaders", "pipeline_progress", "pipeline_text",
    "plot_style", "qa_near_duplicates", "schemas", "script_io_args",
    "syllabi_config", "syllabi_crossref", "syllabi_harvest", "syllabi_io",
    "syllabi_process", "utils",
}

# Dual-role files reclassified Tier-2: they carry a thin main() but are genuinely
# reused computational libraries (extraction would fracture a tight cluster).
# Each stays flat; see docs/repo-layout.md § "Dual-role reclassified Tier-2".
RECLASSIFIED_DUAL_ROLE = {
    "compute_divergence",          # METHODS dispatch registry (rule 8)
    "compute_null_model",          # permutation drivers
    "compute_divergence_bootstrap",  # divergence-family cluster
    "compute_changepoints",        # convergence computation reused by compute_convergence
    "corpus_merge_citations",      # merge_citations reused by the cache-migration one-off
    "enrich_dois",                 # find_doi cached-lookup API reused by syllabi_process
}

# The full flat library surface = private `_` modules (matched by prefix) plus
# these named modules. Anything else imported by another script is a Tier-3
# entry point leaking a helper — a hazard the move tickets cannot absorb.
NAMED_FLAT = NAMED_LIBRARIES | RECLASSIFIED_DUAL_ROLE


def _top_modules():
    return sorted(
        f[:-3] for f in os.listdir(SCRIPTS_DIR) if f.endswith(".py")
    )


def _script_imports(name):
    """Top-level module names imported by scripts/<name>.py."""
    with open(os.path.join(SCRIPTS_DIR, name + ".py")) as fh:
        tree = ast.parse(fh.read(), filename=name + ".py")
    hits = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                hits.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                hits.add(alias.name.split(".")[0])
    return hits


def _imported_by_script():
    """Map: top-level module -> set of top-level scripts that import it."""
    modules = set(_top_modules())
    importers = {}
    for name in sorted(modules):
        for m in _script_imports(name):
            if m in modules and m != name:
                importers.setdefault(m, set()).add(name)
    return importers


def test_no_tier3_entry_point_is_imported():
    """Every script imported by another script is on the flat Tier-2 surface."""
    importers = _imported_by_script()
    violations = {
        m: sorted(who)
        for m, who in importers.items()
        if not m.startswith("_") and m not in NAMED_FLAT
    }
    assert not violations, (
        "These entry points are imported by another script but are NOT on the "
        "flat Tier-2 library surface — a dual-role hazard the wave-1 moves "
        "(0255–0258) cannot absorb. Resolve each: extract the leaked helper into "
        "a neutral `_`-module (0250/0254 pattern) and repoint the importer, or "
        "reclassify the file into RECLASSIFIED_DUAL_ROLE here (and "
        "docs/repo-layout.md):\n"
        + "\n".join(f"  {m} imported by {who}" for m, who in sorted(violations.items()))
    )


def test_no_stale_named_flat_allowlist():
    """Every named Tier-2 entry actually is imported by some script."""
    importers = _imported_by_script()
    stale = sorted(m for m in NAMED_FLAT if m not in importers)
    assert not stale, (
        "These modules are on the NAMED_FLAT allowlist but no script imports "
        f"them — remove them (or the file was deleted/renamed): {stale}"
    )
