"""Freeze the bounded four-country JETP comparison handoff for ticket 0730.

This builder consumes the approved 0818--0821 documentary artifacts.  It is not
a portfolio ledger: candidates, source context and staged observations retain
their own denominators and never enter financial or transition-date arithmetic.
"""

import argparse
import csv
import gzip
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
    "data/jetp/plan-projects.csv",
    "data/jetp/vnm-pilot-observations.csv",
    "data/jetp/vnm-pilot-manifest.csv",
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


def _record(
    *,
    record_id: str,
    country: str,
    record_type: str,
    source_id: str,
    document_sha256: str | None,
    locator: str,
    extraction_method: str,
    semantic_interpretation: str,
    entity_label: str,
    entity_link_status: str,
    entity_link_confidence: str,
    link_dedup_rule: str,
    financial_semantic_status: str,
    financial_amount_original: str | None,
    financial_currency: str | None,
    financial_bound_type: str,
    date_semantic_status: str,
    date_value: str | None,
    date_bound_type: str,
    conflict_status: str,
    conflict_note: str | None,
    missingness_reason: str | None,
) -> dict:
    """One source-linked descriptive record; unknown is retained, never zeroed."""
    financial_lower = (
        financial_amount_original
        if financial_bound_type
        in {"point_as_reported", "point_as_reported_millions", "lower_bound"}
        else None
    )
    financial_upper = (
        financial_amount_original
        if financial_bound_type in {"point_as_reported", "point_as_reported_millions"}
        else None
    )
    if date_bound_type == "year" and date_value and len(date_value) == 4:
        date_lower, date_upper = f"{date_value}-01-01", f"{date_value}-12-31"
    elif date_bound_type == "point_as_reported":
        date_lower = date_upper = date_value
    else:
        date_lower = date_upper = None
    reconciliation_status = (
        "incompatible"
        if conflict_status == "explicit_conflict"
        else "unavailable"
        if financial_bound_type == "unknown" and date_bound_type == "unknown"
        else "exact"
    )
    adjudication_ids = {
        "ZAF": ["0818-zaf-q1-2026"],
        "IDN": ["0819-indonesia-ingestion"],
        "VNM": ["0820-vietnam-staging"],
        "SEN": ["0821-senelec-annual-review"],
    }[country]
    record = {
        "record_id": record_id,
        "source_candidate_id": record_id,
        "country": country,
        "record_type": record_type,
        "observation_kind": record_type,
        "measure": "source_position_or_candidate",
        "original_label": entity_label,
        "original_value": financial_amount_original,
        "included_in_descriptive_subset": True,
        "pedigree": {
            "raw_source_id": source_id,
            "raw_document_sha256": document_sha256,
            "locator": locator,
            "extraction_method": extraction_method,
            "semantic_interpretation": semantic_interpretation,
            "link_dedup_rule": link_dedup_rule,
            "confidence": entity_link_confidence,
        },
        "entity_label": entity_label,
        "entity_link_status": entity_link_status,
        "entity_link_confidence": entity_link_confidence,
        "financial_semantic_status": financial_semantic_status,
        "financial_amount_original": financial_amount_original,
        "financial_currency": financial_currency,
        "financial_bound_type": financial_bound_type,
        "financial_lower_original": financial_lower,
        "financial_upper_original": financial_upper,
        "date_semantic_status": date_semantic_status,
        "date_value": date_value,
        "date_bound_type": date_bound_type,
        "date_lower": date_lower,
        "date_upper": date_upper,
        "conflict_status": conflict_status,
        "conflict_note": conflict_note,
        "missingness_reason": missingness_reason,
        "date_role": date_semantic_status,
        "disposition": entity_link_status,
        "disposition_reason": semantic_interpretation,
        "notes": conflict_note or missingness_reason or semantic_interpretation,
        "evidence_ref": (
            {"document_sha256": document_sha256, "locator": locator}
            if document_sha256
            else None
        ),
        "evidence_gap": (
            None
            if document_sha256
            else "No retained raw document byte is available in this bounded artifact."
        ),
        "operation_dimension_coverage": {
            "transition_function": "source_label_only_unclassified",
            "financing": financial_semantic_status,
            "history": date_semantic_status,
        },
        "reconciliation": {
            "status": reconciliation_status,
            "lower_original": financial_lower,
            "upper_original": financial_upper,
            "currency": financial_currency,
            "basis": financial_semantic_status,
            "perimeter": "source_stated_or_unknown",
            "ownership": "mixed_unallocated_or_unknown",
            "input_candidate_ids": [record_id],
            "excluded_candidate_ids": [],
            "adjudication_ids": adjudication_ids,
            "method_version": "jetp-comparative-snapshot/1",
            "reason": semantic_interpretation,
            "notes": conflict_note or missingness_reason or semantic_interpretation,
            "precedence_rule": (
                "0818 source-layer rule retains the register signed-date label but overrides any legacy interpretation of it as a verified signature/event."
                if country == "ZAF"
                else "Approved 0818-0821 bounded artifact takes precedence over incompatible legacy interpretations."
            ),
        },
    }
    return record


