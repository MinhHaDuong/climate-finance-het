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


def validate_protocol(protocol: dict) -> None:
    """Reject causal claims, lifecycle mixtures, and missing-as-zero rules."""
    if protocol.get("claim_class") != "descriptive_comparison":
        raise ProtocolError("protocol must be non-causal descriptive comparison")
    states = protocol.get("lifecycle_states")
    if not isinstance(states, list) or not states or not set(states) <= _PERMITTED_STATES:
        raise ProtocolError("protocol needs permitted lifecycle states")
    aggregate = protocol.get("aggregate", [])
    if aggregate and (not isinstance(aggregate, list) or len(set(aggregate)) != 1
                      or not set(aggregate) <= set(states)):
        raise ProtocolError("aggregate must use one declared lifecycle state")
    if protocol.get("missingness_policy") != "explicit":
        raise ProtocolError("missingness must remain explicit, not zero")
