"""Contract tests for the bounded 0817 source census."""

from __future__ import annotations

import sys
import csv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from jetp._source_census import validate_census
from jetp.build_0817_source_census import build_rows


def test_frozen_census_covers_every_local_source_once() -> None:
    """The four country tickets inherit a finite, replayable source universe."""
    census_path = ROOT / "docs" / "jetp-study" / "0817-source-census.csv"
    with census_path.open(newline="", encoding="utf-8") as handle:
        census = list(csv.DictReader(handle))

    validate_census(census)
    assert {row["country"] for row in census} == {"ZAF", "IDN", "VNM", "SEN"}
    assert {row["country_owner"] for row in census} == {"0818", "0819", "0820", "0821"}
    assert len(census) == 301
    assert {row["source_id"] for row in census} == {
        row["source_id"]
        for row in csv.DictReader((ROOT / "data" / "jetp" / "sources.csv").open(encoding="utf-8"))
        if row["country"] in {"ZAF", "IDN", "VNM", "SEN"}
    }
    assert all(row["source_version"] != "unversioned" for row in census)
    assert census == build_rows(
        ROOT / "data" / "jetp" / "sources.csv", ROOT / "data" / "jetp" / "manifest.csv"
    )


def test_census_requires_a_disposition_and_preserves_source_semantics() -> None:
    """Pages, revisions, blocked routes and unnamed slots remain explicit work."""
    rows = [
        {
            "item_id": "idn-cipp-page-1",
            "country": "IDN",
            "source_id": "idn-cipp-2023",
            "source_version": "2023-11-21",
            "route": "official_pdf",
            "expected_item": "page 1",
            "expected_count": "1",
            "financial_semantics": "plan_priority_not_finance",
            "date_semantics": "publication_date_only",
            "retention": "raw_byte_dvc_then_review",
            "disposition": "admitted",
            "country_owner": "0819",
        },
        {
            "item_id": "idn-cipp-revised",
            "country": "IDN",
            "source_id": "idn-cipp-2023",
            "source_version": "2023-11-21-revised",
            "route": "official_pdf",
            "expected_item": "revised file",
            "expected_count": "1",
            "financial_semantics": "plan_priority_not_finance",
            "date_semantics": "publication_date_only",
            "retention": "raw_byte_dvc_then_review",
            "disposition": "duplicate",
            "country_owner": "0819",
        },
        {
            "item_id": "idn-portal-blocked",
            "country": "IDN",
            "source_id": "idn-cipp-portal",
            "source_version": "2026-09-15-observation",
            "route": "official_portal",
            "expected_item": "portfolio index",
            "expected_count": "1",
            "financial_semantics": "discovery_only",
            "date_semantics": "observation_date_only",
            "retention": "attempt_log_then_review",
            "disposition": "unavailable",
            "country_owner": "0819",
        },
        {
            "item_id": "idn-unnamed-slot-01",
            "country": "IDN",
            "source_id": "idn-cipp-2023",
            "source_version": "2023-11-21",
            "route": "official_pdf",
            "expected_item": "unnamed portfolio slot 01",
            "expected_count": "1",
            "financial_semantics": "plan_priority_not_finance",
            "date_semantics": "publication_date_only",
            "retention": "raw_byte_dvc_then_review",
            "disposition": "lost_visibility",
            "country_owner": "0819",
        },
    ]

    validate_census(rows)

    incomplete = [*rows]
    incomplete[-1] = {**incomplete[-1], "disposition": ""}
    with pytest.raises(ValueError, match="disposition"):
        validate_census(incomplete)

    zeroed = [*rows]
    zeroed[2] = {**zeroed[2], "disposition": "complete"}
    with pytest.raises(ValueError, match="unavailable"):
        validate_census(zeroed)
