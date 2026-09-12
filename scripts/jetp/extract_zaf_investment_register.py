# WARNING: AI-generated, not human-reviewed
"""Extract project identities and finance events from the ZAF JET register.

The official JET PMU dashboard embeds its ``Overall - Data`` table as a JSON
array in the page.  This module turns one collected HTML snapshot into the two
canonical ledgers without fetching the live site during extraction.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
from pathlib import Path

from script_io_args import parse_io_args, validate_io
from utils import get_logger

from jetp.schemas import validate_event_record

log = get_logger("jetp.extract_zaf_investment_register")

PROJECT_FIELDS = (
    "project_id",
    "country",
    "canonical_name",
    "aliases",
    "technology",
    "location",
    "operator",
    "first_seen_date",
    "last_seen_date",
    "verification_status",
    "notes",
)

EVENT_FIELDS = (
    "event_id",
    "project_id",
    "country",
    "event_date",
    "scope",
    "financial_status",
    "funder",
    "window",
    "instrument",
    "amount_original",
    "currency_original",
    "amount_usd",
    "conversion_method",
    "source_id",
    "document_sha256",
    "locator",
    "verification_status",
    "notes",
)

REGISTER_PATTERN = re.compile(r"const\s+OVERALL\s*=\s*(\[.*?\]);", re.DOTALL)


def _text(value) -> str:
    """Return a compact string representation for a dashboard scalar."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return " ".join(str(value).split())


def _date(value) -> str:
    return _text(value)[:10]


