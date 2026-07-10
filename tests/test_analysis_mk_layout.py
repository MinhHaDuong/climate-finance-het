"""Layout guard — Phase-2 analysis .mk live under scripts/analysis/, not root.

Ticket 0239 (code reorg 1/4): the top level stopped carrying build fragments.
The five Phase-2 "concern" Makefile fragments moved under `scripts/analysis/`;
the only `.mk` left at the repo root is `paths.mk` (the shared variable
interface `-include`d by both the Phase-2 Makefile and every Phase-3 render
`.mk`). This guard fails if a new analysis `.mk` reappears at root or a moved
one goes missing.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO = Path(__file__).resolve().parent.parent
ANALYSIS_MK_DIR = REPO / "scripts" / "analysis"

# The five Phase-2 analysis fragments, at their post-0239 home. The root
# `zoo.mk` was renamed `zoo-figures.mk` to end the basename clash with the
# Phase-3 render fragment `deliverables/zoo/zoo.mk`.
EXPECTED_ANALYSIS_MK = {
    "divergence.mk",
    "separation.mk",
    "venues.mk",
    "multilayer-detection.mk",
    "zoo-figures.mk",
}


def test_analysis_mk_live_under_scripts_analysis():
    present = {p.name for p in ANALYSIS_MK_DIR.glob("*.mk")}
    missing = EXPECTED_ANALYSIS_MK - present
    assert not missing, f"analysis .mk missing from scripts/analysis/: {sorted(missing)}"


def test_root_carries_only_paths_mk():
    root_mk = {p.name for p in REPO.glob("*.mk")}
    assert root_mk == {"paths.mk"}, (
        f"repo root must carry only paths.mk; found {sorted(root_mk)}. "
        "Phase-2 analysis fragments belong under scripts/analysis/ (ticket 0239)."
    )
