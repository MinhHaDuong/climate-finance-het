"""The central JETP figure must remain a coverage figure, not a causal claim."""

import csv
import json
import sys
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from jetp.build_0823_figure import _svg, build_figure_data, render_outputs

pytestmark = pytest.mark.wp_jetp

def test_figure_data_keeps_one_denominator_and_the_null_join_visible() -> None:
    """Different documentary panels cannot be made to look like a joint sample."""
    data = build_figure_data(ROOT)

    assert [row["panel_id"] for row in data["panels"]] == [
        "A_function_labels",
        "B_finance_instruments",
        "C_event_history",
    ]
    assert {row["atomic_denominator"] for row in data["panels"]} == {1740}
    assert data["common_explicit_unit_observations"] == 0
    assert data["central_result"] == (
        "The frozen corpus documents the three dimensions at sharply different "
        "coverage levels and contains no atomic assertion explicitly coded on all three."
    )
    assert all("causal" not in row["panel_note"].lower() for row in data["panels"])


def test_rendered_figure_exposes_unknowns_and_replays_from_manifest(tmp_path: Path) -> None:
    """A zero or missing panel renders legibly and records exact inputs and outputs."""
    render_outputs(ROOT, tmp_path)

    plotted = list(csv.DictReader((tmp_path / "0823-central-figure-data.csv").open()))
    assert len(plotted) == 3
    assert plotted[2]["documented_observations"] == "7"
    assert plotted[2]["unknown_or_uncoded_observations"] == "1733"

    svg = (tmp_path / "0823-central-figure.svg").read_text(encoding="utf-8")
    assert "A. Function labels" in svg
    assert "B. Finance instruments" in svg
    assert "C. Event history" in svg
    assert "No common explicit A/B/C atomic assertion: 0 / 1,740" in svg
    assert "causal" not in svg.lower()

    manifest = json.loads((tmp_path / "0823-figure-manifest.json").read_text())
    assert manifest["reproduction"].endswith("build_0823_figure.py --root .")
    assert manifest["files"]["0823-central-figure.svg"]["sha256"]
    assert manifest["input_0730_sha256"]


def test_zero_documented_panel_remains_visible_in_a_mixed_fixture() -> None:
    """A future empty panel must say zero, not disappear or become a causal gap."""
    data = deepcopy(build_figure_data(ROOT))
    data["panels"][2]["documented_observations"] = 0
    data["panels"][2]["unknown_or_uncoded_observations"] = 1740

    svg = _svg(data)

    assert "0 documented · 1,740 unknown/uncoded · n=1,740" in svg
    assert "C. Event history" in svg
    assert "causal" not in svg.lower()


def test_every_rendered_label_declares_a_bounding_width_inside_the_viewbox(tmp_path: Path) -> None:
    """A long count or provenance label cannot run beyond the SVG canvas again."""
    render_outputs(ROOT, tmp_path)
    root = ElementTree.parse(tmp_path / "0823-central-figure.svg").getroot()
    _, _, viewbox_width, viewbox_height = map(float, root.attrib["viewBox"].split())

    for label in root.findall("{http://www.w3.org/2000/svg}text"):
        assert "textLength" in label.attrib
        assert float(label.attrib["x"]) + float(label.attrib["textLength"]) <= viewbox_width
        assert float(label.attrib["y"]) <= viewbox_height


def test_vietnam_context_stays_at_assertion_and_reconciliation_scale() -> None:
    """The small VNM reconciliation set is not silently promoted to operations."""
    vnm = build_figure_data(ROOT)["candidate_assessment"][2]

    assert "source-assertion" in vnm["intrinsic_interest"]
    assert "operation scale" not in vnm["intrinsic_interest"]
