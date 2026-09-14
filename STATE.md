# State

Last updated: 2026-09-14T12:30Z

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

Historical/bilateral audit **0735** and tomorrow's pilot preparation land through
**PR #1347**; 0735 closes with that merge. Selection/design-tracker **PR #1348**
remains open at `63bb738ef8f8bf7c96db3201a8ce48b717136075`; use that pinned
version for selection inputs and the updated 0729 ticket until it lands.
Enough evidence exists to compare designs; no primary causal design is selected.
AFD first, KfW/FCDO complementary pilots are prepared **for a fresh session, not launched**.
Start with [the pilot handoff](docs/jetp-pilot-handoff-2026-09-14.md): exact branches,
source bundles, first tests, bounded budgets and three candidate comparisons.
For 15 September, the [prepared protocol](docs/jetp-pilots/2026-09-15/protocol.md)
and child tickets **0737–0739** supply baseline alternatives, sample rules,
output schemas and stopping decisions. Recommended: Sol high leads, Terra high
for bounded lender work; independent scientific review before design selection.
Next session: **15 September — start AFD 0737 / #1349**; KfW 0738 / #1350
and FCDO 0739 / #1351 are independent complements. Preparation freeze:
`1e532975`; use subsequent reviewed corrections on main if present. The handoff
contains a ready-to-use launch instruction. No pilot is scheduled or launched.
DVC source bytes are preserved in primary/local caches; remote replication remains
pending. Preserve the audit source worktrees and caches until recovery is
verified, including `/tmp/jetp-audit-0735` after its branch merges. Closing the
audit does not close replication ticket 0726 or design tracker 0729.

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