def _zaf(root: Path) -> tuple[dict, list[dict]]:
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
    records = [
        _record(
            record_id=row["project_id"],
            country="ZAF",
            record_type="register_candidate",
            source_id=row["source_id"],
            document_sha256=row["document_sha256"],
            locator=row["locator"],
            extraction_method="0818 retained-register row extraction",
            semantic_interpretation="Register pledge/status position; never a payment, verified signature, or transition event.",
            entity_label=row["project_name"],
            entity_link_status="source_register_identity_only",
            entity_link_confidence="high",
            link_dedup_rule="Official unique ID is retained; no cross-source operation link is asserted.",
            financial_semantic_status=(
                "reported_pledge_position_not_payment"
                if row["amount_pledged_original"]
                else "unknown"
            ),
            financial_amount_original=row["amount_pledged_original"] or None,
            financial_currency=row["currency_pledged"] or None,
            financial_bound_type=(
                "point_as_reported" if row["amount_pledged_original"] else "unknown"
            ),
            date_semantic_status=(
                "register_date_label_not_transition"
                if row["register_financing_agreement_label"]
                else "unknown"
            ),
            date_value=row["register_financing_agreement_label"] or None,
            date_bound_type=(
                "point_as_reported"
                if row["register_financing_agreement_label"]
                else "unknown"
            ),
            conflict_status="not_assessed_in_bounded_register",
            conflict_note=None,
            missingness_reason=(
                "Register field blank."
                if not row["amount_pledged_original"]
                or not row["register_financing_agreement_label"]
                else None
            ),
        )
        for row in rows
    ]
    return {
        "source_denominator": {
            "retained_register_rows": len(rows),
            "retained_sources": len(sources),
        },
        "dispositions": {"unadmitted_register_candidate": len(rows)},
        "structured_record_count": len(records),
        "admissibility": "source_layer_unadmitted_candidates",
        "prohibited_inferences": ["payment", "signature_date", "transition_date"],
        "source_links": [
            {"source_id": next(iter(sources)), "document_sha256": next(iter(hashes))}
        ],
    }, records


