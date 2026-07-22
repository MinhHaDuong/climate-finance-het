#!/usr/bin/env python3
"""Compute the per-document reference-count distribution (ticket 0285).

Answers the RDJ-26561 R&R referee (remark R1-13), who asks whether per-document
reference counts were recorded and predicts empty/aberrant reference lists in
OpenAlex. This script computes that distribution from the shipped citation edge
list; ticket 0277 writes the prose interpreting it.

Semantics (see ticket 0285 Plan):
  ``refined_citations.csv`` is an edge list — one row per reference. A document
  with zero references has NO rows. Its count therefore comes from an outer join
  onto the full DOI universe (refined_works), fillna(0), never from the edge
  list alone. Documents with no DOI cannot be a ``source_doi``; they are reported
  separately ("excluded from the citation graph"), never folded into "zero
  references" (methodological honesty).

Inputs:
  - refined_works.csv (via load_refined_works or --input[0])
  - refined_citations.csv (via load_refined_citations or --input[1])

Outputs:
  - deliverables/_shared/tables/tab_reference_counts.csv (long metric/value)

Usage:
    uv run python scripts/analysis/compute_reference_counts.py \
        --output deliverables/_shared/tables/tab_reference_counts.csv
"""

import os

import numpy as np
import pandas as pd
from pipeline_io import save_csv
from pipeline_text import normalize_doi_safe
from schemas import ReferenceCountsSchema
from script_io_args import parse_io_args, validate_io
from utils import get_logger

log = get_logger("compute_reference_counts")

# Distribution buckets over the per-document reference count. bucket_0 isolates
# the referee's "empty list" prediction; bucket_100_plus the "aberrant" high tail.
# Percentile-based tail statistics (p5/p95) flag the tails without a magic cutoff.
_TAIL_PERCENTILES = (5, 95)


def compute_reference_counts(
    works: pd.DataFrame, citations: pd.DataFrame
) -> pd.DataFrame:
    """Compute the per-document reference-count distribution.

    Parameters
    ----------
    works : pd.DataFrame
        refined_works-like frame; must contain a ``doi`` column (nullable).
    citations : pd.DataFrame
        refined_citations-like edge list; must contain a ``source_doi`` column
        (one row per reference).

    Returns
    -------
    pd.DataFrame
        Long format with columns ``metric`` (str) and ``value`` (float):
        document totals, the zero-reference headline, the no-DOI exclusion
        count, the six bucket counts (which partition the DOI universe), and
        tail statistics (median / mean / p5 / p95 / max).

    """
    works = works.copy()
    works["doi_norm"] = works["doi"].apply(normalize_doi_safe)

    with_doi = works[works["doi_norm"] != ""]
    n_total = len(works)
    n_with_doi = len(with_doi)
    n_no_doi = n_total - n_with_doi

    # Per-source-document reference count from the edge list. Every source_doi is
    # a member of the DOI universe (guaranteed by load_refined_citations), so
    # value_counts gives the edge count per citing document.
    edge_source = citations["source_doi"].apply(normalize_doi_safe)
    edge_source = edge_source[edge_source != ""]
    per_doc_edges = edge_source.value_counts()

    # Outer-join onto the DOI universe: documents absent from the edge list get 0.
    ref_counts = (
        with_doi["doi_norm"].map(per_doc_edges).fillna(0).astype(int)
    )

    b0 = int((ref_counts == 0).sum())
    b1_5 = int(((ref_counts >= 1) & (ref_counts <= 5)).sum())
    b6_20 = int(((ref_counts >= 6) & (ref_counts <= 20)).sum())
    b21_50 = int(((ref_counts >= 21) & (ref_counts <= 50)).sum())
    b51_100 = int(((ref_counts >= 51) & (ref_counts <= 100)).sum())
    b100_plus = int((ref_counts > 100).sum())

    share_zero = (b0 / n_with_doi) if n_with_doi else np.nan
    if n_with_doi:
        median = float(np.median(ref_counts))
        mean = float(ref_counts.mean())
        p5 = float(np.percentile(ref_counts, _TAIL_PERCENTILES[0]))
        p95 = float(np.percentile(ref_counts, _TAIL_PERCENTILES[1]))
        rmax = float(ref_counts.max())
    else:
        median = mean = p5 = p95 = rmax = np.nan

    rows = [
        ("n_documents_total", float(n_total)),
        ("n_documents_with_doi", float(n_with_doi)),
        ("n_documents_no_doi", float(n_no_doi)),
        ("n_zero_references", float(b0)),
        ("share_zero_references", share_zero),
        ("bucket_0", float(b0)),
        ("bucket_1_5", float(b1_5)),
        ("bucket_6_20", float(b6_20)),
        ("bucket_21_50", float(b21_50)),
        ("bucket_51_100", float(b51_100)),
        ("bucket_100_plus", float(b100_plus)),
        ("ref_count_median", median),
        ("ref_count_mean", mean),
        ("ref_count_p5", p5),
        ("ref_count_p95", p95),
        ("ref_count_max", rmax),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])


def main():
    io_args, _extra = parse_io_args()
    os.makedirs(os.path.dirname(io_args.output) or ".", exist_ok=True)
    validate_io(output=io_args.output)

    inputs = io_args.input or []
    if len(inputs) >= 2:
        log.info("Reading from --input: %s, %s", inputs[0], inputs[1])
        works = pd.read_csv(inputs[0], dtype=str, keep_default_na=False)
        citations = pd.read_csv(inputs[1], dtype=str, keep_default_na=False)
    elif inputs:
        raise SystemExit(
            "compute_reference_counts needs two --input files "
            "(refined_works.csv refined_citations.csv) or none."
        )
    else:
        from pipeline_loaders import load_refined_citations, load_refined_works

        works = load_refined_works()
        citations = load_refined_citations()

    result = compute_reference_counts(works, citations)
    ReferenceCountsSchema.validate(result)
    save_csv(result, io_args.output)
    log.info("Wrote %d metrics to %s", len(result), io_args.output)


if __name__ == "__main__":
    main()
