"""Figure 2 (companion paper): transition zone validation heatmap.

Rows: the six lead methods (S2 Energy, L1 JS, G9 Community, G2 Spectral,
C2ST embedding, C2ST lexical).
Columns: years from ``companion.year_min`` to ``companion.year_max``.
Cell value: Z-score for distance methods, (AUC − 0.5) × ``auc_scale``
for C2ST rows — so the colormap stays on a common signal scale.

Validated zones (≥ ``validated_zone_min_methods`` rows above the
``z_threshold`` simultaneously) are marked with rectangular borders.

Usage::

    uv run python scripts/plot_companion_heatmap.py \\
        --output content/figures/fig_companion_heatmap.png \\
        [--tables-dir path/to/tables]
"""

import argparse
import sys

import matplotlib.pyplot as plt
import numpy as np
from _companion_plot_utils import (
    add_tables_dir_arg,
    companion_config,
    load_c2st_tables,
    load_summary_tables,
    save_companion_figure,
    signal_matrix,
    validated_zone_columns,
)
from matplotlib.patches import Rectangle
from plot_style import DPI, FIGWIDTH, apply_style
from script_io_args import parse_io_args, validate_io
from utils import get_logger

log = get_logger("plot_companion_heatmap")
apply_style()


def main() -> None:
    io_args, extra = parse_io_args()
    validate_io(output=io_args.output)

    parser = argparse.ArgumentParser()
    add_tables_dir_arg(parser)
    args = parser.parse_args(extra)

    cfg = companion_config()
    window = int(cfg["lead_window"])
    z_thr = float(cfg["z_threshold"])
    y0, y1 = int(cfg["year_min"]), int(cfg["year_max"])
    min_methods = int(cfg["validated_zone_min_methods"])
    auc_chance = float(cfg["auc_chance"])
    auc_scale = float(cfg["auc_scale"])
    methods_labels = cfg["methods"]
    zone_edge = cfg["colors"]["zone_edge"]
    cmap = cfg["colors"]["z_cmap"]

    row_order = list(methods_labels.keys())
    years = list(range(y0, y1 + 1))

    summaries = load_summary_tables(args.tables_dir)
    c2sts = load_c2st_tables(args.tables_dir)
    mat = signal_matrix(
        summaries,
        c2sts,
        years,
        window,
        auc_chance,
        auc_scale,
        row_order,
    )

    # Symmetric normalisation around zero so the diverging cmap reads truthfully.
    vmax = float(np.nanmax(np.abs(mat))) if np.isfinite(mat).any() else z_thr
    vmax = max(vmax, z_thr * 1.2)

    fig, ax = plt.subplots(figsize=(FIGWIDTH, 3.2))
    im = ax.imshow(
        mat,
        aspect="auto",
        cmap=cmap,
        vmin=-vmax,
        vmax=vmax,
        origin="upper",
        extent=(y0 - 0.5, y1 + 0.5, len(row_order) - 0.5, -0.5),
        interpolation="nearest",
    )

    # Yearly validated-zone borders (per column). The rule lives in
    # _companion_plot_utils so the prose in the paper (compute_vars reads the
    # same helper for zone_1_start/end) cannot drift from what is drawn here.
    zone_cols = validated_zone_columns(mat, z_thr, min_methods)
    for c in zone_cols:
        ax.add_patch(
            Rectangle(
                (years[c] - 0.5, -0.5),
                1.0,
                len(row_order),
                fill=False,
                edgecolor=zone_edge,
                linewidth=1.2,
                zorder=5,
            )
        )

    ax.set_yticks(range(len(row_order)))
    ax.set_yticklabels([methods_labels[m] for m in row_order])
    ax.set_xlabel("Year")
    ax.set_xticks([y for y in years if y % 5 == 0 or y in (y0, y1)])
    ax.set_title(f"Transition zone heatmap (window = {window})")

    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label(f"Signal (Z or (AUC−{auc_chance:g})×{auc_scale:g})")

    fig.tight_layout()
    save_companion_figure(fig, io_args.output, dpi=DPI)
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
