"""Bounded replay contract for the seven Indonesia 0819 documents."""

import json
from pathlib import Path

import pytest
from jetp.build_0819_indonesia_ingestion import build_report, validate_adjudications

ROOT = Path(__file__).resolve().parents[1]


pytestmark = pytest.mark.wp_jetp

def test_seven_document_review_keeps_priority_separate_from_finance() -> None:
    """A priority list supplies plan candidates, never an allocation or approval."""
    report = build_report(ROOT)

    assert report["source_count"] == 7
    assert report["candidate_counts"] == {
        "plan_priority_candidate": 1142,
        "canonical_finance_admitted": 0,
    }
    progress = next(
        row for row in report["sources"]
        if row["source_id"] == "idn-jetp-progress-report-2025"
    )
    assert progress["candidate_kind"] == "plan_priority_candidate"
    assert len(progress["candidate_ids"]) == 1142
    assert len(set(progress["candidate_ids"])) == 1142
    assert progress["canonical_finance_admitted"] == 0
    assert progress["date_precision"] == "reporting_cutoff_or_publication_review_required"
    assert all(row["review_disposition"] == "no_operation_candidate"
               for row in report["sources"] if row is not progress)


def test_committed_report_is_a_clean_replay_of_the_bounded_review() -> None:
    path = ROOT / "docs" / "jetp-study" / "0819-indonesia-ingestion.json"
    assert json.loads(path.read_text(encoding="utf-8")) == build_report(ROOT)


def test_thematic_source_needs_page_adjudication_before_a_zero_conclusion() -> None:
    """A retained PDF cannot become a reviewed zero merely by source genre."""
    adjudications = [
        {
            "source_id": "idn-jetp-energy-efficiency-electrification-2025",
            "page": "78",
            "excerpt": "proposed reform roadmap",
            "disposition": "no_operation_candidate",
            "reason": "Policy roadmap, not an identified operation or finance event.",
        }
    ]
    with pytest.raises(ValueError, match="missing page adjudication"):
        validate_adjudications(adjudications, {
            "idn-jetp-energy-efficiency-electrification-2025",
            "idn-jetp-captive-power-study-2025",
        })

    report = build_report(ROOT)
    thematic = [row for row in report["sources"] if row["candidate_kind"] == "contextual_analysis_only"]
    assert len(thematic) == 6
    assert all(row["adjudication"]["page"] and row["adjudication"]["excerpt"] for row in thematic)
