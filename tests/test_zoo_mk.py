"""Tests for the zoo Phase-2 concern .mk structure — schematic + result panels.

The Phase-2 concern fragment moved to `scripts/analysis/zoo-figures.mk` and was
renamed to end the basename clash with the Phase-3 render fragment
`deliverables/zoo/zoo.mk` (ticket 0239).
"""

import re
from pathlib import Path

import pytest
from _mk_discovery import makefile_constants

ZOO_MK = (
    Path(__file__).resolve().parent.parent / "scripts" / "analysis" / "zoo-figures.mk"
)
# The Phase-3 render rule lives beside its source (ticket 0237); the Phase-2
# concern fragment is scripts/analysis/zoo-figures.mk (ticket 0239).
ZOO_RENDER_MK = (
    Path(__file__).resolve().parent.parent / "deliverables" / "zoo" / "zoo.mk"
)

SCHEMATIC_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts" / "figures"


def _mk_list(name: str) -> list[str]:
    """`name`'s tokens from zoo-figures.mk, via the shared `.mk` parser (0248)."""
    constants = makefile_constants(files=[ZOO_MK])
    assert name in constants, f"{name} not found in zoo-figures.mk"
    return constants[name].split()


def _schematic_script_stems() -> set[str]:
    """Stems of the plot_schematic_*.py scripts actually on disk."""
    return {
        p.stem[len("plot_schematic_"):]
        for p in SCHEMATIC_SCRIPTS_DIR.glob("plot_schematic_*.py")
    }


@pytest.fixture(scope="class")
def zoo_mk_text():
    return ZOO_MK.read_text()


class TestZooMkStructure:
    def test_zoo_figures_is_phony(self, zoo_mk_text):
        assert re.search(r"^\.PHONY:.*zoo-figures", zoo_mk_text, re.MULTILINE), (
            "zoo-figures must be declared .PHONY"
        )

    def test_zoo_figures_target_exists(self, zoo_mk_text):
        assert re.search(r"^zoo-figures\s*:", zoo_mk_text, re.MULTILINE), (
            "zoo-figures target missing from zoo-figures.mk"
        )

    def test_schematic_pattern_recipe_exists(self, zoo_mk_text):
        assert re.search(r"schematic_%\.png\s*:.*plot_schematic_%\.py", zoo_mk_text), (
            "Pattern rule for schematic_%.png missing from zoo-figures.mk"
        )

    def test_result_panel_pattern_recipe_exists(self, zoo_mk_text):
        assert re.search(r"fig_zoo_%\.png\s*:.*plot_zoo_results\.py", zoo_mk_text), (
            "Pattern rule for fig_zoo_%.png missing from zoo-figures.mk"
        )

    def test_crossyear_tables_is_phony(self, zoo_mk_text):
        assert re.search(r"^\.PHONY:.*crossyear-tables", zoo_mk_text, re.MULTILINE), (
            "crossyear-tables must be declared .PHONY"
        )

    def test_crossyear_methods_has_18_methods(self):
        methods = _mk_list("CROSSYEAR_METHODS")
        assert len(methods) == 18, (
            f"Expected 18 CROSSYEAR_METHODS, got {len(methods)}: {methods}"
        )

    def test_cumulative_methods_included(self):
        """L3, G3, G4, G7 use cumulative/single windows — must still have recipes."""
        methods = _mk_list("CROSSYEAR_METHODS")
        for expected in (
            "L3",
            "G3_coupling_age",
            "G4_cross_tradition",
            "G7_disruption",
        ):
            assert expected in methods, f"{expected} missing from CROSSYEAR_METHODS"

    def test_schematic_stems_match_the_scripts_on_disk(self):
        """`ZOO_SCHEMATIC_STEMS` and `plot_schematic_*.py` must name the same set.

        The pattern rule builds `schematic_$(stem).png` from
        `plot_schematic_$(stem).py`, so a stem with no script fails loudly at
        build time — but the other direction is silent: a script the list omits
        is simply never built, and `make zoo-figures` ships the deliverable one
        panel short at exit 0. The comment at the head of zoo-figures.mk says
        the two "match exactly" and nothing enforced it (ticket 0571), so the
        assertion is set equality rather than a subset check.
        """
        declared = set(_mk_list("ZOO_SCHEMATIC_STEMS"))
        on_disk = _schematic_script_stems()
        assert declared == on_disk, (
            "ZOO_SCHEMATIC_STEMS must match scripts/figures/plot_schematic_*.py. "
            f"Declared with no script: {sorted(declared - on_disk)}; "
            f"script with no stem (panel would never build): "
            f"{sorted(on_disk - declared)}"
        )

    def test_zoo_pdf_target_in_render_mk(self):
        """The zoo PDF render rule lives in deliverables/zoo/zoo.mk (ticket 0237).

        Phase 3 render is split from Phase 2 compute: the render rule sits beside
        its source under deliverables/zoo/, not in the concern fragment
        scripts/analysis/zoo-figures.mk.
        """
        render_text = ZOO_RENDER_MK.read_text()
        assert re.search(
            r"^deliverables/zoo/breakpoint-detect-method-zoo\.pdf\s*:",
            render_text,
            re.MULTILINE,
        ), "breakpoint-detect-method-zoo.pdf recipe must live in deliverables/zoo/zoo.mk"

    def test_concern_zoo_mk_has_no_render_rule(self, zoo_mk_text):
        """The concern fragment must be pure Phase-2 — no render rule (0237)."""
        assert "quarto render" not in zoo_mk_text, (
            "zoo-figures.mk must not carry a render recipe; render lives in "
            "deliverables/zoo/zoo.mk"
        )
        assert ".pdf:" not in zoo_mk_text, (
            "zoo-figures.mk must carry no .pdf render target"
        )
