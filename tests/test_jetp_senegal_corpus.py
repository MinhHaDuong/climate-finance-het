"""Source-bounded corpus and plan-line contract for Senegal's JETP."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "jetp"

MAIN_PLAN = "sen-investment-plan-l4-mirror"
ANNEXES = "sen-investment-plan-annexes-mirror"
DECLARATION = "sen-political-declaration-fr-2023"
MAIN_SHA256 = "97c36b242257462f024a934baee6bed3aa02fe0e4917f076d7b865701db65dca"
ANNEX_SHA256 = "dcd4fd924f9e637d36beb192f509b7971b8b5dda0a76e3c17b799ba26ff43b21"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_declaration_plan_and_annexes_are_materialized() -> None:
    sources = {
        row["source_id"]: row
        for row in read_csv(DATA / "sources.csv")
        if row["country"] == "SEN"
    }
    material = {
        row["source_id"]: row
        for row in read_csv(DATA / "manifest.csv")
        if row["country"] == "SEN"
        and row["status"] in {"collected", "not_modified"}
        and row["sha256"]
    }

    assert {DECLARATION, MAIN_PLAN, ANNEXES} <= sources.keys()
    assert {DECLARATION, MAIN_PLAN, ANNEXES} <= material.keys()
    assert material[MAIN_PLAN]["sha256"] == MAIN_SHA256
    assert material[ANNEXES]["sha256"] == ANNEX_SHA256
    assert sources[MAIN_PLAN]["source_type"] == "investment_plan"
    assert sources[ANNEXES]["source_type"] == "investment_plan"
    assert sources[DECLARATION]["source_type"] == "political_declaration"


def test_all_38_received_projects_are_preserved_as_plan_lines() -> None:
    rows = [
        row
        for row in read_csv(DATA / "plan-projects.csv")
        if row["country"] == "SEN" and row["source_id"] == ANNEXES
    ]

    assert len(rows) == 38
    assert len({row["plan_project_id"] for row in rows}) == 38
    assert {int(row["ordinal"]) for row in rows} == set(range(1, 39))
    assert {row["document_sha256"] for row in rows} == {ANNEX_SHA256}
    assert {row["priority_tier"] for row in rows} == {"priority"}
    assert all("received" in row["notes"].lower() for row in rows)


def test_main_plan_keeps_its_11_quick_wins_as_a_separate_cohort() -> None:
    rows = [
        row
        for row in read_csv(DATA / "plan-projects.csv")
        if row["country"] == "SEN"
        and row["source_id"] == MAIN_PLAN
        and row["technology_group"] == "quick_win"
    ]

    assert len(rows) == 11
    assert {int(row["ordinal"]) for row in rows} == set(range(1, 12))
    assert {row["priority_tier"] for row in rows} == {"top_priority"}
    assert {row["document_sha256"] for row in rows} == {MAIN_SHA256}

    qw11 = next(row for row in rows if row["ordinal"] == "11")
    assert "1,000" in qw11["notes"]
    assert "2,000" in qw11["notes"]


def test_plan_and_annex_project_counts_remain_distinct_claims() -> None:
    claims = {
        row["claim_id"]: row
        for row in read_csv(DATA / "source-claims.csv")
        if row["country"] == "SEN"
    }

    assert {"sen-plan-project-count-34", "sen-annex-project-count-38"} <= claims.keys()
    assert "34" in claims["sen-plan-project-count-34"]["claim_summary"]
    assert "38" in claims["sen-annex-project-count-38"]["claim_summary"]
    assert {
        claims["sen-plan-project-count-34"]["match_status"],
        claims["sen-annex-project-count-38"]["match_status"],
    } == {"context_only"}
