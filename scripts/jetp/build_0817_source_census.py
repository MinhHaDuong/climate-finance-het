"""Freeze the local JETP source inventory into the 0817 acquisition census."""

import argparse
import csv
from pathlib import Path

from jetp._source_census import COUNTRY_OWNERS, REQUIRED_FIELDS

FINANCIAL_SEMANTICS = {
    "investment_plan": "plan_priority_not_finance",
    "implementation_plan": "plan_or_policy_not_finance",
    "political_declaration": "pledge_not_operation_finance",
    "approval_document": "approval_not_disbursement",
    "project_list": "portfolio_membership_not_finance",
    "progress_update": "reported_position_not_payment",
    "annual_report": "reported_position_not_payment",
    "official_news": "announced_finance_or_event",
    "project_page": "project_profile_not_finance",
    "operator_report": "operator_status_or_reported_finance",
    "data_portal": "discovery_or_snapshot",
}


def _semantics(source_type: str) -> tuple[str, str]:
    financial = FINANCIAL_SEMANTICS.get(source_type, "source_specific_review_required")
    if source_type in {"progress_update", "annual_report"}:
        return financial, "reporting_cutoff_or_publication_review_required"
    if source_type in {"political_declaration", "investment_plan", "implementation_plan"}:
        return financial, "publication_date_not_event_date"
    return financial, "source_date_semantics_review_required"


def build_rows(sources_path: Path, manifest_path: Path) -> list[dict[str, str]]:
    """Build one coverage item per locally declared source, without fetching."""
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    with sources_path.open(encoding="utf-8", newline="") as handle:
        sources = list(csv.DictReader(handle))

    rows: list[dict[str, str]] = []
    for source in sources:
        country = source["country"]
        if country not in COUNTRY_OWNERS:
            continue
        source_id = source["source_id"]
        observation = manifest.get(source_id, {})
        status = observation.get("status", "unavailable")
        version = observation.get("sha256") or source.get("published_date") or "declared-undated"
        financial, date = _semantics(source["source_type"])
        rows.append({
            "item_id": f"{country.lower()}-{source_id}",
            "country": country,
            "source_id": source_id,
            "source_version": version,
            "route": source["expected_format"],
            "expected_item": source["title"],
            "expected_count": "1",
            "financial_semantics": financial,
            "date_semantics": date,
            "retention": "raw_byte_dvc_then_review" if status in {"collected", "not_modified"} else "attempt_log_then_review",
            "disposition": "admitted" if status in {"collected", "not_modified"} else "unavailable",
            "country_owner": COUNTRY_OWNERS[country],
        })
    return sorted(rows, key=lambda row: (row["country"], row["source_id"]))


def write_census(output_path: Path, sources_path: Path, manifest_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_FIELDS)
        writer.writeheader()
        writer.writerows(build_rows(sources_path, manifest_path))


def main() -> None:
    """Write the census from local source metadata; never retrieve a source."""
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "docs" / "jetp-study" / "0817-source-census.csv",
        help="CSV census destination",
    )
    args = parser.parse_args()
    write_census(
        args.output,
        root / "data" / "jetp" / "sources.csv",
        root / "data" / "jetp" / "manifest.csv",
    )


if __name__ == "__main__":
    main()
