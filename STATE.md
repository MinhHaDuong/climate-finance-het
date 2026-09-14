# State

Last updated: 2026-09-14T10:59Z

## Current goal

**REL literature review — the only work on a clock, due ~2026-12-06.**
Ticket 0700 is the tracker; 0701 (agreed outline) and 0705 (Œconomia
non-overlap guard) are the two ready children, the rest queue behind them.
RDJ-26561 rev. 1 and Œconomia v2.0.5 have been with their editors since late
July — nothing to do but wait.

## JETP checkpoint

Local observatory and scientific export corrections: PR #1343; validation and
scope in `docs/jetp-observatory-mvp-validation.md`. 383 named records, 21 unnamed
slots, 301 registered sources, 97 historical closed operations. Public release,
hosting and monthly editions remain 0726–0728; this is not a causal result.

Evidence audits are checkpointed in open PRs **#1347** (historical/bilateral
sources) and **#1348** (selection chronology and design tracker). Enough evidence
exists to compare designs; no primary causal design is selected. AFD first,
KfW/FCDO complementary pilots are prepared **for a fresh session, not launched**.
Start with [the pilot handoff](docs/jetp-pilot-handoff-2026-09-14.md): exact branches,
source bundles, first tests, bounded budgets and three candidate comparisons.
DVC source bytes are preserved in primary/local caches; remote replication remains
pending. Preserve caches and the open worktrees until recovery is verified.

Pilots feed **0729**, then **0730 → 0732** analysis and short paper. **0731** data
paper follows the citable release; **0733** is the long paper with Christophe.
Strategy: `conception/jetp-observatory-and-papers-plan.md`.

## Status

Use `erg ready tickets/` for live work. The separate prose PR #1322 is outside
this checkpoint. Programme tracker 0725 stays open. MVP slice 0734 passed its independent
evidence gate (10/10 criteria); closure applies only to the local preview. Existing untracked `data/book/` is user material, preserved.

## Submissions

- **REL literature review — INVITED, scope agreed, due ~2026-12-06. HIGH
  PRIORITY.** *Reviews of Economic Literature* (Stanford UP, open access);
  proposed 2026-08-06, accepted 2026-08-21 — **acceptance of a proposal is not a
  promise of publication**. Agreed scope, the four accounting controversies and
  the timeline are in ticket 0700. Hard constraint declared to the editor: no
  shared text or analyses with the Œconomia manuscript — same corpus, opposite direction.
- RDJ-26561 rev. 1 resubmitted 2026-07-29; Œconomia v2.0.5 resubmitted 2026-07-21 — both awaiting editor

## Corpus (v2, built 2026-07-24, frozen 2026-07-27)
- 8 sources; 43,179 unified → 33,344 refined; 38,736×1024 embeddings;
  1,087,209 refined citations; core (≥50 cites) 2,644
- Citation coverage 40/47/69% by period (all-works denominator), driven by
  DOI carriage 46→85%
- Keydocs: UNFCCC 225 + OECD 33; pools DVC-pushed; 1992 Manual OCRed
- data/book/riomarkers/: 6 CRS zips (503 MB) — book chapter, NOT the paper
