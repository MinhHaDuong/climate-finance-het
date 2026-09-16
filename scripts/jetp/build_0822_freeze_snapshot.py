"""Freeze the bounded four-country JETP comparison handoff for ticket 0730.

This builder consumes the approved 0818--0821 documentary artifacts.  It is not
a portfolio ledger: candidates, source context and staged observations retain
their own denominators and never enter financial or transition-date arithmetic.
"""

import argparse
import gzip
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from jetp._freeze_0822_journals import (
    _atomic_journals,
    _reconciliations,
    _validate_records,
)
from jetp._freeze_0822_sources import (
    DVC_MIGRATION_PATH,
    _dvc_migration_input,
    _idn,
    _input_hashes,
    _sen,
    _vnm,
    _zaf,
)

SCHEMA_VERSION = "jetp-0822-comparative-snapshot/2"


def _digest(snapshot: dict) -> str:
    unsigned = deepcopy(snapshot)
    unsigned.pop("snapshot_sha256", None)
    return hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_snapshot(root: Path, *, input_git_sha: str) -> dict:
    """Build a deterministic, source-linked comparative handoff without aggregation."""
    root = Path(root)
    if len(input_git_sha) != 8 or any(
        char not in "0123456789abcdef" for char in input_git_sha
    ):
        raise ValueError(
            "input Git revision must be the pinned eight-character lowercase SHA"
        )
    country_results = {
        "ZAF": _zaf(root),
        "IDN": _idn(root),
        "VNM": _vnm(root),
        "SEN": _sen(root),
    }
    countries = {country: result[0] for country, result in country_results.items()}
    records = [
        record
        for country in ("ZAF", "IDN", "VNM", "SEN")
        for record in country_results[country][1]
    ]
    _validate_records(records)
    atomic_observations, event_journal, position_journal = _atomic_journals(
        root, records
    )
    reconciliations = _reconciliations()
    reconciled_ids = {
        candidate_id
        for reconciliation in reconciliations
        for candidate_id in reconciliation["input_candidate_ids"]
    }
    atomic_ids = {row["source_candidate_id"] for row in atomic_observations}
    if not reconciled_ids <= atomic_ids:
        raise ValueError("reconciliation refers to a non-atomic observation")
    financial_points = sum(
        row["financial_bound_type"] != "unknown" for row in atomic_observations
    )
    date_observations = sum(
        row["date_lower"] is not None or row["event_date"] is not None
        for row in atomic_observations
    )
    unknown_money = sum(
        row["financial_bound_type"] == "unknown" for row in atomic_observations
    )
    unknown_dates = sum(
        row["date_lower"] is None and row["event_date"] is None
        for row in atomic_observations
    )
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "input_git_sha": input_git_sha,
        "scope": "approved bounded 0818-0821 artifacts; no external acquisition",
        "inputs": _input_hashes(root),
        "countries": countries,
        "records": records,
        "document_coverage": {
            "status": "bounded approved 0818-0821 source coverage; not a journal",
            "country_sources": {
                country: value["source_denominator"]
                for country, value in countries.items()
            },
        },
        "atomic_observations": atomic_observations,
        "event_journal": event_journal,
        "position_journal": position_journal,
        "reconciliations": reconciliations,
        "coverage_groups": [
            {
                "country": "VNM",
                "group_id": "vnm-rmp-inventory-positions",
                "count": 279,
                "record_materialization": "279 source rows are materialized in atomic_observations; this is a documentary coverage denominator, not an extra observation.",
                "pedigree": {
                    "raw_source_id": "vnm-migration-0764",
                    "raw_document_sha256": countries["VNM"]["source_links"][0][
                        "sha256"
                    ],
                    "locator": "rmp_inventory_positions",
                    "extraction_method": "0820 staged migration summary",
                    "semantic_interpretation": "Inventory membership only; neither operation identity nor finance fact.",
                    "link_dedup_rule": "The 279 individually extracted assertions retain their source IDs; this group is not additive.",
                    "confidence": "source_only",
                },
            }
        ],
        "analysis_subsets": {
            "all_atomic_observations": {
                "count": len(atomic_observations),
                "rule": "Every extracted assertion, including document coverage and unknown money/date; no reconciliation removes an observation.",
            },
            "routed_event_or_position_observations": {
                "count": len(event_journal) + len(position_journal),
                "rule": "Assertions routed once to the disjoint event or position journals; documentary coverage remains outside both journals.",
            },
            "reconciled_atomic_observations": {
                "count": len(reconciled_ids),
                "rule": "Atomic observations named by one or more documentary reconciliation records; values are not pooled unless that reconciliation says so.",
            },
            "unreconciled_atomic_observations": {
                "count": len(atomic_ids - reconciled_ids),
                "rule": "Atomic observations not named by a reconciliation; retained explicitly for descriptive coverage and later adjudication.",
            },
            "source_reported_money_positions": {
                "count": financial_points,
                "rule": "Record-level source amounts/bounds; not deduplicated and never a cross-country total.",
            },
            "source_reported_date_observations": {
                "count": date_observations,
                "rule": "Reported, registered, or estimated date values; not transition timing.",
            },
            "records_with_unknown_money": {
                "count": unknown_money,
                "rule": "Retained records whose bounded source artifact does not report a monetary value.",
            },
            "records_with_unknown_date": {
                "count": unknown_dates,
                "rule": "Retained records whose bounded source artifact does not report a date value.",
            },
            "vnm_rmp_inventory_coverage": {
                "count": 279,
                "rule": "Documentary denominator corresponding to 279 individually materialized RMP position assertions; not an additional group-only observation.",
            },
        },
        "aggregation": {
            "financial_total": "not_computable",
            "transition_date_total": "not_computable",
            "point_quantities": "Record and coverage-group counts only, each with its stated denominator.",
            "interval_quantities": "Record-level lower bounds and year bounds are retained where source wording supports them; no pooled interval is calculated.",
            "reason": "Source positions have incompatible financial/date semantics and unresolved links/duplicates; unknown is retained, not zeroed, but no pooled finance or transition-time estimate is identified.",
        },
        "handoff": "0730 may compute descriptives on each named subset and report its coverage, missingness, conflict status, and semantic pedigree. It must not pool source amounts, interpret source dates as transition dates, or make causal/payment claims.",
    }
    snapshot["snapshot_sha256"] = _digest(snapshot)
    validate_snapshot(snapshot, root, input_git_sha=input_git_sha)
    return snapshot


