"""Figure 4 (companion paper): community sizes before/after each zone.

The ticket asks for an alluvial / Sankey flow between Louvain community
structures before and after each validated zone.  Alluvial layouts are
fragile with unknown community counts, so this script renders the
robust fallback mentioned in the ticket: a grouped bar chart showing
community sizes on each side of each validated zone.

Reads ``tab_community_shifts.csv`` (or ``tab_community_shifts_{zone}.csv``
parts) from ``--tables-dir``. An absent interpretation table is an error
(ticket 0064).

Expected schema:
    zone, side, community_id, size[, label]

Usage::

    uv run python scripts/plot_companion_community.py \\
        --output content/figures/fig_companion_community.png \\
        [--tables-dir path/to/tables]
"""

import argparse
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from _companion_plot_utils import (
    add_tables_dir_arg,
    read_csv_or_none,
    save_companion_figure,
)
from plot_style import DARK, DPI, FIGWIDTH, LIGHT, apply_style
from script_io_args import parse_io_args, validate_io

apply_style()


def _load_shifts(tables_dir: str) -> pd.DataFrame:
    primary = os.path.join(tables_dir, "tab_community_shifts.csv")
    df = read_csv_or_none(primary)
    if df is not None and not df.empty:
        return df
    parts = []
    if os.path.isdir(tables_dir):
        for name in sorted(os.listdir(tables_dir)):
            if name.startswith("tab_community_shifts_") and name.endswith(".csv"):
                part = pd.read_csv(os.path.join(tables_dir, name))
                if "zone" not in part.columns:
                    part["zone"] = name[len("tab_community_shifts_") : -len(".csv")]
                parts.append(part)
    if parts:
        return pd.concat(parts, ignore_index=True)
    raise FileNotFoundError(
        f"tab_community_shifts.csv missing or empty in {tables_dir}; "
        "build the interpretation layer (ticket 0064)"
    )


def main() -> None:
    io_args, extra = parse_io_args()
    validate_io(output=io_args.output)

    parser = argparse.ArgumentParser()
    add_tables_dir_arg(parser)
    args = parser.parse_args(extra)

    df = _load_shifts(args.tables_dir)
    zones = sorted(df["zone"].unique())
    n_zones = max(1, len(zones))

    fig, axes = plt.subplots(
        1,
        n_zones,
        figsize=(FIGWIDTH, 3.2),
        sharey=True,
    )
    if n_zones == 1:
        axes = [axes]

    for ax, zone in zip(axes, zones):
        sub = df[df["zone"] == zone].copy()
        pivot = (
            sub.groupby(["community_id", "side"])["size"]
            .sum()
            .unstack("side")
            .fillna(0.0)
            .sort_index()
        )
        communities = list(pivot.index)
        x = np.arange(len(communities))
        width = 0.4

        before = pivot.get("before", pd.Series(0, index=communities))
        after = pivot.get("after", pd.Series(0, index=communities))

        ax.bar(x - width / 2, before, width, label="before", color=LIGHT)
        ax.bar(x + width / 2, after, width, label="after", color=DARK)
        ax.set_xticks(x)
        ax.set_xticklabels([f"c{int(c)}" for c in communities])
        ax.set_title(str(zone))
        ax.set_xlabel("Community")
    axes[0].set_ylabel("Size (documents)")
    axes[0].legend(frameon=False, fontsize=7)

    fig.tight_layout()
    save_companion_figure(fig, io_args.output, dpi=DPI)
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
