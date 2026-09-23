"""M1a preserves frozen source rows before any canonical reconciliation."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from jetp.build_m1a_inventories import (
    FIELDS,
    FrozenLayer,
    build_existing_layers,
    write_inventories,
)

ROOT = Path(__file__).resolve().parents[1]


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
        exported.extend(rows)

    assert {row["source_row_id"] for row in exported} == {"1", "2", "3", "4"}
    assert len(exported) == sum(len(layer.rows) for layer in layers)
    assert manifest["countries"]["IDN"]["unknowns"]["identity_rows"] == 1
    assert manifest["countries"]["SEN"]["unknowns"]["field_values"] >= 1
    assert manifest["countries"]["SEN"]["unknowns"]["unavailable_source_rows"] == 2
    assert json.loads((tmp_path / "manifest.json").read_text()) == manifest


def test_existing_inputs_replay_without_fusion_and_with_pinned_layer_dates(
    tmp_path: Path,
) -> None:
    layers = build_existing_layers(ROOT)

    assert {(layer.country, layer.layer_id): len(layer.rows) for layer in layers} == {
        ("ZAF", "register-q1-2026"): 257,
        ("IDN", "cipp-2023-priority-projects"): 437,
        ("IDN", "progress-2025-priority-projects"): 1142,
        ("VNM", "rmp-2023-inventory"): 279,
        ("SEN", "investment-plan-annex-submissions"): 38,
        ("SEN", "investment-plan-quick-wins"): 11,
    }
    first = tmp_path / "first"
    second = tmp_path / "second"
    manifest = write_inventories(layers, first)
    write_inventories(build_existing_layers(ROOT), second)

    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    assert {
        country: details["row_count"]
        for country, details in manifest["countries"].items()
    } == {"ZAF": 257, "IDN": 1579, "VNM": 279, "SEN": 49}
    assert manifest["countries"]["VNM"]["unknowns"]["identity_rows"] == 181
    assert all(
        layer["edition"] and layer["cutoff"] and layer["input_sha256"]
        for details in manifest["countries"].values()
        for layer in details["sublayers"]
    )
    for country in ("ZAF", "IDN", "VNM", "SEN"):
        with (first / f"{country}.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert all(row["source_id"] and row["source_layer"] for row in rows)
        assert all(row["record_type"] and row["reported_status"] for row in rows)
        assert len({(row["source_layer"], row["source_row_id"]) for row in rows}) == len(rows)


def test_checked_in_m1a_release_and_mvp_downloads_match_clean_replay(
    tmp_path: Path,
) -> None:
    expected = tmp_path / "m1a"
    write_inventories(build_existing_layers(ROOT), expected)
    published = ROOT / "deliverables" / "jetp-observatory" / "data" / "m1a"
    assert {path.name: path.read_bytes() for path in published.iterdir()} == {
        path.name: path.read_bytes() for path in expected.iterdir()
    }

    renderer = (ROOT / "deliverables" / "jetp-observatory" / "app.js").read_text()
    # The inventories are the Entries step of the paper trail (ticket 0881).
    assert "function entriesPage()" in renderer
    assert "not a live status service" in renderer
    assert "identity_rows" in renderer
    assert "unavailable_source_rows" in renderer
    for country in ("ZAF", "IDN", "VNM", "SEN"):
        assert f'data/m1a/{country}.csv' in renderer
    assert 'data/m1a/manifest.json' in renderer


def _raw_row(row_id: str, **raw: object) -> dict[str, object]:
    row = _row(row_id, f"Operation {row_id}", "register_row", "completed")
    row["source_fields"] = dict(row["source_fields"]) | raw
    return row


def test_csv_width_is_per_country_and_excluded_rows_reach_the_manifest(
    tmp_path: Path,
) -> None:
    excluded = (
        {
            "raw_index": 0,
            "ordinal": 1,
            "unique_id_raw": 248,
            "project_name_raw": None,
            "portfolios_raw": None,
            "amount_reported_usd_raw": 100.5,
            "amount_reported_zar_raw": 200.5,
        },
    )
    layers = [
        FrozenLayer(
            country="ZAF",
            layer_id="register",
            source_id="zaf-register",
            edition="Q1 2026",
            cutoff="2026-03-31",
            source_sha256="a" * 64,
            rows=(_raw_row("1", raw_example_field="carried verbatim"),),
            excluded_source_rows=excluded,
        ),
        FrozenLayer(
            country="IDN",
            layer_id="priority-list",
            source_id="idn-plan",
            edition="2025",
            cutoff="2025-12-31",
            source_sha256="b" * 64,
            rows=(_row("2", "Plan project", "project", "priority"),),
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
            rows=(_row("4", "Rural component", "component", "listed"),),
        ),
    ]

    manifest = write_inventories(layers, tmp_path)

    with (tmp_path / "ZAF.csv").open(encoding="utf-8", newline="") as handle:
        zaf = csv.reader(handle)
        assert tuple(next(zaf)) == FIELDS + ("raw_example_field",)
        assert next(zaf)[-1] == "carried verbatim"
    for country in ("IDN", "VNM", "SEN"):
        with (tmp_path / f"{country}.csv").open(encoding="utf-8", newline="") as handle:
            assert tuple(next(csv.reader(handle))) == FIELDS

    assert manifest["countries"]["ZAF"]["sublayers"][0]["excluded_source_rows"] == list(
        excluded
    )
    for country in ("IDN", "VNM", "SEN"):
        assert manifest["countries"][country]["sublayers"][0]["excluded_source_rows"] == []
    assert json.loads((tmp_path / "manifest.json").read_text()) == manifest
