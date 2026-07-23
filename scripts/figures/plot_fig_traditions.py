"""Pre-2007 co-citation network: three intellectual traditions.

Method: Louvain community detection on co-citation graph of the 250 most-cited
pre-2007 references. Three communities are identified as intellectual traditions
by matching anchor authors; the remaining seven are rendered as background.

Produces:
  content/figures/fig_traditions.png
  content/figures/fig_traditions.pdf

Usage:
    uv run python scripts/plot_fig_traditions.py --output content/figures/fig_traditions.png
    uv run python scripts/plot_fig_traditions.py --output content/figures/fig_traditions.png \
        --input refined_works.csv refined_citations.csv
"""

import argparse
import os

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from _community_registry import (
    override_label,
    short_label,
    surname_label,
    tradition_concepts,
)
from _pre2007_traditions import (
    RANDOM_STATE,
    TRADITION_ANCHORS,
    build_pre2007_traditions,
)
from pipeline_io import save_figure
from plot_style import DARK, DPI, FIGWIDTH, apply_style
from script_io_args import parse_io_args, validate_io
from utils import get_logger

log = get_logger("plot_fig_traditions")


_TRAD = tradition_concepts()
TRADITION_LABELS = {t: lab for t, (lab, _) in _TRAD.items()}
TRADITION_LABELS["other"] = None
TRADITION_COLORS = {t: col for t, (_, col) in _TRAD.items()}
TRADITION_COLORS["other"] = "#DDDDDD"
TRADITION_EDGE_COLORS = dict(TRADITION_COLORS)
TRADITION_EDGE_COLORS["other"] = "#CCCCCC"


def _render_traditions(G, partition, pos, comm_to_tradition,
                       trad_to_comm, comm_to_nodes, ref_counts,
                       actual_top_n, n_comm, modularity,
                       out_stem, pdf, cutoff_year):
    """Render the traditions network figure."""
    fig_w = FIGWIDTH * 1.6
    fig_h = fig_w * 0.75
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    # Edges
    edge_colors, edge_widths = [], []
    all_weights = [G[u][v]["weight"] for u, v in G.edges()]
    max_w = max(all_weights) if all_weights else 1.0

    for u, v in G.edges():
        t_u = comm_to_tradition.get(partition[u], "other")
        t_v = comm_to_tradition.get(partition[v], "other")
        if t_u == t_v and t_u != "other":
            edge_colors.append(TRADITION_EDGE_COLORS[t_u])
            edge_widths.append(0.5 + 1.5 * G[u][v]["weight"] / max_w)
        else:
            edge_colors.append("#E0E0E0")
            edge_widths.append(0.2)

    nx.draw_networkx_edges(G, pos, ax=ax, edge_color=edge_colors,
                           width=edge_widths, alpha=0.6)

    # Nodes
    cit_arr = np.array([G.nodes[n]["citations"] for n in G.nodes()])
    node_sizes = 30 + 250 * np.sqrt(cit_arr / cit_arr.max())
    node_colors = [
        TRADITION_COLORS[comm_to_tradition.get(partition[n], "other")]
        for n in G.nodes()
    ]
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors,
                           node_size=node_sizes, edgecolors="white",
                           linewidths=0.4, alpha=0.9)

    # Labels
    _draw_labels(ax, G, pos, trad_to_comm, comm_to_nodes, ref_counts,
                 cutoff_year)

    # Legend
    _draw_legend(ax, trad_to_comm, comm_to_nodes, comm_to_tradition)

    ax.set_title(
        f"Three intellectual traditions before climate finance\n"
        f"(co-citation communities among pre-{cutoff_year + 1} references "
        f"of the climate finance corpus)",
        fontsize=8, pad=8)
    ax.axis("off")
    caption = (
        "Reading guide.  Each circle is one CITED REFERENCE published before "
        f"{cutoff_year + 1}; circle area grows with its citation count in the corpus, "
        "edges link references frequently cited together (co-citation), edge width "
        "with co-citation strength.  Colored communities are the three traditions "
        "identified by anchor authors; grey nodes belong to other communities "
        "(largest ones labeled, surname + year).\n"
        f"Method: co-citation graph of the top {actual_top_n} most-cited "
        f"pre-{cutoff_year + 1} references (citing side: the whole 1990-2025 corpus), "
        f"Louvain community detection with fixed seed, {n_comm} communities, "
        f"weighted modularity = {modularity:.2f}.  Layout: force-directed spring "
        "embedding (distances are indicative only).  Names and colors follow the "
        "shared community registry (config/community_registry.yml); same concept = "
        "same name and color across all corpus network figures.")
    fig.text(0.02, 0.01, caption, fontsize=5.8, color=DARK,
             ha="left", va="bottom", wrap=True)
    plt.tight_layout(rect=(0, 0.12, 1, 1), pad=0.5)

    save_figure(fig, out_stem, pdf=pdf, dpi=DPI)
    plt.close()


