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

# Every deliverable that describes this corpus's embedding model. The
# shared-semantic-space guard below runs over all of them; the capability
# patterns above stay scoped to the data paper, for the reason given there.
MULTILAYER = os.path.join(ROOT, "deliverables", "multilayer", "multilayer-detection.qmd")
MULTILAYER_TECHREP = os.path.join(
    ROOT, "deliverables", "multilayer", "multilayer-detection-techrep.qmd")
EMBEDDING_DOCS = (DATA_PAPER, MULTILAYER, MULTILAYER_TECHREP)

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

# Every separator that renders as a hyphen. A copy-paste from a word processor
# or a reference manager carries U+2010/2011/2013 or a soft hyphen, each of
# which reads as "cross-lingual" on the page and slipped past a plain `\-`
# (round-2 review).
_HYPHENS = r"[\s\-­‐‑‒–—―]"

UNDEMONSTRATED = (
    # cross-lingual, crosslingual, cross linguistic, cross-language.
    # `\b` is load-bearing: without it the optional whitespace lets the pattern
    # straddle a word boundary and fire on the abstract's legitimate "works
    # across linguistic contexts", which is a retrieval claim, not a capability
    # claim.
    rf"\bcross{_HYPHENS}?lingu",
    rf"\bcross{_HYPHENS}?language",
    # the travel metaphor, with or without an interposed count
    r"travell?ed?\s+across",
    # comparison framed as a capability the corpus does not demonstrate
    r"compar\w+[^.]{0,60}(?:across|between)\s+(?:the\s+)?(?:\S+\s+){0,3}languages",
    r"compar\w+\s+(?:the\s+)?languages\b",
    r"(?:support|permit|enabl|allow)\w*[^.]{0,60}"
    r"(?:across|between)\s+(?:the\s+)?(?:\S+\s+){0,3}languages",
)


# The shared-semantic-space assertion, which the patterns above do not cover.
#
# 0338 cut "place all works in a shared semantic space regardless of language"
# from the data paper's §1 and never pinned it — so the paper could regress to
# it, and two sentences in the multilayer paper still carried it. Only one of
# those was found by review; the other (§2, describing the corpus rather than
# comparing methods) was found by running this pattern. That asymmetry is the
# argument for the guard.
#
# The defect is the *unattributed indicative*. A multilingual transformer is
# trained on an objective that pulls translations together; whether it succeeds
# on this corpus is a measurement nobody here has taken. Saying the model "is
# trained to place" texts in one space reports the objective, which is true and
# checkable; saying it "places" them reports an outcome, which is not.
#
# Attribution is therefore what the guard looks for, not vocabulary. This keeps
# it usable in a methods paper whose subject *is* embedding behaviour — a guard
# forbidding the topic's words in a paper about that topic would be the wrong
# shape, and would push an author to drop the honest sentence rather than
# attribute it.
# The span is wide because the object of "place" is often a language list: the
# multilayer §2 sentence puts 70 characters between the verb and the phrase,
# and a 60-character bound silently missed it while catching its §6.1 sibling.
# Widening costs nothing — `[^.]` cannot cross a sentence boundary.
_PLACING = r"\b(?:place|places|map|maps|put|puts|project|projects)\b[^.]{0,120}\bsemantic space\b"
_ATTRIBUTION = r"\b(?:trained|designed|intended|built|meant|aims?)\s+to\b"


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


def _unattributed_placing(text: str) -> list[str]:
    """Sentences asserting the model *does* place texts in one semantic space.

    Sentence-scoped rather than pattern-scoped: the attribution and the verb it
    qualifies are always in the same sentence, and a lookbehind cannot span the
    variable-width phrases that carry it.
    """
    found = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if re.search(_PLACING, sentence, flags=re.I) and not re.search(
                _ATTRIBUTION, sentence, flags=re.I):
            found.append(" ".join(sentence.split()))
    return found


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

    # English comes from the fixture, not from reconstructing it out of the
    # rounded percentage: `_pct` keeps one decimal, so at corpus scale that
    # reconstruction is off by a few works and the identity would only hold
    # because the fixture is tiny (round-2 review).
    english = languages.count("en")
    assert english + _count(v["lang_non_english_n"]) + _count(
        v["lang_unclassified_n"]) == _count(v["corpus_total"])


