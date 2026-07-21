"""Negative half of the prose ratchet over deliverables/manuscript/manuscript.qmd (ticket 0147).

Per the CI test-polarity rule (ticket 0148): this file pins only *negative*
guards and mechanical density checks. No positive authorial wording is asserted
— a legitimate rewrite must never turn one of these red. The positive voice
lives in the editorial brief, not here.

Two guard shapes:

- **Hard bans** — a forbidden phrasing whose count must stay zero. Seeded from
  ``config/ai-tells.yml`` (the single source for the wordlists) plus the AEDIST
  technical-report defect classes (forward promises, lab-journal connectives,
  AI-English doublets, hedging stacks) and the v2.0.2 reviewer defects
  (define-by-negation closers, empty paragraph-closers, repeated openers).

- **Density ratchets** — a count that may only decrease. The ceiling lives in a
  committed ``tests/data/<metric>_ceiling.txt`` integer; an edit pushing the
  count above it fails, and the only way to pass after a reduction is to lower
  the ceiling in a deliberate commit. Covers em dashes, define-by-negation
  ("not X, but Y"), conditional words (``robust``/``landscape``), and hardcoded
  figure/table cross-refs (which should be ``@fig-``/``@tbl-``).

Each guard is a pure ``find_*`` function exercised twice: once against the live
manuscript (must be clean / within ceiling) and once against a known-bad
fixture (the fang — proves the guard actually catches its defect). The fang
tests are the red-first proof required by the ticket.
"""

import re
from pathlib import Path

import pytest
import yaml
from manuscript_source_qmd import REPO_ROOT, abstract, body, paragraphs, section

pytestmark = pytest.mark.adherence

DATA_DIR = Path(__file__).resolve().parent / "data"
AI_TELLS = REPO_ROOT / "config" / "ai-tells.yml"


# --------------------------------------------------------------------------- #
# ai-tells.yml — the single source for the wordlists
# --------------------------------------------------------------------------- #
def _ai_tells() -> dict:
    with open(AI_TELLS, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _word_re(word: str) -> re.Pattern:
    return re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)


def find_words(text: str, words: list[str]) -> list[str]:
    """Whole-word, case-insensitive matches for any word in ``words``."""
    return [m.group(0) for w in words for m in _word_re(w).finditer(text)]


def find_phrases(text: str, phrases: list[str]) -> list[str]:
    """Case-insensitive substring matches for any phrase in ``phrases``."""
    low = text.lower()
    return [p for p in phrases if p.lower() in low]


def find_patterns(text: str, patterns: list[str]) -> list[str]:
    """Case-insensitive regex matches for any pattern in ``patterns``."""
    return [
        m.group(0)
        for p in patterns
        for m in re.finditer(p, text, re.IGNORECASE)
    ]


# --------------------------------------------------------------------------- #
# Defect-class pattern banks (AEDIST + v2.0.2 reviewer findings)
# --------------------------------------------------------------------------- #
# Forward promises: deleted, not hedged. Forward-looking material is framed as
# programme in a future-work section, never as a commitment inside the paper.
FORWARD_PROMISE = [
    r"\bwe will (?:show|see|argue|demonstrate|report|present|return to)\b",
    r"\bas we (?:shall|will) see\b",
    r"\bin what follows\b",
    r"\bthe (?:next|following) section will\b",
    r"\bwe plan to\b",
    r"\bwe intend to\b",
    r"\bfuture work will\b",
]

# Lab-journal register: state the method/result, not the chronology of doing it.
LAB_JOURNAL = [
    r"\bwe then ran\b",
    r"\bwe next ran\b",
    r"\bwe proceeded to\b",
    r"\bwe decided to\b",
    r"\bwe set out to\b",
    r"\bwe began by\b",
    r"\bwe started by\b",
    r"\bhaving (?:run|finished|completed)\b",
]

# AI-English doublets: vacuous near-synonym emphasis pairs.
AI_DOUBLET = [
    r"\bsolidly and firmly\b",
    r"\bclearly and explicitly\b",
    r"\bfully and completely\b",
    r"\bsimply and easily\b",
    r"\bcarefully and thoroughly\b",
    r"\baccurately and precisely\b",
    r"\bcomprehensive and complete\b",
]

