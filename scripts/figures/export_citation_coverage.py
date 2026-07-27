"""Render the citation-coverage table for Quarto includes.

Reads: deliverables/_shared/tables/tab_citation_coverage_periods.csv
Writes: deliverables/_shared/tables/tab_citation_coverage.md

This script renders; it does not measure. The metric — and in particular its
denominator — is defined once in scripts/analysis/compute_citation_coverage.py
(ticket 0317). Recomputing it here is what let the v1.0 prose numbers drift
away from the artifact.

Usage:
    uv run python scripts/figures/export_citation_coverage.py \
        --input deliverables/_shared/tables/tab_citation_coverage_periods.csv \
        --output deliverables/_shared/tables/tab_citation_coverage.md
"""

import os

import pandas as pd
from script_io_args import parse_io_args, validate_io
from utils import BASE_DIR, get_logger

log = get_logger("export_citation_coverage")

TABLES_DIR = os.path.join(BASE_DIR, "deliverables", "_shared", "tables")
DEFAULT_INPUT = os.path.join(TABLES_DIR, "tab_citation_coverage_periods.csv")


def _period_count(metrics):
    """How many p<i>_ period blocks the artifact carries."""
    i = 1
    while f"p{i}_n_works" in metrics:
        i += 1
    return i - 1


def render_table(metrics):
    """Render the coverage markdown from the long (metric, value) mapping."""
    lines = [
        "| Period | Total works | With citation data | Coverage |",
        "|--------|------------:|-------------------:|---------:|",
    ]
    for i in range(1, _period_count(metrics) + 1):
        label = f"{int(metrics[f'p{i}_year_min'])}–{int(metrics[f'p{i}_year_max'])}"
        total = int(metrics[f"p{i}_n_works"])
        with_data = int(metrics[f"p{i}_n_covered"])
        pct = metrics[f"p{i}_share_covered"]
        lines.append(f"| {label} | {total:,} | {with_data:,} | {pct:.0f}% |")

    threshold = int(metrics["core_threshold"])
    lines += [
        "",
        f"Coverage is significantly higher for the most-cited works "
        f"(core papers with $\\geq {threshold}$ incoming citations): "
        f"{int(metrics['core_n_covered']):,} of {int(metrics['core_n']):,} "
        f"({metrics['core_share_covered']:.0f}%) have reference data.",
    ]
    return "\n".join(lines) + "\n"


def main():
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)

    inputs = io_args.input or []
    source = inputs[0] if inputs else DEFAULT_INPUT
    df = pd.read_csv(source)
    metrics = dict(zip(df["metric"], df["value"]))

    content = render_table(metrics)
    os.makedirs(os.path.dirname(io_args.output), exist_ok=True)
    with open(io_args.output, "w") as f:
        f.write(content)

    log.info("Wrote %s", io_args.output)
    log.info("\n%s", content)


if __name__ == "__main__":
    main()
