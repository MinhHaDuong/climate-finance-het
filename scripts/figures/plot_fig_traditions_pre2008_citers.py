"""Citer-limited variant of fig_traditions (ticket 0286, R1-14 supplement).

Same method as the canonical figure (top pre-2007 references, co-citation,
Louvain, same anchors) but the CITING side is restricted to corpus documents
published <= the citer cutoff (config `network_limitations.citer_cutoff`).
Shows what the sparse early citation record establishes on its own: the two
economic traditions separate; the burden-sharing pole is absent. Produced as
a potential electronic supplement to the data paper — not embedded in it.

Community names and colors follow the shared registry
`config/community_registry.yml` (committed by ticket 0307) when present;
otherwise the canonical figure's tradition labels/colors are used, so this
script renders identically once the registry lands.

Usage:
    uv run python scripts/figures/plot_fig_traditions_pre2008_citers.py \
        --output deliverables/_shared/figures/fig_traditions_pre2008_citers.png
"""

import argparse
import os

import community as community_louvain
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import yaml
from _citer_limited_traditions import (
    build_top_graph,
    citer_limited_cutoff,
    load_citer_limited,
)
from _pre2007_traditions import RANDOM_STATE, _assign_traditions
from pipeline_io import save_figure
from pipeline_loaders import BASE_DIR
from plot_style import DARK, DPI, FIGWIDTH, apply_style
from script_io_args import parse_io_args, validate_io
from utils import get_logger

log = get_logger("plot_fig_traditions_pre2008_citers")

REGISTRY_PATH = os.path.join(BASE_DIR, "config", "community_registry.yml")


def tradition_style():
    """(labels, colors) per tradition key, from the shared registry.

    Falls back to the canonical figure's labels/colors when the registry
    (ticket 0307) is not yet present, so the two branches merge in any order.
    """
    if os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH) as fh:
            reg = yaml.safe_load(fh)
        concepts = reg["concepts"]
        labels = {t: concepts[c]["label"] for t, c in reg["traditions"].items()}
        colors = {t: concepts[c]["color"] for t, c in reg["traditions"].items()}
        colors["other"] = concepts.get("other", {}).get("color", "#DDDDDD")
        log.info("Using community registry: %s", REGISTRY_PATH)
    else:
        from plot_fig_traditions import TRADITION_COLORS, TRADITION_LABELS
        labels = {t: (v or "").replace("\n", " ")
                  for t, v in TRADITION_LABELS.items() if v}
        colors = dict(TRADITION_COLORS)
        log.info("Registry absent — canonical figure labels/colors.")
    return labels, colors


def build_variant(citer_cutoff, works_path=None, cit_path=None):
    """Build the citer-limited co-citation network and its partition."""
    cit, doi_meta, cutoff_year = load_citer_limited(
        citer_cutoff, works_path, cit_path)
    G, ref_counts = build_top_graph(cit, doi_meta, cutoff_year)
    if G is None or G.number_of_nodes() == 0:
        return None
    partition = community_louvain.best_partition(
        G, weight="weight", random_state=RANDOM_STATE)
    n_comm = len(set(partition.values()))
    modularity = community_louvain.modularity(partition, G, weight="weight")
    log.info("  Louvain: %d communities, modularity=%.4f", n_comm, modularity)
    comm_to_tradition, trad_to_comm, comm_to_nodes = _assign_traditions(
        G, partition)
    return dict(graph=G, partition=partition,
                comm_to_tradition=comm_to_tradition,
                trad_to_comm=trad_to_comm, comm_to_nodes=comm_to_nodes,
                ref_counts=ref_counts, n_comm=n_comm, modularity=modularity,
                cutoff_year=cutoff_year, citer_cutoff=citer_cutoff)


