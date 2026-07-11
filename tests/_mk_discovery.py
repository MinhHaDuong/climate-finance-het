"""Shared `.mk` discovery for the build-guard tests (ticket 0248).

One place enumerates every Makefile fragment the pipeline `-include`s, so a
future `.mk` relocation updates a single list and no guard can silently narrow
its coverage. This closes the class defect that ticket 0239 surfaced: five
guards each hand-rolled a fixed-directory glob union that drifted apart when
fragments moved.

`<repo>` is resolved from this file's own location, so the helper is correct in
any worktree.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def mk_fragments() -> list[Path]:
    """Every `-include`d build fragment, sorted for stable parametrized test IDs.

    Covers the three homes a `.mk` fragment can live in:
      - repo-root ``*.mk`` (``paths.mk``, the shared variable interface);
      - ``scripts/analysis/*.mk`` (Phase-2 analysis concerns, relocated by 0239);
      - ``deliverables/*/*.mk`` (per-deliverable Phase-3 render fragments).

    Excludes the top-level ``Makefile`` — use :func:`all_makefiles` for that.
    """
    fragments = list(REPO_ROOT.glob("*.mk"))
    fragments += list((REPO_ROOT / "scripts" / "analysis").glob("*.mk"))
    fragments += list((REPO_ROOT / "deliverables").glob("*/*.mk"))
    return sorted(fragments)


def all_makefiles(include_main: bool = True) -> list[Path]:
    """Every Makefile the build reads: the top-level ``Makefile`` plus fragments.

    Pass ``include_main=False`` for a guard that asserts a property of the
    ``-include``d *fragments* alone — e.g. single-phase purity, since the main
    ``Makefile`` legitimately wires both render and compute concerns.
    """
    files = mk_fragments()
    if include_main:
        files = [REPO_ROOT / "Makefile"] + files
    return files
