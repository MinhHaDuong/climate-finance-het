# WARNING: AI-generated, not human-reviewed
"""Controlled vocabularies for the JETP documentary ledger."""

from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "jetp_tracking.yaml"


def _load_contract() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


CONTRACT = _load_contract()
COUNTRIES = frozenset(CONTRACT["countries"])
FINANCIAL_STATUSES = frozenset(CONTRACT["financial_statuses"])
IMPLEMENTATION_STATUSES = frozenset(CONTRACT["implementation_statuses"])
SCOPES = frozenset(CONTRACT["scopes"])
SOURCE_TYPES = frozenset(CONTRACT["source_types"])
AUTHORITY_CATEGORIES = frozenset(CONTRACT["authority_categories"])


def validate_event_record(record: dict[str, str]) -> None:
    """Validate the fields that prevent financial-event double counting.

    Parameters
    ----------
    record
        A candidate financial event represented as string-valued fields.

    Raises
    ------
    ValueError
        If a controlled value or original-currency amount is invalid.

    """
    country = record.get("country", "")
    if country not in COUNTRIES:
        raise ValueError(f"invalid country: {country!r}")
    scope = record.get("scope", "")
    if scope not in SCOPES:
        raise ValueError(f"invalid scope: {scope!r}")
    status = record.get("financial_status", "")
    if status not in FINANCIAL_STATUSES:
        raise ValueError(f"invalid financial_status: {status!r}")
    amount = record.get("amount_original", "")
    currency = record.get("currency_original", "")
    if bool(amount) != bool(currency):
        raise ValueError("amount_original and currency_original must travel together")
    if amount:
        try:
            if Decimal(amount) < 0:
                raise ValueError("amount_original must be non-negative")
        except InvalidOperation as exc:
            raise ValueError(f"invalid amount_original: {amount!r}") from exc


def validate_implementation_event_record(record: dict[str, str]) -> None:
    """Validate a non-financial project delivery or closure observation."""
    country = record.get("country", "")
    if country not in COUNTRIES:
        raise ValueError(f"invalid country: {country!r}")
    status = record.get("implementation_status", "")
    if status not in IMPLEMENTATION_STATUSES:
        raise ValueError(f"invalid implementation_status: {status!r}")
    capacity = record.get("capacity_mw", "")
    if capacity:
        try:
            if Decimal(capacity) < 0:
                raise ValueError("capacity_mw must be non-negative")
        except InvalidOperation as exc:
            raise ValueError(f"invalid capacity_mw: {capacity!r}") from exc
