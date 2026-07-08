"""Degree-preserving null model for tradition separation (ticket 0182).

Given a co-citation graph and a mapping of nodes to intellectual
traditions, measure whether the observed within-tradition cohesion
exceeds what the degree sequence alone produces. The null is a
configuration-model rewiring (``networkx.double_edge_swap``): edges are
reshuffled while every node keeps its degree, so any residual separation
in the null is attributable to sparsity / degree structure, not to a real
intellectual boundary.

Two separation statistics, both computed on the subgraph induced by the
tradition-assigned nodes:

- ``within_tradition_share`` — fraction of edges whose endpoints share a
  tradition. Higher = more separated. This is 1 - inter-tradition share.
- ``partition_modularity`` — Newman modularity of the tradition partition.

The statistics are unweighted: the sparsity concern is about the presence
of co-citation edges (degrees), and ``double_edge_swap`` preserves the
binary degree sequence exactly.
"""

import logging

import networkx as nx
import numpy as np

log = logging.getLogger(__name__)


def label_nodes_by_anchors(G, anchor_works, anchor_authors):
    """Assign graph nodes to traditions a priori, without community detection.

    Membership is fixed from the intellectual-history record (the
    ``@tbl-traditions`` anchor works and authors), never inferred from the
    graph's own structure. This is the non-circular labelling path: it calls
    no Louvain / modularity optimisation, so an "optimised partition beats the
    null" objection cannot apply to it.

    Parameters
    ----------
    G : networkx.Graph
        Nodes are reference DOIs; each carries an ``author`` attribute (the
        lowercased first-author surname).
    anchor_works : dict
        ``tradition -> [doi, ...]`` — nodes assigned by exact DOI match.
    anchor_authors : dict
        ``tradition -> [surname_substring, ...]`` — nodes assigned when their
        ``author`` attribute contains one of the substrings.

    Returns
    -------
    dict
        ``node -> tradition`` for assigned nodes only. Unmatched nodes are
        absent. A DOI match wins over an author match. A node whose author
        matches anchors of two or more traditions is ambiguous and dropped.

    """
    doi_to_tradition = {}
    for trad, dois in anchor_works.items():
        for doi in dois:
            doi_to_tradition[doi] = trad

    labels = {}
    for node in G.nodes():
        if node in doi_to_tradition:
            labels[node] = doi_to_tradition[node]
            continue
        author = str(G.nodes[node].get("author", "") or "").lower()
        if not author:
            continue
        matched = {
            trad
            for trad, anchors in anchor_authors.items()
            if any(a in author for a in anchors)
        }
        if len(matched) == 1:
            labels[node] = matched.pop()
        # zero matches -> unlabeled; two or more -> ambiguous, dropped
    return labels


def within_tradition_share(G, node_to_tradition):
    """Share of edges whose endpoints share a tradition.

    Counts only edges where *both* endpoints are assigned to a tradition
    (nodes mapped to ``None`` / absent are ignored). Returns NaN when no
    such edge exists.
    """
    within = 0
    total = 0
    for u, v in G.edges():
        tu = node_to_tradition.get(u)
        tv = node_to_tradition.get(v)
        if tu is None or tv is None:
            continue
        total += 1
        if tu == tv:
            within += 1
    if total == 0:
        return float("nan")
    return within / total


def partition_modularity(G, node_to_tradition):
    """Newman modularity of the tradition partition (tradition nodes only).

    Computed UNWEIGHTED (``weight=None``): the sparsity concern is about the
    presence of co-citation edges, and ``double_edge_swap`` preserves only the
    binary degree sequence. Unweighted modularity is a deliberate design
    choice, not the networkx default (which weights by the co-citation edge
    ``weight`` attribute).

    Note on non-independence: for a fixed partition on the tradition-induced
    subgraph, Q = within_tradition_share - K, where
    K = Σ_c (d_c / 2m)^2 is invariant under any degree-preserving rewiring
    (degrees and edge count fixed). So the unweighted modularity is an affine
    image of within_tradition_share with the SAME variance and z-score under
    the null — a descriptive companion, not an independent second test. That
    is why within_tradition_share is reported as the single primary statistic.
    """
    nodes = [n for n in G.nodes() if node_to_tradition.get(n) is not None]
    H = G.subgraph(nodes)
    if H.number_of_edges() == 0:
        return float("nan")
    communities = {}
    for n in nodes:
        communities.setdefault(node_to_tradition[n], set()).add(n)
    return nx.community.modularity(H, communities.values(), weight=None)