def _draw_labels(ax, res, pos, barrett_nodes):
    """Top-4 labels per tradition + Barrett nodes, deduped, anti-collision."""
    G = res["graph"]
    ref_counts = res["ref_counts"]
    label_nodes = set(barrett_nodes)
    for c in res["trad_to_comm"].values():
        label_nodes.update(sorted(
            res["comm_to_nodes"][c], key=lambda d: -ref_counts.get(d, 0))[:4])
    candidates = sorted(label_nodes, key=lambda d: -ref_counts.get(d, 0))
    labels, seen = {}, set()
    for n in candidates:
        t = G.nodes[n]["label"]
        if " " not in t or t.startswith("10."):
            continue
        year = t.split()[-1][:4]
        if year.isdigit() and int(year) > res["cutoff_year"] + 1:
            log.warning("Anachronistic label year (metadata defect), "
                        "skipping label: %s (%s)", t, n)
            continue
        if t in seen and n not in barrett_nodes:
            continue
        seen.add(t)
        labels[n] = t
    placed = []
    for n, text in sorted(labels.items(), key=lambda kv: pos[kv[0]][1],
                          reverse=True):
        x, y = pos[n]
        ly = y + 0.05
        while any(abs(x - px) < 0.30 and abs(ly - py) < 0.06
                  for px, py in placed):
            ly += 0.06
        placed.append((x, ly))
        weight = "bold" if n in barrett_nodes else "normal"
        ax.text(x, ly, text, fontsize=6, color=DARK, ha="center",
                va="bottom", fontweight=weight,
                bbox=dict(boxstyle="round,pad=0.15", fc="white",
                          ec="none", alpha=0.75))


def render(res, out_stem):
    """Render the network with tradition coloring and Barrett highlighted."""
    G = res["graph"]
    partition = res["partition"]
    comm_to_tradition = res["comm_to_tradition"]
    trad_to_comm = res["trad_to_comm"]
    comm_to_nodes = res["comm_to_nodes"]
    labels_by_trad, colors_by_trad = tradition_style()

    fig_w = FIGWIDTH * 1.6
    fig, ax = plt.subplots(figsize=(fig_w, fig_w * 0.75))
    pos = nx.spring_layout(G, weight="weight", k=2.5,
                           iterations=200, seed=RANDOM_STATE)

    # De-trivialize: unmatched ("other") communities of size >= 4 get muted
    # distinct colors; smaller ones stay grey.
    pale = ["#b5a6c9", "#c9b98a", "#9ec4c9", "#c99ea6",
            "#a6c99e", "#c9c09e", "#9ea6c9", "#c99ec4"]
    other_comm_color = {}
    i = 0
    for c, nodes in sorted(comm_to_nodes.items(), key=lambda kv: -len(kv[1])):
        if comm_to_tradition.get(c) == "other" and len(nodes) >= 4:
            other_comm_color[c] = pale[i % len(pale)]
            i += 1

    def node_color(n):
        c = partition[n]
        t = comm_to_tradition.get(c, "other")
        if t != "other":
            return colors_by_trad[t]
        return other_comm_color.get(c, colors_by_trad["other"])

    all_w = [G[u][v]["weight"] for u, v in G.edges()] or [1.0]
    max_w = max(all_w)
    edge_colors, edge_widths = [], []
    for u, v in G.edges():
        t_u = comm_to_tradition.get(partition[u], "other")
        t_v = comm_to_tradition.get(partition[v], "other")
        if t_u == t_v and t_u != "other":
            edge_colors.append(colors_by_trad[t_u])
            edge_widths.append(0.5 + 1.5 * G[u][v]["weight"] / max_w)
        else:
            edge_colors.append("#E0E0E0")
            edge_widths.append(0.3)
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color=edge_colors,
                           width=edge_widths, alpha=0.6)

    barrett_nodes = [n for n in G.nodes()
                     if "barrett" in G.nodes[n].get("author", "")]
    other_nodes = [n for n in G.nodes() if n not in barrett_nodes]
    cit_arr = np.array([G.nodes[n]["citations"] for n in G.nodes()])
    max_cit = cit_arr.max()

    def sizes(nodes, base=40, span=300):
        return [base + span * np.sqrt(G.nodes[n]["citations"] / max_cit)
                for n in nodes]

    nx.draw_networkx_nodes(
        G, pos, nodelist=other_nodes, ax=ax,
        node_color=[node_color(n) for n in other_nodes],
        node_size=sizes(other_nodes), edgecolors="white",
        linewidths=0.4, alpha=0.9)
    # Barrett highlighted: star marker, dark contour, whatever community.
    nx.draw_networkx_nodes(
        G, pos, nodelist=barrett_nodes, ax=ax, node_shape="*",
        node_color=[node_color(n) for n in barrett_nodes],
        node_size=[s * 2.2 for s in sizes(barrett_nodes)],
        edgecolors=DARK, linewidths=1.6, alpha=1.0)

    _draw_labels(ax, res, pos, barrett_nodes)

    handles = []
    for trad, c in trad_to_comm.items():
        handles.append(mpatches.Patch(
            facecolor=colors_by_trad[trad], edgecolor="white",
            label=labels_by_trad[trad] + f"  (n={len(comm_to_nodes[c])})"))
    n_pale = sum(len(comm_to_nodes[c]) for c in other_comm_color)
    if other_comm_color:
        handles.append(mpatches.Patch(
            facecolor=pale[0], edgecolor="white",
            label=f"Unlabeled communities, size >= 4  "
                  f"(k={len(other_comm_color)}, n={n_pale})"))
    n_grey = sum(len(v) for c, v in comm_to_nodes.items()
                 if comm_to_tradition[c] == "other"
                 and c not in other_comm_color)
    handles.append(mpatches.Patch(
        facecolor=colors_by_trad["other"], edgecolor="white",
        label=f"Trivial communities (< 4 nodes)  (n={n_grey})"))
    handles.append(plt.Line2D(
        [], [], marker="*", linestyle="", markersize=11,
        markerfacecolor="white", markeredgecolor=DARK,
        label="Scott Barrett"))
    ax.legend(handles=handles, loc="lower left", framealpha=0.9,
              edgecolor=DARK, fontsize=6, handlelength=1.2)

    ax.set_title(
        f"Early climate finance scholarship, contemporary view — "
        f"citing documents restricted to <= {res['citer_cutoff']}",
        fontsize=8, pad=8)
    ax.axis("off")
    caption = (
        "Reading guide.  Each circle is one cited reference published before "
        f"{res['cutoff_year'] + 1}; circle area grows with its citation "
        "count, edges link references frequently cited together "
        "(co-citation), edge width with co-citation strength.  Colored "
        "communities are the traditions identified by anchor authors; muted "
        "colors mark unlabeled communities of >= 4 nodes; the star marks "
        "Scott Barrett's works.\n"
        f"Method: co-citation graph of the top most-cited "
        f"pre-{res['cutoff_year'] + 1} references, citing side restricted to "
        f"corpus documents published <= {res['citer_cutoff']} (the canonical "
        f"figure uses all citers), Louvain community detection with fixed "
        f"seed, {res['n_comm']} communities, weighted modularity = "
        f"{res['modularity']:.2f}.  Layout: force-directed spring embedding "
        "(distances are indicative only)."
        + ("  Names and colors follow the shared community registry "
           "(config/community_registry.yml)."
           if os.path.exists(REGISTRY_PATH) else ""))
    fig.text(0.02, 0.01, caption, fontsize=5.8, color=DARK,
             ha="left", va="bottom", wrap=True)
    plt.tight_layout(rect=(0, 0.13, 1, 1), pad=0.5)
    save_figure(fig, out_stem, pdf=False, dpi=DPI)
    plt.close()


