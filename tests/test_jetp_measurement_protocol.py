"""Red tests for the non-causal comparative JETP measurement protocol."""

import pytest

from jetp._measurement_protocol import ProtocolError, validate_protocol


def test_protocol_rejects_mixed_lifecycle_states_missing_as_zero_and_causal_claim():
    protocol = {
        "claim_class": "causal effect",
        "lifecycle_states": ["pledge", "signature"],
        "aggregate": ["pledge", "signature"],
        "missingness_policy": "zero",
    }

    with pytest.raises(ProtocolError, match="non-causal|lifecycle|missing"):
        validate_protocol(protocol)
