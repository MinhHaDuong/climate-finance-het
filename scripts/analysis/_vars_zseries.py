"""Z-series vars: peak years, peak stability, and the validated transition zone.

Split out of `compute_vars` (ticket 0570), following the `_vars_retrieval` /
`_vars_ablation` pattern — the collector plus its two helpers pushed that
module past the god-module line limit, and this is the seam the house style
already uses for a self-contained group of variables.

`_companion_plot_utils` is imported inside the functions rather than at module
scope: it is a figure-side helper that pulls matplotlib, and `compute_vars` is
imported by guards that only want its constants.
"""

from utils import DERIVED_TABLES_DIR, get_logger

log = get_logger("vars_zseries")


def _peak_year(df, window, year_min, year_max):
    """Year of the largest Z-score at ``window``, within ``[year_min, year_max]``.

    The year window is not decoration. The divergence tables run wider than the
    companion analysis reports — `tab_summary_S2_energy.csv` starts at 1993 —
    and the S2 argmax over the full table is 1996, while `plot_companion_zseries`
    draws `set_xlim(year_min, year_max)` and the sentence quoting this value
    points at that figure. An unrestricted argmax therefore names a year the
    reader cannot find on the figure cited beside it, which is this ticket's own
    defect class one step over: not a missing number, a number that answers a
    different question than the sentence asks. The zone bounds below were
    already restricted (`signal_matrix` is built on `years`), so restricting
    here also makes the five keys answer over one range instead of two.

    None rather than an exception when the table is absent or carries no
    Z-score in range: a partial build has no summary tables at all, and the
    caller's fallback is what keeps `make stats` working there.
    """
    if df is None or df.empty:
        return None
    from _companion_plot_utils import window_rows

    rows = window_rows(df, window)
    if "z_score" not in rows.columns:
        return None
    rows = rows[(rows["year"] >= year_min) & (rows["year"] <= year_max)]
    if not rows["z_score"].notna().any():
        return None
    return int(rows.loc[rows["z_score"].idxmax(), "year"])


def _peak_spread(df, year_min, year_max):
    """Range in years between the earliest and latest peak across half-widths.

    Zero when every window agrees on the peak year. The sweep is over whatever
    windows the table carries — §4.8 varies `w` over {2,3,4} — rather than a
    hardcoded set, so the number tracks the table instead of a stale comment.
    """
    if df is None or df.empty or "window" not in df.columns:
        return None
    peaks = [
        p
        for w in sorted(df["window"].dropna().unique())
        if (p := _peak_year(df, int(w), year_min, year_max)) is not None
    ]
    return max(peaks) - min(peaks) if peaks else None


def zseries_stats(v):
    """Z-series peak years and the first validated transition zone (0570).

    Reads the three `tab_summary_*.csv` the divergence chain produces. The
    ticket-0570 comment these vars used to carry — "not yet generated" — was
    stale: `divergence.mk` has built those targets since the bootstrap/null
    work landed, so what was missing was a reader, not the data.

    The zone bounds come from the same helper the heatmap draws its borders
    with, on the same signal matrix, because the paragraph in the paper says
    "@fig-heatmap marks it as a confirmed discontinuity" — a second definition
    here would let the sentence and the figure it points at disagree.

    `_companion_plot_utils` is imported inside the function, not at module
    scope: it is a figure-side helper, and `compute_vars` is imported by guards
    that only want its constants. Nothing here degrades to an exception — a
    machine without the summary tables leaves every key untouched for the
    caller's fallback, which is the partial-build path this ticket must keep.
    """
    from _companion_plot_utils import (
        companion_config,
        contiguous_runs,
        load_c2st_tables,
        load_summary_tables,
        signal_matrix,
        validated_zone_columns,
    )

    cfg = companion_config()
    window = int(cfg["lead_window"])
    if window != 3:
        # The key names pin the window (`_w3`). Writing a w=4 number into a key
        # that says w3 is this ticket's own defect class — a value that reads
        # as something it is not — so refuse and let the keys fall back to the
        # sentinel, which the render guard then reports.
        log.error(
            "companion.lead_window is %d but the Z-series vars are named _w3; "
            "rename the keys (and the prose) before changing the window.",
            window,
        )
        return

    summaries = load_summary_tables(DERIVED_TABLES_DIR)
    if not summaries:
        log.info("No tab_summary_*.csv in %s — Z-series vars stay unset.",
                 DERIVED_TABLES_DIR)
        return

    year_min, year_max = int(cfg["year_min"]), int(cfg["year_max"])
    for key, method in (
        ("s2_peak_year_w3", "S2_energy"),
        ("l1_peak_year_w3", "L1"),
        ("g9_peak_year_w3", "G9_community"),
    ):
        peak = _peak_year(summaries.get(method), window, year_min, year_max)
        if peak is not None:
            v[key] = str(peak)

    # How far each peak travels as the half-width varies (§4.8 sweeps w over
    # {2,3,4}). §5.1 quotes these to argue a peak year is a weak summary of
    # these series, and a hand-typed spread would rot at the next corpus
    # rebuild exactly as the numbers this ticket replaced did.
    for key, method in (
        ("s2_peak_spread_w234", "S2_energy"),
        ("l1_peak_spread_w234", "L1"),
        ("g9_peak_spread_w234", "G9_community"),
    ):
        spread = _peak_spread(summaries.get(method), year_min, year_max)
        if spread is not None:
            v[key] = str(spread)

    years = list(range(year_min, year_max + 1))
    mat = signal_matrix(
        summaries,
        load_c2st_tables(DERIVED_TABLES_DIR),
        years,
        window,
        float(cfg["auc_chance"]),
        float(cfg["auc_scale"]),
        list(cfg["methods"].keys()),
    )
    runs = contiguous_runs(
        validated_zone_columns(
            mat, float(cfg["z_threshold"]), int(cfg["validated_zone_min_methods"])
        )
    )
    if runs:
        v["zone_1_start"] = str(years[runs[0][0]])
        v["zone_1_end"] = str(years[runs[0][-1]])
