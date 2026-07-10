"""Tickets 0219 / 0222 — layout mirrors dataflow phase: no Phase-2 output under data/catalogs/.

`data/` is split by pipeline phase: `data/catalogs/` (+ pool/exports/syllabi) is
Phase-1 corpus (DVC-managed), `data/derived/` is Phase-2 derived data (gitignored,
regenerable). A Phase-2 output living in the Phase-1 corpus dir breaks that mirror.

This is a **class** guard (0222 generalized 0219's two-basename whitelist): it reads
the Makefile as the source of truth and fails if *any* target produced by a Phase-2
script resolves under `data/catalogs/`, or if any script reads a `data/derived`
output from `CATALOGS_DIR`. A newly-introduced Phase-2 output under `data/catalogs/`
fails the test with no edit to this file.
"""

import glob
import os
import re

import pytest

# Mechanical adherence gate (`make lint` / `pytest -m adherence`).
pytestmark = pytest.mark.adherence

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
MAKEFILE = os.path.join(PROJECT_ROOT, "Makefile")
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

# A Make prerequisite naming one of these script prefixes marks a Phase-2 producer.
#
# Two blind spots, documented in .claude/rules/architecture.md
# ("Phase is semantic, not a filename prefix"):
#   1. Only Makefile-wired targets are checked. A script writing to a hardcoded
#      CATALOGS_DIR default with no Make target is invisible here — e.g.
#      compute_reranker_calibration.py (Phase-1 corpus scoring, correctly under
#      data/catalogs/, no Make target).
#   2. The prefix is a heuristic, not the semantic phase: compute_reranker_calibration
#      has a compute_ prefix but is Phase-1; qa_embeddings / qa_detect_type have a
#      qa_ prefix but write Phase-2 outputs to DERIVED_TABLES_DIR.
# Extending the guard to close these (a ~20-basename allowlist) was declined (0227):
# low leak probability, upkeep not worth it.
PHASE2_PRODUCER = re.compile(r"scripts/(analyze_|compute_|plot_|export_|summarize_|build_het)")
CATALOGS = "data/catalogs/"
DERIVED = "data/derived/"
_MAKE_VAR = re.compile(r"\$\(([A-Z_][A-Z0-9_]*)\)")


def _makefile_constants():
    """Parse `NAME := value` assignments and fully expand nested $(REF) references."""
    raw = {}
    with open(MAKEFILE, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^([A-Z_][A-Z0-9_]*)\s*:=\s*(.+?)\s*$", line)
            if m:
                raw[m.group(1)] = m.group(2)

    def expand(value, seen):
        def repl(mm):
            name = mm.group(1)
            if name in raw and name not in seen:
                return expand(raw[name], seen | {name})
            return mm.group(0)
        return _MAKE_VAR.sub(repl, value)

    return {k: expand(v, {k}) for k, v in raw.items()}


def _resolve(token, consts):
    return _MAKE_VAR.sub(lambda m: consts.get(m.group(1), m.group(0)), token)


def test_no_phase2_target_under_catalogs():
    """Producer side: no target built by a Phase-2 script resolves under data/catalogs/."""
    consts = _makefile_constants()
    offenders = []
    with open(MAKEFILE, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            # A rule line "target[ target…]: prereqs" (not a ":=" assignment, not a recipe).
            m = re.match(r"^([^\s#][^:=]*):\s+(\S.*)$", line)
            if not m or not PHASE2_PRODUCER.search(m.group(2)):
                continue
            for tok in m.group(1).split():
                if CATALOGS in _resolve(tok, consts):
                    offenders.append(f"Makefile:{i}: {tok} -> {_resolve(tok, consts)}")
    assert not offenders, (
        "Phase-2 outputs must resolve under data/derived/, not data/catalogs/ "
        "(ticket 0219/0222). A Phase-2-produced Make target still lands in the "
        "Phase-1 corpus dir:\n  " + "\n  ".join(offenders)
    )


def test_no_script_reads_derived_output_from_catalogs():
    """Consumer side: no script reads a data/derived output via CATALOGS_DIR."""
    consts = _makefile_constants()
    derived_names = {
        os.path.basename(v) for v in consts.values() if DERIVED in v and v.endswith((".csv", ".json", ".npz"))
    }
    offenders = []
    for path in glob.glob(os.path.join(SCRIPTS_DIR, "*.py")):
        with open(path, encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                for name in derived_names:
                    if f'CATALOGS_DIR, "{name}"' in line or f"CATALOGS_DIR, '{name}'" in line:
                        rel = os.path.relpath(path, PROJECT_ROOT)
                        offenders.append(f"{rel}:{i}: reads {name} from CATALOGS_DIR")
    assert not offenders, (
        "A Phase-2 derived output is read from CATALOGS_DIR — use DERIVED_TABLES_DIR "
        "(ticket 0219/0222):\n  " + "\n  ".join(offenders)
    )
