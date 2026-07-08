"""SCOUT: cross-tradition citation coupling over time (0182/0183 follow-up).

Reframes the "three traditions were separate then integrated at crystallization"
claim as a citation-coupling TIME SERIES rather than the static co-citation test
that came back DEMOTE (0182). Three methods, side by side:

  1. SOFT-MEMBERSHIP COUPLING (primary). Each work gets a membership
     DISTRIBUTION m(w) over the three tradition centroids (softmax of the cosine
     similarities at temperature T). For a citation edge A->B the within-
     tradition-ness is the soft generalisation of the within-tradition share:
     c(A,B) = m(A) . m(B) = P(same tradition). Per year, the statistic is the
     mean of c over that year's citation edges. A DECLINE over time = the
     traditions blend = integration.

  2. NO-SCAFFOLD CROSS-CHECK. Drop traditions/centroids entirely: per year, the
     mean cosine DISTANCE between the embeddings of citing and cited works. If
     traditions merge, citations bridge wider semantic gaps, so this RISES over
     time. Convergence with method 1 = robust; divergence = a reported tension.

  3. HARD-ASSIGNMENT ASSORTATIVITY (comparison). Nearest-centroid labels +
     Newman categorical assortativity per year. The lossy baseline the author
     asked to keep as a third row.

All three share the same density/retro-indexing control: a per-year z-score
against a null that keeps the graph fixed and permutes the node property
(membership vector / embedding / label) across the nodes present that year, so a
trend cannot be a mechanical artefact of the corpus growing denser or better
DOI-indexed over time (the confound flagged in 0071).

Membership is content-only (embeddings), assigned to ALL works, independent of
the citation graph it is then tested on -- avoiding both the degeneracy (only
~20 anchors labelled) and the circularity (Louvain optimised on the tested
graph) of the 0182 test.

This is recon: loaders + config seed, no Pandera/Makefile/test ceremony.

Reproduce:
  CLIMATE_FINANCE_DATA=$PWD/data HF_HOME=/home/haduong/data/cache/huggingface \\
    HF_HUB_DISABLE_PROGRESS_BARS=1 TQDM_DISABLE=1 \\
    uv run python scripts/scout_tradition_coupling.py \\
    --output content/figures/scratch/scout_tradition_coupling.png
"""

import argparse
import logging
import os

import numpy as np
import pandas as pd
import pipeline_loaders as pl
from pipeline_text import normalize_doi

log = logging.getLogger("scout.tradition_coupling")

SEED = 20260708
YEAR_LO, YEAR_HI = 1990, 2018
CRYST_LO, CRYST_HI = 2007, 2014
N_PERM = 500
MIN_EDGES = 30
TEMP = 0.10  # primary softmax temperature for soft membership
TEMP_GRID = [0.05, 0.10, 0.20]  # sensitivity sweep

# @tbl-traditions key references. (doi, title) -- title is the fresh-embed
# fallback when the work is not a corpus work (no aligned embedding).
ANCHORS: dict[str, dict[str, tuple[str | None, str]]] = {
    "env_econ": {
        "ayres_kneese1969": (None, "Production, Consumption, and Externalities"),
        "nordhaus1992": (
            "10.1126/science.258.5086.1315",
            "An Optimal Transition Path for Controlling Greenhouse Gases",
        ),
        "manne_richels1992": (
            "10.1016/0301-4215(92)90024-V",
            "Buying Greenhouse Insurance",
        ),
        "stern2007": (None, "The Economics of Climate Change: The Stern Review"),
        "weitzman2007": (
            "10.1257/jel.45.3.703",
            "A Review of the Stern Review on the Economics of Climate Change",
        ),
        "weitzman2009": (
            "10.1162/rest.91.1.1",
            "On Modeling and Interpreting the Economics of Catastrophic Climate Change",
        ),
    },
    "development": {
        "desrosieres1998": (
            None,
            "The Politics of Large Numbers: A History of Statistical Reasoning",
        ),
        "michaelowa2007": (
            "10.1007/s10584-007-9270-3",
            "Climate or Development: Is ODA Diverted from Its Original Purpose?",
        ),
    },
    "burden_sharing": {
        "negishi1960": (
            "10.1111/j.1467-999X.1960.tb00275.x",
            "Welfare Economics and Existence of an Equilibrium for a Competitive Economy",
        ),
        "michaelowa2019": (
            "10.1002/wcc.613",
            "Evolution of International Carbon Markets: Lessons for the Paris Agreement",
        ),
        "stadelmann2011": (
            "10.1080/17565529.2011.599550",
            "New and Additional to What? Assessing Options for Baselines to Assess Climate Finance Pledges",
        ),
    },
}
TRADS = list(ANCHORS.keys())


def _l2(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float64)
    return v / (np.linalg.norm(v) + 1e-12)


