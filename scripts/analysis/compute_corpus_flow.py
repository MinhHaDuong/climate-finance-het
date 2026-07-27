"""CONSORT-style corpus construction ledger (ticket 0327).

Produces deliverables/_shared/tables/tab_corpus_flow.csv — one row per pipeline
stage. Rendering it for Quarto is scripts/figures/export_corpus_flow.py's job:
compute and export stay separate (architecture.md Phase-2 rule 4), which also
gives each Make rule a single output.

Each row carries In / Removed / Out, and the stages chain: every stage starts
where the previous one ended, and the last Out is the refined corpus. The
script refuses to write a ledger that does not close.

The defect this replaces: `corpus_audit.csv` records three actions — `keep`,
`remove` and `deduped` — and the paper's prose ledger counted only the first
two, so 399 duplicate-DOI drops (19 of them flagged-but-protected works) went
missing from the arithmetic. Here the buckets are enumerated explicitly and an
unrecognised one is a hard error.

Usage:
    uv run python scripts/analysis/compute_corpus_flow.py \
        --output deliverables/_shared/tables/tab_corpus_flow.csv
"""

import glob
import json
import os

import pandas as pd
from pipeline_loaders import REFINED_WORKS_PATH
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


def audit_buckets(audit: pd.DataFrame) -> dict[str, int]:
    """Count audit rows per action, refusing any action we do not model.

    A new action value must be given its own stage in the ledger rather than
    being folded into an existing one or silently dropped.
    """
    counts = audit["action"].value_counts(dropna=False)
    if counts.index.isna().any():
        raise ValueError(
            "corpus_audit.csv has rows with no action; every record must be "
            "accounted for by exactly one bucket"
        )
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


def build_flow(
    merge_report: dict, buckets: dict[str, int], refined_n: int
) -> pd.DataFrame:
    """Assemble the stage table from the merge run report and audit buckets.

    Raises ValueError when the ledger fails to close. Three checks, each
    independent of the others, because two of them alone were not:

    1. the merge report's own arithmetic (pooled - removals == unified);
    2. the audit buckets accounting for every unified record;
    3. the last Out equalling `refined_n`, the row count of the corpus the
       paper actually ships.

    Check 3 is the one that has to come from outside. Comparing the last Out
    to `buckets["keep"]` is algebraically implied by check 2, so an audit whose
    rows are all `keep` — no filtering ran — produced a published-shape ledger
    ending 9,835 works high with nothing raised. Measuring against the refined
    corpus closes that hole at the source rather than leaving it to the suite.
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
    if running != refined_n:
        raise ValueError(
            f"ledger ends at {running}, not the {refined_n} works in "
            "refined_works.csv — the published corpus and the audit disagree"
        )
    return pd.DataFrame(rows)


def latest_merge_report(catalogs_dir: str = CATALOGS_DIR) -> dict:
    """Read the most recent catalog_merge run report.

    Run IDs are ISO-8601 UTC stamps (catalog_merge__20260724T132552Z.json), a
    fixed-width format whose lexicographic order is its chronological order, so
    a plain sort picks the latest. Same idiom as compute_vars.dedup_stats.
    """
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
    audit_path = os.path.join(CATALOGS_DIR, "corpus_audit.csv")
    if not os.path.isfile(audit_path):
        raise FileNotFoundError(
            f"{audit_path} not found — the ledger is built from Phase-1 "
            "outputs (run `dvc repro corpus_filter`)"
        )
    audit = pd.read_csv(audit_path, usecols=["action"])
    log.info("Loaded %d audit rows from %s", len(audit), audit_path)

    # One column of the shipped corpus: the external anchor the ledger's
    # closing check needs. Cheap next to the audit read, and it is the only
    # check the audit cannot satisfy by construction.
    refined_n = len(pd.read_csv(REFINED_WORKS_PATH, usecols=["source"]))
    log.info("Refined corpus: %d works", refined_n)

    flow = build_flow(latest_merge_report(), audit_buckets(audit), refined_n)
    CorpusFlowSchema.validate(flow)
    save_csv(flow, output_csv)


if __name__ == "__main__":
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)
    main(io_args.output)
