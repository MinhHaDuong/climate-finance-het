"""Density-conditioned null for the pre-2007 tradition separation (0182).

The manuscript (A.1 tripod, A.5) claims the three intellectual traditions
were structurally separate in the pre-2007 co-citation graph. That graph
is the sparsest slice of the corpus, so co-citation would show separation
almost regardless. This script asks the fortify-or-demote question: does
the observed within-tradition cohesion exceed what the degree sequence
alone produces?

The three tradition seed-sets are the same Louvain communities the
published figure (@fig-traditions) anchors by author names — we import
build_pre2007_traditions() so the null tests exactly those seed-sets. The
null is a configuration-model rewiring of the subgraph induced by the
tradition nodes: edges reshuffled, degrees preserved.

Output: content/tables/tab_null_separation_pre2007.csv, one row per
statistic (within_tradition_share, modularity), validated by
NullSeparationSchema.

Usage:
    uv run python scripts/compute_null_separation.py \
        --output content/tables/tab_null_separation_pre2007.csv

    CLIMATE_FINANCE_DATA=tests/fixtures/smoke \
        uv run python scripts/compute_null_separation.py \
        --output /tmp/tab_null_separation_pre2007.csv
"""

import argparse
import os

import pandas as pd
from _null_separation import (
    null_separation_test,
    partition_modularity,
    within_tradition_share,
)
from pipeline_loaders import load_analysis_config
from plot_fig_traditions import build_pre2007_traditions
from schemas import NullSeparationSchema
from script_io_args import parse_io_args, validate_io
from utils import CATALOGS_DIR, get_logger

log = get_logger("compute_null_separation")


def tradition_seed_sets(result):
    """Map each tradition node to its tradition label (drop 'other').

    The seed-sets are the three anchored communities; 'other' communities
    are not part of the manuscript's three-tradition claim and are excluded.
    """
    partition = result["partition"]
    comm_to_tradition = result["comm_to_tradition"]
    node_to_tradition = {}
    for node, comm in partition.items():
        trad = comm_to_tradition.get(comm, "other")
        if trad != "other":
            node_to_tradition[node] = trad
    return node_to_tradition


def _result_row(statistic_name, stat_fn, subgraph, node_to_tradition, n_perm, seed):
    """One CSV row: observed vs degree-preserving null for one statistic."""
    res = null_separation_test(
        subgraph, node_to_tradition, stat_fn, n_perm=n_perm, seed=seed
    )
    return {
        "statistic": statistic_name,
        "observed": res["observed"],
        "null_mean": res["null_mean"],
        "null_std": res["null_std"],
        "z_score": res["z_score"],
        "p_value": res["p_value"],
        "n_perm": res["n_perm"],
        "seed": res["seed"],
        "n_nodes": subgraph.number_of_nodes(),
        "n_edges": subgraph.number_of_edges(),
    }


def main():
    io_args, extra = parse_io_args()
    validate_io(output=io_args.output, inputs=io_args.input)
    argparse.ArgumentParser().parse_args(extra)  # reject unknown flags

    cfg = load_analysis_config()
    sep_cfg = cfg["pre2007_separation"]
    seed = int(sep_cfg["random_seed"])
    n_perm = int(sep_cfg["n_perm"])

    works_path = (
        io_args.input[0] if io_args.input
        else os.path.join(CATALOGS_DIR, "refined_works.csv")
    )
    cit_path = (
        io_args.input[1] if io_args.input and len(io_args.input) >= 2
        else None
    )

    result = build_pre2007_traditions(works_path, cit_path)
    if result is None:
        log.info("No pre-2007 traditions network. Writing empty output.")
        pd.DataFrame(
            columns=list(NullSeparationSchema.columns)
        ).to_csv(io_args.output, index=False)
        return

    node_to_tradition = tradition_seed_sets(result)
    trad_nodes = list(node_to_tradition)
    subgraph = result["graph"].subgraph(trad_nodes).copy()
    log.info(
        "Tradition seed-sets: %d nodes across %d traditions; "
        "induced subgraph %d nodes, %d edges",
        len(trad_nodes),
        len(set(node_to_tradition.values())),
        subgraph.number_of_nodes(),
        subgraph.number_of_edges(),
    )
    log.info("Null: %d degree-preserving rewirings (seed=%d)", n_perm, seed)

    rows = [
        _result_row(
            "within_tradition_share", within_tradition_share,
            subgraph, node_to_tradition, n_perm, seed,
        ),
        _result_row(
            "modularity", partition_modularity,
            subgraph, node_to_tradition, n_perm, seed,
        ),
    ]
    for row in rows:
        log.info(
            "  %-22s observed=%.4f null=%.4f+-%.4f z=%.2f p=%.4g",
            row["statistic"], row["observed"], row["null_mean"],
            row["null_std"], row["z_score"], row["p_value"],
        )

    df = pd.DataFrame(rows)
    NullSeparationSchema.validate(df)
    df.to_csv(io_args.output, index=False)
    log.info("Saved separation null -> %s", io_args.output)


if __name__ == "__main__":
    main()
