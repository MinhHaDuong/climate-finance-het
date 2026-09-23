"""Figure 3 (companion paper): discriminative terms per validated zone.

Reads ``tab_discrim_terms.csv`` (ticket 0056 interpretation layer) from
``--tables-dir`` and renders a grouped horizontal bar chart of the top
``companion.top_terms`` terms (by log-odds) for each validated zone.

An absent interpretation table is an error (ticket 0064).

Expected schema (one row per term × zone):
    zone, term, log_odds, direction, rank

Usage::

    uv run python scripts/plot_companion_terms.py \\
        --output content/figures/fig_companion_terms.png \\
        [--tables-dir path/to/tables]
"""

import argparse
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd
from _companion_plot_utils import (
    add_tables_dir_arg,
    companion_config,
    read_csv_or_none,
    save_companion_figure,
)
from plot_style import DARK, DPI, FIGWIDTH, LIGHT, apply_style
from script_io_args import parse_io_args, validate_io

apply_style()


def _load_terms(tables_dir: str) -> pd.DataFrame:
    primary = os.path.join(tables_dir, "tab_discrim_terms.csv")
    df = read_csv_or_none(primary)
    if df is not None and not df.empty:
        return df
    # Allow per-zone files (tab_discrim_terms_{zone}.csv) — concatenate them.
    parts = []
    if os.path.isdir(tables_dir):
        for name in sorted(os.listdir(tables_dir)):
            if name.startswith("tab_discrim_terms_") and name.endswith(".csv"):
                part = pd.read_csv(os.path.join(tables_dir, name))
                if "zone" not in part.columns:
                    part["zone"] = name[len("tab_discrim_terms_") : -len(".csv")]
                parts.append(part)
    if parts:
        return pd.concat(parts, ignore_index=True)
    raise FileNotFoundError(
        f"tab_discrim_terms.csv missing or empty in {tables_dir}; "
        "build the interpretation layer (ticket 0064)"
    )


def main() -> None:
    io_args, extra = parse_io_args()
    validate_io(output=io_args.output)

    parser = argparse.ArgumentParser()
    add_tables_dir_arg(parser)
    args = parser.parse_args(extra)

    cfg = companion_config()
    top_n = int(cfg["top_terms"])
    df = _load_terms(args.tables_dir)
    zones = sorted(df["zone"].unique())
    n_zones = max(1, len(zones))

    fig, axes = plt.subplots(
        1,
        n_zones,
        figsize=(FIGWIDTH, 1.2 + 0.22 * top_n),
        sharey=False,
    )
    if n_zones == 1:
        axes = [axes]

    for ax, zone in zip(axes, zones):
        sub = df[df["zone"] == zone].sort_values("log_odds", ascending=True).tail(top_n)
        colors = [DARK if v >= 0 else LIGHT for v in sub["log_odds"]]
        ax.barh(sub["term"], sub["log_odds"], color=colors)
        ax.axvline(0, color="black", linewidth=0.6)
        ax.set_title(str(zone))
        ax.set_xlabel("Log-odds")

    fig.tight_layout()
    save_companion_figure(fig, io_args.output, dpi=DPI)
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
