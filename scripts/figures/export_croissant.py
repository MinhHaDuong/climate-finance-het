"""Emit the Croissant (MLCommons JSON-LD) description of the deposit (0354).

A second serialisation of the same column contract that produces
`datapackage.json`, for ML consumers that index datasets by field. Croissant
carries a checksum, so this reads the whole CSV where the Frictionless emitter
reads only its header.

Usage:
    uv run python scripts/figures/export_croissant.py \
        --input data/products/climate_finance_corpus.csv \
        --output data/products/croissant.json
"""

import argparse
import json
import os
import sys

from _deposit_schema import (
    DEPOSIT_VERSION,
    count_rows,
    read_header,
    render_croissant,
)
from _deposit_variables import check_columns
from script_io_args import parse_io_args, validate_io
from utils import get_logger

log = get_logger("export_croissant")


def main() -> None:
    io_args, extra = parse_io_args()
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=DEPOSIT_VERSION,
                        help="Dataset version recorded in the description")
    opts = parser.parse_args(extra)

    if not io_args.input:
        log.error("--input <deposit csv> is required to describe the shipped file")
        sys.exit(2)
    os.makedirs(os.path.dirname(io_args.output) or ".", exist_ok=True)
    validate_io(output=io_args.output, inputs=io_args.input)

    csv_path = io_args.input[0]
    columns = read_header(csv_path)
    errors = check_columns(columns)
    if errors:
        for e in errors:
            log.error(e)
        sys.exit(1)

    n_rows = count_rows(csv_path)
    description = render_croissant(columns, opts.version, csv_path, n_rows)

    with open(io_args.output, "w", encoding="utf-8") as f:
        json.dump(description, f, indent=2, ensure_ascii=False)
        f.write("\n")
    log.info("Wrote %s (%d fields, %d rows)", io_args.output,
             len(description["recordSet"][0]["field"]), n_rows)  # type: ignore[index]


if __name__ == "__main__":
    main()