def rewire_degree_preserving(G, seed, n_swaps_factor=10):
    """Return a degree-preserving rewiring of ``G`` (configuration model).

    Uses ``networkx.double_edge_swap`` — every node keeps its degree while
    edges are reshuffled. A graph too small to swap (< 2 edges or < 4
    nodes) is returned unchanged. The swap count scales with the edge
    count so the graph is thoroughly randomised.

    Returns
    -------
    (networkx.Graph, bool)
        The rewired graph and a ``truncated`` flag. ``truncated`` is True
        when ``double_edge_swap`` raised ``NetworkXAlgorithmError`` — the
        requested number of swaps was not reached within ``max_tries`` and
        the graph is only partially mixed. The caller must not treat a
        truncated replicate as a fully mixed configuration-model draw.

    """
    H = G.copy()
    m = H.number_of_edges()
    if m < 2 or H.number_of_nodes() < 4:
        return H, False
    nswap = max(1, n_swaps_factor * m)
    try:
        nx.double_edge_swap(H, nswap=nswap, max_tries=nswap * 20, seed=seed)
    except nx.NetworkXAlgorithmError:
        # Fewer than nswap valid swaps found within max_tries: partial mixing.
        # Flag it so the null test can report it rather than silently accept
        # an under-randomised replicate.
        return H, True
    return H, False


def _swap_target(G, n_swaps_factor=10):
    """Number of double-edge swaps requested per rewiring (0 if too small)."""
    m = G.number_of_edges()
    if m < 2 or G.number_of_nodes() < 4:
        return 0
    return max(1, n_swaps_factor * m)


def null_separation_test(G, node_to_tradition, statistic_fn, n_perm, seed):
    """Permutation test: observed separation vs degree-preserving null.

    Parameters
    ----------
    G : networkx.Graph
        Graph to test — pass the subgraph induced by the tradition nodes
        so the rewiring preserves the induced degree sequence.
    node_to_tradition : dict
        Node -> tradition label.
    statistic_fn : callable
        ``(G, node_to_tradition) -> float`` separation statistic; higher
        means more separated.
    n_perm : int
        Number of rewired null replicates.
    seed : int
        Master seed for the permutation RNG.

    Returns
    -------
    dict
        observed, null_mean, null_std, z_score, p_value, n_perm, seed,
        n_truncated. The empirical p is one-sided: P(null >= observed),
        add-one smoothed. z is NaN when the null has zero spread.
        ``n_truncated`` counts replicates whose degree-preserving rewiring
        did not reach the requested swap count (partial mixing) — a nonzero
        value warns that some null draws are under-randomised.

    """
    observed = statistic_fn(G, node_to_tradition)
    rng = np.random.default_rng(seed)
    null_vals = np.empty(n_perm, dtype=float)
    n_truncated = 0
    for i in range(n_perm):
        swap_seed = int(rng.integers(0, 2**31 - 1))
        H, truncated = rewire_degree_preserving(G, seed=swap_seed)
        if truncated:
            n_truncated += 1
        null_vals[i] = statistic_fn(H, node_to_tradition)

    nswap = _swap_target(G)
    log.info(
        "Null: %d rewirings, %d swaps requested each; %d truncated (partial mixing)",
        n_perm, nswap, n_truncated,
    )
    if n_truncated:
        log.warning(
            "%d/%d degree-preserving rewirings truncated before %d swaps — "
            "those null draws are under-randomised",
            n_truncated, n_perm, nswap,
        )

    null_mean = float(np.nanmean(null_vals))
    null_std = float(np.nanstd(null_vals, ddof=1))
    z = (observed - null_mean) / null_std if null_std > 0 else float("nan")
    n_ge = int(np.sum(null_vals >= observed))
    p = (n_ge + 1) / (n_perm + 1)
    return {
        "observed": float(observed),
        "null_mean": null_mean,
        "null_std": null_std,
        "z_score": float(z),
        "p_value": float(p),
        "n_perm": int(n_perm),
        "seed": int(seed),
        "n_truncated": int(n_truncated),
    }
