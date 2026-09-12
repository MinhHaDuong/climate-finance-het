"""Coverage contract for the Indonesian JETP sources and authorities."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "jetp"
COVERAGE = DATA / "authority-coverage.csv"
SOURCES = DATA / "sources.csv"

REPORT_SERIES_2025 = {
    "idn-jetp-progress-report-2025",
    "idn-jetp-energy-efficiency-electrification-2025",
    "idn-jetp-captive-power-study-2025",
    "idn-jetp-just-transition-study-2025",
    "idn-jetp-guarantees-insurance-2025",
    "idn-jetp-small-scale-renewables-finance-2025",
    "idn-jetp-carbon-pricing-2025",
}

TERMINAL_VERDICTS = {
    "collected",
    "not_published",
    "blocked",
    "not_applicable",
}

# The 2025 Progress Report names the national bodies, current and former IPG
# members, GFANZ, and public finance institutions below. Country-level rows do
# not replace institution-level rows where an implementing financier is named.
REQUIRED_IDN_AUTHORITIES = {
    "idn-cmea-task-force",
    "idn-jetp-secretariat",
    "idn-memr",
    "idn-pln",
    "idn-ipg",
    "idn-gfanz",
    "idn-canada",
    "idn-denmark",
    "idn-eu",
    "idn-france",
    "idn-germany",
    "idn-italy",
    "idn-japan",
    "idn-norway",
    "idn-uk",
    "idn-us-historical",
    "idn-adb",
    "idn-world-bank-group",
    "idn-afd",
    "idn-kfw",
    "idn-jica",
    "idn-jbic",
    "idn-eib",
    "idn-cif-act-etm",
    "idn-bii",
    "idn-norfund",
    "idn-eifo-dsif-ifu",
    "idn-pidg-guarantco",
    "idn-deg-proparco",
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
    assert {by_id[source_id]["active"] for source_id in REPORT_SERIES_2025} == {"true"}
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
        if row["country"] == "IDN"
        and row["financial_status"] == "approved"
        and row["source_id"] == "idn-jetp-progress-report-2025"
    ]
    progress_projects = {
        row["project_id"]
        for row in events
        if row["source_id"] == "idn-jetp-progress-report-2025"
    }

    assert len(projects) == 53
    assert len({row["project_id"] for row in projects}) == 53
    assert (
        len([row for row in projects if row["project_id"].startswith("idn-fin-")]) == 9
    )
    assert (
        len([row for row in projects if row["project_id"].startswith("idn-grant-")])
        == 44
    )
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


def test_current_portfolio_preserves_three_post_report_approvals() -> None:
    events = [
        row
        for row in read_csv(DATA / "events.csv")
        if row["country"] == "IDN"
        and row["project_id"]
        in {
            "idn-pipe-green-corridors-sulawesi",
            "idn-pipe-nagajaya-micro-hydro",
            "idn-pipe-hululais-1-2",
        }
    ]
    by_project: dict[str, list[dict[str, str]]] = {}
    for event in events:
        by_project.setdefault(event["project_id"], []).append(event)

    for project_events in by_project.values():
        assert {row["financial_status"] for row in project_events} == {
            "announced",
            "approved",
        }

    approved = {
        row["project_id"]: row
        for row in events
        if row["financial_status"] == "approved"
    }
    assert approved["idn-pipe-green-corridors-sulawesi"]["amount_original"] == (
        "300000000"
    )
    assert approved["idn-pipe-green-corridors-sulawesi"]["currency_original"] == ("EUR")
    assert approved["idn-pipe-nagajaya-micro-hydro"]["amount_original"] == ("1260000")
    assert approved["idn-pipe-nagajaya-micro-hydro"]["currency_original"] == "USD"
    assert approved["idn-pipe-hululais-1-2"]["amount_original"] == "29156000000"
    assert approved["idn-pipe-hululais-1-2"]["currency_original"] == "JPY"


def test_nagajaya_source_specific_capacity_is_not_flattened() -> None:
    rows = [
        row
        for row in read_csv(DATA / "implementation-events.csv")
        if row["project_id"] == "idn-pipe-nagajaya-micro-hydro"
    ]

    assert {row["capacity_mw"] for row in rows} == {"6", "6.5"}
    assert {row["source_id"] for row in rows} == {
        "idn-jetp-progress-report-2025",
        "idn-portfolio-project-nagajaya",
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

    aggregate_ids = {
        "idn-cmea-mar25-approved-aggregate",
        "idn-progress25-approved-aggregate",
        "idn-progress25-approved-grants",
        "idn-progress25-finance-in-process",
    }
    assert aggregate_ids <= claims.keys()
    assert {claims[claim_id]["match_status"] for claim_id in aggregate_ids} == {
        "context_only"
    }
    assert "54" in claims["idn-cmea-mar25-approved-aggregate"]["claim_summary"]
    assert "53" in claims["idn-progress25-approved-aggregate"]["claim_summary"]
    assert "idn-search-official-portfolio-20260912" in searches
    assert searches["idn-search-official-portfolio-20260912"]["outcome"] == "blocked"


def test_cirebon_finance_and_physical_retirement_are_distinct() -> None:
    implementation = [
        row
        for row in read_csv(DATA / "implementation-events.csv")
        if row["project_id"] == "idn-pipe-cirebon-1-retirement"
    ]
    finance = [
        row
        for row in read_csv(DATA / "events.csv")
        if row["project_id"] == "idn-pipe-cirebon-1-retirement"
    ]

    assert {row["implementation_status"] for row in implementation} == {
        "closure_proposed",
        "suspended",
    }
    assert {row["capacity_mw"] for row in implementation} == {"660"}
    assert {row["financial_status"] for row in finance} <= {"announced", "mou"}
    assert not (
        {"approved", "signed", "disbursed"}
        & {row["financial_status"] for row in finance}
    )


def test_pipeline_updates_preserve_source_specific_status_history() -> None:
    rows = [
        row
        for row in read_csv(DATA / "implementation-events.csv")
        if row["project_id"]
        in {
            "idn-pipe-solar-cell-manufacturing",
            "idn-pipe-sutami-floating-solar",
            "idn-pipe-legok-nangka-waste",
        }
    ]
    statuses: dict[str, set[str]] = {}
    for row in rows:
        statuses.setdefault(row["project_id"], set()).add(
            row["implementation_status"]
        )

    assert statuses["idn-pipe-solar-cell-manufacturing"] == {
        "construction",
        "operational",
    }
    assert statuses["idn-pipe-sutami-floating-solar"] == {
        "procurement",
        "construction",
    }
    assert statuses["idn-pipe-legok-nangka-waste"] == {
        "proposed",
        "construction",
    }


def test_cmea_selected_monitoring_list_is_fully_reconciled() -> None:
    links = [
        row
        for row in read_csv(DATA / "project-source-links.csv")
        if row["country"] == "IDN"
        and row["source_id"] == "idn-jetp-progress-report-2025"
        and row["relationship"] == "cmea_selected_monitoring"
    ]
    claims = [
        row
        for row in read_csv(DATA / "source-claims.csv")
        if row["country"] == "IDN"
        and row["source_id"] == "idn-jetp-progress-report-2025"
        and row["section"] == "Appendix 2"
    ]

    assert len(links) == 14
    assert len(claims) == 14
    assert {row["match_status"] for row in claims} == {"matched"}
    assert {
        "idn-pipe-green-corridors-sulawesi",
        "idn-pipe-dediesel-east-phase1",
        "idn-pipe-dediesel-west-phase1",
        "idn-pipe-singkarak-floating-solar",
        "idn-fin-saguling-floating-solar",
        "idn-pipe-hijaunesia-2",
        "idn-monitor-gde-pipeline-2025",
        "idn-pipe-sutami-floating-solar",
        "idn-pipe-cirebon-1-retirement",
        "idn-pipe-hululais-1-2",
        "idn-pipe-solar-cell-manufacturing",
        "idn-pipe-rsud-energy-efficiency",
        "idn-pipe-rscm-energy-efficiency",
        "idn-monitor-cihaur-talaga-micro-hydro",
    } == {row["project_id"] for row in links}


def test_indonesia_authority_matrix_is_terminal_and_sourced() -> None:
    rows = [row for row in read_csv(COVERAGE) if row["country"] == "IDN"]
    by_id = {row["authority_id"]: row for row in rows}

    assert REQUIRED_IDN_AUTHORITIES <= by_id.keys()
    assert all(row["verdict"] in TERMINAL_VERDICTS for row in rows)

    source_ids = {row["source_id"] for row in read_csv(SOURCES)}
    for row in rows:
        linked = {item for item in row["source_ids"].split(";") if item}
        assert linked <= source_ids
        if row["verdict"] == "collected":
            assert linked, row["authority_id"]


def test_every_official_indonesian_project_has_a_source() -> None:
    projects = [
        row
        for row in read_csv(ROOT / "data" / "jetp" / "projects.csv")
        if row["country"] == "IDN"
    ]
    known_source_ids = {row["source_id"] for row in read_csv(SOURCES)}
    direct = {
        row["project_id"]
        for row in read_csv(SOURCES)
        if row["country"] == "IDN" and row["project_id"]
    }
    event_linked = {
        row["project_id"]
        for row in read_csv(ROOT / "data" / "jetp" / "events.csv")
        if row["country"] == "IDN" and row["source_id"] in known_source_ids
    }
    source_linked = {
        row["project_id"]
        for row in read_csv(ROOT / "data" / "jetp" / "project-source-links.csv")
        if row["country"] == "IDN" and row["source_id"] in known_source_ids
    }

    assert len(projects) == 74
    assert {row["project_id"] for row in projects} <= (
        direct | event_linked | source_linked
    )
