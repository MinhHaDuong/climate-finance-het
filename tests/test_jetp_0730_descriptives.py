"""Ticket 0730 must preserve the snapshot's documentary denominators."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from jetp.build_0730_descriptives import build_analysis, build_manifest


def test_descriptives_keep_atomic_reconciled_and_unreconciled_denominators() -> None:
    """No missing amount, date, or unit link can disappear from 0730 tables."""
    analysis = build_analysis(ROOT)

    assert analysis["denominators"] == {
        "atomic_observations": 1740,
        "event_journal": 7,
        "position_journal": 1729,
        "document_coverage": 4,
        "reconciled_atomic_observations": 15,
        "unreconciled_atomic_observations": 1725,
    }
    assert analysis["countries"]["VNM"]["atomic_observations"] == 325
    assert analysis["countries"]["IDN"]["atomic_observations"] == 1148
    assert analysis["money"]["source_reported_positions"] == 297
    assert analysis["money"]["pooled_total"] == "not_computable"
    assert analysis["history"]["event_assertions"] == 7
    assert analysis["history"]["transition_duration"] == "not_computable"


def test_descriptives_only_join_dimensions_when_the_same_explicit_unit_has_them() -> None:
    """Source labels are useful coverage, not a fabricated A/B/C portfolio panel."""
    analysis = build_analysis(ROOT)

    assert analysis["dimensions"]["function"]["documented_observations"] == 1399
    assert analysis["dimensions"]["finance"]["documented_observations"] == 303
    assert analysis["dimensions"]["history"]["documented_observations"] == 7
    assert analysis["dimensions"]["common_explicit_unit_observations"] == 0
    assert analysis["dimensions"]["common_explicit_unit_note"] == (
        "No atomic assertion contains all three frozen, explicitly coded dimensions; "
        "this is a coverage result, not evidence of absence in JETPs."
    )


def test_rendered_outputs_are_replayable_and_handoff_retains_null_candidates(tmp_path: Path) -> None:
    """0823 receives plotted data and candidate results, including the null join."""
    analysis = build_analysis(ROOT)
    manifest = build_manifest(ROOT, analysis)

    assert manifest["input_snapshot_sha256"] == (
        "e76e706704b0040f7142124ed5dc569a2f2c7b61708b75d5ad2188fcb0514171"
    )
    candidate_ids = {row["candidate_id"] for row in analysis["result_candidates"]}
    assert candidate_ids == {
        "coverage-asymmetry",
        "zaf-reported-lifecycle",
        "vnm-finance-history-pedigree",
    }
    assert any(row["result"] == "null_common_sample" for row in analysis["result_candidates"])

    output = tmp_path / "0730-descriptives.json"
    output.write_text(json.dumps(analysis, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    assert json.loads(output.read_text(encoding="utf-8"))["denominators"]["atomic_observations"] == 1740
