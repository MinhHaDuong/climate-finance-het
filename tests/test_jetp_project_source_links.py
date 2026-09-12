"""Integrity rules for project-level evidence links in the JETP ledger."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "jetp"
LINKS = DATA / "project-source-links.csv"

RELATIONSHIPS = {
    "project_page",
    "project_page_component",
    "project_report",
    "approval_document",
    "data_portal",
    "named_in",
    "possible_match",
}
REVIEW_STATUSES = {"confirmed", "provisional", "unreviewed"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_project_source_links_reference_canonical_records() -> None:
    links = read_csv(LINKS)
    projects = read_csv(DATA / "projects.csv")
    sources = read_csv(DATA / "sources.csv")
    project_ids = {row["project_id"] for row in projects}
    source_ids = {row["source_id"] for row in sources}

    assert links
    assert len({row["link_id"] for row in links}) == len(links)
    assert {row["project_id"] for row in links} <= project_ids
    assert {row["source_id"] for row in links} <= source_ids
    assert {row["relationship"] for row in links} <= RELATIONSHIPS
    assert {row["review_status"] for row in links} <= REVIEW_STATUSES


def test_zaf_project_pages_are_evidence_not_duplicate_projects() -> None:
    projects = [
        row for row in read_csv(DATA / "projects.csv") if row["country"] == "ZAF"
    ]
    links = [row for row in read_csv(LINKS) if row["country"] == "ZAF"]
    project_page_sources = {
        row["source_id"]
        for row in read_csv(DATA / "sources.csv")
        if row["country"] == "ZAF" and row["source_id"].startswith("zaf-project-")
    }

    register_projects = [
        row for row in projects if row["project_id"].startswith("zaf-register-")
    ]
    assert len(register_projects) == 257
    assert not any(row["project_id"].startswith("zaf-jetpmu-") for row in projects)
    assert {
        "zaf-annex-zandkopsdrift",
        "zaf-growth-gateway-smme-accelerator",
        "zaf-murp",
        "zaf-eepbip",
        "zaf-uk-nev-support",
    } <= {row["project_id"] for row in projects}
    assert project_page_sources <= {row["source_id"] for row in links}
    assert not any(row["project_id"].startswith("zaf-jetpmu-") for row in links)
