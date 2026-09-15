"""Contracts for the pre-outcome JETP causal-feasibility screen."""

import json

import pytest

from jetp._causal_feasibility import (
    load_country_quarter_observations,
    validate_comparison_countries,
    validate_country_quarter_observations,
)


def valid_observation() -> dict[str, str | None]:
    return {
        "country": "Indonesia",
        "quarter": "2023-Q4",
        "source_version": "afd-export-2024-05-27",
        "source_locator": "financing/CMA123500",
        "approval_date_semantics": "reported award date",
        "currency_basis": "EUR nominal",
        "concessionality_rule": "official concessional financing field",
        "instrument_rule": "grant",
        "missingness_state": "observed",
        "denominator_state": "unknown",
        "lost_visibility_state": "not_assessed",
    }


@pytest.mark.parametrize(
    "field",
    [
        "source_version",
        "source_locator",
        "approval_date_semantics",
        "currency_basis",
        "concessionality_rule",
        "instrument_rule",
        "missingness_state",
        "denominator_state",
        "lost_visibility_state",
    ],
)
def test_observation_contract_rejects_missing_provenance_or_coverage_state(field):
    observation = valid_observation()
    observation[field] = None

    with pytest.raises(ValueError, match=field):
        validate_country_quarter_observations([observation])


def test_comparison_contract_rejects_untreated_country_with_unknown_negotiation():
    countries = [
        {
            "country": "India",
            "comparison_status": "untreated",
            "negotiation_exposure": "unknown",
        }
    ]

    with pytest.raises(ValueError, match="negotiation_exposure"):
        validate_comparison_countries(countries)


def test_observation_loader_validates_records_before_returning_them(tmp_path):
    path = tmp_path / "observations.json"
    observation = valid_observation()
    observation["source_version"] = None
    path.write_text(json.dumps([observation]), encoding="utf-8")

    with pytest.raises(ValueError, match="source_version"):
        load_country_quarter_observations(path)
