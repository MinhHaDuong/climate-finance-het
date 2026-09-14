"""Offline FCDO feasibility calculations; acceptance-test starting point."""
import json


def clocks(record, parent=None):
    dates = [json.loads(d) for d in (parent or record).get("json.activity-date", [])]
    return {
        "actual_start": next((d["iso-date"] for d in dates if d["type"] == 2), ""),
        "approved_unsigned": record.get("activity_status_code") == "1",
    }
