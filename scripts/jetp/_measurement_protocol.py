"""Fail-closed validation for the comparative, non-causal JETP study protocol."""

from datetime import datetime


class ProtocolError(ValueError):
    """The proposed study protocol permits an unsupported comparison or claim."""


_PERMITTED_STATES = {
    "pledge",
    "allocation",
    "approval",
    "signature",
    "disbursement",
    "implementation",
}
_REQUIRED_FIELDS = {
    "study_id",
    "countries",
    "unit",
    "lifecycle_states",
    "aggregate",
    "missingness_policy",
    "evidence_cutoff",
    "denominator_policy",
    "money_policy",
    "date_policy",
    "coverage_states",
    "permitted_claim",
    "prohibited_claims",
    "lifecycle_definitions",
    "comparison_rules",
    "source_census_handoff",
    "question",
    "jetp_attribution_rule",
    "denominator_contract",
    "cutoff_semantics",
}


def _validate_identity(protocol: dict) -> None:
    """Validate the study frame and its frozen evidence date."""
    if protocol.get("claim_class") != "descriptive_comparison":
        raise ProtocolError("protocol must be non-causal descriptive comparison")
    missing_fields = _REQUIRED_FIELDS - set(protocol)
    if missing_fields:
        raise ProtocolError(f"protocol lacks required fields: {sorted(missing_fields)}")
    if protocol["unit"] != "country-source-lifecycle-state observation":
        raise ProtocolError("protocol needs a declared measurement unit")
    if protocol["countries"] != ["ZAF", "IDN", "VNM", "SEN"]:
        raise ProtocolError("protocol needs the frozen four JETP countries")
    try:
        datetime.fromisoformat(protocol["evidence_cutoff"].replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        raise ProtocolError("protocol needs a frozen evidence cutoff")


def _validate_lifecycle(protocol: dict) -> list[str]:
    """Validate lifecycle states and return their declared order."""
    states = protocol.get("lifecycle_states")
    if (
        not isinstance(states, list)
        or not states
        or not set(states) <= _PERMITTED_STATES
    ):
        raise ProtocolError("protocol needs permitted lifecycle states")
    aggregate = protocol.get("aggregate", [])
    if aggregate and (
        not isinstance(aggregate, list)
        or len(set(aggregate)) != 1
        or not set(aggregate) <= set(states)
    ):
        raise ProtocolError("aggregate must use one declared lifecycle state")
    if protocol.get("missingness_policy") != "explicit":
        raise ProtocolError("missingness must remain explicit, not zero")
    return states


def _validate_claim_boundaries(protocol: dict, states: list[str]) -> None:
    """Validate the claims, definitions, and non-additivity rules."""
    if protocol["permitted_claim"] != "traceability_and_coverage_comparison":
        raise ProtocolError("protocol has an unsupported permitted claim")
    prohibited = set(protocol["prohibited_claims"])
    required_prohibitions = {
        "causal_effect",
        "additionality",
        "total_investment",
        "physical_delivery",
    }
    if not required_prohibitions <= prohibited:
        raise ProtocolError("protocol needs every prohibited claim category")
    definitions = protocol["lifecycle_definitions"]
    if set(definitions) != set(states) or any(
        not definitions[state] for state in states
    ):
        raise ProtocolError(
            "protocol needs evidence thresholds for every lifecycle state"
        )
    required_rules = {
        "no_cross_state_aggregation",
        "no_cumulative_flow_mix",
        "no_inferred_transition",
        "deduplicate_same_financing",
        "no_programme_component_double_count",
        "select_one_cumulative_snapshot",
    }
    if not required_rules <= set(protocol["comparison_rules"]):
        raise ProtocolError("protocol needs non-additivity comparison rules")


def _validate_handoff(protocol: dict) -> None:
    """Validate the finite source-census handoff."""
    handoff = protocol["source_census_handoff"]
    required_dispositions = {
        "admitted",
        "duplicate",
        "excluded",
        "unavailable",
        "lost_visibility",
    }
    if (
        handoff.get("finite_universe") is not True
        or not required_dispositions <= set(handoff.get("required_dispositions", []))
        or not handoff.get("window_rule")
    ):
        raise ProtocolError("protocol needs a finite source census handoff")


def _validate_observation_contract(protocol: dict, states: list[str]) -> None:
    """Validate denominators, attribution, dates, and coverage states."""
    if set(protocol["denominator_contract"]) != set(states) or any(
        not protocol["denominator_contract"][state] for state in states
    ):
        raise ProtocolError("protocol needs a denominator for every lifecycle state")
    if not protocol["jetp_attribution_rule"].get("explicit_source_link_required"):
        raise ProtocolError("protocol needs an explicit JETP attribution rule")
    cutoff = protocol["cutoff_semantics"]
    if not all(
        cutoff.get(key)
        for key in {"event", "publication", "retrieval", "undated", "revision"}
    ):
        raise ProtocolError("protocol needs cutoff semantics for all date roles")
    if not set(protocol["coverage_states"]) >= {
        "observed",
        "unavailable",
        "lost_visibility",
        "excluded",
    }:
        raise ProtocolError("protocol needs explicit coverage states")


def validate_protocol(protocol: dict) -> None:
    """Reject causal claims, lifecycle mixtures, and missing-as-zero rules."""
    _validate_identity(protocol)
    states = _validate_lifecycle(protocol)
    _validate_claim_boundaries(protocol, states)
    _validate_handoff(protocol)
    _validate_observation_contract(protocol, states)
