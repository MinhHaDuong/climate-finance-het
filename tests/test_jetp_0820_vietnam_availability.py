"""Bounded staging result for the retained Viet Nam corpus."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from jetp.build_0820_vietnam_availability import build_report, validate_report


def test_retained_vietnam_corpus_invalidates_zero_extraction() -> None:
    """The local RMP candidate and 46 pilot rows are a nonempty staging corpus."""
    report = build_report(ROOT)

    assert report["rmp_inventory_positions"]["count"] == 279
    assert report["pilot_observations"]["count"] == 46
    assert (
        report["rmp_inventory_positions"]["admission_status"] == "unadmitted_candidate"
    )
    assert report["pilot_observations"]["eligible_for_account"] is False
    assert report["availability_disposition"] == "nonempty_unadmitted_staging"
    validate_report(report, ROOT)
    zeroed = deepcopy(report)
    zeroed["rmp_inventory_positions"]["count"] = 0
    with pytest.raises(ValueError, match="zero extraction"):
        validate_report(zeroed, ROOT)


def test_checked_in_staging_result_is_a_clean_replay() -> None:
    path = ROOT / "docs" / "jetp-study" / "0820-vietnam-staging.json"
    assert json.loads(path.read_text(encoding="utf-8")) == build_report(ROOT)
