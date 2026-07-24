"""Exploration 2: the paper's 6 semantic clusters (v1 committed centroids)
vs the direct-citation communities and a fresh k-means k=6.

Per-work assignment for the paper partition = nearest committed v1 centroid
(config/v1_cluster_centroids.npy) in raw embedding space, matching the
KMeans geometry of compute_clusters.py. No figure output.
"""

import json
import os
import sys
from collections import Counter

import community as community_louvain
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

sys.path.insert(0, "scripts")
sys.path.insert(0, "libs/openalex-corpus/src")

import yaml

from openalex_corpus.text import normalize_doi
from pipeline_loaders import (BASE_DIR, load_refined_citations,
                              load_refined_embeddings, load_refined_works)

RANDOM_STATE = 42

_REG_PATH = ("/home/haduong/Climate_finance/.claude/worktrees/"
             "agent-a47c0bce2b431187f/config/community_registry.yml")


def short(lab, n=3):
    return " / ".join(lab.split(" / ")[:n])


def main():
    cit = load_refined_citations()
    cit["source_doi"] = cit["source_doi"].apply(normalize_doi)
    cit["ref_doi"] = cit["ref_doi"].apply(normalize_doi)
    bad = {"", "nan", "none"}
    cit = cit[~cit["source_doi"].isin(bad) & ~cit["ref_doi"].isin(bad)]
    works = load_refined_works().reset_index(drop=True)
    emb = load_refined_embeddings()
    works["doi_norm"] = works["doi"].apply(normalize_doi)
    keep = ~works["doi_norm"].isin(bad)
    doi2row = {}
    for i, d in zip(works.index[keep], works.loc[keep, "doi_norm"]):
        doi2row.setdefault(d, i)

    corpus = set(works.loc[keep, "doi_norm"])
    sub = cit[cit["source_doi"].isin(corpus) & cit["ref_doi"].isin(corpus)]
    sub = sub[sub["source_doi"] != sub["ref_doi"]]
    G = nx.Graph()
    G.add_edges_from(sub[["source_doi", "ref_doi"]].drop_duplicates()
                     .itertuples(index=False, name=None))
    G.remove_nodes_from(list(nx.isolates(G)))
    part = community_louvain.best_partition(G, random_state=RANDOM_STATE)
    n = G.number_of_nodes()
    sizes = Counter(part.values())
    big = [c for c, s in sizes.most_common() if s / n >= 0.02]

    with open(_REG_PATH) as f:
        reg = yaml.safe_load(f)
    names = {int(cid): reg["concepts"][k]["label"]
             for cid, k in reg["figures"]["fig_global_map_direct"].items()}

    nodes = [d for d in G.nodes() if part[d] in big and d in doi2row]
    X = emb[[doi2row[d] for d in nodes]].astype(np.float64)
    norms = np.linalg.norm(X, axis=1)
    ok = np.isfinite(X).all(axis=1) & (norms > 0)
    nodes = [d for d, o in zip(nodes, ok) if o]
    X = X[ok]
    y_cit = np.array([part[d] for d in nodes])
    print(f"analysis set: {len(nodes)} works "
          f"({(~ok).sum()} dropped for NaN/zero embeddings)")

    # 1. paper-pipeline partition. The committed per-work artifact does not
    # exist (compute_clusters.py writes only aggregates), and the committed
    # v1 centroids are 384-d vs the current 1024-d bge-m3 space, so
    # nearest-centroid assignment is impossible. Fallback: the pipeline's own
    # deterministic parameters (KMeans k=6, seed 42, n_init=20, raw space).
    y_v1 = KMeans(n_clusters=6, random_state=RANDOM_STATE,
                  n_init=20).fit_predict(X)
    print("paper-pipeline k=6 sizes:", dict(Counter(y_v1.tolist())))
    # quick content labels: top distinctive title words per cluster
    from sklearn.feature_extraction.text import TfidfVectorizer
    doi2title = dict(zip(works.loc[keep, "doi_norm"],
                         works.loc[keep, "title"].fillna("")))
    titles = [str(doi2title.get(d, "")) for d in nodes]
    vec = TfidfVectorizer(stop_words="english", max_features=5000, min_df=5)
    T = vec.fit_transform(titles)
    feats = np.array(vec.get_feature_names_out())
    gmean = np.asarray(T.mean(axis=0)).ravel()
    v1_labels = {}
    for c in range(6):
        m = y_v1 == c
        dist = np.asarray(T[m].mean(axis=0)).ravel() - gmean
        v1_labels[c] = " / ".join(feats[np.argsort(dist)[::-1][:5]])
        print(f"  cluster {c} (n={m.sum()}): {v1_labels[c]}")

    # 2. fresh k-means k=6 on normalized embeddings, seed 42
    Xn = X / np.linalg.norm(X, axis=1, keepdims=True)
    y_km6 = KMeans(n_clusters=6, random_state=RANDOM_STATE,
                   n_init=10).fit_predict(Xn)
    print(f"\nARI(v1, kmeans6-normalized)  = {adjusted_rand_score(y_v1, y_km6):.3f}")
    print(f"NMI(v1, kmeans6-normalized)  = {normalized_mutual_info_score(y_v1, y_km6):.3f}")
    # also raw-space k-means (the paper's own geometry)
    y_km6r = KMeans(n_clusters=6, random_state=RANDOM_STATE,
                    n_init=10).fit_predict(X)
    print(f"ARI(v1, kmeans6-raw)         = {adjusted_rand_score(y_v1, y_km6r):.3f}")
    print(f"NMI(v1, kmeans6-raw)         = {normalized_mutual_info_score(y_v1, y_km6r):.3f}")

    # 3. citation communities x v1 clusters
    print(f"\nARI(citation, v1) = {adjusted_rand_score(y_cit, y_v1):.3f}")
    print(f"NMI(citation, v1) = {normalized_mutual_info_score(y_cit, y_v1):.3f}")
    cm = pd.crosstab(
        pd.Series([names.get(c, f"comm-{c}") for c in y_cit], name="citation"),
        pd.Series([f"{k}:{short(v1_labels[k])}" for k in y_v1], name="v1"),
        normalize="index")
    print("\nConfusion (rows = citation communities, row proportions):")
    print(cm.round(2).to_string())


if __name__ == "__main__":
    main()