def _project_id(unique_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", unique_id.lower()).strip("-")
    if not slug:
        raise ValueError(f"invalid Unique ID: {unique_id!r}")
    return f"zaf-register-{slug}"


def parse_register_html(document: str) -> list[dict]:
    """Parse material project rows from one official dashboard snapshot."""
    match = REGISTER_PATTERN.search(html.unescape(document))
    if not match:
        raise ValueError("official register JSON array not found")
    try:
        raw_rows = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError("official register JSON array is invalid") from exc
    rows = [
        row
        for row in raw_rows
        if isinstance(row, dict)
        and isinstance(row.get("Unique ID"), str)
        and row.get("Project Name")
        and row.get("Portfolios")
    ]
    identifiers = [_text(row["Unique ID"]) for row in rows]
    duplicates = sorted(
        {identifier for identifier in identifiers if identifiers.count(identifier) > 1}
    )
    if duplicates:
        raise ValueError(f"duplicate Unique ID values: {duplicates}")
    return rows


def _notes(row: dict, *fields: str) -> str:
    parts = []
    for field in fields:
        value = _text(row.get(field))
        if value:
            parts.append(f"{field}={value}")
    return "; ".join(parts)


def build_project_records(
    rows: list[dict], *, reported_date: str
) -> list[dict[str, str]]:
    """Build stable project identities from official register identifiers."""
    records = []
    for row in rows:
        unique_id = _text(row["Unique ID"])
        signed_date = _date(row.get("Date of Financing Agreement Signed*"))
        operator = _text(row.get("Implementing Entity")) or _text(
            row.get("Institutional / South African Partner")
        )
        record = {
            "project_id": _project_id(unique_id),
            "country": "ZAF",
            "canonical_name": _text(row["Project Name"]),
            "aliases": "",
            "technology": _text(row.get("Portfolios")),
            "location": "",
            "operator": operator,
            "first_seen_date": signed_date or reported_date,
            "last_seen_date": reported_date,
            "verification_status": "official_register",
            "notes": "official register id="
            + unique_id
            + "; "
            + _notes(
                row,
                "Purpose",
                "Priority Areas",
                "Beneficiary",
                "End Date",
                "Project Description",
            ),
        }
        records.append(record)
    return records


def _financial_status(row: dict) -> str:
    if _date(row.get("Date of Financing Agreement Signed*")):
        return "signed"
    project_status = _text(row.get("Status"))
    if any(
        word in project_status for word in ("Approved", "Implementation", "Completed")
    ):
        return "approved"
    return "announced"


def build_event_records(
    rows: list[dict],
    *,
    source_id: str,
    document_sha256: str,
    reported_date: str,
) -> list[dict[str, str]]:
    """Build one dated finance observation per official register row."""
    records = []
    for row in rows:
        unique_id = _text(row["Unique ID"])
        signed_date = _date(row.get("Date of Financing Agreement Signed*"))
        amount_usd = _text(row.get("Total US$"))
        record = {
            "event_id": f"{_project_id(unique_id)}-{reported_date}",
            "project_id": _project_id(unique_id),
            "country": "ZAF",
            "event_date": signed_date or reported_date,
            "scope": "jetp_strict",
            "financial_status": _financial_status(row),
            "funder": _text(row.get("Funding Partners"))
            or _text(row.get("Funder/Source")),
            "window": _text(row.get("Portfolios")),
            "instrument": _text(row.get("Funding Instrument")),
            "amount_original": _text(row.get("Amount: Pledged")),
            "currency_original": _text(row.get("Currency: Pledged")),
            "amount_usd": amount_usd,
            "conversion_method": (
                f"JET PMU reported USD equivalent at {reported_date}"
                if amount_usd
                else ""
            ),
            "source_id": source_id,
            "document_sha256": document_sha256,
            "locator": f"Overall - Data, Unique ID {unique_id}",
            "verification_status": "official_register",
            "notes": _notes(
                row,
                "Status",
                "Disbursement Channel",
                "Co-Financing: Name",
                "Institutional / South African Partner",
            )
            + "; project implementation status is not treated as disbursement evidence",
        }
        validate_event_record(record)
        records.append(record)
    return records


def _read_existing(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(fields):
            raise ValueError(f"{path} has incompatible headers")
        return list(reader)


def _write_rows(
    path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def extract_to_ledgers(
    register_html: str | Path,
    projects_path: str | Path,
    events_path: str | Path,
    *,
    source_id: str,
    document_sha256: str,
    reported_date: str,
) -> tuple[int, int]:
    """Replace the rows generated from one register snapshot in both ledgers."""
    register = Path(register_html)
    projects_file = Path(projects_path)
    events_file = Path(events_path)
    rows = parse_register_html(register.read_text(encoding="utf-8"))
    projects = build_project_records(rows, reported_date=reported_date)
    events = build_event_records(
        rows,
        source_id=source_id,
        document_sha256=document_sha256,
        reported_date=reported_date,
    )
    existing_projects = [
        row
        for row in _read_existing(projects_file, PROJECT_FIELDS)
        if not row["project_id"].startswith("zaf-register-")
    ]
    existing_events = [
        row
        for row in _read_existing(events_file, EVENT_FIELDS)
        if row["source_id"] != source_id
    ]
    _write_rows(projects_file, PROJECT_FIELDS, existing_projects + projects)
    _write_rows(events_file, EVENT_FIELDS, existing_events + events)
    return len(projects), len(events)


def main(argv=None) -> None:
    """Extract a collected dashboard snapshot from the command line."""
    io_args, extra = parse_io_args(argv)
    parser = argparse.ArgumentParser()
    parser.add_argument("--events-output", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--document-sha256", required=True)
    parser.add_argument("--reported-date", required=True)
    args = parser.parse_args(extra)
    if not io_args.input or len(io_args.input) != 1:
        parser.error("exactly one --input register HTML is required")
    os.makedirs(Path(io_args.output).parent, exist_ok=True)
    os.makedirs(Path(args.events_output).parent, exist_ok=True)
    validate_io(output=io_args.output, inputs=io_args.input)
    validate_io(output=args.events_output)
    project_count, event_count = extract_to_ledgers(
        io_args.input[0],
        io_args.output,
        args.events_output,
        source_id=args.source_id,
        document_sha256=args.document_sha256,
        reported_date=args.reported_date,
    )
    log.info("extracted %d projects and %d events", project_count, event_count)


if __name__ == "__main__":
    main()