# Hedging stacks: one hedge maximum (prose rule). These are doubled hedges.
HEDGING_STACK = [
    r"\bmay potentially\b",
    r"\bcould possibly\b",
    r"\bmight perhaps\b",
    r"\bit might be argued that\b",
    r"\bit seems likely that perhaps\b",
    r"\bperhaps,? to some extent\b",
]

# Empty paragraph-closers: vacuous summary sentences that add no content.
EMPTY_CLOSER = [
    r"\bthis is significant\.",
    r"\bthis matters\.",
    r"\bthis is important\.",
    r"\bthese findings are important\.",
    r"\bthis cannot be overstated\.",
    r"\bthis is no accident\.",
    r"\bthis is the central claim\.",
]

# Cambridge British -ise/-isation spelling variants (ticket 0243 D2: this
# manuscript uses Oxford British throughout — -ize/-ization). Manuscript-scoped
# deliberately: other deliverables may keep their own spelling convention, and
# ai-tells.yml's blacklisted_words also feeds the cross-document reduction
# guard (qa_llm_judge_guards.py), which is the wrong scope for a per-document
# house-style choice. Root -ise words that are NOT part of this suffix family
# (precise, promise, surprise, otherwise, compromise, expertise, exercise,
# arise, rise, raise, devise, disguise, supervise) are deliberately absent —
# they never had an -ize form to ratchet.
BRITISH_ISE_SPELLING = [
    r"\bmobilisation\b", r"\bmobilised\b", r"\bmobilise\b", r"\bmobilising\b",
    r"\boptimisation\b", r"\boptimised\b",
    r"\bstabilised\b", r"\bstabilise\b", r"\bstabilises\b",
    r"\beconomisation\b", r"\bindustrialised\b",
    r"\borganisation\b", r"\borganisations\b", r"\borganised\b", r"\borganise\b",
    r"\bemphasised\b", r"\bpolarisation\b",
    r"\bcrystallised\b", r"\bcrystallise\b",
    r"\brecognised\b", r"\brecognise\b", r"\bcharacterise\b",
    r"\bnormalised\b", r"\bstandardised\b", r"\bstandardise\b",
    r"\bspecialised\b", r"\binternalising\b", r"\boperationalised\b",
    r"\broutinisation\b", r"\bmodernise\b", r"\bmaximising\b", r"\bmetabolises\b",
]


# --------------------------------------------------------------------------- #
# Density metrics
# --------------------------------------------------------------------------- #
# "not X, but Y" define-by-negation: the centerpiece v2.0.2 reviewer defect.
DEFINE_BY_NEGATION_RE = re.compile(r"\bnot\b[^.,;:]{1,60}?,?\s+but\b", re.IGNORECASE)
# Hardcoded figure/table/equation cross-refs (should be @fig-/@tbl-/@eq-).
# Plural ("Figures 3 and 4") and lowercase ("figure 3") forms are caught too, so
# the ratchet cannot be silently evaded by a casing or pluralization change.
# "Section N" is excluded: Oeconomia house style mandates numbered sections, so
# referring to them by number in prose is legitimate, not a Quarto-ref defect.
HARDCODED_XREF_RE = re.compile(
    r"\b(?:Figures?|Tables?|Fig\.|Equations?|Eq\.)\s+\d+", re.IGNORECASE
)

EM_DASH_PARAGRAPH_CAP = 2  # local clustering cap at the ai-tells target (max_per_paragraph: 2)


def find_define_by_negation(text: str) -> list[str]:
    return [m.group(0) for m in DEFINE_BY_NEGATION_RE.finditer(text)]


def find_hardcoded_xref(text: str) -> list[str]:
    return [m.group(0) for m in HARDCODED_XREF_RE.finditer(text)]


def find_conditional_words(text: str) -> list[str]:
    words = [c["word"] for c in _ai_tells()["conditional_words"]]
    return find_words(text, words)


def count_em_dashes(text: str) -> int:
    """Em dashes in prose: literal U+2014 plus the ``---`` Markdown ligature."""
    return text.count("—") + text.count("---")


def _ceiling(name: str) -> int:
    path = DATA_DIR / f"{name}_ceiling.txt"
    assert path.exists(), (
        f"missing {path}: the {name} ratchet ceiling must be committed "
        "(one line, the integer count). See ticket 0147."
    )
    return int(path.read_text(encoding="utf-8").strip())


def _assert_within_ceiling(name: str, count: int) -> None:
    ceiling = _ceiling(name)
    assert count <= ceiling, (
        f"manuscript.qmd has {count} {name} occurrences, above the committed "
        f"ceiling of {ceiling} (tests/data/{name}_ceiling.txt). Either reduce "
        f"the count or lower the ceiling in a deliberate commit (ticket 0147)."
    )


