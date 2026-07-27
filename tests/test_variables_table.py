"""Tests for ticket 0279: generated variables-description table for the data paper.

Remark ED-03 (tracker 0274): the data paper must carry a table describing the
variables of climate_finance_corpus.csv, generated from a single declared
contract — not hand-written prose. The contract lives in
scripts/_deposit_variables.py; export_deposit.py enforces it at write time, so
the table cannot drift from the shipped CSV.
"""

import os
import re

import pandas as pd
import pytest
from _deposit_variables import (
    DEPOSIT_VARIABLES,
    GROUPS,
    check_columns,
    compute_missingness,
    contract_names,
    describe,
    latex_inline,
    render_codebook,
    render_markdown_table,
    transform,
)
from utils import FROM_COLS, WORKS_COLUMNS

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_PAPER = os.path.join(ROOT, "deliverables", "data-paper", "data-paper.qmd")
SCRIPT = os.path.join(ROOT, "scripts", "figures", "export_variables_table.py")

# The reconstruction recipe the data paper prints twice: once in §3 prose, once
# in the variables table. Ticket 0325 — LaTeX ate the tilde in the table copy,
# publishing the complement of the advertised subset.
RECIPE = "df[~df['is_flagged'] | df['is_protected']]"

# extended_works.csv column layout, mirroring the pipeline: WORKS_COLUMNS +
# provenance flags + carry columns (catalog_merge), abstract_status
# (enrich_join), doi_norm + flag columns + annotations + protection + action
# (corpus_filter --extend), in_v1.
EXTENDED_COLUMNS = (
    WORKS_COLUMNS
    + FROM_COLS
    + ["abstract_provenance", "keywords_provenance", "source_count"]
    + ["abstract_status", "doi_norm"]
    + [
        "missing_metadata",
        "no_abstract_irrelevant",
        "title_blacklist",
        "citation_isolated_old",
        "semantic_outlier",
        "semantic_outlier_dist",
        "llm_irrelevant",
        "near_duplicate_group",
        "protected",
        "protect_reason",
        "action",
        "in_v1",
    ]
)


@pytest.fixture()
def extended_df():
    row = {c: "" for c in EXTENDED_COLUMNS}
    row.update({
        "source": "openalex", "source_id": "W1", "doi": "10.1/x",
        "title": "T", "year": "2010", "cited_by_count": "3",
        "abstract": "A long abstract",
    })
    for c in FROM_COLS:
        row[c] = 0
    row["from_openalex"] = 1
    for c in ["missing_metadata", "no_abstract_irrelevant", "title_blacklist",
              "citation_isolated_old", "semantic_outlier", "llm_irrelevant",
              "protected", "in_v1"]:
        row[c] = False
    return pd.DataFrame([row])


class TestContract:
    def test_contract_nonempty_rows_well_formed(self):
        assert len(DEPOSIT_VARIABLES) > 20
        for var in DEPOSIT_VARIABLES:
            assert var.name and var.type and var.description and var.source

    def test_v2_provenance_columns_documented(self):
        names = contract_names()
        for col in ["from_unfccc", "from_oecd",
                    "abstract_provenance", "keywords_provenance"]:
            assert col in names, f"corpus-v2 column {col} missing from contract"

    def test_abstract_status_documents_reconstructed(self):
        var = {v.name: v for v in DEPOSIT_VARIABLES}["abstract_status"]
        assert "reconstructed" in var.description

    def test_abstract_not_in_contract(self):
        assert "abstract" not in contract_names(), \
            "abstract is dropped from the deposit (redistribution restrictions)"

    def test_check_columns_accepts_contract(self):
        assert check_columns(contract_names()) == []

    def test_check_columns_flags_undocumented_column(self):
        errors = check_columns(contract_names() + ["mystery_col"])
        assert any("mystery_col" in e for e in errors)

    def test_check_columns_flags_missing_required(self):
        cols = [c for c in contract_names() if c != "doi"]
        errors = check_columns(cols)
        assert any("doi" in e for e in errors)

    def test_optional_columns_may_be_absent(self):
        optional = [v.name for v in DEPOSIT_VARIABLES if not v.required]
        cols = [c for c in contract_names() if c not in optional]
        assert check_columns(cols) == []


