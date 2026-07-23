"""Tests for compute_dedup_error_estimates (ticket 0301, R1-12).

Fixture design follows the ticket's Test section: a known WP/published pair,
a DOI collision, and an empty-year generic-title merge — each counter must
pick up exactly its own case.
"""

import os
import sys

import pandas as pd
import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, os.path.join(SCRIPTS_DIR, "analysis"))  # 0257: analysis entry points

from compute_dedup_error_estimates import (
    DEFAULT_THRESHOLDS,
    compute_false_negatives,
    compute_false_positives,
    compute_dedup_error_estimates,
)


def _metric(df, name):
    rows = df.loc[df["metric"] == name, "value"]
    assert len(rows) == 1, f"metric {name} missing or duplicated"
    return rows.iloc[0]


@pytest.fixture
def refined_fixture():
    """Refined-works-like frame with one WP/published pair, one fuzzy pair,
    and unrelated singletons."""
    return pd.DataFrame(
        {
            "title": [
                # WP → journal version pair: same title, same author, years 2 apart
                "Carbon pricing and adaptation finance",
                "Carbon pricing and adaptation finance",
                # Fuzzy near-duplicate pair (Jaccard >= 0.7), same author
                "Measuring climate finance flows to developing countries",
                "Measuring the climate finance flows to developing countries",
                # Unrelated singletons (one shares an author with the pair above)
                "Ocean acidification economics",
                "A totally different subject",
            ],
            "first_author": [
                "Jane Doe",
                "Doe, Jane",  # name-order swap must still match
                "Alice Smith",
                "Smith, Alice",
                "Alice Smith",
                "Bob Jones",
            ],
            "year": [2010, 2012, 2015, 2015, 2020, 2021],
        }
    )


@pytest.fixture
def combined_fixture():
    """Pre-dedup combined-catalog frame exercising both FP counters."""
    return pd.DataFrame(
        {
            "doi": [
                # DOI collision: same DOI, unrelated titles
                "10.1000/xyz",
                "10.1000/xyz",
                # Benign DOI group: subtitle truncation (divergent but overlapping)
                "10.2000/abc",
                "10.2000/abc",
                # No-DOI rows below
                "",
                "",
                "",
                "",
                "",
            ],
            "title": [
                "Green bonds in emerging markets",
                "Fisheries management under uncertainty",
                "Climate risk disclosure",
                "Climate risk disclosure: evidence from banks",
                # Empty-year generic-title merge (3 rows, one group)
                "Climate finance",
                "Climate finance",
                "Climate finance",
                # Title+year author-conflict group
                "Adaptation costs",
                "Adaptation costs",
            ],
            "first_author": [
                "A One",
                "B Two",
                "C Three",
                "C Three",
                "D Four",
                "E Five",
                "F Six",
                "G Seven",
                "H Eight",
            ],
            "year": ["", "", "2019", "2019", "", "", "", "2018", "2018"],
        }
    )


def test_false_negatives(refined_fixture):
    fn = compute_false_negatives(refined_fixture, DEFAULT_THRESHOLDS)
    # Exactly the WP/published pair: same exact title, same author, 0 < gap <= 5
    assert fn["fn_exact_title_pairs"] == 1
    # Candidate families: the exact pair (2 docs) + the fuzzy pair (2 docs)
    assert fn["fn_candidate_family_docs"] == 4


def test_false_negative_year_gap_bound(refined_fixture):
    wide = refined_fixture.copy()
    wide.loc[1, "year"] = 2010 + DEFAULT_THRESHOLDS["year_gap_max"] + 1
    fn = compute_false_negatives(wide, DEFAULT_THRESHOLDS)
    assert fn["fn_exact_title_pairs"] == 0


def test_false_positives(combined_fixture):
    fp = compute_false_positives(combined_fixture, DEFAULT_THRESHOLDS)
    # DOI pass: 2 groups, 4 rows, 2 removals; both groups have divergent
    # titles but only the collision has near-zero token overlap.
    assert fp["fp_doi_removals"] == 2
    assert fp["fp_doi_groups"] == 2
    assert fp["fp_doi_groups_divergent_title"] == 2
    assert fp["fp_doi_groups_near_zero_overlap"] == 1
    # Title+year pass: empty-year group (3 rows) + author-conflict group (2 rows)
    assert fp["fp_titleyear_removals"] == 3
    assert fp["fp_titleyear_groups"] == 2
    # Both merged groups mix distinct authors: the dedicated conflict group
    # AND the empty-year group (three distinct authors merged by the
    # degenerate key) — the counters overlap by design.
    assert fp["fp_titleyear_groups_author_conflict"] == 2
    assert fp["fp_empty_year_groups"] == 1
    assert fp["fp_empty_year_docs_merged"] == 3
    assert fp["fp_empty_year_max_group_size"] == 3


def test_long_format_and_schema(refined_fixture, combined_fixture):
    from schemas import DedupErrorEstimatesSchema

    out = compute_dedup_error_estimates(
        refined_fixture, combined_fixture, DEFAULT_THRESHOLDS
    )
    DedupErrorEstimatesSchema.validate(out)
    assert list(out.columns) == ["metric", "value"]
    assert _metric(out, "n_refined_docs") == len(refined_fixture)
    assert _metric(out, "fn_exact_title_pairs") == 1
    assert _metric(out, "fp_doi_groups_near_zero_overlap") == 1
    assert _metric(out, "fp_empty_year_max_group_size") == 3
