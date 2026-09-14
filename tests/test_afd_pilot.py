"""Acceptance contracts for the AFD historical observation pilot."""

from build_afd_pilot import payment_observation, reconcile


def test_cma123501_disappearance_is_not_an_outcome():
    row = {
        "id_concours": "CMA123501",
        "date_de_1er_versement_concours": None,
        "etat_du_projet": "Exécution",
        "date_de_signature_de_convention": "2019-06-28",
    }
    result = reconcile(row, None)
    assert result["observation_status"] == "lost_visibility"
    assert result["outcome"] == "unknown"
    assert result["last_observed_stage"] == "signature"
    assert result["last_observed_snapshot"] == "legacy-retrieved-2026-09-14"


def test_exact_payment_is_preserved_and_no_uncovered_interval():
    result = payment_observation("2022-08-30", ["2022-12-31"])
    assert result["date"] == "2022-08-30"
    assert result["precision"] == "day"
    missing = payment_observation(None, ["2022-12-31"])
    assert missing["date"] is None
    assert missing["precision"] == "unknown"
    assert missing["interval"] is None


def test_value_date_never_imputes_award_and_parent_never_joins():
    row = {"id_concours": "CMA123501", "date_d_octroi": None}
    result = reconcile(
        row, {"code_concours_simple": "CMA123502", "value_date": "2020-01-01"}
    )
    assert result["award"] is None
    assert result["observation_status"] == "lost_visibility"


def test_all_193_legacy_exact_payment_dates_survive():
    import json
    from pathlib import Path

    comparisons = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "docs/jetp-audits/0735/round3/afd/legacy-xml-comparisons.json"
        ).read_text()
    )
    paid = [r for r in comparisons if r["legacy_first_payment"]]
    assert len(paid) == 193
    for row in paid:
        result = payment_observation(
            row["legacy_first_payment"], [row["earliest_reported_disbursement"]]
        )
        assert result["date"] == row["legacy_first_payment"]
        assert result["date"] != row["earliest_reported_disbursement"]


def test_amounts_are_not_normalized_as_dates():
    import xml.etree.ElementTree as ET
    from build_afd_pilot import build_observations

    activity = ET.fromstring("""<iati-activity><default-finance-type code="110"/>
      <sector vocabulary="1" code="23010"/><transaction><transaction-type code="3"/>
      <transaction-date iso-date="2023-12-31"/><value value-date="2023-12-31">-12</value>
      </transaction></iati-activity>""")
    units, events = build_observations(
        {},
        {"X": {"iati_identifier": "FR-3-P", "recipient_country_narrative": "MAROC"}},
        {"X": (activity, "xml", "MA")},
    )
    amount = next(r for r in events if r["raw_field"] == "value")
    assert amount["raw_value"] == "-12"
    assert amount["normalized_date"] is None
    assert units[0]["xml_sector_raw"] == "1:23010"