class TestDataDictionary:
    """Ticket 0287: formal data dictionary — group, allowed values, missingness."""

    def test_four_groups_declared_in_order(self):
        assert GROUPS == [
            "Record identity",
            "Bibliographic metadata",
            "Provenance flags",
            "Curation metadata",
        ]

    def test_every_variable_has_a_declared_group(self):
        for v in DEPOSIT_VARIABLES:
            assert v.group in GROUPS, f"{v.name}: group {v.group!r} not in GROUPS"

    def test_groups_are_contiguous_in_contract_order(self):
        seen = [v.group for v in DEPOSIT_VARIABLES]
        order = [g for i, g in enumerate(seen) if i == 0 or g != seen[i - 1]]
        assert order == [g for g in GROUPS if g in seen], \
            "contract order must follow the four logical groups without interleaving"

    def test_enumerated_columns_declare_allowed_values(self):
        by_name = {v.name: v for v in DEPOSIT_VARIABLES}
        assert "original" in by_name["abstract_status"].allowed_values
        assert "curated" in by_name["abstract_provenance"].allowed_values
        assert "extracted" in by_name["keywords_provenance"].allowed_values
        assert "openalex" in by_name["source"].allowed_values
        for v in DEPOSIT_VARIABLES:
            if v.type.startswith("boolean"):
                assert v.allowed_values, f"boolean {v.name} needs allowed_values"

    def test_compute_missingness_counts_nan_and_empty(self):
        df = pd.DataFrame({
            "doi": ["10.1/x", None, ""],
            "title": ["a", "b", "c"],
            "not_in_contract": [1, 2, 3],
        })
        miss = compute_missingness(df)
        assert miss["doi"] == pytest.approx(2 / 3)
        assert miss["title"] == 0.0
        assert "not_in_contract" not in miss

    def test_render_codebook_grouped_and_complete(self):
        miss = {"doi": 0.123, "title": 0.0}
        md = render_codebook(miss, n_rows=42)
        for g in GROUPS:
            assert f"## {g}" in md
        for name in contract_names():
            assert f"`{name}`" in md
        assert "12.3%" in md and "42" in md

    def test_render_codebook_marks_absent_optional_columns(self):
        md = render_codebook({"doi": 0.0}, n_rows=1)
        assert "n/a" in md, "columns absent from the measured build show n/a"

    def test_variables_table_names_groups_in_caption(self):
        # Groups moved from a column to caption-only naming, with
        # \midrule separators (author decision 2026-07-24).
        md = render_markdown_table()
        assert "record identity" in md
        assert md.count("\\midrule") >= 4


class TestDepositTransformMatchesContract:
    def test_transform_output_covered_by_contract(self, extended_df):
        out = transform(extended_df)
        assert check_columns(list(out.columns)) == [], \
            "export_deposit output must satisfy the variables contract"

    def test_transform_produces_all_required(self, extended_df):
        out = transform(extended_df)
        required = [v.name for v in DEPOSIT_VARIABLES if v.required]
        missing = [c for c in required if c not in out.columns]
        assert not missing, f"required contract columns absent: {missing}"


class TestMarkdownTable:
    def test_render_contains_every_variable(self):
        md = render_markdown_table()
        for name in contract_names():
            assert name.replace("_", "\\_") in md

    def test_render_has_quarto_label_and_caption(self):
        md = render_markdown_table()
        assert "{#tbl-variables}" in md
        assert md.strip().splitlines()[-1] == ":::", \
            "table is a crossref div; caption is its closing paragraph"

    def test_export_script_exists(self):
        assert os.path.isfile(SCRIPT)


def latex_block(md: str) -> str:
    """The raw-LaTeX payload of the rendered table div."""
    body = md.split("```{=latex}", 1)[1]
    return body.split("```", 1)[0]


def plain_text(cell: str) -> str:
    """Recover the source text from an emitted LaTeX cell.

    Round-tripping is what keeps the assertions below non-tautological: they
    compare recovered text against the contract's own strings, never against a
    second copy of the escaping table.
    """
    for seq, char in [
        (r"\textbackslash{}", "\\"), (r"\textasciitilde{}", "~"),
        (r"\textasciicircum{}", "^"), (r"\textbar{}", "|"),
        (r"\textless{}", "<"), (r"\textgreater{}", ">"),
        (r"\textquotesingle{}", "'"), (r"\ldots{}", "..."),
        (r"\&", "&"), (r"\%", "%"), (r"\#", "#"), (r"\_", "_"),
        (r"\$", "$"), (r"\{", "{"), (r"\}", "}"),
    ]:
        cell = cell.replace(seq, char)
    # Unescaping consumed every brace an escape sequence introduced, so what
    # remains inside a code span is brace-free text.
    return re.sub(r"\\texttt\{([^}]*)\}", r"\1", cell)


