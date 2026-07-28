"""Export the deposited reranker human-validation table (ticket 0372).

The data paper quotes AUC = 0.818 for the cross-encoder relevance filter
(flag 6). The per-work human labels behind that number were destroyed by
their own collection sheet — ``compute_reranker_calibration.py`` blanks the
``human_label`` column on every re-run, and no graded copy survives (0372
forensics, 2026-07-28). What survives is the validation sample itself
(``docs/reranker_hitl_stratified.csv``, scores intact, labels blank) and the
per-quintile human-relevance rates recorded in technical report §3.1 at
commit 5d8224b3, the commit that introduced the claim.

This script rebuilds the validation evidence from those two survivors: one
row per score quintile with the sample composition measured from the sheet
and the human-relevance rate from the recorded protocol. Because the strata
are score-disjoint and score-ordered, these rates alone determine the AUC up
to within-stratum ties; ``implied_auc()`` computes it (0.8175, vs 0.818
quoted — the corroboration that closed the forensics).
``tests/test_reranker_validation_claim.py`` pins the paper's quote to this
artifact.

Usage:
    uv run python scripts/figures/export_reranker_validation.py \
        --output deliverables/_shared/tables/tab_reranker_validation.csv
"""

import os

import pandas as pd
from script_io_args import parse_io_args, validate_io
from utils import get_logger, save_csv

log = get_logger("export_reranker_validation")

# Per-quintile human-relevant rates, technical report §3.1 at commit 5d8224b3
# (2026-03-13): "The proportion of human-relevant papers increased
# monotonically across score quintiles (10%, 15%, 20%, 60%, 80%)". Historical
# measurement, not a tunable parameter — the raw labels no longer exist, so
# these constants are the record.
HUMAN_RELEVANT_RATE = {1: 0.10, 2: 0.15, 3: 0.20, 4: 0.60, 5: 0.80}

# Default sample location: git-tracked, so this export needs no corpus data.
DEFAULT_SAMPLE = os.path.join("docs", "reranker_hitl_stratified.csv")


def implied_auc(rates: dict[int, float], n_per_stratum: dict[int, int]) -> float:
    """AUC implied by per-stratum relevance rates over score-ordered strata.

    Cross-stratum pairs are fully determined by stratum order; within-stratum
    pairs are ties and count 1/2, the standard AUC tie convention.
    """
    strata = sorted(rates)
    pos = {s: rates[s] * n_per_stratum[s] for s in strata}
    neg = {s: n_per_stratum[s] - pos[s] for s in strata}
    num = 0.0
    for i in strata:
        for j in strata:
            if i > j:
                num += pos[i] * neg[j]
            elif i == j:
                num += 0.5 * pos[i] * neg[j]
    denom = sum(pos.values()) * sum(neg.values())
    return num / denom


def build_table(sample: pd.DataFrame) -> pd.DataFrame:
    """One row per score quintile: measured composition + recorded rate."""
    rows = []
    for stratum, grp in sample.groupby("stratum"):
        stratum = int(stratum)
        rate = HUMAN_RELEVANT_RATE[stratum]
        rows.append({
            "stratum": stratum,
            "n": len(grp),
            "score_min": grp["reranker_score"].min(),
            "score_max": grp["reranker_score"].max(),
            "human_relevant_rate": rate,
            "human_relevant_n": round(rate * len(grp)),
        })
    return pd.DataFrame(rows).sort_values("stratum").reset_index(drop=True)


def main():
    io_args, _ = parse_io_args()
    validate_io(io_args.output, inputs=[DEFAULT_SAMPLE])
    sample = pd.read_csv(DEFAULT_SAMPLE)
    table = build_table(sample)
    auc = implied_auc(
        HUMAN_RELEVANT_RATE, dict(zip(table["stratum"], table["n"]))
    )
    log.info("implied AUC from per-quintile rates: %.4f", auc)
    save_csv(table, io_args.output)
    log.info("wrote %s (%d strata, %d works)", io_args.output, len(table), table["n"].sum())


if __name__ == "__main__":
    main()
