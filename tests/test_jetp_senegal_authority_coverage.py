"""Authority and publication-series coverage contract for Senegal's JETP."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "jetp"

REQUIRED_AUTHORITIES = {
    "sen-mepm",
    "sen-jetp-secretariat",
    "sen-ipg",
    "sen-france-afd",
    "sen-germany-kfw",
    "sen-eu",
    "sen-uk",
    "sen-canada",
    "sen-afdb",
    "sen-world-bank-group",
    "sen-eib",
    "sen-senelec",
}
TERMINAL_VERDICTS = {
    "collected",
    "not_published",
    "blocked",
    "not_applicable",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_required_senegal_authorities_have_terminal_verdicts() -> None:
    rows = {
        row["authority_id"]: row
        for row in read_csv(DATA / "authority-coverage.csv")
        if row["country"] == "SEN"
    }
    source_ids = {row["source_id"] for row in read_csv(DATA / "sources.csv")}

    assert REQUIRED_AUTHORITIES <= rows.keys()
    for authority_id in REQUIRED_AUTHORITIES:
        row = rows[authority_id]
        assert row["verdict"] in TERMINAL_VERDICTS
        assert row["checked_at"] == "2026-09-12"
        assert set(row["source_ids"].split(";")) <= source_ids
        assert row["notes"]


def test_missing_dedicated_annual_report_is_an_explicit_observation() -> None:
    searches = {
        row["search_id"]: row
        for row in read_csv(DATA / "dry-searches.csv")
        if row["country"] == "SEN"
    }
    search = searches["sen-search-jetp-annual-report-20260912"]

    assert search["outcome"] == "not_published"
    assert "annual" in search["query_or_route"].lower()
    assert "2024" in search["notes"]
    assert "2025" in search["notes"]
