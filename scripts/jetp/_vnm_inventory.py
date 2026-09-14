"""Extract the bounded English RMP inventories as source positions, not identities.

The PDF prints landscape tables rotated within portrait pages. Ruled table
columns are therefore logical rows. Rotate character coordinates for reading,
retain every cell and its wrapped wording, and read ordinals only in their cell.
This is a hash/version-bound transcription: PDF character decoding and whitespace
reconstruction are not a facsimile. The saved PDF remains the original evidence.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE_SHA256 = "b145af2e7f4a441dc87d7ec2d99a29e1e6d7b265406d398dd64013dd4560733c"
PARSER_VERSION = "pdfplumber-0.11.9;vnm-ruled-rotated-v1"
BOUNDARIES = {"I.1": (155, 158, 37), "I.2": (159, 174, 181), "II": (175, 186, 61)}
# Reviewed examples only; unknown is preferable to speculative named identities.
NAMED_ROWS = {("I.1", n) for n in (*range(1, 6), *range(8, 28))}
PROGRAMME_ROWS = {("I.1", n) for n in (6, 7, *range(28, 37))} | {("I.2", 1)}


def assemble_inventory(
    fragments: list[dict], *, require_complete: bool = True
) -> list[dict]:
    """Assemble explicit ordinal cells and optional page continuations losslessly."""
    rows: list[dict] = []
    for fragment in fragments:
        cells = fragment["cells"]
        annex = fragment["annex"]
        page = fragment["page"]
        ordinal = cells[0].strip()
        if ordinal:
            if not ordinal.isdecimal():
                raise ValueError(f"Invalid ordinal cell: {ordinal!r}")
            rows.append(
                {
                    "inventory_id": f"vnm-rmp-2023:annex-{annex}:{int(ordinal):03d}",
                    "annex": annex,
                    "ordinal": int(ordinal),
                    "pages": [page],
                    "printed_pages": [page - 16],
                    "source_cells": list(cells),
                    "source_wording": fragment["source_wording"],
                }
            )
        else:
            if (
                not rows
                or rows[-1]["annex"] != annex
                or page != rows[-1]["pages"][-1] + 1
            ):
                raise ValueError("Orphan or nonconsecutive inventory continuation")
            row = rows[-1]
            if len(cells) != len(row["source_cells"]):
                raise ValueError("Continuation changed cell count")
            row["pages"].append(page)
            row["printed_pages"].append(page - 16)
            row["source_wording"] += "\n\f\n" + fragment["source_wording"]
            row["source_cells"] = [
                a + ("\n" if a and b else "") + b
                for a, b in zip(row["source_cells"], cells)
            ]
    for row in rows:
        key = (row["annex"], row["ordinal"])
        row["classification"] = (
            "programme"
            if key in PROGRAMME_ROWS or row["annex"] == "II"
            else "named"
            if key in NAMED_ROWS
            else "unknown"
        )
        row["locator"] = (
            f"Annex {row['annex']}; PDF pages {','.join(map(str, row['pages']))}; printed pages {','.join(map(str, row['printed_pages']))}; ordinal {row['ordinal']}"
        )
    keys = [(r["annex"], r["ordinal"]) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate inventory ordinal")
    if require_complete:
        expected = [
            (annex, n)
            for annex, (_, _, count) in BOUNDARIES.items()
            for n in range(1, count + 1)
        ]
        if keys != expected:
            raise ValueError("English RMP inventory is incomplete or out of order")
    return rows


def _cell_text(page, bbox) -> str:
    """Decode characters in a ruled cell using its physical bounds."""
    from pdfplumber.utils import extract_text

    chars = []
    for char in page.chars:
        if (
            bbox[0] <= (char["x0"] + char["x1"]) / 2 < bbox[2]
            and bbox[1] <= (char["top"] + char["bottom"]) / 2 < bbox[3]
        ):
            chars.append(
                dict(
                    char,
                    x0=page.height - char["bottom"],
                    x1=page.height - char["top"],
                    top=char["x0"],
                    bottom=char["x1"],
                    upright=True,
                )
            )
    return extract_text(chars, x_tolerance=3, y_tolerance=3)


def extract_inventory(pdf: Path) -> list[dict]:
    """Extract all 279 rows from the selected immutable English RMP only."""
    import pdfplumber

    if hashlib.sha256(pdf.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Inventory extractor requires the pinned English RMP bytes")
    if pdfplumber.__version__ != "0.11.9":
        raise ValueError("Inventory extractor requires pdfplumber 0.11.9")
    fragments = []
    with pdfplumber.open(pdf) as document:
        for annex, (first, last, _) in BOUNDARIES.items():
            for number in range(first, last + 1):
                page = document.pages[number - 1]
                tables = page.find_tables()
                if len(tables) != 1:
                    raise ValueError(f"Expected one ruled table on PDF page {number}")
                table = tables[0]
                for column in table.columns:
                    # Merged full-width cells are section headings, not rows.
                    if column.cells[-1] is None:
                        continue
                    cells = [
                        _cell_text(page, box) if box else ""
                        for box in reversed(column.cells)
                    ]
                    if cells[0].startswith("No"):
                        continue
                    if cells[0] and not cells[0].isdecimal():
                        raise ValueError(
                            f"Unexpected ordinal on PDF page {number}: {cells[0]!r}"
                        )
                    fragments.append(
                        {
                            "annex": annex,
                            "page": number,
                            "cells": cells,
                            "source_wording": _cell_text(page, column.bbox),
                        }
                    )
    return assemble_inventory(fragments)
