#!/usr/bin/env python3
"""Compute periodised citation coverage for the data paper (ticket 0317).

The data paper's §4 reports how much of the corpus appears as a *citing
source* in the deposited citation network, and how that share moves across
the three periods. The v1.0 prose quoted 27% before 2007 against 47% after
2015 — stale numbers, and quoted without their denominator.

Denominators (this is the whole point of the artifact):

  ``share_covered``          covered / ALL works in the period.
  ``share_covered_of_doi``   covered / works in the period that CARRY A DOI.

Both ship, because they point in opposite directions and only the first
matches the paper's stated definition ("the share of corpus works"). A work
with no DOI can never be matched as a citing source, so conditioning on DOI
carriage hides exactly the population the coverage caveat is about: on corpus
v2 the all-works share rises 40% -> 47% -> 69% while the DOI-bearing share
peaks mid-corpus (88% -> 95% -> 82%), because DOI carriage itself nearly
doubles (46% -> 85%). Reporting only the second reverses the gradient and
contradicts the caveat the paragraph exists to make.

Output: deliverables/_shared/tables/tab_citation_coverage_periods.csv, long
(metric, value) format validated by CitationCoveragePeriodsSchema. Periods
are emitted positionally (p1/p2/p3) with their year bounds as values, so the
labels are reconstructable from a floats-only table.

Usage:
    uv run python scripts/analysis/compute_citation_coverage.py \
        --output deliverables/_shared/tables/tab_citation_coverage_periods.csv
"""

import argparse
import os

import pandas as pd
from pipeline_io import save_csv
from pipeline_loaders import (
    load_analysis_config,
    load_analysis_periods,
    load_refined_works,
)
from pipeline_text import normalize_doi_safe
from schemas import CitationCoveragePeriodsSchema
from script_io_args import parse_io_args, validate_io
from utils import CATALOGS_DIR, get_logger, normalize_doi

log = get_logger("compute_citation_coverage")

CITATIONS_PATH = os.path.join(CATALOGS_DIR, "citations.csv")

_EMPTY_DOI = {"", "nan", "none"}


def _share(numerator, denominator):
    """Percentage on a 0-100 scale, or None when the denominator is empty."""
    return 100.0 * numerator / denominator if denominator else None


def compute_citation_coverage(works, citations, core_threshold, periods=None):
    """Coverage of the citation network over the corpus, by period.

    Parameters
    ----------
    works : pd.DataFrame
        refined_works-like frame with ``doi``, ``year``, ``cited_by_count``.
    citations : pd.DataFrame
        Citation edge list with a ``source_doi`` column. One row per
        reference; a work that cites nothing simply has no rows.
    core_threshold : int
        ``cited_by_count`` at or above which a work belongs to the core subset.
    periods : list[tuple[int, int]] | None
        Inclusive (year_min, year_max) bounds. Defaults to the configured
        periodisation. Works dated outside every period are counted in the
        corpus totals but in no period row.

    Returns
    -------
    pd.DataFrame
        Long (metric, value) table.

    """
    if periods is None:
        periods, _labels = load_analysis_periods()

    works = works.copy()
    works["doi_norm"] = works["doi"].apply(normalize_doi_safe)
    has_doi = ~works["doi_norm"].isin(_EMPTY_DOI)

    source_dois = {
        normalize_doi(d) for d in citations["source_doi"].dropna().unique()
    } - _EMPTY_DOI
    # A work counts as covered only if it carries a DOI *and* that DOI appears
    # as a citing source. Belt and braces, deliberately: empty keys are already
    # stripped from source_dois above, so either guard alone would do. Both are
    # kept because a work with no DOI being counted as covered would invert the
    # coverage gradient this artifact exists to report, and normalize_doi_safe
    # maps several junk forms ("", "nan", "none") onto keys that a future change
    # to either side could reintroduce. The contract — not the mechanism — is
    # pinned by test_a_work_without_a_doi_is_never_counted_as_covered.
    covered = has_doi & works["doi_norm"].isin(source_dois)

    year = pd.to_numeric(works["year"], errors="coerce")
    rows = []

    for i, (lo, hi) in enumerate(periods, start=1):
        in_period = (year >= lo) & (year <= hi)
        n_works = int(in_period.sum())
        n_with_doi = int((in_period & has_doi).sum())
        n_covered = int((in_period & covered).sum())
        # One numerator, two denominators: ``covered`` already implies
        # ``has_doi`` (line above), so the DOI-conditioned share differs from
        # the headline share only in what it divides by.
        rows += [
            (f"p{i}_year_min", float(lo)),
            (f"p{i}_year_max", float(hi)),
            (f"p{i}_n_works", float(n_works)),
            (f"p{i}_n_with_doi", float(n_with_doi)),
            (f"p{i}_n_covered", float(n_covered)),
            (f"p{i}_share_covered", _share(n_covered, n_works)),
            (f"p{i}_share_with_doi", _share(n_with_doi, n_works)),
            (f"p{i}_share_covered_of_doi", _share(n_covered, n_with_doi)),
        ]

    core = works["cited_by_count"].fillna(0).astype(float) >= core_threshold
    n_core = int(core.sum())
    n_core_covered = int((core & covered).sum())
    n_all = len(works)
    n_all_covered = int(covered.sum())

    rows += [
        ("core_threshold", float(core_threshold)),
        ("core_n", float(n_core)),
        ("core_n_covered", float(n_core_covered)),
        ("core_share_covered", _share(n_core_covered, n_core)),
        ("all_n_works", float(n_all)),
        ("all_n_with_doi", float(int(has_doi.sum()))),
        ("all_n_covered", float(n_all_covered)),
        ("all_share_covered", _share(n_all_covered, n_all)),
    ]

    return pd.DataFrame(rows, columns=["metric", "value"])


def main():
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)
    argparse.ArgumentParser().parse_args(_extra)  # reject unknown flags

    cfg = load_analysis_config()
    core_threshold = cfg["clustering"]["cite_threshold"]

    inputs = io_args.input or []
    if inputs:
        works = pd.read_csv(inputs[0], low_memory=False)
    else:
        works = load_refined_works()
    citations_path = inputs[1] if len(inputs) > 1 else CITATIONS_PATH
    citations = pd.read_csv(citations_path, usecols=["source_doi"], low_memory=False)
    log.info("Loaded %d works, %d citation rows", len(works), len(citations))

    df = compute_citation_coverage(works, citations, core_threshold)
    for metric, value in df.itertuples(index=False):
        log.info("  %-26s %s", metric, value)

    CitationCoveragePeriodsSchema.validate(df)
    save_csv(df, io_args.output)
    log.info("Saved citation coverage -> %s", io_args.output)


if __name__ == "__main__":
    main()
