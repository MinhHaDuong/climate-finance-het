"""Replay the bounded review of the seven Indonesia 0819 source documents.

This is deliberately a review handoff, not a new financial ledger.  The
progress report's appendix is preserved as plan-priority candidates; the six
thematic reports are contextual analysis and do not by themselves identify an
operation, allocation, approval, or payment.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


INVENTORY_IDS = {
    "idn-progress-report-2025",
    "idn-study-energy-efficiency-2025",
    "idn-study-captive-power-2025",
    "idn-study-just-transition-2025",
    "idn-study-guarantees-2025",
    "idn-study-small-renewables-2025",
    "idn-study-carbon-pricing-2025",
}
PROGRESS_SOURCE = "idn-jetp-progress-report-2025"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _latest_manifest(rows: list[dict[str, str]], source_id: str) -> dict[str, str]:
    for row in reversed(rows):
        if row["source_id"] == source_id and row["storage_path"]:
            return row
    raise ValueError(f"0819 source has no retained raw byte: {source_id}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report(root: Path) -> dict:
    """Build a deterministic, source-qualified disposition for the 0819 intake."""
    root = Path(root)
    data = root / "data" / "jetp"
    inventory = [
        row for row in _rows(root / "docs" / "jetp-study" / "0817-inventory-manifest.csv")
        if row["country"] == "IDN"
    ]
    if {row["inventory_id"] for row in inventory} != INVENTORY_IDS:
        raise ValueError("0819 inventory is not the frozen seven-document scope")
    manifests = _rows(data / "manifest.csv")
    plans = [
        row for row in _rows(data / "plan-projects.csv")
        if row["source_id"] == PROGRESS_SOURCE
    ]
    if len(plans) != 1142 or {row["priority_tier"] for row in plans} - {"priority", "top_priority"}:
        raise ValueError("Indonesia progress priorities are not a complete plan-only extract")

    sources: list[dict] = []
    for item in sorted(inventory, key=lambda row: row["source_id"]):
        source_id = item["source_id"]
        manifest = _latest_manifest(manifests, source_id)
        raw_path = data / "documents" / manifest["storage_path"]
        if not raw_path.is_file() or _sha256(raw_path) != manifest["sha256"]:
            raise ValueError(f"retained raw byte does not match manifest: {source_id}")
        progress = source_id == PROGRESS_SOURCE
        sources.append({
            "inventory_id": item["inventory_id"],
            "source_id": source_id,
            "document_sha256": manifest["sha256"],
            "storage_path": manifest["storage_path"],
            "source_version": manifest["sha256"],
            "retrieval_status": item["retrieval_status"],
            "date_precision": (
                "reporting_cutoff_or_publication_review_required" if progress
                else "publication_or_cutoff_not_event_without_explicit_event_statement"
            ),
            "candidate_kind": "plan_priority_candidate" if progress else "contextual_analysis_only",
            "candidate_count": len(plans) if progress else 0,
            "canonical_finance_admitted": 0,
            "review_disposition": (
                "reviewed_plan_candidates_not_finance" if progress
                else "reviewed_no_operation_candidate"
            ),
            "review_note": (
                "The 1,142 appendix lines remain plan priorities; no allocation, approval, or payment is admitted."
                if progress else
                "The retained thematic report is contextual analysis; this bounded review admits no operation-level fact from it."
            ),
        })
    return {
        "schema_version": "jetp-0819-ingestion/1",
        "country": "IDN",
        "scope": "seven frozen 0817 inventory documents only",
        "source_count": len(sources),
        "candidate_counts": {
            "plan_priority_candidate": len(plans),
            "canonical_finance_admitted": 0,
        },
        "sources": sources,
    }


def write_report(root: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_report(root), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--output", type=Path, default=root / "docs" / "jetp-study" / "0819-indonesia-ingestion.json")
    args = parser.parse_args()
    write_report(root, args.output)


if __name__ == "__main__":
    main()
