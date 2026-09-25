"""Indonesian plan and approval observations retain their separate meanings."""

import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.wp_jetp

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
    # 0875 moved 65 project identities out of projects.csv; 0926 added 9
    # acquisition rows; 0970 added 4 reviewed project identities. 0878
    # retires this legacy sidecar.
    assert len(result["legacy_dispositions"]) == 2233
    assert result["comparison"]["inventory_rows_by_source"] == {
        "idn-cipp-2023-cpr-mirror": 437,
        "idn-jetp-progress-report-2025": 1142,
    }
    assert result["payment_candidates"] == []
    assert result["account_total"] is None
    assert result["writer_owner"] == result["publication_mode"] == "legacy"
    for view in MVP_VIEWS:
        assert result["mvp_views"][view] == read_mvp_view(root, view, supported_versions={"mvp/1"})


@pytest.mark.parametrize("alias_kind", ["direct", "symlink", "hardlink"])
def test_writer_rejects_accepted_targets_and_aliases_before_build(tmp_path, monkeypatch, alias_kind):
    """A candidate path cannot be used to replace a public/recovery artifact."""
    from jetp import build_idn_positions as builder

    accepted = tmp_path / "deliverables/jetp-observatory/data/IDN.json"
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


@pytest.mark.parametrize("alias_kind", ["direct", "symlink", "hardlink"])
def test_writer_refuses_malformed_prior_candidate_before_build(tmp_path, monkeypatch, alias_kind):
    """Markers alone never grant replacement authority to an existing file."""
    from jetp import build_idn_positions as builder

    target = tmp_path / "previous.json"
    target.write_text('{"country": "IDN", "schema_version": "country-migration/1"}\n')
    output = target
    if alias_kind != "direct":
        output = tmp_path / "candidate.json"
        if alias_kind == "symlink":
            output.symlink_to(target)
        else:
            output.hardlink_to(target)
    monkeypatch.setattr(builder, "build_migration", lambda *args, **kwargs: pytest.fail("must not build"))
    with pytest.raises(ValueError):
        builder.write_migration(tmp_path, output)
    assert target.read_text() == '{"country": "IDN", "schema_version": "country-migration/1"}\n'


@pytest.mark.parametrize("alias_kind", ["direct", "symlink", "hardlink"])
def test_writer_refuses_full_field_empty_lookalike_before_build(tmp_path, monkeypatch, alias_kind):
    """Every declared field must be populated before replacement is permitted."""
    from jetp import build_idn_positions as builder

    candidate = {
        "schema_version": "country-migration/1", "country": "IDN",
        "admission_status": "unadmitted_candidate", "writer_owner": "legacy",
        "publication_mode": "legacy", "inputs": {}, "recipe_inputs": {},
        "recovery_inputs": {}, "selected_sources": [],
        "inventory_positions": [{"inventory_id": "lookalike", "ordinal": 1}],
        "plan_positions": [{}], "approval_positions": [], "payment_candidates": [],
        "account_total": None,
        "legacy_dispositions": [{"disposition": "retained_legacy_authority"}],
        "legacy_evidence": [], "legacy_unresolved": [], "inventory_boundaries": [],
        "source_regime": [],
        "mvp_views": {view: {} for view in ("overview", "comparison", "ZAF", "IDN", "VNM", "SEN")},
        "comparison": {},
    }
    target = tmp_path / "previous.json"
    target.write_text(builder.encoded(candidate).decode())
    output = target
    if alias_kind != "direct":
        output = tmp_path / "candidate.json"
        if alias_kind == "symlink":
            output.symlink_to(target)
        else:
            output.hardlink_to(target)
    monkeypatch.setattr(builder, "build_migration", lambda *args, **kwargs: pytest.fail("must not build"))
    with pytest.raises(ValueError):
        builder.write_migration(tmp_path, output)
    assert target.read_bytes() == builder.encoded(candidate)


@pytest.mark.parametrize("alias_kind", ["direct", "symlink", "hardlink"])
def test_writer_refuses_real_candidate_without_approval_positions_before_build(
        tmp_path, monkeypatch, alias_kind):
    """The real IDN contract requires a populated structured approval ledger."""
    from jetp import build_idn_positions as builder

    root = Path(__file__).resolve().parents[1]
    source = root / "data/jetp/releases/idn-migration-0766.json"
    if not source.exists():
        pytest.skip("DVC checkout required for complete-candidate recognition audit")
    candidate = copy.deepcopy(json.loads(source.read_text()))
    candidate["approval_positions"] = []
    target = tmp_path / "previous.json"
    target.write_bytes(builder.encoded(candidate))
    output = target
    if alias_kind != "direct":
        output = tmp_path / "candidate.json"
        if alias_kind == "symlink":
            output.symlink_to(target)
        else:
            output.hardlink_to(target)
    monkeypatch.setattr(builder, "build_migration", lambda *args, **kwargs: pytest.fail("must not build"))
    with pytest.raises(ValueError):
        builder.write_migration(tmp_path, output)
    assert target.read_bytes() == builder.encoded(candidate)
