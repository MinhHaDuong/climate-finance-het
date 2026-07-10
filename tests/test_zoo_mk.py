"""Tests for the zoo Phase-2 concern .mk structure — schematic + result panels.

The Phase-2 concern fragment moved to `scripts/analysis/zoo-figures.mk` and was
renamed to end the basename clash with the Phase-3 render fragment
`deliverables/zoo/zoo.mk` (ticket 0239).
"""

import re
from pathlib import Path

import pytest

ZOO_MK = (
    Path(__file__).resolve().parent.parent / "scripts" / "analysis" / "zoo-figures.mk"
)
# The Phase-3 render rule lives beside its source (ticket 0237); the Phase-2
# concern fragment is scripts/analysis/zoo-figures.mk (ticket 0239).
ZOO_RENDER_MK = (
    Path(__file__).resolve().parent.parent / "deliverables" / "zoo" / "zoo.mk"
)

_CROSSYEAR_RE = re.compile(
    r"^CROSSYEAR_METHODS\s*:=\s*(.*?)(?=\n\S|\n\n|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _parse_crossyear_methods(mk: str) -> list[str]:
    m = _CROSSYEAR_RE.search(mk)
    assert m, "CROSSYEAR_METHODS not found in zoo-figures.mk"
    return [t for t in m.group(1).split() if t != "\\"]


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

    def test_crossyear_methods_has_18_methods(self, zoo_mk_text):
        methods = _parse_crossyear_methods(zoo_mk_text)
        assert len(methods) == 18, (
            f"Expected 18 CROSSYEAR_METHODS, got {len(methods)}: {methods}"
        )

    def test_cumulative_methods_included(self, zoo_mk_text):
        """L3, G3, G4, G7 use cumulative/single windows — must still have recipes."""
        methods = _parse_crossyear_methods(zoo_mk_text)
        for expected in (
            "L3",
            "G3_coupling_age",
            "G4_cross_tradition",
            "G7_disruption",
        ):
            assert expected in methods, f"{expected} missing from CROSSYEAR_METHODS"

    def test_zoo_pdf_target_in_render_mk(self):
        """The zoo PDF render rule lives in deliverables/zoo/zoo.mk (ticket 0237).

        Phase 3 render is split from Phase 2 compute: the render rule sits beside
        its source under deliverables/zoo/, not in the root concern zoo.mk.
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
