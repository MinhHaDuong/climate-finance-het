"""Regression contract for the 0816 documentary diagnostic matrix."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from jetp.build_0816_diagnostic import (
    documentary_rows,
    summarize_diagnostic,
    validate_0816_acceptance,
    validate_date_roles,
    validate_diagnostic_rows,
    write_summary,
)


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
    assert sum(row["supports_A_B_C"] == "yes" for row in matrix) == 0
    assert not any(
        row["country"] == "SEN" and row["supports_B_strict"] == "yes"
        for row in matrix
    )
    saguling = next(row for row in matrix if row["operation_id"] == "idn-fin-saguling-floating-solar")
    assert saguling["finance_observation"] == "DEG, Proparco and Standard Chartered package 60000000 USD"
    assert saguling["finance_ownership"] == "mixed_unallocated"
    assert all(
        row["financial_state"] == "allocation"
        for row in matrix
        if row["operation_id"] in {"zaf-register-actip001", "zaf-register-nl002"}
    )
    vocabulary = protocol["lifecycle_taxonomy"]
    assert {"allocation", "disbursed", "unavailable", "lost_visibility"} <= set(vocabulary["financial"])
    assert "duplicate" in protocol["coverage_universe"]["disposition_vocabulary"]


def test_acceptance_rejects_causal_scope_and_zero_filled_missing_finance() -> None:
    protocol = {"permitted_comparisons": ["causal acceleration"]}
    with pytest.raises(ValueError, match="causal"):
        validate_0816_acceptance(protocol, [])

    protocol = {"permitted_comparisons": ["documentary coverage"]}
    with pytest.raises(ValueError, match="zero"):
        validate_0816_acceptance(protocol, [{"finance_observation": "0"}])


def test_summary_is_derived_and_cutoff_dates_cannot_create_a_history_sequence() -> None:
    matrix = list(csv.DictReader((ROOT / "docs/jetp-study/0816-diagnostic-matrix.csv").open()))
    summary = summarize_diagnostic(matrix)
    frozen_summary = json.loads((ROOT / "docs/jetp-study/0816-diagnostic-summary.json").read_text())

    assert frozen_summary == summary
    cirebon = next(row for row in matrix if row["operation_id"] == "idn-pipe-cirebon-1-retirement")
    assert cirebon["supports_C_sequence"] == "no"
    assert summary["A"] == 8
    assert summary["B_strict"] == 6
    assert summary["C_sequence"] == 0
    assert summary["A_B_C"] == 0

    with pytest.raises(ValueError, match="registered"):
        validate_date_roles([
            {
                "pre_jetp_milestone": "2021-11-01: register row",
                "post_jetp_milestone": "2025-11-30: report cutoff",
                "history_precision": "day",
                "pre_date_role": "registered",
                "post_date_role": "observed_state",
            }
        ])


def test_duplicate_evidence_must_agree_and_summary_is_written_from_rows(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="conflicting contribution"):
        documentary_rows(
            operations=[{"operation_id": "x", "country": "IDN"}],
            finance=[
                {"operation_id": "x", "contribution_id": "same", "amount_original": "1"},
                {"operation_id": "x", "contribution_id": "same", "amount_original": "2"},
            ],
            milestones=[],
        )

    output = tmp_path / "summary.json"
    write_summary(
        ROOT / "docs/jetp-study/0816-diagnostic-matrix.csv",
        output,
    )
    assert json.loads(output.read_text()) == {
        "A": 8,
        "A_B_C": 0,
        "B_strict": 6,
        "C_sequence": 0,
    }


def test_summary_rejects_duplicate_id_and_strict_finance_without_an_observation() -> None:
    """The reviewed matrix cannot claim a strict B row without its evidence."""
    valid = {
        "operation_id": "idn-saguling",
        "jetp_link": "jetp_strict",
        "finance_observation": "mixed package 60000000 USD",
        "finance_ownership": "mixed_unallocated",
        "supports_A": "yes",
        "supports_B_strict": "yes",
        "supports_C_sequence": "no",
        "supports_A_B_C": "no",
    }
    with pytest.raises(ValueError, match="duplicate operation_id"):
        validate_diagnostic_rows([valid, valid.copy()])

    unsupported_b = valid | {"operation_id": "zaf-register", "finance_observation": ""}
    with pytest.raises(ValueError, match="strict finance"):
        summarize_diagnostic([unsupported_b])
