"""Ticket 0730 must preserve the snapshot's documentary denominators."""

import gzip
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from jetp.build_0730_descriptives import (
    _snapshot,
    build_analysis,
    build_manifest,
    render_outputs,
)


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

    render_outputs(ROOT, tmp_path)
    output = tmp_path / "0730-descriptives.json"
    assert json.loads(output.read_text(encoding="utf-8"))["denominators"]["atomic_observations"] == 1740
    assert (tmp_path / "0730-plot-data.csv").is_file()
    assert "cohorte commune opérationnelle A/B/C" in (
        tmp_path / "0730-descriptives-report.md"
    ).read_text(encoding="utf-8")


def test_snapshot_loader_rejects_tampered_payload_even_when_declared_digest_survives(
    tmp_path: Path,
) -> None:
    """The signed field is not trusted in lieu of recomputing canonical JSON."""
    source_archive = ROOT / "docs/jetp-study/0822-comparative-snapshot.json.gz"
    source_manifest = ROOT / "docs/jetp-study/0822-comparative-snapshot-manifest.json"
    target_dir = tmp_path / "docs/jetp-study"
    target_dir.mkdir(parents=True)
    snapshot = json.loads(gzip.decompress(source_archive.read_bytes()))
    tampered = deepcopy(snapshot)
    tampered["atomic_observations"][0]["notes"] = "tampered without resigning"
    (target_dir / source_archive.name).write_bytes(
        gzip.compress(
            (json.dumps(tampered, sort_keys=True, indent=2) + "\n").encode(), mtime=0
        )
    )
    (target_dir / source_manifest.name).write_bytes(source_manifest.read_bytes())

    with pytest.raises(ValueError, match="canonical digest"):
        _snapshot(tmp_path)


def test_snapshot_loader_rejects_rewritten_manifest_bytes(tmp_path: Path) -> None:
    """The 0730 freeze pins the reviewed 0822 manifest as an input, too."""
    source_archive = ROOT / "docs/jetp-study/0822-comparative-snapshot.json.gz"
    source_manifest = ROOT / "docs/jetp-study/0822-comparative-snapshot-manifest.json"
    target_dir = tmp_path / "docs/jetp-study"
    target_dir.mkdir(parents=True)
    (target_dir / source_archive.name).write_bytes(source_archive.read_bytes())
    rewritten = json.loads(source_manifest.read_text(encoding="utf-8"))
    rewritten["reproduction"] = "rewritten manifest"
    (target_dir / source_manifest.name).write_text(
        json.dumps(rewritten, sort_keys=True) + "\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="manifest bytes"):
        _snapshot(tmp_path)


def test_vietnam_and_zaf_candidates_use_their_scoped_reconciliation_and_date_counts() -> None:
    """Candidate prose cannot silently borrow Senegal reconciliation or label dates."""
    analysis = build_analysis(ROOT)
    candidates = {row["candidate_id"]: row for row in analysis["result_candidates"]}

    assert analysis["countries"]["VNM"]["named_reconciliations"] == 3
    assert analysis["countries"]["VNM"]["reconciled_atomic_observations"] == 14
    assert "3 named VNM reconciliations" in candidates["vnm-finance-history-pedigree"]["evidence"]
    assert analysis["countries"]["ZAF"]["source_date_values"] == 235
    assert "257 implementation-status semantic labels" in candidates["zaf-reported-lifecycle"]["evidence"]
    assert "235 source register-date values" in candidates["zaf-reported-lifecycle"]["evidence"]
