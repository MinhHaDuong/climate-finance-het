# WARNING: AI-generated, not human-reviewed
"""Build the migrated 10 August 2026 Viet Nam pilot without rewriting its evidence.

The pilot predates the shared four-country contract and uses French field names
and collection statuses.  These staging tables retain every legacy value while
adding stable identifiers, common country/status fields, and the independently
recorded verification verdicts.  They are inputs to later source and event
normalisation; they are not themselves the canonical financial-event ledger.
"""

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path

from script_io_args import parse_io_args, validate_io

PILOT_SNAPSHOT_DATE = "2026-08-10"

MANIFEST_FIELDS = (
    "pilot_row_id",
    "source_id",
    "country",
    "pilot_snapshot_date",
    "source_class",
    "legacy_filename",
    "url",
    "legacy_status",
    "collection_status",
    "http_status",
    "sha256",
    "size_bytes",
    "notes",
)

OBSERVATION_FIELDS = (
    "observation_id",
    "country",
    "ratified",
    "operation",
    "funder",
    "instrument",
    "amount_original",
    "currency_original",
    "event_date",
    "legacy_status",
    "source_filename",
    "locator",
    "confidence",
    "notes",
    "verification_verdict",
    "verification_note",
    "matched_snippet",
    "project_count",
    "portfolio_role",
)

STATUS_MAP = {
    "fetched": "collected",
    "blocked": "blocked",
    "skipped": "missing",
}

PORTFOLIO_COUNTS = {
    "Pipeline JETP — 7 premiers projets identifiés": ("7", "initial_projects"),
    "Pipeline JETP — 17 projets retenus au criblage 2025": (
        "17",
        "new_proposals_screened",
    ),
    "Pipeline JETP — portefeuille total à juillet 2025": (
        "24",
        "total_portfolio",
    ),
    "Pipeline JETP — portefeuille total à juillet 2026": (
        "50",
        "total_portfolio",
    ),
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    if not slug:
        raise ValueError(f"cannot derive source_id from filename: {value!r}")
    return slug


def _migrate_manifest(pilot_dir: Path) -> list[dict[str, str]]:
    rows = _read_csv(pilot_dir / "manifest.csv")
    output: list[dict[str, str]] = []
    source_ids: set[str] = set()
    for index, row in enumerate(rows, 1):
        try:
            collection_status = STATUS_MAP[row["status"]]
        except KeyError as exc:
            raise ValueError(f"unknown pilot collection status: {row['status']!r}") from exc
        source_id = f"vnm-pilot-{_slug(row['filename'])}"
        if source_id in source_ids:
            raise ValueError(f"duplicate migrated source_id: {source_id}")
        source_ids.add(source_id)
        output.append(
            {
                "pilot_row_id": f"vnm-pilot-source-{index:03d}",
                "source_id": source_id,
                "country": "VNM",
                "pilot_snapshot_date": PILOT_SNAPSHOT_DATE,
                "source_class": row["classe"],
                "legacy_filename": row["filename"],
                "url": row["url"],
                "legacy_status": row["status"],
                "collection_status": collection_status,
                "http_status": row["http_code"],
                "sha256": row["sha256"],
                "size_bytes": row["size_bytes"],
                "notes": row["notes"],
            }
        )
    return output


def _load_verdicts(path: Path) -> dict[int, dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    verdicts = {int(row["row_id"]): row for row in payload["verdicts"]}
    if len(verdicts) != len(payload["verdicts"]):
        raise ValueError("duplicate row_id in verification verdicts")
    return verdicts


def _migrate_observations(pilot_dir: Path) -> list[dict[str, str]]:
    rows = _read_csv(pilot_dir / "verite-terrain-brouillon.csv")
    verdicts = _load_verdicts(pilot_dir / "verif-verdicts.json")
    expected_ids = set(range(1, len(rows) + 1))
    if set(verdicts) != expected_ids:
        raise ValueError("verification verdict row_ids do not cover every observation")

    output: list[dict[str, str]] = []
    for index, row in enumerate(rows, 1):
        verdict = verdicts[index]
        project_count, portfolio_role = PORTFOLIO_COUNTS.get(
            row["operation"], ("", "")
        )
        output.append(
            {
                "observation_id": f"vnm-pilot-observation-{index:03d}",
                "country": "VNM",
                "ratified": row["ratifie"],
                "operation": row["operation"],
                "funder": row["financier"],
                "instrument": row["instrument"],
                "amount_original": row["montant"],
                "currency_original": row["devise"],
                "event_date": row["date"],
                "legacy_status": row["statut"],
                "source_filename": row["document_source"],
                "locator": row["localisation"],
                "confidence": row["confiance"],
                "notes": row["notes"],
                "verification_verdict": verdict["verdict"],
                "verification_note": verdict["note"],
                "matched_snippet": verdict["matched_snippet"],
                "project_count": project_count,
                "portfolio_role": portfolio_role,
            }
        )
    return output


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def migrate_pilot(
    pilot_dir: Path, manifest_output: Path, observations_output: Path
) -> None:
    """Write lossless, deterministic staging tables for the Viet Nam pilot."""
    manifest_rows = _migrate_manifest(pilot_dir)
    observation_rows = _migrate_observations(pilot_dir)
    known_filenames = {row["legacy_filename"] for row in manifest_rows}
    unknown_sources = {
        row["source_filename"] for row in observation_rows
    } - known_filenames
    if unknown_sources:
        raise ValueError(f"observation sources absent from manifest: {unknown_sources}")
    _write_csv(manifest_output, MANIFEST_FIELDS, manifest_rows)
    _write_csv(observations_output, OBSERVATION_FIELDS, observation_rows)


def main(argv: list[str] | None = None) -> None:
    """Generate both Viet Nam migration tables below an output directory."""
    io_args, extra = parse_io_args(argv)
    parser = argparse.ArgumentParser()
    parser.parse_args(extra)
    if not io_args.input or len(io_args.input) != 1:
        parser.error("--input requires the Viet Nam pilot directory")
    validate_io(output=io_args.output, inputs=io_args.input)

    output_dir = Path(io_args.output)
    if not output_dir.is_dir():
        parser.error("--output must be an existing directory")
    migrate_pilot(
        Path(io_args.input[0]),
        output_dir / "vnm-pilot-manifest.csv",
        output_dir / "vnm-pilot-observations.csv",
    )


if __name__ == "__main__":
    main()
