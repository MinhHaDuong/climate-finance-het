"""Lossless migration contract for the 10 August 2026 Viet Nam pilot."""

from __future__ import annotations

import csv
from pathlib import Path

from jetp.migrate_vnm_pilot import migrate_pilot


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "conception" / "jetp" / "papier-3-ledger" / "pilote-ledger-vn"
DATA = ROOT / "data" / "jetp"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_migration_preserves_all_pilot_rows_and_provenance(tmp_path: Path) -> None:
    manifest_out = tmp_path / "manifest.csv"
    observations_out = tmp_path / "observations.csv"

    migrate_pilot(PILOT, manifest_out, observations_out)

    legacy_manifest = read_csv(PILOT / "manifest.csv")
    migrated_manifest = read_csv(manifest_out)
    legacy_truth = read_csv(PILOT / "verite-terrain-brouillon.csv")
    migrated_truth = read_csv(observations_out)

    assert len(legacy_manifest) == len(migrated_manifest) == 66
    assert len(legacy_truth) == len(migrated_truth) == 46
    assert [row["filename"] for row in legacy_manifest] == [
        row["legacy_filename"] for row in migrated_manifest
    ]
    assert [row["url"] for row in legacy_manifest] == [
        row["url"] for row in migrated_manifest
    ]
    assert [row["sha256"] for row in legacy_manifest] == [
        row["sha256"] for row in migrated_manifest
    ]
    assert [row["operation"] for row in legacy_truth] == [
        row["operation"] for row in migrated_truth
    ]
    assert [row["document_source"] for row in legacy_truth] == [
        row["source_filename"] for row in migrated_truth
    ]
    assert {row["country"] for row in migrated_manifest + migrated_truth} == {"VNM"}


def test_migration_maps_collection_results_without_erasing_failures(
    tmp_path: Path,
) -> None:
    manifest_out = tmp_path / "manifest.csv"
    migrate_pilot(PILOT, manifest_out, tmp_path / "observations.csv")
    rows = read_csv(manifest_out)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["collection_status"]] = counts.get(row["collection_status"], 0) + 1

    assert counts == {"collected": 54, "blocked": 8, "missing": 4}
    for row in rows:
        if row["collection_status"] == "collected":
            assert row["sha256"]
            assert row["size_bytes"]
        else:
            assert not row["sha256"]
            assert not row["size_bytes"]


def test_migration_joins_all_manual_verification_verdicts(tmp_path: Path) -> None:
    observations_out = tmp_path / "observations.csv"
    migrate_pilot(PILOT, tmp_path / "manifest.csv", observations_out)
    rows = read_csv(observations_out)

    assert {row["verification_verdict"] for row in rows} == {"verified", "partial"}
    assert sum(row["verification_verdict"] == "verified" for row in rows) == 45
    assert sum(row["verification_verdict"] == "partial" for row in rows) == 1
    assert all(row["verification_note"] for row in rows)
    assert all(row["matched_snippet"] for row in rows)


def test_24_project_portfolio_is_not_the_17_new_proposals(tmp_path: Path) -> None:
    observations_out = tmp_path / "observations.csv"
    migrate_pilot(PILOT, tmp_path / "manifest.csv", observations_out)
    by_operation = {row["operation"]: row for row in read_csv(observations_out)}

    screened = by_operation["Pipeline JETP — 17 projets retenus au criblage 2025"]
    portfolio = by_operation["Pipeline JETP — portefeuille total à juillet 2025"]

    assert screened["project_count"] == "17"
    assert screened["portfolio_role"] == "new_proposals_screened"
    assert screened["amount_original"] == "5520000000"
    assert portfolio["project_count"] == "24"
    assert portfolio["portfolio_role"] == "total_portfolio"
    assert portfolio["amount_original"] == "7040000000"
    assert screened["observation_id"] != portfolio["observation_id"]


def test_committed_migration_outputs_are_reproducible(tmp_path: Path) -> None:
    manifest_out = tmp_path / "manifest.csv"
    observations_out = tmp_path / "observations.csv"
    migrate_pilot(PILOT, manifest_out, observations_out)

    assert manifest_out.read_bytes() == (DATA / "vnm-pilot-manifest.csv").read_bytes()
    assert observations_out.read_bytes() == (
        DATA / "vnm-pilot-observations.csv"
    ).read_bytes()
