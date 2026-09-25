"""Senegal plan and programme positions retain their original uncertainty."""

import hashlib
from pathlib import Path

import pytest

pytestmark = pytest.mark.wp_jetp

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


@pytest.mark.slow
def test_real_candidate_covers_pinned_inventories_and_keeps_mvp_legacy_owned():
    """Both saved plan editions remain distinct from every legacy finance assertion."""
    from jetp._compatibility import MVP_VIEWS, read_mvp_view
    from jetp.build_sen_positions import build_migration

    root = Path(__file__).resolve().parents[1]
    annexes = root / "data/jetp/documents/objects/dc/dcd4fd924f9e637d36beb192f509b7971b8b5dda0a76e3c17b799ba26ff43b21.pdf"
    plan = root / "data/jetp/documents/objects/97/97c36b242257462f024a934baee6bed3aa02fe0e4917f076d7b865701db65dca.pdf"
    if not annexes.exists() or not plan.exists():
        pytest.skip("DVC checkout required for Senegal inventory audit")
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest()
              for path in (root / "data/jetp").glob("*.csv")}

    result = build_migration(root)

    assert len(result["inventory_positions"]) == 49
    assert result["comparison"]["inventory_rows_by_source"] == {
        "sen-investment-plan-annexes-mirror": 38,
        "sen-investment-plan-l4-mirror": 11,
    }
    assert result["payment_candidates"] == []
    assert result["account_total"] is None
    assert result["writer_owner"] == result["publication_mode"] == "legacy"
    assert all(row["match_status"] == "provisional" for row in result["provisional_matches"])
    for view in MVP_VIEWS:
        assert result["mvp_views"][view] == read_mvp_view(root, view, supported_versions={"mvp/1"})
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest
               for path, digest in before.items())


@pytest.mark.parametrize("alias_kind", ["direct", "symlink", "hardlink"])
def test_writer_rejects_accepted_route_or_alias_before_build(tmp_path, monkeypatch, alias_kind):
    """No Senegal candidate path may replace an accepted route through an alias."""
    from jetp import build_sen_positions as builder

    accepted = tmp_path / "deliverables/jetp-observatory/data/SEN.json"
    accepted.parent.mkdir(parents=True)
    accepted.write_text('{"accepted": true}\n')
    output = accepted
    if alias_kind != "direct":
        output = tmp_path / "candidate.json"
        if alias_kind == "symlink":
            output.symlink_to(accepted)
        else:
            output.hardlink_to(accepted)
    monkeypatch.setattr(builder, "build_migration", lambda *args, **kwargs: pytest.fail("must not build"))
    with pytest.raises(ValueError):
        builder.write_migration(tmp_path, output)
    assert accepted.read_text() == '{"accepted": true}\n'