def _idn(root: Path) -> tuple[dict, list[dict]]:
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
    plan_rows = [
        row
        for row in _rows(root / "data/jetp/plan-projects.csv")
        if row["source_id"] == "idn-jetp-progress-report-2025"
    ]
    if len(plan_rows) != 1142:
        raise ValueError("Indonesia structured priority rows changed")
    records = [
        _record(
            record_id=row["plan_project_id"],
            country="IDN",
            record_type="plan_priority_candidate",
            source_id=row["source_id"],
            document_sha256=row["document_sha256"],
            locator=row["locator"],
            extraction_method="0819 retained progress-report appendix extraction",
            semantic_interpretation="Priority-plan row; not an allocation, approval, payment, or transition event.",
            entity_label=row["project_name"],
            entity_link_status=(
                "crosswalk_candidate"
                if row["canonical_project_id"]
                else "plan_identity_only"
            ),
            entity_link_confidence=(
                "reviewed" if row["canonical_project_id"] else "source_only"
            ),
            link_dedup_rule="Retain source plan ID; a blank canonical ID is not imputed and a candidate crosswalk is not a finance link.",
            financial_semantic_status=(
                "estimated_plan_investment_not_finance"
                if row["estimated_investment_usd_mn"]
                else "unknown"
            ),
            financial_amount_original=row["estimated_investment_usd_mn"] or None,
            financial_currency=("USD" if row["estimated_investment_usd_mn"] else None),
            financial_bound_type=(
                "point_as_reported_millions"
                if row["estimated_investment_usd_mn"]
                else "unknown"
            ),
            date_semantic_status=(
                "estimated_plan_start_not_transition"
                if row["estimated_start"]
                else "unknown"
            ),
            date_value=row["estimated_start"] or None,
            date_bound_type=(
                "year"
                if row["estimated_start"] and len(row["estimated_start"]) == 4
                else "point_as_reported"
                if row["estimated_start"]
                else "unknown"
            ),
            conflict_status="not_assessed_in_bounded_plan",
            conflict_note=None,
            missingness_reason=(
                "Plan appendix does not report estimated investment."
                if not row["estimated_investment_usd_mn"]
                else None
            ),
        )
        for row in plan_rows
    ]
    records.extend(
        _record(
            record_id=f"idn-context-{item['source_id']}",
            country="IDN",
            record_type="reviewed_contextual_source",
            source_id=item["source_id"],
            document_sha256=item["document_sha256"],
            locator=f"reviewed page {item['adjudication']['page']}",
            extraction_method="0819 page-located thematic adjudication",
            semantic_interpretation=item["review_note"],
            entity_label=item["source_id"],
            entity_link_status="no_operation_candidate",
            entity_link_confidence="reviewed",
            link_dedup_rule="Contextual source is retained once and does not establish an operation or finance link.",
            financial_semantic_status="unknown",
            financial_amount_original=None,
            financial_currency=None,
            financial_bound_type="unknown",
            date_semantic_status="unknown",
            date_value=None,
            date_bound_type="unknown",
            conflict_status="not_assessed_in_bounded_context_review",
            conflict_note=None,
            missingness_reason="Reviewed source identifies no operation-specific allocation, approval, payment, or event.",
        )
        for item in contextual
    )
    return {
        "source_denominator": {
            "retained_documents": len(sources),
            "reviewed_contextual_documents": len(contextual),
        },
        "dispositions": {
            "reviewed_contextual_source": len(contextual),
            "unadmitted_plan_priority_candidate": progress[0]["candidate_count"],
        },
        "structured_record_count": len(records),
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
    }, records


