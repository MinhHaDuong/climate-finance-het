"""Shared parsing and CSV helpers for Indonesian priority-project tables."""

import csv
import re
from pathlib import Path

FIELDS = [
    "plan_project_id",
    "country",
    "source_id",
    "technology_group",
    "priority_tier",
    "ordinal",
    "project_name",
    "system",
    "estimated_start",
    "capacity_value",
    "capacity_unit",
    "estimated_investment_usd_mn",
    "natural_retirement_year",
    "estimated_retirement_year",
    "ruptl",
    "canonical_project_id",
    "reconciliation_status",
    "document_sha256",
    "locator",
    "notes",
]


def text(value: object) -> str:
    return " ".join(str(value or "").split())


def number(value: str) -> str:
    """Normalise Indonesian decimal commas and thousands separators."""
    value = text(value)
    if not value or value in {"TBD", "N/A"}:
        return ""
    if re.fullmatch(r"\d+,\d{2}", value):
        return value.replace(",", ".")
    return value.replace(",", "")


def ordinal(value: object) -> tuple[int, str] | None:
    match = re.fullmatch(r"\s*(\d+)\s*\.?\s*(.*?)\s*", str(value or ""))
    if not match:
        return None
    return int(match.group(1)), match.group(2)


def write_csv(
    rows: list[dict[str, str]],
    output: Path,
    source_id: str,
) -> None:
    preserved: list[dict[str, str]] = []
    if output.exists():
        with output.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames and set(FIELDS) <= set(reader.fieldnames):
                preserved = [row for row in reader if row["source_id"] != source_id]
    combined = sorted(
        [*preserved, *rows], key=lambda row: (row["source_id"], row["plan_project_id"])
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(combined)
