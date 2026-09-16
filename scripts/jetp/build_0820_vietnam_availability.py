"""Stage the locally retained Viet Nam corpus without financial promotion.

This is a bounded reconciliation of the existing 0764 RMP candidate and the
legacy pilot observations. It neither retrieves sources nor writes canonical
finance, payment, implementation, or project-identity facts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

COUNTRY = "VNM"
MIGRATION_PATH = Path("data/jetp/releases/vnm-migration-0764.json")
RMP_CLASSIFICATIONS = {"named": 25, "programme": 73, "unknown": 181}
PILOT_CLASSIFICATIONS = {
    "event_assertion_pending_evidence": 7,
    "reported_absence_position": 1,
    "reported_cumulative_position": 3,
    "reported_financial_position": 5,
    "reported_financing_envelope": 15,
    "reported_financing_proposal": 9,
    "reported_portfolio_count": 4,
    "reported_programme_position": 1,
    "withdrawal_assertion_pending_evidence": 1,
}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _migration(root: Path) -> dict:
    path = Path(root) / MIGRATION_PATH
    if not path.is_file():
        raise ValueError("materialized local 0764 Vietnam candidate is required")
    return json.loads(path.read_text(encoding="utf-8"))


def _counter(rows: list[dict], field: str) -> dict[str, int]:
    return dict(sorted(Counter(row[field] for row in rows).items()))


def validate_report(report: dict, root: Path) -> None:
    """Reject an empty or promoted rendition of the bounded candidate corpus."""
    if report.get("country") != COUNTRY:
        raise ValueError("staging result must be Viet Nam")
    if report.get("availability_disposition") != "nonempty_unadmitted_staging":
        raise ValueError("nonempty corpus needs an unadmitted staging disposition")
    rmp = report.get("rmp_inventory_positions")
    pilot = report.get("pilot_observations")
    if not isinstance(rmp, dict) or rmp.get("count") == 0:
        raise ValueError("zero extraction contradicts the retained RMP inventory")
    if rmp.get("count") != 279 or rmp.get("classifications") != RMP_CLASSIFICATIONS:
        raise ValueError("RMP inventory count or classifications changed")
    if rmp.get("admission_status") != "unadmitted_candidate":
        raise ValueError("RMP inventory cannot be promoted to admitted facts")
    if not isinstance(pilot, dict) or pilot.get("count") != 46:
        raise ValueError("pilot observation count changed")
    if pilot.get("classifications") != PILOT_CLASSIFICATIONS:
        raise ValueError("pilot classifications changed")
    if pilot.get("eligible_for_account") is not False:
        raise ValueError("pilot observations cannot enter a financial account")
    migration = _migration(root)
    source = report.get("source_artifact", {})
    if source.get("path") != str(MIGRATION_PATH) or source.get("sha256") != _sha256(
        Path(root) / MIGRATION_PATH
    ):
        raise ValueError(
            "staging report does not identify the retained candidate bytes"
        )
    positions = migration.get("inventory_positions", [])
    candidates = migration.get("legacy_position_candidates", [])
    if len(positions) != rmp["count"] or len(candidates) != pilot["count"]:
        raise ValueError("staging counts do not replay the retained candidate")
    if any(
        row.get("transition_date") is not None or row.get("payment_amount") is not None
        for row in [*positions, *candidates]
    ):
        raise ValueError("staging must not promote dates or payments")


def build_report(root: Path) -> dict:
    """Build a deterministic, source-qualified staging availability result."""
    root = Path(root)
    migration = _migration(root)
    positions = migration.get("inventory_positions", [])
    candidates = migration.get("legacy_position_candidates", [])
    if (
        migration.get("schema_version") != "country-migration/1"
        or migration.get("country") != COUNTRY
    ):
        raise ValueError("0764 candidate is not the Viet Nam migration contract")
    if _counter(positions, "classification") != RMP_CLASSIFICATIONS:
        raise ValueError("0764 RMP inventory is not the declared 279-row population")
    if _counter(candidates, "classification") != PILOT_CLASSIFICATIONS:
        raise ValueError("0764 pilot candidates are not the declared 46-row population")
    pilot_rows = _rows(root / "data" / "jetp" / "vnm-pilot-observations.csv")
    candidate_ids = {row["source_assertion"]["observation_id"] for row in candidates}
    if len(pilot_rows) != 46 or candidate_ids != {
        row["observation_id"] for row in pilot_rows
    }:
        raise ValueError(
            "pilot candidate identities do not replay the retained observation CSV"
        )
    report = {
        "schema_version": "jetp-0820-staging/1",
        "country": COUNTRY,
        "scope": "locally retained 0764 candidate and pilot CSV only; no acquisition",
        "availability_disposition": "nonempty_unadmitted_staging",
        "source_artifact": {
            "path": str(MIGRATION_PATH),
            "sha256": _sha256(root / MIGRATION_PATH),
        },
        "rmp_inventory_positions": {
            "count": len(positions),
            "classifications": _counter(positions, "classification"),
            "admission_status": "unadmitted_candidate",
            "identity_disposition": "unresolved_inventory_membership",
            "financial_disposition": "not_financial_facts",
        },
        "pilot_observations": {
            "count": len(candidates),
            "classifications": _counter(candidates, "classification"),
            "admission_status": "unadmitted_candidate",
            "eligible_for_account": False,
            "financial_disposition": "reported_positions_not_payments",
        },
        "boundary": (
            "RMP rows remain source inventory membership and pilot rows remain pending "
            "reported positions or assertions; proposals, needs, envelopes, and mobilised "
            "amounts are not promoted to payments or canonical financial facts."
        ),
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
        default=root / "docs" / "jetp-study" / "0820-vietnam-staging.json",
    )
    args = parser.parse_args()
    write_report(root, args.output)


if __name__ == "__main__":
    main()
