"""The deposited removal-ablation table is internally consistent (ticket 0337).

The ticket's red test: the ``removed`` column, summed over any complete
stratification, equals the pipeline's total removals. A table failing this
double-counts or drops works, and the §2.3 disclosure built on it inherits
the error. The source axis is exempt — a work found by two sources appears
in both rows by design.
"""

import os

import pandas as pd
import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TABLE = os.path.join(
    REPO, "deliverables", "_shared", "tables", "tab_filter_ablation.csv"
)
QMD = os.path.join(REPO, "deliverables", "data-paper", "data-paper.qmd")

COMPLETE_AXES = ["language", "period", "doi", "citation_decile"]


@pytest.fixture(scope="module")
def table():
    return pd.read_csv(TABLE)


@pytest.fixture(scope="module")
def totals(table):
    row = table[table["axis"].eq("corpus")]
    assert len(row) == 1, "exactly one corpus total row"
    return row.iloc[0]


@pytest.mark.parametrize("axis", COMPLETE_AXES)
def test_complete_axes_sum_to_the_corpus_totals(table, totals, axis):
    part = table[table["axis"].eq(axis)]
    for col in ("n", "flagged", "rescued", "removed"):
        assert part[col].sum() == totals[col], (
            f"axis {axis!r}: {col} sums to {part[col].sum()} against a corpus "
            f"total of {totals[col]} — the stratification drops or "
            "double-counts works"
        )


def test_flag_arithmetic_holds(table):
    """flagged = rescued + removed on every complete stratum: a flagged work
    is either rescued by protection or removed, never both, never neither."""
    part = table[table["axis"].isin(COMPLETE_AXES + ["corpus"])]
    mismatch = part[part["flagged"] != part["rescued"] + part["removed"]]
    assert mismatch.empty, (
        f"flagged != rescued + removed in:\n{mismatch.to_string(index=False)}"
    )


def test_prose_quotes_the_deposited_shares():
    """§2.3's ablation sentence carries macros, and the vars they resolve to
    come from this table (compute_vars.filter_ablation_stats reads it back),
    so prose and artifact cannot diverge. This test pins the prose side: the
    macros are present and the table is named."""
    qmd = open(QMD).read()
    for macro in (
        "ablation_nonen_removed_pct",
        "ablation_en_removed_pct",
        "ablation_f6_nonen_share_pct",
    ):
        assert macro in qmd, f"data-paper.qmd lost the {macro} macro"
    assert "`tab_filter_ablation.csv`" in qmd, (
        "data-paper.qmd no longer names the deposited ablation table"
    )
