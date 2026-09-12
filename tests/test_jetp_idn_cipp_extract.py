"""Extraction contract for all 437 priority-project lines in CIPP 2023."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from jetp.extract_idn_cipp_priority_projects import CIPP_SHA256

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "jetp"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_cipp_priority_project_appendices_are_exhaustive() -> None:
    rows = read_csv(DATA / "plan-projects.csv")
    indonesia = [
        row
        for row in rows
        if row["country"] == "IDN" and row["source_id"] == "idn-cipp-2023-cpr-mirror"
    ]

    assert len(indonesia) == 437
    assert len({row["plan_project_id"] for row in indonesia}) == 437
    assert Counter(row["technology_group"] for row in indonesia) == {
        "transmission": 37,
        "coal_retirement": 2,
        "geothermal": 90,
        "hydro": 158,
        "bioenergy": 33,
        "solar": 64,
        "wind": 53,
    }
    assert {row["document_sha256"] for row in indonesia} == {CIPP_SHA256}
    project_ids = {row["project_id"] for row in read_csv(DATA / "projects.csv")}
    source_ids = {row["source_id"] for row in read_csv(DATA / "sources.csv")}
    assert {row["source_id"] for row in indonesia} <= source_ids
    assert {
        row["canonical_project_id"]
        for row in indonesia
        if row["canonical_project_id"]
    } <= project_ids


def test_cipp_rows_preserve_plan_values_and_selected_canonical_matches() -> None:
    rows = {
        row["plan_project_id"]: row for row in read_csv(DATA / "plan-projects.csv")
    }

    assert rows["idn-cipp-transmission-001"]["estimated_investment_usd_mn"] == "22.4"
    assert rows["idn-cipp-coal-retirement-002"]["natural_retirement_year"] == "2042"
    assert rows["idn-cipp-coal-retirement-002"]["estimated_retirement_year"] == "2035"
    assert rows["idn-cipp-coal-retirement-002"]["capacity_value"] == "660"
    assert rows["idn-cipp-coal-retirement-002"]["canonical_project_id"] == (
        "idn-pipe-cirebon-1-retirement"
    )
    assert rows["idn-cipp-geothermal-017"]["canonical_project_id"] == (
        "idn-pipe-hululais-1-2"
    )
    assert rows["idn-cipp-solar-003"]["canonical_project_id"] == (
        "idn-pipe-sutami-floating-solar"
    )
    assert rows["idn-cipp-wind-003"]["canonical_project_id"] == (
        "idn-pipe-tanah-laut-wind"
    )
    assert {row["reconciliation_status"] for row in rows.values()} <= {
        "matched",
        "plan_only",
    }
