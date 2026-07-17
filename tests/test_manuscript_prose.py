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
from manuscript_source_qmd import REPO_ROOT, abstract, body, paragraphs, raw, section

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


def test_mitchell_object_and_aid_apparatus_cited():
    """R2.30 + object-construction lineage: Mitchell's account of the economy as
    a constructed object (1998) anchors the intro thesis, and his critique of the
    development/aid apparatus (2002) is engaged in the development-economics
    passage alongside Desrosières/Porter — the on-point reference for the
    'biased aid architectures' remark, read before citing."""
    assert "@mitchell1998" in section("a precise number"), (
        "Mitchell 1998 not cited in the introduction thesis"
    )
    assert "@mitchell2002" in section("three disjoint traditions"), (
        "Mitchell 2002 not cited in the development-economics passage"
    )


def test_biennial_assessment_figure_is_sourced():
    """Ticket 0192: the $340--650bn total-flows figure must carry its source
    (the 2014 UNFCCC Biennial Assessment), not stand uncited."""
    assert "@unfccc2014biennial" in section("Crystallization"), (
        "the $340--650bn Biennial Assessment figure is not sourced"
    )


def test_100bn_legal_standing_and_baku_gap_visible():
    """Ticket 0191: the $100bn pledge's move from Copenhagen 'take note' to Cancún
    decision standing must be cited (@unfccc2010cancun); and the Baku passage must
    make the distributive gap visible — the $1.3T call vs the $300bn binding goal,
    the non-binding 'Baku to Belém' roadmap — and set the magnitude against a state
    defence budget. Mechanical presence, no phrasing pinned."""
    cryst = section("Crystallization")
    assert "@unfccc2010cancun" in cryst, "Cancún formalisation of the $100bn pledge not cited"
    controv = section("Counting is governing")
    assert "1.3 trillion" in controv, "Baku $1.3T call (the ask) not made visible"
    assert "Baku to Bel" in controv, "'Baku to Belém' roadmap not named"
    assert "national defence" in controv.lower() or "1.01 trillion" in controv, (
        "defence-budget scale comparator missing"
    )
    assert "floor" in controv.lower(), (
        "recipient-side decomposition (SIDS/LDC allocation floors) missing"
    )


def test_article43_to_bali_shift_is_concrete():
    """Ticket 0189 (R2p, R2w): the Article 4.3 obligation must name the Annex II /
    GEF machinery behind it, and the Bali shift must name the policy gap that
    drove the move to a broader category (the GEF's incremental-cost logic
    proving insufficient for adaptation) — not just assert that a shift
    happened. Mechanical presence, no phrasing pinned.

    An earlier version of this guard also pinned a single named trigger (the
    IPCC's Fourth Assessment Report) for the Bali shift. The author dropped
    that attribution on reread (2026-07-17): reducing a multicausal diplomatic
    conjuncture to one report overstates what it can explain (R2.12/R2.19 in
    ticket 0152's traceability ledger carry the full reasoning). The guard no
    longer requires a single-trigger claim.
    """
    before = section("three disjoint traditions")
    assert "Annex II" in before, "Article 4.3 obligation not tied to Annex II"
    assert "Global Environment Facility" in before, (
        "incremental-cost mechanism (GEF) not named in the Article 4.3 passage"
    )
    cryst = section("Crystallization")
    assert "Global Environment Facility" in cryst, (
        "GEF/adaptation policy gap not named as the driver of the Bali shift"
    )
    assert "adaptation" in cryst.lower(), (
        "mitigation/adaptation incremental-cost asymmetry not stated as the mechanism"
    )


def test_cdm_functioning_named():
    """Ticket 0190: the CDM passage must show the mechanism functioning — the
    registering body (Executive Board) and the source of post-2012 demand (the
    EU ETS) — beyond the already-present CER / additionality / price-collapse
    detail. Presence check, survives rewrites."""
    before = section("three disjoint traditions")
    assert "Executive Board" in before, "CDM Executive Board (registering body) not named"
    assert "Emissions Trading System" in before, (
        "post-2012 demand source (EU ETS) not named"
    )


def test_turkiye_case_maps_to_four_controversies():
    """Ticket 0194: the Türkiye case must keep its concrete detail (project ID,
    amounts) and make the mapping to the four recurring controversies explicit in
    prose — including why the private-finance-attribution controversy does not
    apply to this all-public deal, and the $100bn rescaling. Guards against the
    mapping being dropped, or the concrete figures shed, on a later rewrite."""
    case = section("Türkiye")
    assert "P508354" in case, "Türkiye case dropped its project identifier"
    assert "625" in case, "Türkiye case dropped the IBRD loan figure"
    assert "four controvers" in case.lower(), "explicit mapping to the four controversies missing"
    assert "private" in case, "the private-finance-attribution (non-)applicability not addressed"
    assert "100 billion" in case, "the $100bn rescaling of the attribution dispute missing"


