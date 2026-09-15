"""Regression contract for the 0816 documentary diagnostic matrix."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from jetp.build_0816_diagnostic import documentary_rows, validate_0816_acceptance


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


def test_frozen_matrix_is_four_country_but_not_a_four_country_joint_sample() -> None:
    matrix = list(csv.DictReader((ROOT / "docs/jetp-study/0816-diagnostic-matrix.csv").open()))
    protocol = json.loads((ROOT / "docs/jetp-study/0816-protocol.json").read_text())

    validate_0816_acceptance(protocol, matrix)
    assert {row["country"] for row in matrix} == {"ZAF", "IDN", "VNM", "SEN"}
    assert sum(row["supports_A_B_C"] == "yes" for row in matrix) == 1
    assert not any(
        row["country"] == "SEN" and row["supports_B_strict"] == "yes"
        for row in matrix
    )


def test_acceptance_rejects_causal_scope_and_zero_filled_missing_finance() -> None:
    protocol = {"permitted_comparisons": ["causal acceleration"]}
    with pytest.raises(ValueError, match="causal"):
        validate_0816_acceptance(protocol, [])

    protocol = {"permitted_comparisons": ["documentary coverage"]}
    with pytest.raises(ValueError, match="zero"):
        validate_0816_acceptance(protocol, [{"finance_observation": "0"}])
