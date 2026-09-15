"""Small, transparent transformations for the 0816 documentary diagnostic."""

from collections import defaultdict
from collections.abc import Iterable


def documentary_rows(
    *,
    operations: Iterable[dict[str, str]],
    finance: Iterable[dict[str, str]],
    milestones: Iterable[dict[str, str]],
) -> list[dict[str, str]]:
    """Return one diagnostic row per operation without fabricating allocation or dates.

    ``contribution_id`` is the accounting identity. Several sources supporting it
    are evidence, not several contributions. A milestone's publication date is
    deliberately retained in a separate field from its event date.
    """
    operation_rows = {row["operation_id"]: row for row in operations}
    contributions: dict[tuple[str, str], dict[str, str]] = {}
    for item in finance:
        key = (item["operation_id"], item["contribution_id"])
        contributions.setdefault(key, item)

    milestone_by_operation: dict[str, dict[str, str]] = {}
    for item in milestones:
        existing = milestone_by_operation.get(item["operation_id"])
        if existing is None or (not existing.get("event_date") and item.get("event_date")):
            milestone_by_operation[item["operation_id"]] = item

    by_operation: dict[str, list[dict[str, str]]] = defaultdict(list)
    for (operation_id, _), item in contributions.items():
        by_operation[operation_id].append(item)

    rows: list[dict[str, str]] = []
    for operation_id, operation in operation_rows.items():
        items = by_operation.get(operation_id, [])
        mixed = [item for item in items if item.get("ownership") == "mixed_unallocated"]
        private = [item for item in items if item.get("ownership") == "private"]
        format_amount = lambda item: " ".join(
            filter(None, (item.get("amount_original"), item.get("currency_original")))
        )
        milestone = milestone_by_operation.get(operation_id, {})
        rows.append({
            "operation_id": operation_id,
            "country": operation["country"],
            "function": operation.get("function", ""),
            "social_objective": operation.get("social_objective", ""),
            "beneficiaries": operation.get("beneficiaries", ""),
            "finance_contribution_count": str(len(items)),
            "private_amount_original": "; ".join(format_amount(item) for item in private),
            "mixed_unallocated_amount_original": "; ".join(format_amount(item) for item in mixed),
            "event_date": milestone.get("event_date", ""),
            "publication_date": milestone.get("publication_date", ""),
            "date_precision": milestone.get("date_precision", "unknown"),
        })
    return rows


def validate_0816_acceptance(protocol: dict, matrix: Iterable[dict[str, str]]) -> None:
    """Fail closed on the two claims that would invalidate this diagnostic.

    This is deliberately not a general protocol validator: it protects the
    fixed 0816 diagnostic from causal scope creep and from converting an absent
    financing observation into a numerical zero.
    """
    comparisons = protocol.get("permitted_comparisons", [])
    if any("causal" in item.lower() for item in comparisons):
        raise ValueError("causal comparison is prohibited for 0816")
    for row in matrix:
        if row.get("finance_observation", "").strip() == "0":
            raise ValueError("zero-filled missing finance is prohibited for 0816")
