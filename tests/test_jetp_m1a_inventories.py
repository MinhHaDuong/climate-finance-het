"""M1a preserves frozen source rows before any canonical reconciliation."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from jetp.build_m1a_inventories import FrozenLayer, write_inventories


def _row(
    row_id: str,
    label: str,
    record_type: str,
    status: str,
    identity_status: str = "named",
) -> dict[str, object]:
    return {
        "source_row_id": row_id,
        "label": label,
        "record_type": record_type,
        "reported_status": status,
        "identity_status": identity_status,
        "evidence_locator": f"table 1, row {row_id}",
        "source_fields": {"name": label, "status": status, "optional_note": ""},
    }


def test_four_country_export_preserves_layers_rows_and_separate_unknowns(
    tmp_path: Path,
) -> None:
    layers = [
        FrozenLayer(
            country="ZAF",
            layer_id="register",
            source_id="zaf-register",
            edition="Q1 2026",
            cutoff="2026-03-31",
            source_sha256="a" * 64,
            rows=(_row("1", "Named operation", "operation", "completed"),),
        ),
        FrozenLayer(
            country="IDN",
            layer_id="priority-list",
            source_id="idn-plan",
            edition="2025",
            cutoff="2025-12-31",
            source_sha256="b" * 64,
            rows=(_row("2", "", "project", "priority", "unknown"),),
        ),
        FrozenLayer(
            country="VNM",
            layer_id="rmp",
            source_id="vnm-rmp",
            edition="2023",
            cutoff="2023-12-01",
            source_sha256="c" * 64,
            rows=(_row("3", "Grid programme", "programme", "listed"),),
        ),
        FrozenLayer(
            country="SEN",
            layer_id="annex",
            source_id="sen-plan",
            edition="2025",
            cutoff="2025-04-02",
            source_sha256="d" * 64,
            unavailable_source_rows=2,
            rows=(_row("4", "Rural component", "component", ""),),
        ),
    ]

    manifest = write_inventories(layers, tmp_path)

    assert sorted(path.name for path in tmp_path.glob("*.csv")) == [
        "IDN.csv",
        "SEN.csv",
        "VNM.csv",
        "ZAF.csv",
    ]
    exported = []
    for country in ("ZAF", "IDN", "VNM", "SEN"):
        with (tmp_path / f"{country}.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 1
        assert rows[0]["country"] == country
        assert rows[0]["source_id"]
        assert rows[0]["source_layer"]
        assert rows[0]["source_edition"]
        assert rows[0]["source_cutoff"]
        assert rows[0]["record_type"]
        assert "reported_status" in rows[0]
        assert json.loads(rows[0]["source_fields_json"])["optional_note"] == ""
        exported.extend(rows)

    assert {row["source_row_id"] for row in exported} == {"1", "2", "3", "4"}
    assert len(exported) == sum(len(layer.rows) for layer in layers)
    assert manifest["countries"]["IDN"]["unknowns"]["identity_rows"] == 1
    assert manifest["countries"]["SEN"]["unknowns"]["field_values"] >= 1
    assert manifest["countries"]["SEN"]["unknowns"]["unavailable_source_rows"] == 2
    assert json.loads((tmp_path / "manifest.json").read_text()) == manifest
