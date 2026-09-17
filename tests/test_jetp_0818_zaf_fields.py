"""The 0818 extraction carries every register field and names what it drops.

Fast tier by construction: the fixture below is a three-row stand-in for the
744 kB pinned dashboard snapshot, whose byte-for-byte replay already lives in
``test_jetp_0818_zaf_q1_reconciliation.py`` and ``test_jetp_m1a_inventories.py``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

SOURCE_KEYS = (
    "Unique ID",
    "Project Name",
    "Portfolios",
    "Purpose",
    "Priority Areas",
    "Funder/Source",
    "Funding Instrument",
    "Disbursement Channel",
    "Co-Financing: Name",
    "Currency: Pledged",
    "Amount: Pledged",
    "Total US$",
    "Total ZAR",
    "Funding Partners",
    "Implementing Entity",
    "Institutional / South African Partner",
    "Beneficiary",
    "Status",
    "Project Description",
    "Date of Financing Agreement Signed*",
    "End Date",
)


def _material_row(unique_id: str, name: str, **overrides: object) -> dict:
    row = {key: f"{key} value" for key in SOURCE_KEYS}
    row["Unique ID"] = unique_id
    row["Project Name"] = name
    row["Portfolios"] = "Energy"
    row.update(overrides)
    return row


def _fixture_document() -> tuple[str, list[dict]]:
    overall = [
        _material_row("R-1", "First operation", Purpose=""),
        _material_row("R-2", "Second operation", **{"Priority Areas": None}),
        dict.fromkeys(SOURCE_KEYS)
        | {
            "Unique ID": 248,
            "Project Name": None,
            "Portfolios": None,
            "Total US$": 100.5,
            "Total ZAR": 200.5,
        },
    ]
    document = (
        "<html><script>const OVERALL = "
        + json.dumps(overall)
        + ";</script></html>"
    )
    return document, overall


def _policy(document: Path) -> dict:
    return {
        "register_row_count": 2,
        "sources": [
            {
                "role": "register",
                "source_id": "zaf-jet-investment-register-fixture",
                "edition_id": "fixture-edition",
                "document_sha256": hashlib.sha256(document.read_bytes()).hexdigest(),
            }
        ],
    }


def test_excluded_register_rows_reports_the_total_line_without_coercing_it() -> None:
    from jetp.build_zaf_investment_register import (
        excluded_register_rows,
        parse_register_html,
    )

    document, _ = _fixture_document()

    assert len(parse_register_html(document)) == 2

    excluded = excluded_register_rows(document)
    assert len(excluded) == 1
    entry = excluded[0]
    assert entry["raw_index"] == 2
    assert entry["ordinal"] == 3
    assert entry["unique_id_raw"] == 248
    assert isinstance(entry["unique_id_raw"], int)
    assert not isinstance(entry["unique_id_raw"], bool)
    assert entry["project_name_raw"] is None
    assert entry["portfolios_raw"] is None
    assert entry["amount_reported_usd_raw"] == 100.5
    assert entry["amount_reported_zar_raw"] == 200.5


def test_build_rows_carries_all_twenty_one_source_fields(tmp_path: Path) -> None:
    from jetp.build_0818_zaf_q1_reconciliation import FIELDS, build_rows

    document_text, overall = _fixture_document()
    document = tmp_path / "register.html"
    document.write_text(document_text, encoding="utf-8")
    rows = build_rows(document, _policy(document))

    assert len(FIELDS) == 42
    assert FIELDS[21:] == SOURCE_KEYS
    assert len(rows) == 2
    for row in rows:
        assert set(row) == set(FIELDS)
        assert len(row) == 42

    assert rows[0]["Purpose"] == ""
    assert rows[1]["Priority Areas"] == ""
    for row, source in zip(rows, overall[:2], strict=True):
        assert row["Unique ID"] == source["Unique ID"]
        assert row["Project Name"] == source["Project Name"]
        assert row["Beneficiary"] == source["Beneficiary"]


def test_report_names_the_excluded_row_and_its_python_type(tmp_path: Path) -> None:
    from jetp.build_0818_zaf_q1_reconciliation import (
        _report,
        build_rows,
    )
    from jetp.build_zaf_investment_register import excluded_register_rows

    document_text, _ = _fixture_document()
    document = tmp_path / "register.html"
    document.write_text(document_text, encoding="utf-8")
    policy = _policy(document)
    rows = build_rows(document, policy)
    excluded = excluded_register_rows(document_text)

    report = _report(rows, excluded, policy)

    assert "Excluded rows" in report
    assert "248" in report
    assert "int" in report
    assert "100.5" in report
    assert "200.5" in report
    assert "ordinal 3" in report
    assert "raw index 2" in report
