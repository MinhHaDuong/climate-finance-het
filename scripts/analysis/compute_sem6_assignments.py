"""Per-work semantic-cluster and citation-community assignments (ticket 0310).

Reproducibility artifact behind the data paper's semantic-robustness and
citation-vs-semantic confirmations (results 5 and 6): for every corpus work
that sits in a major direct-citation community and has a valid embedding,
the baseline k-means semantic cluster (raw embedding space, the companion
paper's geometry) and the Louvain citation community id.

Deterministic by construction: fixed KMeans random_state and n_init from
config, the shared Louvain seed, and canonical DOI-sorted row order.

Output: tab_sem6_assignments.csv (doi, year, sem_cluster, cit_community),
validated by Sem6AssignmentsSchema.

Usage:
    uv run python scripts/analysis/compute_sem6_assignments.py \
        --output deliverables/_shared/tables/tab_sem6_assignments.csv
"""

import os

import community as community_louvain
import numpy as np
import pandas as pd
from analyze_global_map import direct_graph, load_data
from pipeline_loaders import (
    load_analysis_config,
    load_refined_embeddings,
    load_refined_works,
)
from schemas import Sem6AssignmentsSchema
from script_io_args import parse_io_args, validate_io
from sklearn.cluster import KMeans
from utils import get_logger, normalize_doi

log = get_logger("compute_sem6_assignments")

BAD_DOIS = {"", "nan", "none"}
MIN_SHARE = 0.02  # major-community threshold, as in the global map


def analysis_set():
    """Nodes of major citation communities with a finite non-zero embedding.

    Returns (dois, X, y_cit, years): DOI list sorted for determinism, raw
    embedding matrix, citation community ids, publication years.
    """
    cit, works, _meta = load_data()
    G, _rank = direct_graph(cit, works)
    seed = int(load_analysis_config()["pre2007_traditions"]["louvain_seed"])
    part = community_louvain.best_partition(G, weight="weight", random_state=seed)
    n = G.number_of_nodes()
    sizes = pd.Series(part).value_counts()
    big = set(sizes[sizes / n >= MIN_SHARE].index)

    emb = load_refined_embeddings()
    all_works = load_refined_works().reset_index(drop=True)
    assert len(emb) == len(all_works), (len(emb), len(all_works))
    all_works["doi_norm"] = all_works["doi"].apply(normalize_doi)
    keep = ~all_works["doi_norm"].isin(BAD_DOIS)
    doi2row, doi2year = {}, {}
    for i, d, y in zip(all_works.index[keep], all_works.loc[keep, "doi_norm"],
                       all_works.loc[keep, "year"]):
        doi2row.setdefault(d, i)
        doi2year.setdefault(d, y)

    dois = sorted(d for d in G.nodes() if part[d] in big and d in doi2row)
    X = emb[[doi2row[d] for d in dois]].astype(np.float64)
    norms = np.linalg.norm(X, axis=1)
    ok = np.isfinite(X).all(axis=1) & (norms > 0)
    if not ok.all():
        log.info("dropping %d works with NaN/zero embeddings", int((~ok).sum()))
        dois = [d for d, o in zip(dois, ok) if o]
        X = X[ok]
    y_cit = np.array([part[d] for d in dois])
    years = [doi2year.get(d) for d in dois]
    log.info("analysis set: %d works in %d major communities",
             len(dois), len(big))
    return dois, X, y_cit, years


def main():
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)
    cfg = load_analysis_config()["lit_confirmations"]

    dois, X, y_cit, years = analysis_set()
    km = KMeans(n_clusters=int(cfg["sem_k"]),
                random_state=int(cfg["sem_seed"]),
                n_init=int(cfg["sem_n_init"]))
    y_sem = km.fit_predict(X)

    df = pd.DataFrame({
        "doi": dois,
        "year": pd.to_numeric(pd.Series(years), errors="coerce"),
        "sem_cluster": y_sem,
        "cit_community": y_cit,
    })
    Sem6AssignmentsSchema.validate(df)
    os.makedirs(os.path.dirname(io_args.output) or ".", exist_ok=True)
    df.to_csv(io_args.output, index=False)
    log.info("Wrote %d assignments to %s", len(df), io_args.output)


if __name__ == "__main__":
    main()
