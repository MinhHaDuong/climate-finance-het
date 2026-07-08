"""Coverage diagnostic for the pre-2007 corpus slice (ticket 0182).

The pre-2007 citation graph is the sparsest slice of the corpus (retro-
indexing skew, grey literature under-referenced). Before reading any
co-citation "separation" as intellectual structure, we measure how thin
the evidence is: how many works, how many carry an outgoing reference
edge at all, the median references per work, and the academic-vs-grey
split. These numbers decide the interpretive regime for the separation
null model (compute_null_separation.py).

Output: content/tables/tab_pre2007_coverage.csv (long format, one
(metric, value) row per statistic), validated by Pre2007CoverageSchema.

Usage:
    uv run python scripts/compute_pre2007_coverage.py \
        --output content/tables/tab_pre2007_coverage.csv

    CLIMATE_FINANCE_DATA=tests/fixtures/smoke \
        uv run python scripts/compute_pre2007_coverage.py \
        --output /tmp/tab_pre2007_coverage.csv
"""

import argparse

import pandas as pd
from pipeline_loaders import (
    load_analysis_config,
    load_refined_citations,
    load_refined_works,
    pre2007_cutoff_year,
)
from schemas import Pre2007CoverageSchema
from script_io_args import parse_io_args, validate_io
from utils import get_logger, normalize_doi

log = get_logger("compute_pre2007_coverage")


def _is_grey(series):
    """Coerce the from_grey provenance column (str '0'/'1'/'True') to bool."""
    return series.astype(str).str.strip().str.lower().isin({"1", "true"})


def compute_coverage(works, cit, cutoff_year):
    """Compute pre-slice coverage metrics as an ordered (metric, value) list."""
    year = pd.to_numeric(works["year"], errors="coerce")
    pre = works[year <= cutoff_year].copy()
    n_works = len(pre)

    pre["doi_norm"] = pre["doi"].apply(normalize_doi)
    has_doi = ~pre["doi_norm"].isin(["", "nan", "none"])
    n_with_doi = int(has_doi.sum())

    src = cit["source_doi"].apply(normalize_doi)
    refs_per_source = src[~src.isin(["", "nan", "none"])].value_counts()
    source_dois = set(refs_per_source.index)

    with_edge = pre["doi_norm"].isin(source_dois) & has_doi
    n_with_edge = int(with_edge.sum())
    share_with_edge = n_with_edge / n_works if n_works else float("nan")

    refs_count = pre["doi_norm"].map(refs_per_source).fillna(0)
    refs_count = refs_count.where(has_doi, other=0)
    median_refs = float(refs_count.median()) if n_works else float("nan")

    grey = _is_grey(pre["from_grey"]) if "from_grey" in pre.columns else pd.Series(
        [False] * n_works, index=pre.index
    )
    n_grey = int(grey.sum())
    n_academic = n_works - n_grey
    share_grey = n_grey / n_works if n_works else float("nan")

    return [
        ("cutoff_year", float(cutoff_year)),
        ("n_works", float(n_works)),
        ("n_with_doi", float(n_with_doi)),
        ("n_with_outgoing_edge", float(n_with_edge)),
        ("share_with_outgoing_edge", share_with_edge),
        ("median_refs_per_work", median_refs),
        ("n_academic", float(n_academic)),
        ("n_grey", float(n_grey)),
        ("share_grey", share_grey),
    ]


def main():
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)
    argparse.ArgumentParser().parse_args(_extra)  # reject unknown flags

    cfg = load_analysis_config()
    cutoff = pre2007_cutoff_year(cfg)
    log.info("Pre-%d coverage diagnostic", cutoff + 1)

    works = load_refined_works()
    cit = load_refined_citations()
    log.info("Loaded %d works, %d citation pairs", len(works), len(cit))

    rows = compute_coverage(works, cit, cutoff)
    for metric, value in rows:
        log.info("  %-26s %s", metric, value)

    df = pd.DataFrame(rows, columns=["metric", "value"])
    Pre2007CoverageSchema.validate(df)
    df.to_csv(io_args.output, index=False)
    log.info("Saved coverage diagnostic -> %s", io_args.output)


if __name__ == "__main__":
    main()
