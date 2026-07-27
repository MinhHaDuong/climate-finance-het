"""The data paper's verification numbers come from the artifact (ticket 0320).

§2 claimed citation-graph verification "confirmed 99.0% ... (95% CI [97.1%,
99.7%]); the 1% unconfirmed". Those literals were typed from a corpus-v1 run
and survived the v2 rebuild unchanged, while qa_citations_report.json moved to
97.0%, CI [94.4%, 98.4%], 9 unconfirmed — a claimed point estimate outside its
own interval, and a "1%" that was really 3%.

Two things are pinned here: the producer flattens the report faithfully, and
the paragraph carries no bare statistic that could drift again.
"""

import os
import re
import sys

import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, os.path.join(SCRIPTS_DIR, "analysis"))  # 0257: analysis entry points

from compute_citation_verification import compute_citation_verification

DATA_PAPER = os.path.join(
    os.path.dirname(__file__), "..", "deliverables", "data-paper", "data-paper.qmd"
)

REPORT = {
    "accuracy": {
        "sample_n": 300, "tested_n": 300, "confirmed": 291, "not_confirmed": 9,
        "errors": 0, "proportion": 0.97, "ci_lower": 0.943977, "ci_upper": 0.984138,
    },
    "completeness": {
        "sample_n": 300, "total_cr_ref_dois": 6119, "captured": 6016, "missed": 103,
        "proportion": 0.983167, "ci_lower": 0.979627, "ci_upper": 0.986101,
    },
}


@pytest.fixture
def metrics():
    df = compute_citation_verification(REPORT)
    return dict(zip(df["metric"], df["value"]))


def test_proportions_are_rescaled_to_percentages(metrics):
    """The report stores 0-1; the prose writes percent. Getting this wrong
    is silent — 0.97 reads as a plausible '0.97%'."""
    assert metrics["verify_confirmed_pct"] == pytest.approx(97.0)
    assert metrics["complete_captured_pct"] == pytest.approx(98.3167)


def test_confidence_bounds_travel_with_the_estimate(metrics):
    """The interval is the point of the sentence, so it may never be dropped
    or silently rounded into a different interval."""
    assert metrics["verify_ci_lower_pct"] == pytest.approx(94.3977)
    assert metrics["verify_ci_upper_pct"] == pytest.approx(98.4138)
    assert metrics["verify_ci_lower_pct"] < metrics["verify_confirmed_pct"]
    assert metrics["verify_confirmed_pct"] < metrics["verify_ci_upper_pct"]


def test_unconfirmed_share_is_derived_not_assumed(metrics):
    """'the 1% unconfirmed' outlived a 3% measurement because the prose did
    this arithmetic by hand. The artifact does it now."""
    assert metrics["verify_unconfirmed_n"] == 9
    assert metrics["verify_unconfirmed_pct"] == pytest.approx(3.0)
    assert metrics["verify_confirmed_pct"] + metrics["verify_unconfirmed_pct"] == (
        pytest.approx(100.0)
    )


def test_counts_are_consistent_with_the_sample(metrics):
    assert metrics["verify_confirmed_n"] + metrics["verify_unconfirmed_n"] == (
        metrics["verify_tested_n"]
    )
    assert metrics["complete_captured_n"] + metrics["complete_missed_n"] == (
        metrics["complete_total_n"]
    )


def test_missing_accuracy_block_is_an_error_not_a_default():
    """A report without accuracy leaves the paper's claim unsourced. Failing
    loudly beats emitting a zero that renders as '0.0%'."""
    with pytest.raises(KeyError, match="accuracy"):
        compute_citation_verification({"completeness": REPORT["completeness"]})


def test_completeness_is_optional():
    """An accuracy-only run still yields a usable artifact."""
    df = compute_citation_verification({"accuracy": REPORT["accuracy"]})
    m = dict(zip(df["metric"], df["value"]))
    assert "verify_confirmed_pct" in m
    assert "complete_captured_pct" not in m


def test_quality_paragraph_carries_no_hand_typed_statistic():
    """Negative guard, per the project's CI test-polarity rule: pin the defect
    (a bare percentage literal), never a specific positive phrasing.

    The paragraph's numbers must all arrive as {{< meta >}} macros. A literal
    like '99.0%' here is exactly what went stale across a corpus rebuild.
    """
    with open(DATA_PAPER) as fh:
        text = fh.read()

    sentence_start = text.index("Citation graph verification")
    paragraph_end = text.index("\n", sentence_start)
    paragraph = text[sentence_start:paragraph_end]

    # Strip the macros, then the confidence LEVEL ("95% CI"), which is a
    # constant of the method and not a measurement that moves with the corpus.
    without_macros = re.sub(r"\{\{<[^>]*>\}\}", "", paragraph)
    without_level = re.sub(r"\b95\s*%\s*CI", "CI", without_macros)
    literals = re.findall(r"\d+\.?\d*\s*%", without_level)
    assert not literals, (
        f"hand-typed statistic(s) {literals} in the verification sentence — "
        f"every number there must come from tab_citation_verification.csv "
        f"via compute_vars (ticket 0320)"
    )
