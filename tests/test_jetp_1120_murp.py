"""The AfDB MURP approval has its own cited loan and an unresolved event day."""

import csv
from pathlib import Path

import pytest
from jetp.build_observations import normalize_event_tables, reconcile_timing_rows

DATA = Path(__file__).resolve().parents[1] / "data/jetp"
EVENT = "zaf-murp-afdb-approved-2026"


pytestmark = pytest.mark.wp_jetp

def rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_1120_source_identity_stage_and_date_are_separate():
    decision, = rows(DATA / "migration/1120-event-adjudications.csv")
    event, = [row for row in rows(DATA / "events.csv") if row["event_id"] == EVENT]
    line, = [row for row in rows(DATA / "lines.d/ZAF-2026.csv")
             if row["line_id"] == decision["line_id"]]
    referent, = [row for row in rows(DATA / "line-referents.csv")
                 if row["referent_row_id"] == "1120.agreement.agreement-zaf-murp-afdb-2026"]
    agreement, = [row for row in rows(DATA / "agreements.csv")
                  if row["agreement_id"] == decision["referent_id"]]
    collected = {row["sha256"] for row in rows(DATA / "retrievals.csv")
                 if row["document_id"] == event["source_id"] and row["status"] == "collected"}
    assert line["sha256"] in collected
    assert line["locator"].endswith("p:nth-of-type(1)")
    assert line["own_status"] == event["financial_status"] == "approved"
    assert referent["line_id"] == line["line_id"]
    assert referent["referent_id"] == agreement["agreement_id"]
    assert agreement["agreement_id"] != "agreement-zaf-register-afdb004"

    observations, timings, pending = normalize_event_tables(
        [event], [], [row for row in rows(DATA / "event-timing.csv")
                      if row["event_id"] == EVENT],
        rows(DATA / "migration/0875-dispositions.csv"), [decision])
    observation, = observations
    assert (observation["subject_kind"], observation["subject_id"],
            observation["value"], observation["currency"], observation["own_status"]) == (
                "agreement", agreement["agreement_id"], "400000000", "USD", "approved")
    assert timings == []
    assert [row["reason"] for row in pending] == [
        "approval_day_unsupported_by_cited_article"]
    reconciliation, = reconcile_timing_rows(
        [row for row in rows(DATA / "event-timing.csv") if row["event_id"] == EVENT],
        observations, timings, pending)
    assert reconciliation["outcome"] == "pending"
    assert reconciliation["timing_id"] == ""
