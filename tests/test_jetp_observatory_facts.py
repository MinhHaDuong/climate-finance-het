"""Stage-three facts descend to their stage-two evidence; a document lists what cites it.

Pure in-memory fixtures for the transforms, a temporary root for the two files
``extraction_index`` reads: the fast tier, no subprocess, none of the real
data.  One fictional country ``QQ`` with one named project and one disclosure
slot; two M1a rows, one per source.  One test reads the shipped ZAF view: the
publication cap (ticket 0855) is a property of the real bytes, and the slow
tier was the only thing guarding it.
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
M1A_ROWS = [
    ["QQ", "plan-inventory", "qq-src-a", "qq-src-a:row:001", "Row from source A",
     "Annex 1; PDF pages 12"],
    ["QQ", "plan-inventory", "qq-src-b", "qq-src-b:row:001", "Row from source B",
     "Section 2"],
]
M1A_FIELDS = ["country", "source_layer", "source_id", "source_row_id", "label",
              "evidence_locator"]
CONFIG = {"countries": {"QQ": {"headline_source": ""}}}

# The keys country_data() and project_data() produced before ticket 0839,
# captured on this fixture: no existing key may disappear.  0839 added
# ``evidence`` to each project, a verbatim copy of the country's ledger rows;
# ticket 0855 removed it again, because the copy put the ZAF view 280 kB over
# the publication cap while ``observations/<CODE>.json`` already served the
# same rows.  The descent now reads that view, so a project carries exactly
# the keys it carried before 0839.
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


def test_a_fact_carries_no_copy_of_its_observation_rows() -> None:
    # Neither the rows nor a per-row reference list: 338 ZAF observations at
    # eight spare bytes each is the whole margin under the cap (ticket 0855).
    # The descent reads observations/<CODE>.json, filtered on project_id.
    project = project_data(dict(NAMED), fixture_tables())

    assert "evidence" not in project


def test_the_shipped_zaf_view_stays_under_the_publication_cap() -> None:
    # The slow tier guards this through build_zaf_positions.validate_migration;
    # main went red for a day before anyone ran it (ticket 0855).  Same limit,
    # same file, read at the fast tier.
    policy = json.loads((ROOT / "config/jetp-zaf-migration.json").read_text())
    view = ROOT / "deliverables/jetp-observatory/data/ZAF.json"

    assert view.stat().st_size <= policy["publication_limit_bytes"]


def test_a_disclosure_slot_gains_no_fact_page_even_with_a_correct_count(tmp_path) -> None:
    result = country_data(tmp_path, "QQ", CONFIG, fixture_tables())

    assert result["undisclosed"] == 1
    assert len(result["projects"]) == 1
    assert result["projects"][0]["id"] == "qq-project-a"


def test_every_pre_ticket_key_survives_and_none_is_added(tmp_path) -> None:
    result = country_data(tmp_path, "QQ", CONFIG, fixture_tables())

    assert COUNTRY_KEYS_BEFORE <= set(result)
    assert set(result["projects"][0]) == PROJECT_KEYS_BEFORE


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
    descent = renderer[renderer.index("function projectEvidenceRow("):]
    descent = descent[:descent.index("\nfunction median(")]
    assert "<details" in descent
    # The fold-out is built from the country's observations view, the one the
    # Observations tab loads, not from a copy in the country view (0855).
    assert "p.evidence" not in descent
    assert "observationsView(p.country)" in descent
    assert 'load("observations/" + ' in renderer
    assert "No link between the 2023 table and the 2025 portfolio" in renderer
