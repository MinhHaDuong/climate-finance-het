"""Coverage contract for the Indonesian JETP source timeline."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "jetp"

REPORT_SERIES_2025 = {
    "idn-jetp-progress-report-2025",
    "idn-jetp-energy-efficiency-electrification-2025",
    "idn-jetp-captive-power-study-2025",
    "idn-jetp-just-transition-study-2025",
    "idn-jetp-guarantees-insurance-2025",
    "idn-jetp-small-scale-renewables-finance-2025",
    "idn-jetp-carbon-pricing-2025",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_indonesia_timeline_covers_launch_plan_and_2025_reports() -> None:
    rows = [row for row in read_csv(DATA / "sources.csv") if row["country"] == "IDN"]
    by_id = {row["source_id"]: row for row in rows}

    assert {
        "idn-jetp-joint-statement-2022",
        "idn-cipp-2023-cpr-mirror",
        "idn-cmea-progress-march-2025",
        "idn-cmea-progress-december-2025",
        *REPORT_SERIES_2025,
    } <= by_id.keys()
    assert {by_id[source_id]["active"] for source_id in REPORT_SERIES_2025} == {
        "true"
    }
    assert {
        by_id[source_id]["published_date"][:4] for source_id in REPORT_SERIES_2025
    } == {"2025"}


def test_indonesia_2025_report_series_is_archived() -> None:
    material = {
        row["source_id"]
        for row in read_csv(DATA / "manifest.csv")
        if row["country"] == "IDN"
        and row["status"] in {"collected", "not_modified"}
        and row["sha256"]
    }

    assert REPORT_SERIES_2025 <= material


def test_indonesia_2025_approved_portfolio_is_project_level() -> None:
    all_projects = [
        row for row in read_csv(DATA / "projects.csv") if row["country"] == "IDN"
    ]
    projects = [
        row
        for row in all_projects
        if row["project_id"].startswith(("idn-fin-", "idn-grant-"))
    ]
    events = [
        row
        for row in read_csv(DATA / "events.csv")
        if row["country"] == "IDN" and row["financial_status"] == "approved"
    ]
    progress_projects = {
        row["project_id"]
        for row in events
        if row["source_id"] == "idn-jetp-progress-report-2025"
    }

    assert len(projects) == 53
    assert len({row["project_id"] for row in projects}) == 53
    assert len([row for row in projects if row["project_id"].startswith("idn-fin-")]) == 9
    assert len([row for row in projects if row["project_id"].startswith("idn-grant-")]) == 44
    assert {row["project_id"] for row in projects} == progress_projects
    assert len(events) == 59
    assert {row["financial_status"] for row in events} == {"approved"}
    assert {
        "idn-fin-muara-laboh-2",
        "idn-fin-saguling-floating-solar",
        "idn-fin-xurya-rooftop",
        "idn-grant-wolcot",
        "idn-grant-patuha-2",
        "idn-grant-jetp-etp",
        "idn-grant-ietf",
    } <= {row["project_id"] for row in projects}


def test_indonesia_2025_finance_pipeline_is_project_level() -> None:
    projects = [
        row
        for row in read_csv(DATA / "projects.csv")
        if row["country"] == "IDN" and row["project_id"].startswith("idn-pipe-")
    ]
    events = [
        row
        for row in read_csv(DATA / "events.csv")
        if row["country"] == "IDN"
        and row["source_id"] == "idn-jetp-progress-report-2025"
        and row["financial_status"] != "approved"
    ]

    assert len(projects) == 19
    assert len(events) == 20
    assert len({row["project_id"] for row in events}) == 20
    assert {row["financial_status"] for row in events} == {"announced", "mou"}
    assert {row["project_id"] for row in projects} | {"idn-fin-rbl-aicet"} == {
        row["project_id"] for row in events
    }


def test_indonesia_temporal_totals_are_preserved_not_overwritten() -> None:
    claims = {
        row["claim_id"]: row
        for row in read_csv(DATA / "source-claims.csv")
        if row["country"] == "IDN"
    }
    searches = {
        row["search_id"]: row
        for row in read_csv(DATA / "dry-searches.csv")
        if row["country"] == "IDN"
    }

    assert {
        "idn-cmea-mar25-approved-aggregate",
        "idn-progress25-approved-aggregate",
        "idn-progress25-approved-grants",
        "idn-progress25-finance-in-process",
    } <= claims.keys()
    assert {row["match_status"] for row in claims.values()} == {"context_only"}
    assert "54" in claims["idn-cmea-mar25-approved-aggregate"]["claim_summary"]
    assert "53" in claims["idn-progress25-approved-aggregate"]["claim_summary"]
    assert "idn-search-official-portfolio-20260912" in searches
    assert searches["idn-search-official-portfolio-20260912"]["outcome"] == "blocked"


def test_cirebon_finance_and_physical_retirement_are_distinct() -> None:
    implementation = {
        row["project_id"]: row
        for row in read_csv(DATA / "implementation-events.csv")
        if row["country"] == "IDN"
    }
    finance = [
        row
        for row in read_csv(DATA / "events.csv")
        if row["project_id"] == "idn-pipe-cirebon-1-retirement"
    ]

    assert implementation["idn-pipe-cirebon-1-retirement"][
        "implementation_status"
    ] == "closure_proposed"
    assert implementation["idn-pipe-cirebon-1-retirement"]["capacity_mw"] == "660"
    assert {row["financial_status"] for row in finance} <= {"announced", "mou"}
    assert not ({"approved", "signed", "disbursed"} & {
        row["financial_status"] for row in finance
    })
