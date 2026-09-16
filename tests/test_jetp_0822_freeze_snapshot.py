"""The four-country freeze must retain each country's documentary boundary."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from jetp.build_0822_freeze_snapshot import (
    build_manifest,
    build_snapshot,
    render_snapshot,
    validate_snapshot,
)


def test_freeze_preserves_denominators_without_mixed_stage_arithmetic() -> None:
    """Candidate, context, and staging rows cannot become a financial total."""
    snapshot = build_snapshot(ROOT, input_git_sha="fed33609")

    assert snapshot["countries"]["ZAF"]["dispositions"] == {
        "unadmitted_register_candidate": 257,
    }
    assert snapshot["countries"]["IDN"]["dispositions"] == {
        "reviewed_contextual_source": 6,
        "unadmitted_plan_priority_candidate": 1142,
    }
    assert snapshot["countries"]["VNM"]["dispositions"] == {
        "unadmitted_pilot_observation": 46,
        "unadmitted_rmp_inventory_position": 279,
    }
    assert snapshot["countries"]["SEN"]["dispositions"] == {
        "indexed_file_not_retained": 4,
        "unresolved_annual_report_candidate": 6,
    }
    assert snapshot["admitted_comparative_units"] == 0
    assert snapshot["aggregation"]["financial_total"] == "not_computable"
    assert snapshot["aggregation"]["transition_date_total"] == "not_computable"
    assert (
        snapshot["countries"]["VNM"]["admissibility"] == "nonempty_unadmitted_staging"
    )
    assert snapshot["countries"]["VNM"]["prohibited_inferences"] == [
        "payment",
        "transition_date",
        "operation_identity",
    ]
    validate_snapshot(snapshot, ROOT, input_git_sha="fed33609")


def test_freeze_fails_closed_if_a_source_link_or_count_changes() -> None:
    snapshot = build_snapshot(ROOT, input_git_sha="fed33609")

    broken = deepcopy(snapshot)
    broken["countries"]["SEN"]["dispositions"]["unresolved_annual_report_candidate"] = 7
    with pytest.raises(ValueError, match="Senegal candidate count"):
        validate_snapshot(broken, ROOT, input_git_sha="fed33609")

    broken = deepcopy(snapshot)
    broken["inputs"]["docs/jetp-study/0820-vietnam-staging.json"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="input hash"):
        validate_snapshot(broken, ROOT, input_git_sha="fed33609")


def test_checked_in_snapshot_and_run_manifest_replay_byte_for_byte() -> None:
    snapshot = build_snapshot(ROOT, input_git_sha="fed33609")
    snapshot_path = ROOT / "docs/jetp-study/0822-comparative-snapshot.json"
    manifest_path = ROOT / "docs/jetp-study/0822-comparative-snapshot-manifest.json"

    assert snapshot_path.read_bytes() == render_snapshot(snapshot)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest == build_manifest(snapshot)
