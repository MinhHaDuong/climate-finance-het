"""Availability result for Viet Nam's intentionally empty first inventory."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from jetp.build_0820_vietnam_availability import build_report, validate_report


def test_empty_initial_inventory_is_not_zero_evidence_or_complete_coverage() -> None:
    """No declared object means no measurement, not a null finding."""
    report = build_report(ROOT)

    initial = report["initial_inventory"]
    assert initial["expected_objects"] == 0
    assert initial["extracted_objects"] == 0
    assert initial["coverage_disposition"] == "no_initial_extractable_inventory"
    assert initial["evidence_disposition"] == "not_measured_not_zero"
    assert report["required_next_source_leads"]

    with pytest.raises(ValueError, match="zero evidence"):
        validate_report({
            **report,
            "initial_inventory": {**initial, "evidence_disposition": "zero_evidence"},
        }, ROOT)
    with pytest.raises(ValueError, match="complete coverage"):
        validate_report({
            **report,
            "initial_inventory": {**initial, "coverage_disposition": "complete"},
        }, ROOT)


def test_checked_in_availability_result_is_a_clean_replay() -> None:
    path = ROOT / "docs" / "jetp-study" / "0820-vietnam-availability.json"
    assert json.loads(path.read_text(encoding="utf-8")) == build_report(ROOT)