def table_rows(md: str) -> dict[str, tuple[str, str]]:
    """{variable: (type cell, description cell)} from the emitted LaTeX."""
    rows = {}
    for line in latex_block(md).splitlines():
        if not line.startswith(r"\texttt{"):
            continue
        cells = line.rsplit(r" \\", 1)[0].split(" & ")
        rows[plain_text(cells[0])] = (cells[1], cells[2])
    return rows


class TestLatexEscaping:
    """Ticket 0325: the emitter writes raw LaTeX, so it owns the escaping.

    `~` is a non-breaking space and a backtick is an opening quote in LaTeX;
    both passed through unescaped, which turned the published reconstruction
    recipe into its own complement.
    """

    def test_recipe_is_declared_once_and_reaches_both_copies(self):
        """§3 prose and the contract carry the same expression, character for
        character — the precondition for the rendered copies agreeing."""
        with open(DATA_PAPER) as f:
            paper = f.read()
        assert f"`{RECIPE}`" in paper, "data-paper §3 no longer prints this recipe"
        by_name = {v.name: v for v in DEPOSIT_VARIABLES}
        assert f"`{RECIPE}`" in by_name["is_flagged"].description

    def test_recipe_survives_latex_escaping(self):
        """The tilde reaches the table as a tilde, not a non-breaking space."""
        _, desc = table_rows(render_markdown_table())["is_flagged"]
        assert RECIPE in plain_text(desc), \
            f"recipe corrupted by the LaTeX emitter:\n{desc}"

    def test_every_description_survives_unaltered(self):
        """Exit criterion: no description loses or gains a character in transit."""
        rows = table_rows(render_markdown_table())
        for v in DEPOSIT_VARIABLES:
            type_cell, desc_cell = rows[v.name]
            assert plain_text(type_cell) == v.type
            assert plain_text(desc_cell) == describe(v).replace("`", "")

    def test_no_live_special_reaches_the_pdf(self):
        """A bare `~` or backtick in raw LaTeX is markup, not a character."""
        block = latex_block(render_markdown_table())
        assert "`" not in block, "a backtick in raw LaTeX renders as an opening quote"
        assert not re.search(r"(?<!\\text)~", block.replace(r"\textasciitilde{}", "")), \
            "a bare tilde in raw LaTeX is a non-breaking space"

    def test_code_spans_set_as_code(self):
        block = latex_block(render_markdown_table())
        assert r"\texttt{original}" in block, \
            "abstract_status enumerates code literals; they must set as code"

    def test_unbalanced_backtick_is_a_build_error(self):
        """A malformed contract description fails loudly, not silently."""
        with pytest.raises(ValueError, match="backtick"):
            latex_inline("a `dangling span")


class TestCodebookEscaping:
    """The codebook is a Markdown pipe table; `|` in a cell splits the cell.

    Same defect class as the LaTeX one — a delimiter in payload text — in the
    other markup language the contract renders into. The shipped codebook cut
    the recipe in half at the `|`.
    """

    def test_every_row_has_exactly_five_cells(self):
        md = render_codebook({"doi": 0.0}, n_rows=1)
        for line in md.splitlines():
            if not line.startswith("|"):
                continue
            cells = re.split(r"(?<!\\)\|", line)
            assert len(cells) == 7, f"row splits into the wrong cell count: {line}"

    def test_recipe_survives_the_pipe_table(self):
        md = render_codebook({}, n_rows=1)
        row = next(ln for ln in md.splitlines() if ln.startswith("| `is_flagged`"))
        assert row.replace("\\|", "|").count(RECIPE) == 1, \
            f"recipe corrupted in the codebook:\n{row}"


class TestDataPaperIntegration:
    def test_data_paper_includes_table(self):
        with open(DATA_PAPER) as f:
            text = f.read()
        assert "tables/tab_variables.md" in text
        assert "@tbl-variables" in text, \
            "data-paper.qmd must reference the variables table in the text"

    def test_makefile_target_exists(self):
        with open(os.path.join(ROOT, "Makefile")) as f:
            mk = f.read()
        assert "deliverables/_shared/tables/tab_variables.md:" in mk


@pytest.mark.slow
class TestAgainstShippedCorpus:
    """Drift check against the real deposit CSV, when present (padme)."""

    def test_shipped_csv_matches_contract(self):
        path = os.path.join(ROOT, "data", "catalogs", "extended_works.csv")
        if not os.path.isfile(path):
            pytest.skip("extended_works.csv not available on this machine")
        df = pd.read_csv(path, nrows=5, low_memory=False)
        errors = check_columns(list(transform(df).columns))
        assert errors == [], f"contract drift vs pipeline output: {errors}"
