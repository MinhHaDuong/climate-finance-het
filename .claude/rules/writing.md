---
globs: ["deliverables/**"]
---

# Writing Rules

## Core argument

Climate finance crystallized as an economic object by ~2009. Everything since has been fought within the categories established at that moment. This is intellectual history showing how economists create governable objects through quantification.

## Three-act periodization (history, corpus-corroborated)

- I. Before climate finance (1990–2006) — three disconnected traditions
- II. Crystallization (2007–2014) — structural breaks at 2007 (cosine) and 2013 (JS)
- III. The established field (2015–2025) — no further structural break

The periodization is historically grounded and *corroborated* by embedding-based break detection — not the reverse. The detection is blind to the COP calendar, so finding the act I→II break at 2007/2009 independently of the policy timeline is corroboration, not circularity. The act II→III boundary is institutional: Paris (2015) shows only a marginal Jensen–Shannon rise, not a rupture, which is what the thesis predicts (post-2015 disputes occur within crystallized categories). Don't claim the periodization is "endogenous / not imposed from COP milestones" — that overclaims and contradicts the confirmatory framing. The core subset (most-cited papers) shows no structural break at all.

## Corpus

~28,400 works from OpenAlex + Semantic Scholar + ISTEX + bibCNRS + SciSpace + grey lit + teaching. Core subset: ~2,300 papers cited ≥ 50 times.

## Self-check questions

Before producing any substantial text:
1. Does this advance the core argument? (Climate finance as constructed economic object)
2. Is the economist's role visible? (Not just "institutions" or "policymakers")
3. Is this historically grounded? (Specific dates, documents, actors)
4. Does this fit Œconomia's interdisciplinary scope? (HET + STS + policy studies)
5. Will this interest both historians of economics AND climate policy scholars?

This is not a policy paper or a technical report. It's intellectual history.

## Voice and style

- Academic but accessible
- Historical narrative combined with analytical argument
- Avoid jargon; define terms when first introduced
- Show, don't just tell (use specific examples, names, dates)

## Things to avoid

- **Don't:** Write as if climate finance naturally exists. **Do:** Show how it was constructed.
- **Don't:** Assume categories are neutral or technical. **Do:** Analyze political implications of measurement choices.
- **Don't:** Oversimplify North-South divides. **Do:** Show specific actors and their motivations.

## Citation practices

- Cite primary sources with dates
- Name economists and institutions specifically (not "policymakers" but "OECD DAC")
- Include both academic and grey literature
- Track evolution of key terms across time
- Prioritize works that show economists' role in category-making
- Balance institutional documents with critical scholarship
- Include Global South perspectives

## Ghost mode

Write in *The Economist* style: clear, direct, concrete, no filler. No AI tells.
Internalize this — don't mechanically check a list while drafting.
The `/review-pr-prose` panel includes a dedicated AI-tells auditor with full wordlists (`config/ai-tells.yml`).

## CI test polarity rule

Prose adherence tests (`tests/test_manuscript_prose.py`) pin only **negative guards** (forbidden phrasings) and **mechanical checks** (density ratchets, structural presence). They never assert that a specific *positive* phrasing appears — positive pins break on every legitimate rewrite. The asymmetry: defects are lexically stable (an overclaim reads the same in any draft), good prose is not.

Positive editorial intent lives in `docs/editorial-brief.md` — one entry per standing decision (**Decision** / **Rationale** / **Ticket** / **Status**) — and is checked at review time by the `/review-pr-prose` brief auditor against each diff.

**Pure prose tickets get no `## Test` section: TDD is not appropriate.** The red step assumes a machine-checkable positive outcome, and the polarity rule above says prose has none. Verification is review-based: the recompiled artifact and the `/review-pr-prose` panel. A prose ticket extends `tests/test_manuscript_prose.py` only when it pins a newly-observed defect class (negative or mechanical, per the polarity rule), never pro forma to satisfy the handoff template.

**Permitted is not proportionate: close a prose defect class with a sweep, not a guard.** The rule above says *when* a prose guard is allowed; this says when one is worth writing. Fix every instance, then sweep the whole tree for the class at `/roar` step 3 — that sweep is the deliverable. Write a standing guard only if the class recurs *after* a sweep already cleared it.

Why the sweep wins: a prose claim has no data signature, so the only instrument is a source-text pattern match, and that is always one spelling behind. Each synonym needs a new pattern, so the guard accretes lines forever and still misses the next instance, while the sweep costs nothing and reads every file at once. Where a defect *does* have a data signature, the opposite holds — assert the property in the code path (`~/.claude/rules/workflow.md`, and the `feedback_static_guard_cannot_replace_an_invariant` memory).

Measured on ticket 0338/0590 (2026-07-28), an unattributed capability claim — "the model **places** works in a shared semantic space", asserting as an outcome what is only its training objective. Three live instances across two deliverables: review found one, a drafted guard found the second, the `/roar` sweep found the third. The guard would have missed that third one, matching `semantic space` where the sentence said `same space`. It was reverted at the author's direction — 115 test lines for two phrases — and the third instance is the evidence for that call, not against it.

Two shaping notes if a guard does earn its place. Key it on the **distinguishing feature** (there, whether an attribution verb is present) and never on topic vocabulary, or it fires on a methods paper whose subject *is* that topic and gets deleted within a week. And check the span bounds between the parts of the pattern: a 60-character window caught one instance and silently skipped its sibling, where a language list sat in between.

## Testing

`make check-fast` before editing. `make clean` then `make all` (separate Bash calls) as integration test before PR.

## When to ask the author

- Argument direction is genuinely ambiguous
- Multiple good sources conflict
- Author's position on controversial topic is unclear
