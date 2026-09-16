"""Bounded replay contract for the seven Indonesia 0819 documents."""

from __future__ import annotations

import json
from pathlib import Path

from jetp.build_0819_indonesia_ingestion import build_report


ROOT = Path(__file__).resolve().parents[1]


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
    assert progress["canonical_finance_admitted"] == 0
    assert progress["date_precision"] == "reporting_cutoff_or_publication_review_required"
    assert all(row["review_disposition"] == "reviewed_no_operation_candidate"
               for row in report["sources"] if row is not progress)


def test_committed_report_is_a_clean_replay_of_the_bounded_review() -> None:
    path = ROOT / "docs" / "jetp-study" / "0819-indonesia-ingestion.json"
    assert json.loads(path.read_text(encoding="utf-8")) == build_report(ROOT)
