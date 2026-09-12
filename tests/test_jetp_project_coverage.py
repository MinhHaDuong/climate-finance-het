"""Contract for explicit project-by-project source follow-up."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "jetp"

REVIEW_STATUSES = {
    "pending",
    "collected",
    "central_only",
    "blocked",
    "not_published",
    "not_applicable",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_every_indonesian_project_has_a_followup_row() -> None:
    project_ids = {
        row["project_id"]
        for row in read_csv(DATA / "projects.csv")
        if row["country"] == "IDN"
    }
    coverage = [
        row
        for row in read_csv(DATA / "project-coverage.csv")
        if row["country"] == "IDN"
    ]

    assert len(project_ids) == 74
    assert len(coverage) == 74
    assert {row["project_id"] for row in coverage} == project_ids
    assert len({row["project_id"] for row in coverage}) == len(coverage)
    assert {row["review_status"] for row in coverage} <= REVIEW_STATUSES


def test_project_followup_sources_resolve_to_the_registry() -> None:
    source_ids = {row["source_id"] for row in read_csv(DATA / "sources.csv")}
    coverage = [
        row
        for row in read_csv(DATA / "project-coverage.csv")
        if row["country"] == "IDN"
    ]

    for row in coverage:
        linked = {item for item in row["source_ids"].split(";") if item}
        assert linked <= source_ids
        assert linked, row["project_id"]
        if row["review_status"] != "pending":
            assert row["checked_at"], row["project_id"]
            assert row["query_or_route"], row["project_id"]