def validate_snapshot(snapshot: dict, root: Path, *, input_git_sha: str) -> None:
    """Fail closed on a changed artifact, country boundary, or content signature."""
    if (
        snapshot.get("schema_version") != SCHEMA_VERSION
        or snapshot.get("input_git_sha") != input_git_sha
    ):
        raise ValueError("snapshot schema or pinned Git revision changed")
    actual_inputs = _input_hashes(Path(root))
    if snapshot.get("inputs") != actual_inputs:
        raise ValueError("input hash changed")
    results = {
        "ZAF": _zaf(Path(root)),
        "IDN": _idn(Path(root)),
        "VNM": _vnm(Path(root)),
        "SEN": _sen(Path(root)),
    }
    expected = {country: result[0] for country, result in results.items()}
    expected_records = [
        record
        for country in ("ZAF", "IDN", "VNM", "SEN")
        for record in results[country][1]
    ]
    expected_atomic, expected_events, expected_positions = _atomic_journals(
        Path(root), expected_records
    )
    countries = snapshot.get("countries")
    if countries != expected:
        if (
            isinstance(countries, dict)
            and countries.get("SEN", {})
            .get("dispositions", {})
            .get("unresolved_annual_report_candidate")
            != 6
        ):
            raise ValueError("Senegal candidate count changed")
        raise ValueError("country disposition or source linkage changed")
    if snapshot.get("records") != expected_records:
        raise ValueError("structured record, uncertainty, or pedigree changed")
    _validate_records(snapshot["records"])
    if (
        snapshot.get("atomic_observations") != expected_atomic
        or snapshot.get("event_journal") != expected_events
        or snapshot.get("position_journal") != expected_positions
    ):
        raise ValueError(
            "atomic journal routing or exhaustive source retention changed"
        )
    if snapshot.get("reconciliations") != _reconciliations():
        raise ValueError("reconciliation adjudication changed")
    subsets = snapshot.get("analysis_subsets", {})
    atomic_ids = {row["source_candidate_id"] for row in expected_atomic}
    reconciled_ids = {
        candidate_id
        for reconciliation in _reconciliations()
        for candidate_id in reconciliation["input_candidate_ids"]
    }
    if (
        subsets.get("all_atomic_observations", {}).get("count")
        != len(expected_atomic)
        or subsets.get("routed_event_or_position_observations", {}).get("count")
        != len(expected_events) + len(expected_positions)
        or subsets.get("reconciled_atomic_observations", {}).get("count")
        != len(reconciled_ids)
        or subsets.get("unreconciled_atomic_observations", {}).get("count")
        != len(atomic_ids - reconciled_ids)
    ):
        raise ValueError("descriptive atomic denominator changed")
    if (
        snapshot.get("aggregation", {}).get("financial_total") != "not_computable"
        or snapshot.get("aggregation", {}).get("transition_date_total")
        != "not_computable"
    ):
        raise ValueError("mixed-stage arithmetic is prohibited")
    if snapshot.get("snapshot_sha256") != _digest(snapshot):
        raise ValueError("snapshot content signature changed")


def render_snapshot(snapshot: dict) -> bytes:
    return (json.dumps(snapshot, indent=2, sort_keys=True) + "\n").encode()


def render_snapshot_archive(snapshot: dict) -> bytes:
    """Stable compressed representation keeps the full structured snapshot in Git."""
    return gzip.compress(render_snapshot(snapshot), mtime=0)


def build_manifest(snapshot: dict) -> dict:
    return {
        "schema_version": "jetp-0822-run-manifest/1",
        "input_git_sha": snapshot["input_git_sha"],
        "input_sha256": snapshot["inputs"],
        "dvc_inputs": {
            DVC_MIGRATION_PATH: _dvc_migration_input(
                Path(__file__).resolve().parents[2]
            )
        },
        "snapshot_path": "docs/jetp-study/0822-comparative-snapshot.json.gz",
        "snapshot_sha256": snapshot["snapshot_sha256"],
        "reproduction": "Run this builder with --input-git-sha at the recorded revision; inputs are content-hashed and output rendering is deterministic.",
        "dvc_boundary": "The VNM migration bytes remain DVC-managed and unstaged. Replay validates the tracked DVC pointer (MD5 and size) plus the materialized JSON SHA-256.",
    }


def write_outputs(
    root: Path, snapshot_path: Path, manifest_path: Path, *, input_git_sha: str
) -> None:
    snapshot = build_snapshot(root, input_git_sha=input_git_sha)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_bytes(render_snapshot_archive(snapshot))
    manifest_path.write_text(
        json.dumps(build_manifest(snapshot), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-git-sha", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "docs/jetp-study/0822-comparative-snapshot.json.gz",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=root / "docs/jetp-study/0822-comparative-snapshot-manifest.json",
    )
    args = parser.parse_args()
    write_outputs(root, args.output, args.manifest, input_git_sha=args.input_git_sha)


if __name__ == "__main__":
    main()
