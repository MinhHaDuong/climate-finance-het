#!/usr/bin/env python3
"""Embed the HET corpus and compute its first principal component (PCA1).

One-off companion to het_build_corpus.py -- see that script's docstring for
context. Deliberately does NOT call enrich_embeddings.py: that script filters
works outside config/analysis.yaml's periodization (1990-2024), which would
drop nearly this entire 1916-1992 corpus, and it writes into the shared
enrich_cache/ used by the main climate-finance pipeline. Text-building
follows the same convention (title + abstract + keywords) via a local import
of enrich_embeddings.build_text.

Model: paraphrase-multilingual-MiniLM-L12-v2, not the main pipeline's
BAAI/bge-m3 -- this host (doudou) has no GPU, and bge-m3 (24 layers, 1024-dim)
is impractically slow to encode even 1162 short texts in fp32 on CPU (repeated
runs were killed after several minutes without finishing). MiniLM-L12 is
~5x smaller, still multilingual (this corpus has French/German/Swedish
titles), and adequate for a qualitative semantic-landscape axis -- it is not
being used for any quantitative claim that requires bge-m3's precision.

Outputs:
  data/het/embeddings.npz  -- openalex_id keys + vectors (gitignored)
  data/het/works_pca.csv   -- works.csv + a pca1 column
"""

import argparse
import os

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

import numpy as np
import pandas as pd
from enrich_embeddings import build_text
from sklearn.decomposition import PCA
from utils import get_logger

log = get_logger("het_embed")

_HERE = os.path.dirname(os.path.abspath(__file__))
HET_DIR = os.path.join(os.path.dirname(_HERE), "data", "het")
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def embed_works(df):
    """Encode title+abstract+keywords for every work with the shared model."""
    import torch
    from sentence_transformers import SentenceTransformer

    texts = df.apply(build_text, axis=1).tolist()
    n_cpu = os.cpu_count() or 4
    torch.set_num_threads(n_cpu)
    log.info("Loading %s (%d threads)...", MODEL_NAME, n_cpu)
    model = SentenceTransformer(MODEL_NAME)
    if torch.cuda.is_available():
        model.half()  # halves VRAM; CPU has no fast fp16 kernels, so fp32 there
    log.info("Encoding %d texts...", len(texts))
    return model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)


def compute_pca1(vectors):
    """First principal component of the embedding vectors (deterministic, full SVD)."""
    pca = PCA(n_components=1, svd_solver="full")
    coords = pca.fit_transform(vectors)[:, 0]
    log.info("PCA1 explained variance ratio: %.3f", pca.explained_variance_ratio_[0])
    return coords


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--works-input", default=os.path.join(HET_DIR, "works.csv"))
    parser.add_argument("--output-embeddings", default=os.path.join(HET_DIR, "embeddings.npz"))
    parser.add_argument("--output-works", default=os.path.join(HET_DIR, "works_pca.csv"))
    args = parser.parse_args()

    df = pd.read_csv(args.works_input)
    df["abstract"] = df["abstract"].fillna("")
    df["keywords"] = df["keywords"].fillna("")
    has_title = df["title"].notna() & (df["title"].str.len() > 0)
    df = df[has_title].reset_index(drop=True)
    log.info("Works with titles: %d", len(df))

    vectors = embed_works(df)
    np.savez_compressed(
        args.output_embeddings,
        openalex_id=df["openalex_id"].values,
        vectors=vectors,
        model=np.array(MODEL_NAME),
    )
    log.info("Saved %d embeddings -> %s", len(vectors), args.output_embeddings)

    df["pca1"] = compute_pca1(vectors)
    df.to_csv(args.output_works, index=False)
    log.info("Wrote %d works with pca1 -> %s", len(df), args.output_works)


if __name__ == "__main__":
    main()
