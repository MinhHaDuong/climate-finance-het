"""Meta-guard — no test may hand-roll a flat `scripts/` enumeration (ticket 0260).

Several script guards used to each `os.listdir(SCRIPTS_DIR)` or `glob("*.py")`
the flat `scripts/` root to enumerate the pipeline's entry points. Epic 0240
moves ~132 entry points into phase subdirectories (`scripts/figures/`,
`scripts/harvest/`, `scripts/analysis/`, `scripts/qa/`); under a flat glob a
moved file silently drops out of a guard's coverage and the test keeps passing —
over fewer files, not because the contract still holds.

The class fix is one shared discovery helper, `tests/_script_discovery.py`
(recursive `scripts/**/*.py`). This guard is the standing regression test for
the class: it fails if any test file outside the helper hand-rolls a *flat*
script enumeration (a `listdir(SCRIPTS_DIR)`, a `glob.glob(... SCRIPTS ... *.py)`
union, or a `Path(SCRIPTS_DIR).glob("*.py")`). Recursive `os.walk(SCRIPTS_DIR)`
guards are already subdir-safe and are deliberately NOT flagged.
"""

import re
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent

# A hand-rolled *flat* script enumeration rooted at SCRIPTS_DIR:
#  - os.listdir(SCRIPTS_DIR)                       -> non-recursive dir listing
#  - glob.glob(os.path.join(SCRIPTS_DIR, "*.py"))  -> non-recursive glob union
#  - Path(SCRIPTS_DIR).glob("*.py")                -> non-recursive pathlib glob
# `os.walk(SCRIPTS_DIR)` and the helper's own `.rglob("*.py")` are recursive and
# subdir-safe, so they are not matched.
_FLAT_SCRIPT_ENUM = re.compile(
    r"""listdir\s*\([^)]*SCRIPTS                 # os.listdir(SCRIPTS_DIR)
      | glob\.glob\([^)]*SCRIPTS[^)]*\*\.py      # glob.glob(os.path.join(SCRIPTS_DIR, "*.py"))
      | SCRIPTS[^\n]*?\.glob\(\s*['"]\*\.py      # Path(SCRIPTS_DIR).glob("*.py")
    """,
    re.VERBOSE,
)

# Files permitted to enumerate scripts directly:
#  - the shared helper itself is the ONE sanctioned enumeration;
#  - this meta-guard names the pattern it searches for.
_ALLOWLIST = {
    "_script_discovery.py",
    Path(__file__).name,
}


@pytest.mark.adherence
def test_no_handrolled_script_enumeration():
    offenders = []
    for path in sorted(TESTS_DIR.glob("*.py")):
        if path.name in _ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if _FLAT_SCRIPT_ENUM.search(line):
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, (
        "Hand-rolled flat `scripts/` enumeration found — use "
        "tests/_script_discovery.py (all_script_files / all_script_basenames / "
        "all_script_stems / script_paths_by_stem) so a `scripts/` relocation "
        "updates one place and no guard silently narrows:\n" + "\n".join(offenders)
    )
