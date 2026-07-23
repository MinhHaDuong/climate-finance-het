"""Semantic-cluster robustness and citation-vs-semantic structure (ticket 0310).

Results 5 and 6 of the data paper's literature confirmations:

5. The companion paper's six semantic clusters are robust: k-means variants
   (normalised embedding space; fewer restarts) reproduce the baseline
   partition of tab_sem6_assignments.csv — adjusted Rand index (ARI)
   between baseline and each variant.
6. Citation links carry more group structure than semantic similarity:
   ARI / normalized mutual information (NMI) between the direct-citation
   communities and the six semantic clusters, both read from the
   assignments artifact.

Deterministic: fixed seeds, canonical row order inherited from the
assignments artifact.

Output: tab_semantic_robustness.csv (metric, value), validated by
LitConfirmationsSchema (same long-format contract).

Usage:
    uv run python scripts/analysis/compute_semantic_robustness.py \
        --input deliverables/_shared/tables/tab_sem6_assignments.csv \
        --output deliverables/_shared/tables/tab_semantic_robustness.csv
"""

import os

import numpy as np
import pandas as pd
from pipeline_loaders import (
    load_analysis_config,
    load_refined_embeddings,
    load_refined_works,
)
from schemas import LitConfirmationsSchema
from script_io_args import parse_io_args, validate_io
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from utils import get_logger, normalize_doi

log = get_logger("compute_semantic_robustness")

BAD_DOIS = {"", "nan", "none"}


def embedding_matrix(dois):
    """Raw embedding rows for the assignment DOIs, in artifact order."""
    emb = load_refined_embeddings()
    works = load_refined_works().reset_index(drop=True)
    works["doi_norm"] = works["doi"].apply(normalize_doi)
    keep = ~works["doi_norm"].isin(BAD_DOIS)
    doi2row = {}
    for i, d in zip(works.index[keep], works.loc[keep, "doi_norm"]):
        doi2row.setdefault(d, i)
    return emb[[doi2row[d] for d in dois]].astype(np.float64)


def main():
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)
    cfg = load_analysis_config()["lit_confirmations"]
    k = int(cfg["sem_k"])
    seed = int(cfg["sem_seed"])

    assign = pd.read_csv(io_args.input[0])
    y_base = assign["sem_cluster"].to_numpy()
    y_cit = assign["cit_community"].to_numpy()
    X = embedding_matrix(assign["doi"].tolist())

    # Result 5: variant partitions vs baseline.
    Xn = X / np.linalg.norm(X, axis=1, keepdims=True)
    y_norm = KMeans(n_clusters=k, random_state=seed,
                    n_init=int(cfg["sem_n_init"])).fit_predict(Xn)
    y_ninit = KMeans(n_clusters=k, random_state=seed,
                     n_init=int(cfg["sem_n_init_variant"])).fit_predict(X)
    ari_norm = adjusted_rand_score(y_base, y_norm)
    ari_ninit = adjusted_rand_score(y_base, y_ninit)

    # Result 6: citation communities vs semantic clusters.
    ari_cit = adjusted_rand_score(y_cit, y_base)
    nmi_cit = normalized_mutual_info_score(y_cit, y_base)
    log.info("n=%d k=%d: ARI norm-variant=%.3f, n_init-variant=%.3f; "
             "citation-vs-semantic ARI=%.3f NMI=%.3f",
             len(y_base), k, ari_norm, ari_ninit, ari_cit, nmi_cit)

    df = pd.DataFrame(
        [
            ("sem6_n_works", float(len(y_base))),
            ("sem6_k", float(k)),
            ("sem6_ari_norm_variant", float(ari_norm)),
            ("sem6_ari_ninit_variant", float(ari_ninit)),
            ("sem6_ari_min_variant", float(min(ari_norm, ari_ninit))),
            ("citsem_ari", float(ari_cit)),
            ("citsem_nmi", float(nmi_cit)),
        ],
        columns=["metric", "value"],
    )
    LitConfirmationsSchema.validate(df)
    os.makedirs(os.path.dirname(io_args.output) or ".", exist_ok=True)
    df.to_csv(io_args.output, index=False)
    log.info("Wrote %d metrics to %s", len(df), io_args.output)


if __name__ == "__main__":
    main()
