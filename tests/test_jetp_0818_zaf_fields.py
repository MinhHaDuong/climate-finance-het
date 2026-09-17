"""The 0818 extraction carries every register field and names what it drops.

Behaviour is pinned on a three-row fixture standing in for the 744 kB dashboard
snapshot; only the last test reads the pinned snapshot itself, to check that the
shipped sidecar is its replayable result and joins the frozen rows table 1:1 —
the same shape, and the same tier, as ``test_jetp_0818_zaf_q1_reconciliation.py``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from jetp.build_0818_zaf_q1_reconciliation import (
    SOURCE_FIELDS as SOURCE_KEYS,
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


def test_sidecar_table_carries_all_twenty_one_source_fields(tmp_path: Path) -> None:
    """The register's own 21 fields ride in the sidecar, keyed by ``ordinal``.

    They are deliberately not columns of ``FIELDS``: the reconciled CSV is a
    content-hashed input of the 0822 comparative freeze, so widening it would
    mutate a frozen artifact.  The pin below is therefore two-sided — 21 source
    columns in the sidecar, and the derived table left at its frozen width.
    """
    from jetp.build_0818_zaf_q1_reconciliation import (
        FIELD_TABLE_FIELDS,
        FIELDS,
        build_field_rows,
        build_rows,
    )

    document_text, overall = _fixture_document()
    document = tmp_path / "register.html"
    document.write_text(document_text, encoding="utf-8")
    policy = _policy(document)
    rows = build_rows(document, policy)
    field_rows = build_field_rows(document, policy)

    assert len(FIELDS) == 21
    assert len(SOURCE_KEYS) == 21
    assert not set(FIELDS) & set(SOURCE_KEYS)
    assert FIELD_TABLE_FIELDS == ("ordinal",) + SOURCE_KEYS
    assert len(field_rows) == len(rows) == 2
    for field_row in field_rows:
        assert set(field_row) == set(FIELD_TABLE_FIELDS)
        assert len(field_row) == 22

    # The join key is shared, so the two tables line up 1:1 by construction.
    assert [field_row["ordinal"] for field_row in field_rows] == [
        row["ordinal"] for row in rows
    ]

    assert field_rows[0]["Purpose"] == ""
    assert field_rows[1]["Priority Areas"] == ""
    for field_row, source in zip(field_rows, overall[:2], strict=True):
        assert field_row["Unique ID"] == source["Unique ID"]
        assert field_row["Project Name"] == source["Project Name"]
        assert field_row["Beneficiary"] == source["Beneficiary"]


def test_write_field_table_round_trips_the_sidecar(tmp_path: Path) -> None:
    from jetp.build_0818_zaf_q1_reconciliation import (
        FIELD_TABLE_FIELDS,
        build_field_rows,
        write_field_table,
    )

    document_text, _ = _fixture_document()
    document = tmp_path / "register.html"
    document.write_text(document_text, encoding="utf-8")
    field_rows = build_field_rows(document, _policy(document))

    sidecar = tmp_path / "0818-zaf-q1-2026-fields.csv"
    write_field_table(field_rows, sidecar)
    with sidecar.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert tuple(reader.fieldnames or ()) == FIELD_TABLE_FIELDS
        assert list(reader) == field_rows


def test_checked_in_sidecar_replays_and_joins_the_frozen_rows_table() -> None:
    """The shipped sidecar is the replayable result and joins the frozen CSV 1:1."""
    from jetp.build_0818_zaf_q1_reconciliation import build_field_rows

    policy = json.loads((ROOT / "config/jetp-zaf-migration.json").read_text())
    source = next(item for item in policy["sources"] if item["role"] == "register")
    expected = build_field_rows(
        ROOT / "data/jetp/documents" / source["storage_path"], policy
    )
    with (ROOT / "docs/jetp-study/0818-zaf-q1-2026-fields.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        shipped = list(csv.DictReader(handle))
    assert shipped == expected
    assert len(shipped) == 257

    with (ROOT / "docs/jetp-study/0818-zaf-q1-2026-rows.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        frozen = list(csv.DictReader(handle))
    assert [row["ordinal"] for row in shipped] == [row["ordinal"] for row in frozen]
    assert [row["Unique ID"] for row in shipped] == [
        row["official_unique_id"] for row in frozen
    ]


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


def test_excluded_section_reads_portfolios_from_its_own_raw_field() -> None:
    """`Project Name` and `Portfolios` are two fields, so they render from two.

    The pinned snapshot leaves both ``None`` on the aggregate line, which makes
    a single-source rendering indistinguishable from a correct one on today's
    data.  The entry below therefore carries two distinct non-``None`` values.
    """
    from jetp.build_0818_zaf_q1_reconciliation import _excluded_section

    excluded = [
        {
            "raw_index": 2,
            "ordinal": 3,
            "unique_id_raw": 248,
            "project_name_raw": "Overall total",
            "portfolios_raw": "All portfolios",
            "amount_reported_usd_raw": 100.5,
            "amount_reported_zar_raw": 200.5,
        }
    ]

    section = "\n".join(_excluded_section([], excluded))

    assert "Overall total" in section
    assert "All portfolios" in section
