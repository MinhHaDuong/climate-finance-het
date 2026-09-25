"""Source and referent integrity for the 27 Indonesia event decisions."""

import csv
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "data/jetp"


pytestmark = pytest.mark.wp_jetp

def rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_0970_adjudications_cite_collected_rows_and_existing_referents():
    decisions = rows(DATA / "migration/0970-event-adjudications.csv")
    assert len(decisions) == 27
    assert len({(r["legacy_table"], r["legacy_event_id"]) for r in decisions}) == 27

    events = {r["event_id"]: r for r in rows(DATA / "events.csv")}
    implementations = {
        r["implementation_event_id"]: r
        for r in rows(DATA / "implementation-events.csv")
    }
    lines = {
        r["line_id"]: r
        for path in (DATA / "lines.d").glob("*.csv")
        for r in rows(path)
    }
    referents = {
        (r["line_id"], r["referent_kind"], r["referent_id"])
        for r in rows(DATA / "line-referents.csv")
        if r["status"] == "accepted"
    }
    valid_ids = {
        "agreement": {r["agreement_id"] for r in rows(DATA / "agreements.csv")},
        "project": {r["project_id"] for r in rows(DATA / "projects.csv")},
    }
    for decision in decisions:
        table = decision["legacy_table"]
        assert table in {"events", "implementation-events"}
        legacy = (events if table == "events" else implementations)[
            decision["legacy_event_id"]
        ]
        line = lines[decision["line_id"]]
        assert legacy["project_id"] == decision["legacy_project_id"]
        assert legacy["source_id"] == decision["source_id"]
        assert legacy["document_sha256"] == line["sha256"]
        assert line["country"] == "IDN"
        kind, identity = decision["referent_kind"], decision["referent_id"]
        if kind == "line":
            assert identity == decision["line_id"]
            assert decision["identity_decision"] == "source_row_only"
        else:
            assert identity in valid_ids[kind]
            assert (decision["line_id"], kind, identity) in referents


def test_0970_keeps_distinct_grants_and_holds_unsupported_physical_claims():
    decisions = rows(DATA / "migration/0970-event-adjudications.csv")
    grants = [
        r for r in decisions
        if r["legacy_event_id"].startswith(("idn-approved-etp-", "idn-approved-ietf-"))
    ]
    assert len(grants) == 4
    assert len({r["referent_id"] for r in grants}) == 4
    assert len({r["line_id"] for r in grants}) == 4

    held = {r["legacy_event_id"] for r in decisions if r["promotion"] == "hold"}
    assert held == {
        "idn-impl-green-corridors-2025",
        "idn-impl-dieng34-2025",
        "idn-impl-nagajaya-portal-2026",
    }
    assert all(r["legacy_table"] == "implementation-events" for r in decisions if r["promotion"] == "hold")
    assert sum(r["promotion"] == "accept" for r in decisions) == 24
