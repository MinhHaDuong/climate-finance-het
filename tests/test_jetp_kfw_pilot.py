"""Acceptance boundaries for the BMZ/KfW documentary pilot."""

from xml.etree import ElementTree as ET

import analyze_jetp_kfw_pilot as pilot


def test_identical_exports_count_distinct_activities():
    payload = (
        "<iati-activities>"
        + "".join(
            f"<iati-activity><iati-identifier>DE-1-{i}</iati-identifier>"
            '<participating-org ref="XM-DAC-5-2"/></iati-activity>'
            for i in range(4036)
        )
        + "</iati-activities>"
    ).encode()
    assert len(pilot.parse_exports([payload, payload])) == 4036


def test_quarter_end_and_partial_period_are_not_first_payment_dates():
    for day in ["2018-12-31", "2021-03-31", "2026-08-26"]:
        event = pilot.payment_event("case", day, "100", "tx1")
        assert event["stage"] == "observed_disbursement"
        assert event["normalized_date"] == ""
        assert event["first_payment_date"] == ""
        assert event["validation_status"] == "period_semantics_unverified"


def test_identical_starts_do_not_validate_zero_delay():
    node = ET.fromstring(
        '<iati-activity><activity-date type="1" iso-date="2016-01-01"/>'
        '<activity-date type="2" iso-date="2016-01-01"/></iati-activity>'
    )
    assert pilot.start_delay(node) is None


def test_negative_entry_is_not_cancellation():
    event = pilot.payment_event("case", "2020-12-31", "-20", "tx1")
    assert event["stage"] == "negative_correction"
    assert event["normalized_date"] == ""


def test_sample_round_robin_excludes_challenges_and_retains_all_candidates():
    units = [
        {"unit_id": str(i), "country": "MA", "sector": sector, "instrument": "110"}
        for sector, i in [
            ("energy", 1),
            ("energy", 2),
            ("non-energy", 3),
            ("non-energy", 4),
            ("non-energy", 5),
        ]
    ]
    selected = pilot.select_sample(units, {"1"}, size=3)
    assert [r["unit_id"] for r in selected if r["selected"] == "true"] == [
        "2",
        "3",
        "4",
    ]
    assert len(selected) == 4
    assert selected[-1]["selected"] == "false"
