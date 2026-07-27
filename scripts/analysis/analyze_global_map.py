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
import re
from collections import Counter

import community as community_louvain
import networkx as nx
import numpy as np
from _global_map_graph import direct_graph, load_data
from _label_vocabulary import LABEL_STOPWORDS, collapse_acronyms
from openalex_corpus.embedding import is_boilerplate_abstract
from pipeline_loaders import load_analysis_config
from scipy.sparse import csr_matrix
from script_io_args import parse_io_args, validate_io
from sklearn.feature_extraction.text import TfidfVectorizer
from utils import get_logger

log = get_logger("analyze_global_map")

def load_config():
    """Global-map parameters + the shared Louvain seed from config/analysis.yaml."""
    cfg = load_analysis_config()
    gm = cfg["global_map"]
    seed = int(cfg["pre2007_traditions"]["louvain_seed"])
    return gm, seed


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


def _member_text(row):
    """Labelling text for one work: title + keywords + clean abstract.

    Mirrors the sem-composition labelling input (compute_clusters): abstracts
    are included, but boilerplate/stub abstracts are dropped
    (is_boilerplate_abstract), and known expansions collapse to acronyms.
    """
    def _clean(v):
        s = str(v or "")
        return "" if s.lower() in ("nan", "none") else s

    title = _clean(row.get("title"))
    # Keywords carry concept-disambiguation parentheticals — "Adaptation
    # (eye)", "Vulnerability (computing)" — that are noise, not content.
    keywords = re.sub(r"\([^)]*\)", " ", _clean(row.get("keywords")))
    abstract = _clean(row.get("abstract"))
    if is_boilerplate_abstract(abstract, title=title):
        abstract = ""
    return collapse_acronyms(" ".join(p for p in (title, keywords, abstract) if p))


def add_top_terms(summary, partition, works, n_terms=3):
    """Attach top-N TF-IDF distinctive terms to each major community.

    Same method as the sem-composition panel subtitles (compute_clusters):
    TF-IDF over member texts, distinctiveness = community mean - corpus mean,
    shared LABEL_STOPWORDS filter. Terms are deduplicated by token stem.
    """
    major = {c["id"] for c in summary["communities"]}
    w = works.drop_duplicates("doi_norm").set_index("doi_norm")
    docs, comm_of = [], []
    for doi, c in partition.items():
        if c in major and doi in w.index:
            docs.append(_member_text(w.loc[doi]))
            comm_of.append(c)
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2), max_features=8000, sublinear_tf=True,
        stop_words="english", min_df=5, max_df=0.8)
    X = vectorizer.fit_transform(docs)
    features = np.array(vectorizer.get_feature_names_out())
    corpus_mean = np.asarray(X.mean(axis=0)).flatten()
    comm_arr = np.array(comm_of)
    for comm in summary["communities"]:
        mask = comm_arr == comm["id"]
        dist = np.asarray(X[mask].mean(axis=0)).flatten() - corpus_mean
        terms, used_stems = [], set()
        for i in np.argsort(dist)[::-1]:
            if dist[i] <= 0 or len(terms) >= n_terms:
                break
            tokens = features[i].split()
            stems = {t.rstrip("s") for t in tokens}
            if any(t in LABEL_STOPWORDS for t in tokens) or stems & used_stems:
                continue
            terms.append(str(features[i]))
            used_stems |= stems
        comm["top_terms"] = terms
    return summary


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
    if args.method == "direct":
        # Direct-map communities are labelled by their top TF-IDF terms
        # (author directive 2026-07-24); cocitation nodes are references,
        # often outside the corpus, so no member texts exist for them.
        add_top_terms(summary, partition, works)
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
