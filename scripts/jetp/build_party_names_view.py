"""Serve reviewed organisation names for the static JETP observatory."""

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build(ledger: Path) -> dict:
    with (ledger / "parties.csv").open(newline="") as stream:
        parties = {row["party_id"]: row for row in csv.DictReader(stream)}
    with (ledger / "party-names.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))

    accepted = [row for row in rows if row["status"] == "accepted"]
    superseded = {row["supersedes"] for row in rows if row["supersedes"]}
    current = [row for row in accepted if row["name_row_id"] not in superseded]
    if any(row["party_id"] not in parties for row in current):
        raise ValueError("A reviewed party name refers to an unknown party")
    preferred = {}
    for row in current:
        if row["form_type"] == "preferred":
            preferred[row["party_id"]] = preferred.get(row["party_id"], 0) + 1
    if any(preferred.get(party_id) != 1 for party_id in parties):
        raise ValueError("A party must have one preferred name in force")
    return {"names": [
        {key: row[key] for key in (
            "party_id", "name", "form_type", "document_id", "line_id", "recorded_at"
        )} | {"country": parties[row["party_id"]]["country"]}
        for row in sorted(current, key=lambda r: (r["party_id"], r["name_row_id"]))
    ]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=ROOT / "data/jetp")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(build(args.ledger), ensure_ascii=False, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
