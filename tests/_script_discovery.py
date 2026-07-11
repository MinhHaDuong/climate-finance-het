"""Shared `scripts/` discovery for the script-enumeration guards (ticket 0260).

One place enumerates every active pipeline script, recursively, so a future
`scripts/` reorg (epic 0240 moves 132 entry points into `scripts/figures/`,
`scripts/harvest/`, `scripts/analysis/`, `scripts/qa/`) updates a single list and
no guard can silently narrow its coverage. This closes the same class defect
that ticket 0248 fixed for `.mk` discovery: several guards each hand-rolled a
*flat* `os.listdir(SCRIPTS_DIR)` / `glob("*.py")` union, so a moved file drops
out of a guard's coverage and the test keeps passing — over fewer files, not
because the contract still holds.

`<repo>` is resolved from this file's own location, so the helper is correct in
any worktree.

Exclusions: `scripts/archive*/` (frozen, superseded experimental scripts, not
active code and not part of the wave-1 moves) and `__pycache__/`.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _is_excluded(rel_parts: tuple[str, ...]) -> bool:
    """A path is excluded when any directory component is archive-like or a cache.

    `archive/` and `archive_traditions/` both hold frozen scripts preserved for
    reference; neither is active code nor a wave-1 move target, so the active-
    script guards must not see them. `__pycache__/` holds compiled bytecode.
    """
    for part in rel_parts[:-1]:  # directory components only
        if part.startswith("archive") or part == "__pycache__":
            return True
    return False


def all_script_files() -> list[Path]:
    """Every active `scripts/**/*.py`, recursively, sorted for stable test IDs.

    Full paths. Covers the flat `scripts/` root and every phase subdirectory the
    reorg introduces (`figures/`, `harvest/`, `analysis/`, `qa/`). Excludes
    `scripts/archive*/` and `__pycache__/`. This is the ONE sanctioned script
    enumeration — every guard routes through it (or a derived shape below) so a
    relocation can never narrow a guard's file set.
    """
    files = [
        p
        for p in SCRIPTS_DIR.rglob("*.py")
        if not _is_excluded(p.relative_to(SCRIPTS_DIR).parts)
    ]
    return sorted(files)


def all_script_basenames() -> list[str]:
    """Basenames (e.g. ``plot_fig1_bars.py``) of every active script, sorted."""
    return sorted(p.name for p in all_script_files())


def all_script_stems() -> list[str]:
    """Module stems (e.g. ``plot_fig1_bars``) of every active script, sorted."""
    return sorted(p.stem for p in all_script_files())


def script_paths_by_stem() -> dict[str, Path]:
    """Map module stem -> path, for guards that resolve a script by import name.

    A moved file keeps its stem (imports are by basename), so this map lets a
    guard read the file wherever it now lives without assuming the flat root.
    """
    return {p.stem: p for p in all_script_files()}
