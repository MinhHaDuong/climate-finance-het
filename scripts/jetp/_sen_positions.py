"""Keep Senegal plan needs and tentative joins outside the finance account.

The Senegal plan presents programme envelopes, component needs and received
proposals in overlapping inventories.  They are all source positions.  A
similar title, amount, or provisional link cannot turn any of them into an
approval, payment, or additive total.
"""

from jetp._source_crosswalk import _identity


def _require(row: dict, fields: tuple[str, ...], kind: str) -> None:
    missing = [field for field in fields if not row.get(field)]
    if missing:
        raise ValueError(f"{kind} is missing required fields: {', '.join(missing)}")


def migrate_positions(*, plan_rows: list[dict], provisional_matches: list[dict]) -> dict:
    """Stage source positions without calculating finance or confirming identity."""
    positions = []
    valid_ids = set()
    for row in plan_rows:
        _require(row, ("inventory_id", "ordinal", "source_wording", "locator", "position_role"), "Plan row")
        position_id = f"{row['inventory_id']}:{row['ordinal']}"
        if position_id in valid_ids:
            raise ValueError(f"Duplicate Senegal plan position {position_id}")
        valid_ids.add(position_id)
        role = row["position_role"]
        if role not in {"programme", "component_need", "received_proposal", "quick_win"}:
            raise ValueError(f"Unsupported Senegal plan position role: {role}")
        measure = {"programme": "programme_need", "component_need": "component_need",
                   "received_proposal": "received_proposal", "quick_win": "quick_win_need"}[role]
        positions.append({
            "record_kind": "position_candidate",
            "record_id": _identity("sen-plan-position", row),
            "plan_inventory_id": position_id,
            "source_row": dict(row),
            "measure": measure,
            "amount_original": row.get("amount_original"),
            "currency_original": row.get("currency_original"),
            "transition_date": None,
            "payment_amount": None,
            "eligible_for_account": False,
            "reason": "Plan position retained without financing, payment, or identity inference",
        })
    matches = []
    for row in provisional_matches:
        _require(row, ("plan_inventory_id", "legacy_project_id", "rationale"), "Provisional match")
        if row["plan_inventory_id"] not in valid_ids:
            raise ValueError("Provisional match refers to absent Senegal plan position")
        matches.append({**row, "record_kind": "provisional_identity_match",
                        "record_id": _identity("sen-provisional-match", row),
                        "match_status": "provisional", "transition_date": None,
                        "payment_amount": None, "eligible_for_account": False})
    if len({row["record_id"] for row in [*positions, *matches]}) != len(positions) + len(matches):
        raise ValueError("Duplicate Senegal candidate identity")
    return {"plan_positions": positions, "provisional_matches": matches,
            "payment_candidates": [], "account_total": None}
