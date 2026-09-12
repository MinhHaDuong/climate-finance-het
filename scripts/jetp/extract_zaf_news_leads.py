# WARNING: AI-generated, not human-reviewed
"""Extract secondary-news leads listed by the South African JET PMU.

The resulting rows are discovery aids only.  They are deliberately kept out of
the event evidence model until a primary source corroborates the claim.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from script_io_args import parse_io_args, validate_io

LEAD_FIELDS = (
    "lead_id",
    "country",
    "published_date",
    "publisher",
    "title",
    "url",
    "lead_type",
    "topics",
    "related_project_ids",
    "discovery_source_id",
    "evidence_role",
    "review_status",
    "notes",
)

TOPIC_TERMS = (
    ("grid", ("grid", "transmission")),
    ("finance", ("finance", "funding", "fund ", "investment", "bill", "pledge")),
    ("coal_transition", ("coal", "eskom", "komati")),
    ("municipalities", ("municipal",)),
    ("skills", ("skill", "job", "employment")),
    ("green_hydrogen", ("green hydrogen", "hydrogen")),
    ("electric_vehicles", ("electric vehicle", "new energy vehicle")),
    ("renewable_energy", ("renewable", "solar", "wind")),
)


def _topic_labels(title: str) -> str:
    lowered = title.lower()
    labels = [label for label, terms in TOPIC_TERMS if any(term in lowered for term in terms)]
    return ";".join(labels or ["general"])


def _iso_date(value: str) -> str:
    if not value:
        return ""
    return datetime.strptime(value, "%d.%m.%Y").date().isoformat()


def _related_projects(title: str) -> str:
    """Attach only leads whose title identifies the JET Funding Platform."""
    lowered = title.lower()
    if "funding platform" in lowered or "green pipeline" in lowered:
        return "zaf-register-fr020;zaf-register-uk043"
    return ""


class _NewsCardParser(HTMLParser):
    """Read Elementor loop cards without adding an HTML-parser dependency."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.card: dict[str, str] | None = None
        self.capture = ""
        self.buffer: list[str] = []
        self.rows: list[dict[str, str]] = []

    @staticmethod
    def _attributes(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key: value or "" for key, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = self._attributes(attrs)
        if self.card is None:
            classes = attributes.get("class", "").split()
            is_media_card = (
                tag == "div"
                and attributes.get("data-elementor-type") == "loop-item"
                and "article-category-media-coverage" in classes
            )
            if not is_media_card:
                return
            post_class = next((item for item in classes if item.startswith("post-")), "")
            self.card = {
                "post_id": post_class.removeprefix("post-"),
                "url": "",
                "title": "",
                "published_date": "",
            }
            self.depth = 1
            return

        if tag == "div":
            self.depth += 1
        if tag == "a" and attributes.get("aria-label") == "Open Article":
            self.card["url"] = attributes.get("href", "")
        if tag in {"h3", "time"}:
            self.capture = tag
            self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.card is not None and self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.card is None:
            return
        if tag == self.capture:
            value = " ".join("".join(self.buffer).split())
            field = "title" if tag == "h3" else "published_date"
            self.card[field] = value
            self.capture = ""
            self.buffer = []
        if tag != "div":
            return
        self.depth -= 1
        if self.depth:
            return
        card = self.card
        self.card = None
        if not all(card.get(field) for field in ("post_id", "title", "url")):
            return
        hostname = urlparse(card["url"]).hostname or ""
        self.rows.append(
            {
                "lead_id": f"zaf-news-post-{card['post_id']}",
                "country": "ZAF",
                "published_date": _iso_date(card["published_date"]),
                "publisher": hostname.removeprefix("www."),
                "title": card["title"],
                "url": card["url"],
                "lead_type": "secondary_news",
                "topics": _topic_labels(card["title"]),
                "related_project_ids": _related_projects(card["title"]),
                "discovery_source_id": "zaf-jet-pmu-news",
                "evidence_role": "lead_only",
                "review_status": "unreviewed",
                "notes": "Listed as Media Coverage by the official JET PMU news hub",
            }
        )


def parse_secondary_news(html: str) -> list[dict[str, str]]:
    """Return secondary media cards in source order."""
    parser = _NewsCardParser()
    parser.feed(html)
    parser.close()
    return parser.rows


def latest_material_path(manifest: Path, storage_root: Path, source_id: str) -> Path:
    """Resolve the newest stored material observation for ``source_id``."""
    with manifest.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in reversed(rows):
        if row["source_id"] == source_id and row["storage_path"]:
            return storage_root / row["storage_path"]
    raise ValueError(f"no material manifest row for {source_id}")


def main(argv: list[str] | None = None) -> None:
    """Extract the latest official hub's secondary-news leads to CSV."""
    io_args, extra = parse_io_args(argv)
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", required=True)
    parser.add_argument("--source-id", default="zaf-jet-pmu-news")
    args = parser.parse_args(extra)
    if not io_args.input or len(io_args.input) != 1:
        parser.error("exactly one --input manifest is required")
    validate_io(output=io_args.output, inputs=io_args.input)
    source = latest_material_path(
        Path(io_args.input[0]), Path(args.storage_root), args.source_id
    )
    rows = parse_secondary_news(source.read_text(encoding="utf-8"))
    output = Path(io_args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=LEAD_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
