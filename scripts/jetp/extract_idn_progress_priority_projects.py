"""Extract every priority-project row from the Indonesia JETP Progress Report 2025."""

from __future__ import annotations

import argparse
from pathlib import Path

import pdfplumber

try:
    from jetp.extract_idn_cipp_priority_projects import (
        _number,
        _ordinal,
        _text,
        write_csv,
    )
except ModuleNotFoundError:  # Support direct execution from scripts/jetp.
    from extract_idn_cipp_priority_projects import (  # type: ignore[no-redef]
        _number,
        _ordinal,
        _text,
        write_csv,
    )

PROGRESS_SHA256 = "74fb460fd09e76607e3cff308f5ba2754f2ebd91b0c9b7613c1a041e7b361162"
SOURCE_ID = "idn-jetp-progress-report-2025"

EXPECTED_COUNTS = {
    "energy_efficiency": 13,
    "transmission": 340,
    # Counts are physical data rows, not the highest printed row number. The
    # report repeats hydro labels 110--119 and row 48 in two other tables; it
    # also skips geothermal/dispatchable row 49 and solar row 281.
    "hydro": 183,
    "geothermal": 134,
    "bioenergy": 58,
    "other_dispatchable": 70,
    "solar": 281,
    "wind": 55,
    "supply_chain": 8,
}

TABLE_NUMBERS = {
    "energy_efficiency": "1",
    "transmission": "2",
    "hydro": "3",
    "geothermal": "4",
    "bioenergy": "5",
    "other_dispatchable": "6",
    "solar": "7",
    "wind": "8",
    "supply_chain": "9",
}

CANONICAL_MATCHES = {
    ("energy_efficiency", 1): "idn-fin-mrt-east-west",
    ("energy_efficiency", 3): "idn-pipe-rsud-energy-efficiency",
    ("hydro", 73): "idn-monitor-cihaur-talaga-micro-hydro",
    ("hydro", 75): "idn-monitor-cihaur-talaga-micro-hydro",
    ("geothermal", 5): "idn-grant-patuha-2",
    ("geothermal", 18): "idn-pipe-hululais-1-2",
    ("geothermal", 19): "idn-pipe-hululais-1-2",
    ("solar", 21): "idn-fin-saguling-floating-solar",
    ("solar", 29): "idn-pipe-sutami-floating-solar",
    ("wind", 11): "idn-pipe-tanah-laut-wind",
    ("supply_chain", 3): "idn-pipe-solar-cell-manufacturing",
}


def _green(color: object) -> bool:
    return (
        isinstance(color, tuple)
        and len(color) == 3
        and color[1] > color[0] + 0.08
        and color[1] > color[2] + 0.08
        and color[1] < 0.9
    )


def _overlap(first: tuple[float, ...], second: tuple[float, ...]) -> float:
    x0 = max(first[0], second[0])
    top = max(first[1], second[1])
    x1 = min(first[2], second[2])
    bottom = min(first[3], second[3])
    return max(0.0, x1 - x0) * max(0.0, bottom - top)


def _is_top_priority(page: pdfplumber.page.Page, table, row_index: int) -> bool:
    """Read green cell shading used by the report to mark top-priority rows."""
    cells = table.rows[row_index].cells
    if len(cells) < 2 or cells[1] is None:
        return False
    name_cell = cells[1]
    area = (name_cell[2] - name_cell[0]) * (name_cell[3] - name_cell[1])
    return any(
        _green(rect.get("non_stroking_color"))
        and _overlap(
            name_cell,
            (rect["x0"], rect["top"], rect["x1"], rect["bottom"]),
        )
        > area * 0.5
        for rect in page.rects
    )


def _capacity(value: object) -> str:
    raw = _text(value).replace("*", "")
    normalised = _number(raw)
    return normalised if normalised.replace(".", "", 1).isdigit() else ""


def _record(
    group: str,
    ordinal: int,
    name: str,
    system: str,
    start: str,
    capacity: str,
    top_priority: bool,
    notes: str,
    source_ordinal: int | None = None,
) -> dict[str, str]:
    printed_ordinal = source_ordinal if source_ordinal is not None else ordinal
    canonical = CANONICAL_MATCHES.get((group, ordinal), "")
    if printed_ordinal != ordinal:
        notes += (
            f"; source printed row {printed_ordinal}, normalised physical row {ordinal}"
        )
    return {
        "plan_project_id": f"idn-progress25-{group.replace('_', '-')}-{ordinal:03d}",
        "country": "IDN",
        "source_id": SOURCE_ID,
        "technology_group": group,
        "priority_tier": "top_priority" if top_priority else "priority",
        "ordinal": str(ordinal),
        "project_name": _text(name),
        "system": _text(system),
        "estimated_start": _text(start),
        "capacity_value": _capacity(capacity),
        "capacity_unit": (
            "km" if group == "transmission" else "MW" if capacity else ""
        ),
        "estimated_investment_usd_mn": "",
        "natural_retirement_year": "",
        "estimated_retirement_year": "",
        "ruptl": "",
        "canonical_project_id": canonical,
        "reconciliation_status": "matched" if canonical else "plan_only",
        "document_sha256": PROGRESS_SHA256,
        "locator": (
            f"Appendix 1, table {TABLE_NUMBERS[group]}, printed row {printed_ordinal}"
        ),
        "notes": notes,
    }


