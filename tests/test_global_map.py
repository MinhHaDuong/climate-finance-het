"""Tests for the global citation-network map (ticket 0307, R1-14).

Covers the community registry (config/community_registry.yml + helper),
the compute-side aggregation (analyze_global_map.summarize on a small
fixture graph), and the compute/plot contract conventions.
"""

import os
import sys

import networkx as nx
import pytest
import yaml

BASE = os.path.join(os.path.dirname(__file__), "..")
SCRIPTS_DIR = os.path.join(BASE, "scripts")
sys.path.insert(0, os.path.join(SCRIPTS_DIR, "figures"))

REGISTRY_PATH = os.path.join(BASE, "config", "community_registry.yml")


@pytest.fixture(scope="module")
def registry():
    with open(REGISTRY_PATH) as f:
        return yaml.safe_load(f)


class TestRegistry:
    """config/community_registry.yml is coherent."""

    def test_figure_mappings_reference_known_concepts(self, registry):
        concepts = set(registry["concepts"])
        for fig, mapping in registry["figures"].items():
            for cid, key in mapping.items():
                assert key in concepts, f"{fig}: community {cid} -> unknown {key}"

    def test_traditions_reference_known_concepts(self, registry):
        concepts = set(registry["concepts"])
        assert set(registry["traditions"].values()) <= concepts

    def test_one_concept_one_color(self, registry):
        """One concept = one color: no two concepts share a color."""
        colors = [c["color"] for c in registry["concepts"].values()]
        assert len(colors) == len(set(colors))

    def test_green_finance_unified_across_maps(self, registry):
        """Green bonds & sustainable finance uses ONE concept on both maps."""
        figs = registry["figures"]
        assert "green-finance" in figs["fig_global_map_direct"].values()
        assert "green-finance" in figs["fig_global_map_cocitation"].values()

    def test_label_overrides_present(self, registry):
        """Broken-metadata overrides validated by the author are registered."""
        ov = registry["label_overrides"]
        assert ov["O. C. Future 1987"] == "Our Common Future 1987"
        assert ov["theory justice original"] == "Rawls 1971"
        assert ov["Nations 1992"] == "United Nations 1992"


class TestRegistryHelpers:
    """_community_registry helper functions."""

    def test_concept_and_figure_lookup(self):
        from _community_registry import concept, figure_communities
        label, color = concept("green-finance")
        assert label == "Green bonds & sustainable finance"
        assert color.startswith("#")
        reg = figure_communities("fig_global_map_direct")
        assert reg, "direct map has registered communities"
        assert all(isinstance(k, int) for k in reg)

    def test_surname_and_short_label(self):
        from _community_registry import short_label, surname_label
        assert surname_label("William D. Nordhaus 2015") == "Nordhaus 2015"
        assert short_label("Axel Michaelowa 2003") == "A. Michaelowa 2003"

    def test_override_label(self):
        from _community_registry import override_label
        assert override_label("Nations 1992") == "United Nations 1992"
        assert override_label("Stern 2007") == "Stern 2007"  # pass-through


class TestSummarize:
    """analyze_global_map.summarize aggregates a partition correctly."""

    @pytest.fixture()
    def toy(self):
        # Two dense communities of 4 nodes + one 1-node community (below
        # min_share=0.25 of 9 nodes)
        G = nx.Graph()
        a = [f"a{i}" for i in range(4)]
        b = [f"b{i}" for i in range(4)]
        for grp in (a, b):
            G.add_edges_from(
                (grp[i], grp[j]) for i in range(4) for j in range(i + 1, 4))
        G.add_edge("a0", "b0")
        G.add_edge("a1", "c0")
        partition = {n: 0 for n in a} | {n: 1 for n in b} | {"c0": 2}
        rank = {n: i for i, n in enumerate(a + b + ["c0"])}
        meta = {n: {"first_author": "Jane Doe", "year": 2010} for n in G}
        return G, partition, rank, meta

    def test_meta_graph_contract(self, toy):
        sys.path.insert(0, os.path.join(SCRIPTS_DIR, "analysis"))
        from analyze_global_map import summarize
        G, partition, rank, meta = toy
        s = summarize(G, partition, rank, meta, min_share=0.25, top_members=3)
        assert s["n_nodes"] == 9
        assert s["n_communities_total"] == 3
        assert s["n_communities_major"] == 2
        assert s["coverage_share"] == pytest.approx(8 / 9, abs=1e-3)
        # inter-community edge a0-b0 counted once; c0 excluded (below share)
        assert s["edges"] == [{"a": 0, "b": 1, "weight": 1}]
        # communities sorted by size, top members capped and labeled
        for c in s["communities"]:
            assert c["size"] == 4
            assert len(c["top_members"]) == 3
            assert c["top_members"][0]["label"] == "Jane Doe 2010"
        assert 0 < s["modularity"] <= 1


class TestConventions:
    """Compute/plot contract: config-driven, save_figure, no hardcoded seed."""

    def _src(self, *parts):
        with open(os.path.join(SCRIPTS_DIR, *parts)) as f:
            return f.read()

    def test_compute_reads_config_seed(self):
        src = self._src("analysis", "analyze_global_map.py")
        assert "louvain_seed" in src
        assert "random_state=seed" in src
        assert "random_state=42" not in src

    def test_config_has_global_map_block(self):
        with open(os.path.join(BASE, "config", "analysis.yaml")) as f:
            cfg = yaml.safe_load(f)
        gm = cfg["global_map"]
        for key in ("cocitation_top_k", "cocitation_min_cocit",
                    "min_share", "top_members"):
            assert key in gm

    def test_plot_uses_save_figure_and_registry(self):
        src = self._src("figures", "plot_fig_global_map.py")
        assert "save_figure(" in src
        assert ".savefig(" not in src
        assert "figure_communities" in src
        assert "override_label" in src

    def test_plot_has_no_embedded_reading_guide(self):
        """The reading guide lives in the Quarto caption, not the PNG."""
        src = self._src("figures", "plot_fig_global_map.py")
        assert "Reading guide" not in src

    def test_scripts_use_io_args(self):
        for parts in (("analysis", "analyze_global_map.py"),
                      ("figures", "plot_fig_global_map.py")):
            src = self._src(*parts)
            assert "parse_io_args" in src and "validate_io" in src

    def test_traditions_plot_uses_registry(self):
        src = self._src("figures", "plot_fig_traditions.py")
        assert "tradition_concepts" in src
        assert "override_label" in src

    def test_datapaper_prose_uses_generated_vars(self):
        """No hand-typed community count/coverage/modularity in the prose."""
        qmd = os.path.join(BASE, "deliverables", "data-paper", "data-paper.qmd")
        with open(qmd) as f:
            text = f.read()
        for var in ("gm_communities", "gm_coverage_pct",
                    "gm_n_connected", "gm_modularity"):
            assert f"{{{{< meta {var} >}}}}" in text
        assert "fig_global_map_direct.png" in text
        assert "fig_global_map_cocitation" not in text  # companion, not embedded
