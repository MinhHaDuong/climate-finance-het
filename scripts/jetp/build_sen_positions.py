"""Build Senegal's unadmitted plan-position sidecar beside the unchanged MVP."""

import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path

from jetp._compatibility import MVP_VIEWS, read_mvp_view
from jetp._contracts import validate_evidence_tuple
from jetp._country_migration import SCHEMA_VERSION, inventory_positions, legacy_dispositions
from jetp._observatory_bundle import _protect_output, _protect_replacement
from jetp._sen_positions import migrate_positions
from jetp._source_crosswalk import _identity, migrate_sources


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _context(policy: dict, crosswalk: dict, rows: list[dict], recipe: dict) -> dict:
    attempts = [row for row in crosswalk["acquisitions"] if all(
        row[key] == policy[key] for key in ("source_id", "retrieved_at", "document_sha256"))]
    if len(attempts) != 1 or attempts[0]["byte_status"] != "available":
        raise ValueError("Selected Senegal source bytes are not recoverable")
    edition = {"record_kind": "edition", "record_id": policy["edition_id"]}
    snapshot = {"record_kind": "edition_snapshot", "edition": edition,
                "document_sha256": policy["document_sha256"],
                "acquisition_id": attempts[0]["acquisition_id"], "review_state": "pending"}
    parser = {"name": "legacy-committed-plan-inventory", "recipe_inputs": recipe,
              "status": "source-row transcription retained; saved PDF remains original evidence"}
    extraction = {"extraction_id": _identity("extraction", [policy["document_sha256"], parser]),
                  "document_sha256": policy["document_sha256"], "parser": parser,
                  "output_sha256": hashlib.sha256(encoded(rows)).hexdigest(),
                  "locators": [row["locator"] for row in rows],
                  "admission_status": "unadmitted_candidate"}
    return {"policy": policy, "acquisition": attempts[0], "edition_snapshot": snapshot,
            "extraction": extraction}


def _inventory(rows: list[dict]) -> list[dict]:
    return [{"inventory_id": row["source_id"], "ordinal": int(row["ordinal"]),
             "source_wording": row["project_name"], "source_fields": row,
             "locator": row["locator"], "source_id": row["source_id"],
             "classification": ("received_project" if row["technology_group"] == "submitted_project"
                                else "quick_win")}
            for row in rows]


def build_migration(root: Path, *, source_root: Path | None = None) -> dict:
    root, source_root = Path(root).resolve(), Path(source_root or root).resolve()
    policy = json.loads((root / "config/jetp-sen-migration.json").read_text())
    crosswalk = migrate_sources(root, source_root=source_root)
    committed = [row for row in crosswalk["inputs"]["data/jetp/plan-projects.csv"]["rows"]
                 if row["country"] == "SEN" and row["source_id"] in {p["source_id"] for p in policy["sources"]}]
    source_order = {entry["source_id"]: number for number, entry in enumerate(policy["sources"])}
    rows = sorted(committed, key=lambda row: (source_order[row["source_id"]], int(row["ordinal"])))
    expected = {entry["source_id"]: entry["row_count"] for entry in policy["sources"]}
    if Counter(row["source_id"] for row in rows) != Counter(expected):
        raise ValueError("Incomplete selected Senegal plan inventories")
    recipe_paths = ["scripts/jetp/_sen_positions.py", "scripts/jetp/build_sen_positions.py",
                    "scripts/jetp/_country_migration.py", "config/jetp-sen-migration.json"]
    recipe = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in recipe_paths}
    contexts = {entry["source_id"]: _context(entry, crosswalk,
                [row for row in rows if row["source_id"] == entry["source_id"]], recipe)
                for entry in policy["sources"]}
    projects = [row for row in crosswalk["inputs"]["data/jetp/projects.csv"]["rows"] if row["country"] == "SEN"]
    inventory = inventory_positions("SEN", _inventory(rows), projects, {})
    for position in inventory:
        context = contexts[position["source_id"]]
        evidence = {"document_sha256": context["policy"]["document_sha256"],
                    "edition": context["edition_snapshot"]["edition"], "locator": position["locator"],
                    "acquisition_id": context["acquisition"]["acquisition_id"],
                    "extraction_id": context["extraction"]["extraction_id"], "source_id": position["source_id"]}
        validate_evidence_tuple(evidence, context["acquisition"], context["extraction"], [context["edition_snapshot"]])
        position.update(evidence=evidence, eligible_for_account=False,
                        candidate_created_at=policy["recorded_at"])
    plan_rows = [{"inventory_id": row["source_id"], "ordinal": int(row["ordinal"]),
                  "source_wording": row["project_name"], "amount_original": row["estimated_investment_usd_mn"] or None,
                  "currency_original": "USD_million" if row["estimated_investment_usd_mn"] else None,
                  "locator": row["locator"], "position_role": "received_proposal" if row["technology_group"] == "submitted_project" else "quick_win",
                  "source_plan_row": row} for row in rows]
    provisional = [{"plan_inventory_id": f"{row['source_id']}:{int(row['ordinal'])}",
                    "legacy_project_id": row["canonical_project_id"],
                    "rationale": "Legacy plan table link retained as a provisional candidate; it does not establish identity, component relation, financing, or implementation"}
                   for row in rows if row["canonical_project_id"]]
    semantic = migrate_positions(plan_rows=plan_rows, provisional_matches=provisional)
    legacy = legacy_dispositions(crosswalk, "SEN", {})
    selected_ids = {row["row_id"] for row in legacy}
    views = {view: read_mvp_view(root, view, supported_versions={"mvp/1"}) for view in sorted(MVP_VIEWS)}
    result = {"schema_version": SCHEMA_VERSION, "country": "SEN", "admission_status": "unadmitted_candidate",
              "writer_owner": "legacy", "publication_mode": "legacy",
              "inputs": {name: {key: value for key, value in info.items() if key != "rows"}
                         for name, info in crosswalk["inputs"].items()}, "recipe_inputs": recipe,
              "recovery_inputs": crosswalk["recovery_inputs"], "selected_sources": list(contexts.values()),
              "inventory_positions": inventory, **semantic, "legacy_dispositions": legacy,
              "legacy_evidence": [row for row in crosswalk["evidence"] if row["legacy_row_id"] in selected_ids],
              "legacy_unresolved": [row for row in crosswalk["unresolved"] if row["legacy_row_id"] in selected_ids],
              "inventory_boundaries": [{"inventory_id": entry["source_id"], "disposition": "selected",
                                        "row_count": entry["row_count"], "role": entry["role"]}
                                       for entry in policy["sources"]], "source_regime": policy["source_regime"],
              "mvp_views": views,
              "comparison": {"legacy_rows_by_table": dict(Counter(row["path"] for row in legacy)),
                             "inventory_rows_by_source": dict(Counter(row["source_id"] for row in rows)),
                             "existing_project_ids": [row["project_id"] for row in projects],
                             "added_public_project_ids": [], "removed_public_project_ids": [],
                             "financial_event_additions": 0, "website_semantic_changes": [],
                             "reason": "Candidate preserves legacy ownership and every MVP view"}}
    validate_migration(result)
    return result