def _numbered_table_rows(
    page,
    table,
    group: str,
    offset: int = 0,
) -> list[dict[str, str]]:
    extracted = table.extract()
    output = []
    for row_index, row in enumerate(extracted):
        numbered = _ordinal(row[0])
        if numbered is None:
            continue
        source_ordinal, prefix = numbered
        ordinal = offset + len(output) + 1
        name = prefix + _text(row[1])
        raw_capacity = _text(row[4])
        note = "Progress Report 2025 priority-project line; plan values are not financing events"
        if raw_capacity and not _capacity(raw_capacity):
            note += f"; raw capacity={raw_capacity}"
        output.append(
            _record(
                group,
                ordinal,
                name,
                _text(row[2]),
                _text(row[3]),
                raw_capacity,
                _is_top_priority(page, table, row_index),
                note,
                source_ordinal,
            )
        )
    return output


def _energy_efficiency_rows(page, table) -> list[dict[str, str]]:
    output = []
    for row in table.extract():
        numbered = _ordinal(row[0])
        if numbered is None:
            continue
        ordinal, prefix = numbered
        output.append(
            _record(
                "energy_efficiency",
                ordinal,
                prefix + _text(row[1]),
                "",
                "",
                "",
                False,
                "Progress Report 2025 priority-project line; "
                + _text(row[2]),
            )
        )
    return output


def _supply_chain_rows(page, table) -> list[dict[str, str]]:
    del page
    output = []
    for ordinal, row in enumerate(table.extract()[1:], start=1):
        raw_capacity = _text(row[4])
        output.append(
            _record(
                "supply_chain",
                ordinal,
                _text(row[1]),
                _text(row[3]),
                _text(row[2]),
                "",
                False,
                "Progress Report 2025 priority supply-chain line; "
                f"type={_text(row[0])}; raw capacity={raw_capacity}",
            )
        )
    return output


def extract_priority_projects(pdf_path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    group_counts: dict[str, int] = {}

    def add_numbered(page, table, group: str) -> None:
        extracted = _numbered_table_rows(
            page,
            table,
            group,
            group_counts.get(group, 0),
        )
        rows.extend(extracted)
        group_counts[group] = group_counts.get(group, 0) + len(extracted)

    with pdfplumber.open(pdf_path) as pdf:
        for page_number in (160, 161):
            page = pdf.pages[page_number - 1]
            rows.extend(_energy_efficiency_rows(page, page.find_tables()[0]))
        for page_number in range(162, 179):
            page = pdf.pages[page_number - 1]
            add_numbered(page, page.find_tables()[0], "transmission")
        for page_number in range(179, 186):
            page = pdf.pages[page_number - 1]
            add_numbered(page, page.find_tables()[0], "hydro")
        for page_number in range(186, 191):
            page = pdf.pages[page_number - 1]
            add_numbered(page, page.find_tables()[0], "geothermal")
        for page_number in range(191, 194):
            page = pdf.pages[page_number - 1]
            add_numbered(page, page.find_tables()[0], "bioenergy")
        page = pdf.pages[193 - 1]
        add_numbered(page, page.find_tables()[1], "other_dispatchable")
        for page_number in range(194, 196):
            page = pdf.pages[page_number - 1]
            add_numbered(page, page.find_tables()[0], "other_dispatchable")
        for page_number in range(196, 208):
            page = pdf.pages[page_number - 1]
            add_numbered(page, page.find_tables()[0], "solar")
        for page_number in range(208, 211):
            page = pdf.pages[page_number - 1]
            add_numbered(page, page.find_tables()[0], "wind")
        page = pdf.pages[211 - 1]
        rows.extend(_supply_chain_rows(page, page.find_tables()[0]))

    by_group: dict[str, list[int]] = {}
    for row in rows:
        by_group.setdefault(row["technology_group"], []).append(int(row["ordinal"]))
    actual = {group: len(ordinals) for group, ordinals in by_group.items()}
    if actual != EXPECTED_COUNTS:
        raise ValueError(f"unexpected progress-report project counts: {actual!r}")
    for group, count in EXPECTED_COUNTS.items():
        if sorted(by_group[group]) != list(range(1, count + 1)):
            raise ValueError(f"non-contiguous progress-report ordinals for {group}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_csv(extract_priority_projects(args.pdf), args.output, SOURCE_ID)


if __name__ == "__main__":
    main()
