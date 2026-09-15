"""Metadata contracts for the pre-outcome causal-feasibility screen.

This module validates provenance and comparison admissibility only. It must not
derive approval values, country contrasts, or treatment effects.
"""

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any


OBSERVATION_REQUIRED_FIELDS = (
    "country",
    "quarter",
    "source_version",
    "source_locator",
    "approval_date_semantics",
    "currency_basis",
    "concessionality_rule",
    "instrument_rule",
    "missingness_state",
    "denominator_state",
    "lost_visibility_state",
)


def _require_nonempty(row: Mapping[str, Any], field: str) -> None:
    """Reject a record whose required metadata field is absent or blank."""
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")


def validate_country_quarter_observations(
    observations: Sequence[Mapping[str, Any]],
) -> None:
    """Validate that each prospective observation preserves source semantics."""
    for observation in observations:
        for field in OBSERVATION_REQUIRED_FIELDS:
            _require_nonempty(observation, field)


def load_country_quarter_observations(path: Path) -> list[dict[str, Any]]:
    """Load and validate a prospective observation list before it can be used."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(
        isinstance(observation, dict) for observation in payload
    ):
        raise ValueError("observation file must contain a JSON list of objects")
    validate_country_quarter_observations(payload)
    return payload


def validate_comparison_countries(countries: Sequence[Mapping[str, Any]]) -> None:
    """Reject an untreated label when negotiation exposure has not been resolved."""
    for country in countries:
        _require_nonempty(country, "country")
        _require_nonempty(country, "comparison_status")
        negotiation_exposure = country.get("negotiation_exposure")
        if country["comparison_status"] == "untreated" and negotiation_exposure in {
            None,
            "",
            "unknown",
        }:
            raise ValueError(
                "negotiation_exposure must be resolved before a country is untreated"
            )
