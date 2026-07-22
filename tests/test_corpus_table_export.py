"""Tests for export_corpus_table.py — ticket #252, #270.

Verifies that the exported CSV has correct columns and that Raw counts
use from_* columns (not the source column fallback).
"""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "figures"))  # 0255: moved figures entry points
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "analysis"))  # 0288: compute_vars data-driven source count

TABLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "deliverables", "_shared", "tables",
)
CSV_PATH = os.path.join(TABLES_DIR, "tab_corpus_sources.csv")


@pytest.fixture
def corpus_table():
    """Load the exported corpus sources table.

    The CSV is a Make-generated, untracked artifact (`make corpus-tables`);
    on a machine that has not built it the tests skip rather than error
    (ticket 0263, cluster 1 — data-complete machines still validate it).
    """
    if not os.path.exists(CSV_PATH):
        pytest.skip(f"{CSV_PATH} not built here — run make corpus-tables (ticket 0263)")
    return pd.read_csv(CSV_PATH)


@pytest.mark.slow
def test_required_columns(corpus_table):
    """Table must have Raw, Refined, and Unique columns."""
    for col in ("Raw", "Refined", "Unique"):
        assert col in corpus_table.columns, f"Missing column: {col}"


@pytest.mark.slow
def test_raw_counts_use_from_columns(corpus_table):
    """Raw counts must reflect from_* totals, not primary-source fallback.

    The usecols=["source"] bug caused ISTEX Raw=1 and bibCNRS Raw=212.
    With from_* columns, ISTEX Raw>=4 and bibCNRS Raw>=233.
    """
    row_istex = corpus_table[corpus_table["Source"] == "ISTEX"]
    assert len(row_istex) == 1, "ISTEX row missing"
    assert row_istex.iloc[0]["Raw"] >= 4, (
        f"ISTEX Raw={row_istex.iloc[0]['Raw']} — likely still using source column fallback"
    )

    row_bib = corpus_table[corpus_table["Source"] == "bibCNRS"]
    assert len(row_bib) == 1, "bibCNRS row missing"
    assert row_bib.iloc[0]["Raw"] >= 233, (
        f"bibCNRS Raw={row_bib.iloc[0]['Raw']} — likely still using source column fallback"
    )


@pytest.mark.slow
def test_unique_column_plausible(corpus_table):
    """Unique must be <= Refined for every source."""
    data_rows = corpus_table[corpus_table["Source"] != "TOTAL"]
    for _, row in data_rows.iterrows():
        if pd.notna(row.get("Unique")) and pd.notna(row.get("Refined")):
            assert row["Unique"] <= row["Refined"], (
                f"{row['Source']}: Unique ({row['Unique']}) > Refined ({row['Refined']})"
            )


@pytest.mark.slow
def test_total_row_present(corpus_table):
    """A TOTAL row must exist."""
    total = corpus_table[corpus_table["Source"] == "TOTAL"]
    assert len(total) == 1, "Missing TOTAL row"


def test_source_meta_matches_source_names():
    """SOURCE_META keys must match utils.SOURCE_NAMES (single source of truth)."""
    from export_corpus_table import SOURCE_META
    from utils import SOURCE_NAMES
    assert set(SOURCE_META.keys()) == set(SOURCE_NAMES), (
        f"SOURCE_META keys {set(SOURCE_META.keys())} != "
        f"SOURCE_NAMES {set(SOURCE_NAMES)}"
    )


class TestKeydocsSourcesPreV2Data:
    """Ticket 0288: unfccc/oecd join SOURCE_NAMES before the v2 corpus is
    rebuilt. Phase-2 renders on v1 data must not change: a source whose
    from_* column is absent from BOTH unified and refined frames is skipped,
    and the corpus_sources var counts columns present in the data, not the
    forward-looking SOURCE_NAMES constant."""

    def test_sources_present_skips_absent_layer(self):
        from export_corpus_table import sources_present

        v1_cols = ["source", "from_openalex", "from_istex", "from_bibcnrs",
                   "from_scispace", "from_grey", "from_teaching"]
        present = sources_present(v1_cols, v1_cols)
        assert "unfccc" not in present
        assert "oecd" not in present
        assert "openalex" in present and "grey" in present

    def test_sources_present_includes_layer_when_column_exists(self):
        from export_corpus_table import sources_present

        v2_cols = ["source", "from_openalex", "from_unfccc", "from_oecd"]
        present = sources_present(v2_cols, [])
        assert "unfccc" in present
        assert "oecd" in present

    def test_count_sources_is_data_driven(self):
        import pandas as pd
        from compute_vars import count_sources

        v1 = pd.DataFrame(columns=["title", "from_openalex", "from_istex",
                                   "from_bibcnrs", "from_scispace",
                                   "from_grey", "from_teaching"])
        assert count_sources(v1) == 6
        v2 = pd.DataFrame(columns=list(v1.columns) + ["from_unfccc", "from_oecd"])
        assert count_sources(v2) == 8
