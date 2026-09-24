"""Ledger rows served as explorable observations, under their own counts.

Pure fixtures for the transform, plain file reads for the shipped views: the
fast tier.  The three tables are two extractions apart from the M1a
inventories, so nothing here is ever added to an inventory row count.
"""

import json
from pathlib import Path

import pytest
from jetp._observatory_data import observation_entry
from jetp.build_observations import (
    COUNTRIES,
    build_registry,
    observations_by_country,
)

ROOT = Path(__file__).resolve().parents[1]
OBSERVATIONS = ROOT / "deliverables" / "jetp-observatory" / "data" / "observations"

REGISTRY = {
    "source-a": {"sha256": "aa" * 32},
    "source-b": {"sha256": "bb" * 32},
}

EVENT_VERIFIED = {
    "event_id": "e1",
    "project_id": "p1",
    "country": "ZAF",
    "event_date": "2021-01-01",
    "scope": "jetp_strict",
    "financial_status": "signed",
    "funder": "BEI",
    "window": "Skills",
    "instrument": "Grants",
    "amount_original": "12.5",
    "currency_original": "EUR",
    "amount_usd": "14.0",
    "conversion_method": "x",
    "source_id": "source-a",
    "document_sha256": "aa" * 32,
    "locator": "PDF pages 10",
    "verification_status": "official_register",
    "notes": "n1",
}
EVENT_SECONDARY = dict(
    EVENT_VERIFIED,
    event_id="e2",
    verification_status="secondary_only",
    source_id="source-b",
    locator="Appendix 3, row 4",
)
IMPLEMENTATION_EVENT = {
    "implementation_event_id": "i1",
    "project_id": "p1",
    "country": "ZAF",
    "event_date": "2025-01-01",
    "implementation_status": "preparation",
    "capacity_mw": "10",
    "source_id": "source-a",
    "document_sha256": "aa" * 32,
    "locator": "Table 4.3-3 pp.72-73",
    "verification_status": "primary_source",
    "notes": "n3",
}
PROJECT_SOURCE_LINK = {
    "link_id": "l1",
    "country": "ZAF",
    "project_id": "p1",
    "source_id": "source-b",
    "relationship": "project_report",
    "locator": "whole report",
    "review_status": "provisional",
    "notes": "n4",
}


def fixture_tables():
    return {
        "events": [dict(EVENT_VERIFIED), dict(EVENT_SECONDARY)],
        "implementation-events": [dict(IMPLEMENTATION_EVENT)],
        "project-source-links": [dict(PROJECT_SOURCE_LINK)],
    }


def test_every_country_key_is_served_even_when_it_has_no_row() -> None:
    # A country with no row of a table is a correct result, not an omission: a
    # view that dropped the empty countries would make the page 404 for them.
    result = observations_by_country(fixture_tables(), REGISTRY)

    assert {code: len(rows) for code, rows in result.items()} == {
        "ZAF": 4,
        "IDN": 0,
        "VNM": 0,
        "SEN": 0,
    }


def test_rows_keep_their_table_order_and_are_never_merged() -> None:
    result = observations_by_country(fixture_tables(), REGISTRY)

    assert [entry["table"] for entry in result["ZAF"]] == [
        "events",
        "events",
        "implementation-events",
        "project-source-links",
    ]
    # Both event rows carry the same project_id: an implementation that grouped
    # by project would serve one row where the ledger holds two.
    assert [entry["table"] for entry in result["ZAF"]].count("events") == 2


def test_the_kind_is_derived_from_the_table_never_read_from_a_column() -> None:
    result = observations_by_country(fixture_tables(), REGISTRY)

    assert [entry["kind"] for entry in result["ZAF"]] == [
        "financial_event",
        "financial_event",
        "implementation_event",
        "project_source_link",
    ]
    # None of the three tables publishes a kind column, so the value cannot
    # have come from the row.
    assert all("kind" not in row for row in fixture_tables()["events"])


def test_amounts_are_served_as_the_source_wrote_them() -> None:
    entry = observations_by_country(fixture_tables(), REGISTRY)["ZAF"][0]

    assert entry["amount_original"] == "12.5"
    assert isinstance(entry["amount_original"], str)
    assert entry["amount_usd"] == "14.0"
    assert isinstance(entry["amount_usd"], str)


def test_a_secondary_only_row_keeps_its_own_verification_word() -> None:
    result = observations_by_country(fixture_tables(), REGISTRY)

    assert result["ZAF"][1]["verification"] == "secondary_only"
    # The alias is a uniform reading key across tables, not a replacement: the
    # column the source published stays in the entry under its own name.
    assert result["ZAF"][1]["verification_status"] == "secondary_only"
    assert result["ZAF"][0]["verification"] == "official_register"
    assert result["ZAF"][0]["verification_status"] == "official_register"


def test_the_two_tables_that_name_their_review_column_differently_both_resolve() -> None:
    result = observations_by_country(fixture_tables(), REGISTRY)

    assert result["ZAF"][2]["verification"] == "primary_source"
    assert result["ZAF"][3]["verification"] == "provisional"
    assert result["ZAF"][3]["review_status"] == "provisional"