def _vnm(root: Path) -> tuple[dict, list[dict]]:
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
    source_manifest = {
        row["legacy_filename"]: row
        for row in _rows(root / "data/jetp/vnm-pilot-manifest.csv")
    }
    pilot_rows = _rows(root / "data/jetp/vnm-pilot-observations.csv")
    if len(pilot_rows) != 46:
        raise ValueError("Viet Nam pilot rows changed")
    records = []
    for row in pilot_rows:
        source_row = source_manifest.get(row["source_filename"])
        if source_row is None:
            raise ValueError(
                "Viet Nam pilot observation lacks source-manifest pedigree"
            )
        conflict = "CONFLIT" in row["notes"]
        lower_bound = "at least" in row["notes"].lower()
        records.append(
            _record(
                record_id=row["observation_id"],
                country="VNM",
                record_type="pilot_observation",
                source_id=source_row["source_id"],
                document_sha256=source_row["sha256"],
                locator=row["locator"],
                extraction_method="0764 retained pilot observation extraction",
                semantic_interpretation=(
                    "Reported position/assertion retained as staged evidence; it is not promoted to payment or independently verified transition."
                ),
                entity_label=row["operation"],
                entity_link_status="source_assertion_subject_unresolved",
                entity_link_confidence=row["confidence"],
                link_dedup_rule="Keep each source assertion; conflict or duplicate notes prohibit additive aggregation.",
                financial_semantic_status="reported_amount_not_payment",
                financial_amount_original=row["amount_original"] or None,
                financial_currency=row["currency_original"] or None,
                financial_bound_type=(
                    "lower_bound" if lower_bound else "point_as_reported"
                ),
                date_semantic_status="reported_event_assertion_pending_evidence",
                date_value=row["event_date"] or None,
                date_bound_type=(
                    "point_as_reported" if row["event_date"] else "unknown"
                ),
                conflict_status=(
                    "explicit_conflict"
                    if conflict
                    else "no_explicit_conflict_not_deduplicated"
                ),
                conflict_note=(row["notes"] if conflict else None),
                missingness_reason=None,
            )
        )
    records.append(
        _record(
            record_id="vnm-rmp-inventory-aggregate",
            country="VNM",
            record_type="rmp_inventory_coverage_group",
            source_id="vnm-migration-0764",
            document_sha256=source["sha256"],
            locator="rmp_inventory_positions (279 staged rows)",
            extraction_method="0820 staged migration summary",
            semantic_interpretation="Aggregate inventory membership only; the 279 source rows are not materialized here and do not establish operation identity or finance.",
            entity_label="Viet Nam RMP inventory positions",
            entity_link_status="aggregate_inventory_identity_unresolved",
            entity_link_confidence="source_only",
            link_dedup_rule="Keep aggregate coverage separate; do not fabricate individual candidate IDs from a count.",
            financial_semantic_status="unknown",
            financial_amount_original=None,
            financial_currency=None,
            financial_bound_type="unknown",
            date_semantic_status="unknown",
            date_value=None,
            date_bound_type="unknown",
            conflict_status="not_assessed_in_staging_summary",
            conflict_note=None,
            missingness_reason="Only the 279-row count/classification summary is available in this worktree.",
        )
    )
    return {
        "source_denominator": {
            "rmp_inventory_positions": rmp["count"],
            "pilot_observations": pilot["count"],
        },
        "dispositions": {
            "unadmitted_pilot_observation": pilot["count"],
            "unadmitted_rmp_inventory_position": rmp["count"],
        },
        "structured_record_count": len(records),
        "admissibility": "nonempty_unadmitted_staging",
        "prohibited_inferences": ["payment", "transition_date", "operation_identity"],
        "source_links": [{"path": source["path"], "sha256": source["sha256"]}],
    }, records


def _sen(root: Path) -> tuple[dict, list[dict]]:
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
    records = [
        _record(
            record_id=row["candidate_id"],
            country="SEN",
            record_type=row["candidate_type"],
            source_id=row["source_id"],
            document_sha256=row["document_sha256"],
            locator=row["locator"],
            extraction_method="0821 page-located annual-report candidate extraction",
            semantic_interpretation="Annual-report lead; JETP identity, finance attribution, and implementation link remain unresolved.",
            entity_label=row["candidate_summary"],
            entity_link_status="unresolved_no_identity",
            entity_link_confidence="source_only",
            link_dedup_rule="Shared location/technology/capacity is insufficient for a JETP operation link; retain separately.",
            financial_semantic_status="unknown",
            financial_amount_original=None,
            financial_currency=None,
            financial_bound_type="unknown",
            date_semantic_status="unknown",
            date_value=None,
            date_bound_type="unknown",
            conflict_status="not_assessed_in_bounded_candidate_review",
            conflict_note=None,
            missingness_reason=row["reason"],
        )
        for row in candidates
    ]
    return {
        "source_denominator": {
            "indexed_annual_editions": len(editions),
            "retained_reviewed_editions": len(reviewed),
        },
        "dispositions": {
            "indexed_file_not_retained": statuses["index_retained_file_not_retained"],
            "unresolved_annual_report_candidate": len(candidates),
        },
        "structured_record_count": len(records),
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
    }, records


