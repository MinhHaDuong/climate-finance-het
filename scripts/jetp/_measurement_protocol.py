"""Fail-closed validation for the comparative, non-causal JETP study protocol."""


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
}


def validate_protocol(protocol: dict) -> None:
    """Reject causal claims, lifecycle mixtures, and missing-as-zero rules."""
    if protocol.get("claim_class") != "descriptive_comparison":
        raise ProtocolError("protocol must be non-causal descriptive comparison")
    missing_fields = _REQUIRED_FIELDS - set(protocol)
    if missing_fields:
        raise ProtocolError(f"protocol lacks required fields: {sorted(missing_fields)}")
    if protocol["unit"] != "country-source-lifecycle-state observation":
        raise ProtocolError("protocol needs a declared measurement unit")
    if not isinstance(protocol["evidence_cutoff"], str) or not protocol["evidence_cutoff"].endswith("Z"):
        raise ProtocolError("protocol needs a frozen evidence cutoff")
    states = protocol.get("lifecycle_states")
    if not isinstance(states, list) or not states or not set(states) <= _PERMITTED_STATES:
        raise ProtocolError("protocol needs permitted lifecycle states")
    aggregate = protocol.get("aggregate", [])
    if aggregate and (not isinstance(aggregate, list) or len(set(aggregate)) != 1
                      or not set(aggregate) <= set(states)):
        raise ProtocolError("aggregate must use one declared lifecycle state")
    if protocol.get("missingness_policy") != "explicit":
        raise ProtocolError("missingness must remain explicit, not zero")
