"""The data paper's AUC = 0.818 claim recomputes from what the deposit ships.

Ticket 0372. The per-work human labels behind the reranker validation were
destroyed by their own collection sheet, so the shipped evidence is the
stratified sample plus the per-quintile human-relevance rates recorded at
commit 5d8224b3. These tests hold the chain together: the deposited table
matches the sample it summarises, the AUC the paper quotes recomputes from
the table alone, and every evidence file the prose names is actually staged
by the archive build — so the number can never again point at an artifact
that cannot support it.
"""

import os
import sys

import pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))

from figures.export_reranker_validation import (
    HUMAN_RELEVANT_RATE,
    build_table,
    implied_auc,
)

QMD = os.path.join(REPO, "deliverables", "data-paper", "data-paper.qmd")
TABLE = os.path.join(
    REPO, "deliverables", "_shared", "tables", "tab_reranker_validation.csv"
)
SAMPLE = os.path.join(REPO, "docs", "reranker_hitl_stratified.csv")
BUILD_SCRIPT = os.path.join(REPO, "build", "build_datapaper_archive.sh")

QUOTED_AUC = 0.818
EVIDENCE_FILES = [
    "tab_reranker_validation.csv",
    "reranker_hitl_stratified.csv",
    "reranker_hitl_review.csv",
    "reranker_calibration.csv",
]


def _read(path):
    with open(path) as f:
        return f.read()


def test_prose_quotes_the_recomputable_auc():
    """The quoted AUC recomputes from the shipped per-quintile table."""
    table = pd.read_csv(TABLE)
    rates = dict(zip(table["stratum"], table["human_relevant_rate"]))
    ns = dict(zip(table["stratum"], table["n"]))
    auc = implied_auc(rates, ns)
    assert abs(auc - QUOTED_AUC) <= 0.001, (
        f"shipped table implies AUC {auc:.4f}; the paper quotes {QUOTED_AUC} — "
        "the deposited evidence no longer supports the prose"
    )
    assert f"AUC = {QUOTED_AUC}" in _read(QMD), (
        f"data-paper.qmd no longer quotes AUC = {QUOTED_AUC}; update this "
        "test's QUOTED_AUC together with the prose, never separately"
    )


def test_deposited_table_matches_the_stratified_sample():
    """The table's composition columns are measured from the sample sheet."""
    committed = pd.read_csv(TABLE)
    rebuilt = build_table(pd.read_csv(SAMPLE))
    pd.testing.assert_frame_equal(
        committed, rebuilt, check_exact=False, atol=1e-9
    )


def test_rates_match_the_recorded_protocol():
    """The table carries the 5d8224b3 rates, not silently substituted ones."""
    table = pd.read_csv(TABLE)
    rates = dict(zip(table["stratum"], table["human_relevant_rate"]))
    assert rates == HUMAN_RELEVANT_RATE, (
        "deposited rates diverge from the recorded protocol (tech report "
        "§3.1 at 5d8224b3) — changing them requires a new validation, not "
        "an edit (ticket 0372 invariant)"
    )


def test_prose_names_only_evidence_the_build_stages():
    """Every evidence file §2.3 names is staged into data/products/."""
    qmd = _read(QMD)
    sh = _read(BUILD_SCRIPT)
    staged = [
        ln for ln in sh.splitlines() if "data/products" in ln and "cp " in ln
    ]
    for name in EVIDENCE_FILES:
        assert f"`{name}`" in qmd, (
            f"data-paper.qmd §2.3 no longer names {name}; the evidence "
            "sentence and this list must move together"
        )
        assert any(name in ln for ln in staged), (
            f"{name} is named as deposit evidence but no build line stages "
            "it into data/products/ — the paper promises a file the archive "
            "drops (the original 0372 defect)"
        )
