"""Global citation-network map: render the community meta-graph (ticket 0307).

Plot side of the global map (R1-14). Reads the JSON summary produced by
scripts/analysis/analyze_global_map.py (--input) and renders one PNG
(--output): one circle per major Louvain community (area ~ membership),
edges between communities (width ~ inter-community link count).

The reading guide is NOT embedded in the PNG — it lives in the Quarto figure
caption (deliverables/data-paper/data-paper.qmd). The PNG carries the map,
a short title, and a one-line method subtitle only.

Community names and colors come from config/community_registry.yml (one
concept = one name = one color across all corpus network figures); unmapped
communities fall back to grey with an auto author-year label. Broken-metadata
labels are fixed by the registry's label_overrides at render time.

Usage:
    python scripts/figures/plot_fig_global_map.py \
        --input data/derived/tables/global_map_direct.json \
        --output deliverables/_shared/figures/fig_global_map_direct.png
"""

import json
import os

import matplotlib.pyplot as plt
import networkx as nx
from _community_registry import figure_communities, override_label, surname_label
from pipeline_io import save_figure
from pipeline_loaders import load_analysis_config
from plot_style import DARK, DPI, FIGWIDTH, apply_style
from script_io_args import parse_io_args, validate_io
from utils import get_logger

log = get_logger("plot_fig_global_map")

TITLES = {
    "direct": ("Global map of climate finance scholarship",
               "Direct-citation communities among corpus documents "
               "(Louvain, node area ~ community size)"),
    "cocitation": ("Reference canons of climate finance scholarship",
                   "Co-citation communities among the most-cited references "
                   "(Louvain, node area ~ community size)"),
}


def auto_label(comm):
    """Fallback label for an unregistered community: its top two members."""
    tops = [surname_label(m["label"]) for m in comm["top_members"][:2]]
    return " / ".join(override_label(t) for t in tops)


def render(summary, out_path):
    """Render the community meta-graph PNG."""
    figure_name = f"fig_global_map_{summary['method']}"
    reg = figure_communities(figure_name)
    seed = int(load_analysis_config()["pre2007_traditions"]["louvain_seed"])

    M = nx.Graph()
    comms = {c["id"]: c for c in summary["communities"]}
    for c in summary["communities"]:
        M.add_node(c["id"], size=c["size"])
    for e in summary["edges"]:
        M.add_edge(e["a"], e["b"], weight=e["weight"])

    apply_style()
    fig_w = FIGWIDTH * 1.6
    fig, ax = plt.subplots(figsize=(fig_w, fig_w * 0.8))
    pos = nx.spring_layout(M, weight="weight", seed=seed, k=1.8)
    maxw = max((d["weight"] for _, _, d in M.edges(data=True)), default=1)
    nx.draw_networkx_edges(
        M, pos, ax=ax, edge_color="#BBBBBB",
        width=[0.5 + 6 * d["weight"] / maxw for _, _, d in M.edges(data=True)],
        alpha=0.6)
    maxs = max(c["size"] for c in summary["communities"])
    nx.draw_networkx_nodes(
        M, pos, ax=ax,
        node_size=[300 + 4200 * M.nodes[c]["size"] / maxs for c in M.nodes()],
        node_color=[reg[c][1] if c in reg else "#DDDDDD" for c in M.nodes()],
        edgecolors="white", linewidths=1.0, alpha=0.9)
    for c in M.nodes():
        lab = reg[c][0] if c in reg else auto_label(comms[c])
        x, y = pos[c]
        ax.text(x, y + 0.09, f"{lab}\n(n={M.nodes[c]['size']:,})",
                ha="center", va="bottom", fontsize=6, color=DARK,
                bbox=dict(boxstyle="round,pad=0.2", fc="white",
                          ec="none", alpha=0.8))
    title, subtitle = TITLES[summary["method"]]
    ax.set_title(f"{title}\n{subtitle}", fontsize=8, pad=8)
    ax.axis("off")
    plt.tight_layout(pad=0.5)
    save_figure(fig, os.path.splitext(out_path)[0], pdf=False, dpi=DPI)
    plt.close(fig)


def main():
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)
    if not io_args.input:
        raise SystemExit("--input <global_map_*.json> is required")
    with open(io_args.input[0]) as f:
        summary = json.load(f)
    render(summary, io_args.output)
    log.info("Rendered %s map -> %s", summary["method"], io_args.output)


if __name__ == "__main__":
    main()
