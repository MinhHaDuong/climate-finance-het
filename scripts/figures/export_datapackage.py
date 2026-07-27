"""Emit the Frictionless Data Package descriptor for the deposit (ticket 0354).

The descriptor turns every value-level claim the codebook publishes — types,
enumerations, ranges — into constraints `frictionless validate` checks against
the *written* CSV. Ships in the Zenodo package beside the data it describes.

Only the header of the input CSV is read: the descriptor must describe the file
as shipped, so an optional column absent from a build gets no field.

Usage:
    uv run python scripts/figures/export_datapackage.py \
        --input data/products/climate_finance_corpus.csv \
        --output data/products/datapackage.json
"""

import argparse
import json
import os
import sys

from _deposit_schema import DEPOSIT_VERSION, read_header, render_datapackage
from _deposit_variables import check_columns
from script_io_args import parse_io_args, validate_io
from utils import get_logger

log = get_logger("export_datapackage")


def main() -> None:
    io_args, extra = parse_io_args()
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=DEPOSIT_VERSION,
                        help="Dataset version recorded in the descriptor")
    opts = parser.parse_args(extra)

    if not io_args.input:
        log.error("--input <deposit csv> is required to describe the shipped file")
        sys.exit(2)
    os.makedirs(os.path.dirname(io_args.output) or ".", exist_ok=True)
    validate_io(output=io_args.output, inputs=io_args.input)

    columns = read_header(io_args.input[0])

    # The same drift check export_deposit.py runs at write time. A descriptor
    # generated from an off-contract CSV would publish the drift instead of
    # catching it.
    errors = check_columns(columns)
    if errors:
        for e in errors:
            log.error(e)
        sys.exit(1)

    descriptor = render_datapackage(columns, opts.version)
    n_fields = len(descriptor["resources"][0]["schema"]["fields"])  # type: ignore[index]

    with open(io_args.output, "w", encoding="utf-8") as f:
        json.dump(descriptor, f, indent=2, ensure_ascii=False)
        f.write("\n")
    log.info("Wrote %s (%d fields, version %s)",
             io_args.output, n_fields, opts.version)


if __name__ == "__main__":
    main()
