"""Stage-three facts carry their stage-two evidence; a document lists what cites it.

Pure in-memory fixtures for the transforms, a temporary root for the two files
``extraction_index`` reads: the fast tier, no subprocess, none of the real
data.  One fictional country ``QQ`` with one named project and one disclosure
slot; two ledger observations for the named project, in the shape ticket 0838
serves; two M1a rows, one per source.
"""

import json
from pathlib import Path

import pytest
from jetp.build_observatory import (
    country_data,
    documents_data,
    extraction_index,
    project_data,
)

ROOT = Path(__file__).resolve().parents[1]

NAMED = {
    "project_id": "qq-project-a",
    "country": "QQ",
    "canonical_name": "Project A",
    "verification_status": "official_report",
}
SLOT = dict(NAMED, project_id="qq-slot-1", canonical_name="",
            verification_status="official_count_slot")
EVENT = {
    "event_id": "qq-event-1",
    "project_id": "qq-project-a",
    "country": "QQ",
    "event_date": "2025-01-01",
    "financial_status": "approved",
    "funder": "Bank A",
    "instrument": "Loan",
    "amount_original": "1",
    "currency_original": "EUR",
    "source_id": "qq-src-a",
    "locator": "PDF pages 12",
    "verification_status": "official_report",
    "notes": "",
}
IMPLEMENTATION_EVENT = {
    "implementation_event_id": "qq-impl-1",
    "project_id": "qq-project-a",
    "country": "QQ",
    "event_date": "2025-06-01",
    "implementation_status": "preparation",
    "source_id": "qq-src-b",
    "locator": "Section 2",
    "verification_status": "secondary_only",
    "notes": "",
}
SOURCES = [
    {"source_id": "qq-src-a", "title": "Source A", "url": "https://example.test/a"},
    {"source_id": "qq-src-b", "title": "Source B", "url": "https://example.test/b"},
]
MANIFEST = [
    {"source_id": "qq-src-a", "status": "collected", "retrieved_at": "2026-01-01T00:00:00Z",
     "sha256": "aa" * 32},
    {"source_id": "qq-src-b", "status": "collected", "retrieved_at": "2026-01-01T00:00:00Z",
     "sha256": "bb" * 32},
]
# The shape ticket 0838 serves: the ledger row verbatim, plus the five fields
# build_observations.py adds.
OBSERVATIONS = [
    dict(EVENT, table="events", kind="financial_event",
         verification="official_report", sha256="aa" * 32, pdf_page=12),
    dict(IMPLEMENTATION_EVENT, table="implementation-events",
         kind="implementation_event", verification="secondary_only",
         sha256="bb" * 32, pdf_page=None),
]
M1A_ROWS = [
    ["QQ", "plan-inventory", "qq-src-a", "qq-src-a:row:001", "Row from source A",
     "Annex 1; PDF pages 12"],
    ["QQ", "plan-inventory", "qq-src-b", "qq-src-b:row:001", "Row from source B",
     "Section 2"],
]
M1A_FIELDS = ["country", "source_layer", "source_id", "source_row_id", "label",
              "evidence_locator"]
CONFIG = {"countries": {"QQ": {"headline_source": ""}}}

# The keys country_data() and project_data() produced before this ticket,
# captured on this fixture: no existing key may disappear.
COUNTRY_KEYS_BEFORE = {"country", "projects", "undisclosed", "record_count",
                       "sources", "editorial", "stages", "technologies"}
PROJECT_KEYS_BEFORE = {"id", "country", "name", "technology", "location",
                       "operator", "notes", "coverage", "coverage_note",
                       "finance_stage", "funders", "events", "claims",
                       "source_links", "sources"}


def fixture_tables():
    return {
        "projects": [dict(NAMED), dict(SLOT)],
        "events": [dict(EVENT)],
        "implementation-events": [dict(IMPLEMENTATION_EVENT)],
        "project-source-links": [],
        "sources": [dict(row) for row in SOURCES],
        "source-claims": [],
        "project-coverage": [],
        "manifest": [dict(row) for row in MANIFEST],
        "event-timing": [],
    }


def fixture_root(tmp_path, *, m1a=True):
    """A root holding only what extraction_index reads besides the tables."""
    data = tmp_path / "deliverables/jetp-observatory/data"
    (data / "m1a").mkdir(parents=True)
    if m1a:
        (data / "m1a/QQ.json").write_text(json.dumps(
            {"country": "QQ", "fields": M1A_FIELDS, "rows": M1A_ROWS}))
    (data / "reviewed-evidence.json").write_text(json.dumps({"records": [
        {"id": "canonical-QQ-headline", "label": "QQ reported position",
         "country": "QQ", "status": "reviewed_fact",
         "evidence": [{"source_id": "qq-src-a", "sha256": "aa" * 32,
                       "locator": "Headline"}]},
    ]}))
    return tmp_path


