"""Project-identity and follow-up contract for Senegal's 2025 JETP plan."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "jetp"

ANNEX_SOURCE = "sen-investment-plan-annexes-mirror"
MAIN_SOURCE = "sen-investment-plan-l4-mirror"
QW_TO_ANNEX = {
    4: 7,
    5: 11,
    6: 17,
    7: 19,
    9: 16,
    11: 20,
}
STANDALONE_QUICK_WINS = {1, 2, 3, 8, 10}
TERMINAL_VERDICTS = {
    "collected",
    "central_only",
    "blocked",
    "not_published",
    "not_applicable",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_plan_lines_resolve_to_43_nonduplicated_projects() -> None:
    projects = [
        row for row in read_csv(DATA / "projects.csv") if row["country"] == "SEN"
    ]
    project_ids = {row["project_id"] for row in projects}
    plan_rows = [
        row
        for row in read_csv(DATA / "plan-projects.csv")
        if row["country"] == "SEN"
        and row["source_id"] in {ANNEX_SOURCE, MAIN_SOURCE}
    ]

    assert len(projects) == 43
    assert len(project_ids) == 43
    assert len(plan_rows) == 49
    assert {row["reconciliation_status"] for row in plan_rows} == {"matched"}
    assert {row["canonical_project_id"] for row in plan_rows} == project_ids


def test_quick_win_crosswalk_uses_only_plan_demonstrated_matches() -> None:
    rows = {
        int(row["ordinal"]): row
        for row in read_csv(DATA / "plan-projects.csv")
        if row["country"] == "SEN"
        and row["source_id"] == MAIN_SOURCE
        and row["technology_group"] == "quick_win"
    }

    for quick_win, annex_ordinal in QW_TO_ANNEX.items():
        assert rows[quick_win]["canonical_project_id"] == (
            f"sen-project-annex-{annex_ordinal:02d}"
        )
        assert "crosswalk" in rows[quick_win]["notes"].lower()
    for quick_win in STANDALONE_QUICK_WINS:
        assert rows[quick_win]["canonical_project_id"] == (
            f"sen-project-qw-{quick_win:02d}"
        )


def test_every_senegal_project_has_a_terminal_followup_verdict() -> None:
    project_ids = {
        row["project_id"]
        for row in read_csv(DATA / "projects.csv")
        if row["country"] == "SEN"
    }
    coverage = [
        row
        for row in read_csv(DATA / "project-coverage.csv")
        if row["country"] == "SEN"
    ]

    assert len(coverage) == 43
    assert {row["project_id"] for row in coverage} == project_ids
    assert {row["review_status"] for row in coverage} <= TERMINAL_VERDICTS
    assert {row["checked_at"] for row in coverage} == {"2026-09-12"}
    assert all(row["query_or_route"] for row in coverage)


def test_collected_project_verdicts_resolve_to_direct_sources() -> None:
    sources = {
        row["source_id"]: row
        for row in read_csv(DATA / "sources.csv")
        if row["country"] == "SEN"
    }
    coverage = [
        row
        for row in read_csv(DATA / "project-coverage.csv")
        if row["country"] == "SEN" and row["review_status"] == "collected"
    ]
    links = {
        (row["project_id"], row["source_id"])
        for row in read_csv(DATA / "project-source-links.csv")
        if row["country"] == "SEN" and row["review_status"] == "confirmed"
    }

    for row in coverage:
        direct = {
            source_id
            for source_id in row["source_ids"].split(";")
            if source_id in sources
            and sources[source_id]["project_id"] == row["project_id"]
        }
        assert direct, row["project_id"]
        assert {(row["project_id"], source_id) for source_id in direct} <= links
