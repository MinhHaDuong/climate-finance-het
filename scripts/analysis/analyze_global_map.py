"""Global citation-network map of the corpus: community meta-graph (ticket 0307).

Compute side of the global map figure (R1-14). Two methods share one output
contract (dispatcher pattern, architecture rule 8):

- direct     : undirected graph of direct citations between corpus documents
               (DOI-matched, intra-corpus). The data-paper figure.
- cocitation : co-citation graph over the top-K most-cited references
               (any reference, in-corpus or not). Companion material.

Louvain community detection with the config seed, then aggregation to a
community meta-graph: one node per community holding >= min_share of the
connected nodes, edges = inter-community link counts. The plot script
(scripts/figures/plot_fig_global_map.py) renders the JSON; compute_vars.py
reads its stats block for the data-paper Quarto variables.

Usage:
    python scripts/analysis/analyze_global_map.py --method direct \
        --output data/derived/tables/global_map_direct.json
"""

import argparse
import json
import os
from collections import Counter

import community as community_louvain
import networkx as nx
import numpy as np
from pipeline_loaders import load_analysis_config, load_refined_works
from scipy.sparse import csr_matrix
from script_io_args import parse_io_args, validate_io
from utils import get_logger, load_refined_citations, normalize_doi

log = get_logger("analyze_global_map")

BAD_DOIS = {"", "nan", "none"}


def load_config():
    """Global-map parameters + the shared Louvain seed from config/analysis.yaml."""
    cfg = load_analysis_config()
    gm = cfg["global_map"]
    seed = int(cfg["pre2007_traditions"]["louvain_seed"])
    return gm, seed


def load_data():
    """Load cleaned citation pairs, corpus works, and a DOI metadata lookup."""
    cit = load_refined_citations()
    cit["source_doi"] = cit["source_doi"].apply(normalize_doi)
    cit["ref_doi"] = cit["ref_doi"].apply(normalize_doi)
    cit = cit[~cit["source_doi"].isin(BAD_DOIS) & ~cit["ref_doi"].isin(BAD_DOIS)]
    works = load_refined_works()
    works["doi_norm"] = works["doi"].apply(normalize_doi)
    works = works[~works["doi_norm"].isin(BAD_DOIS)]
    meta = works.set_index("doi_norm")[["first_author", "year"]].to_dict("index")
    # Reference-side fallback for references outside the corpus (cocitation)
    if "ref_first_author" in cit.columns:
        sub = cit.drop_duplicates("ref_doi")
        for d, au, yr in zip(sub["ref_doi"], sub.get("ref_first_author", ""),
                             sub.get("ref_year", "")):
            if d not in meta:
                meta[d] = {"first_author": au, "year": yr}
    return cit, works, meta


def direct_graph(cit, works):
    """Undirected graph of direct citations between corpus documents."""
    corpus = set(works["doi_norm"])
    sub = cit[cit["source_doi"].isin(corpus) & cit["ref_doi"].isin(corpus)]
    sub = sub[sub["source_doi"] != sub["ref_doi"]]
    G = nx.Graph()
    G.add_edges_from(
        sub[["source_doi", "ref_doi"]].drop_duplicates().itertuples(
            index=False, name=None))
    G.remove_nodes_from(list(nx.isolates(G)))
    rank = sub.groupby("ref_doi").size().to_dict()
    return G, rank


def cocitation_graph(cit, top_k, min_cocit):
    """Weighted co-citation graph over the top-K most-cited references."""
    rc = cit.groupby("ref_doi").size().sort_values(ascending=False)
    top = rc.head(top_k)
    top_refs = top.index.tolist()
    ridx = {r: i for i, r in enumerate(top_refs)}
    sub = cit[cit["ref_doi"].isin(ridx)]
    docs = {d: i for i, d in enumerate(sub["source_doi"].unique())}
    B = csr_matrix(
        (np.ones(len(sub)),
         (sub["source_doi"].map(docs), sub["ref_doi"].map(ridx))),
        shape=(len(docs), len(top_refs)))
    B.data[:] = 1.0  # dedupe duplicate citation rows
    C = (B.T @ B).tocoo()
    G = nx.Graph()
    for i, j, w in zip(C.row, C.col, C.data):
        if i < j and w >= min_cocit:
            G.add_edge(top_refs[i], top_refs[j], weight=float(w))
    G.remove_nodes_from(list(nx.isolates(G)))
    return G, top.to_dict()


