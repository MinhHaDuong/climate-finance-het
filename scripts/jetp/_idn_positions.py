"""Keep Indonesian plan and approval observations as distinct candidate positions.

Planning estimates, later approvals and disbursements have different evidentiary
meanings.  This narrow adapter deliberately creates no payment or account record:
those require occurrence and coverage reconciliation in ticket 0768.
"""

from jetp._source_crosswalk import _identity


def _required(row: dict, fields: tuple[str, ...], kind: str) -> None:
    missing = [field for field in fields if not row.get(field)]
    if missing:
        raise ValueError(f"{kind} is missing required fields: {', '.join(missing)}")


def migrate_positions(*, plan_rows: list[dict], approval_rows: list[dict]) -> dict:
    """Stage source rows without using names or amounts as identity/payment joins."""
    plans = []
    for row in plan_rows:
        _required(row, ("plan_project_id", "project_name", "source_wording", "locator"), "Plan row")
        plans.append({
            "record_kind": "position_candidate",
            "record_id": _identity("idn-plan-position", row),
            "source_row": dict(row),
            "measure": "planned_investment",
            "amount_original": row.get("estimated_investment_usd_mn"),
            "currency_original": "USD_million" if row.get("estimated_investment_usd_mn") else None,
            "component_relation": "unresolved",
            "transition_date": None,
            "payment_amount": None,
            "eligible_for_account": False,
            "reason": "Plan inventory membership and estimate retained without approval, payment or identity inference",
        })
    approvals = []
    for row in approval_rows:
        _required(row, ("event_id", "project_id", "source_wording", "amount_original", "currency_original", "event_date"), "Approval row")
        approvals.append({
            "record_kind": "position_candidate",
            "record_id": _identity("idn-approval-position", row),
            "source_row": dict(row),
            "measure": "approved_finance",
            "amount_original": row["amount_original"],
            "currency_original": row["currency_original"],
            "approval_date": row["event_date"],
            "component_relation": "component_A" if "component a" in row["source_wording"].lower() else "unresolved",
            "transition_date": None,
            "payment_amount": None,
            "eligible_for_account": False,
            "reason": "Approval evidence is retained separately from plan inventory and does not establish a payment",
        })
    if len({row["record_id"] for row in [*plans, *approvals]}) != len(plans) + len(approvals):
        raise ValueError("Duplicate Indonesian position identity")
    return {"plan_positions": plans, "approval_positions": approvals,
            "payment_candidates": [], "account_total": None}
