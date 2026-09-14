"""Indonesian plan and approval observations retain their separate meanings."""


def test_plan_and_later_approval_component_do_not_become_payment_or_double_count():
    """A shared programme name never turns two source positions into a disbursement."""
    from jetp._idn_positions import migrate_positions

    result = migrate_positions(
        plan_rows=[{
            "plan_project_id": "idn-cipp-solar-003",
            "project_name": "Harapan programme",
            "source_wording": "Harapan solar programme (component A)",
            "estimated_investment_usd_mn": "100",
            "locator": "CIPP appendix 10.4, row 3",
        }],
        approval_rows=[{
            "event_id": "idn-approved-harapan-a",
            "project_id": "idn-pipe-harapan",
            "source_wording": "Harapan programme: component A approved",
            "amount_original": "100",
            "currency_original": "USD",
            "event_date": "2025-03-01",
        }],
    )

    assert len(result["plan_positions"]) == 1
    assert len(result["approval_positions"]) == 1
    assert result["plan_positions"][0]["measure"] == "planned_investment"
    assert result["approval_positions"][0]["measure"] == "approved_finance"
    assert result["plan_positions"][0]["component_relation"] == "unresolved"
    assert result["approval_positions"][0]["component_relation"] == "component_A"
    assert result["payment_candidates"] == []
    assert result["account_total"] is None