def test_the_fingerprint_follows_the_registry_not_the_row_column() -> None:
    result = observations_by_country(fixture_tables(), REGISTRY)

    assert [entry["sha256"] for entry in result["ZAF"]] == [
        "aa" * 32,
        "bb" * 32,
        "aa" * 32,
        "bb" * 32,
    ]
    # Falsify the registry: an implementation that copied the row's own
    # document_sha256 column would still answer "aa" * 32 here.
    falsified = {"source-a": {"sha256": "zz" * 32}, "source-b": {"sha256": "bb" * 32}}
    assert observations_by_country(fixture_tables(), falsified)["ZAF"][0][
        "sha256"
    ] == "zz" * 32


def test_the_pdf_page_comes_from_the_locator_and_is_absent_where_none_is_named() -> None:
    result = observations_by_country(fixture_tables(), REGISTRY)

    assert [entry["pdf_page"] for entry in result["ZAF"]] == [10, None, None, None]


def test_a_source_the_collection_never_recorded_serves_its_locator_not_an_error() -> None:
    # Seven Viet Nam link rows name sources that were never collected. Aborting
    # the build would leave that country with no observations at all; the entry
    # is served with a null fingerprint so the page shows the locator as text.
    entry = observation_entry(
        dict(PROJECT_SOURCE_LINK, source_id="source-never-collected"),
        "project-source-links",
        REGISTRY,
    )

    assert entry["sha256"] is None
    assert entry["locator"] == "whole report"
    assert entry["verification"] == "provisional"


def test_an_unknown_table_is_refused() -> None:
    with pytest.raises(ValueError, match="observation table"):
        observation_entry(dict(EVENT_VERIFIED), "reviewed-evidence", REGISTRY)


def test_the_per_table_count_never_diverges_from_the_rows_it_summarises() -> None:
    rows = observations_by_country(fixture_tables(), REGISTRY)["ZAF"]

    per_table = {
        table: sum(1 for entry in rows if entry["table"] == table)
        for table in ("events", "implementation-events", "project-source-links")
    }

    assert per_table == {"events": 2, "implementation-events": 1, "project-source-links": 1}
    assert sum(per_table.values()) == len(rows)


def test_the_shipped_views_carry_every_ledger_row_once() -> None:
    import csv

    served = 0
    for code in COUNTRIES:
        served += len(json.loads((OBSERVATIONS / f"{code}.json").read_text("utf-8")))

    ledger = 0
    for table in ("events", "implementation-events", "project-source-links"):
        with (ROOT / "data/jetp" / f"{table}.csv").open(encoding="utf-8") as stream:
            ledger += len(list(csv.DictReader(stream)))

    assert served == ledger == 766


def test_a_row_without_a_fingerprint_is_one_of_two_named_collection_gaps() -> None:
    # Two different absences, and the page cannot show either as a link, so
    # both are pinned rather than pooled: link rows naming a source the
    # registry never recorded at all, and twenty-one rows naming one it
    # recorded but never archived. Neither is a renderer defect, and a new
    # one cannot reach the page unnoticed.
    import csv

    with (ROOT / "data/jetp/manifest.csv").open(encoding="utf-8") as stream:
        registry = build_registry({"manifest": list(csv.DictReader(stream))})

    unregistered, unarchived = [], []
    for code in COUNTRIES:
        for entry in json.loads((OBSERVATIONS / f"{code}.json").read_text("utf-8")):
            if entry["sha256"]:
                continue
            target = unarchived if entry["source_id"] in registry else unregistered
            target.append((code, entry["table"], entry["source_id"]))

    # Empty, not a count: ticket 0854 collected the seven Viet Nam link
    # sources this list used to name (all `collected`, none failed), so any
    # source — in any country, in any of the three tables — that a link row
    # cites without a registry attempt fails here with its own identifier in
    # the message. A source whose attempt failed belongs in `unarchived`
    # below, with its status.
    assert unregistered == []
    # The second gap is a collection outcome, not a join failure: these sources
    # are in the registry and no attempt of theirs recorded a digest.
    # Twenty-one, not the twenty-two measured before the registry rule stopped
    # ranking on disk state: sen-arcop-aser-audit-2023 has a recorded digest
    # and only looked archive-less because its bytes were absent here.
    assert len(unarchived) == 21
    assert all(registry[source_id]["sha256"] is None for _, _, source_id in unarchived)


def test_the_shipped_views_resolve_against_the_shipped_registry() -> None:
    # Two assertions, because either alone passes a defect the other catches.
    # Membership: every published fingerprint is one the collection recorded
    # for that same source, so the renderer's sha256 index finds the document.
    # Equality: it is the fingerprint the registry rule selects, so a view
    # regenerated from a different rule — or not regenerated at all — reddens
    # here instead of shipping a stale digest that still exists somewhere.
    import csv

    documents = json.loads(
        (OBSERVATIONS.parent / "documents.json").read_text(encoding="utf-8")
    )["documents"]
    by_source = {}
    for entry in documents:
        by_source.setdefault(entry["id"], set()).add(entry["sha256"])
    with (ROOT / "data/jetp/manifest.csv").open(encoding="utf-8") as stream:
        registry = build_registry({"manifest": list(csv.DictReader(stream))})

    for code in COUNTRIES:
        for entry in json.loads((OBSERVATIONS / f"{code}.json").read_text("utf-8")):
            if entry["sha256"]:
                assert entry["sha256"] in by_source[entry["source_id"]], entry[
                    "source_id"
                ]
                assert registry[entry["source_id"]]["sha256"] == entry["sha256"]


