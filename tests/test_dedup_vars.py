"""Dedup vars for the data paper trace to pipeline artifacts (ticket 0276).

The paper quotes per-procedure removal counts (ticket 0284's catalog_merge
run report) and error estimates (ticket 0301's tab_dedup_error_estimates.csv)
through {{< meta >}} shortcodes only — never as hand-typed numbers. These
tests pin the collector's artifact-to-variable mapping and the prose's use of
the shortcodes.
"""

import json
import os
import sys
import warnings

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "analysis"))

import compute_vars

QMD = os.path.join(
    os.path.dirname(__file__), "..", "deliverables", "data-paper", "data-paper.qmd"
)


@pytest.fixture
def artifact_dirs(tmp_path, monkeypatch):
    """Fake catalogs (run report) and tables (error estimates) directories."""
    catalogs = tmp_path / "catalogs"
    (catalogs / "run_reports").mkdir(parents=True)
    report = {
        "script": "catalog_merge",
        "run_id": "test",
        "records_total": 43906,
        "doi_duplicates_removed": 833,
        "title_year_duplicates_removed": 154,
        "dropped_empty_title": 3,
        "records_unified": 42916,
    }
    with open(catalogs / "run_reports" / "catalog_merge__test.json", "w") as f:
        json.dump(report, f)

    tables = tmp_path / "tables"
    tables.mkdir()
    pd.DataFrame(
        {
            "metric": [
                "fn_exact_title_pairs",
                "fn_exact_title_pairs_share",
                "fn_candidate_family_docs",
                "fn_candidate_family_docs_share",
                "fp_doi_groups_near_zero_overlap",
                "fp_titleyear_groups_author_conflict",
                "fp_empty_year_groups",
                "fp_empty_year_docs_merged",
            ],
            "value": [329.0, 0.0106, 1064.0, 0.0343, 38.0, 48.0, 7.0, 18.0],
        }
    ).to_csv(tables / "tab_dedup_error_estimates.csv", index=False)

    monkeypatch.setattr(compute_vars, "CATALOGS_DIR", str(catalogs))
    monkeypatch.setattr(compute_vars, "TABLES_DIR", str(tables))
    return catalogs, tables


def test_dedup_stats_maps_artifacts_to_vars(artifact_dirs):
    v = {}
    compute_vars.dedup_stats(v)
    assert v["dedup_doi_removed"] == "833"
    assert v["dedup_titleyear_removed"] == "154"
    assert v["dedup_fn_pairs"] == "329"
    assert v["dedup_fn_pairs_pct"] == "1.1"
    assert v["dedup_fn_upper_docs"] == "1,064"
    assert v["dedup_fn_upper_pct"] == "3.4"
    assert v["dedup_fp_doi_collision_groups"] == "38"
    assert v["dedup_fp_empty_year_groups"] == "7"
    assert v["dedup_fp_empty_year_docs"] == "18"


def test_dedup_stats_warns_when_artifacts_absent(tmp_path, monkeypatch):
    (tmp_path / "run_reports").mkdir()
    monkeypatch.setattr(compute_vars, "CATALOGS_DIR", str(tmp_path))
    monkeypatch.setattr(compute_vars, "TABLES_DIR", str(tmp_path))
    v = {}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        compute_vars.dedup_stats(v)
    assert v == {}
    assert len(caught) == 2


def test_dedup_vars_registered_for_data_paper():
    for key in (
        "dedup_doi_removed",
        "dedup_titleyear_removed",
        "dedup_fn_pairs",
        "dedup_fn_upper_docs",
        "dedup_fp_doi_collision_groups",
    ):
        assert key in compute_vars.DOC_VARS["data-paper"], key


def test_paper_quotes_counts_via_shortcodes_not_literals():
    with open(QMD) as f:
        text = f.read()
    assert "{{< meta dedup_doi_removed >}}" in text
    assert "{{< meta dedup_titleyear_removed >}}" in text
    assert "{{< meta dedup_fn_pairs >}}" in text
    # No hand-curated dedup counts in the prose (invariant, ticket 0276).
    for literal in ("833", "154", "329", "1,064"):
        assert literal not in text, f"hard-coded dedup count {literal} in data-paper.qmd"
