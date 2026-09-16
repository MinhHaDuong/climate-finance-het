"""Source-specific adapters for the JETP 0822 comparative freeze."""

import csv
import hashlib
import json
import re
from collections import Counter
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
    "data/jetp/releases/vnm-migration-0764.json",
)
SCHEMA_VERSION = "jetp-0822-comparative-snapshot/2"
DVC_MIGRATION_PATH = "data/jetp/releases/vnm-migration-0764.json"
DVC_MIGRATION_POINTER = f"{DVC_MIGRATION_PATH}.dvc"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _document(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _input_hashes(root: Path) -> dict[str, dict[str, str]]:
    return {name: {"sha256": _sha256(root / name)} for name in INPUTS}


def _dvc_migration_input(root: Path) -> dict[str, str | int]:
    """Validate the tracked DVC pointer and the materialized migration bytes."""
    pointer_path = root / DVC_MIGRATION_POINTER
    migration_path = root / DVC_MIGRATION_PATH
    pointer = pointer_path.read_text(encoding="utf-8")
    md5 = re.search(r"^\s*- md5: ([0-9a-f]{32})$", pointer, re.MULTILINE)
    size = re.search(r"^\s+size: (\d+)$", pointer, re.MULTILINE)
    if not md5 or not size or "hash: md5" not in pointer:
        raise ValueError("VNM DVC migration pointer is malformed")
    if not migration_path.is_file():
        raise ValueError("VNM DVC migration input is not materialized; run dvc checkout")
    actual_md5 = hashlib.md5(migration_path.read_bytes()).hexdigest()
    if actual_md5 != md5.group(1) or migration_path.stat().st_size != int(size.group(1)):
        raise ValueError("VNM DVC migration input does not match its pinned pointer")
    return {
        "pointer_path": DVC_MIGRATION_POINTER,
        "hash": "md5",
        "md5": actual_md5,
        "size": migration_path.stat().st_size,
        "sha256": _sha256(migration_path),
    }


def _numeric(value: str | None) -> int | float | None:
    """Keep source wording separately while making reported numeric bounds computable."""
    if value is None or not value.strip() or not re.fullmatch(r"-?\d+(?:\.\d+)?", value):
        return None
    return int(value) if "." not in value else float(value)


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
    amount = _numeric(financial_amount_original)
    financial_lower = (
        amount
        if financial_bound_type
        in {"point_as_reported", "point_as_reported_millions", "lower_bound"}
        else None
    )
    financial_upper = (
        amount
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
                    "lower_bound"
                    if lower_bound and _numeric(row["amount_original"])
                    else "point_as_reported"
                    if _numeric(row["amount_original"])
                    else "unknown"
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