def test_a_fact_carries_its_evidence_rows_verbatim_and_in_order() -> None:
    evidence = project_data(dict(NAMED), fixture_tables(), OBSERVATIONS)["evidence"]

    # The two complete dictionaries, not their number: a count of two would
    # pass an implementation that doubled one row or recoded secondary_only.
    assert evidence == OBSERVATIONS
    assert [entry["source_id"] for entry in evidence] == ["qq-src-a", "qq-src-b"]
    assert [entry["verification"] for entry in evidence] == [
        "official_report", "secondary_only",
    ]


def test_evidence_is_filtered_on_project_id_only() -> None:
    foreign = dict(OBSERVATIONS[0], project_id="qq-other", event_id="qq-event-9")

    evidence = project_data(dict(NAMED), fixture_tables(),
                            [foreign, *OBSERVATIONS])["evidence"]

    assert evidence == OBSERVATIONS


def test_a_disclosure_slot_gains_no_fact_page_even_with_a_correct_count(tmp_path) -> None:
    result = country_data(tmp_path, "QQ", CONFIG, fixture_tables())

    assert result["undisclosed"] == 1
    assert len(result["projects"]) == 1
    assert result["projects"][0]["id"] == "qq-project-a"
    # Built from the tables, through the 0838 builder: the same two rows.
    assert [(e["table"], e["verification"], e["source_id"])
            for e in result["projects"][0]["evidence"]] == [
        ("events", "official_report", "qq-src-a"),
        ("implementation-events", "secondary_only", "qq-src-b"),
    ]


def test_every_pre_ticket_key_survives_and_evidence_is_the_only_addition(tmp_path) -> None:
    result = country_data(tmp_path, "QQ", CONFIG, fixture_tables())

    assert COUNTRY_KEYS_BEFORE <= set(result)
    project = result["projects"][0]
    assert PROJECT_KEYS_BEFORE < set(project)
    assert set(project) - PROJECT_KEYS_BEFORE == {"evidence"}


def test_a_document_indexes_the_same_project_under_each_of_its_sources(tmp_path) -> None:
    index = extraction_index(fixture_root(tmp_path), fixture_tables(), CONFIG)

    fact = {"project_id": "qq-project-a", "name": "Project A", "country": "QQ"}
    assert index["qq-src-b"]["facts"] == [fact]
    # Source A also carries the reviewed record; the project fact is the same
    # dictionary on both sides, not a substitute.
    assert index["qq-src-a"]["facts"][0] == fact
    assert index["qq-src-a"]["facts"][0] == index["qq-src-b"]["facts"][0]
    assert [f for f in index["qq-src-a"]["facts"] if "record_id" in f] == [
        {"record_id": "canonical-QQ-headline", "label": "QQ reported position",
         "country": "QQ", "status": "reviewed_fact"},
    ]


def test_extracted_lists_hold_the_ledger_row_and_the_m1a_row_separately(tmp_path) -> None:
    index = extraction_index(fixture_root(tmp_path), fixture_tables(), CONFIG)

    products = [(row["product"], row.get("id") or row.get("source_row_id"))
                for row in index["qq-src-a"]["extracted"]]
    assert products == [("ledger", "qq-event-1"), ("m1a", "qq-src-a:row:001")]
    assert [row["product"] for row in index["qq-src-b"]["extracted"]] == [
        "ledger", "m1a",
    ]
    # Two lists per source, never a total across them.
    assert set(index["qq-src-a"]) == {"extracted", "facts"}


def test_a_missing_m1a_view_stops_the_build_instead_of_serving_an_empty_list(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="m1a/QQ.json"):
        extraction_index(fixture_root(tmp_path, m1a=False), fixture_tables(), CONFIG)


def test_the_documents_view_carries_the_index_when_given_the_config(tmp_path) -> None:
    root = fixture_root(tmp_path)
    tables = fixture_tables()

    with_index = documents_data(root, tables, CONFIG)
    registry_only = documents_data(root, tables)

    assert set(with_index["by_source_id"]) == {"qq-src-a", "qq-src-b"}
    assert with_index["documents"] == registry_only["documents"]
    assert "by_source_id" not in registry_only


def test_renderer_ports_the_descent_and_the_climb() -> None:
    renderer = (ROOT / "deliverables/jetp-observatory/app.js").read_text()

    assert "by_source_id" in renderer
    assert "documentHref(" in renderer
    project_page = renderer[renderer.index("function projectPage("):]
    project_page = project_page[:project_page.index("\nfunction ")]
    assert "<details" in project_page
    assert "No link between the 2023 table and the 2025 portfolio" in renderer