def member_label(doi, meta):
    """Raw 'Author Year' label for a community member (formatting is render-side)."""
    m = meta.get(doi, {})
    au = str(m.get("first_author", "") or "?").split(",")[0].strip()
    yr = str(m.get("year", "") or "?")[:4]
    return f"{au} {yr}"


def summarize(G, partition, rank, meta, min_share, top_members):
    """Aggregate the partition into the meta-graph summary dict."""
    # "weight" is python-louvain's default edge-data key; edges without the
    # attribute (direct graph) count as 1, so one code path serves both methods.
    n = G.number_of_nodes()
    mod = community_louvain.modularity(partition, G, weight="weight")
    sizes = Counter(partition.values())
    big = [(c, s) for c, s in sizes.most_common() if s / n >= min_share]
    bigset = {c for c, _ in big}
    inter = Counter()
    for u, v in G.edges():
        cu, cv = partition[u], partition[v]
        if cu != cv and cu in bigset and cv in bigset:
            inter[tuple(sorted((cu, cv)))] += 1
    members = {c: [] for c in bigset}
    for d, c in partition.items():
        if c in bigset:
            members[c].append(d)
    communities = []
    for c, s in big:
        top = sorted(members[c], key=lambda d: -rank.get(d, 0))[:top_members]
        communities.append({
            "id": int(c),
            "size": int(s),
            "share": round(s / n, 4),
            "top_members": [
                {"label": member_label(d, meta),
                 "rank": int(rank.get(d, 0))} for d in top],
        })
    coverage = sum(s for _, s in big) / n
    return {
        "n_nodes": int(n),
        "n_edges": int(G.number_of_edges()),
        "n_communities_total": len(sizes),
        "n_communities_major": len(big),
        "min_share": min_share,
        "coverage_share": round(coverage, 4),
        "modularity": round(mod, 4),
        "communities": communities,
        "edges": [{"a": int(a), "b": int(b), "weight": int(w)}
                  for (a, b), w in sorted(inter.items())],
    }


def main():
    io_args, extra = parse_io_args()
    os.makedirs(os.path.dirname(io_args.output) or ".", exist_ok=True)
    validate_io(output=io_args.output)
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=["direct", "cocitation"],
                        default="direct")
    args = parser.parse_args(extra)

    gm, seed = load_config()
    cit, works, meta = load_data()
    log.info("citation pairs: %d; corpus works with DOI: %d", len(cit), len(works))

    if args.method == "direct":
        G, rank = direct_graph(cit, works)
    else:
        G, rank = cocitation_graph(
            cit, int(gm["cocitation_top_k"]), int(gm["cocitation_min_cocit"]))
    log.info("%s graph: %d nodes, %d edges", args.method,
             G.number_of_nodes(), G.number_of_edges())

    partition = community_louvain.best_partition(
        G, weight="weight", random_state=seed)
    summary = summarize(G, partition, rank, meta,
                        float(gm["min_share"]), int(gm["top_members"]))
    summary["method"] = args.method
    summary["louvain_seed"] = seed

    with open(io_args.output, "w") as f:
        json.dump(summary, f, indent=1)
    log.info("%s: %d/%d communities >= %.0f%% cover %.0f%% of %d connected "
             "nodes, modularity=%.3f -> %s",
             args.method, summary["n_communities_major"],
             summary["n_communities_total"], 100 * summary["min_share"],
             100 * summary["coverage_share"], summary["n_nodes"],
             summary["modularity"], io_args.output)


if __name__ == "__main__":
    main()
