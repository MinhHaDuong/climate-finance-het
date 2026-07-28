"""The Z-series vars carry real numbers, and degrade without inventing any (0570).

Five keys — the three `*_peak_year_w3` and the two zone bounds — were written
as the literal `[MISSING]` and quoted by a results paragraph of
`multilayer-detection.qmd`, which therefore published "S2 energy distance
peaks at year [MISSING]" at exit code 0. `test_render_placeholders.py` closes
the publishing side; this closes the producing side.

Two properties, and they pull in opposite directions, which is why both are
pinned here:

* with the summary tables present, `zseries_stats` reports the peak years and
  the first validated zone;
* without them, it writes nothing at all, so `main`'s `setdefault` fallback
  still fires and `make stats` keeps working on a checkout that has never run
  the divergence chain.

The zone rule itself is checked directly rather than only through the
collector: the figure draws its borders from the same two helpers, and a
regression there would move the sentence and the figure together, leaving them
consistent and both wrong.
"""

import logging
import os
import sys

import _companion_plot_utils
import numpy as np
import pandas as pd
import pytest
from _companion_plot_utils import contiguous_runs, validated_zone_columns

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "analysis"))
import compute_vars

#: Years the fixture puts above threshold on every method, in two separate
#: runs — the shape the real corpus has (a 2007-2009 zone and a 2013-2015 one).
ZONE_A = (2008, 2009, 2010)
ZONE_B = (2014, 2015)
PEAK = 2009


def _summary(method: str, peak: int = PEAK) -> pd.DataFrame:
    """A tab_summary_{method}.csv whose w=3 rows peak at `peak`.

    Two decoys, because the collector must ignore both:

    * other *windows* carry a higher Z at a different year, so a collector that
      forgot to filter on the window reports that year instead;
    * the years *below* `companion.year_min` carry the highest Z in the table,
      which is what the real S2 table does — it starts at 1993 and its argmax
      is 1996, six years before the figure the sentence cites begins.

    Both make a wrong collector fail loudly rather than coincidentally agree.
    """
    rows = []
    for year in range(1993, 2022):
        for window in (2, 3, 4):
            if year < 1998:
                z = 200.0
            elif window == 3:
                z = 9.0 if year == peak else (3.0 if year in ZONE_A + ZONE_B else 0.4)
            else:
                z = 99.0 if year == 1999 else 0.1
            rows.append({
                "method": method, "year": year, "window": window,
                "hyperparams": "default", "point_estimate": 0.1,
                "boot_median": 0.1, "boot_q025": 0.0, "boot_q975": 0.2,
                "z_score": z, "p_value": 0.01, "significant": z >= 2.0,
            })
    return pd.DataFrame(rows)


@pytest.fixture
def tables(tmp_path, monkeypatch):
    """A tables dir holding the three summary tables the collector reads."""
    for method in ("S2_energy", "L1", "G9_community"):
        _summary(method).to_csv(tmp_path / f"tab_summary_{method}.csv", index=False)
    monkeypatch.setattr(compute_vars, "DERIVED_TABLES_DIR", str(tmp_path))
    return tmp_path


# ─── The zone rule, shared with the heatmap ──────────────────────────────


def test_validated_zone_needs_enough_methods():
    """A column is validated only once `min_methods` rows clear the threshold."""
    signal = np.array([[3.0, 3.0, 0.1], [3.0, 0.1, 0.1]])
    assert list(validated_zone_columns(signal, 2.0, 2)) == [0]


def test_validated_zone_counts_negative_signal():
    """A strongly negative Z is a discontinuity too — the rule takes abs()."""
    signal = np.array([[-3.0], [-3.0]])
    assert list(validated_zone_columns(signal, 2.0, 2)) == [0]


def test_validated_zone_treats_a_missing_cell_as_not_clearing():
    """A nan must not poison the column count, or a short series erases a zone."""
    signal = np.array([[3.0], [3.0], [np.nan]])
    assert list(validated_zone_columns(signal, 2.0, 2)) == [0]


