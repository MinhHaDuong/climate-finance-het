"""Limitations demonstration on the citer-limited early network (ticket 0286).

R1-14 asks the data paper to demonstrate the citation layer's potential
and/or limitations. This script industrializes the hardest-case test: the
co-citation network built from citing documents published <= the citer
cutoff (config `network_limitations.citer_cutoff`, the sparse early period).
Three quantities back the response letter:

1. Separation of the two economic clusters (CDM vs pricing): observed
   within-cluster edge share on the induced subgraph vs a degree-preserving
   rewiring null (`_null_separation.null_separation_test`).
2. Absence of a burden-sharing / equity co-citation community: how many of
   the a-priori candidate anchors even enter the network.
3. Bootstrap over citing documents: rates at which the CDM cluster, the
   pricing cluster, and a burden/governance community appear across
   replicate corpora.

Output: one long-format CSV (metric, value), validated by
NetworkLimitationsSchema. Every number quoted in
deliverables/data-paper/revision-rdj26561/r1-14-network-response.md traces
to a row of this artifact (no hand-curated numbers).

Usage:
    uv run python scripts/analysis/compute_network_limitations.py \
        --output deliverables/_shared/tables/tab_network_limitations.csv
"""

import argparse

import community as community_louvain
import numpy as np
import pandas as pd
from _citer_limited_traditions import (
    BURDEN_CANDIDATES,
    build_top_graph,
    burden_hits,
    candidates_in_network,
    citer_limited_cutoff,
    cluster_present,
    load_citer_limited,
)
from _null_separation import null_separation_test, within_tradition_share
from _pre2007_traditions import (
    RANDOM_STATE,
    TRADITION_ANCHORS,
    _assign_traditions,
)
from pipeline_loaders import load_analysis_config
from schemas import NetworkLimitationsSchema
from script_io_args import parse_io_args, validate_io
from utils import get_logger

log = get_logger("compute_network_limitations")


def econ_bipartition_rows(G, n_perm, seed):
    """CDM/pricing separation vs degree-preserving null, on induced subgraph."""
    partition = community_louvain.best_partition(
        G, weight="weight", random_state=RANDOM_STATE)
    ctt, _, _ = _assign_traditions(G, partition)
    node_to_trad = {n: ctt[partition[n]] for n in G.nodes()
                    if ctt.get(partition[n]) in ("cdm", "pricing")}
    H = G.subgraph(node_to_trad).copy()
    cross_edges = sum(1 for u, v in H.edges()
                      if node_to_trad[u] != node_to_trad[v])
    res = null_separation_test(
        H, node_to_trad, within_tradition_share, n_perm=n_perm, seed=seed)
    log.info("Bipartition: %d nodes, %d edges, %d cross edges; "
             "within obs=%.3f null=%.3f+/-%.3f z=%.1f p=%.4f",
             H.number_of_nodes(), H.number_of_edges(), cross_edges,
             res["observed"], res["null_mean"], res["null_std"],
             res["z_score"], res["p_value"])
    return [
        ("econ_subgraph_n_nodes", H.number_of_nodes()),
        ("econ_subgraph_n_edges", H.number_of_edges()),
        ("econ_cross_cluster_edges_observed", cross_edges),
        ("econ_within_share_observed", res["observed"]),
        ("econ_cross_share_null_mean", 1.0 - res["null_mean"]),
        ("econ_cross_share_null_std", res["null_std"]),
        ("econ_within_share_z", res["z_score"]),
        ("econ_within_share_p", res["p_value"]),
        ("econ_null_n_perm", res["n_perm"]),
    ]


def burden_rows(G, partition):
    """Absence of the equity community in the observed network."""
    counts, sizes = burden_hits(G, partition)
    max_together = max(counts.values(), default=0)
    return [
        ("burden_candidates", len(BURDEN_CANDIDATES)),
        ("burden_candidates_in_network", candidates_in_network(G)),
        ("burden_max_anchors_one_community", max_together),
        ("burden_community_observed",
         int(any(v >= 3 and sizes[c] >= 4 for c, v in counts.items()))),
    ]


