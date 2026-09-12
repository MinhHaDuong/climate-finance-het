"""Build a durable project-by-project source follow-up register."""

import argparse
import csv
from pathlib import Path

FIELDS = [
    "country",
    "project_id",
    "review_status",
    "source_ids",
    "checked_at",
    "query_or_route",
    "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def seed_rows(
    projects_path: Path,
    output_path: Path,
    country: str,
    source_id: str,
) -> list[dict[str, str]]:
    projects = [
        row for row in read_csv(projects_path) if row["country"] == country
    ]
    existing = read_csv(output_path)
    by_key = {(row["country"], row["project_id"]): row for row in existing}

    for project in projects:
        key = (country, project["project_id"])
        if key not in by_key:
            by_key[key] = {
                "country": country,
                "project_id": project["project_id"],
                "review_status": "pending",
                "source_ids": source_id,
                "checked_at": "",
                "query_or_route": "",
                "notes": (
                    "Central portfolio evidence indexed; direct authority, operator, "
                    "report and news routes still require review"
                ),
            }

    return sorted(by_key.values(), key=lambda row: (row["country"], row["project_id"]))


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("country")
    parser.add_argument("source_id")
    parser.add_argument("projects", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_csv(
        seed_rows(args.projects, args.output, args.country, args.source_id),
        args.output,
    )


if __name__ == "__main__":
    main()
