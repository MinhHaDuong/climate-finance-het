"""Contracts for Indonesia's archived official JETP programme profiles."""

from __future__ import annotations

import csv
from pathlib import Path

from jetp.build_idn_portfolio_pages import parse_portfolio_html

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "jetp"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def archived_page(source_id: str) -> str:
    manifest = read_csv(DATA / "manifest.csv")
    row = next(
        row
        for row in reversed(manifest)
        if row["source_id"] == source_id and row["storage_path"]
    )
    return (DATA / "documents" / row["storage_path"]).read_text(encoding="utf-8")


def test_parser_preserves_two_multi_donor_modalities() -> None:
    rows = parse_portfolio_html(archived_page("idn-portfolio-etp"))

    assert len(rows) == 2
    assert rows[0]["title"] == "South East Asia Energy Transition Partnership (ETP)"
    assert rows[0]["period"] == "10 March 2023 - 31 March 2025"
    assert rows[0]["ipg_entity"] == "Canada and UK"
    assert [row["financing_source"] for row in rows] == [
        "IPG - Canada",
        "IPG - United Kingdom",
    ]
    assert [row["amount_home_currency"] for row in rows] == ["CAD", "GBP"]
    assert [row["amount_home"] for row in rows] == ["2000000", "2000000"]
    assert [row["amount_usd"] for row in rows] == ["1500000", "2492000"]


def test_canonical_portfolio_observations_cover_and_reconcile_every_grant() -> None:
    observations = read_csv(DATA / "idn-portfolio-observations.csv")

    assert len(observations) == 46
    assert len({row["project_id"] for row in observations}) == 44
    assert {row["country"] for row in observations} == {"IDN"}
    assert all(row["document_sha256"] for row in observations)
    assert all(row["matched_event_id"] for row in observations)
    assert {row["reconciliation_status"] for row in observations} <= {
        "matched",
        "amount_mismatch",
    }

    s4i = [row for row in observations if row["project_id"] == "idn-grant-s4i"]
    assert len(s4i) == 1
    assert s4i[0]["amount_home"] == "17100000"
    assert s4i[0]["report_amount_home"] == "17000000"
    assert s4i[0]["reconciliation_status"] == "amount_mismatch"


def test_esmap_profiles_remain_assigned_to_the_right_donors() -> None:
    observations = {
        row["project_id"]: row
        for row in read_csv(DATA / "idn-portfolio-observations.csv")
    }

    canada = observations["idn-grant-esmap-canada"]
    assert canada["ipg_entity"] == "Canada"
    assert canada["amount_home_currency"] == "CAD"
    assert canada["amount_home"] == "2000000"

    uk = observations["idn-grant-esmap-uk"]
    assert uk["ipg_entity"] == "UK"
    assert uk["amount_home_currency"] == "GBP"
    assert uk["amount_home"] == "5000000"
