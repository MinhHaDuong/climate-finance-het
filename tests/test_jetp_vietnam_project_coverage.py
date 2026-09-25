"""Coverage contract for Viet Nam's July 2025 JETP project portfolio."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "jetp"

NAMED_PROJECT_SOURCES = {
    "vnm-project-bac-ai-pumped-hydro": {
        "vnm-moit-project-bac-ai",
        "vnm-evn-cdp-bac-ai-2025",
        "vnm-eib-bac-ai-package-2025",
    },
    "vnm-project-binh-duong-dong-nai-transmission": {
        "vnm-moit-project-binh-duong-dong-nai",
        "vnm-evn-afd-transmission-2025",
    },
    "vnm-project-tri-an-expansion": {
        "vnm-moit-project-tri-an",
        "vnm-evn-kfw-tri-an-2025",
    },
}


pytestmark = pytest.mark.wp_jetp

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_july_2025_portfolio_has_24_source_bounded_project_records() -> None:
    projects = [
        row for row in read_csv(DATA / "migration/0875-projects-legacy.csv") if row["country"] == "VNM"
    ]
    project_ids = {row["project_id"] for row in projects}
    initial_slots = {
        project_id
        for project_id in project_ids
        if project_id.startswith("vnm-project-initial-undisclosed-")
    }
    screened_slots = {
        project_id
        for project_id in project_ids
        if project_id.startswith("vnm-project-screened-undisclosed-")
    }

    assert len(projects) == 24
    assert len(project_ids) == 24
    assert NAMED_PROJECT_SOURCES.keys() <= project_ids
    assert len(initial_slots) == 4
    assert len(screened_slots) == 17
    assert len(initial_slots | screened_slots | NAMED_PROJECT_SOURCES.keys()) == 24


def test_undisclosed_slots_do_not_invent_project_identities() -> None:
    projects = [
        row
        for row in read_csv(DATA / "migration/0875-projects-legacy.csv")
        if row["country"] == "VNM" and "-undisclosed-" in row["project_id"]
    ]

    assert len(projects) == 21
    assert {row["verification_status"] for row in projects} == {
        "official_count_slot"
    }
    for row in projects:
        assert row["technology"] == "Not published"
        assert row["location"] == "Not published"
        assert row["operator"] == "Not published"
        assert "not a claimed project identity" in row["notes"]


def test_every_vietnamese_project_has_a_terminal_followup_verdict() -> None:
    project_ids = {
        row["project_id"]
        for row in read_csv(DATA / "migration/0875-projects-legacy.csv")
        if row["country"] == "VNM"
    }
    coverage = [
        row
        for row in read_csv(DATA / "project-coverage.csv")
        if row["country"] == "VNM"
    ]

    assert len(coverage) == 24
    assert {row["project_id"] for row in coverage} == project_ids
    assert "pending" not in {row["review_status"] for row in coverage}
    assert {row["checked_at"] for row in coverage} == {"2026-09-12"}

    by_id = {row["project_id"]: row for row in coverage}
    for project_id in NAMED_PROJECT_SOURCES:
        assert by_id[project_id]["review_status"] == "collected"
    for project_id, row in by_id.items():
        if "-undisclosed-" in project_id:
            assert row["review_status"] == "not_published"
            assert "identity" in row["notes"].lower()


def test_named_projects_link_direct_moit_and_funder_sources() -> None:
    sources = {
        row["source_id"]: row
        for row in read_csv(DATA / "sources.csv")
        if row["country"] == "VNM"
    }
    coverage = {
        row["project_id"]: row
        for row in read_csv(DATA / "project-coverage.csv")
        if row["country"] == "VNM"
    }
    confirmed_links = {
        (row["project_id"], row["source_id"])
        for row in read_csv(DATA / "project-source-links.csv")
        if row["country"] == "VNM" and row["review_status"] == "confirmed"
    }

    for project_id, expected_sources in NAMED_PROJECT_SOURCES.items():
        assert expected_sources <= sources.keys()
        assert {sources[source_id]["project_id"] for source_id in expected_sources} == {
            project_id
        }
        assert expected_sources <= set(coverage[project_id]["source_ids"].split(";"))
        assert {
            (project_id, source_id) for source_id in expected_sources
        } <= confirmed_links


def test_non_public_project_identities_have_an_explicit_dry_search() -> None:
    searches = {
        row["search_id"]: row
        for row in read_csv(DATA / "dry-searches.csv")
        if row["country"] == "VNM"
    }
    search = searches["vnm-search-undisclosed-project-identities-20260912"]

    assert search["outcome"] == "not_published"
    assert "4" in search["notes"]
    assert "17" in search["notes"]
