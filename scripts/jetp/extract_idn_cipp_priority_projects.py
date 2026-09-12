"""Extract the 437 priority-project rows from the Indonesia CIPP 2023 PDF."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import pdfplumber

CIPP_SHA256 = "747283facac512780ad757313c493d1080c39705824e72c4b231e87ecb4102b5"
SOURCE_ID = "idn-cipp-2023-cpr-mirror"

FIELDS = [
    "plan_project_id",
    "country",
    "source_id",
    "technology_group",
    "ordinal",
    "project_name",
    "system",
    "estimated_start",
    "capacity_value",
    "capacity_unit",
    "estimated_investment_usd_mn",
    "natural_retirement_year",
    "estimated_retirement_year",
    "ruptl",
    "canonical_project_id",
    "reconciliation_status",
    "document_sha256",
    "locator",
    "notes",
]

EXPECTED_COUNTS = {
    "transmission": 37,
    "coal_retirement": 2,
    "geothermal": 90,
    "hydro": 158,
    "bioenergy": 33,
    "solar": 64,
    "wind": 53,
}

# Only exact name/capacity matches are linked. Repeated quota rows and bundles remain
# plan-only until an official source identifies the underlying assets.
CANONICAL_MATCHES = {
    ("coal_retirement", 2): "idn-pipe-cirebon-1-retirement",
    ("geothermal", 6): "idn-grant-candi-umbul-telomoyo",
    ("geothermal", 17): "idn-pipe-hululais-1-2",
    ("solar", 3): "idn-pipe-sutami-floating-solar",
    ("solar", 9): "idn-fin-saguling-floating-solar",
    ("wind", 3): "idn-pipe-tanah-laut-wind",
    ("wind", 4): "idn-pipe-tanah-laut-wind",
}


def _text(value: object) -> str:
    return " ".join(str(value or "").split())


def _number(value: str) -> str:
    """Normalise Indonesian decimal commas and thousands separators."""
    value = _text(value)
    if not value or value in {"TBD", "N/A"}:
        return ""
    if re.fullmatch(r"\d+,\d{2}", value):
        return value.replace(",", ".")
    return value.replace(",", "")


def _ordinal(value: object) -> tuple[int, str] | None:
    match = re.fullmatch(r"\s*(\d+)\s*(.*?)\s*", str(value or ""))
    if not match:
        return None
    return int(match.group(1)), match.group(2)


def _record(
    group: str,
    ordinal: int,
    name: str,
    system: str,
    start: str,
    capacity: str,
    *,
    investment: str = "",
    natural_retirement: str = "",
    early_retirement: str = "",
    ruptl: str = "",
) -> dict[str, str]:
    canonical = CANONICAL_MATCHES.get((group, ordinal), "")
    appendix = {
        "transmission": "10.1",
        "coal_retirement": "10.2",
        "geothermal": "10.3",
        "hydro": "10.4",
        "bioenergy": "10.5",
        "solar": "10.6",
        "wind": "10.7",
    }[group]
    return {
        "plan_project_id": f"idn-cipp-{group.replace('_', '-')}-{ordinal:03d}",
        "country": "IDN",
        "source_id": SOURCE_ID,
        "technology_group": group,
        "ordinal": str(ordinal),
        "project_name": _text(name),
        "system": _text(system),
        "estimated_start": _text(start),
        "capacity_value": _number(capacity),
        "capacity_unit": "km" if group == "transmission" else "MW",
        "estimated_investment_usd_mn": _number(investment),
        "natural_retirement_year": _text(natural_retirement),
        "estimated_retirement_year": _text(early_retirement),
        "ruptl": _text(ruptl),
        "canonical_project_id": canonical,
        "reconciliation_status": "matched" if canonical else "plan_only",
        "document_sha256": CIPP_SHA256,
        "locator": f"Appendix {appendix}, row {ordinal}",
        "notes": "CIPP priority-project line; plan values are not financing events",
    }


def _is_blank(row: list[object]) -> bool:
    return not any(_text(cell) for cell in row)


def _transmission_rows(tables: list[list[list[object]]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for table in tables:
        for index, row in enumerate(table):
            numbered = _ordinal(row[0])
            if numbered is None:
                continue
            ordinal, _ = numbered
            before: list[list[object]] = []
            cursor = index - 1
            if (
                cursor >= 0
                and not _is_blank(table[cursor])
                and _ordinal(table[cursor][0]) is None
            ):
                previous_has_investment = any(
                    _text(table[cursor][column]) for column in (7, 8)
                )
                previous_has_system = bool(_text(table[cursor][2]))
                if previous_has_investment or previous_has_system:
                    before.insert(0, table[cursor])
                    cursor -= 1
                    # A system fragment immediately before a numbered row belongs to
                    # that row, but the name above it may finish the preceding row.
                    if not previous_has_system:
                        while cursor >= 0 and not _is_blank(table[cursor]):
                            if _ordinal(table[cursor][0]) is not None:
                                break
                            before.insert(0, table[cursor])
                            cursor -= 1
            after: list[list[object]] = []
            cursor = index + 1
            while cursor < len(table) and not _is_blank(table[cursor]):
                if _ordinal(table[cursor][0]) is not None:
                    break
                has_investment = any(_text(table[cursor][column]) for column in (7, 8))
                has_system = bool(_text(table[cursor][2]))
                current_has_system = bool(_text(row[2]))
                if has_investment or (has_system and current_has_system):
                    break
                after.append(table[cursor])
                cursor += 1
            group = [*before, row, *after]
            name = " ".join(_text(item[1]) for item in group if _text(item[1]))
            system = "-".join(_text(item[2]) for item in group if _text(item[2]))
            investments = [
                _text(item[column])
                for item in group
                for column in (7, 8)
                if len(item) > column and _text(item[column])
            ]
            output.append(
                _record(
                    "transmission",
                    ordinal,
                    name,
                    system,
                    _text(row[3]),
                    _text(row[6]),
                    investment=investments[0] if investments else "",
                    ruptl=_text(row[10]),
                )
            )
    return output


def _coal_rows(table: list[list[object]]) -> list[dict[str, str]]:
    output = []
    for row in table:
        numbered = _ordinal(row[0])
        if numbered is None:
            continue
        ordinal, _ = numbered
        output.append(
            _record(
                "coal_retirement",
                ordinal,
                _text(row[1]),
                _text(row[2]),
                _text(row[6]) + _text(row[8]),
                _text(row[9]),
                investment=_text(row[12]),
                natural_retirement=_text(row[3]),
                early_retirement=_text(row[6]) + _text(row[8]),
            )
        )
    return output


def _standard_rows(
    table: list[list[object]],
    group: str,
    *,
    name_index: int,
    system_index: int,
    start_index: int,
    capacity_index: int,
) -> list[dict[str, str]]:
    output = []
    for row in table:
        numbered = _ordinal(row[0])
        if numbered is None:
            continue
        ordinal, prefix = numbered
        name = prefix + _text(row[name_index])
        ruptl = next(
            (_text(cell) for cell in reversed(row) if _text(cell) in {"YES", "NO"}),
            "",
        )
        output.append(
            _record(
                group,
                ordinal,
                name,
                _text(row[system_index]),
                _text(row[start_index]),
                _text(row[capacity_index]),
                ruptl=ruptl,
            )
        )
    return output


def extract_priority_projects(pdf_path: Path) -> list[dict[str, str]]:
    """Return every numbered row in CIPP appendices 10.1 through 10.7."""
    rows: list[dict[str, str]] = []
    with pdfplumber.open(pdf_path) as pdf:
        tables = {page: pdf.pages[page - 1].extract_tables() for page in range(282, 301)}
        rows.extend(_transmission_rows([tables[page][0] for page in (282, 283, 284)]))
        rows.extend(_coal_rows(tables[285][0]))
        for page, table_index in [(285, 1), (286, 0), (287, 0), (288, 0)]:
            rows.extend(
                _standard_rows(
                    tables[page][table_index],
                    "geothermal",
                    name_index=2,
                    system_index=4,
                    start_index=7,
                    capacity_index=10,
                )
            )
        for page, table_index in [
            (288, 1),
            (289, 0),
            (290, 0),
            (291, 0),
            (292, 0),
            (293, 0),
            (294, 0),
        ]:
            rows.extend(
                _standard_rows(
                    tables[page][table_index],
                    "hydro",
                    name_index=2,
                    system_index=4,
                    start_index=7,
                    capacity_index=10,
                )
            )
        rows.extend(
            _standard_rows(
                tables[294][2],
                "bioenergy",
                name_index=1,
                system_index=3,
                start_index=7,
                capacity_index=9,
            )
        )
        rows.extend(
            _standard_rows(
                tables[295][0],
                "bioenergy",
                name_index=2,
                system_index=4,
                start_index=7,
                capacity_index=10,
            )
        )
        for page in (296, 297, 298):
            rows.extend(
                _standard_rows(
                    tables[page][0],
                    "solar",
                    name_index=1,
                    system_index=2,
                    start_index=3,
                    capacity_index=6,
                )
            )
        for page in (299, 300):
            rows.extend(
                _standard_rows(
                    tables[page][0],
                    "wind",
                    name_index=2,
                    system_index=4,
                    start_index=7,
                    capacity_index=10,
                )
            )

    by_group: dict[str, list[int]] = {}
    for row in rows:
        by_group.setdefault(row["technology_group"], []).append(int(row["ordinal"]))
    actual = {group: len(ordinals) for group, ordinals in by_group.items()}
    if actual != EXPECTED_COUNTS:
        raise ValueError(f"unexpected CIPP project counts: {actual!r}")
    for group, count in EXPECTED_COUNTS.items():
        if sorted(by_group[group]) != list(range(1, count + 1)):
            raise ValueError(f"non-contiguous CIPP ordinals for {group}")
    return rows


def write_csv(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_csv(extract_priority_projects(args.pdf), args.output)


if __name__ == "__main__":
    main()
