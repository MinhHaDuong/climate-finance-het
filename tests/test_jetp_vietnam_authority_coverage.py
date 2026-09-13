"""Coverage contract for ADB and BII in the Viet Nam JETP source universe."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "jetp"

EXPECTED_SOURCES = {
    "vnm-adb": {
        "vnm-adb-vinfast-55327-001",
        "vnm-adb-bess-58382-001",
        "vnm-adb-vinfast-news-2022",
    },
    "vnm-bii": {
        "vnm-bii-vpbank-2025",
        "vnm-vpbank-sustainable-finance-2025",
        "vnm-iati-bii-publisher",
    },
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_adb_and_bii_have_terminal_authority_verdicts() -> None:
    rows = {
        row["authority_id"]: row
        for row in read_csv(DATA / "authority-coverage.csv")
        if row["country"] == "VNM"
    }
    source_ids = {row["source_id"] for row in read_csv(DATA / "sources.csv")}

    assert EXPECTED_SOURCES.keys() <= rows.keys()
    assert rows["vnm-adb"]["verdict"] == "blocked"
    assert rows["vnm-bii"]["verdict"] == "collected"
    for authority_id, expected_sources in EXPECTED_SOURCES.items():
        row = rows[authority_id]
        assert expected_sources <= set(row["source_ids"].split(";"))
        assert expected_sources <= source_ids
        assert row["checked_at"] == "2026-09-12"


def test_adb_and_bii_leads_are_not_forced_into_the_strict_24() -> None:
    sources = {
        row["source_id"]: row
        for row in read_csv(DATA / "sources.csv")
        if row["country"] == "VNM"
    }

    for source_ids in EXPECTED_SOURCES.values():
        assert {sources[source_id]["project_id"] for source_id in source_ids} == {
            ""
        }
    assert sources["vnm-adb-vinfast-55327-001"]["source_type"] == "project_page"
    assert sources["vnm-adb-bess-58382-001"]["source_type"] == "project_page"
    assert sources["vnm-bii-vpbank-2025"]["source_type"] == "official_news"
    assert sources["vnm-iati-bii-publisher"]["source_type"] == "data_portal"


def test_unresolved_adb_and_bii_jetp_matching_is_explicit() -> None:
    searches = {
        row["search_id"]: row
        for row in read_csv(DATA / "dry-searches.csv")
        if row["country"] == "VNM"
    }

    adb = searches["vnm-search-adb-jetp-allocation-20260912"]
    bii = searches["vnm-search-bii-iati-jetp-allocation-20260912"]
    assert adb["outcome"] == "blocked"
    assert "403" in adb["notes"]
    assert bii["outcome"] == "partial"
    assert "IATI" in bii["notes"]
    assert "JETP" in bii["notes"]
