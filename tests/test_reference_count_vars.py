"""Ticket 0277 — reference-count vars traceable to 0285's artifact.

The data paper quotes the per-document reference-count distribution
(R1-13). Numbers must flow from deliverables/_shared/tables/
tab_reference_counts.csv through compute_vars.py into Quarto meta
shortcodes — never hard-coded in prose.
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "scripts", "analysis")
)
from compute_vars import DOC_VARS, reference_count_stats

BASE = os.path.join(os.path.dirname(__file__), "..")
ARTIFACT = os.path.join(
    BASE, "deliverables", "_shared", "tables", "tab_reference_counts.csv"
)
QMD = os.path.join(BASE, "deliverables", "data-paper", "data-paper.qmd")

REFS_KEYS = [
    "refs_doi_docs",
    "refs_zero_n",
    "refs_zero_share_pct",
    "refs_median",
    "refs_mean",
    "refs_p95",
    "refs_max",
]


def _metrics():
    df = pd.read_csv(ARTIFACT)
    return dict(zip(df["metric"], df["value"]))


def test_collector_matches_artifact():
    """reference_count_stats values are formatted from the 0285 artifact."""
    m = _metrics()
    v = {}
    reference_count_stats(v)
    assert v["refs_doi_docs"] == f"{int(m['n_documents_with_doi']):,}"
    assert v["refs_zero_n"] == f"{int(m['n_zero_references']):,}"
    assert v["refs_zero_share_pct"] == f"{100 * m['share_zero_references']:.1f}"
    assert v["refs_median"] == f"{int(m['ref_count_median']):,}"
    assert v["refs_mean"] == f"{m['ref_count_mean']:.1f}"
    assert v["refs_p95"] == f"{int(m['ref_count_p95']):,}"
    assert v["refs_max"] == f"{int(m['ref_count_max']):,}"


def test_refs_keys_registered_for_data_paper():
    """All refs_* variables are declared in DOC_VARS['data-paper']."""
    declared = set(DOC_VARS["data-paper"])
    missing = [k for k in REFS_KEYS if k not in declared]
    assert not missing, f"missing from DOC_VARS['data-paper']: {missing}"


def test_prose_uses_meta_not_hardcoded_numbers():
    """The qmd quotes reference counts via meta shortcodes, never hard-coded."""
    with open(QMD) as f:
        text = f.read()
    # Stale pre-0300 headline must never reappear.
    assert "41.5" not in text
    # Current artifact values must not be hard-coded either.
    m = _metrics()
    for lit in (
        f"{100 * m['share_zero_references']:.1f}",
        f"{int(m['n_zero_references']):,}",
        f"{m['ref_count_mean']:.1f}",
    ):
        assert lit not in text, f"hard-coded number {lit!r} in data-paper.qmd"
    # The distribution is actually reported.
    for key in REFS_KEYS:
        assert f"{{{{< meta {key} >}}}}" in text, f"{key} not quoted in prose"


def test_grobid_stance_is_honest():
    """GROBID is described as implemented at reference-string level, and the
    stale 'not implemented' claim is gone."""
    with open(QMD) as f:
        text = f.read()
    assert "GROBID" in text
    assert "not implemented in the current pipeline" not in text
    assert "corpus_parse_citations_grobid" in text
