#!/usr/bin/env python3
"""Summarize publication venues for core works.

Reads:
- $DATA/derived/tables/het_mostcited_50.csv

Writes:
- tables/tab_core_venues_journals.csv
- tables/tab_core_venues_series.csv
- tables/tab_core_venues_all.csv

Usage:
    uv run python scripts/summarize_core_venues.py
"""

import os

import pandas as pd
from _venue_naming import canonical_venue, institution_group, venue_type
from script_io_args import parse_io_args, validate_io
from utils import BASE_DIR, DERIVED_TABLES_DIR, get_logger, save_csv

log = get_logger("summarize_core_venues")


def parse_args():
    io_args, extra = parse_io_args()
    validate_io(output=io_args.output)

    import argparse
    parser = argparse.ArgumentParser(description="Summarize core venue distributions")
    parser.add_argument(
        "--core",
        type=str,
        default=os.path.join(DERIVED_TABLES_DIR, "het_mostcited_50.csv"),
        help="Input core works CSV",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=30,
        help="Top N venues per output table",
    )
    args = parser.parse_args(extra)

    # Primary output is --output; sibling outputs derive from its directory
    args.out_all = io_args.output
    out_dir = os.path.dirname(io_args.output) or os.path.join(BASE_DIR, "deliverables", "_shared", "tables")
    args.out_journals = os.path.join(out_dir, "tab_core_venues_journals.csv")
    args.out_series = os.path.join(out_dir, "tab_core_venues_series.csv")
    args.out_institutions = os.path.join(out_dir, "tab_core_institutions.csv")
    args.out_institution_types = os.path.join(out_dir, "tab_core_institution_by_type.csv")
    return args


def summarize(df, group_cols, top_n):
    out = (
        df.groupby(group_cols, as_index=False)
        .agg(n_core_works=("venue_raw", "size"), cited_by_sum=("cited_by_count", "sum"))
        .sort_values(["n_core_works", "cited_by_sum"], ascending=[False, False])
        .head(top_n)
        .reset_index(drop=True)
    )
    return out


def main():
    args = parse_args()
    if not os.path.exists(args.core):
        raise FileNotFoundError(f"Core file not found: {args.core}")

    df = pd.read_csv(args.core)
    if "journal" not in df.columns:
        raise ValueError("Expected column 'journal' in core file")

    df = df.copy()
    df["venue_raw"] = df["journal"].fillna("").astype(str).str.strip()
    df["venue_raw"] = df["venue_raw"].mask(df["venue_raw"].eq(""), "[missing]")
    df["venue_canonical"] = df["venue_raw"].map(canonical_venue)
    df["venue_type"] = df["venue_canonical"].map(venue_type)
    df["cited_by_count"] = pd.to_numeric(df.get("cited_by_count", 0), errors="coerce").fillna(0).astype(int)

    all_tbl = summarize(df, ["venue_type", "venue_canonical"], args.top)
    journals_tbl = summarize(df[df["venue_type"] == "journal"], ["venue_canonical"], args.top)
    series_tbl = summarize(
        df[df["venue_type"].isin(["working_paper_series", "report_series"])],
        ["venue_type", "venue_canonical"],
        args.top,
    )
    df["institution_group"] = df["venue_canonical"].map(institution_group)
    inst_tbl = (
        df.groupby("institution_group", as_index=False)
        .agg(n_core_works=("venue_raw", "size"), cited_by_sum=("cited_by_count", "sum"))
        .sort_values(["n_core_works", "cited_by_sum"], ascending=[False, False])
        .reset_index(drop=True)
    )
    inst_type_tbl = (
        df.groupby(["institution_group", "venue_type"], as_index=False)
        .agg(n_core_works=("venue_raw", "size"), cited_by_sum=("cited_by_count", "sum"))
        .sort_values(["institution_group", "n_core_works"], ascending=[True, False])
        .reset_index(drop=True)
    )

    save_csv(all_tbl, args.out_all)
    save_csv(journals_tbl, args.out_journals)
    save_csv(series_tbl, args.out_series)
    save_csv(inst_tbl, args.out_institutions)
    save_csv(inst_type_tbl, args.out_institution_types)

    coverage = (
        df.groupby("venue_type", as_index=False)
        .agg(n_core_works=("venue_raw", "size"))
        .sort_values("n_core_works", ascending=False)
    )

    log.info("Done.")
    log.info("  Input rows: %s", f"{len(df):,}")
    log.info("  Venue type coverage:")
    for _, row in coverage.iterrows():
        log.info("    - %s: %d", row['venue_type'], int(row['n_core_works']))
    log.info("  Institution coverage:")
    for _, row in inst_tbl.iterrows():
        log.info("    - %s: %d", row['institution_group'], int(row['n_core_works']))


if __name__ == "__main__":
    main()
