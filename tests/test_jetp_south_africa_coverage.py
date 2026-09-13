"""Coverage contract for the South African JETP source universe."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "data" / "jetp" / "authority-coverage.csv"
SOURCES = ROOT / "data" / "jetp" / "sources.csv"

TERMINAL_VERDICTS = {
    "collected",
    "not_published",
    "blocked",
    "not_applicable",
}

# The 2023-2027 Implementation Plan and the official JET PMU resource hub
# identify these bodies as authorities or named public finance/implementation
# partners.  A missing web publication is evidence only when recorded with a
# terminal verdict; silence is not coverage.
REQUIRED_ZAF_AUTHORITIES = {
    "zaf-presidency",
    "zaf-pcc",
    "zaf-jet-pmu",
    "zaf-ipg",
    "zaf-france-afd",
    "zaf-germany-kfw",
    "zaf-uk",
    "zaf-eu-eib",
    "zaf-us",
    "zaf-netherlands",
    "zaf-denmark",
    "zaf-spain",
    "zaf-switzerland",
    "zaf-canada",
    "zaf-cif",
    "zaf-world-bank",
    "zaf-afdb",
    "zaf-dbsa",
    "zaf-idc",
    "zaf-eskom",
    "zaf-ntcsa",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_south_africa_authority_matrix_is_terminal_and_sourced() -> None:
    rows = [row for row in read_csv(COVERAGE) if row["country"] == "ZAF"]
    by_id = {row["authority_id"]: row for row in rows}

    assert REQUIRED_ZAF_AUTHORITIES <= by_id.keys()
    assert all(row["verdict"] in TERMINAL_VERDICTS for row in rows)

    source_ids = {row["source_id"] for row in read_csv(SOURCES)}
    for row in rows:
        linked = {item for item in row["source_ids"].split(";") if item}
        assert linked <= source_ids
        if row["verdict"] == "collected":
            assert linked, row["authority_id"]


def test_every_official_south_african_project_has_a_source() -> None:
    projects = [
        row
        for row in read_csv(ROOT / "data" / "jetp" / "projects.csv")
        if row["country"] == "ZAF"
    ]
    direct_project_sources = {
        row["project_id"]
        for row in read_csv(SOURCES)
        if row["country"] == "ZAF" and row["project_id"]
    }
    known_source_ids = {row["source_id"] for row in read_csv(SOURCES)}
    events = [
        row
        for row in read_csv(ROOT / "data" / "jetp" / "events.csv")
        if row["country"] == "ZAF"
    ]
    event_project_sources = {
        row["project_id"]
        for row in events
        if row["source_id"] in known_source_ids
    }
    linked_project_sources = {
        row["project_id"]
        for row in read_csv(ROOT / "data" / "jetp" / "project-source-links.csv")
        if row["country"] == "ZAF" and row["source_id"] in known_source_ids
    }
    register_events = [
        row
        for row in events
        if row["source_id"] == "zaf-jet-investment-register-q1-2026"
    ]

    assert projects, "No South African project has been inventoried"
    assert len(register_events) == 257
    assert len({row["event_id"] for row in register_events}) == 257
    assert {row["project_id"] for row in projects} <= (
        direct_project_sources | event_project_sources | linked_project_sources
    )