def main():
    io_args, extra = parse_io_args()
    validate_io(output=io_args.output, inputs=io_args.input)
    parser = argparse.ArgumentParser(
        description="Traditions variant: contemporary citers only")
    parser.add_argument("--citer-cutoff", type=int, default=None,
                        help="Override config network_limitations.citer_cutoff")
    args = parser.parse_args(extra)
    apply_style()

    citer_cutoff = (args.citer_cutoff if args.citer_cutoff is not None
                    else citer_limited_cutoff())
    works_path = io_args.input[0] if io_args.input else None
    cit_path = (io_args.input[1]
                if io_args.input and len(io_args.input) >= 2 else None)
    res = build_variant(citer_cutoff, works_path, cit_path)
    if res is None:
        log.info("Empty network — writing empty output.")
        open(io_args.output, "w").close()
        return

    G = res["graph"]
    for trad, c in res["trad_to_comm"].items():
        top3 = sorted(res["comm_to_nodes"][c],
                      key=lambda d: -res["ref_counts"].get(d, 0))[:3]
        log.info("  %10s -> community %d (n=%d): %s", trad, c,
                 len(res["comm_to_nodes"][c]),
                 ", ".join(G.nodes[d]["label"] for d in top3))
    for n in [n for n in G.nodes()
              if "barrett" in G.nodes[n].get("author", "")]:
        c = res["partition"][n]
        log.info("  BARRETT node %s (%s) -> community %d (%s), degree %d",
                 n, G.nodes[n]["label"], c,
                 res["comm_to_tradition"].get(c, "other"), G.degree(n))

    render(res, os.path.splitext(io_args.output)[0])
    log.info("Done.")


if __name__ == "__main__":
    main()