def _digest(snapshot: dict) -> str:
    unsigned = deepcopy(snapshot)
    unsigned.pop("snapshot_sha256", None)
    return hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


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
    migration = _document(root / "data/jetp/releases/vnm-migration-0764.json")
    rmp = migration["inventory_positions"]
    if len(rmp) != 279:
        raise ValueError("all 279 VNM RMP rows must remain individually retained")
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
                "journal": "positions",
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
                "event_date": None,
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
    positions = list(atomic)
    event_ids = {
        row["source_assertion"]["observation_id"]
        for row in migration["legacy_position_candidates"]
        if row["classification"] == "event_assertion_pending_evidence"
    }
    events = [
        dict(
            row,
            journal="events",
            event_date=row["date_lower"],
            linked_position_candidate_id=row["source_candidate_id"],
        )
        for row in atomic
        if row["source_candidate_id"] in event_ids
    ]
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
            "upper_original": "480000000 EUR",
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
            "lower_original": "15500000000 USD",
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


def build_snapshot(root: Path, *, input_git_sha: str) -> dict:
    """Build a deterministic, source-linked comparative handoff without aggregation."""
    root = Path(root)
    if len(input_git_sha) != 8 or any(
        char not in "0123456789abcdef" for char in input_git_sha
    ):
        raise ValueError(
            "input Git revision must be the pinned eight-character lowercase SHA"
        )
    country_results = {
        "ZAF": _zaf(root),
        "IDN": _idn(root),
        "VNM": _vnm(root),
        "SEN": _sen(root),
    }
    countries = {country: result[0] for country, result in country_results.items()}
    records = [
        record
        for country in ("ZAF", "IDN", "VNM", "SEN")
        for record in country_results[country][1]
    ]
    financial_points = sum(
        record["financial_bound_type"] != "unknown" for record in records
    )
    date_observations = sum(
        record["date_bound_type"] != "unknown" for record in records
    )
    unknown_money = sum(
        record["financial_bound_type"] == "unknown" for record in records
    )
    unknown_dates = sum(record["date_bound_type"] == "unknown" for record in records)
    conflicts = sum(
        record["conflict_status"] == "explicit_conflict" for record in records
    )
    _validate_records(records)
    atomic_observations, event_journal, position_journal = _atomic_journals(
        root, records
    )
    reconciliations = _reconciliations()
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "input_git_sha": input_git_sha,
        "scope": "approved bounded 0818-0821 artifacts; no external acquisition",
        "inputs": _input_hashes(root),
        "countries": countries,
        "records": records,
        "document_coverage": {
            "status": "bounded approved 0818-0821 source coverage; not a journal",
            "country_sources": {
                country: value["source_denominator"]
                for country, value in countries.items()
            },
        },
        "atomic_observations": atomic_observations,
        "event_journal": event_journal,
        "position_journal": position_journal,
        "reconciliations": reconciliations,
        "coverage_groups": [
            {
                "country": "VNM",
                "group_id": "vnm-rmp-inventory-positions",
                "count": 279,
                "record_materialization": "group_only_source_rows_not_available_in_this_worktree",
                "pedigree": {
                    "raw_source_id": "vnm-migration-0764",
                    "raw_document_sha256": countries["VNM"]["source_links"][0][
                        "sha256"
                    ],
                    "locator": "rmp_inventory_positions",
                    "extraction_method": "0820 staged migration summary",
                    "semantic_interpretation": "Inventory membership only; neither operation identity nor finance fact.",
                    "link_dedup_rule": "No individual row is inferred from the aggregate staging summary.",
                    "confidence": "source_only",
                },
            }
        ],
        "analysis_subsets": {
            "all_source_linked_records": {
                "count": len(records),
                "rule": "Every structured record with raw source/version and locator, including unknown money/date.",
            },
            "source_reported_money_positions": {
                "count": financial_points,
                "rule": "Record-level source amounts/bounds; not deduplicated and never a cross-country total.",
            },
            "source_reported_date_observations": {
                "count": date_observations,
                "rule": "Reported, registered, or estimated date values; not transition timing.",
            },
            "records_with_unknown_money": {
                "count": unknown_money,
                "rule": "Retained records whose bounded source artifact does not report a monetary value.",
            },
            "records_with_unknown_date": {
                "count": unknown_dates,
                "rule": "Retained records whose bounded source artifact does not report a date value.",
            },
            "explicit_conflicts": {
                "count": conflicts,
                "rule": "Source notes explicitly flag incompatible amount, perimeter, date, nature, or duplicate claims.",
            },
            "vnm_rmp_inventory_coverage": {
                "count": 279,
                "rule": "Coverage group retained separately because individual RMP rows are not materialized in this worktree.",
            },
        },
        "aggregation": {
            "financial_total": "not_computable",
            "transition_date_total": "not_computable",
            "point_quantities": "Record and coverage-group counts only, each with its stated denominator.",
            "interval_quantities": "Record-level lower bounds and year bounds are retained where source wording supports them; no pooled interval is calculated.",
            "reason": "Source positions have incompatible financial/date semantics and unresolved links/duplicates; unknown is retained, not zeroed, but no pooled finance or transition-time estimate is identified.",
        },
        "handoff": "0730 may compute descriptives on each named subset and report its coverage, missingness, conflict status, and semantic pedigree. It must not pool source amounts, interpret source dates as transition dates, or make causal/payment claims.",
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
    results = {
        "ZAF": _zaf(Path(root)),
        "IDN": _idn(Path(root)),
        "VNM": _vnm(Path(root)),
        "SEN": _sen(Path(root)),
    }
    expected = {country: result[0] for country, result in results.items()}
    expected_records = [
        record
        for country in ("ZAF", "IDN", "VNM", "SEN")
        for record in results[country][1]
    ]
    expected_atomic, expected_events, expected_positions = _atomic_journals(
        Path(root), expected_records
    )
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
    if snapshot.get("records") != expected_records:
        raise ValueError("structured record, uncertainty, or pedigree changed")
    _validate_records(snapshot["records"])
    if (
        snapshot.get("atomic_observations") != expected_atomic
        or snapshot.get("event_journal") != expected_events
        or snapshot.get("position_journal") != expected_positions
    ):
        raise ValueError(
            "atomic journal routing or exhaustive source retention changed"
        )
    if snapshot.get("reconciliations") != _reconciliations():
        raise ValueError("reconciliation adjudication changed")
    if snapshot.get("analysis_subsets", {}).get("all_source_linked_records", {}).get(
        "count"
    ) != len(expected_records):
        raise ValueError("descriptive record denominator changed")
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


def render_snapshot_archive(snapshot: dict) -> bytes:
    """Stable compressed representation keeps the full structured snapshot in Git."""
    return gzip.compress(render_snapshot(snapshot), mtime=0)


def build_manifest(snapshot: dict) -> dict:
    return {
        "schema_version": "jetp-0822-run-manifest/1",
        "input_git_sha": snapshot["input_git_sha"],
        "input_sha256": snapshot["inputs"],
        "snapshot_path": "docs/jetp-study/0822-comparative-snapshot.json.gz",
        "snapshot_sha256": snapshot["snapshot_sha256"],
        "reproduction": "Run this builder with --input-git-sha at the recorded revision; inputs are content-hashed and output rendering is deterministic.",
        "dvc_boundary": "0822 consumes the reviewed Git artifacts. Their source links retain DVC document hashes where applicable; this freeze does not materialize or reinterpret DVC bytes.",
    }


def write_outputs(
    root: Path, snapshot_path: Path, manifest_path: Path, *, input_git_sha: str
) -> None:
    snapshot = build_snapshot(root, input_git_sha=input_git_sha)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_bytes(render_snapshot_archive(snapshot))
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
        default=root / "docs/jetp-study/0822-comparative-snapshot.json.gz",
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