def validate_migration(result: dict) -> None:
    if result["writer_owner"] != "legacy" or result["publication_mode"] != "legacy":
        raise ValueError("Senegal candidate cannot transfer ownership")
    if set(result["mvp_views"]) != MVP_VIEWS or result["payment_candidates"] or result["account_total"] is not None:
        raise ValueError("Candidate must retain views and create no account")
    for boundary in result["inventory_boundaries"]:
        rows = [row for row in result["inventory_positions"] if row["inventory_id"] == boundary["inventory_id"]]
        if sorted(row["ordinal"] for row in rows) != list(range(1, boundary["row_count"] + 1)):
            raise ValueError("Incomplete selected Senegal inventory")
    if any(row["match_status"] != "provisional" for row in result["provisional_matches"]):
        raise ValueError("Senegal legacy links must remain provisional")
    if any(row["disposition"] != "retained_legacy_authority" for row in result["legacy_dispositions"]):
        raise ValueError("Incomplete Senegal legacy disposition")


def _country_output(output: Path) -> bool:
    try:
        previous = json.loads(output.read_bytes())
        required = {"schema_version", "country", "admission_status", "writer_owner", "publication_mode", "inputs",
                    "recipe_inputs", "recovery_inputs", "selected_sources", "inventory_positions", "plan_positions",
                    "provisional_matches", "payment_candidates", "account_total", "legacy_dispositions", "legacy_evidence",
                    "legacy_unresolved", "inventory_boundaries", "source_regime", "mvp_views", "comparison"}
        if not isinstance(previous, dict) or previous.keys() != required or previous["country"] != "SEN":
            return False
        validate_migration(previous)
        return all(previous[key] for key in ("selected_sources", "inventory_positions", "plan_positions", "legacy_dispositions"))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def write_migration(root: Path, output: Path, *, source_root: Path | None = None) -> dict:
    root, output = Path(root).resolve(), Path(output)
    _protect_replacement(output, _country_output(output))
    output = output.resolve()
    if output.suffix != ".json":
        raise ValueError("Country candidate output must end in .json")
    source_root = Path(source_root or root).resolve()
    for checkout in {root, source_root}:
        _protect_output(checkout, output, inputs=[path for path in (checkout / "data/jetp/releases").rglob("*") if path.is_file() and path != output])
    result = build_migration(root, source_root=source_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(encoded(result)); stream.flush(); os.fsync(stream.fileno()); os.replace(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)
    return result
