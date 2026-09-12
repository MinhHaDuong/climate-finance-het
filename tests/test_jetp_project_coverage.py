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

APPROVED_FINANCE_PROJECTS = {
    "idn-fin-isle-1",
    "idn-fin-mrt-east-west",
    "idn-fin-mrt-north-south",
    "idn-fin-muara-laboh-2",
    "idn-fin-pbl-aset",
    "idn-fin-rbl-aicet",
    "idn-fin-rbl-sreap",
    "idn-fin-saguling-floating-solar",
    "idn-fin-xurya-rooftop",
}
DIRECTLY_SOURCED_APPROVED_FINANCE_PROJECTS = APPROVED_FINANCE_PROJECTS - {
    "idn-fin-rbl-sreap"
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


def test_indonesian_approved_finance_projects_have_been_reviewed() -> None:
    coverage = {
        row["project_id"]: row
        for row in read_csv(DATA / "project-coverage.csv")
        if row["country"] == "IDN"
    }

    assert APPROVED_FINANCE_PROJECTS <= coverage.keys()
    for project_id in APPROVED_FINANCE_PROJECTS:
        row = coverage[project_id]
        assert row["review_status"] != "pending", project_id
        assert row["checked_at"] == "2026-09-12", project_id
        assert row["query_or_route"], project_id

    assert coverage["idn-fin-rbl-sreap"]["review_status"] == "central_only"


def test_reviewed_approved_finance_projects_link_direct_sources() -> None:
    coverage = {
        row["project_id"]: row
        for row in read_csv(DATA / "project-coverage.csv")
        if row["country"] == "IDN"
    }
    direct_sources: dict[str, set[str]] = {}
    for source in read_csv(DATA / "sources.csv"):
        if source["country"] == "IDN" and source["project_id"]:
            direct_sources.setdefault(source["project_id"], set()).add(
                source["source_id"]
            )

    for project_id in DIRECTLY_SOURCED_APPROVED_FINANCE_PROJECTS:
        linked = {
            source_id
            for source_id in coverage[project_id]["source_ids"].split(";")
            if source_id
        }
        assert linked & direct_sources.get(project_id, set()), project_id


def test_direct_approved_finance_sources_are_adjudicated_and_summarized() -> None:
    coverage = {
        row["project_id"]: row
        for row in read_csv(DATA / "project-coverage.csv")
        if row["country"] == "IDN"
    }
    direct_sources = {
        row["source_id"]
        for row in read_csv(DATA / "sources.csv")
        if row["country"] == "IDN"
        and row["project_id"] in DIRECTLY_SOURCED_APPROVED_FINANCE_PROJECTS
    }
    linked_pairs = {
        (row["project_id"], row["source_id"])
        for row in read_csv(DATA / "project-source-links.csv")
        if row["country"] == "IDN" and row["review_status"] == "confirmed"
    }
    claimed_projects = {
        project_id
        for row in read_csv(DATA / "source-claims.csv")
        if row["country"] == "IDN" and row["source_id"] in direct_sources
        for project_id in row["matched_project_ids"].split(";")
        if project_id
    }

    for project_id in DIRECTLY_SOURCED_APPROVED_FINANCE_PROJECTS:
        reviewed_sources = {
            source_id
            for source_id in coverage[project_id]["source_ids"].split(";")
            if source_id in direct_sources
        }
        assert reviewed_sources, project_id
        assert {(project_id, source_id) for source_id in reviewed_sources} <= linked_pairs
    assert DIRECTLY_SOURCED_APPROVED_FINANCE_PROJECTS <= claimed_projects


def test_indonesian_grants_link_the_direct_official_portfolio() -> None:
    grant_projects = {
        row["project_id"]
        for row in read_csv(DATA / "projects.csv")
        if row["country"] == "IDN" and row["project_id"].startswith("idn-grant-")
    }
    coverage = {
        row["project_id"]: row
        for row in read_csv(DATA / "project-coverage.csv")
        if row["country"] == "IDN"
    }
    sources = {
        row["source_id"]: row
        for row in read_csv(DATA / "sources.csv")
        if row["country"] == "IDN"
    }

    assert len(grant_projects) == 44
    for project_id in grant_projects:
        row = coverage[project_id]
        assert row["review_status"] == "collected", project_id
        assert row["checked_at"] == "2026-09-12", project_id
        direct = [
            sources[source_id]
            for source_id in row["source_ids"].split(";")
            if source_id in sources
            and sources[source_id]["url"].startswith(
                "https://portfolio.jetp.id/program/"
            )
        ]
        assert direct, project_id
        assert {source["project_id"] for source in direct} == {project_id}
