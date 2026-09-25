"""The four-country freeze must retain each country's documentary boundary."""

from __future__ import annotations

import gzip
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
    render_snapshot_archive,
    validate_snapshot,
)

pytestmark = pytest.mark.wp_jetp

def test_freeze_preserves_denominators_without_mixed_stage_arithmetic() -> None:
    """Candidate, context, and staging rows cannot become a financial total."""
    snapshot = build_snapshot(ROOT, input_git_sha="e90ff6fe")

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
    assert snapshot["analysis_subsets"]["all_atomic_observations"]["count"] == 1740
    assert (
        snapshot["analysis_subsets"]["routed_event_or_position_observations"]["count"]
        == 1736
    )
    assert snapshot["coverage_groups"][0]["count"] == 279
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
    validate_snapshot(snapshot, ROOT, input_git_sha="e90ff6fe")


def test_unknown_fields_stay_in_descriptive_records_and_conflicts_stay_explicit() -> (
    None
):
    """Missing money/date is coverage, not an exclusion; conflicting evidence survives."""
    snapshot = build_snapshot(ROOT, input_git_sha="e90ff6fe")
    records = snapshot["records"]

    indonesia_unknown = next(
        row
        for row in records
        if row["country"] == "IDN"
        and row["financial_semantic_status"] == "unknown"
        and row["date_semantic_status"] == "unknown"
    )
    assert indonesia_unknown["record_id"].startswith("idn-")
    assert indonesia_unknown["included_in_descriptive_subset"] is True
    assert any(
        row["record_id"] == "vnm-pilot-observation-002"
        and row["conflict_status"] == "explicit_conflict"
        and "Trois valeurs" in row["conflict_note"]
        for row in records
    )
    lower_bound = next(
        row for row in records if row["record_id"] == "vnm-pilot-observation-001"
    )
    assert lower_bound["financial_bound_type"] == "lower_bound"
    assert lower_bound["financial_lower_original"] == 15500000000
    assert lower_bound["financial_upper_original"] is None
    year_bound = next(
        row for row in records if row["record_id"] == "idn-progress25-bioenergy-001"
    )
    assert year_bound["date_bound_type"] == "year"
    assert (year_bound["date_lower"], year_bound["date_upper"]) == (
        "2022-01-01",
        "2022-12-31",
    )
    assert snapshot["analysis_subsets"]["all_atomic_observations"]["count"] == 1740
    assert snapshot["analysis_subsets"]["records_with_unknown_money"]["count"] == 1443
    assert snapshot["analysis_subsets"]["records_with_unknown_date"]["count"] == 326
    validate_snapshot(snapshot, ROOT, input_git_sha="e90ff6fe")


def test_atomic_journals_keep_all_rmp_rows_and_incompatible_inputs() -> None:
    """Coverage is not an operation count; events and positions never silently merge."""
    snapshot = build_snapshot(ROOT, input_git_sha="e90ff6fe")

    rmp = [
        row
        for row in snapshot["atomic_observations"]
        if row["source_layer"] == "vnm_rmp"
    ]
    assert len(rmp) == 279
    assert len({row["source_candidate_id"] for row in rmp}) == 279
    assert all(
        row["journal"] == "positions" and row["event_date"] is None for row in rmp
    )
    assert any(
        row["source_candidate_id"] == "vnm-pilot-observation-018"
        and row["journal"] == "events"
        for row in snapshot["event_journal"]
    )
    tri_an = next(
        row
        for row in snapshot["reconciliations"]
        if row["reconciliation_id"] == "vnm-tri-an-018-019"
    )
    assert tri_an["status"] == "incompatible"
    assert len(tri_an["input_candidate_ids"]) == 2


def test_freeze_fails_closed_if_a_source_link_or_count_changes() -> None:
    snapshot = build_snapshot(ROOT, input_git_sha="e90ff6fe")

    broken = deepcopy(snapshot)
    broken["countries"]["SEN"]["dispositions"]["unresolved_annual_report_candidate"] = 7
    with pytest.raises(ValueError, match="Senegal candidate count"):
        validate_snapshot(broken, ROOT, input_git_sha="e90ff6fe")

    broken = deepcopy(snapshot)
    broken["inputs"]["docs/jetp-study/0820-vietnam-staging.json"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="input hash"):
        validate_snapshot(broken, ROOT, input_git_sha="e90ff6fe")


def test_checked_in_snapshot_and_run_manifest_replay_byte_for_byte() -> None:
    snapshot = build_snapshot(ROOT, input_git_sha="e90ff6fe")
    snapshot_path = ROOT / "docs/jetp-study/0822-comparative-snapshot.json.gz"
    manifest_path = ROOT / "docs/jetp-study/0822-comparative-snapshot-manifest.json"

    assert snapshot_path.read_bytes() == render_snapshot_archive(snapshot)
    assert json.loads(gzip.decompress(snapshot_path.read_bytes())) == snapshot
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest == build_manifest(snapshot)


def test_replay_pins_dvc_input_and_partitions_atomic_journals_for_0730() -> None:
    """The 0730 handoff starts from all assertions, not copied journal rows."""
    snapshot = build_snapshot(ROOT, input_git_sha="e90ff6fe")
    manifest = build_manifest(snapshot)

    assert manifest["dvc_inputs"] == {
        "data/jetp/releases/vnm-migration-0764.json": {
            "hash": "md5",
            "md5": "180429d7c6b882fdc2871b9fa6fbf003",
            "sha256": "ef7538d2af534d31877634bd42f28c5fae1c20b192e6647fc030146a7492eb34",
            "size": 2554708,
            "pointer_path": "data/jetp/releases/vnm-migration-0764.json.dvc",
        }
    }

    event_ids = {row["source_candidate_id"] for row in snapshot["event_journal"]}
    position_ids = {
        row["source_candidate_id"] for row in snapshot["position_journal"]
    }
    routed_ids = {
        row["source_candidate_id"]
        for row in snapshot["atomic_observations"]
        if row["journal"] in {"events", "positions"}
    }
    assert event_ids.isdisjoint(position_ids)
    assert event_ids | position_ids == routed_ids

    subsets = snapshot["analysis_subsets"]
    assert subsets["all_atomic_observations"]["count"] == 1740
    assert subsets["unreconciled_atomic_observations"]["count"] == 1725
    assert subsets["reconciled_atomic_observations"]["count"] == 15
    assert all(
        isinstance(value, (int, float))
        for reconciliation in snapshot["reconciliations"]
        for value in (
            reconciliation["lower_original"],
            reconciliation["upper_original"],
        )
        if value is not None
    )
