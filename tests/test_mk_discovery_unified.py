"""Meta-guard — no test may hand-roll its own `.mk` enumeration (ticket 0248).

Several build guards used to each glob a *fixed* set of directories to enumerate
the pipeline's Makefile fragments. When a `.mk` moved (ticket 0239 relocated the
five Phase-2 concern fragments to `scripts/analysis/`), it silently dropped out
of a guard's coverage and the test kept passing — over fewer files, not because
the contract still held.

The class fix is one shared discovery helper, `tests/_mk_discovery.py`. This
guard is the standing regression test for the class: it fails if any test file
outside the helper hand-rolls a `.mk` enumeration (a `glob(... .mk)` union or a
`listdir`/`endswith(".mk")` filter). A future PR that reintroduces a hand-rolled
glob is caught here rather than rotting into a latent coverage gap.
"""

import re
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent

# A hand-rolled `.mk` enumeration: a `glob(... .mk)` union (glob.glob or
# pathlib `.glob`), or a `listdir`/`endswith(".mk")` filter over a directory.
_HANDROLLED_MK = re.compile(
    r"""glob\s*\([^)]*\.mk        # glob.glob(..., "*.mk") / path.glob("*.mk")
      | listdir[^\n]*\.mk         # os.listdir(...) then a .mk filter on one line
      | endswith\(\s*['"]\.mk['"] # [f for f in ... if f.endswith(".mk")]
    """,
    re.VERBOSE,
)

# Files permitted to enumerate `.mk` directly:
#  - the shared helper itself is the ONE sanctioned enumeration;
#  - this meta-guard names the pattern it searches for;
#  - the layout guard globs each directory to assert *placement* (root carries
#    only paths.mk; the five concern fragments live under scripts/analysis/) —
#    a per-directory membership check, not a coverage union that can silently
#    narrow, so unifying it would defeat its purpose.
_ALLOWLIST = {
    "_mk_discovery.py",
    Path(__file__).name,
    "test_analysis_mk_layout.py",
}


@pytest.mark.adherence
def test_no_handrolled_mk_enumeration():
    offenders = []
    for path in sorted(TESTS_DIR.glob("*.py")):
        if path.name in _ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if _HANDROLLED_MK.search(line):
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, (
        "Hand-rolled `.mk` enumeration found — use tests/_mk_discovery.py "
        "(all_makefiles / mk_fragments) so a `.mk` relocation updates one place "
        "and no guard silently narrows:\n" + "\n".join(offenders)
    )
