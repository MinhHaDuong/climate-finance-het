"""Tests for export_corpus_table.py — ticket #252, #270, 0370.

Verifies that the exported CSV has correct columns, that Raw counts use
from_* columns (not the source column fallback), and that the Markdown
sibling survives rendering with a pipe-bearing value (ticket 0370).
"""

import os
import sys
from html import escape

import pandas as pd
import pytest
from _qmd_render import cell_texts, render_qmd, require_pandoc, row_with

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


class TestTotalRowIsTheDeduplicatedUnion:
    """Ticket 0327, gaps 3 and 4: the per-source columns count provenance
    *memberships*, so they sum above the TOTAL row, which counts distinct
    works. The table has to say so and give the overlap for both columns."""

    @pytest.mark.slow
    def test_total_is_not_the_naive_column_sum(self, corpus_table):
        rows = corpus_table[corpus_table["Source"] != "TOTAL"]
        total = corpus_table[corpus_table["Source"] == "TOTAL"].iloc[0]
        for col in ("Raw", "Refined"):
            assert rows[col].sum() > total[col], (
                f"{col}: per-source sum should exceed the deduplicated TOTAL"
            )

    @pytest.mark.slow
    def test_caption_reports_both_overlap_counts(self, corpus_table):
        """The extra memberships in each column must appear in the caption,
        so a reader can reconcile the column sum with the TOTAL."""
        md_path = os.path.splitext(CSV_PATH)[0] + ".md"
        if not os.path.exists(md_path):
            pytest.skip(f"{md_path} not built here — run make corpus-tables")
        with open(md_path) as f:
            caption = f.read()

        rows = corpus_table[corpus_table["Source"] != "TOTAL"]
        total = corpus_table[corpus_table["Source"] == "TOTAL"].iloc[0]
        for col in ("Raw", "Refined"):
            extra = int(rows[col].sum() - total[col])
            assert f"{extra:,}" in caption, (
                f"{col}: caption must report the {extra:,} extra memberships"
            )

    @pytest.mark.slow
    def test_caption_labels_the_total_row_as_a_union(self, corpus_table):
        md_path = os.path.splitext(CSV_PATH)[0] + ".md"
        if not os.path.exists(md_path):
            pytest.skip(f"{md_path} not built here — run make corpus-tables")
        with open(md_path) as f:
            caption = f.read()
        assert "TOTAL" in caption and "union" in caption.lower()

    def test_overlap_counts_are_computed_not_hand_typed(self):
        """The caption is built from the frames, so it cannot drift."""
        from export_corpus_table import build_caption

        caption = build_caption(
            raw_multi=748, raw_extra=773, raw_triple=25,
            refined_multi=738, refined_extra=763, refined_triple=24,
        )
        for token in ("748", "773", "738", "763", "25", "24"):
            assert token in caption, token
        assert "{#tbl-quality}" in caption

    def test_caption_counts_triples_per_column(self):
        """Each column's triple-provenance count is its own measurement — one
        figure standing for both populations would be an unmeasured claim."""
        from export_corpus_table import build_caption, membership_overlap

        frame = pd.DataFrame(
            {"from_a": [1, 1, 1], "from_b": [0, 1, 1], "from_c": [0, 0, 1]}
        )
        assert membership_overlap(frame, ["from_a", "from_b", "from_c"]) == (2, 3, 1)

        caption = build_caption(
            raw_multi=9, raw_extra=9, raw_triple=1,
            refined_multi=8, refined_extra=8, refined_triple=7,
        )
        assert "1 and 7 of them carry three" in caption


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


# --- Ticket 0370: the Markdown sibling must survive rendering ---

# A pipe in a source label is not a hypothetical the emitter gets to rule out:
# `SOURCE_META` is edited by hand and its labels are free text. The shape is the
# one that already shipped twice — 0325 in the deposit codebook, 0339 in both
# venue tables — where a raw `|` ends the cell and the renderer drops the
# overflow instead of erroring.
PIPE_SOURCE = "OECD DAC | CRS key documents"
PIPE_TOTAL = "TOTAL | all sources"

