"""Density-conditioned null for the pre-2007 tradition separation (0182).

The manuscript (A.1 tripod, A.5) claims the three intellectual traditions
were structurally separate in the pre-2007 co-citation graph. That graph
is the sparsest slice of the corpus, so co-citation would show separation
almost regardless. This script asks the fortify-or-demote question: does
the observed within-tradition cohesion exceed what the degree sequence
alone produces?

Two labellings of the same co-citation graph are tested, distinguished by a
``labelling`` column so the robustness is itself traceable:

- ``louvain_anchored`` — seed-sets are the Louvain communities the published
  figure (@fig-traditions) anchors by author name. Louvain maximises
  modularity by construction, so "the optimised partition beats a
  configuration-model null on that same graph" overstates the manuscript's
  claim about three *historically* defined traditions.
- ``a_priori_anchors`` — seed-sets fixed a priori from the intellectual-history
  record (@tbl-traditions authors, config ``pre2007_separation.anchor_*``),
  via ``label_nodes_by_anchors``. This labelling path invokes no community
  detection at all, so the circularity objection cannot reach it.

The null is a configuration-model rewiring of the subgraph induced by the
tradition nodes: edges reshuffled, degrees preserved.

Output: content/tables/tab_null_separation_pre2007.csv, one row per
(labelling, statistic) — within_tradition_share and modularity for each of
the two labellings — validated by NullSeparationSchema.

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
    label_nodes_by_anchors,
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


def _result_row(labelling, statistic_name, stat_fn, subgraph,
                node_to_tradition, n_perm, seed):
    """One CSV row: observed vs degree-preserving null for one statistic."""
    res = null_separation_test(
        subgraph, node_to_tradition, stat_fn, n_perm=n_perm, seed=seed
    )
    return {
        "labelling": labelling,
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
        "n_truncated": res["n_truncated"],
    }


def _labelling_rows(labelling, graph, node_to_tradition, n_perm, seed):
    """Two statistic rows (share, modularity) for one labelling of the graph.

    The induced subgraph is restricted to the labelled nodes so the rewiring
    preserves exactly their degree sequence.
    """
    trad_nodes = list(node_to_tradition)
    subgraph = graph.subgraph(trad_nodes).copy()
    log.info(
        "[%s] %d nodes across %d traditions; induced subgraph %d nodes, %d edges",
        labelling, len(trad_nodes), len(set(node_to_tradition.values())),
        subgraph.number_of_nodes(), subgraph.number_of_edges(),
    )
    return [
        _result_row(
            labelling, "within_tradition_share", within_tradition_share,
            subgraph, node_to_tradition, n_perm, seed,
        ),
        _result_row(
            labelling, "modularity", partition_modularity,
            subgraph, node_to_tradition, n_perm, seed,
        ),
    ]


def main():
    io_args, extra = parse_io_args()
    validate_io(output=io_args.output, inputs=io_args.input)
    parser = argparse.ArgumentParser()
    parser.parse_args(extra)  # reject unknown flags

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

    graph = result["graph"]
    log.info("Null: %d degree-preserving rewirings per statistic (seed=%d)",
             n_perm, seed)

    # Labelling 1 — Louvain-anchored seed-sets (circular; kept for comparison).
    louvain_labels = tradition_seed_sets(result)

    # Labelling 2 — a-priori anchors, NO community detection in this path.
    anchor_authors = {k: list(v) for k, v in sep_cfg["anchor_authors"].items()}
    anchor_works = {k: list(v) for k, v in sep_cfg.get("anchor_works", {}).items()}
    apriori_labels = label_nodes_by_anchors(graph, anchor_works, anchor_authors)

    rows = []
    rows += _labelling_rows("louvain_anchored", graph, louvain_labels,
                            n_perm, seed)
    rows += _labelling_rows("a_priori_anchors", graph, apriori_labels,
                            n_perm, seed)

    for row in rows:
        log.info(
            "  [%-16s] %-22s observed=%.4f null=%.4f+-%.4f z=%.2f p=%.4g "
            "(n_truncated=%d)",
            row["labelling"], row["statistic"], row["observed"],
            row["null_mean"], row["null_std"], row["z_score"],
            row["p_value"], row["n_truncated"],
        )

    df = pd.DataFrame(rows)
    NullSeparationSchema.validate(df)
    df.to_csv(io_args.output, index=False)
    log.info("Saved separation null -> %s", io_args.output)


if __name__ == "__main__":
    main()
