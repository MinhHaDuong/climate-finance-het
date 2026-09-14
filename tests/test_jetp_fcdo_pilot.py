"""FCDO programme and component clocks must retain their distinct meanings."""

import importlib.util
import json
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "fcdo_pilot",
    Path(__file__).parents[1] / "docs/jetp-pilots/2026-09-15/fcdo/calculate.py",
)
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)


def test_component_start_and_earlier_expenditure_are_not_parent_or_transfer_clock():
    parent = {"json.activity-date": [json.dumps({"type": 2, "iso-date": "2007-03-09"})]}
    component = {
        "json.activity-date": [json.dumps({"type": 2, "iso-date": "2007-02-01"})],
        "json.transaction": [
            json.dumps(t)
            for t in [
                {
                    "transaction-type": {"code": 4},
                    "transaction-date": {"iso-date": "2007-03-31"},
                    "value": 300000,
                    "description": {"narrative": "Aggregated spend data"},
                },
                {
                    "transaction-type": {"code": 3},
                    "transaction-date": {"iso-date": "2010-08-11"},
                    "value": 100,
                },
            ]
        ],
    }
    result = pilot.clocks(component, parent)
    assert result["actual_start"] == "2007-02-01"
    assert result["earliest_observed_expenditure"] == "2007-03-31"
    assert result["earliest_observed_transfer"] == "2010-08-11"
    assert result["first_spending"] == ""


def test_pipeline_is_not_approved_unsigned_financing():
    assert pilot.clocks({"activity_status_code": "1"})["approved_unsigned"] == "unknown"


def test_parallel_arrays_are_not_milestone_pairs():
    assert (
        pilot.clocks(
            {"activity_date_type": ["2"], "activity_date_iso_date": ["2007-03-09"]}
        )["actual_start"]
        == ""
    )


def test_sampling_keeps_completed_and_does_not_guess_sector_vocabulary():
    records = [
        {
            "iati_identifier": f"AL-{i:02}",
            "hierarchy": 1,
            "activity_status_code": "4",
            "recipient_country_code": ["AL"],
            "sector_code": ["23010"],
        }
        for i in range(15)
    ]
    records += [
        {"iati_identifier": ident, "hierarchy": hierarchy}
        for ident, hierarchy in [("GB-1-112151", 1), ("GB-1-112151-101", 2)]
    ]
    rows = pilot.selection(records)
    sampled = [r for r in rows if r["role"] == "sample"]
    assert len(sampled) == 15
    assert [r["case_id"] for r in sampled if r["selected"] == "true"] == [
        f"AL-{i:02}" for i in range(12)
    ]
    assert all(r["stratum"] == "AL|mixed-or-unmapped|missing" for r in sampled)


def test_unknown_membership_denominator_is_not_measured_zero():
    unit = {
        "unit_id": "example",
        "country": "IN",
        "sector_mapped": "non-energy",
        "instrument_raw": "",
        "source_unit": "programme",
    }
    rows = pilot.build_coverage([unit], {})
    unsupported = [r for r in rows if r["count_kind"] in {"member", "pending"}]
    assert unsupported
    assert all(r["count"] == "" and r["missing_count"] == "" for r in unsupported)


def test_entry_cohort_separates_unpaired_dates_from_missing_start():
    assert (
        pilot.entry_cohort({"activity_date_type": ["1", "3"]}, {})
        == "missing_actual_start"
    )
    assert (
        pilot.entry_cohort({"activity_date_type": ["1", "2", "3"]}, {})
        == "unvalidated_unpaired_or_conflicting"
    )
