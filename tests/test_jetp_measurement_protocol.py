"""Tests for the non-causal comparative JETP measurement protocol."""

import json
from pathlib import Path

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


def test_frozen_four_country_protocol_is_a_valid_descriptive_measurement_design():
    path = Path("docs/jetp-study/0816-comparative-measurement-protocol.json")

    protocol = json.loads(path.read_text(encoding="utf-8"))

    validate_protocol(protocol)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("aggregate", ["pledge", "signature"], "aggregate"),
        ("missingness_policy", "zero", "missingness"),
        ("evidence_cutoff", "to be decided", "cutoff"),
        ("unit", None, "unit"),
        ("countries", ["USA"], "countries"),
        ("permitted_claim", "JETP caused additional investment", "claim"),
    ],
)
def test_protocol_rejects_each_unsupported_measurement_rule(field, value, message):
    protocol = json.loads(
        Path("docs/jetp-study/0816-comparative-measurement-protocol.json").read_text()
    )
    protocol[field] = value

    with pytest.raises(ProtocolError, match=message):
        validate_protocol(protocol)