def _draw_labels(ax, G, pos, trad_to_comm, comm_to_nodes, ref_counts,
                 cutoff_year):
    """Draw node labels for top-cited nodes per tradition."""
    label_nodes = set()
    for c in trad_to_comm.values():
        nodes_sorted = sorted(
            comm_to_nodes[c], key=lambda d: -ref_counts.get(d, 0))
        label_nodes.update(nodes_sorted[:5])

    other_nodes = sorted(
        [d for d in G.nodes()
         if d not in {n for s in
                      [comm_to_nodes.get(trad_to_comm.get(t), [])
                       for t in TRADITION_ANCHORS]
                      for n in s}],
        key=lambda d: -ref_counts.get(d, 0))
    # Label the biggest grey (non-tradition) nodes so the reader sees what
    # the colored traditions are NOT. Surname-only format ("Nordhaus 2015").
    grey_label_nodes = set(other_nodes[:4])
    label_nodes.update(grey_label_nodes)

    # Keep readable labels only; dedupe identical label texts
    # (e.g. two distinct references both rendered "Axel Michaelowa 2003"),
    # keeping the most-cited node.
    candidates = sorted(label_nodes, key=lambda d: -ref_counts.get(d, 0))
    labels, seen_texts = {}, set()
    for n in candidates:
        text = G.nodes[n]["label"]
        if " " not in text or text.startswith("10."):
            continue
        if n in grey_label_nodes:
            # "William D. Nordhaus 2015" -> "Nordhaus 2015"
            text = surname_label(text)
        else:
            # "Axel Michaelowa 2003" -> "A. Michaelowa 2003"
            text = short_label(text)
        text = override_label(text)  # registry fixes for broken metadata
        year = text.split()[-1][:4]
        if year.isdigit() and int(year) > cutoff_year + 1:
            log.warning("Anachronistic label year (metadata defect), "
                        "skipping label: %s (%s)", text, n)
            continue
        if text in seen_texts:
            continue
        seen_texts.add(text)
        labels[n] = text

    # Place labels above their node, then greedily nudge apart any pair
    # that would overlap (simple vertical stacking — no extra dependency).
    dy = 0.045
    placed = []  # (x, y) of placed label centres
    for n, text in sorted(labels.items(), key=lambda kv: pos[kv[0]][1],
                          reverse=True):
        x, y = pos[n]
        ly = y + dy
        while any(abs(x - px) < 0.28 and abs(ly - py) < 0.055
                  for px, py in placed):
            ly += 0.055
        placed.append((x, ly))
        ax.text(x, ly, text, fontsize=5.5, color=DARK,
                ha="center", va="bottom",
                bbox=dict(boxstyle="round,pad=0.15", fc="white",
                          ec="none", alpha=0.75))


def _draw_legend(ax, trad_to_comm, comm_to_nodes, comm_to_tradition):
    """Draw tradition legend."""
    legend_handles = []
    for trad in ("pricing", "cdm", "unfccc"):
        c = trad_to_comm.get(trad)
        if c is None:
            continue
        n = len(comm_to_nodes[c])
        label = TRADITION_LABELS[trad] + f"  (n={n})"
        patch = mpatches.Patch(
            facecolor=TRADITION_COLORS[trad],
            edgecolor="white", linewidth=0.5, label=label)
        legend_handles.append(patch)

    other_count = sum(
        len(v) for c, v in comm_to_nodes.items()
        if comm_to_tradition[c] == "other")
    legend_handles.append(
        mpatches.Patch(
            facecolor=TRADITION_COLORS["other"],
            edgecolor="white", linewidth=0.5,
            label=f"Other communities  (n={other_count})"))

    ax.legend(handles=legend_handles, loc="lower left",
              framealpha=0.9, edgecolor=DARK, fontsize=6,
              handlelength=1.2, handleheight=1.0)


def main():
    io_args, extra = parse_io_args()
    validate_io(output=io_args.output, inputs=io_args.input)

    parser = argparse.ArgumentParser(
        description="Pre-2007 co-citation traditions network")
    parser.add_argument("--pdf", action="store_true",
                        help="Also save PDF output")
    args = parser.parse_args(extra)

    apply_style()
    out_stem = os.path.splitext(io_args.output)[0]

    works_path = io_args.input[0] if io_args.input else None
    cit_path = (
        io_args.input[1] if io_args.input and len(io_args.input) >= 2
        else None
    )

    result = build_pre2007_traditions(works_path, cit_path)
    if result is None:
        log.info("No pre-2007 traditions network. Creating empty output.")
        open(io_args.output, "w").close()
        return

    G = result["graph"]
    partition = result["partition"]
    comm_to_tradition = result["comm_to_tradition"]
    trad_to_comm = result["trad_to_comm"]
    comm_to_nodes = result["comm_to_nodes"]
    ref_counts = result["ref_counts"]
    n_comm = result["n_comm"]
    modularity = result["modularity"]
    actual_top_n = result["actual_top_n"]
    cutoff_year = result["cutoff_year"]

    log.info("Tradition assignments:")
    for trad, c in trad_to_comm.items():
        nodes = comm_to_nodes[c]
        top3 = sorted(nodes, key=lambda d: -ref_counts.get(d, 0))[:3]
        names = [G.nodes[d]["label"] for d in top3]
        log.info("  %10s -> community %d (n=%d): %s",
                 trad, c, len(nodes), ", ".join(names))

    log.info("Computing layout...")
    pos = nx.spring_layout(G, weight="weight", k=2.5,
                           iterations=200, seed=RANDOM_STATE)

    _render_traditions(G, partition, pos, comm_to_tradition,
                       trad_to_comm, comm_to_nodes, ref_counts,
                       actual_top_n, n_comm, modularity,
                       out_stem, args.pdf, cutoff_year)

    log.info("Done.")


if __name__ == "__main__":
    main()
