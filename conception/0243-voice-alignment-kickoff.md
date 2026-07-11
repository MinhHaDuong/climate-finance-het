# Ticket 0243 — Voice-alignment kickoff note

**For the author.** This note asks you to settle four voice decisions before the
full style pass runs, and proposes the protocol for that pass. The companion
files hold the calibration material: `conception/0243-fewshot-set.md` (anchor ×
manuscript comparative pairs) and `conception/0243-sample-rewrites.md` (three
short before/after samples for your arbitration). Nothing in the manuscript has
been touched.

## Decisions to settle

### D1 — Person: authorial "we" or first-person "I"?

The manuscript uses "we / our / us" 21 times and first-person singular zero
times (the only "I" in the file is "Annex I"). The response letter was
converted to first-person singular on 2026-07-10 (ticket 0152 log), with
manuscript quotes deliberately left in "we" until the manuscript itself is
revised — that is this decision.

Your own pre-AI sole-author practice runs both ways. "What is the Price of
Carbon?" (2009) uses "we feel that it would be more informative to clarify";
"Transparency and control" (2001) uses "I find no reason to be satisfied with
potential transparency". The historical pattern is roughly: "we" for procedure,
"I" for conviction.

Options:

- **(a) Keep "we" throughout.** Least churn; standard HET editorial "we"; the
  abstract and method statements read naturally.
- **(b) Switch to "I".** Consistent with the response letter and with sole
  authorship; Œconomia publishes single-author "I" papers; matches the 2001
  register.
- **(c) Your historical mix** — "we" in method prose, "I" at moments of
  judgment. Closest to the anchors, hardest to apply mechanically; the full
  pass would flag each occurrence for a case-by-case call.

### D2 — Spelling: the manuscript currently mixes varieties

Counts from `deliverables/manuscript/manuscript.qmd`: **-ization nouns**
crystallization ×12, periodization ×6; **-isation/-ise forms** mobilisation
×18, mobilised ×16, optimisation ×6, economisation ×4, stabilised, standardised,
operationalised, and the verbs crystallise/crystallised — the same lemma spelt
both ways (plus one stray "crystallized"). "Scientization" (Marcussen's term)
and "ghettoization" (quoted from Carè & Weber) are quoted terms of art and stay
as their sources spell them, whatever you decide.

The style anchor's language policy (docs/style-anchor-v205.md, decision (a),
2026-07-08) is British English. British has two legitimate conventions:

- **(a) Cambridge British (-ise/-isation everywhere):** crystallisation,
  periodisation, mobilisation. Touches the paper's key term in 14 places,
  including the section title.
- **(b) Oxford British (-ize/-ization):** keeps crystallization and
  periodization as they stand; changes mobilisation → mobilization and the
  whole -ise family (~60 changes). Recognised British (OUP, Nature); reads as
  American to some referees.
- **(c) Pin the status quo as a deliberate convention** (nouns of art in
  -ization, everything else -ise). Defensible only if stated; fragile under
  copy-editing.

Either (a) or (b) satisfies the one-variety rule; (a) is the smaller diff.

### D3 — Hedging register: how far toward your dry understatement?

Current manuscript hedges are formal-academic: "It is thus possible that",
"may record", "the reading proposed here", "seemed useful to us". Your
anchored hedging is lighter and drier: "we suggest", "in our view", "it might
not be a bad idea" — one hedge at a time, often with understatement ("Recent
macroeconomic developments remind that this is not sustainable").

The dial to set: full anchor register (dry, occasionally ironic — the "touch
of sarcasm" of the 2009 essay), or a restrained version (plain verbs, single
hedges, no irony)? Two constraints bound the upper end: the no-oversell norms
on the periodization are untouchable in either direction — understatement must
not shade into coyness about what the corpus does and does not show — and
Œconomia's HPS readership tolerates light irony but not glibness.

### D4 — Question-closings: use your device or not?

Your anchors close arguments with a question ("Is not this the essence of the
precautionary principle?" — 2003 ozone paper, conclusion). The manuscript
already uses question volleys mid-argument ("Additional to what? To existing
ODA? To the target of 0.7% of GNI?") but every section closes declaratively.

Options: adopt the question-close at one or two section ends where the question
genuinely is the point (candidates: end of @sec-controverses, end of the
Türkiye subsection); or keep all closes declarative. Sparing use recommended if
adopted — the device marks your voice precisely because it is rare.

## Protocol proposal (anchor-first, per AEDIST 0522)

The direct precedent is AEDIST ticket 0522 (tactical editorial round,
2026-06-10): author-articulated intent first, voice calibrated from your real
texts with concrete reproduction patterns rather than a vague gloss, and 2–3
anchor passages author-approved in session **before** the full pass. It worked;
this ticket reuses it.

1. **You settle D1–D4** (this note) and **arbitrate the three samples** in
   `conception/0243-sample-rewrites.md`: accept, amend, or reject each. Amended
   samples become the binding calibration.
2. **Full pass, section by section**, driven by the approved samples plus the
   comparative pairs in `conception/0243-fewshot-set.md`. One PR, one commit
   per manuscript section, so you can accept or bounce sections independently.
   Manuscript prose is a prose workpackage: the autonomous pass goes through
   branch + PR for your arbitration, never in place.
3. **Guards on every commit:** prose suite green (`tests/test_manuscript_prose.py`);
   ratchet ceilings may tighten, never rise (the em-dash ratchet is at ceiling,
   so the pass must not add a single em-dash); content-drift grep — citation
   keys, numbers, figure/table references byte-identical before and after;
   AI-tells auditor clean on the diff.
4. **Review interface:** the recompiled PDF and the PR diff; you accept or
   reject per section (ticket 0243, Action 4).

## Cross-project voice rules folded in

1. **Anchor-first** (AEDIST 0522): no full pass before you bless the anchors.
2. **Plain verbs** (AEDIST voice memory): you never write formal-cliché verbs —
   "accord with", "align with", "serves to underscore" are out; "matches",
   "bears this out", "shows" are in.
3. **Sole-author weighting** (chemin-de-voix corpus rule): co-authored texts
   carry a mixed-voice signal, so the few-shot set weights your sole-author
   passages highest — Ha-Duong 2009 "What is the Price of Carbon?" and
   Ha-Duong 2001 "Transparency and control" — with the first-author co-authored
   anchors (2009 leakage, 2003 ozone, 2007 IPCC, 2004 bounding) as secondary
   evidence.
