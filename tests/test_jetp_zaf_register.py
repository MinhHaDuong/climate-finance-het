"""Contracts for extracting South Africa's official JET register."""

from __future__ import annotations

import pytest

from jetp.extract_zaf_investment_register import (
    build_event_records,
    build_project_records,
    parse_register_html,
)


REGISTER_HTML = """
<html><script>
const OVERALL = [
  {
    "Unique ID": "UK001",
    "Project Name": "Grid support",
    "Portfolios": "Electricity",
    "Purpose": "Technical Assistance",
    "Priority Areas": "Grid expansion",
    "Funding Instrument": "Grants",
    "Currency: Pledged": "GBP",
    "Amount: Pledged": 1000000,
    "Total US$": 1250000,
    "Funding Partners": "United Kingdom",
    "Implementing Entity": "NTCSA",
    "Status": "C. Implementation Phase",
    "Project Description": "Technical support",
    "Date of Financing Agreement Signed*": "2025-01-31T00:00:00",
    "End Date": "2026-12-31T00:00:00"
  },
  {
    "Unique ID": "EU002",
    "Project Name": "Municipal preparation",
    "Portfolios": "Municipal",
    "Purpose": "Project preparation",
    "Priority Areas": null,
    "Funding Instrument": "Grants",
    "Currency: Pledged": "EUR",
    "Amount: Pledged": 500000,
    "Total US$": 540000,
    "Funding Partners": "European Union",
    "Implementing Entity": null,
    "Status": "D. Completed",
    "Project Description": null,
    "Date of Financing Agreement Signed*": null,
    "End Date": null
  },
  {"Unique ID": 0, "Project Name": "TOTAL", "Portfolios": null}
];
</script></html>
"""


def test_register_parser_filters_summary_rows_and_preserves_official_ids() -> None:
    rows = parse_register_html(REGISTER_HTML)

    assert [row["Unique ID"] for row in rows] == ["UK001", "EU002"]


def test_register_parser_rejects_duplicate_official_ids() -> None:
    duplicated = REGISTER_HTML.replace(
        '{"Unique ID": 0, "Project Name": "TOTAL", "Portfolios": null}',
        '{"Unique ID": "UK001", "Project Name": "Duplicate", "Portfolios": "Skills"}',
    )

    with pytest.raises(ValueError, match="duplicate Unique ID"):
        parse_register_html(duplicated)


def test_register_rows_become_separate_projects_and_financial_events() -> None:
    rows = parse_register_html(REGISTER_HTML)
    projects = build_project_records(rows, reported_date="2026-03-30")
    events = build_event_records(
        rows,
        source_id="zaf-jet-investment-register-q1-2026",
        document_sha256="abc123",
        reported_date="2026-03-30",
    )

    assert [row["project_id"] for row in projects] == [
        "zaf-register-uk001",
        "zaf-register-eu002",
    ]
    assert events[0]["project_id"] == projects[0]["project_id"]
    assert events[0]["financial_status"] == "signed"
    assert events[0]["event_date"] == "2025-01-31"
    assert events[0]["amount_original"] == "1000000"
    assert events[0]["currency_original"] == "GBP"
    assert events[0]["amount_usd"] == "1250000"

    # A completed implementation is not evidence of a financial disbursement.
    assert events[1]["financial_status"] == "approved"
    assert events[1]["event_date"] == "2026-03-30"
    assert events[1]["locator"] == "Overall - Data, Unique ID EU002"
