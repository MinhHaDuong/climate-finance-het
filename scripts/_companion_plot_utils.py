"""Shared helpers for the companion-paper figure scripts (ticket 0058).

All four ``plot_companion_*.py`` scripts share:
- a preferred location for their input CSVs (``content/tables/``),
- a ``--tables-dir`` override used by the test suite,
- the companion config block in ``config/analysis.yaml``,
- a thin wrapper around ``pipeline_io.save_figure`` that respects
  ``os.path.splitext(--output)[0]`` as the stem (so Make controls the path).

Keeping this logic in one place avoids duplication across the four plot
scripts while staying well inside Phase 2 rules 4 (compute/plot/include
separate) and 5 (save_figure mandatory).
"""

import os
from typing import Any

import numpy as np
import pandas as pd
from pipeline_io import save_figure
from utils import DERIVED_TABLES_DIR, load_analysis_config

DEFAULT_TABLES_DIR = DERIVED_TABLES_DIR

# Method IDs in the fixed lead order used by the heatmap and Z-series panels.
DISTANCE_METHODS = ("S2_energy", "L1", "G9_community", "G2_spectral")
C2ST_CHANNELS = ("embedding", "lexical")


def companion_config() -> dict[str, Any]:
    """Return the ``companion`` block of ``config/analysis.yaml``.

    Raises
    ------
    KeyError if the block is missing — plot scripts should surface the
    config-discipline violation rather than silently fall back to defaults.

    """
    cfg = load_analysis_config()
    if "companion" not in cfg:
        raise KeyError(
            "config/analysis.yaml is missing the 'companion:' block. "
            "Add it per ticket 0058."
        )
    return cfg["companion"]


def add_tables_dir_arg(parser) -> None:
    """Register the shared ``--tables-dir`` option on an argparse parser."""
    parser.add_argument(
        "--tables-dir",
        default=DEFAULT_TABLES_DIR,
        help=(
            "Directory holding tab_summary_*.csv / tab_div_C2ST_*.csv / "
            "tab_discrim_terms*.csv / tab_community_shifts*.csv. "
            "Defaults to content/tables/."
        ),
    )


def read_csv_or_none(path: str) -> pd.DataFrame | None:
    """Return a DataFrame or ``None`` if the file is absent."""
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


def load_summary_tables(tables_dir: str) -> dict[str, pd.DataFrame]:
    """Load tab_summary_{method}.csv for the four distance methods.

    Missing tables are skipped (the caller decides whether to degrade
    gracefully).  Returns a dict {method: DataFrame}.
    """
    out: dict[str, pd.DataFrame] = {}
    for method in DISTANCE_METHODS:
        df = read_csv_or_none(os.path.join(tables_dir, f"tab_summary_{method}.csv"))
        if df is not None and not df.empty:
            out[method] = df
    return out


def load_c2st_tables(tables_dir: str) -> dict[str, pd.DataFrame]:
    """Load tab_div_C2ST_{embedding,lexical}.csv.

    Returns a dict keyed ``'C2ST_embedding'`` / ``'C2ST_lexical'`` so the
    four distance keys and the two C2ST keys live in the same namespace.
    """
    out: dict[str, pd.DataFrame] = {}
    for channel in C2ST_CHANNELS:
        df = read_csv_or_none(os.path.join(tables_dir, f"tab_div_C2ST_{channel}.csv"))
        if df is not None and not df.empty:
            out[f"C2ST_{channel}"] = df
    return out


def save_companion_figure(fig, output_path: str, dpi: int = 300) -> None:
    """Strip the extension from ``output_path`` and save via ``save_figure``."""
    stem = os.path.splitext(output_path)[0]
    save_figure(fig, stem, dpi=dpi)


def signal_matrix(
    summaries: dict[str, pd.DataFrame],
    c2sts: dict[str, pd.DataFrame],
    years: list[int],
    window: int,
    auc_chance: float,
    auc_scale: float,
    row_order: list[str],
) -> np.ndarray:
    """Build the (method, year) signed signal matrix the zone rule runs on.

    Distance rows carry their Z-score; C2ST rows carry ``(AUC − auc_chance) ×
    auc_scale``, which puts both on one scale so a single threshold reads
    across the two kinds of detector. Cells no table covers stay ``nan``.

    Shared with the zone rule below because the two are one decision: which
    years count as validated depends on what went into the matrix, so a caller
    that builds its own matrix has, in effect, its own zone definition.
    """
    mat = np.full((len(row_order), len(years)), np.nan, dtype=float)
    year_to_col = {y: i for i, y in enumerate(years)}

    for i, method in enumerate(row_order):
        if method in summaries:
            sub = window_rows(summaries[method], window)
            for _, row in sub.iterrows():
                y = int(row["year"])
                if y in year_to_col and pd.notna(row.get("z_score")):
                    mat[i, year_to_col[y]] = float(row["z_score"])
        elif method in c2sts:
            sub = window_rows(c2sts[method], window)
            for _, row in sub.iterrows():
                y = int(row["year"])
                if y in year_to_col and pd.notna(row.get("value")):
                    mat[i, year_to_col[y]] = (float(row["value"]) - auc_chance) * auc_scale
    return mat


def validated_zone_columns(
    signal: np.ndarray, z_threshold: float, min_methods: int
) -> np.ndarray:
    """Column indices where at least ``min_methods`` rows clear the threshold.

    One definition of "which years form a validated zone", used by the heatmap
    that draws the borders and by ``compute_vars``, which reports the zone's
    bounds in prose. Two implementations would let the figure and the sentence
    beside it disagree without either being wrong on its own terms.

    ``signal`` is the (method, year) matrix the heatmap displays: Z-scores for
    the distance rows, rescaled AUC for the C2ST rows, so a single threshold
    reads across both. ``np.abs`` before the comparison is deliberate — a
    strongly *negative* Z is as much a discontinuity as a positive one — and
    ``np.nansum`` counts a missing cell as not-clearing rather than poisoning
    the column, which is what lets a method with a short year range participate.
    """
    above = np.abs(signal) >= z_threshold
    return np.where(np.nansum(above, axis=0) >= min_methods)[0]


def contiguous_runs(indices) -> list[list[int]]:
    """Split a sorted index sequence into maximal runs of consecutive integers.

    A zone is a *run* of validated years, not the scattered set of them: the
    companion analysis reports two zones (around 2007--2009 and 2013--2015),
    and reading the first zone's bounds off min/max of the whole set would
    merge them into one span covering everything between.
    """
    runs: list[list[int]] = []
    for i in sorted(int(x) for x in indices):
        if runs and i == runs[-1][-1] + 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    return runs


def window_rows(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """Return rows whose ``window`` column matches ``window``.

    The CSVs use a string-or-int window; coerce defensively.
    """
    if "window" not in df.columns:
        return df
    w_str = str(window)
    mask = df["window"].astype(str).eq(w_str)
    return df.loc[mask]
