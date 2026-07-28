"""The genealogy band scheme has one definition, and every consumer reads it.

`N_COMMUNITIES`, `BAND_NAMES` and `BAND_COLORS_RGB` decide which colour means
which lineage band. They were hand-copied into three modules — the model
(`analyze_genealogy.py`) and both renderers — each carrying a "must match"
comment and no way to enforce it. Re-theming one renderer left
`fig_genealogy.png` and `fig_genealogy.html` disagreeing at exit 0, with no
exception and no missing target (ticket 0571).

The fix is `scripts/_band_scheme.py`, the neutral-module pattern already used
by `_tradition_style.py` (0250/0254/0286): the definition lives at the
`scripts/` root, the one directory every subpackage sees on `PYTHONPATH`.

This guard is a source-inspection check rather than a value comparison,
because once the copies are gone there are no second values left to compare
against. What can regress is a module *re-introducing* a literal, so that is
what the test looks for.
"""

import ast
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCRIPTS = BASE / "scripts"

#: The names the shared module owns. A consumer may bind them by import, never
#: by assignment.
BAND_SCHEME_NAMES = frozenset({"N_COMMUNITIES", "BAND_NAMES", "BAND_COLORS_RGB"})

#: Every module that draws or labels the lineage bands.
CONSUMERS = (
    SCRIPTS / "analysis" / "analyze_genealogy.py",
    SCRIPTS / "figures" / "plot_genealogy.py",
    SCRIPTS / "figures" / "plot_genealogy_html.py",
)


def _module_level_assignments(tree: ast.Module) -> set[str]:
    """Names bound by a module-level assignment (the shape a copy takes)."""
    bound = set()
    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                bound.add(target.id)
    return bound


def _names_imported_from(tree: ast.Module, module: str) -> set[str]:
    return {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == module
        for alias in node.names
    }


def test_band_scheme_module_defines_the_scheme():
    """`scripts/_band_scheme.py` is the single definition."""
    tree = ast.parse((SCRIPTS / "_band_scheme.py").read_text())
    defined = _module_level_assignments(tree)
    missing = BAND_SCHEME_NAMES - defined
    assert not missing, f"_band_scheme.py must define {sorted(missing)}"


def test_no_consumer_redefines_the_band_scheme():
    """A module that re-assigns one of the names has forked the scheme."""
    offenders = {}
    for path in CONSUMERS:
        tree = ast.parse(path.read_text())
        redefined = _module_level_assignments(tree) & BAND_SCHEME_NAMES
        if redefined:
            offenders[path.name] = sorted(redefined)
    assert not offenders, (
        "band-scheme constants must be imported from _band_scheme, not "
        f"redefined: {offenders}"
    )


def test_every_consumer_imports_the_names_it_uses():
    """Using a band-scheme name without importing it is the same fork, later.

    A module that neither defines nor imports the name would raise NameError,
    so this catches the intermediate state where one renderer is migrated and
    another still has its own copy under a different alias.
    """
    for path in CONSUMERS:
        source = path.read_text()
        tree = ast.parse(source)
        imported = _names_imported_from(tree, "_band_scheme")
        used = {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and node.id in BAND_SCHEME_NAMES
        }
        missing = used - imported
        assert not missing, (
            f"{path.name} uses {sorted(missing)} without importing from "
            "_band_scheme"
        )


def test_no_module_keeps_the_retired_community_names_alias():
    """`COMMUNITY_NAMES` was the renderers' local name for `BAND_NAMES`.

    Two names for one mapping is how the copies survived review; the alias is
    retired so a future reader cannot re-fork it by re-introducing a second
    spelling.
    """
    offenders = [
        path.name
        for path in CONSUMERS
        if "COMMUNITY_NAMES" in path.read_text()
    ]
    assert not offenders, (
        f"COMMUNITY_NAMES is retired in favour of BAND_NAMES: {offenders}"
    )