def _l2_rows(m: np.ndarray) -> np.ndarray:
    m = np.asarray(m, dtype=np.float64)
    return m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-12)


def build_centroids(works: pd.DataFrame, emb: np.ndarray):
    """Return (centroids[3,D], sims[N,3], provenance). Content only."""
    ndoi = works["doi"].map(lambda x: normalize_doi(x) if pd.notna(x) else "")
    doi2idx = {d: i for i, d in enumerate(ndoi) if d}

    cent_vecs: dict[str, list] = {t: [] for t in TRADS}
    provenance: dict[str, list] = {t: [] for t in TRADS}
    fresh: dict[tuple, str] = {}
    for t, d in ANCHORS.items():
        for key, (doi, title) in d.items():
            idx = doi2idx.get(normalize_doi(doi)) if doi else None
            if idx is not None:
                cent_vecs[t].append(_l2(emb[idx]))
                provenance[t].append((key, "corpus"))
            else:
                fresh[(t, key)] = title

    if fresh:
        from sentence_transformers import SentenceTransformer

        log.info("Embedding %d absent anchors fresh with bge-m3", len(fresh))
        model = SentenceTransformer("BAAI/bge-m3")
        vecs = model.encode(list(fresh.values()), normalize_embeddings=False)
        for (t, key), vec in zip(fresh.keys(), vecs):
            cent_vecs[t].append(_l2(vec))
            provenance[t].append((key, "fresh_title"))

    centroids = np.vstack([_l2(np.mean(np.vstack(cent_vecs[t]), axis=0)) for t in TRADS])
    sims = _l2_rows(emb) @ centroids.T  # cosine similarity of every work to each centroid
    return centroids, sims, provenance


def soft_membership(sims: np.ndarray, temp: float) -> np.ndarray:
    """Softmax of cosine sims at temperature `temp` -> membership distribution."""
    z = sims / temp
    z = z - z.max(axis=1, keepdims=True)
    ex = np.exp(z)
    return ex / ex.sum(axis=1, keepdims=True)


def internal_edges(citations, works, labels):
    """Corpus-internal citation edges dated by the CITING paper's year."""
    ndoi = works["doi"].map(lambda x: normalize_doi(x) if pd.notna(x) else "")
    doi2node = {d: i for i, d in enumerate(ndoi) if d}
    src = citations["source_doi"].map(lambda x: normalize_doi(x) if pd.notna(x) else "")
    ref = citations["ref_doi"].map(lambda x: normalize_doi(x) if pd.notna(x) else "")
    si = src.map(doi2node)
    ri = ref.map(doi2node)
    mask = si.notna() & ri.notna()
    si = si[mask].astype(int).to_numpy()
    ri = ri[mask].astype(int).to_numpy()
    keep = si != ri
    si, ri = si[keep], ri[keep]
    years = works["year"].to_numpy()
    return pd.DataFrame(
        {
            "src_node": si,
            "ref_node": ri,
            "src_lab": labels[si],
            "ref_lab": labels[ri],
            "cite_year": years[si],
        }
    )


# --- method 3: hard-assignment assortativity -------------------------------


def assortativity_from_pairs(lab_a, lab_b, k):
    """Newman categorical assortativity from edge label-pairs (symmetrised)."""
    if len(lab_a) == 0:
        return np.nan
    e = np.zeros((k, k), dtype=np.float64)
    np.add.at(e, (lab_a, lab_b), 1.0)
    e = e + e.T
    tot = e.sum()
    if tot == 0:
        return np.nan
    e /= tot
    a, b = e.sum(axis=1), e.sum(axis=0)
    denom = 1.0 - float((a * b).sum())
    if abs(denom) < 1e-12:
        return np.nan
    return (float(np.trace(e)) - float((a * b).sum())) / denom


def yearly_assortativity(edges, labels, rng):
    k = len(TRADS)
    rows = []
    for year in range(YEAR_LO, YEAR_HI + 1):
        ye = edges[edges["cite_year"] == year]
        if len(ye) < MIN_EDGES:
            rows.append(dict(year=year, n_edges=len(ye), obs=np.nan, z=np.nan))
            continue
        la, lb = ye["src_lab"].to_numpy(), ye["ref_lab"].to_numpy()
        obs = assortativity_from_pairs(la, lb, k)
        nodes = np.unique(np.concatenate([ye["src_node"].to_numpy(), ye["ref_node"].to_numpy()]))
        node_lab = labels[nodes]
        pos = {n: i for i, n in enumerate(nodes)}
        sp = ye["src_node"].map(pos).to_numpy()
        rp = ye["ref_node"].map(pos).to_numpy()
        null = np.array(
            [assortativity_from_pairs(pm[sp], pm[rp], k) for pm in (rng.permutation(node_lab) for _ in range(N_PERM))]
        )
        z = (obs - np.nanmean(null)) / (np.nanstd(null) + 1e-12)
        rows.append(dict(year=year, n_edges=len(ye), obs=obs, z=z, null_mean=float(np.nanmean(null))))
    return pd.DataFrame(rows)


