"""Freeze the bounded four-country JETP comparison handoff for ticket 0730.

This builder consumes the approved 0818--0821 documentary artifacts.  It is not
a portfolio ledger: candidates, source context and staged observations retain
their own denominators and never enter financial or transition-date arithmetic.
"""

import argparse
import csv
import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

INPUTS = (
    "docs/jetp-study/0818-zaf-q1-2026-rows.csv",
    "docs/jetp-study/0819-indonesia-ingestion.json",
    "docs/jetp-study/0820-vietnam-staging.json",
    "docs/jetp-study/0821-senelec-annual-candidates.csv",
    "docs/jetp-study/0821-senelec-annual-editions.csv",
)
SCHEMA_VERSION = "jetp-0822-comparative-snapshot/1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _document(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _input_hashes(root: Path) -> dict[str, dict[str, str]]:
    return {name: {"sha256": _sha256(root / name)} for name in INPUTS}


def _zaf(root: Path) -> dict:
    rows = _rows(root / INPUTS[0])
    if len(rows) != 257 or {row["disposition"] for row in rows} != {
        "unadmitted_candidate"
    }:
        raise ValueError(
            "South Africa register is not the approved 257-row candidate intake"
        )
    if any(row["eligible_for_account"] != "false" for row in rows):
        raise ValueError("South Africa candidates cannot enter the comparative account")
    hashes = {row["document_sha256"] for row in rows}
    sources = {row["source_id"] for row in rows}
    if len(hashes) != 1 or len(sources) != 1:
        raise ValueError("South Africa source linkage is not singular and replayable")
    return {
        "source_denominator": {
            "retained_register_rows": len(rows),
            "retained_sources": len(sources),
        },
        "dispositions": {"unadmitted_register_candidate": len(rows)},
        "admitted_comparative_units": 0,
        "admissibility": "source_layer_unadmitted_candidates",
        "prohibited_inferences": ["payment", "signature_date", "transition_date"],
        "source_links": [
            {"source_id": next(iter(sources)), "document_sha256": next(iter(hashes))}
        ],
    }


def _idn(root: Path) -> dict:
    report = _document(root / INPUTS[1])
    if report.get("country") != "IDN" or report.get("source_count") != 7:
        raise ValueError("Indonesia report is not the approved seven-source intake")
    counts = report.get("candidate_counts")
    if counts != {"canonical_finance_admitted": 0, "plan_priority_candidate": 1142}:
        raise ValueError("Indonesia priority candidates or finance boundary changed")
    sources = report.get("sources", [])
    contextual = [
        item
        for item in sources
        if item.get("candidate_kind") == "contextual_analysis_only"
    ]
    progress = [
        item
        for item in sources
        if item.get("candidate_kind") == "plan_priority_candidate"
    ]
    if (
        len(contextual) != 6
        or len(progress) != 1
        or progress[0].get("candidate_count") != 1142
    ):
        raise ValueError("Indonesia source-level dispositions changed")
    return {
        "source_denominator": {
            "retained_documents": len(sources),
            "reviewed_contextual_documents": len(contextual),
        },
        "dispositions": {
            "reviewed_contextual_source": len(contextual),
            "unadmitted_plan_priority_candidate": progress[0]["candidate_count"],
        },
        "admitted_comparative_units": 0,
        "admissibility": "plan_priorities_and_context_not_finance",
        "prohibited_inferences": [
            "allocation",
            "approval",
            "payment",
            "transition_date",
        ],
        "source_links": [
            {
                "source_id": item["source_id"],
                "document_sha256": item["document_sha256"],
                "disposition": item["review_disposition"],
            }
            for item in sorted(sources, key=lambda item: item["source_id"])
        ],
    }


def _vnm(root: Path) -> dict:
    report = _document(root / INPUTS[2])
    rmp, pilot = report.get("rmp_inventory_positions"), report.get("pilot_observations")
    if (report.get("country"), report.get("availability_disposition")) != (
        "VNM",
        "nonempty_unadmitted_staging",
    ):
        raise ValueError("Viet Nam staging disposition changed")
    if (
        not isinstance(rmp, dict)
        or not isinstance(pilot, dict)
        or rmp.get("count") != 279
        or pilot.get("count") != 46
    ):
        raise ValueError("Viet Nam staged denominators changed")
    if (
        rmp.get("admission_status") != "unadmitted_candidate"
        or pilot.get("eligible_for_account") is not False
    ):
        raise ValueError("Viet Nam staging cannot be promoted")
    source = report.get("source_artifact", {})
    if not source.get("path") or not source.get("sha256"):
        raise ValueError("Viet Nam staging lacks retained source linkage")
    return {
        "source_denominator": {
            "rmp_inventory_positions": rmp["count"],
            "pilot_observations": pilot["count"],
        },
        "dispositions": {
            "unadmitted_pilot_observation": pilot["count"],
            "unadmitted_rmp_inventory_position": rmp["count"],
        },
        "admitted_comparative_units": 0,
        "admissibility": "nonempty_unadmitted_staging",
        "prohibited_inferences": ["payment", "transition_date", "operation_identity"],
        "source_links": [{"path": source["path"], "sha256": source["sha256"]}],
    }


