"""Integrity rules for claims extracted from JETP reports and official news."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "jetp"
CLAIMS = DATA / "source-claims.csv"
LINKS = DATA / "project-source-links.csv"

MATCH_STATUSES = {"matched", "partial", "not_in_register", "context_only"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def split_ids(value: str) -> set[str]:
    return {item for item in value.split(";") if item}


def test_source_claims_reference_known_sources_and_projects() -> None:
    claims = read_csv(CLAIMS)
    source_ids = {row["source_id"] for row in read_csv(DATA / "sources.csv")}
    project_ids = {row["project_id"] for row in read_csv(DATA / "projects.csv")}

    assert claims
    assert len({row["claim_id"] for row in claims}) == len(claims)
    assert {row["source_id"] for row in claims} <= source_ids
    assert {row["match_status"] for row in claims} <= MATCH_STATUSES

    for row in claims:
        matched = split_ids(row["matched_project_ids"])
        assert matched <= project_ids
        if row["match_status"] in {"matched", "partial"}:
            assert matched, row["claim_id"]
        if row["match_status"] in {"not_in_register", "context_only"}:
            assert not matched, row["claim_id"]


def test_matched_claim_projects_have_document_links() -> None:
    links = {
        (row["source_id"], row["project_id"])
        for row in read_csv(LINKS)
    }

    for claim in read_csv(CLAIMS):
        for project_id in split_ids(claim["matched_project_ids"]):
            assert (claim["source_id"], project_id) in links, claim["claim_id"]


def test_project_report_reviews_capture_key_verifiable_claims() -> None:
    claims = {row["claim_id"]: row for row in read_csv(CLAIMS)}
    expected = {
        "zaf-growth26-pipeline",
        "zaf-growth26-funnel",
        "zaf-growth26-investment-need",
        "zaf-eepbip23-duration",
        "zaf-eepbip23-guarantee",
        "zaf-eepbip23-jobs-target",
        "zaf-eepbip-maf-funding",
    }

    assert expected <= claims.keys()
    assert {claims[claim_id]["match_status"] for claim_id in expected} == {"matched"}


def test_2025_annex_review_covers_every_portfolio_section() -> None:
    rows = [
        row
        for row in read_csv(CLAIMS)
        if row["source_id"] == "zaf-jetp-leaders-2025-annex"
    ]

    assert {
        "Electricity",
        "Green hydrogen",
        "New energy vehicles",
        "Municipalities",
        "Just",
        "Skills",
        "Road to Rail",
        "Energy Efficiency",
    } <= {row["section"] for row in rows}
    unresolved = {
        row["claim_id"] for row in rows if row["match_status"] == "not_in_register"
    }
    assert not unresolved
    assert {
        row["matched_project_ids"]
        for row in rows
        if row["claim_id"] == "zaf-annex25-uk-nev"
    } == {"zaf-uk-nev-support"}
    assert {
        row["matched_project_ids"]
        for row in rows
        if row["claim_id"] == "zaf-annex25-eu-cso-grants"
    } == {"zaf-eu-cso-green-economy-grants"}
