"""Record the bounded 0820 Viet Nam availability result without acquisition.

The 0817 first-wave inventory deliberately names no Viet Nam object.  This
builder makes that absence explicit as an unmeasured coverage state; it does
not turn the empty extraction queue into a zero-finance or complete-coverage
finding.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

COUNTRY = "VNM"
NO_INITIAL_INVENTORY = "no_initial_extractable_inventory"
NOT_MEASURED = "not_measured_not_zero"
LEAD_IDS = (
    "vnm-rmp-2023",
    "vnm-decision-458-2026",
    "vnm-moit-project-index-2026",
    "vnm-evn-afd-transmission-2025",
    "vnm-evn-kfw-tri-an-2025",
    "vnm-eib-bac-ai-package-2025",
)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_report(report: dict, root: Path) -> None:
    """Fail closed if an empty queue is described as a substantive null."""
    if report.get("country") != COUNTRY:
        raise ValueError("availability result must be Viet Nam")
    initial = report.get("initial_inventory")
    if not isinstance(initial, dict):
        raise ValueError("missing initial inventory")
    if initial.get("expected_objects") != 0 or initial.get("extracted_objects") != 0:
        raise ValueError("Viet Nam first-wave inventory must remain empty")
    if initial.get("evidence_disposition") == "zero_evidence":
        raise ValueError("empty inventory cannot be reported as zero evidence")
    if initial.get("coverage_disposition") == "complete":
        raise ValueError("empty inventory cannot be reported as complete coverage")
    if initial.get("coverage_disposition") != NO_INITIAL_INVENTORY:
        raise ValueError("invalid empty-inventory coverage disposition")
    if initial.get("evidence_disposition") != NOT_MEASURED:
        raise ValueError("empty inventory must remain not measured")
    if not initial.get("reason", "").strip():
        raise ValueError("empty inventory requires a finite reason")

    census = _rows(Path(root) / "docs" / "jetp-study" / "0817-source-census.csv")
    source_ids = {row["source_id"] for row in census if row["country"] == COUNTRY}
    leads = report.get("required_next_source_leads")
    if not isinstance(leads, list) or not leads:
        raise ValueError("empty inventory requires next source leads")
    lead_ids = tuple(
        lead.get("source_id", "") for lead in leads if isinstance(lead, dict)
    )
    if lead_ids != LEAD_IDS or not set(lead_ids) <= source_ids:
        raise ValueError("next source leads must be declared Viet Nam census sources")
    for lead in leads:
        if not lead.get("purpose", "").strip() or not lead.get("boundary", "").strip():
            raise ValueError("next source lead lacks purpose or boundary")


def build_report(root: Path) -> dict:
    """Build the finite availability disposition from the frozen 0817 files."""
    root = Path(root)
    inventory = _rows(root / "docs" / "jetp-study" / "0817-inventory-manifest.csv")
    vnm_inventory = [row for row in inventory if row["country"] == COUNTRY]
    if vnm_inventory:
        raise ValueError("0820 scope changed: Viet Nam now has an inventory object")
    census = _rows(root / "docs" / "jetp-study" / "0817-source-census.csv")
    vnm_census = [row for row in census if row["country"] == COUNTRY]
    if not vnm_census or {row["country_owner"] for row in vnm_census} != {"0820"}:
        raise ValueError("Viet Nam census ownership is not frozen for 0820")
    report = {
        "schema_version": "jetp-0820-availability/1",
        "country": COUNTRY,
        "scope": "0817 initial extractable inventory only; no acquisition",
        "initial_inventory": {
            "expected_objects": 0,
            "extracted_objects": 0,
            "coverage_disposition": NO_INITIAL_INVENTORY,
            "evidence_disposition": NOT_MEASURED,
            "reason": (
                "The frozen 0817 inventory manifest declares no Viet Nam object for "
                "the first extraction wave; the empty queue cannot measure operation, "
                "finance, implementation, or their coverage."
            ),
        },
        "frozen_census_source_count": len(vnm_census),
        "required_next_source_leads": [
            {
                "source_id": "vnm-rmp-2023",
                "purpose": "Review named plan priorities as candidates, not finance or payments.",
                "boundary": "A resource-mobilisation plan cannot by itself establish allocation, approval, or disbursement.",
            },
            {
                "source_id": "vnm-decision-458-2026",
                "purpose": "Review the updated implementation scheme for programme and project references.",
                "boundary": "A policy decision is not operation-level financing evidence without an explicit linked statement.",
            },
            {
                "source_id": "vnm-moit-project-index-2026",
                "purpose": "Retain and review the current official project index when its source byte is available.",
                "boundary": "The census currently marks this index unavailable; it cannot be treated as an empty portfolio.",
            },
            {
                "source_id": "vnm-evn-afd-transmission-2025",
                "purpose": "Adjudicate the transmission financing announcement with its operation identity and event wording.",
                "boundary": "An announcement is not a payment and must retain its stated financial stage.",
            },
            {
                "source_id": "vnm-evn-kfw-tri-an-2025",
                "purpose": "Adjudicate the Tri An financing announcement and potential pre-JETP history.",
                "boundary": "A named project cannot be linked to JETP or dated as a transition without explicit evidence.",
            },
            {
                "source_id": "vnm-eib-bac-ai-package-2025",
                "purpose": "Adjudicate the Bac Ai package while separating package total, contributors, and financing state.",
                "boundary": "A reported package must not be summed with its components or treated as a disbursement.",
            },
        ],
    }
    validate_report(report, root)
    return report


def write_report(root: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_report(root), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "docs" / "jetp-study" / "0820-vietnam-availability.json",
    )
    args = parser.parse_args()
    write_report(root, args.output)


if __name__ == "__main__":
    main()
