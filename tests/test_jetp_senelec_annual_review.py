"""Bounded review contract for the six Senelec annual-report editions."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from jetp._senelec_annual_review import validate_candidates, validate_editions


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_six_indexed_senelec_editions_have_explicit_bounded_dispositions() -> None:
    """2019--22 stay unretained; only the two retained PDFs are reviewed."""
    rows = read_csv(ROOT / "docs" / "jetp-study" / "0821-senelec-annual-editions.csv")
    validate_editions(rows)

    assert {row["edition"] for row in rows} == {str(year) for year in range(2019, 2025)}
    unretained = [row for row in rows if int(row["edition"]) < 2023]
    assert {row["raw_disposition"] for row in unretained} == {"index_retained_file_not_retained"}
    assert {row["extraction_disposition"] for row in unretained} == {"not_extracted"}
    reviewed = [row for row in rows if int(row["edition"]) >= 2023]
    assert {row["raw_disposition"] for row in reviewed} == {"raw_retained"}
    assert {row["extraction_disposition"] for row in reviewed} == {"reviewed"}


def test_annual_report_candidates_cannot_merge_with_a_plan_slot_by_similarity() -> None:
    """Names, capacity or geography alone never manufacture a JETP link."""
    editions = read_csv(ROOT / "docs" / "jetp-study" / "0821-senelec-annual-editions.csv")
    candidates = read_csv(ROOT / "docs" / "jetp-study" / "0821-senelec-annual-candidates.csv")
    validate_candidates(candidates, editions)

    assert len(candidates) == 6
    assert {row["candidate_disposition"] for row in candidates} == {"unresolved_no_identity"}
    assert {row["canonical_project_id"] for row in candidates} == {""}
    assert {
        (row["edition"], row["candidate_id"])
        for row in candidates
    } == {
        ("2023", "sen-senelec-2023-best"),
        ("2023", "sen-senelec-2023-brt-solar"),
        ("2023", "sen-senelec-2023-lekela-bess"),
        ("2023", "sen-senelec-2023-pamacel"),
        ("2023", "sen-senelec-2023-padaes-best-crd"),
        ("2024", "sen-senelec-2024-diass-generation"),
    }
