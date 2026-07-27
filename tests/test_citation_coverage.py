"""Tests for the periodised citation-coverage metric (ticket 0317).

The data paper's §4 quotes citation coverage per period. The v1.0 prose gave
27% pre-2007 vs 47% post-2015; on corpus v2 the numbers move, and a competing
denominator (works *carrying a DOI* rather than all works) reverses the
apparent gradient. These tests pin the denominator so the prose cannot drift
back onto the wrong one.
"""

import os
import sys

import pandas as pd
import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, os.path.join(SCRIPTS_DIR, "analysis"))  # 0257: analysis entry points

from compute_citation_coverage import compute_citation_coverage


def _works():
    """Six works over three periods, with a deliberate DOI-carriage gradient.

    Pre-2007: 2 works, 1 with a DOI, and that one is covered.
        -> all-works share 1/2 = 50%, DOI-bearing share 1/1 = 100%
    2007-2014: 2 works, 2 with DOIs, 1 covered -> 50% and 50%
    2015-2024: 2 works, 2 with DOIs, 1 covered -> 50% and 50%
    """
    return pd.DataFrame(
        {
            "doi": ["10.1/a", None, "10.1/c", "10.1/d", "10.1/e", "10.1/f"],
            "year": [1998, 2001, 2010, 2012, 2018, 2020],
            "cited_by_count": [80, 0, 10, 0, 60, 0],
        }
    )


def _citations():
    """Edge list: a, c and e appear as citing sources."""
    return pd.DataFrame(
        {
            "source_doi": ["10.1/a", "10.1/a", "10.1/c", "10.1/e"],
            "ref_doi": ["10.9/x", "10.9/y", "10.9/z", "10.9/w"],
        }
    )


@pytest.fixture
def coverage_df():
    return compute_citation_coverage(_works(), _citations(), core_threshold=50)


@pytest.fixture
def metrics(coverage_df):
    return dict(zip(coverage_df["metric"], coverage_df["value"]))


def test_output_is_long_metric_value(coverage_df):
    assert list(coverage_df.columns) == ["metric", "value"]
    assert coverage_df["metric"].is_unique


def test_period_boundaries_are_emitted(metrics):
    """Labels are reconstructable from the CSV alone (floats-only schema)."""
    assert metrics["p1_year_min"] == 1990
    assert metrics["p1_year_max"] == 2006
    assert metrics["p3_year_min"] == 2015
    assert metrics["p3_year_max"] == 2024


def test_all_works_denominator_counts_works_without_a_doi(metrics):
    """The headline share divides by ALL works in the period, not by the
    DOI-bearing subset. A no-DOI work can never be a citing source, and
    hiding it in the denominator is what inverts the gradient."""
    assert metrics["p1_n_works"] == 2
    assert metrics["p1_n_covered"] == 1
    assert metrics["p1_share_covered"] == pytest.approx(50.0)


def test_doi_bearing_denominator_is_reported_separately(metrics):
    """Both denominators ship, so the prose can name the mechanism without
    recomputing anything by hand."""
    assert metrics["p1_n_with_doi"] == 1
    assert metrics["p1_share_covered_of_doi"] == pytest.approx(100.0)
    assert metrics["p1_share_with_doi"] == pytest.approx(50.0)


def test_the_two_denominators_can_disagree_in_direction(metrics):
    """Regression guard for the 0317 misreading: on this fixture the
    all-works share is flat across periods while the DOI-bearing share
    falls. Whichever way real data points, the artifact must expose both."""
    all_works = [metrics[f"p{i}_share_covered"] for i in (1, 2, 3)]
    of_doi = [metrics[f"p{i}_share_covered_of_doi"] for i in (1, 2, 3)]
    assert all_works == pytest.approx([50.0, 50.0, 50.0])
    assert of_doi[0] > of_doi[2]


def test_core_subset_uses_the_configured_threshold(metrics):
    """cited_by_count >= threshold; a, e qualify and both are covered."""
    assert metrics["core_threshold"] == 50
    assert metrics["core_n"] == 2
    assert metrics["core_n_covered"] == 2
    assert metrics["core_share_covered"] == pytest.approx(100.0)


def test_corpus_totals_are_emitted(metrics):
    assert metrics["all_n_works"] == 6
    assert metrics["all_n_covered"] == 3
    assert metrics["all_share_covered"] == pytest.approx(50.0)


def test_works_outside_every_period_are_excluded_from_period_rows():
    """A work dated outside 1990-2024 belongs to no period; it must not be
    silently folded into the nearest one."""
    works = _works()
    works.loc[len(works)] = {"doi": "10.1/z", "year": 2030, "cited_by_count": 0}
    df = compute_citation_coverage(works, _citations(), core_threshold=50)
    m = dict(zip(df["metric"], df["value"]))
    assert m["p3_n_works"] == 2
    assert m["all_n_works"] == 7


def test_missing_year_does_not_crash_and_is_excluded():
    works = _works()
    works.loc[len(works)] = {"doi": "10.1/q", "year": None, "cited_by_count": 0}
    df = compute_citation_coverage(works, _citations(), core_threshold=50)
    m = dict(zip(df["metric"], df["value"]))
    assert sum(m[f"p{i}_n_works"] for i in (1, 2, 3)) == 6


def test_doi_matching_is_normalised():
    """Coverage must survive case and https://doi.org/ prefixes on either
    side of the join."""
    works = pd.DataFrame(
        {
            "doi": ["https://doi.org/10.1/A"],
            "year": [2018],
            "cited_by_count": [0],
        }
    )
    cit = pd.DataFrame({"source_doi": ["10.1/a"], "ref_doi": ["10.9/x"]})
    m = dict(zip(*compute_citation_coverage(works, cit, core_threshold=50).values.T))
    assert m["p3_n_covered"] == 1


def test_a_work_without_a_doi_is_never_counted_as_covered():
    """Contract: no DOI means no coverage, whatever junk is in either column.

    A work with no DOI cannot be matched as a citing source at all — that is
    the whole mechanism behind the coverage gradient the paper reports. Two
    independent guards enforce it (empty keys are stripped from the source
    set, AND the covered mask requires has_doi), which is why mutating either
    one alone leaves the other 10 tests green. This pins the observable
    contract, so losing both is caught even though losing one is not.
    """
    works = pd.DataFrame(
        {
            "doi": [None, "", "  ", "nan", "none"],
            "year": [1998, 2005, 2010, 2018, 2020],
            "cited_by_count": [0, 0, 0, 0, 0],
        }
    )
    # Citation rows whose source_doi degenerates to the same junk forms.
    cit = pd.DataFrame(
        {
            "source_doi": ["", "  ", "nan", "none", "10.1/real"],
            "ref_doi": ["10.9/a"] * 5,
        }
    )
    df = compute_citation_coverage(works, cit, core_threshold=50)
    m = dict(zip(df["metric"], df["value"]))

    assert m["all_n_works"] == 5
    assert m["all_n_with_doi"] == 0
    assert m["all_n_covered"] == 0, (
        "a work with no usable DOI was counted as covered — the empty-key "
        "guard and the has_doi conjunction have both been lost"
    )
    for i in (1, 2, 3):
        assert m[f"p{i}_n_covered"] == 0
