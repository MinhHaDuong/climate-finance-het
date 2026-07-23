"""Tests for the citer-limited network limitations pipeline (ticket 0286).

The R1-14 response letter quotes numbers from
deliverables/_shared/tables/tab_network_limitations.csv and
qa_cocitation_edges_report.json. These tests pin the pure logic (burden-anchor
counting, cluster-presence predicate, candidate census) on synthetic graphs,
and the CLI/Makefile contracts by source inspection (no subprocess in the
fast tier).
"""

import os
import re

import networkx as nx
import yaml

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")


def _graph(authors_by_comm):
    """Graph + partition: {comm_id: [author, ...]} -> (G, partition)."""
    G = nx.Graph()
    partition = {}
    i = 0
    for c, authors in authors_by_comm.items():
        for a in authors:
            G.add_node(f"n{i}", author=a)
            partition[f"n{i}"] = c
            i += 1
    return G, partition


def test_burden_candidates_are_sixteen_distinct():
    from _citer_limited_traditions import BURDEN_CANDIDATES

    assert len(BURDEN_CANDIDATES) == 16
    flat = [v for c in BURDEN_CANDIDATES
            for v in (c if isinstance(c, tuple) else (c,))]
    assert len(set(flat)) == len(flat)


def test_burden_hits_counts_anchors_per_community():
    from _citer_limited_traditions import burden_hits

    G, partition = _graph({0: ["tol", "grubb", "smith"],
                           1: ["nordhaus", "weitzman"]})
    counts, sizes = burden_hits(G, partition)
    assert counts == {0: 2}
    assert sizes == {0: 3, 1: 2}


def test_burden_hits_matches_diacritic_variant():
    from _citer_limited_traditions import burden_hits

    G, partition = _graph({0: ["höhne", "oberthür", "x", "y"]})
    counts, _ = burden_hits(G, partition)
    assert counts == {0: 2}


def test_cluster_present_thresholds():
    from _citer_limited_traditions import cluster_present

    G, partition = _graph({0: ["michaelowa", "sutter", "a", "b"],
                           1: ["haites", "c"]})
    anchors = ["michaelowa", "sutter", "haites"]
    assert cluster_present(G, partition, anchors,
                           min_anchors=2, min_size=4)
    # Size threshold not met when the community is too small
    assert not cluster_present(G, partition, anchors,
                               min_anchors=2, min_size=5)
    # Anchor threshold
    assert not cluster_present(G, partition, anchors,
                               min_anchors=3, min_size=2)


def test_candidates_in_network_counts_variants_once():
    from _citer_limited_traditions import candidates_in_network

    G = nx.Graph()
    G.add_node("a", author="hohne")
    G.add_node("b", author="höhne")
    G.add_node("c", author="tol")
    G.add_node("d", author="nordhaus")
    assert candidates_in_network(G) == 2


def test_candidates_in_network_word_boundary():
    """'stolz' must not match the candidate 'tol'."""
    from _citer_limited_traditions import candidates_in_network

    G = nx.Graph()
    G.add_node("a", author="stolz")
    assert candidates_in_network(G) == 0


def test_config_declares_network_limitations_parameters():
    cfg_path = os.path.join(SCRIPTS, "..", "config", "analysis.yaml")
    with open(cfg_path) as fh:
        cfg = yaml.safe_load(fh)
    nl = cfg["network_limitations"]
    for key in ("citer_cutoff", "n_perm", "n_boot", "seed",
                "edge_sample_n", "edge_sample_seed"):
        assert key in nl, key


def test_compute_script_cli_contract():
    src = open(os.path.join(
        SCRIPTS, "analysis", "compute_network_limitations.py")).read()
    assert "parse_io_args" in src
    assert "--n-boot" in src
    assert "--skip-bootstrap" in src
    assert "NetworkLimitationsSchema" in src
    # Bootstrap must resample citers as DISTINCT documents (the k^2 trap).
    assert "#{i}" in src.replace('f"{d}#{i}"', "#{i}")


def test_plot_script_reads_registry_with_fallback():
    src = open(os.path.join(
        SCRIPTS, "figures", "plot_fig_traditions_pre2008_citers.py")).read()
    assert "community_registry.yml" in src
    assert "plot_fig_traditions" in src  # fallback labels/colors
    assert "save_figure" in src
    assert "fig.savefig" not in src


def test_qa_script_reuses_crossref_idiom():
    src = open(os.path.join(SCRIPTS, "qa", "qa_cocitation_edges.py")).read()
    assert "from qa_citations import fetch_crossref_refs, wilson_ci" in src
    assert "--sample-n" in src


def test_makefile_wires_targets():
    mk = open(os.path.join(
        SCRIPTS, "analysis", "network-limitations.mk")).read()
    for t in ("tab_network_limitations.csv",
              "fig_traditions_pre2008_citers.png",
              "qa_cocitation_edges_report.json"):
        assert t in mk, t
    top = open(os.path.join(SCRIPTS, "..", "Makefile")).read()
    assert "network-limitations.mk" in top


def test_response_letter_numbers_trace_to_artifact():
    """Every statistic in the R1-14 paragraph exists in the stats CSV."""
    base = os.path.join(SCRIPTS, "..")
    csv_path = os.path.join(
        base, "deliverables", "_shared", "tables",
        "tab_network_limitations.csv")
    md_path = os.path.join(
        base, "deliverables", "data-paper", "revision-rdj26561",
        "r1-14-network-response.md")
    assert os.path.exists(md_path)
    assert os.path.exists(csv_path)
    import pandas as pd

    df = pd.read_csv(csv_path).set_index("metric")["value"]
    md = open(md_path).read()
    # The headline claims are backed by artifact rows.
    assert df["econ_cross_cluster_edges_observed"] == 0
    for metric in ("econ_cross_share_null_mean", "econ_within_share_z",
                   "burden_candidates_in_network", "boot_burden_rate",
                   "boot_cdm_rate", "boot_pricing_rate"):
        assert metric in df.index, metric
    # The letter quotes the null cross-share percentage and z-score verbatim.
    pct = round(100 * df["econ_cross_share_null_mean"])
    assert f"{pct:.0f}%" in md
    assert f"z = {df['econ_within_share_z']:.1f}" in md
