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

Robustness (red team, PR #876): the Louvain-anchored seed-sets are detected
on the same graph the null tests, and Louvain maximises modularity by
construction. The a-priori labeling path fixes membership from the
historical record (tbl-traditions anchor works and authors) with no
community detection anywhere — proven here by poisoning the community
module.
"""

import os
import sys

import networkx as nx
import pytest

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
    H, truncated = rewire_degree_preserving(G, seed=7)
    after = dict(H.degree())
    assert before == after
    assert truncated is False  # cliques rewire without exhausting tries


def test_null_test_records_truncation_count():
    """No silently partial rewiring: the result reports truncated replicates."""
    from _null_separation import null_separation_test, within_tradition_share

    G, node_to_tradition = _three_cliques()
    res = null_separation_test(
        G, node_to_tradition, within_tradition_share, n_perm=20, seed=1
    )
    assert res["n_truncated"] == 0


def test_rewire_flags_truncation_on_unmixable_graph():
    """A star cannot be degree-preservingly rewired: truncated must be True.

    Every edge of a star shares the centre node, so no double-edge swap can
    avoid creating a parallel edge — double_edge_swap exhausts max_tries and
    raises NetworkXAlgorithmError. The flag must surface that, not swallow it.
    """
    from _null_separation import rewire_degree_preserving

    star = nx.star_graph(5)  # 6 nodes, 5 edges, all incident to node 0
    H, truncated = rewire_degree_preserving(star, seed=1)
    assert truncated is True
    assert dict(H.degree()) == dict(star.degree())  # degrees still preserved


def test_null_test_counts_truncated_replicates():
    """n_truncated counts every truncated replicate (all of them, for a star)."""
    from _null_separation import null_separation_test, within_tradition_share

    star = nx.star_graph(5)
    labels = {n: ("a" if n % 2 else "b") for n in star.nodes()}
    res = null_separation_test(
        star, labels, within_tradition_share, n_perm=15, seed=2
    )
    assert res["n_truncated"] == 15  # every rewiring of a star truncates


@pytest.mark.slow
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

    R, _ = rewire_degree_preserving(G, seed=123)
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
    R, _ = rewire_degree_preserving(G, seed=5)
    q_random = partition_modularity(R, node_to_tradition)
    assert q_cliques > q_random


# ---------------------------------------------------------------------------
# A-priori labeling path (robustness against the Louvain-circularity objection)
# ---------------------------------------------------------------------------


def _toy_authored_graph():
    """Toy graph whose nodes carry DOI ids and author metadata."""
    G = nx.Graph()
    nodes = {
        "10.1/nordhaus": "nordhaus",
        "10.1/weitzman": "weitzman",
        "10.1/michaelowa": "michaelowa",
        "10.1/sutter": "sutter",
        "10.1/negishi": "negishi",
        "10.1/dimaggio": "dimaggio",
        "10.1/unrelated": "smith",
    }
    for doi, author in nodes.items():
        G.add_node(doi, author=author)
    G.add_edges_from([
        ("10.1/nordhaus", "10.1/weitzman"),
        ("10.1/michaelowa", "10.1/sutter"),
        ("10.1/negishi", "10.1/dimaggio"),
        ("10.1/nordhaus", "10.1/unrelated"),
    ])
    return G


ANCHOR_WORKS = {"env": ["10.1/nordhaus"], "dev": [], "effort": []}
ANCHOR_AUTHORS = {
    "env": ["weitzman"],
    "dev": ["michaelowa", "sutter"],
    "effort": ["negishi", "dimaggio"],
}


def test_label_nodes_by_anchors_matches_doi_and_author():
    """A-priori labeling assigns by anchor DOI and by anchor author."""
    from _null_separation import label_nodes_by_anchors

    G = _toy_authored_graph()
    labels = label_nodes_by_anchors(G, ANCHOR_WORKS, ANCHOR_AUTHORS)
    assert labels["10.1/nordhaus"] == "env"      # DOI match
    assert labels["10.1/weitzman"] == "env"      # author match
    assert labels["10.1/michaelowa"] == "dev"
    assert labels["10.1/negishi"] == "effort"
    assert "10.1/unrelated" not in labels        # no anchor -> unlabeled


def test_label_nodes_by_anchors_doi_wins_and_ambiguous_dropped():
    """DOI assignment overrides author match; ambiguous author matches drop."""
    from _null_separation import label_nodes_by_anchors

    G = _toy_authored_graph()
    # DOI says dev even though the author matches an env anchor
    works = {"env": [], "dev": ["10.1/weitzman"], "effort": []}
    labels = label_nodes_by_anchors(G, works, ANCHOR_AUTHORS)
    assert labels["10.1/weitzman"] == "dev"

    # An author matching two traditions is ambiguous -> dropped
    authors = {"env": ["smith"], "dev": ["smith"], "effort": []}
    labels = label_nodes_by_anchors(G, {"env": [], "dev": [], "effort": []}, authors)
    assert "10.1/unrelated" not in labels


def test_a_priori_path_invokes_no_community_detection(monkeypatch):
    """The a-priori labeling path must never call community detection.

    Red-team requirement (PR #876): poison python-louvain's best_partition;
    the a-priori labeling + null test must still run. Also pin statically
    that the null-model module never imports the community-detection lib.
    """
    import community as community_louvain

    def _bomb(*args, **kwargs):
        raise AssertionError("community detection invoked in a-priori path")

    monkeypatch.setattr(community_louvain, "best_partition", _bomb)

    from _null_separation import (
        label_nodes_by_anchors,
        null_separation_test,
        within_tradition_share,
    )

    G = _toy_authored_graph()
    labels = label_nodes_by_anchors(G, ANCHOR_WORKS, ANCHOR_AUTHORS)
    sub = G.subgraph(labels).copy()
    res = null_separation_test(
        sub, labels, within_tradition_share, n_perm=10, seed=3
    )
    assert 0.0 <= res["observed"] <= 1.0

    src_path = os.path.join(SCRIPTS_DIR, "_null_separation.py")
    with open(src_path) as f:
        src = f.read()
    assert "community_louvain" not in src


def test_load_data_reads_works_through_loader(monkeypatch):
    """arch rule 9 (ticket 0185): with no explicit works_path, _load_data
    must read the works catalog via load_refined_works(), not a direct
    pd.read_csv. Shared by the figure (plot_fig_traditions) and the
    pre-2007 separation null (compute_null_separation), both via the
    neutral _pre2007_traditions module."""
    import _pre2007_traditions as p27
    import pandas as pd

    works = pd.DataFrame({
        "doi": ["10.1/a"],
        "title": ["Title A"],
        "first_author": ["Auth A"],
        "year": [2005],
    })
    cit = pd.DataFrame({
        "source_doi": ["10.1/a"],
        "ref_doi": ["10.1/b"],
        "ref_title": ["Ref B"],
        "ref_first_author": ["Auth B"],
        "ref_year": [2003],
    })
    calls = {"works": 0}

    def fake_load_works():
        calls["works"] += 1
        return works.copy()

    monkeypatch.setattr(p27, "load_refined_works", fake_load_works)
    monkeypatch.setattr(p27, "load_refined_citations", lambda: cit.copy())

    _cit, doi_meta = p27._load_data(None, None)

    assert calls["works"] == 1, "works must be read through load_refined_works()"
    assert "10.1/a" in doi_meta
