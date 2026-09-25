"""The short JETP package is a reviewable evidence package, not a placeholder."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "deliverables" / "jetp-mesure" / "jetp-mesure.tex"
RECIPE = ROOT / "deliverables" / "jetp-mesure" / "jetp-mesure.mk"


pytestmark = pytest.mark.wp_jetp

def test_short_package_exposes_frozen_result_figure_and_next_iteration() -> None:
    """Reviewers can see the result, its frozen input, and what must be re-harvested."""
    source = TEX.read_text(encoding="utf-8")

    assert "0823-central-figure.svg" in source
    assert "1,740" in source
    assert "0" in source
    assert "Detailed manuscript plan" in source
    assert "Evidence slot" in source
    assert "Citation slot" in source
    assert "Iteration and re-harvesting agenda" in source
    assert r"unit\_kind" in source
    assert r"explicit\_JETP" in source
    assert r"adjacent\_transition" in source
    assert "Rio mitigation/adaptation markers" in source
    assert "not a causal estimate" in source


def test_short_package_does_not_promote_coverage_into_a_substantive_effect() -> None:
    """The provisional coverage result stays distinct from the sought JETP finding."""
    source = TEX.read_text(encoding="utf-8").lower()

    assert "does not establish acceleration" in source
    assert "does not establish private-finance mobilisation" in source
    assert "sought substantive result" in source


def test_short_package_keeps_the_standard_latexmk_source_directory_recipe() -> None:
    """A document-content ticket must not substitute the established renderer."""
    recipe = RECIPE.read_text(encoding="utf-8")

    assert "LATEXMK ?= latexmk" in recipe
    assert "LATEXMK_FLAGS ?= -cd -pdf -halt-on-error -interaction=nonstopmode" in recipe
    assert "$(LATEXMK) $(LATEXMK_FLAGS) $<" in recipe
    assert "TECTONIC" not in recipe