def test_loss_and_damage_is_a_bounded_thesis_limit():
    """Ticket 0138 (R1.4): loss and damage must stand as its own subsection that
    (a) gives the Warsaw-to-Fund genealogy the referee named, not just the 2022
    fund; (b) states explicitly that this is where the within-categories reading
    does not hold; and (c) links the insurance logic to the effort-sharing
    tradition's coalition question. Guards against the material staying a single
    unmarked paragraph in the 'four controversies' list, or shedding the
    genealogy or the coalition link on a later rewrite."""
    ld = section("Loss and damage").lower()  # raises if the subsection is absent
    for marker in ("warsaw", "santiago", "2013", "2023"):
        assert marker in ld, f"loss-and-damage genealogy missing {marker!r}"
    assert re.search(
        r"does not hold|outside the (crystalliz\w+|established) categor|"
        r"limit(s)? (the|this) (claim|reading|thesis)",
        ld,
    ), "no explicit statement that loss and damage bounds the within-categories reading"
    assert "coalition" in ld, "no coalition-formation note"
    assert "negishi" in ld, "coalition note does not link back to the effort-sharing tradition"


def test_loss_and_damage_is_the_falsifiable_test_in_the_conclusion():
    """Ticket 0171 (action 3, formulation b): the loss-and-damage payoff must land
    as an explicit falsifiable test *in the conclusion* — the regime is predicted
    to absorb L&D into the mobilisation/accounting template rather than adjudicated
    liability, with a stated way the thesis could be wrong, anchored on the
    documentary fact that the regime already forecloses the liability logic (Paris
    decision 1/CP.21 para 51, @unfccc2015paris). And it must land ONCE: the
    forward-looking bifurcation must NOT also sit in the §3 'Loss and damage'
    subsection (single-landing — §3 keeps the anomaly, the conclusion owns the
    test). Mechanical presence + negative single-landing guard; no phrasing pinned.
    """
    concl_raw = section("Conclusion")
    concl = concl_raw.lower()
    assert "liability" in concl, (
        "the conclusion does not name the liability logic L&D would require to break the thesis"
    )
    assert "@unfccc2015paris" in concl_raw, (
        "the liability-foreclosure anchor (Paris decision 1/CP.21 para 51) is not cited "
        "in the conclusion"
    )
    assert re.search(
        r"falsif|refut|would be wrong|could be wrong|test of the (thesis|reading|claim)|"
        r"embarrass|prediction",
        concl,
    ), "the conclusion does not frame loss and damage as a falsifiable test of the thesis"
    # single-landing: the forward-looking bifurcation must have left the §3 subsection
    ld = section("Loss and damage").lower()
    assert not re.search(r"how far the settlement can stretch|on that answer rides", ld), (
        "the forward-looking bifurcation is still duplicated in the §3 subsection; "
        "it must land only in the conclusion"
    )


def test_title_and_abstract_lead_with_aggregate_birth():
    """Ticket 0181: the title and abstract lead with the birth of an economic
    aggregate (brief title-frames-aggregate-birth), and the abstract's opening
    paragraph states the three conditions (a political number fixed before the
    object, a pre-existing statistical infrastructure, economists under
    constraint). 'Strategic ambiguity' is the mechanism, not the headline.
    Mechanical presence; no phrasing pinned."""
    title_line = next(
        line for line in raw().splitlines() if line.strip().startswith("title:")
    )
    assert "aggregate" in title_line.lower(), (
        "the title does not lead with the economic aggregate"
    )
    ab = abstract().lower()
    assert "aggregate" in ab, "the abstract does not name the economic aggregate"
    assert re.search(r"political number|before .{0,40}(count|settled|object)", ab), (
        "condition 1 (a political number fixed before the object) missing from the abstract"
    )
    assert re.search(r"infrastructure|development-aid accounts|already (standing|in place)", ab), (
        "condition 2 (a pre-existing statistical infrastructure) missing from the abstract"
    )
    assert "constraint" in ab, (
        "condition 3 (economists under constraint) missing from the abstract"
    )


def test_conclusion_lands_on_aggregate_birth():
    """Ticket 0171 (action 1): the conclusion must land on the thesis — the birth of
    a new economic aggregate — placed in the GDP / monetary-aggregates lineage that
    makes 'aggregate' more than a metaphor, and stating its three general conditions:
    a political number fixed before the object, a pre-existing statistical
    infrastructure, and economists under constraint. 'Strategic ambiguity' stays the
    mechanism inside the story, not the headline (brief title-frames-aggregate-birth).
    Mechanical presence, no phrasing pinned."""
    concl = section("Conclusion").lower()
    assert "aggregate" in concl, "the conclusion does not name the economic aggregate"
    assert re.search(r"monetary aggregat|gross domestic product|\bgdp\b", concl), (
        "the aggregate-birth claim is not placed in the GDP / monetary-aggregates lineage"
    )
    assert re.search(r"before .{0,50}(object|was (defined|settled)|would count|anyone)", concl), (
        "condition 1 (a political number fixed before the object) not stated"
    )
    assert re.search(r"infrastructure|development-aid accounts|already (standing|in place)", concl), (
        "condition 2 (a pre-existing statistical infrastructure) not stated"
    )
    assert "economists" in concl and re.search(r"constraint|constrain", concl), (
        "condition 3 (economists under constraint) not stated"
    )


