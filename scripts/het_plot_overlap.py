#!/usr/bin/env python3
"""Plot citation overlap across the HET "seven costumes" (+ Leontief coda).

One-off companion to het_build_corpus.py / het_embed.py (see those
docstrings). Y = publication year, X = PCA1 of the title+abstract+keywords
embedding. Each of the 8 costume branches gets a fixed categorical hue;
works reachable from two branches (the overlap the figure exists to show)
are drawn as split two-color wedges; works with no branch (context/
methodology citations) are neutral gray. Marker size/opacity fades by hop
distance from the seed (0 = seed, 1 = reference, 2 = reference-of-reference).

Produces:
  data/het/het_overlap.png (+ .svg)
"""

import argparse
import os

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.path import Path
from pipeline_io import save_figure
from utils import get_logger

log = get_logger("het_plot_overlap")

_HERE = os.path.dirname(os.path.abspath(__file__))
HET_DIR = os.path.join(os.path.dirname(_HERE), "data", "het")

# Fixed categorical order == validated palette slot order (dataviz skill,
# references/palette.md) -- never reassign hues by data-dependent frequency.
BRANCH_COLORS = {
    "spatial": "#2a78d6",
    "definetti": "#1baf7a",
    "kantorovich": "#eda100",
    "koopmans": "#008300",
    "gallai": "#4a3aa7",
    "rockafellar": "#e34948",
    "afriat": "#e87ba4",
    "leontief_coda": "#eb6834",
}
BRANCH_LABELS = {
    "spatial": "Spatial price equilibrium",
    "definetti": "de Finetti (coherence)",
    "kantorovich": "Kantorovich (planning)",
    "koopmans": "Koopmans (activity analysis)",
    "gallai": "Gallai (graph potentials)",
    "rockafellar": "Rockafellar (monotropic)",
    "afriat": "Afriat (revealed preference)",
    "leontief_coda": "Leontief (coda)",
}
CONTEXT_COLOR = "#c3c2b7"
HOP_SIZE = {0: 220, 1: 70, 2: 28}
HOP_ALPHA = {0: 0.95, 1: 0.55, 2: 0.28}


def split_branches(cell):
    if not isinstance(cell, str) or not cell:
        return []
    return cell.split("|")


def plot_single_branch_or_context(ax, df):
    """Vectorized scatter for points with 0 or 1 branch."""
    mask_simple = df["_n_branches"] <= 1
    sub = df[mask_simple]
    for branch, group in [("", sub[sub["_n_branches"] == 0])] + [
        (b, sub[sub["_branches_list"].apply(lambda lst: lst == [b])])
        for b in BRANCH_COLORS
    ]:
        if group.empty:
            continue
        color = BRANCH_COLORS.get(branch, CONTEXT_COLOR)
        ax.scatter(
            group["pca1"], group["year"],
            s=group["hop"].map(HOP_SIZE),
            alpha=group["hop"].map(HOP_ALPHA),
            c=color, linewidths=0, zorder=2 if branch else 1,
        )


def plot_overlap_wedges(ax, df):
    """Two-branch works: split marker so both identities stay legible.

    Uses Path.wedge markers (scatter's `s` is points^2, display space) rather
    than Wedge patches anchored in data space -- x spans ~1 unit (PCA1) and y
    spans ~220 units (years), so a data-space radius renders as a flat streak
    instead of a circle.
    """
    overlap = df[df["_n_branches"] == 2]
    for _, row in overlap.iterrows():
        b1, b2 = row["_branches_list"][:2]
        size, alpha = HOP_SIZE[row["hop"]], HOP_ALPHA[row["hop"]]
        x, y = [row["pca1"]], [row["year"]]
        ax.scatter(x, y, s=size, marker=Path.wedge(90, 270), c=BRANCH_COLORS[b1],
                   alpha=alpha, linewidths=0, zorder=3)
        ax.scatter(x, y, s=size, marker=Path.wedge(270, 450), c=BRANCH_COLORS[b2],
                   alpha=alpha, linewidths=0, zorder=3)
        ax.scatter(x, y, s=size, marker=Path.wedge(0, 360), facecolors="none",
                   edgecolors="white", linewidths=1.0, zorder=4)
    if not overlap.empty:
        log.info("Overlap points drawn as split wedges: %d", len(overlap))


def label_seeds(ax, df):
    """Direct-label only the 18 costume-branch seeds -- never every point."""
    seeds = df[(df["hop"] == 0) & (df["_n_branches"] >= 1)]
    for _, row in seeds.iterrows():
        ax.annotate(
            row["seed_key"], (row["pca1"], row["year"]),
            fontsize=6, color="#0b0b0b", xytext=(4, 3),
            textcoords="offset points", zorder=5,
        )


def build_legend(ax):
    handles = [
        Line2D([0], [0], marker="o", linestyle="", color=color, markersize=8,
               label=BRANCH_LABELS[branch])
        for branch, color in BRANCH_COLORS.items()
    ]
    handles.append(
        Line2D([0], [0], marker="o", linestyle="", color=CONTEXT_COLOR, markersize=8,
               label="Context / methodology citation")
    )
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0),
              fontsize=7, frameon=False, title="Costume branch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--works-input", default=os.path.join(HET_DIR, "works_pca.csv"))
    parser.add_argument("--output-stem", default=os.path.join(HET_DIR, "het_overlap"))
    parser.add_argument("--pdf", action="store_true", help="Also save PDF")
    args = parser.parse_args()

    df = pd.read_csv(args.works_input)
    df["branches"] = df["branches"].fillna("")
    df["seed_key"] = df["seed_key"].fillna("")
    df["_branches_list"] = df["branches"].apply(split_branches)
    df["_n_branches"] = df["_branches_list"].apply(len)
    if (df["_n_branches"] > 2).any():
        log.warning("%d works reachable from >2 branches; only the first 2 are drawn",
                    (df["_n_branches"] > 2).sum())

    fig, ax = plt.subplots(figsize=(9, 6.5))
    plot_single_branch_or_context(ax, df)
    plot_overlap_wedges(ax, df)
    label_seeds(ax, df)
    build_legend(ax)

    ax.set_xlabel("PCA1 of title + abstract + keywords embedding (multilingual-MiniLM-L12)")
    ax.set_ylabel("Year of publication")
    ax.set_title("HET corpus: citation overlap across the seven costumes (+ Leontief coda)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e1e0d9", linewidth=0.6, zorder=0)
    fig.tight_layout()

    save_figure(fig, args.output_stem, pdf=args.pdf, dpi=200)
    fig.savefig(f"{args.output_stem}.svg", bbox_inches="tight")
    log.info("Saved -> %s.svg", args.output_stem)


if __name__ == "__main__":
    main()
