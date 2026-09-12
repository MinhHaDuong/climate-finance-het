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