# Freshness guard (ticket 0205): the ``count <= ceiling`` ratchets prove the
# manuscript is *under* each ceiling, never *at* it, so a base rebuild can open a
# huge gap no test flags (em-dash 132 vs 0 after the v2.0.5 rebuild). This upper
# bound catches that. The slack tolerates deliberate ai-tells headroom.
RATCHET_SLACK = 5
RATCHET_METRICS = ("emdash", "define_by_negation", "conditional_words", "hardcoded_xref")


def _ratchet_actuals() -> dict[str, int]:
    """Current count for each density-ratchet metric, keyed by its ceiling name."""
    b = body()
    return {
        "emdash": count_em_dashes(b),
        "define_by_negation": len(find_define_by_negation(b)),
        "conditional_words": len(find_conditional_words(b)),
        "hardcoded_xref": len(find_hardcoded_xref(b)),
    }


def _live_ceilings() -> dict[str, int]:
    return {name: _ceiling(name) for name in RATCHET_METRICS}


def _find_stale(ceilings: dict[str, int], actuals: dict[str, int], slack: int) -> list[str]:
    """Metrics whose ceiling exceeds actual by more than ``slack`` (stale)."""
    return [
        f"{name}: ceiling {ceilings[name]} vs actual {actuals[name]} "
        f"(gap {ceilings[name] - actuals[name]})"
        for name in actuals
        if ceilings[name] - actuals[name] > slack
    ]


# --------------------------------------------------------------------------- #
# Live-manuscript guards
# --------------------------------------------------------------------------- #
def test_no_blacklisted_words():
    hits = find_words(body(), _ai_tells()["blacklisted_words"])
    assert not hits, f"AI-tell blacklisted words in manuscript prose: {hits}"


def test_no_blacklisted_phrases():
    hits = find_phrases(body(), _ai_tells()["blacklisted_phrases"])
    assert not hits, f"AI-tell blacklisted phrases in manuscript prose: {hits}"


def test_no_forward_promise():
    hits = find_patterns(body(), FORWARD_PROMISE)
    assert not hits, f"forward-promise phrasings in manuscript prose: {hits}"


def test_no_lab_journal_register():
    hits = find_patterns(body(), LAB_JOURNAL)
    assert not hits, f"lab-journal process narration in manuscript prose: {hits}"


def test_no_ai_english_doublet():
    hits = find_patterns(body(), AI_DOUBLET)
    assert not hits, f"AI-English synonym doublets in manuscript prose: {hits}"


def test_no_hedging_stack():
    hits = find_patterns(body(), HEDGING_STACK)
    assert not hits, f"stacked hedges in manuscript prose: {hits}"


def test_no_empty_paragraph_closer():
    hits = find_patterns(body(), EMPTY_CLOSER)
    assert not hits, f"empty paragraph-closers in manuscript prose: {hits}"


def test_no_ise_spelling_variants():
    hits = find_patterns(body(), BRITISH_ISE_SPELLING)
    assert not hits, f"Cambridge British -ise/-isation spellings (ticket 0243 D2 is Oxford): {hits}"


def _prose_paragraphs() -> list[str]:
    """Paragraphs that are authored prose — no headings, directives, images."""
    return [p for p in paragraphs() if p.lstrip()[:1] not in ("#", "\\", "!", "|", ":")]


def test_no_repeated_paragraph_openers():
    """No two adjacent prose paragraphs open with the same first four words."""
    openers: list[str] = []
    for para in _prose_paragraphs():
        first = re.sub(r"[*_`#>]", "", para).split()
        openers.append(" ".join(first[:4]).lower())
    dups = [
        openers[i]
        for i in range(1, len(openers))
        if openers[i] and openers[i] == openers[i - 1]
    ]
    assert not dups, f"adjacent paragraphs share an opener: {dups}"


def test_define_by_negation_within_ceiling():
    _assert_within_ceiling("define_by_negation", len(find_define_by_negation(body())))


def test_conditional_words_within_ceiling():
    _assert_within_ceiling("conditional_words", len(find_conditional_words(body())))


def test_hardcoded_xref_within_ceiling():
    _assert_within_ceiling("hardcoded_xref", len(find_hardcoded_xref(body())))


