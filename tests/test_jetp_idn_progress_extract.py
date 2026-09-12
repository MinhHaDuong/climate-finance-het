"""Extraction contract for the complete Indonesia JETP 2025 priority list."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from jetp.extract_idn_progress_priority_projects import PROGRESS_SHA256

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "jetp"
SOURCE_ID = "idn-jetp-progress-report-2025"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_progress_report_priority_appendix_is_exhaustive() -> None:
    rows = [
        row
        for row in read_csv(DATA / "plan-projects.csv")
        if row["country"] == "IDN" and row["source_id"] == SOURCE_ID
    ]

    assert len(rows) == 1142
    assert len({row["plan_project_id"] for row in rows}) == 1142
    assert Counter(row["technology_group"] for row in rows) == {
        "energy_efficiency": 13,
        "transmission": 340,
        "hydro": 183,
        "geothermal": 134,
        "bioenergy": 58,
        "other_dispatchable": 70,
        "solar": 281,
        "wind": 55,
        "supply_chain": 8,
    }
    assert {row["document_sha256"] for row in rows} == {PROGRESS_SHA256}
    assert {row["priority_tier"] for row in rows} == {"priority", "top_priority"}


def test_progress_source_numbering_errors_are_preserved_without_losing_rows() -> None:
    rows = {
        row["plan_project_id"]: row
        for row in read_csv(DATA / "plan-projects.csv")
        if row["source_id"] == SOURCE_ID
    }

    # The published table repeats hydro labels 110--119 and row 48 in the
    # geothermal and dispatchable tables; it also skips solar row 281.
    assert "printed row 110" in rows["idn-progress25-hydro-120"]["locator"]
    assert "normalised physical row 120" in rows["idn-progress25-hydro-120"]["notes"]
    assert "printed row 282" in rows["idn-progress25-solar-281"]["locator"]
    assert "normalised physical row 281" in rows["idn-progress25-solar-281"]["notes"]
    assert "printed row 48" in rows["idn-progress25-geothermal-049"]["locator"]
    assert "printed row 48" in rows[
        "idn-progress25-other-dispatchable-049"
    ]["locator"]


def test_progress_rows_reconcile_only_reviewed_exact_matches() -> None:
    rows = {
        row["plan_project_id"]: row
        for row in read_csv(DATA / "plan-projects.csv")
        if row["source_id"] == SOURCE_ID
    }

    expected = {
        "idn-progress25-energy-efficiency-001": "idn-fin-mrt-east-west",
        "idn-progress25-energy-efficiency-003": "idn-pipe-rsud-energy-efficiency",
        "idn-progress25-hydro-073": "idn-monitor-cihaur-talaga-micro-hydro",
        "idn-progress25-hydro-075": "idn-monitor-cihaur-talaga-micro-hydro",
        "idn-progress25-geothermal-005": "idn-grant-patuha-2",
        "idn-progress25-geothermal-018": "idn-pipe-hululais-1-2",
        "idn-progress25-geothermal-019": "idn-pipe-hululais-1-2",
        "idn-progress25-solar-021": "idn-fin-saguling-floating-solar",
        "idn-progress25-solar-029": "idn-pipe-sutami-floating-solar",
        "idn-progress25-wind-011": "idn-pipe-tanah-laut-wind",
        "idn-progress25-supply-chain-003": "idn-pipe-solar-cell-manufacturing",
    }
    assert {key: rows[key]["canonical_project_id"] for key in expected} == expected
    assert {row["reconciliation_status"] for row in rows.values()} <= {
        "matched",
        "plan_only",
    }