def test_non_english_layer_is_not_total_minus_english(monkeypatch):
    """The originating defect, replayed.

    With unclassified works present, total-minus-English overstates the
    non-English layer. A rewrite that reintroduced the shortcut would pass
    every count-formatting check and fail here.
    """
    languages = ["en"] * 6 + ["fr", "pt", "es"] + [None] * 4
    v = _corpus_stats(languages, monkeypatch)

    total = _count(v["corpus_total"])
    assert _count(v["lang_non_english_n"]) < total - languages.count("en")


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
        # every separator that renders as a hyphen (round-2 review)
        "cross‐lingual analysis",
        "cross‑lingual analysis",
        "cross–lingual analysis",
        "cross­lingual analysis",
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


def test_no_undemonstrated_claim_anywhere_in_the_document():
    """The whole file, from byte zero — the exit criterion says "in the paper".

    §1 sells the reuse cases, and a reuse case is a claim: "cross-lingual
    studies" sat there as well as in the Abstract. But an earlier draft started
    the scan at `## 1. Introduction` and stopped at `## References`, which left
    the title, the keywords list, and the Related-dataset bullet unread.
    Round-2 review replanted the originating string into each of the three and
    all three passed. The title is the worst of them: it is the PDF cover and
    the Zenodo citation string, so a claim there travels further than one in §5.

    Only HTML comments are stripped. They carry provenance notes that name the
    defect on purpose, and a comment is not a claim to a reader.
    """
    document = re.sub(r"<!--.*?-->", "", read(DATA_PAPER), flags=re.S)

    found = _hits(document)

    assert not found, (
        f"the paper claims {found} without a diagnostic behind it (ticket 0338)"
    )


# --- 3. The shared semantic space is an objective, not a measured outcome ---

def test_no_document_asserts_the_shared_semantic_space_as_an_outcome():
    """Every deliverable that describes the embedding model, not just the paper.

    The claim travelled: 0338 calibrated it out of the data paper while two
    sentences of the multilayer paper kept it, and the review that caught the
    first of those missed the second. A guard reads all three documents in one
    pass, which is the thing a review round demonstrably does not do.
    """
    offenders = {
        os.path.relpath(doc, ROOT): hits
        for doc in EMBEDDING_DOCS
        if (hits := _unattributed_placing(re.sub(r"<!--.*?-->", "", read(doc), flags=re.S)))
    }

    assert not offenders, (
        f"{offenders} assert as an outcome what is only the model's training "
        f"objective (ticket 0338). Attribute it — \"is trained to place\", the "
        f"form the data paper's §1 and §3 already use — or publish the "
        f"measurement that makes the indicative true."
    )


def test_semantic_space_guard_catches_the_wordings_it_was_written_against():
    """Red-test: the two live sentences, and the data-paper one 0338 removed."""
    for text in [
        # multilayer §2, the one review missed
        "The multilingual embedding model places works in English, French, "
        "Chinese, Japanese, and German into a shared semantic space.",
        # multilayer §6.1, the one review found
        "Multilingual sentence-transformers (here `BAAI/bge-m3`) place documents "
        "in a shared semantic space regardless of language.",
        # data paper §1, cut by 0338 and unpinned until now
        "embeddings that place all works in a shared semantic space regardless "
        "of language",
        "the encoder maps every abstract into one shared semantic space",
    ]:
        assert _unattributed_placing(text), f"the guard does not catch {text!r}"


def test_semantic_space_guard_passes_attributed_and_unrelated_prose():
    """The other polarity: attributed claims and neighbouring vocabulary.

    The third case is the one that decides the guard's shape. §2 of the
    multilayer paper discusses adapting change-point methods to
    high-dimensional semantic spaces — the topic, with no assertion about this
    model. A guard keyed on the phrase rather than on the verb would fire there
    and be deleted within a week.
    """
    for text in [
        "The multilingual embedding model is trained to place works into a "
        "shared semantic space.",
        "The model maps texts in English, French, Chinese, Japanese, and German "
        "into a shared semantic space, which is designed to group works by topic "
        "rather than by language.",
        "adapting them to high-dimensional semantic spaces requires either "
        "dimensionality reduction or divergence-based summarisation",
        "embedded with a sentence-transformer trained to place texts of any of "
        "them in one semantic space",
    ]:
        assert not _unattributed_placing(text), f"the guard wrongly fires on {text!r}"
