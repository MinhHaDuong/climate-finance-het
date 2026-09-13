"""Regression contracts for safely regenerating Senegal plan rows."""

from __future__ import annotations

import csv

import pytest
from jetp.build_sen_plan_projects import (
    ANNEX_SHA256,
    ANNEX_SOURCE_ID,
    FIELDS,
    MAIN_SHA256,
    MAIN_SOURCE_ID,
    extract_quick_wins,
    extract_received_projects,
    write_csv,
)


def _row(**overrides: str) -> dict[str, str]:
    row = dict.fromkeys(FIELDS, "")
    row.update(
        plan_project_id="sen-plan-qw-01",
        country="SEN",
        source_id=MAIN_SOURCE_ID,
        ordinal="1",
        project_name="Quick win one",
        canonical_project_id="sen-project-annex-15",
        reconciliation_status="matched",
        document_sha256=MAIN_SHA256,
        notes="reviewed crosswalk",
    )
    row.update(overrides)
    return row


def _read(path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_regeneration_preserves_reviewed_reconciliation_only_for_stable_row(
    tmp_path,
) -> None:
    output = tmp_path / "plan-projects.csv"
    stable = _row()
    changed_hash = _row(
        plan_project_id="sen-plan-qw-02",
        ordinal="2",
        document_sha256="0" * 64,
        canonical_project_id="sen-project-qw-02",
        notes="stale reviewed note",
    )
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows([stable, changed_hash])

    regenerated = [
        _row(canonical_project_id="", reconciliation_status="plan_only", notes="raw"),
        _row(
            plan_project_id="sen-plan-qw-02",
            ordinal="2",
            canonical_project_id="",
            reconciliation_status="plan_only",
            notes="fresh raw note",
        ),
    ]
    write_csv(regenerated, output)

    rows = {row["plan_project_id"]: row for row in _read(output)}
    assert rows["sen-plan-qw-01"]["canonical_project_id"] == (
        "sen-project-annex-15"
    )
    assert rows["sen-plan-qw-01"]["reconciliation_status"] == "matched"
    assert rows["sen-plan-qw-01"]["notes"] == "reviewed crosswalk"
    assert rows["sen-plan-qw-02"]["canonical_project_id"] == ""
    assert rows["sen-plan-qw-02"]["reconciliation_status"] == "plan_only"
    assert rows["sen-plan-qw-02"]["notes"] == "fresh raw note"


@pytest.mark.parametrize(
    ("extractor", "expected_hash"),
    [
        (extract_received_projects, ANNEX_SHA256),
        (extract_quick_wins, MAIN_SHA256),
    ],
)
def test_extraction_rejects_noncanonical_pdf_before_parsing(
    tmp_path, monkeypatch, extractor, expected_hash
) -> None:
    document = tmp_path / "wrong.pdf"
    document.write_bytes(b"%PDF-1.7\nnot the canonical Senegal plan")

    def unexpected_parse(_path):
        pytest.fail("mismatched input reached pdfplumber")

    monkeypatch.setattr("jetp.build_sen_plan_projects.pdfplumber.open", unexpected_parse)

    with pytest.raises(ValueError, match=f"SHA-256 mismatch.*{expected_hash}"):
        extractor(document)
