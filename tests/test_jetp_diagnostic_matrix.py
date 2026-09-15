"""Regression contract for the 0816 documentary diagnostic matrix."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from jetp.diagnostic_matrix import documentary_rows


def test_documentary_rules_do_not_invent_a_private_share_or_event_date() -> None:
    """A duplicated mixed package stays one unsplit contribution and undated event."""
    rows = documentary_rows(
        operations=[
            {
                "operation_id": "idn-saguling",
                "country": "IDN",
                "function": "energy_infrastructure",
                "social_objective": "",
                "beneficiaries": "",
            }
        ],
        finance=[
            {
                "contribution_id": "saguling-package",
                "operation_id": "idn-saguling",
                "funder": "DEG;Proparco;Standard Chartered",
                "ownership": "mixed_unallocated",
                "instrument": "loan",
                "amount_original": "60000000",
                "currency_original": "USD",
                "source_id": "agreement",
            },
            {
                "contribution_id": "saguling-package",
                "operation_id": "idn-saguling",
                "funder": "DEG;Proparco;Standard Chartered",
                "ownership": "mixed_unallocated",
                "instrument": "loan",
                "amount_original": "60000000",
                "currency_original": "USD",
                "source_id": "announcement",
            },
        ],
        milestones=[
            {
                "operation_id": "idn-saguling",
                "milestone": "agreement_reported",
                "publication_date": "2025-01-10",
                "event_date": "",
                "date_precision": "unknown",
                "source_id": "announcement",
            }
        ],
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["finance_contribution_count"] == "1"
    assert row["private_amount_original"] == ""
    assert row["mixed_unallocated_amount_original"] == "60000000 USD"
    assert row["event_date"] == ""
    assert row["publication_date"] == "2025-01-10"