def test_em_dash_global_ratchet():
    _assert_within_ceiling("emdash", count_em_dashes(body()))


def test_em_dash_paragraph_cap():
    over = [(count_em_dashes(p), p) for p in paragraphs() if count_em_dashes(p) > EM_DASH_PARAGRAPH_CAP]
    preview = "\n".join(f"  {c} em dashes: {' '.join(p.split())[:90]}…" for c, p in over[:5])
    assert not over, (
        f"{len(over)} paragraph(s) exceed the {EM_DASH_PARAGRAPH_CAP}-em-dash "
        f"cap (ticket 0147). Diversify the punctuation:\n{preview}"
    )


def test_ratchet_ceilings_are_fresh():
    """Ticket 0205: a density-ratchet ceiling sitting more than ``RATCHET_SLACK``
    above its actual count is stale — it guards nothing near the real value. The
    v2.0.5 base rebuild once left the em-dash ceiling at 132 against an actual of
    0, and define-by-negation at 20 against 0, while the ``count <= ceiling`` suite
    stayed green (ticket 0134/0162, #935). This upper guard fails loudly instead,
    and names the remedy. Distinct from the lower ``count <= ceiling`` ratchets,
    which stay in force; the intentional ai-tells budgets (define-by-negation 3,
    conditional-words 5) sit within the slack and pass."""
    stale = _find_stale(_live_ceilings(), _ratchet_actuals(), RATCHET_SLACK)
    assert not stale, (
        "stale ratchet ceiling(s) — re-cut tests/data/<metric>_ceiling.txt toward "
        "the actual count (ticket 0205):\n  " + "\n  ".join(stale)
    )


def test_substrate_smoke():
    """The substrate exposes a non-empty body, paragraphs, abstract, section."""
    assert len(body()) > 1000
    assert len(paragraphs()) > 20
    assert abstract().startswith("**Abstract.**")
    assert "Copenhagen" in section("Crystallization")


# --------------------------------------------------------------------------- #
# Fang tests — each guard must catch its defect on a known-bad fixture
# --------------------------------------------------------------------------- #
def test_fang_blacklisted_words():
    assert find_words("We delve into the vibrant tapestry.", _ai_tells()["blacklisted_words"])


def test_fang_blacklisted_phrases():
    assert find_phrases("It is important to note the result.", _ai_tells()["blacklisted_phrases"])


def test_fang_forward_promise():
    assert find_patterns("As we will show, the next section will explain.", FORWARD_PROMISE)


def test_fang_lab_journal():
    assert find_patterns("We then ran the model and we decided to stop.", LAB_JOURNAL)


def test_fang_ai_doublet():
    assert find_patterns("The proof is clearly and explicitly correct.", AI_DOUBLET)


def test_fang_hedging_stack():
    assert find_patterns("This may potentially could possibly hold.", HEDGING_STACK)


def test_fang_empty_closer():
    assert find_patterns("The break occurs in 2007. This is significant.", EMPTY_CLOSER)


def test_fang_ise_spelling_variants():
    assert find_patterns("Donors mobilised finance through the organisation.", BRITISH_ISE_SPELLING)


def test_fang_define_by_negation():
    found = find_define_by_negation("Economists did not discover reality, but built categories.")
    assert found


def test_fang_hardcoded_xref():
    # Singular, plural, and lowercase forms must all be caught.
    found = find_hardcoded_xref("See Figure 3, Tables 1, figure 4, and Eq. 2.")
    assert len(found) == 4


def test_fang_conditional_words():
    # find_conditional_words reads the live yaml; build a string from its words.
    words = [c["word"] for c in _ai_tells()["conditional_words"]]
    bad = " ".join(f"the {w} result" for w in words)
    assert len(find_conditional_words(bad)) == len(words)


def test_fang_ratchet_freshness():
    # Boundary: a gap equal to the slack is fresh; one beyond it is stale.
    actual = {"emdash": 0}
    assert not _find_stale({"emdash": RATCHET_SLACK}, actual, RATCHET_SLACK)
    assert _find_stale({"emdash": RATCHET_SLACK + 1}, actual, RATCHET_SLACK)


def test_fang_em_dash_count():
    assert count_em_dashes("a — b --- c") == 2


def test_fang_repeated_openers_logic():
    openers = ["the climate finance object", "the climate finance object"]
    dups = [openers[i] for i in range(1, len(openers)) if openers[i] == openers[i - 1]]
    assert dups
