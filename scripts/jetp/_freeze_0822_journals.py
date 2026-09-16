"""Atomic journal and reconciliation contracts for the JETP 0822 freeze."""

from pathlib import Path

from jetp._freeze_0822_sources import (
    DVC_MIGRATION_PATH,
    INPUTS,
    _document,
    _dvc_migration_input,
    _rows,
)

def _validate_records(records: list[dict]) -> None:
    """Guard the minimal comparative contract without promoting source claims."""
    ids = [record.get("source_candidate_id") for record in records]
    if len(ids) != len(set(ids)) or any(not identity for identity in ids):
        raise ValueError("source candidate IDs must be stable and unique")
    required_coverage = {"transition_function", "financing", "history"}
    for record in records:
        if not record.get("notes") or not record.get("disposition_reason"):
            raise ValueError(
                "reconciled record requires nonempty disposition reason and notes"
            )
        if not record.get("evidence_ref") and not record.get("evidence_gap"):
            raise ValueError(
                "reconciled record needs evidence reference or documented gap"
            )
        if set(record.get("operation_dimension_coverage", {})) != required_coverage:
            raise ValueError("every operation needs A/B/C dimension coverage")
        reconciliation = record.get("reconciliation", {})
        if reconciliation.get("status") not in {
            "exact",
            "interval",
            "incompatible",
            "unavailable",
        }:
            raise ValueError("unknown reconciliation status")
        if reconciliation.get("input_candidate_ids") != [record["source_candidate_id"]]:
            raise ValueError("reconciliation input pedigree changed")
        if not reconciliation.get("adjudication_ids") or not reconciliation.get(
            "notes"
        ):
            raise ValueError("reconciliation needs adjudication provenance and notes")
        if record["financial_bound_type"] == "unknown" and (
            record["financial_lower_original"] is not None
            or record["financial_upper_original"] is not None
        ):
            raise ValueError("unknown money cannot become a bound or zero")
        if record["financial_bound_type"] != "unknown" and not isinstance(
            record["financial_lower_original"], (int, float)
        ):
            raise ValueError("reported money bounds must be numeric with separate currency")
        if record["date_bound_type"] == "unknown" and (
            record["date_lower"] is not None or record["date_upper"] is not None
        ):
            raise ValueError("unknown date cannot become a bound")
        if (
            record["conflict_status"] == "explicit_conflict"
            and reconciliation.get("status") != "incompatible"
        ):
            raise ValueError("explicit conflict must remain incompatible")


def _atomic_journals(
    root: Path, records: list[dict]
) -> tuple[list[dict], list[dict], list[dict]]:
    """Keep document assertions atomic before any reconciliation or operation link."""
    root = Path(root)
    _dvc_migration_input(root)
    migration = _document(root / DVC_MIGRATION_PATH)
    rmp = migration["inventory_positions"]
    if len(rmp) != 279:
        raise ValueError("all 279 VNM RMP rows must remain individually retained")
    event_ids = {
        row["source_assertion"]["observation_id"]
        for row in migration["legacy_position_candidates"]
        if row["classification"] == "event_assertion_pending_evidence"
    }
    raw = {}
    for path, key in (
        (INPUTS[0], "project_id"),
        ("data/jetp/plan-projects.csv", "plan_project_id"),
        (INPUTS[3], "candidate_id"),
        ("data/jetp/vnm-pilot-observations.csv", "observation_id"),
    ):
        raw.update({row[key]: row for row in _rows(root / path)})
    atomic = []
    for record in records:
        if record["source_candidate_id"] == "vnm-rmp-inventory-aggregate":
            continue
        source_id = record["source_candidate_id"]
        source_fields = raw.get(source_id, {})
        atomic.append(
            {
                "source_candidate_id": source_id,
                "country": record["country"],
                "source_layer": "approved_0818_0821",
                "journal": "events" if source_id in event_ids else "positions",
                "unit_identity_status": record["entity_link_status"],
                "kind": record["record_type"],
                "measure": record["measure"],
                "original_label": record["original_label"],
                "original_value": record["original_value"],
                "financial_bound_type": record["financial_bound_type"],
                "financial_lower_original": record["financial_lower_original"],
                "financial_upper_original": record["financial_upper_original"],
                "currency": record["financial_currency"],
                "date_role": record["date_role"],
                "event_date": record["date_lower"] if source_id in event_ids else None,
                "date_lower": record["date_lower"],
                "date_upper": record["date_upper"],
                "disposition": record["disposition"],
                "reason": record["disposition_reason"],
                "notes": record["notes"],
                "evidence_ref": record["evidence_ref"],
                "evidence_gap": record["evidence_gap"],
                "source_fields": source_fields,
            }
        )
    for edition in _rows(root / INPUTS[4]):
        if edition["raw_disposition"] == "index_retained_file_not_retained":
            atomic.append(
                {
                    "source_candidate_id": f"sen-senelec-coverage-{edition['edition']}",
                    "country": "SEN",
                    "source_layer": "senelec_index_coverage",
                    "journal": "coverage",
                    "unit_identity_status": "file_not_retained",
                    "kind": "document_coverage",
                    "measure": "indexed_annual_edition",
                    "original_label": edition["edition"],
                    "original_value": None,
                    "financial_bound_type": "unknown",
                    "financial_lower_original": None,
                    "financial_upper_original": None,
                    "currency": None,
                    "date_role": "publication_year_not_event",
                    "event_date": None,
                    "date_lower": f"{edition['edition']}-01-01",
                    "date_upper": f"{edition['edition']}-12-31",
                    "disposition": "indexed_file_not_retained",
                    "reason": edition["notes"],
                    "notes": edition["notes"],
                    "evidence_ref": {
                        "source_id": edition["source_id"],
                        "edition": edition["edition"],
                    },
                    "evidence_gap": "Indexed edition file was not retained in the bounded corpus.",
                    "source_fields": {
                        key: value for key, value in edition.items() if key is not None
                    },
                }
            )
    for row in rmp:
        atomic.append(
            {
                "source_candidate_id": row["inventory_id"],
                "country": "VNM",
                "source_layer": "vnm_rmp",
                "journal": "positions",
                "unit_identity_status": row["disposition"],
                "kind": row["record_kind"],
                "measure": row["measure"],
                "original_label": row["source_wording"],
                "original_value": row["value"],
                "financial_bound_type": "unknown",
                "financial_lower_original": None,
                "financial_upper_original": None,
                "currency": None,
                "date_role": row["date_role"],
                "event_date": None,
                "date_lower": None,
                "date_upper": None,
                "disposition": row["disposition"],
                "reason": row["reason"],
                "notes": row["reason"],
                "evidence_ref": row["evidence"],
                "evidence_gap": None,
                "source_fields": row,
            }
        )
    if len({row["source_candidate_id"] for row in atomic}) != len(atomic):
        raise ValueError("atomic source candidate identity collision")
    positions = [row for row in atomic if row["journal"] == "positions"]
    events = [row for row in atomic if row["journal"] == "events"]
    return atomic, events, positions