# --- methods 1 & 2: edge-metric over a per-node property matrix ------------


def yearly_edge_metric(edges, node_matrix, reducer, rng):
    """Per-year mean edge statistic + z vs a node-permuted null.

    node_matrix[node] -> vector; reducer(V_src, V_ref) -> scalar over the edges.
    The null shuffles which present node carries which property vector.
    """
    rows = []
    for year in range(YEAR_LO, YEAR_HI + 1):
        ye = edges[edges["cite_year"] == year]
        n = len(ye)
        if n < MIN_EDGES:
            rows.append(dict(year=year, n_edges=n, obs=np.nan, z=np.nan))
            continue
        src = ye["src_node"].to_numpy()
        ref = ye["ref_node"].to_numpy()
        obs = reducer(node_matrix[src], node_matrix[ref])
        nodes = np.unique(np.concatenate([src, ref]))
        pos = {nn: i for i, nn in enumerate(nodes)}
        sp = np.fromiter((pos[x] for x in src), dtype=int, count=n)
        rp = np.fromiter((pos[x] for x in ref), dtype=int, count=n)
        subv = node_matrix[nodes]
        null = np.empty(N_PERM)
        for p in range(N_PERM):
            pv = subv[rng.permutation(len(nodes))]
            null[p] = reducer(pv[sp], pv[rp])
        z = (obs - null.mean()) / (null.std() + 1e-12)
        rows.append(dict(year=year, n_edges=n, obs=obs, z=z, null_mean=float(null.mean())))
    return pd.DataFrame(rows)


def _coupling_reducer(a, b):
    return float(np.sum(a * b, axis=1).mean())  # mean m(A).m(B)


def _distance_reducer(a, b):
    return float((1.0 - np.sum(a * b, axis=1)).mean())  # mean cosine distance (unit rows)


# --- change point ----------------------------------------------------------