def test_abandonment_of_precision_is_displacement_not_repeal():
    """Ticket 0171 (action 2): the Article 4.3 -> aggregate trajectory must read as a
    result — a displacement of the centre of gravity — not as repeal. The 1992
    obligation is stated to persist (Article 4.3 still binds / still operates), and
    the conclusion must not claim the aggregate 'replaces' the earlier logic. This
    keeps the conclusion consistent with the body's 'extended, not repealed'
    (@sec-crystallization). Mechanical presence + negative guard; no phrasing pinned.
    """
    concl = section("Conclusion")
    concll = concl.lower()
    assert "4.3" in concl, "the persisting Article 4.3 obligation is not named in the conclusion"
    assert re.search(
        r"never rescinded|not (been )?rescinded|still binds|still operates|does not repeal|"
        r"not (a )?repeal|overlay",
        concll,
    ), "the conclusion does not state that the precise 1992 obligation persists (displacement, not repeal)"
    assert not re.search(r"replaces the logic of reimbursing", concll), (
        "the trajectory still claims the aggregate 'replaces' the earlier logic — an overclaim, "
        "since Article 4.3 was never rescinded"
    )


def test_conclusion_engages_star_griesemer_concede_then_displace():
    """Ticket 0171 (action 4, brief boundary-object-conceded-then-displaced): the
    conclusion must engage Star & Griesemer's boundary object by name
    (@star_griesemer1989), concede the weak-sense fit, then displace — landing,
    via Star 2010 (@star2010), on boundary *infrastructure* (post-2015
    standardisation). Mechanical presence + the two citations; no phrasing pinned.
    """
    concl = section("Conclusion")
    concll = concl.lower()
    assert "@star_griesemer1989" in concl, "Star & Griesemer 1989 not cited in the conclusion"
    assert "@star2010" in concl, "Star 2010 (the infrastructure move) not cited in the conclusion"
    assert "boundary object" in concll, "the boundary-object concept is not engaged by name"
    assert "infrastructure" in concll, "the displacement to boundary *infrastructure* is missing"
    assert re.search(r"concede|the description fits|worth conceding|one might", concll), (
        "no concession of the weak-sense boundary-object fit"
    )
    assert re.search(
        r"stops short|leaves? (it )?unexplained|does not explain|need not begin|"
        r"less a boundary object",
        concll,
    ), "no displacement — what the boundary-object label does not explain"


def test_conclusion_gdp_lineage_anchored():
    """Ticket 0171 (action 7, light anchor): the GDP / aggregate lineage in the
    conclusion is anchored on @lepenies2016 (GDP as a political number resting on a
    convention), cited on the analogy line alongside @desrosieres1998. Light anchor
    only — the analogy justifies the framing, it is not a systematic comparison
    (brief title-frames-aggregate-birth, analogy-scope decision)."""
    concl = section("Conclusion")
    assert "@lepenies2016" in concl, (
        "the GDP lineage (Lepenies 2016, Power of a Single Number) is not cited on the analogy line"
    )


def test_conclusion_chantiers_migrated_leaving_one_limit():
    """Ticket 0171 (action 6): the 'work sites' / chantiers list (archival,
    geographic, legal future-research directions) is migrated to the book project;
    the conclusion keeps at most one limits line — the recipient-side asymmetry
    (donors define and measure). Negative guard on the list + one presence."""
    concl = section("Conclusion").lower()
    assert "work site" not in concl, (
        "the chantiers / 'work sites' list is still in the conclusion — migrate it to the book"
    )
    assert "recipient countries" in concl or "who define and measure" in concl, (
        "the one kept limit (recipient-side asymmetry) is missing from the conclusion"
    )


def test_finance_development_lineage_is_situated():
    """Ticket 0139 (R1.5): the mobilisation/leverage vocabulary must be traced to
    its scholarly home, the finance-and-growth literature (King & Levine 1993,
    Aghion & Bolton 1997), AND the disconnection must be analysed — climate
    finance borrowed the vocabulary while sealing its central category off from
    that literature's unsettled empirical questions. Guards against the
    vocabulary sitting unmoored (lineage never named), or the lineage being
    cited as decoration without the disconnection point that carries the
    analytic weight the reviewer asked for."""
    cryst = section("Crystallization").lower()
    for key in ("king_levine1993", "aghion_bolton1997"):
        assert key in cryst, f"finance-and-growth lineage missing citation {key!r}"
    assert "finance-and-growth" in cryst or "financial deepening" in cryst, \
        "the finance-and-growth / financial-deepening lineage is not named"
    assert "disconnection" in cryst or re.search(
        r"cut loose|sealed?\s+\w*\s*off|stopped at the words", cryst,
    ), "the disconnection from the finance-development debates is not analysed"


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
