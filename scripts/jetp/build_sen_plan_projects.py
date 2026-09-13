"""Build Senegal plan-project rows from the 2025 plan and annex PDFs."""

import argparse
import csv
import hashlib
import re
from pathlib import Path

import pdfplumber

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

MAIN_SOURCE_ID = "sen-investment-plan-l4-mirror"
ANNEX_SOURCE_ID = "sen-investment-plan-annexes-mirror"
MAIN_SHA256 = "97c36b242257462f024a934baee6bed3aa02fe0e4917f076d7b865701db65dca"
ANNEX_SHA256 = "dcd4fd924f9e637d36beb192f509b7971b8b5dda0a76e3c17b799ba26ff43b21"


def _require_sha256(path: Path, expected: str) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(
            f"SHA-256 mismatch for {path}: expected {expected}, got {actual}"
        )


def _text(value: object) -> str:
    return " ".join(str(value or "").split())


def _base_record(
    *,
    plan_project_id: str,
    source_id: str,
    technology_group: str,
    priority_tier: str,
    ordinal: int,
    project_name: str,
    document_sha256: str,
    locator: str,
    notes: str,
) -> dict[str, str]:
    return {
        "plan_project_id": plan_project_id,
        "country": "SEN",
        "source_id": source_id,
        "technology_group": technology_group,
        "priority_tier": priority_tier,
        "ordinal": str(ordinal),
        "project_name": project_name,
        "system": "",
        "estimated_start": "",
        "capacity_value": "",
        "capacity_unit": "",
        "estimated_investment_usd_mn": "",
        "natural_retirement_year": "",
        "estimated_retirement_year": "",
        "ruptl": "",
        "canonical_project_id": "",
        "reconciliation_status": "plan_only",
        "document_sha256": document_sha256,
        "locator": locator,
        "notes": notes,
    }


def extract_received_projects(annexes_path: Path) -> list[dict[str, str]]:
    """Return all 38 submissions in Annex 2, without implying prioritisation."""
    _require_sha256(annexes_path, ANNEX_SHA256)
    records: list[dict[str, str]] = []
    with pdfplumber.open(annexes_path) as pdf:
        for page_number in (13, 14, 15):
            table = pdf.pages[page_number - 1].extract_tables()[0]
            for row in table:
                ordinal_text = _text(row[0])
                if not ordinal_text.isdigit():
                    continue
                ordinal = int(ordinal_text)
                project_name = _text(row[1])
                strategic_axis = _text(row[2])
                promoter = _text(row[5])
                records.append(
                    _base_record(
                        plan_project_id=f"sen-annex-received-{ordinal:02d}",
                        source_id=ANNEX_SOURCE_ID,
                        technology_group="submitted_project",
                        priority_tier="",
                        ordinal=ordinal,
                        project_name=project_name,
                        document_sha256=ANNEX_SHA256,
                        locator=f"Annex 2, p. {page_number}, row {ordinal}",
                        notes=(
                            "Project received for evaluation; "
                            f"strategic orientation axis {strategic_axis}; "
                            f"promoter={promoter}; receipt is not approval, financing "
                            "or implementation"
                        ),
                    )
                )

    if [int(row["ordinal"]) for row in records] != list(range(1, 39)):
        raise ValueError("expected contiguous Senegal received-project ordinals 1-38")
    return records


def extract_quick_wins(main_plan_path: Path) -> list[dict[str, str]]:
    """Return the eleven top-priority lines from the main plan's page 33."""
    _require_sha256(main_plan_path, MAIN_SHA256)
    records: list[dict[str, str]] = []
    with pdfplumber.open(main_plan_path) as pdf:
        tables = pdf.pages[32].extract_tables()
        table = next(
            table for table in tables if _text(table[0][1]) == "Projet Quick Win"
        )
        for row in table[1:]:
            match = re.fullmatch(r"QW(\d+)", _text(row[0]))
            if not match:
                continue
            ordinal = int(match.group(1))
            project_name = _text(row[1])
            strategic_axis = _text(row[2])
            notes = (
                "Plan top-priority line; "
                f"strategic orientation axis {strategic_axis}; quick-win designation "
                "is not finance or implementation"
            )
            if ordinal == 11:
                notes += (
                    "; the same PDF says 1,000 solarised boreholes on p. 78 and "
                    "2,000 hybridised boreholes on pp. 33 and 354; wording here "
                    "follows p. 33 without resolving the conflict"
                )
            records.append(
                _base_record(
                    plan_project_id=f"sen-plan-qw-{ordinal:02d}",
                    source_id=MAIN_SOURCE_ID,
                    technology_group="quick_win",
                    priority_tier="top_priority",
                    ordinal=ordinal,
                    project_name=project_name,
                    document_sha256=MAIN_SHA256,
                    locator=f"p. 33, QW{ordinal}",
                    notes=notes,
                )
            )

    if [int(row["ordinal"]) for row in records] != list(range(1, 12)):
        raise ValueError("expected contiguous Senegal quick-win ordinals 1-11")
    return records


def write_csv(rows: list[dict[str, str]], output: Path) -> None:
    replaced_sources = {MAIN_SOURCE_ID, ANNEX_SOURCE_ID}
    preserved: list[dict[str, str]] = []
    reviewed: dict[tuple[str, str, str], dict[str, str]] = {}
    if output.exists():
        with output.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != FIELDS:
                raise ValueError("unexpected plan-projects schema")
            existing = list(reader)
            preserved = [
                row for row in existing if row["source_id"] not in replaced_sources
            ]
            reviewed = {
                (
                    row["plan_project_id"],
                    row["source_id"],
                    row["document_sha256"],
                ): row
                for row in existing
                if row["source_id"] in replaced_sources
            }
    for row in rows:
        key = (row["plan_project_id"], row["source_id"], row["document_sha256"])
        if previous := reviewed.get(key):
            for field in ("canonical_project_id", "reconciliation_status", "notes"):
                row[field] = previous[field]
    combined = sorted(
        [*preserved, *rows],
        key=lambda row: (row["country"], row["source_id"], row["plan_project_id"]),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(combined)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-plan", type=Path, required=True)
    parser.add_argument("--annexes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [
        *extract_received_projects(args.annexes),
        *extract_quick_wins(args.main_plan),
    ]
    write_csv(rows, args.output)


if __name__ == "__main__":
    main()
