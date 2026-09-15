"""Contract tests for the bounded 0817 source census."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from jetp._source_census import validate_census


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
