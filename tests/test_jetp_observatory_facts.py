"""Stage-three facts carry no copy of their evidence, and a document view no index of it.

Pure in-memory fixtures for the transforms: the fast tier, no subprocess,
none of the real data.  One fictional country ``QQ`` with one named project
and one disclosure slot.  One test reads the shipped ZAF view: the
publication cap (ticket 0855) is a property of the real bytes, and the slow
tier was the only thing guarding it.

The climb, document → what cites it, was ``extraction_index()`` here until
ticket 0858; it is a read-time join in the renderer now, and its tests —
the same project under each of its sources, two lists never a total — are
render tests in ``test_jetp_observatory_render.py``.
"""

import json
from pathlib import Path

from jetp.build_observatory import country_data, documents_data, project_data

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


def test_the_documents_view_is_the_registry_and_nothing_derived(tmp_path) -> None:
    # Ticket 0858: one served file is one table.  The view takes no config
    # and reads no other view; what a document yielded is a join the page
    # makes on the views served beside it, never a key written here.
    view = documents_data(tmp_path, fixture_tables())

    assert set(view) == {"documents"}
    assert [row["id"] for row in view["documents"]] == ["qq-src-a", "qq-src-b"]


def test_renderer_ports_the_descent_and_the_climb() -> None:
    renderer = (ROOT / "deliverables/jetp-observatory/app.js").read_text()

    assert "documentHref(" in renderer
    descent = renderer[renderer.index("function projectEvidenceRow("):]
    descent = descent[:descent.index("\nfunction median(")]
    assert "<details" in descent
    # The fold-out is built from the country's observations view, the one the
    # Observations tab loads, not from a copy in the country view (0855).
    assert "p.evidence" not in descent
    assert "observationsView(p.country)" in descent
    assert 'load("observations/" + ' in renderer
    # The climb is a join on the served stage-two views, loaded per country
    # (0858): the Documents cell reads them through the same cache as the
    # inventory page, and reads nothing from the registry view but the row.
    climb = renderer[renderer.index("function extractionCell("):]
    climb = climb[:climb.index("\nfunction documentsPage(")]
    assert "stageTwo(entry.country)" in climb
    assert "documentsData." not in climb
    assert 'load("m1a/" + ' in renderer
    assert "No link between the 2023 table and the 2025 portfolio" in renderer
