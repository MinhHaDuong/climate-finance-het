"""Contracts for South African JETP secondary-news leads."""

from __future__ import annotations

import csv
from pathlib import Path

from jetp.extract_zaf_news_leads import parse_secondary_news

ROOT = Path(__file__).resolve().parents[1]


def test_parser_keeps_media_coverage_as_non_evidentiary_leads() -> None:
    html = """
    <div data-elementor-type="loop-item"
         class="e-loop-item post-1528 article-category-media-coverage">
      <a aria-label="Open Article" href="https://news.example/grid-story">
        <h3>Grid finance story</h3><time>14.11.2024</time>
      </a>
    </div>
    <div data-elementor-type="loop-item"
         class="e-loop-item post-1589 article-category-press-release">
      <a aria-label="Open Article" href="https://official.example/release.pdf">
        <h3>Official release</h3><time>05.12.2024</time>
      </a>
    </div>
    """

    assert parse_secondary_news(html) == [
        {
            "lead_id": "zaf-news-post-1528",
            "country": "ZAF",
            "published_date": "2024-11-14",
            "publisher": "news.example",
            "title": "Grid finance story",
            "url": "https://news.example/grid-story",
            "lead_type": "secondary_news",
            "topics": "grid;finance",
            "related_project_ids": "",
            "discovery_source_id": "zaf-jet-pmu-news",
            "evidence_role": "lead_only",
            "review_status": "unreviewed",
            "notes": "Listed as Media Coverage by the official JET PMU news hub",
        }
    ]


def test_canonical_leads_are_explicitly_non_evidentiary() -> None:
    path = ROOT / "data" / "jetp" / "news-leads.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    zaf = [row for row in rows if row["country"] == "ZAF"]
    assert zaf
    assert all(row["lead_type"] == "secondary_news" for row in zaf)
    assert all(row["evidence_role"] == "lead_only" for row in zaf)
    assert len({row["lead_id"] for row in zaf}) == len(zaf)

    projects = {
        row["project_id"]
        for row in csv.DictReader(
            (ROOT / "data" / "jetp" / "projects.csv").open(
                encoding="utf-8", newline=""
            )
        )
    }
    attached = [row for row in zaf if row["related_project_ids"]]
    assert attached
    assert all(
        set(row["related_project_ids"].split(";")) <= projects for row in attached
    )
