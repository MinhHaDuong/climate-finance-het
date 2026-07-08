"""Tests for the pre-2007 tradition-separation null model (ticket 0182).

The claim under test: the three intellectual traditions (environmental
economics, development economics, burden-sharing) were structurally
*separate* in the pre-2007 co-citation graph. Because that graph is the
sparsest slice of the corpus, co-citation would show separation almost
regardless. The null model conditions on the degree sequence: does the
observed within-tradition cohesion exceed what degree-preserving rewiring
(configuration model) produces?

Red test: a graph of three cliques must yield observed separation >> null;
a random graph of the same degree sequence must not.
"""

import os
import sys

import networkx as nx

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)


def _three_cliques(size=6):
    """Three disjoint cliques, each mapped to one tradition."""
    G = nx.Graph()
    node_to_tradition = {}
    for t in range(3):
        base = t * size
        nodes = list(range(base, base + size))
        for i in range(len(nodes)):
            node_to_tradition[nodes[i]] = f"trad{t}"
            for j in range(i + 1, len(nodes)):
                G.add_edge(nodes[i], nodes[j])
    return G, node_to_tradition


def test_within_tradition_share_perfect_separation():
    """Three cliques with the clique partition are perfectly separated."""
    from _null_separation import within_tradition_share

    G, node_to_tradition = _three_cliques()
    assert within_tradition_share(G, node_to_tradition) == 1.0


def test_rewiring_preserves_degree():
    """Degree-preserving rewiring keeps every node's degree unchanged."""
    from _null_separation import rewire_degree_preserving

    G, _ = _three_cliques()
    before = dict(G.degree())
    H = rewire_degree_preserving(G, seed=7)
    after = dict(H.degree())
    assert before == after


def test_three_cliques_beat_rewired_null():
    """Three cliques: observed separation >> null; random graph: not.

    Exit-criterion test. The clique graph must produce a large positive
    z and a tiny empirical p (separation exceeds the sparsity-conditioned
    null). A random graph of the same degree sequence must produce a
    small z and a non-significant p (separation is what sparsity alone
    yields).
    """
    from _null_separation import null_separation_test, within_tradition_share

    G, node_to_tradition = _three_cliques()

    cliques = null_separation_test(
        G, node_to_tradition, within_tradition_share, n_perm=200, seed=42
    )
    assert cliques["observed"] == 1.0
    assert cliques["observed"] > cliques["null_mean"]
    assert cliques["z_score"] > 3.0
    assert cliques["p_value"] < 0.01

    # A random graph of the same degree sequence: one rewired instance of
    # the clique graph, keeping the original tradition labels. Its observed
    # separation should sit at the null centre, not above it.
    from _null_separation import rewire_degree_preserving

    R = rewire_degree_preserving(G, seed=123)
    random_graph = null_separation_test(
        R, node_to_tradition, within_tradition_share, n_perm=200, seed=42
    )
    assert abs(random_graph["z_score"]) < 2.0
    assert random_graph["p_value"] > 0.05


def test_modularity_statistic_orders_correctly():
    """Modularity of the 3-partition is high for cliques, low for random."""
    from _null_separation import partition_modularity, rewire_degree_preserving

    G, node_to_tradition = _three_cliques()
    q_cliques = partition_modularity(G, node_to_tradition)
    R = rewire_degree_preserving(G, seed=5)
    q_random = partition_modularity(R, node_to_tradition)
    assert q_cliques > q_random