def change_point(series, rng):
    """pre-2007 (1990-2006) vs post-2009 (2010-2018) mean of `obs`, bootstrap CI of the diff."""
    pre = series[(series.year >= 1990) & (series.year <= 2006)]["obs"].dropna().to_numpy()
    post = series[(series.year >= 2010) & (series.year <= 2018)]["obs"].dropna().to_numpy()
    if len(pre) == 0 or len(post) == 0:
        return dict(pre_mean=np.nan, post_mean=np.nan, diff=np.nan, ci=(np.nan, np.nan), pre_n=len(pre), post_n=len(post))
    boot = np.array([rng.choice(pre, len(pre)).mean() - rng.choice(post, len(post)).mean() for _ in range(5000)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return dict(
        pre_mean=float(pre.mean()),
        post_mean=float(post.mean()),
        diff=float(pre.mean() - post.mean()),
        ci=(float(lo), float(hi)),
        pre_n=len(pre),
        post_n=len(post),
    )


def _report(name, series, cp, higher_is_separation=True):
    log.info("\n=== %s ===", name)
    log.info("%s", series[["year", "n_edges", "obs", "z"]].round(4).to_string(index=False))
    direction = "decline (pre>post) = integration" if higher_is_separation else "rise (post>pre) = integration"
    log.info("pre-2007 mean=%.4f  post-2009 mean=%.4f  diff(pre-post)=%.4f  95%% CI [%.4f, %.4f]  [%s]",
             cp["pre_mean"], cp["post_mean"], cp["diff"], cp["ci"][0], cp["ci"][1], direction)
    zpre = series[(series.year <= 2006)]["z"].dropna()
    zpost = series[(series.year >= 2010)]["z"].dropna()
    log.info("z vs null: pre-2007 mean=%.2f  post-2009 mean=%.2f", zpre.mean(), zpost.mean())


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", required=True, help="figure output path (png)")
    args = ap.parse_args(argv)

    log.info("Loading corpus (works, embeddings, citations)...")
    works = pl.load_refined_works().reset_index(drop=True)
    emb = pl.load_refined_embeddings()
    assert len(works) == len(emb), (len(works), len(emb))
    citations = pl.load_refined_citations()

    centroids, sims, provenance = build_centroids(works, emb)
    hard_labels = sims.argmax(1)
    soft = soft_membership(sims, TEMP)
    en = _l2_rows(emb)

    log.info("\n=== ANCHOR PROVENANCE ===")
    for t in TRADS:
        log.info("  %s: %s", t, provenance[t])

    log.info("\n=== HARD MEMBERSHIP COUNTS (nearest centroid) ===")
    hl = pd.Series([TRADS[i] for i in hard_labels])
    log.info("full corpus:\n%s", hl.value_counts().to_string())
    for lo, hi, name in [(1990, 2006, "pre-2007"), (2007, 2014, "crystallization"), (2015, 2025, "established")]:
        m = ((works.year >= lo) & (works.year <= hi)).to_numpy()
        log.info("%s (n=%d):\n%s", name, int(m.sum()), hl[m].value_counts().to_string())

    log.info("\n=== SOFT MEMBERSHIP (softmax T=%.2f) mean mass per tradition ===", TEMP)
    log.info("full corpus mean mass: %s", dict(zip(TRADS, soft.mean(0).round(3))))

    edges = internal_edges(citations, works, hard_labels)
    log.info("\n=== CITATION GRAPH ===")
    log.info("corpus-internal citation edges: %d", len(edges))

    # METHOD 1: soft coupling (primary)
    soft_series = yearly_edge_metric(edges, soft, _coupling_reducer, np.random.default_rng(SEED))
    cp_soft = change_point(soft_series, np.random.default_rng(SEED + 1))
    _report("METHOD 1 (PRIMARY): SOFT-MEMBERSHIP COUPLING mean m(A).m(B), T=%.2f" % TEMP,
            soft_series, cp_soft, higher_is_separation=True)

    # METHOD 2: no-scaffold citation distance
    dist_series = yearly_edge_metric(edges, en, _distance_reducer, np.random.default_rng(SEED))
    cp_dist = change_point(dist_series, np.random.default_rng(SEED + 2))
    _report("METHOD 2: NO-SCAFFOLD mean citing-cited cosine DISTANCE", dist_series, cp_dist,
            higher_is_separation=False)

    # METHOD 3: hard assortativity (comparison)
    hard_series = yearly_assortativity(edges, hard_labels, np.random.default_rng(SEED))
    cp_hard = change_point(hard_series, np.random.default_rng(SEED + 3))
    _report("METHOD 3 (COMPARISON): HARD-ASSIGNMENT ASSORTATIVITY", hard_series, cp_hard,
            higher_is_separation=True)

    # Temperature sensitivity of the primary metric
    log.info("\n=== SOFT-COUPLING TEMPERATURE SENSITIVITY (pre-2007 vs post-2009 mean) ===")
    for T in TEMP_GRID:
        sm = soft_membership(sims, T)
        ss = yearly_edge_metric(edges, sm, _coupling_reducer, np.random.default_rng(SEED))
        c = change_point(ss, np.random.default_rng(SEED + 7))
        log.info("T=%.2f: pre=%.4f post=%.4f diff=%.4f CI[%.4f,%.4f]",
                 T, c["pre_mean"], c["post_mean"], c["diff"], c["ci"][0], c["ci"][1])

    _plot(soft_series, dist_series, hard_series, args.output)
    log.info("\nFigure written to %s", args.output)


def _plot(soft_series, dist_series, hard_series, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(os.path.dirname(output), exist_ok=True)
    fig, axes = plt.subplots(3, 1, figsize=(9, 10), sharex=True)

    def shade(ax):
        ax.axvspan(CRYST_LO, CRYST_HI, color="orange", alpha=0.15)

    a = soft_series.dropna(subset=["obs"])
    shade(axes[0])
    axes[0].plot(a.year, a.obs, "o-", color="#1f77b4", label="soft coupling mean m(A)·m(B)")
    axes[0].plot(a.year, a.null_mean, ":", color="grey", label="permutation null")
    axes[0].set_ylabel("soft coupling")
    axes[0].set_title("Cross-tradition citation coupling over time (SCOUT, seed %d)" % SEED)
    axes[0].legend(fontsize=8)

    d = dist_series.dropna(subset=["obs"])
    shade(axes[1])
    axes[1].plot(d.year, d.obs, "^-", color="#2ca02c", label="no-scaffold citing–cited cosine distance")
    axes[1].plot(d.year, d.null_mean, ":", color="grey", label="permutation null (random pairs)")
    axes[1].set_ylabel("citation distance")
    axes[1].legend(fontsize=8)

    shade(axes[2])
    for s, c, m, lab in [
        (soft_series, "#1f77b4", "o", "soft coupling z"),
        (dist_series, "#2ca02c", "^", "no-scaffold distance z"),
        (hard_series, "#d62728", "s", "hard assortativity z"),
    ]:
        ss = s.dropna(subset=["z"])
        axes[2].plot(ss.year, ss.z, m + "-", color=c, label=lab, ms=4)
    axes[2].axhline(0, color="grey", lw=0.6, ls=":")
    axes[2].axhline(1.96, color="grey", lw=0.6, ls="--")
    axes[2].axhline(-1.96, color="grey", lw=0.6, ls="--")
    axes[2].set_ylabel("z vs null")
    axes[2].set_xlabel("citing-paper year")
    axes[2].legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
