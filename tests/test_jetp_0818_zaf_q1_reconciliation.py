"""The 0818 Q1-2026 extraction preserves register claims as candidates."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_zaf_q1_reconciliation_replays_all_material_rows_without_event_promotion(
    tmp_path: Path,
) -> None:
    from jetp.build_0818_zaf_q1_reconciliation import build_rows, write_outputs

    policy = json.loads((ROOT / "config/jetp-zaf-migration.json").read_text())
    source = next(row for row in policy["sources"] if row["role"] == "register")
    document = ROOT / "data/jetp/documents" / source["storage_path"]
    rows = build_rows(document, policy)

    assert len(rows) == 257
    assert {row["source_id"] for row in rows} == {source["source_id"]}
    assert {row["document_sha256"] for row in rows} == {source["document_sha256"]}
    assert hashlib.sha256(document.read_bytes()).hexdigest() == source["document_sha256"]
    assert {row["disposition"] for row in rows} == {"unadmitted_candidate"}
    assert {row["date_role"] for row in rows} == {
        "register_date_label_retained_not_transition"
    }
    assert all(row["transition_date"] == "" for row in rows)
    assert all(row["payment_amount"] == "" for row in rows)
    assert all(row["eligible_for_account"] == "false" for row in rows)

    output = tmp_path / "0818-zaf-q1-2026-rows.csv"
    report = tmp_path / "0818-zaf-q1-2026-report.md"
    write_outputs(rows, output, report, policy)
    with output.open(encoding="utf-8", newline="") as handle:
        assert list(csv.DictReader(handle)) == rows
    assert "257" in report.read_text(encoding="utf-8")


def test_checked_in_q1_candidate_table_is_the_replayable_result() -> None:
    from jetp.build_0818_zaf_q1_reconciliation import build_rows

    policy = json.loads((ROOT / "config/jetp-zaf-migration.json").read_text())
    source = next(row for row in policy["sources"] if row["role"] == "register")
    expected = build_rows(ROOT / "data/jetp/documents" / source["storage_path"], policy)
    with (ROOT / "docs/jetp-study/0818-zaf-q1-2026-rows.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        assert list(csv.DictReader(handle)) == expected
