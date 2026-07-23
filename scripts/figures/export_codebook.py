"""Generate the formal data dictionary (codebook) for the deposit (ticket 0287).

Answers remark R1-19: the layout of climate_finance_corpus.csv is kept (four
logical column groups); the manual-exploration concern is met by a codebook —
per column: type, allowed values, and missingness measured on the real data
(never hand-curated). The codebook ships in the Zenodo package (ticket 0280).

Usage:
    uv run python scripts/figures/export_codebook.py \
        --output deliverables/_shared/tables/codebook.md
"""

import os

import pandas as pd
from _deposit_variables import compute_missingness, render_codebook, transform
from script_io_args import parse_io_args, validate_io
from utils import CATALOGS_DIR, get_logger

log = get_logger("export_codebook")


def main():
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)

    extended_path = os.path.join(CATALOGS_DIR, "extended_works.csv")
    log.info("Reading %s", extended_path)
    df = transform(pd.read_csv(extended_path, low_memory=False))

    md = render_codebook(compute_missingness(df), n_rows=len(df))
    with open(io_args.output, "w", encoding="utf-8") as f:
        f.write(md)
    log.info("Wrote %s (%d rows measured)", io_args.output, len(df))


if __name__ == "__main__":
    main()
