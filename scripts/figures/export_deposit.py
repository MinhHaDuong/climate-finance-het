"""Prepare data files for the Zenodo deposit.

Reads extended_works.csv (which has quality flags) and writes
climate_finance_corpus.csv with:
- Abstract column dropped (publisher redistribution restrictions)
- Individual flag columns replaced by is_flagged/is_protected/flag_reason
- Column from_scispsace renamed to from_scispace if present
- Intermediate columns (doi_norm, etc.) dropped

The column transform and the variables contract live in
scripts/deposit_variables.py (ticket 0279); the output is checked against the
contract at write time so the data paper's variables table cannot drift from
the shipped CSV.

Usage:
    uv run python scripts/figures/export_deposit.py --output FILE
"""

import os
import sys

import pandas as pd
from deposit_variables import check_columns, transform
from script_io_args import parse_io_args, validate_io
from utils import CATALOGS_DIR, get_logger

log = get_logger("export_deposit")


def main():
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)

    os.makedirs(os.path.dirname(io_args.output), exist_ok=True)

    # --- Read extended_works.csv (has quality flags) ---
    extended_path = os.path.join(CATALOGS_DIR, "extended_works.csv")
    log.info("Reading %s", extended_path)
    df = pd.read_csv(extended_path, low_memory=False)
    n_total = len(df)
    log.info("Read %d rows, %d columns", n_total, len(df.columns))

    # --- Transform to the deposit column layout ---
    df = transform(df)

    # --- Write ---
    out_path = io_args.output
    df.to_csv(out_path, index=False)
    log.info("Wrote %s (%d rows, %d columns)", out_path, n_total, len(df.columns))

    # --- Verify against the variables contract ---
    errors = check_columns(list(df.columns))

    n_flagged = df["is_flagged"].sum() if "is_flagged" in df.columns else 0
    n_protected = df["is_protected"].sum() if "is_protected" in df.columns else 0
    if "is_flagged" in df.columns and "is_protected" in df.columns:
        n_removed = ((df["is_flagged"]) & (~df["is_protected"])).sum()
    else:
        n_removed = 0
    n_kept = n_total - n_removed
    log.info("Flagged: %d, Protected: %d, Removed: %d, Kept: %d",
             n_flagged, n_protected, n_removed, n_kept)

    if errors:
        for e in errors:
            log.error(e)
        log.error("Deposit columns drifted from scripts/deposit_variables.py — "
                  "update the contract (and the data paper table regenerates).")
        sys.exit(1)

    log.info("Deposit files ready in %s", os.path.dirname(io_args.output))


if __name__ == "__main__":
    main()