def test_contiguous_runs_splits_at_a_gap():
    """Two zones stay two: min/max over the whole set would merge them."""
    assert contiguous_runs([1, 2, 3, 7, 8]) == [[1, 2, 3], [7, 8]]


def test_contiguous_runs_of_nothing_is_nothing():
    assert contiguous_runs([]) == []


# ─── The collector ───────────────────────────────────────────────────────


def test_peak_years_come_from_the_w3_rows(tables):
    """Each peak year is the w=3 argmax, not the larger Z at another window."""
    v = {}
    compute_vars.zseries_stats(v)
    assert v["s2_peak_year_w3"] == str(PEAK)
    assert v["l1_peak_year_w3"] == str(PEAK)
    assert v["g9_peak_year_w3"] == str(PEAK)


def test_peak_year_ignores_years_the_figure_does_not_show(tables):
    """The argmax is taken over `companion.year_min..year_max`, nothing wider.

    Replaying the real defect, not a synthetic one: `tab_summary_S2_energy.csv`
    starts at 1993 and its unrestricted w=3 argmax is 1996, while
    `plot_companion_zseries` sets `xlim(year_min, year_max)` = 1998..2021 and
    the sentence quoting this key points at that figure. An unrestricted collector
    publishes a peak year the reader cannot find on the figure cited beside it.
    The fixture's pre-1998 rows carry the table's largest Z for exactly this
    reason, so a collector that drops the restriction reports 1993 here.
    """
    v = {}
    compute_vars.zseries_stats(v)
    cfg = _companion_plot_utils.companion_config()
    for key in ("s2_peak_year_w3", "l1_peak_year_w3", "g9_peak_year_w3"):
        assert int(cfg["year_min"]) <= int(v[key]) <= int(cfg["year_max"])


def test_zone_1_is_the_first_run_not_the_whole_span(tables):
    """Zone 1 ends where the run ends, not where the last validated year is."""
    v = {}
    compute_vars.zseries_stats(v)
    assert (v["zone_1_start"], v["zone_1_end"]) == (str(ZONE_A[0]), str(ZONE_A[-1]))


def test_no_key_is_a_sentinel_when_the_tables_are_there(tables):
    """The point of the ticket: with data present, nothing reads as unavailable."""
    v = {}
    compute_vars.zseries_stats(v)
    assert compute_vars.MISSING not in v.values()
    assert len(v) == 5


def test_partial_build_writes_nothing(tmp_path, monkeypatch):
    """No summary tables: every key is left for main()'s setdefault fallback.

    Writing a placeholder here instead would be the same defect one layer up,
    and *raising* would break `make stats` on every checkout that has not run
    the divergence chain — the invariant this ticket is explicitly bound by.
    """
    monkeypatch.setattr(compute_vars, "DERIVED_TABLES_DIR", str(tmp_path))
    v = {}
    compute_vars.zseries_stats(v)
    assert v == {}


def test_a_renamed_window_refuses_rather_than_mislabel(tables, monkeypatch, caplog):
    """Changing lead_window must not write a w=4 number into a `_w3` key.

    That is this ticket's own defect class — a value that reads as something it
    is not — so the collector declines and leaves the sentinel, which the
    render guard then reports.
    """
    import _companion_plot_utils

    cfg = dict(_companion_plot_utils.companion_config())
    cfg["lead_window"] = 4
    monkeypatch.setattr(_companion_plot_utils, "companion_config", lambda: cfg)
    # `utils.get_logger` hangs every script logger under a "pipeline" parent
    # that sets propagate=False, so nothing reaches the root handler pytest
    # captures with. Re-enable propagation on that parent for this test;
    # monkeypatch restores it.
    monkeypatch.setattr(logging.getLogger("pipeline"), "propagate", True)
    v = {}
    with caplog.at_level(logging.ERROR, logger=compute_vars.log.name):
        compute_vars.zseries_stats(v)
    assert v == {}
    assert "_w3" in caplog.text
