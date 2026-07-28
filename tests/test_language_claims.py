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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "analysis"))

import compute_vars

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_PAPER = os.path.join(ROOT, "deliverables", "data-paper", "data-paper.qmd")

# Claims of a cross-language capability, as patterns rather than substrings.
#
# The first draft of this guard listed three literal substrings and skipped
# itself whenever any `xling_*` key appeared in the vars file. Both were
# defeated in review: adding `xling_foo: "0"` disarmed it while the forbidden
# claim sat live in the abstract, and "travelled across **the eight**
# languages" walked straight past `"across languages"`. Two lessons, both
# applied here — the escape hatch is gone, and the phrasings are patterns.
#
# There is no automatic lift. Backing the claim with a diagnostic means
# editing this file alongside publishing the measurement, which is a
# deliberate, reviewable act; a stray variable is not.
UNDEMONSTRATED = (
    # cross-lingual, crosslingual, cross linguistic, cross-language.
    # `\b` is load-bearing: without it the optional whitespace lets the pattern
    # straddle a word boundary and fire on the abstract's legitimate "works
    # across linguistic contexts", which is a retrieval claim, not a capability
    # claim.
    r"\bcross[\s\-]?lingu",
    r"\bcross[\s\-]?language",
    # the travel metaphor, with or without an interposed count
    r"travell?ed?\s+across",
    # comparison framed as a capability the corpus does not demonstrate
    r"compar\w+[^.]{0,60}(?:across|between)\s+(?:the\s+)?(?:\S+\s+){0,3}languages",
    r"compar\w+\s+(?:the\s+)?languages\b",
    r"(?:support|permit|enabl|allow)\w*[^.]{0,60}"
    r"(?:across|between)\s+(?:the\s+)?(?:\S+\s+){0,3}languages",
)


def read(path):
    with open(path) as fh:
        return fh.read()


def _count(value: str) -> int:
    """A count as compute_vars formats it: `f"{n:,}"` above 999."""
    return int(value.replace(",", ""))


def _hits(text: str) -> list[str]:
    """Forbidden patterns that match, reported by the text they matched."""
    found = []
    for pattern in UNDEMONSTRATED:
        for match in re.finditer(pattern, text, flags=re.I):
            found.append(match.group(0))
    return sorted(set(found))


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

    total = _count(v["corpus_total"])
    english = round(float(v["lang_english_pct"]) / 100 * total)
    assert english + _count(v["lang_non_english_n"]) + _count(
        v["lang_unclassified_n"]) == total


def test_non_english_layer_is_not_total_minus_english(monkeypatch):
    """The originating defect, replayed.

    With unclassified works present, total-minus-English overstates the
    non-English layer. A rewrite that reintroduced the shortcut would pass
    every count-formatting check and fail here.
    """
    v = _corpus_stats(["en"] * 6 + ["fr", "pt", "es"] + [None] * 4, monkeypatch)

    total = _count(v["corpus_total"])
    english = round(float(v["lang_english_pct"]) / 100 * total)
    assert _count(v["lang_non_english_n"]) < total - english


def test_unclassified_var_registered_for_the_data_paper():
    assert "lang_unclassified_n" in compute_vars.DOC_VARS["data-paper"]


def test_paper_reports_the_unclassified_layer_beside_the_non_english_one():
    """Reporting one without the other is what let the two be summed."""
    text = read(DATA_PAPER)
    assert "{{< meta lang_non_english_n >}}" in text
    assert "{{< meta lang_unclassified_n >}}" in text


# --- 2. No claim the language table does not support ---

def _abstract_and_conclusion():
    """The two places a reader takes the paper's claims from."""
    text = read(DATA_PAPER)
    abstract = text[text.index("abstract: |"):text.index("keywords: |")]
    conclusion = text[text.index("## 5. Concluding Remarks"):
                      text.index("## Data and Code Availability")]
    return abstract + conclusion


def test_abstract_and_conclusion_claim_no_cross_language_capability():
    """The two places a reader takes the paper's claims from, guarded hardest.

    The defensible claim is multilingual *retrieval* --- an eight-language
    keyword taxonomy, which the corpus did run. A cross-language capability is
    a different assertion, and nothing in the paper measures one.
    """
    found = _hits(_abstract_and_conclusion())

    assert not found, (
        f"the Abstract or Conclusion claims {found}, which @tbl-languages does "
        f"not demonstrate: the corpus indexes only the English version of the "
        f"multi-language UNFCCC and OECD documents and reports no retrieval "
        f"evaluation by language (ticket 0338). Calibrate the wording to "
        f"multilingual retrieval. If a diagnostic now backs the claim, publish "
        f"its measurement and retire the matching pattern here in the same "
        f"change --- deliberately, so a reviewer sees it."
    )


def test_guard_catches_every_wording_it_was_written_against():
    """Red-test the guard against the originating text and its near misses.

    A guard shaped around only the wording already fixed is not a guard. Each
    case below defeated an earlier draft: the first three were live in the
    paper, the rest are one-word edits away from them --- review reproduced the
    fourth ("travelled across **the eight** languages") against a
    literal-substring version and it passed 7/7.
    """
    live = [
        "pre-computed multilingual embeddings to support cross-lingual analysis",
        "a single, cross-lingual bibliographic object",
        "permits comparing how the category travelled across languages",
    ]
    near_misses = [
        "comparing how the category travelled across the eight languages",
        "supports crosslingual retrieval",
        "enables cross-language comparison",
        "permits comparison between the corpus languages",
        "designed to compare languages",
    ]
    for text in live + near_misses:
        assert _hits(text), f"the guard does not catch {text!r}"


def test_guard_passes_the_limitation_statements_it_must_not_block():
    """The other half of the red-test: honest limitation prose stays legal.

    A guard that fires on the paper's own concessions would push the author to
    delete the concession rather than the claim --- the opposite of the point.
    """
    for text in [
        "Non-English coverage remains limited.",
        "Coverage at that level supports case studies rather than balanced "
        "comparison; we report no retrieval evaluation by language.",
        "core terms in eight languages",
        "its eight-language retrieval adds a non-English layer",
        # the word-boundary case: "across linguistic" is not "cross-lingual"
        "used to capture relevant works across linguistic contexts",
    ]:
        assert not _hits(text), f"the guard wrongly fires on {text!r}"


def test_no_undemonstrated_claim_anywhere_in_the_body():
    """§1 sells the reuse cases; it may not sell one the corpus cannot serve.

    Scoped wider than the two sections above because the Introduction's list of
    reuse cases is read as a claim too, and the phrase that seeded this ticket
    ("cross-lingual studies") sat there as well as in the Abstract.
    """
    text = read(DATA_PAPER)
    body = text[text.index("## 1. Introduction"):text.index("## References")]
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)

    found = _hits(body)

    assert not found, (
        f"the body claims {found} without a diagnostic behind it (ticket 0338)"
    )