def test_the_published_fingerprint_does_not_depend_on_the_local_snapshot() -> None:
    # The registry is collapsed on what the collection recorded, not on what is
    # staged on disk, so two builds of the same manifest agree whether or not
    # the DVC snapshot is checked out. One Senegal source flipped this way
    # during development: its collected attempt carries the digest, a sibling
    # attempt none, and disk availability decided which one won.
    manifest = [
        {"source_id": "shared", "status": "blocked", "sha256": ""},
        {"source_id": "shared", "status": "collected", "sha256": "cc" * 32},
        {"source_id": "shared", "status": "not_modified", "sha256": "cc" * 32},
    ]

    assert build_registry({"manifest": manifest}) == {"shared": {"sha256": "cc" * 32}}
    assert build_registry({"manifest": list(reversed(manifest))}) == {
        "shared": {"sha256": "cc" * 32}
    }
    # A source whose every attempt failed keeps a null fingerprint rather than
    # an empty string, which would read as a digest of nothing.
    assert build_registry({"manifest": manifest[:1]}) == {"shared": {"sha256": None}}
    # A collection that recorded nothing does not outrank one that did, whatever
    # its status word says.
    hollow = [
        {"source_id": "shared", "status": "collected", "sha256": ""},
        {"source_id": "shared", "status": "not_modified", "sha256": "dd" * 32},
    ]
    assert build_registry({"manifest": hollow}) == {"shared": {"sha256": "dd" * 32}}


def test_two_equally_ranked_attempts_that_disagree_resolve_by_content() -> None:
    # One registry identifier carries two attempts tied on status with
    # different digests (zaf-ntcsa-transmission-plans; no ledger row cites it
    # today). A rank alone leaves that pair to the order of manifest.csv, so
    # the retrieval date and then the digest itself close the order: the answer
    # is a property of the rows, not of how they were filed.
    tied = [
        {
            "source_id": "shared",
            "status": "collected",
            "sha256": "ee" * 32,
            "retrieved_at": "2026-01-01T00:00:00Z",
        },
        {
            "source_id": "shared",
            "status": "collected",
            "sha256": "ff" * 32,
            "retrieved_at": "2026-06-01T00:00:00Z",
        },
    ]

    assert build_registry({"manifest": tied}) == {"shared": {"sha256": "ff" * 32}}
    assert build_registry({"manifest": list(reversed(tied))}) == {
        "shared": {"sha256": "ff" * 32}
    }
    # Same date too: the digest is the last term, and it is still order-free.
    same_day = [dict(row, retrieved_at="2026-06-01T00:00:00Z") for row in tied]
    assert build_registry({"manifest": same_day}) == build_registry(
        {"manifest": list(reversed(same_day))}
    )


def test_the_public_bundle_carries_the_observations_without_a_new_view() -> None:
    # Action 5 of the ticket, verified rather than assumed: site_files is the
    # function the freeze walks, and VIEWS governs only the top-level downloads.
    from jetp._bundle_inventory import SITE, VIEWS, site_files

    site = ROOT / SITE
    carried = {path.relative_to(site).as_posix() for path in site_files(site)}

    for code in COUNTRIES:
        assert f"data/observations/{code}.json" in carried
    assert "observations" not in VIEWS


def test_the_javascript_port_serves_the_same_observation_contract() -> None:
    renderer = (ROOT / "deliverables" / "jetp-observatory" / "app.js").read_text(
        encoding="utf-8"
    )

    assert '"observations/" + code' in renderer or "`observations/${code}`" in renderer
    for key in ("table", "kind", "verification", "pdf_page", "sha256"):
        assert key in renderer
    # The three kinds are labelled in the renderer, and the verification words
    # are shown verbatim: no recoding table may appear beside them.
    for kind in ("financial_event", "implementation_event", "project_source_link"):
        assert kind in renderer
    # The shared component of ticket 0835, under the id the browser recipe
    # addresses (#observations-filters, #observations-count, …).
    assert 'filterTable("observations"' in renderer
    # No recoding table: the verification words reach the page as the ledger
    # wrote them, so none of them can be spelled out in the renderer.
    assert "secondary_only" not in renderer
    assert "official_register" not in renderer


def test_the_two_stage_two_products_are_declared_distinct_on_the_page() -> None:
    renderer = (ROOT / "deliverables" / "jetp-observatory" / "app.js").read_text(
        encoding="utf-8"
    )

    assert "never added together" in renderer
    assert "two readings of some of the same publications" in renderer
