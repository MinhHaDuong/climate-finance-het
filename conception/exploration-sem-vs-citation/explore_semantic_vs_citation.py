"""Exploration: semantic structure vs direct-citation communities.

Reproduces the direct-citation Louvain partition of global_map.py (same seed),
then compares it with k-means clusters on normalized sentence embeddings.
Read-only exploration — outputs a PNG in the worktree and a text report.
"""

import argparse
import os
import sys
from collections import Counter

import community as community_louvain
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    adjusted_rand_score,
    normalized_mutual_info_score,
    silhouette_samples,
    silhouette_score,
)

sys.path.insert(0, "scripts")
sys.path.insert(0, "libs/openalex-corpus/src")

import yaml

RANDOM_STATE = 42  # config/analysis.yaml pre2007_traditions.louvain_seed

_REG_PATH = ("/home/haduong/Climate_finance/.claude/worktrees/"
             "agent-a47c0bce2b431187f/config/community_registry.yml")


def figure_communities(figure_name):
    with open(_REG_PATH) as f:
        reg = yaml.safe_load(f)
    return {int(cid): (reg["concepts"][k]["label"], reg["concepts"][k]["color"])
            for cid, k in reg["figures"].get(figure_name, {}).items()}
from openalex_corpus.text import normalize_doi
from pipeline_loaders import (
    load_refined_citations,
    load_refined_embeddings,
    load_refined_works,
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, help="PNG path for the 2D map")
    args = p.parse_args()

    cit = load_refined_citations()
    cit["source_doi"] = cit["source_doi"].apply(normalize_doi)
    cit["ref_doi"] = cit["ref_doi"].apply(normalize_doi)
    bad = {"", "nan", "none"}
    cit = cit[~cit["source_doi"].isin(bad) & ~cit["ref_doi"].isin(bad)]
    works = load_refined_works()
    emb = load_refined_embeddings()
    assert len(emb) == len(works), (len(emb), len(works))
    works = works.reset_index(drop=True)
    works["doi_norm"] = works["doi"].apply(normalize_doi)
    keep = ~works["doi_norm"].isin(bad)

    # doi -> embedding row (first occurrence)
    doi2row = {}
    for i, d in zip(works.index[keep], works.loc[keep, "doi_norm"]):
        doi2row.setdefault(d, i)
    doi2year = dict(zip(works.loc[keep, "doi_norm"], works.loc[keep, "year"]))

    corpus = set(works.loc[keep, "doi_norm"])
    sub = cit[cit["source_doi"].isin(corpus) & cit["ref_doi"].isin(corpus)]
    sub = sub[sub["source_doi"] != sub["ref_doi"]]
    G = nx.Graph()
    G.add_edges_from(sub[["source_doi", "ref_doi"]].drop_duplicates()
                     .itertuples(index=False, name=None))
    G.remove_nodes_from(list(nx.isolates(G)))
    print(f"direct graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    part = community_louvain.best_partition(G, random_state=RANDOM_STATE)
    n = G.number_of_nodes()
    sizes = Counter(part.values())
    big = [c for c, s in sizes.most_common() if s / n >= 0.02]
    print(f"big communities (>=2%): {big} sizes {[sizes[c] for c in big]}")

    reg = figure_communities("fig_global_map_direct")
    names = {c: (reg[c][0] if c in reg else f"comm-{c}") for c in big}
    colors = {c: (reg[c][1] if c in reg else "#999999") for c in big}

    # nodes in big communities with an embedding
    nodes = [d for d in G.nodes() if part[d] in big and d in doi2row]
    print(f"nodes in big communities with embedding: {len(nodes)} "
          f"(of {sum(sizes[c] for c in big)} in big communities)")
    X = emb[[doi2row[d] for d in nodes]].astype(np.float64)
    norms = np.linalg.norm(X, axis=1)
    ok = np.isfinite(X).all(axis=1) & (norms > 0)
    if not ok.all():
        print(f"dropping {(~ok).sum()} nodes with NaN/zero embeddings")
        nodes = [d for d, o in zip(nodes, ok) if o]
        X = X[ok]
        norms = norms[ok]
    X /= norms[:, None]
    y_cit = np.array([part[d] for d in nodes])

    # 1. k-means k=8
    km = KMeans(n_clusters=8, random_state=RANDOM_STATE, n_init=10)
    y_sem = km.fit_predict(X)
    ari = adjusted_rand_score(y_cit, y_sem)
    nmi = normalized_mutual_info_score(y_cit, y_sem)
    print(f"\nARI(citation, kmeans8) = {ari:.3f}")
    print(f"NMI(citation, kmeans8) = {nmi:.3f}")

    # silhouette-chosen k (on a subsample for speed)
    rng = np.random.default_rng(RANDOM_STATE)
    idx = rng.choice(len(X), size=min(6000, len(X)), replace=False)
    best = None
    for k in range(2, 13):
        lab = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=5).fit_predict(X)
        s = silhouette_score(X[idx], lab[idx], metric="cosine")
        print(f"  k={k:2d} silhouette={s:.4f}")
        if best is None or s > best[1]:
            best = (k, s)
    kbest = best[0]
    print(f"silhouette-best k = {kbest} (s={best[1]:.4f})")
    if kbest != 8:
        y_semb = KMeans(n_clusters=kbest, random_state=RANDOM_STATE,
                        n_init=10).fit_predict(X)
        print(f"ARI(citation, kmeans{kbest}) = {adjusted_rand_score(y_cit, y_semb):.3f}")
        print(f"NMI(citation, kmeans{kbest}) = {normalized_mutual_info_score(y_cit, y_semb):.3f}")

    # confusion matrix, row proportions
    df = pd.DataFrame({"cit": [names[c] for c in y_cit], "sem": y_sem})
    cm = pd.crosstab(df["cit"], df["sem"], normalize="index")
    cm = cm.loc[[names[c] for c in big]]
    print("\nConfusion matrix (rows = citation communities, row proportions):")
    print(cm.round(2).to_string())

    # 3. silhouette of citation communities in semantic space
    sil = silhouette_samples(X, y_cit, metric="cosine")
    comp = pd.Series(sil).groupby(pd.Series(y_cit)).mean().sort_values(ascending=False)
    print("\nSemantic compactness of citation communities (mean silhouette, cosine):")
    for c, v in comp.items():
        print(f"  {v:+.3f}  {names[c]} (n={int((y_cit == c).sum())})")

    # 4. acts composition
    yrs = pd.to_numeric(pd.Series([doi2year.get(d) for d in nodes]), errors="coerce")
    act = pd.cut(yrs, [-np.inf, 2006, 2014, np.inf], labels=["I <=2006", "II 2007-14", "III 2015+"])
    tab = pd.crosstab(pd.Series([names[c] for c in y_cit]), act, normalize="index")
    print("\nComposition by act (row proportions):")
    print(tab.round(2).to_string())

    # 2. PCA 2D map colored by citation community
    p2 = PCA(n_components=2, random_state=RANDOM_STATE).fit_transform(X)
    fig, ax = plt.subplots(figsize=(10, 8))
    for c in big:
        m = y_cit == c
        ax.scatter(p2[m, 0], p2[m, 1], s=4, alpha=0.35, color=colors[c],
                   label=f"{names[c]} (n={m.sum()})", linewidths=0)
    for c in big:
        m = y_cit == c
        cx, cy = p2[m, 0].mean(), p2[m, 1].mean()
        ax.text(cx, cy, names[c], fontsize=8, ha="center", va="center",
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=colors[c], alpha=0.85))
    ax.legend(loc="best", fontsize=7, markerscale=3)
    ax.set_title("Semantic map (PCA of sentence embeddings) colored by "
                 "direct-citation community")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    fig.tight_layout()
    fig.savefig(args.output, dpi=200)
    print(f"\nPNG: {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()
