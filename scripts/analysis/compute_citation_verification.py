#!/usr/bin/env python3
"""Extract the citation-verification statistics the data paper quotes (0320).

The paper's §2 states how much of the citation graph was verified against
Crossref. Those numbers were typed into the prose by hand from a corpus-v1
run and survived a full corpus rebuild unchanged: the paper claimed 99.0%
(95% CI [97.1, 99.7]) while the regenerated report said 97.0% (CI [94.4,
98.4]) — a point estimate outside its own interval, and "the 1% unconfirmed"
where the measurement said 3%.

This script is the formal producer that makes that impossible to repeat. It
reads the artifact `scripts/qa/qa_citations.py` writes and emits the quoted
statistics as a long (metric, value) table, which compute_vars turns into
`{{< meta >}}` variables scoped to the data paper. Nothing in the prose is
typed by hand; the next corpus rebuild moves the sentence.

Two independent tests travel together because they answer different referee
questions (RDJ-26561 R1-13):

  accuracy      of the links we ship, how many does Crossref confirm?
  completeness  of the reference DOIs Crossref holds, how many did we capture?

Output: deliverables/_shared/tables/tab_citation_verification.csv, validated
by CitationVerificationSchema.

Usage:
    uv run python scripts/analysis/compute_citation_verification.py \
        --output deliverables/_shared/tables/tab_citation_verification.csv
"""

import argparse
import json
import os

import pandas as pd
from pipeline_io import save_csv
from schemas import CitationVerificationSchema
from script_io_args import parse_io_args, validate_io
from utils import BASE_DIR, get_logger

log = get_logger("compute_citation_verification")

DEFAULT_REPORT = os.path.join(
    BASE_DIR, "deliverables", "_shared", "tables", "qa_citations_report.json"
)


def _pct(value):
    """Proportion on a 0-1 scale to a percentage, or None if absent."""
    return None if value is None else 100.0 * float(value)


def compute_citation_verification(report):
    """Flatten the QA report's two tests into a long (metric, value) table.

    Parameters
    ----------
    report : dict
        Parsed qa_citations_report.json. Must carry an ``accuracy`` block;
        ``completeness`` is optional so an accuracy-only run still produces
        a usable artifact rather than failing the build.

    """
    if "accuracy" not in report:
        raise KeyError(
            "qa_citations_report.json has no 'accuracy' block — the paper's "
            "verification sentence has no source. Re-run scripts/qa/qa_citations.py."
        )

    acc = report["accuracy"]
    confirmed = int(acc["confirmed"])
    tested = int(acc["tested_n"])
    not_confirmed = int(acc["not_confirmed"])

    rows = [
        ("verify_sample_n", float(acc["sample_n"])),
        ("verify_tested_n", float(tested)),
        ("verify_confirmed_n", float(confirmed)),
        ("verify_unconfirmed_n", float(not_confirmed)),
        ("verify_errors_n", float(acc.get("errors", 0))),
        ("verify_confirmed_pct", _pct(acc["proportion"])),
        ("verify_ci_lower_pct", _pct(acc["ci_lower"])),
        ("verify_ci_upper_pct", _pct(acc["ci_upper"])),
        # Derived here rather than in the prose: the unconfirmed share is the
        # complement of the confirmed one, and letting the paragraph do that
        # arithmetic by hand is how "the 1%" outlived a 3% measurement.
        ("verify_unconfirmed_pct", _pct(1.0 - float(acc["proportion"]))),
    ]

    comp = report.get("completeness")
    if comp:
        rows += [
            ("complete_sample_n", float(comp["sample_n"])),
            ("complete_total_n", float(comp["total_cr_ref_dois"])),
            ("complete_captured_n", float(comp["captured"])),
            ("complete_missed_n", float(comp["missed"])),
            ("complete_captured_pct", _pct(comp["proportion"])),
            ("complete_ci_lower_pct", _pct(comp["ci_lower"])),
            ("complete_ci_upper_pct", _pct(comp["ci_upper"])),
        ]
    else:
        log.warning("Report has no 'completeness' block — emitting accuracy only")

    return pd.DataFrame(rows, columns=["metric", "value"])


def main():
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)
    argparse.ArgumentParser().parse_args(_extra)  # reject unknown flags

    inputs = io_args.input or []
    report_path = inputs[0] if inputs else DEFAULT_REPORT
    with open(report_path) as fh:
        report = json.load(fh)
    log.info("Read %s (generated %s)", report_path, report.get("generated", "?"))

    df = compute_citation_verification(report)
    for metric, value in df.itertuples(index=False):
        log.info("  %-24s %s", metric, value)

    CitationVerificationSchema.validate(df)
    save_csv(df, io_args.output)
    log.info("Saved citation verification -> %s", io_args.output)


if __name__ == "__main__":
    main()
