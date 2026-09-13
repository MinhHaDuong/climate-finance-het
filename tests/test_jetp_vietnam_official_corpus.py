"""Coverage contract for Viet Nam's official JETP document series."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "jetp"

CORE_DOCUMENTS = {
    "vnm-rmp-2023-vi",
    "vnm-decision-1009-2023",
    "vnm-decision-458-2026",
}
NEWSLETTERS = {
    f"vnm-moit-newsletter-{issue:02d}-{year_month}"
    for issue, year_month in enumerate(
        (
            "2025-03",
            "2025-04",
            "2025-05",
            "2025-06",
            "2025-07",
            "2025-08",
            "2025-09",
            "2025-10",
            "2025-11",
            "2025-12",
            "2026-01",
            "2026-02",
            "2026-03",
        ),
        1,
    )
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_official_rmp_and_decisions_are_registered_with_exact_dates() -> None:
    sources = {
        row["source_id"]: row
        for row in read_csv(DATA / "sources.csv")
        if row["country"] == "VNM"
    }

    assert CORE_DOCUMENTS <= sources.keys()
    assert sources["vnm-rmp-2023-vi"]["published_date"] == "2023-12-01"
    assert sources["vnm-decision-1009-2023"]["published_date"] == "2023-08-31"
    assert sources["vnm-decision-458-2026"]["published_date"] == "2026-03-20"
    for source_id in CORE_DOCUMENTS:
        assert sources[source_id]["expected_format"] == "pdf"
        assert sources[source_id]["url"].lower().endswith(".pdf")


def test_all_thirteen_moit_newsletters_are_registered_as_one_series() -> None:
    sources = {
        row["source_id"]: row
        for row in read_csv(DATA / "sources.csv")
        if row["country"] == "VNM"
    }

    assert NEWSLETTERS <= sources.keys()
    assert len(NEWSLETTERS) == 13
    assert {sources[source_id]["source_type"] for source_id in NEWSLETTERS} == {
        "progress_update"
    }
    assert sources["vnm-moit-newsletter-01-2025-03"]["published_date"] == (
        "2025-03-31"
    )
    assert sources["vnm-moit-newsletter-13-2026-03"]["published_date"] == (
        "2026-04-13"
    )


def test_official_document_series_has_content_addressed_snapshots() -> None:
    latest: dict[str, dict[str, str]] = {}
    for row in read_csv(DATA / "manifest.csv"):
        if row["country"] == "VNM":
            latest[row["source_id"]] = row

    for source_id in CORE_DOCUMENTS | NEWSLETTERS:
        row = latest[source_id]
        assert row["status"] == "collected"
        assert len(row["sha256"]) == 64
        assert int(row["size_bytes"]) > 0
        assert row["storage_path"].endswith(f"{row['sha256']}.pdf")
        document = DATA / "documents" / row["storage_path"]
        assert document.read_bytes().startswith(b"%PDF-")
        assert hashlib.sha256(document.read_bytes()).hexdigest() == row["sha256"]


def test_decision_1929_has_a_source_and_an_explicit_full_text_gap() -> None:
    sources = {
        row["source_id"]: row
        for row in read_csv(DATA / "sources.csv")
        if row["country"] == "VNM"
    }
    searches = {
        row["search_id"]: row
        for row in read_csv(DATA / "dry-searches.csv")
        if row["country"] == "VNM"
    }

    source_id = "vnm-evn-decision-1929-news-2026"
    search_id = "vnm-search-decision-1929-fulltext-20260912"
    assert source_id in sources
    assert sources[source_id]["source_type"] == "official_news"
    assert searches[search_id]["outcome"] == "partial"
    assert "1929/QĐ-BCT" in searches[search_id]["notes"]
    assert source_id in searches[search_id]["next_step"]
