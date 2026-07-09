"""Regression guard for the PDF-content audit's pure matching logic.

The audit (`scripts/qa_pdf_content.py`) flags a bib entry when its local PDF's
title signal does not match the bib `title`. The real audit is author-run and
human-verified against copyright pages; here we only pin the *scoring* so a low
score for a genuine mismatch and a high score for the right work stay stable.

The motivating case: `lepenies2016.pdf` once held *Taste as Experience* under the
key for *The Power of a Single Number* — the audit must score that pair LOW.
"""

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "qa_pdf_content",
    Path(__file__).resolve().parent.parent / "scripts" / "qa_pdf_content.py",
)
audit = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(audit)


def test_identical_title_scores_high():
    score = audit.match_score(
        "The Power of a Single Number: A Political History of GDP",
        "The Power of a Single Number: A Political History of GDP",
        "the power of a single number a political history of gdp columbia",
    )
    assert score > 0.9


def test_lepenies_mismatch_scores_low():
    """The exact defect that triggered ticket 0200 must score low."""
    score = audit.match_score(
        "The Power of a Single Number: A Political History of GDP",
        "Taste as Experience: The Philosophy and Aesthetics of Food",
        "taste as experience the philosophy and aesthetics of food columbia",
    )
    assert score < 0.35


def test_containment_recovers_title_from_noisy_first_page():
    """Title tokens present amid front-matter still score high via containment,
    even when metadata Title is absent."""
    score = audit.match_score(
        "Rule of Experts: Egypt, Techno-Politics, and Modernity",
        "",
        "cover Rule of Experts Egypt Techno-Politics and Modernity Timothy Mitchell",
    )
    assert score > 0.8


def test_no_signal_scores_zero():
    """A scanned PDF (no metadata, no extractable text) scores zero — a flag for
    human eyeball, never grounds for auto-replacement."""
    assert audit.match_score("Some Real Title Here", "", "") == 0.0


def test_stopwords_do_not_inflate_containment():
    """Overlap on function words alone must not pass a genuinely different work."""
    score = audit.match_score(
        "The Economics of the Climate", "", "the of the and a an for to in on"
    )
    assert score < 0.35


def test_normalize_strips_punctuation_and_case():
    assert audit.normalize("The Power: A History!") == "the power a history"