def _sen(root: Path) -> dict:
    candidates = _rows(root / INPUTS[3])
    editions = _rows(root / INPUTS[4])
    if len(candidates) != 6 or {row["candidate_disposition"] for row in candidates} != {
        "unresolved_no_identity"
    }:
        raise ValueError("Senegal candidate count or unresolved disposition changed")
    statuses = Counter(row["raw_disposition"] for row in editions)
    reviewed = [row for row in editions if row["extraction_disposition"] == "reviewed"]
    if (
        len(editions) != 6
        or statuses != {"index_retained_file_not_retained": 4, "raw_retained": 2}
        or len(reviewed) != 2
    ):
        raise ValueError("Senegal edition coverage changed")
    hashes = {row["document_sha256"] for row in reviewed}
    if len(hashes) != 2 or any(not digest for digest in hashes):
        raise ValueError("Senegal retained editions lack document hashes")
    return {
        "source_denominator": {
            "indexed_annual_editions": len(editions),
            "retained_reviewed_editions": len(reviewed),
        },
        "dispositions": {
            "indexed_file_not_retained": statuses["index_retained_file_not_retained"],
            "unresolved_annual_report_candidate": len(candidates),
        },
        "admitted_comparative_units": 0,
        "admissibility": "unresolved_candidates_not_jetp_linked",
        "prohibited_inferences": [
            "jetp_identity",
            "finance_attribution",
            "implementation",
            "transition_date",
        ],
        "source_links": [
            {
                "source_id": row["source_id"],
                "edition": row["edition"],
                "document_sha256": row["document_sha256"],
            }
            for row in sorted(reviewed, key=lambda row: row["edition"])
        ],
    }


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
    countries = {
        "ZAF": _zaf(root),
        "IDN": _idn(root),
        "VNM": _vnm(root),
        "SEN": _sen(root),
    }
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "input_git_sha": input_git_sha,
        "scope": "approved bounded 0818-0821 artifacts; no external acquisition",
        "inputs": _input_hashes(root),
        "countries": countries,
        "admitted_comparative_units": sum(
            item["admitted_comparative_units"] for item in countries.values()
        ),
        "aggregation": {
            "financial_total": "not_computable",
            "transition_date_total": "not_computable",
            "reason": "No country artifact admits a common operation-level financial or dated-transition unit; candidate, context, inventory and unresolved lead denominators are not additive.",
        },
        "handoff": "0730 may describe coverage and documentary dispositions by country; it must not calculate finance, transition timing, or a pooled operation denominator from this snapshot.",
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
    expected = {
        "ZAF": _zaf(Path(root)),
        "IDN": _idn(Path(root)),
        "VNM": _vnm(Path(root)),
        "SEN": _sen(Path(root)),
    }
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
    if snapshot.get("admitted_comparative_units") != 0:
        raise ValueError(
            "unadmitted source material cannot enter the comparative account"
        )
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


def build_manifest(snapshot: dict) -> dict:
    return {
        "schema_version": "jetp-0822-run-manifest/1",
        "input_git_sha": snapshot["input_git_sha"],
        "input_sha256": snapshot["inputs"],
        "snapshot_path": "docs/jetp-study/0822-comparative-snapshot.json",
        "snapshot_sha256": snapshot["snapshot_sha256"],
        "reproduction": "Run this builder with --input-git-sha at the recorded revision; inputs are content-hashed and output rendering is deterministic.",
        "dvc_boundary": "0822 consumes the reviewed Git artifacts. Their source links retain DVC document hashes where applicable; this freeze does not materialize or reinterpret DVC bytes.",
    }


def write_outputs(
    root: Path, snapshot_path: Path, manifest_path: Path, *, input_git_sha: str
) -> None:
    snapshot = build_snapshot(root, input_git_sha=input_git_sha)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_bytes(render_snapshot(snapshot))
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
        default=root / "docs/jetp-study/0822-comparative-snapshot.json",
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