def _reconciliations() -> list[dict]:
    """Small reviewed reconciliations; all other atomic records remain unreconciled."""
    return [
        {
            "reconciliation_id": "vnm-tri-an-018-019",
            "status": "incompatible",
            "input_candidate_ids": [
                "vnm-pilot-observation-018",
                "vnm-pilot-observation-019",
            ],
            "lower_original": None,
            "upper_original": None,
            "currency": "EUR/USD",
            "basis": "signed KfW loan versus later USD valuation",
            "perimeter": "Tri An extension",
            "ownership": "public/unknown",
            "adjudication_ids": ["0822-vnm-tri-an"],
            "method_version": "jetp-comparative-snapshot/1",
            "proof": "Different currencies and semantic bases; values remain separate.",
            "rule": "No addition or conversion without documented common basis.",
            "author": "Codex",
            "notes": "Nonadditive EUR/USD observations.",
        },
        {
            "reconciliation_id": "vnm-bac-ai-020-026",
            "status": "incompatible",
            "input_candidate_ids": [
                f"vnm-pilot-observation-{n:03d}" for n in range(20, 27)
            ],
            "lower_original": None,
            "upper_original": 480000000,
            "currency": "EUR",
            "basis": "facility/package/TA/AFD loan/cost/LOI",
            "perimeter": "Bac Ai",
            "ownership": "mixed_unallocated",
            "adjudication_ids": ["0822-vnm-bac-ai"],
            "method_version": "jetp-comparative-snapshot/1",
            "proof": "Inputs describe different financial objects.",
            "rule": "480m is a sourced facility upper bound, not a project total.",
            "author": "Codex",
            "notes": "Retain each input separately.",
        },
        {
            "reconciliation_id": "vnm-envelopes-001-005",
            "status": "incompatible",
            "input_candidate_ids": [
                f"vnm-pilot-observation-{n:03d}" for n in range(1, 6)
            ],
            "lower_original": 15500000000,
            "upper_original": None,
            "currency": "USD",
            "basis": "public/private envelopes with distinct stated perimeters",
            "perimeter": "varies by source",
            "ownership": "mixed_unallocated",
            "adjudication_ids": ["0822-vnm-envelopes"],
            "method_version": "jetp-comparative-snapshot/1",
            "proof": "Sources explicitly conflict on members/perimeters.",
            "rule": "Preserve lower bound and do not sum components.",
            "author": "Codex",
            "notes": "No catalytic inference.",
        },
        {
            "reconciliation_id": "sen-diass-production-bess",
            "status": "unavailable",
            "input_candidate_ids": ["sen-senelec-2024-diass-generation"],
            "lower_original": None,
            "upper_original": None,
            "currency": None,
            "basis": "solar production versus unlinked BESS proposal",
            "perimeter": "Diass labels differ",
            "ownership": "unknown",
            "adjudication_ids": ["0822-sen-diass"],
            "method_version": "jetp-comparative-snapshot/1",
            "proof": "0821 rejects label-only identity match.",
            "rule": "Keep production and BESS distinct.",
            "author": "Codex",
            "notes": "No operation link asserted.",
        },
    ]
