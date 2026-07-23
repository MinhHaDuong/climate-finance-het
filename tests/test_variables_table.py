"""Tests for ticket 0279: generated variables-description table for the data paper.

Remark ED-03 (tracker 0274): the data paper must carry a table describing the
variables of climate_finance_corpus.csv, generated from a single declared
contract — not hand-written prose. The contract lives in
scripts/deposit_variables.py; export_deposit.py enforces it at write time, so
the table cannot drift from the shipped CSV.
"""

import os

import pandas as pd
import pytest

from deposit_variables import (
    DEPOSIT_VARIABLES,
    check_columns,
    contract_names,
    render_markdown_table,
    transform,
)
from utils import FROM_COLS, WORKS_COLUMNS

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_PAPER = os.path.join(ROOT, "deliverables", "data-paper", "data-paper.qmd")
SCRIPT = os.path.join(ROOT, "scripts", "figures", "export_variables_table.py")

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
            assert f"`{name}`" in md

    def test_render_has_quarto_label_and_caption(self):
        md = render_markdown_table()
        assert "{#tbl-variables}" in md
        assert md.strip().splitlines()[-1].startswith(":"), \
            "last line must be the Quarto table caption"

    def test_export_script_exists(self):
        assert os.path.isfile(SCRIPT)


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
