"""Indonesian plan and approval observations retain their separate meanings."""

from pathlib import Path

import pytest


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


@pytest.mark.slow
def test_real_candidate_covers_both_pinned_plan_inventories_and_legacy_rows():
    """The sidecar retains every input while the legacy MVP remains authoritative."""
    root = Path(__file__).resolve().parents[1]
    cipp = root / "data/jetp/documents/objects/74/747283facac512780ad757313c493d1080c39705824e72c4b231e87ecb4102b5.pdf"
    if not cipp.exists():
        pytest.skip("DVC checkout required for Indonesian inventory audit")
    from jetp._compatibility import MVP_VIEWS, read_mvp_view
    from jetp.build_idn_positions import build_migration

    result = build_migration(root)
    assert len(result["inventory_positions"]) == 1579
    assert len(result["plan_positions"]) == 1579
    assert len(result["approval_positions"]) == 62
    assert len(result["legacy_dispositions"]) == 2285
    assert result["comparison"]["inventory_rows_by_source"] == {
        "idn-cipp-2023-cpr-mirror": 437,
        "idn-jetp-progress-report-2025": 1142,
    }
    assert result["payment_candidates"] == []
    assert result["account_total"] is None
    assert result["writer_owner"] == result["publication_mode"] == "legacy"
    for view in MVP_VIEWS:
        assert result["mvp_views"][view] == read_mvp_view(root, view, supported_versions={"mvp/1"})
