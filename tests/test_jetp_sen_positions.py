"""Senegal plan and programme positions retain their original uncertainty."""


def test_programme_components_and_provisional_match_cannot_create_finance_total():
    """Overlapping plan needs are positions, not additive financed amounts."""
    from jetp._sen_positions import migrate_positions

    result = migrate_positions(
        plan_rows=[
            {
                "inventory_id": "quick-wins",
                "ordinal": 5,
                "source_wording": "Programme biodigesteurs",
                "amount_original": "20",
                "currency_original": "EUR_million",
                "locator": "Plan p. 33, QW5",
                "position_role": "programme",
            },
            {
                "inventory_id": "annex-2",
                "ordinal": 11,
                "source_wording": "Biodigesteurs — composante rurale",
                "amount_original": "12",
                "currency_original": "EUR_million",
                "locator": "Annex 2 p. 13, row 11",
                "position_role": "component_need",
            },
        ],
        provisional_matches=[
            {
                "plan_inventory_id": "annex-2:11",
                "legacy_project_id": "sen-project-annex-11",
                "rationale": "Similar wording only; programme/component boundary remains unresolved",
            }
        ],
    )

    assert [row["measure"] for row in result["plan_positions"]] == [
        "programme_need", "component_need"
    ]
    assert all(row["eligible_for_account"] is False for row in result["plan_positions"])
    assert result["provisional_matches"][0]["match_status"] == "provisional"
    assert result["provisional_matches"][0]["transition_date"] is None
    assert result["payment_candidates"] == []
    assert result["account_total"] is None
