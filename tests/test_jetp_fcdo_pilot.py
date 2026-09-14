"""FCDO programme and component clocks must retain their distinct meanings."""
import importlib.util
import json
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "fcdo_pilot", Path(__file__).parents[1] / "docs/jetp-pilots/2026-09-15/fcdo/calculate.py"
)
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)


def test_component_start_and_earlier_expenditure_are_not_parent_or_transfer_clock():
    parent = {"json.activity-date": [json.dumps({"type": 2, "iso-date": "2007-03-09"})]}
    component = {
        "json.activity-date": [json.dumps({"type": 2, "iso-date": "2007-02-01"})],
        "json.transaction": [json.dumps(t) for t in [
            {"transaction-type": {"code": 4}, "transaction-date": {"iso-date": "2007-03-31"},
             "value": 300000, "description": {"narrative": "Aggregated spend data"}},
            {"transaction-type": {"code": 3}, "transaction-date": {"iso-date": "2010-08-11"},
             "value": 100},
        ]],
    }
    result = pilot.clocks(component, parent)
    assert result["actual_start"] == "2007-02-01"
    assert result["earliest_observed_expenditure"] == "2007-03-31"
    assert result["earliest_observed_transfer"] == "2010-08-11"
    assert result["first_spending"] == ""


def test_pipeline_is_not_approved_unsigned_financing():
    assert pilot.clocks({"activity_status_code": "1"})["approved_unsigned"] == "unknown"


def test_parallel_arrays_are_not_milestone_pairs():
    assert pilot.clocks({"activity_date_type": ["2"],
                         "activity_date_iso_date": ["2007-03-09"]})["actual_start"] == ""