def bootstrap_rows(cit, doi_meta, cutoff_year, n_boot, seed):
    """Bootstrap the citing documents; rates of cluster (re)appearance."""
    docs = cit["source_doi"].unique()
    groups = dict(tuple(cit.groupby("source_doi")))
    rng = np.random.default_rng(seed)
    n_burden = n_cdm = n_pricing = n_valid = 0
    for b in range(n_boot):
        sample = rng.choice(docs, size=len(docs), replace=True)
        # Each draw is a DISTINCT citer: without the unique suffix, a doc
        # sampled k times collapses into one source_doi group whose ref list
        # is duplicated k-fold, inflating co-citation counts ~k^2.
        parts = []
        for i, d in enumerate(sample):
            g = groups[d].copy()
            g["source_doi"] = f"{d}#{i}"
            parts.append(g)
        boot_cit = pd.concat(parts, ignore_index=True)
        G, _ = build_top_graph(boot_cit, doi_meta, cutoff_year)
        if G is None or G.number_of_nodes() == 0:
            continue
        n_valid += 1
        partition = community_louvain.best_partition(
            G, weight="weight", random_state=RANDOM_STATE)
        counts, sizes = burden_hits(G, partition)
        if any(v >= 3 and sizes[c] >= 4 for c, v in counts.items()):
            n_burden += 1
        if cluster_present(G, partition, TRADITION_ANCHORS["cdm"]):
            n_cdm += 1
        if cluster_present(G, partition, TRADITION_ANCHORS["pricing"]):
            n_pricing += 1
        if (b + 1) % 50 == 0:
            log.info("  bootstrap %d/%d", b + 1, n_boot)
    denom = max(n_valid, 1)
    return [
        ("boot_n", n_boot),
        ("boot_n_valid", n_valid),
        ("boot_burden_rate", n_burden / denom),
        ("boot_cdm_rate", n_cdm / denom),
        ("boot_pricing_rate", n_pricing / denom),
    ]


def main():
    io_args, extra = parse_io_args()
    validate_io(output=io_args.output, inputs=io_args.input)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-boot", type=int, default=None,
                        help="Override config network_limitations.n_boot")
    parser.add_argument("--skip-bootstrap", action="store_true",
                        help="Null test and observed rows only (fast)")
    args = parser.parse_args(extra)

    cfg = load_analysis_config()["network_limitations"]
    citer_cutoff = citer_limited_cutoff()
    n_perm = int(cfg["n_perm"])
    n_boot = args.n_boot if args.n_boot is not None else int(cfg["n_boot"])
    seed = int(cfg["seed"])

    works_path = io_args.input[0] if io_args.input else None
    cit_path = (io_args.input[1]
                if io_args.input and len(io_args.input) >= 2 else None)
    cit, doi_meta, cutoff_year = load_citer_limited(
        citer_cutoff, works_path, cit_path)

    rows = [("citer_cutoff", citer_cutoff),
            ("ref_cutoff_year", cutoff_year),
            ("n_citing_docs", cit["source_doi"].nunique()),
            ("n_citation_pairs", len(cit))]

    G, _ = build_top_graph(cit, doi_meta, cutoff_year)
    if G is None or G.number_of_nodes() == 0:
        log.info("Empty network — writing header-only output.")
        pd.DataFrame(columns=["metric", "value"]).to_csv(
            io_args.output, index=False)
        return
    rows += [("network_n_nodes", G.number_of_nodes()),
             ("network_n_edges", G.number_of_edges())]

    rows += econ_bipartition_rows(G, n_perm, seed)
    partition = community_louvain.best_partition(
        G, weight="weight", random_state=RANDOM_STATE)
    rows += burden_rows(G, partition)
    if not args.skip_bootstrap:
        rows += bootstrap_rows(cit, doi_meta, cutoff_year, n_boot, seed)

    df = pd.DataFrame(rows, columns=["metric", "value"])
    df["value"] = df["value"].astype(float)
    NetworkLimitationsSchema.validate(df)
    df.to_csv(io_args.output, index=False)
    log.info("Wrote %d metric rows to %s", len(df), io_args.output)


if __name__ == "__main__":
    main()
