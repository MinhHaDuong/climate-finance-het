"""Contract for explicit project-by-project source follow-up."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

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
DIRECT_PORTFOLIO_PIPELINE_SOURCES = {
    "idn-pipe-green-corridors-sulawesi": "idn-portfolio-project-gecs",
    "idn-pipe-nagajaya-micro-hydro": "idn-portfolio-project-nagajaya",
    "idn-pipe-hululais-1-2": "idn-portfolio-project-hululais",
}
PIPELINE_SOURCE_COHORT = {
    "idn-pipe-dieng-3-4": {"idn-project-dieng3-adb"},
    "idn-pipe-cirebon-1-retirement": {
        "idn-project-cirebon-framework-marubeni",
        "idn-news-cirebon-retirement-reuters-2025",
    },
    "idn-pipe-solar-cell-manufacturing": {
        "idn-project-seg-construction-2024",
        "idn-project-seg-operational-2025",
    },
    "idn-pipe-singkarak-floating-solar": {"idn-project-singkarak-acwa-2022"},
    "idn-pipe-sutami-floating-solar": {"idn-project-sutami-construction-plnnp-2026"},
    "idn-pipe-tanah-laut-wind": {
        "idn-project-tanah-laut-plnnp",
        "idn-project-tanah-laut-ppa-ptplnnr",
    },
    "idn-pipe-legok-nangka-waste": {
        "idn-project-legok-agreement-ut-2024",
        "idn-news-legok-groundbreaking-antara-2026",
    },
    "idn-pipe-rsud-energy-efficiency": {"idn-project-rsud-retrofit-c40"},
}
FINAL_PIPELINE_VERDICTS = {
    "idn-monitor-cihaur-talaga-micro-hydro": "central_only",
    "idn-monitor-gde-pipeline-2025": "central_only",
    "idn-pipe-dediesel-east-phase1": "central_only",
    "idn-pipe-dediesel-west-phase1": "collected",
    "idn-pipe-e-taxi": "central_only",
    "idn-pipe-eib-sustainable-infrastructure": "collected",
    "idn-pipe-hijaunesia-2": "collected",
    "idn-pipe-hydro-quota-sulawesi": "collected",
    "idn-pipe-hydro-quota-sumatra": "collected",
    "idn-pipe-rscm-energy-efficiency": "central_only",
}
FINAL_PIPELINE_SOURCES = {
    "idn-pipe-dediesel-west-phase1": {"idn-ibvogt-diesel-west-2023"},
    "idn-pipe-eib-sustainable-infrastructure": {"idn-eib-ptsmi-mou-2024"},
    "idn-pipe-hijaunesia-2": {"idn-jetp-work-plan-2024-presentation"},
    "idn-pipe-hydro-quota-sulawesi": {"idn-jetp-work-plan-2024-presentation"},
    "idn-pipe-hydro-quota-sumatra": {"idn-jetp-work-plan-2024-presentation"},
}
FINAL_PIPELINE_DRY_SEARCHES = {
    "idn-monitor-cihaur-talaga-micro-hydro": "idn-search-cihaur-talaga-20260912",
    "idn-monitor-gde-pipeline-2025": "idn-search-gde-pipeline-20260912",
    "idn-pipe-dediesel-east-phase1": "idn-search-dediesel-east-20260912",
    "idn-pipe-e-taxi": "idn-search-e-taxi-20260912",
    "idn-pipe-rscm-energy-efficiency": "idn-search-rscm-efficiency-20260912",
}


pytestmark = pytest.mark.wp_jetp

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_every_indonesian_project_has_a_followup_row() -> None:
    project_ids = {
        row["project_id"]
        for row in read_csv(DATA / "migration/0875-projects-legacy.csv")
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
        assert {
            (project_id, source_id) for source_id in reviewed_sources
        } <= linked_pairs
    assert DIRECTLY_SOURCED_APPROVED_FINANCE_PROJECTS <= claimed_projects


def test_indonesian_grants_link_the_direct_official_portfolio() -> None:
    grant_projects = {
        row["project_id"]
        for row in read_csv(DATA / "migration/0875-projects-legacy.csv")
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


def test_current_portfolio_pipeline_profiles_are_reviewed_and_archived() -> None:
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
    archived = {
        row["source_id"]
        for row in read_csv(DATA / "manifest.csv")
        if row["status"] in {"collected", "not_modified"} and row["sha256"]
    }

    for project_id, source_id in DIRECT_PORTFOLIO_PIPELINE_SOURCES.items():
        row = coverage[project_id]
        assert row["review_status"] == "collected", project_id
        assert source_id in row["source_ids"].split(";"), project_id
        assert sources[source_id]["project_id"] == project_id
        assert sources[source_id]["url"].startswith(
            "https://portfolio.jetp.id/project/"
        )
        assert source_id in archived


def test_pipeline_source_cohort_is_reviewed_and_archived() -> None:
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
    manifest = {row["source_id"]: row for row in read_csv(DATA / "manifest.csv")}

    for project_id, source_ids in PIPELINE_SOURCE_COHORT.items():
        row = coverage[project_id]
        expected_status = (
            "blocked"
            if project_id in {"idn-pipe-dieng-3-4", "idn-pipe-rsud-energy-efficiency"}
            else "collected"
        )
        assert row["review_status"] == expected_status, project_id
        assert row["checked_at"] == "2026-09-12", project_id
        assert source_ids <= set(row["source_ids"].split(";")), project_id
        for source_id in source_ids:
            assert sources[source_id]["project_id"] == project_id
            assert manifest[source_id]["status"] in {
                "collected",
                "not_modified",
                "blocked",
            }
            if manifest[source_id]["status"] in {"collected", "not_modified"}:
                assert manifest[source_id]["sha256"]


def test_final_pipeline_cohort_has_terminal_evidence_verdicts() -> None:
    coverage = {
        row["project_id"]: row
        for row in read_csv(DATA / "project-coverage.csv")
        if row["country"] == "IDN"
    }
    archived = {
        row["source_id"]
        for row in read_csv(DATA / "manifest.csv")
        if row["status"] in {"collected", "not_modified"} and row["sha256"]
    }
    searches = {
        row["search_id"]: row
        for row in read_csv(DATA / "dry-searches.csv")
        if row["country"] == "IDN"
    }

    assert len(coverage) == 74
    assert not {
        row["project_id"]
        for row in coverage.values()
        if row["review_status"] == "pending"
    }
    for project_id, verdict in FINAL_PIPELINE_VERDICTS.items():
        row = coverage[project_id]
        assert row["review_status"] == verdict, project_id
        assert row["checked_at"] == "2026-09-12", project_id

    for project_id, source_ids in FINAL_PIPELINE_SOURCES.items():
        assert source_ids <= set(coverage[project_id]["source_ids"].split(";"))
        assert source_ids <= archived

    for project_id, search_id in FINAL_PIPELINE_DRY_SEARCHES.items():
        assert search_id in searches, project_id
        assert searches[search_id]["outcome"] == "central_only", project_id


def test_the_vietnamese_count_slot_sources_have_a_recorded_collection_attempt() -> None:
    """Every source behind the 21 counted Viet Nam slots has a registry row.

    The 21 official_count_slot rows all cite the same source triplet; two of
    those sources sat in sources.csv without any collection attempt (ticket
    0859). The registry is append-only provenance: an attempt is a row with a
    named status — `collected`, or a failure the collector wrote itself —
    never a row invented to fill the gap, and never no row at all.
    """
    slot_ids = {
        row["project_id"]
        for row in read_csv(DATA / "migration/0875-projects-legacy.csv")
        if row["country"] == "VNM" and row["verification_status"] == "official_count_slot"
    }
    assert len(slot_ids) == 21

    cited = set()
    for row in read_csv(DATA / "project-coverage.csv"):
        if row["project_id"] in slot_ids:
            cited |= {item for item in row["source_ids"].split(";") if item}
    assert {"vnm-eeas-jetp-project-progress-2025", "vnm-moit-project-index-2026"} <= cited

    attempts: dict[str, set[str]] = {}
    for row in read_csv(DATA / "manifest.csv"):
        attempts.setdefault(row["source_id"], set()).add(row["status"])

    for source_id in sorted(cited):
        assert source_id in attempts, f"{source_id}: no collection attempt in manifest.csv"
        assert attempts[source_id], source_id
        assert "" not in attempts[source_id], f"{source_id}: attempt without a status"