_MD_COLUMNS = ["Source", "Raw", "Refined", "Unique",
               "%non-EN", "%DOI", "%Abstract", "%Refs"]


def _summary_row(source: str) -> dict:
    return {
        "Source": source, "Raw": 1200, "Refined": 900, "Unique": 300,
        "%non-EN": "12%", "%DOI": "88%", "%Abstract": "77%", "%Refs": "66%",
    }


# The caption is a paragraph below the table, not a row, so its content cannot
# split a cell — any placeholder does here. Kept out of the rows deliberately:
# these tests are about the row values, and a caption carrying a `|` would only
# muddy which side of the table an assertion is talking about.
_CAPTION = ": Corpus sources. {#tbl-quality}"


def _render(summary: pd.DataFrame, tmp_path) -> str:
    """Run the real emitter, then read its output back through pandoc."""
    from export_corpus_table import _write_md_table

    output = tmp_path / "tab_corpus_sources.md"
    _write_md_table(summary, str(output), _CAPTION)
    return render_qmd(output.read_text(encoding="utf-8"), tmp_path)


@pytest.mark.integration
def test_pipe_bearing_source_keeps_its_eight_cells(tmp_path):
    """A `|` in a source label must not shift the row's numbers one column left.

    Asserted on the rendered page, not on the emitted source: the renderer is
    the only thing that sees the split, and it reports it by silently dropping
    the overflow (ticket 0325).
    """
    require_pandoc()
    summary = pd.DataFrame([_summary_row(PIPE_SOURCE)], columns=_MD_COLUMNS)

    row = row_with(_render(summary, tmp_path), "OECD DAC")

    assert cell_texts(row) == [
        escape(PIPE_SOURCE, quote=False),
        "1,200", "900", "300", "12%", "88%", "77%", "66%",
    ], f"the source label split the row:\n{row}"


@pytest.mark.integration
def test_total_row_stays_bold_around_an_escaped_value(tmp_path):
    """The TOTAL branch wraps its value in `**…**` — escape first, wrap second.

    Wrapping first would put the emphasis markers where the escaper cannot see
    them, and escaping the whole `**value**` string is what a later edit to the
    helper's character set would turn into a literal `\\*\\*`.
    """
    require_pandoc()
    summary = pd.DataFrame([_summary_row(PIPE_TOTAL)], columns=_MD_COLUMNS)

    row = row_with(_render(summary, tmp_path), "TOTAL")

    assert "<strong>" in row, f"the TOTAL row lost its emphasis:\n{row}"
    assert cell_texts(row) == [
        escape(PIPE_TOTAL, quote=False),
        "1,200", "900", "300", "12%", "88%", "77%", "66%",
    ], f"the TOTAL label split the row:\n{row}"


def test_shipped_labels_are_untouched_by_the_escaper(tmp_path):
    """Escaping must be a no-op on every label the corpus build actually emits.

    The fix is worthless if it churns `tab_corpus_sources.md` on the next
    regeneration: a diff on every row would hide the one row that changed for a
    real reason. No `SOURCE_META` label carries an escapable character today,
    so the emitted table must carry no backslash at all.
    """
    from export_corpus_table import SOURCE_META, _write_md_table

    summary = pd.DataFrame(
        [_summary_row(meta["label"]) for meta in SOURCE_META.values()],
        columns=_MD_COLUMNS,
    )
    output = tmp_path / "tab_corpus_sources.md"
    _write_md_table(summary, str(output), _CAPTION)
    emitted = output.read_text(encoding="utf-8")

    assert "\\" not in emitted, (
        "escaping churned a shipped label — regenerating the table would "
        f"rewrite rows that did not change:\n{emitted}"
    )
    for meta in SOURCE_META.values():
        assert f"| {meta['label']} |" in emitted, (
            f"label {meta['label']!r} was rewritten by the escaper"
        )
