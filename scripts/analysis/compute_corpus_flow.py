"""CONSORT-style corpus construction ledger (ticket 0327).

Produces:
- deliverables/_shared/tables/tab_corpus_flow.csv — one row per pipeline stage
- deliverables/_shared/tables/tab_corpus_flow.md  — Quarto-includable table

Each row carries In / Removed / Out, and the stages chain: every stage starts
where the previous one ended, and the last Out is the refined corpus. The
script refuses to write a ledger that does not close.

The defect this replaces: `corpus_audit.csv` records three actions — `keep`,
`remove` and `deduped` — and the paper's prose ledger counted only the first
two, so 399 duplicate-DOI drops (19 of them flagged-but-protected works) went
missing from the arithmetic. Here the buckets are enumerated explicitly and an
unrecognised one is a hard error.

Usage:
    uv run python scripts/analysis/compute_corpus_flow.py --output <path.csv>
"""

import glob
import json
import os

import pandas as pd
from schemas import CorpusFlowSchema
from script_io_args import parse_io_args, validate_io
from utils import CATALOGS_DIR, get_logger, save_csv

log = get_logger("compute_corpus_flow")

# Every action value corpus_filter.apply_filter can write to the audit.
AUDIT_ACTIONS = ("keep", "remove", "deduped")

# corpus_filter.save_dry_run_audit writes to the SAME corpus_audit.csv with a
# "would_remove" action and no deduplication pass. Such an audit describes a
# filter that never ran, so no ledger can be built from it — the remedy is to
# rerun the filter for real, not to add a stage.
DRY_RUN_ACTION = "would_remove"

CAPTION = (
    ": Corpus construction ledger. Each stage starts where the previous one"
    " ended; *In* less *Removed* equals *Out* on every row. The first *In* is"
    " the pooled source-catalog records, the last *Out* the refined corpus."
    " {#tbl-flow}"
)


def audit_buckets(audit: pd.DataFrame) -> dict[str, int]:
    """Count audit rows per action, refusing any action we do not model.

    A new action value must be given its own stage in the ledger rather than
    being folded into an existing one or silently dropped.
    """
    counts = audit["action"].value_counts()
    if DRY_RUN_ACTION in counts.index:
        raise ValueError(
            f"corpus_audit.csv carries {DRY_RUN_ACTION!r}: it is a dry-run "
            "audit, which records no actual removals and no deduplication "
            "pass. Rerun corpus_filter without --dry-run before building the "
            "ledger."
        )
    unknown = sorted(set(counts.index) - set(AUDIT_ACTIONS))
    if unknown:
        raise ValueError(
            f"corpus_audit.csv carries unmodelled action(s) {unknown}; "
            "add a stage for them in compute_corpus_flow.build_flow"
        )
    return {action: int(counts.get(action, 0)) for action in AUDIT_ACTIONS}


def build_flow(merge_report: dict, buckets: dict[str, int]) -> pd.DataFrame:
    """Assemble the stage table from the merge run report and audit buckets.

    Raises ValueError when either source's own arithmetic fails to close —
    a silent residue here is exactly the defect the table exists to expose.
    """
    pooled = int(merge_report["records_total"])
    unified = int(merge_report["records_unified"])
    merge_removals = [
        ("DOI deduplication at merge", int(merge_report["doi_duplicates_removed"])),
        ("Records without a title dropped", int(merge_report["dropped_empty_title"])),
        (
            "Title and year deduplication at merge",
            int(merge_report["title_year_duplicates_removed"]),
        ),
    ]
    if pooled - sum(n for _, n in merge_removals) != unified:
        raise ValueError(
            f"merge run report does not close: {pooled} pooled less "
            f"{sum(n for _, n in merge_removals)} removed != {unified} unified"
        )
    if sum(buckets.values()) != unified:
        raise ValueError(
            f"audit buckets {buckets} sum to {sum(buckets.values())}, "
            f"not the {unified} unified records they should account for"
        )

    stages = merge_removals + [
        ("Quality filtering, protection criteria applied", buckets["remove"]),
        ("Duplicate-DOI records dropped after enrichment", buckets["deduped"]),
    ]

    rows = []
    running = pooled
    for label, removed in stages:
        rows.append(
            {"Stage": label, "In": running, "Removed": removed, "Out": running - removed}
        )
        running -= removed
    if running != buckets["keep"]:
        raise ValueError(
            f"ledger ends at {running}, not the {buckets['keep']} refined works"
        )
    return pd.DataFrame(rows)


def format_md(flow: pd.DataFrame, caption: str = CAPTION) -> str:
    """Render the ledger as a Quarto-includable markdown table."""
    lines = [
        "| Stage | In | Removed | Out |",
        "|:------|---:|--------:|----:|",
    ]
    for _, row in flow.iterrows():
        lines.append(
            f"| {row['Stage']} | {int(row['In']):,} | "
            f"{int(row['Removed']):,} | {int(row['Out']):,} |"
        )
    lines += ["", caption, ""]
    return "\n".join(lines)


def latest_merge_report(catalogs_dir: str = CATALOGS_DIR) -> dict:
    """Read the most recent catalog_merge run report."""
    pattern = os.path.join(catalogs_dir, "run_reports", "catalog_merge__*.json")
    reports = sorted(glob.glob(pattern))
    if not reports:
        raise FileNotFoundError(
            f"No catalog_merge run report under {pattern} "
            "(run `dvc repro catalog_merge`)"
        )
    log.info("Merge run report: %s", reports[-1])
    with open(reports[-1]) as f:
        return json.load(f)


def main(output_csv: str) -> None:
    # The .md path is derived from --output, so a caller that passes the .md
    # (a bare $@ under the grouped Make target) would write the CSV to the .md
    # path and never touch the tracked CSV. Refuse instead of half-building.
    if not output_csv.endswith(".csv"):
        raise ValueError(
            f"--output must name the .csv member, got {output_csv!r}; "
            "the .md is derived from it"
        )

    audit_path = os.path.join(CATALOGS_DIR, "corpus_audit.csv")
    if not os.path.isfile(audit_path):
        raise FileNotFoundError(
            f"{audit_path} not found — the ledger is built from Phase-1 "
            "outputs (run `dvc repro corpus_filter`)"
        )
    audit = pd.read_csv(audit_path, usecols=["action"])
    log.info("Loaded %d audit rows from %s", len(audit), audit_path)

    flow = build_flow(latest_merge_report(), audit_buckets(audit))
    CorpusFlowSchema.validate(flow)
    save_csv(flow, output_csv)

    md_path = os.path.splitext(output_csv)[0] + ".md"
    with open(md_path, "w") as f:
        f.write(format_md(flow))
    log.info("Wrote %s", md_path)


if __name__ == "__main__":
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)
    main(io_args.output)
