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

import networkx as nx
import numpy as np


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
    """Newman modularity of the tradition partition (tradition nodes only)."""
    nodes = [n for n in G.nodes() if node_to_tradition.get(n) is not None]
    H = G.subgraph(nodes)
    if H.number_of_edges() == 0:
        return float("nan")
    communities = {}
    for n in nodes:
        communities.setdefault(node_to_tradition[n], set()).add(n)
    return nx.community.modularity(H, communities.values())


def rewire_degree_preserving(G, seed, n_swaps_factor=10):
    """Return a degree-preserving rewiring of ``G`` (configuration model).

    Uses ``networkx.double_edge_swap`` — every node keeps its degree while
    edges are reshuffled. A graph too small to swap (< 2 edges or < 4
    nodes) is returned unchanged. The swap count scales with the edge
    count so the graph is thoroughly randomised.
    """
    H = G.copy()
    m = H.number_of_edges()
    if m < 2 or H.number_of_nodes() < 4:
        return H
    nswap = max(1, n_swaps_factor * m)
    try:
        nx.double_edge_swap(H, nswap=nswap, max_tries=nswap * 20, seed=seed)
    except (nx.NetworkXError, nx.NetworkXAlgorithmError):
        # Not enough valid swaps found; H still holds the swaps done so far.
        pass
    return H


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
        observed, null_mean, null_std, z_score, p_value, n_perm, seed.
        The empirical p is one-sided: P(null >= observed), add-one
        smoothed. z is NaN when the null has zero spread.

    """
    observed = statistic_fn(G, node_to_tradition)
    rng = np.random.default_rng(seed)
    null_vals = np.empty(n_perm, dtype=float)
    for i in range(n_perm):
        swap_seed = int(rng.integers(0, 2**31 - 1))
        H = rewire_degree_preserving(G, seed=swap_seed)
        null_vals[i] = statistic_fn(H, node_to_tradition)

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
    }
