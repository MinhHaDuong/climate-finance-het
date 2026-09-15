"""Build the small, transparent transformations for the 0816 diagnostic."""

import argparse
import csv
import json
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path


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
        existing = contributions.get(key)
        if existing is None:
            contributions[key] = item
        elif any(
            existing.get(field) != item.get(field)
            for field in ("funder", "ownership", "instrument", "amount_original", "currency_original")
        ):
            raise ValueError(f"conflicting contribution evidence for {key!r}")

    milestone_by_operation: dict[str, dict[str, str]] = {}
    for item in milestones:
        operation_id = item["operation_id"]
        existing = milestone_by_operation.get(operation_id)
        if existing is None:
            milestone_by_operation[item["operation_id"]] = item
        elif any(
            existing.get(field) != item.get(field)
            for field in ("milestone", "event_date", "publication_date", "date_precision")
        ):
            raise ValueError(f"conflicting milestone evidence for {operation_id!r}")

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


def validate_date_roles(matrix: Iterable[dict[str, str]]) -> None:
    """Reject administrative dates presented as operational history.

    A register timestamp, report cutoff or publication timestamp can describe
    when evidence was observed, but cannot supply either end of a pre/post
    event sequence.  The diagnostic only accepts a sequence made from two
    documented event dates.
    """
    for row in matrix:
        roles = {row.get("pre_date_role", ""), row.get("post_date_role", "")}
        has_history_text = bool(row.get("pre_jetp_milestone") or row.get("post_jetp_milestone"))
        administrative = roles & {"registered", "observed_state", "publication"}
        if has_history_text and administrative:
            raise ValueError("registered, observed-state, or publication date cannot be history evidence")
        if row.get("supports_C_sequence") == "yes":
            if not row.get("pre_jetp_milestone") or not row.get("post_jetp_milestone"):
                raise ValueError("history sequence needs pre- and post-JETP milestones")
            if roles != {"event"}:
                raise ValueError("history sequence needs two documented event dates")


def summarize_diagnostic(matrix: Iterable[dict[str, str]]) -> dict[str, int]:
    """Derive, rather than hand-type, the diagnostic denominators from rows."""
    rows = list(matrix)
    validate_date_roles(rows)
    return {
        "A": sum(row.get("supports_A") == "yes" for row in rows),
        "B_strict": sum(row.get("supports_B_strict") == "yes" for row in rows),
        "C_sequence": sum(row.get("supports_C_sequence") == "yes" for row in rows),
        "A_B_C": sum(row.get("supports_A_B_C") == "yes" for row in rows),
    }


def write_summary(matrix_path: Path, output_path: Path) -> None:
    """Write the frozen denominator summary directly from the diagnostic rows."""
    with matrix_path.open(encoding="utf-8", newline="") as stream:
        summary = summarize_diagnostic(csv.DictReader(stream))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_summary(args.matrix, args.output)


if __name__ == "__main__":
    main()
