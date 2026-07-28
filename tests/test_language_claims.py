"""The data paper's multilingual claims stay inside what @tbl-languages shows.

Ticket 0338, raised by all four external reviewers of the 2026-07-27 panel.
Two defects, one root: the paper's multilingual framing ran ahead of its
language table.

1. *The denominator slip.* "the non-English layer counts 3,381 works" was
   total minus English, silently folding in the works whose language could not
   be classified. The classified layer was 2,023 at the time --- the headline
   multilingual quantity was inflated by two thirds. The count is a variable
   now, but a variable computed as total-minus-English would reproduce the same
   error silently, so the partition is pinned here rather than the value.

2. *The claim gap.* The Abstract and Conclusion advertised "cross-lingual
   analysis" and "comparing how the category travelled across languages". The
   corpus indexes only the English version of the multi-language UNFCCC and
   OECD documents, grey literature is 0% non-English, and no retrieval
   evaluation by language is reported anywhere --- nothing in the paper
   demonstrates either. "Multilingual retrieval" is what the table supports.

Both guards are negative, per the project's CI test-polarity rule: they pin the
defect, never a positive phrasing that a legitimate rewrite would break.
"""

import os
import re
import sys

import pandas as pd
import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "analysis"))

import compute_vars

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_PAPER = os.path.join(ROOT, "deliverables", "data-paper", "data-paper.qmd")
VARS = os.path.join(ROOT, "deliverables", "data-paper", "data-paper-vars.yml")

# A cross-lingual diagnostic, if one is ever run, publishes its result under
# this prefix. Its presence is what lifts the claim guard below: the paper may
# say "cross-lingual" exactly when a measurement backs the word.
DIAGNOSTIC_PREFIX = "xling_"

# Wordings that assert a cross-language capability rather than a multilingual
# harvest. Lexically stable: each reads the same in any draft.
UNDEMONSTRATED = (
    "cross-lingual",
    "cross-linguistic",
    "across languages",
)


def read(path):
    with open(path) as fh:
        return fh.read()


def _corpus_stats(languages, monkeypatch):
    """Run the language block of corpus_stats over a synthetic corpus."""
    df = pd.DataFrame({"language": languages})
    monkeypatch.setattr(compute_vars, "load_refined_works", lambda: df)
    v = {}
    compute_vars.corpus_stats(v)
    return v


# --- 1. The three language buckets partition the corpus ---

def test_language_buckets_partition_the_corpus(monkeypatch):
    """English + classified non-English + unclassified == total, exactly.

    The reviewer's arithmetic, run forward. Publishing the unclassified count
    as its own variable is what makes total-minus-English unavailable as a
    shortcut: a reader who wants the multilingual quantity finds it named.
    """
    languages = ["en"] * 6 + ["fr", "pt", "es"] + [None, "arz"]

    v = _corpus_stats(languages, monkeypatch)

    assert v["corpus_total"] == "11"
    assert v["lang_non_english_n"] == "3"
    assert v["lang_unclassified_n"] == "2"
    assert v["lang_english_pct"] == "54.5"

    english = round(float(v["lang_english_pct"]) / 100 * 11)
    total = int(v["corpus_total"].replace(",", ""))
    assert english + int(v["lang_non_english_n"]) + int(v["lang_unclassified_n"]) == total


def test_non_english_layer_is_not_total_minus_english(monkeypatch):
    """The originating defect, replayed.

    With unclassified works present, total-minus-English overstates the
    non-English layer. A rewrite that reintroduced the shortcut would pass
    every count-formatting check and fail here.
    """
    v = _corpus_stats(["en"] * 6 + ["fr", "pt", "es"] + [None] * 4, monkeypatch)

    total = int(v["corpus_total"])
    english = round(float(v["lang_english_pct"]) / 100 * total)
    assert int(v["lang_non_english_n"]) < total - english


def test_unclassified_var_registered_for_the_data_paper():
    assert "lang_unclassified_n" in compute_vars.DOC_VARS["data-paper"]


def test_paper_reports_the_unclassified_layer_beside_the_non_english_one():
    """Reporting one without the other is what let the two be summed."""
    text = read(DATA_PAPER)
    assert "{{< meta lang_non_english_n >}}" in text
    assert "{{< meta lang_unclassified_n >}}" in text


# --- 2. No claim the language table does not support ---

def _diagnostic_vars():
    with open(VARS) as fh:
        declared = yaml.safe_load(fh) or {}
    return [k for k in declared if k.startswith(DIAGNOSTIC_PREFIX)]


def _abstract_and_conclusion():
    """The two places a reader takes the paper's claims from."""
    text = read(DATA_PAPER)
    abstract = text[text.index("abstract: |"):text.index("keywords: |")]
    conclusion = text[text.index("## 5. Concluding Remarks"):
                      text.index("## Data and Code Availability")]
    return abstract + conclusion


def test_abstract_and_conclusion_claim_no_cross_language_capability():
    """Negative guard on the claim, conditional on the evidence.

    The forbidden wordings become available the moment a cross-lingual
    diagnostic publishes a `xling_*` variable --- the guard asks for evidence,
    not for silence. Until then the defensible claim is multilingual
    *retrieval*: an eight-language keyword taxonomy, which the corpus did run.
    """
    if _diagnostic_vars():
        pytest.skip("a cross-lingual diagnostic backs the claim")

    text = _abstract_and_conclusion().lower()
    found = [phrase for phrase in UNDEMONSTRATED if phrase in text]

    assert not found, (
        f"the Abstract or Conclusion claims {found}, which @tbl-languages does "
        f"not demonstrate: the corpus indexes only the English version of the "
        f"multi-language UNFCCC and OECD documents and reports no retrieval "
        f"evaluation by language (ticket 0338). Either calibrate the wording "
        f"to multilingual retrieval, or run a diagnostic and publish it as a "
        f"`{DIAGNOSTIC_PREFIX}*` variable."
    )


def test_guard_would_catch_the_wording_it_was_written_against():
    """Red-test the guard: the phrases it forbids are the ones that were there.

    Without this, a rename of any forbidden phrase would silently empty the
    guard and it would still pass.
    """
    original = (
        "pre-computed multilingual embeddings to support cross-lingual "
        "analysis ... permits comparing how the category travelled across "
        "languages"
    )
    assert [p for p in UNDEMONSTRATED if p in original] == [
        "cross-lingual", "across languages",
    ]


def test_no_undemonstrated_claim_anywhere_in_the_body():
    """§1 sells the reuse cases; it may not sell one the corpus cannot serve.

    Scoped wider than the two sections above because the Introduction's list of
    reuse cases is read as a claim too, and the phrase that seeded this ticket
    ("cross-lingual studies") sat there as well as in the Abstract.
    """
    if _diagnostic_vars():
        pytest.skip("a cross-lingual diagnostic backs the claim")

    text = read(DATA_PAPER)
    body = text[text.index("## 1. Introduction"):text.index("## References")]
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)

    found = sorted({phrase for phrase in UNDEMONSTRATED if phrase in body.lower()})

    assert not found, (
        f"the body claims {found} without a diagnostic behind it (ticket 0338)"
    )
