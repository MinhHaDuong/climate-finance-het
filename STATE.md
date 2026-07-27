# State

Last updated: 2026-07-27T08:10Z

## Current goal

**RDJ-26561 R&R — corpus frozen, three items to resubmission.** Tracker 0274,
due ~2026-10-20. Friday's queue landed: #1120 (restructure + referee pass),
#1116 (corpus v2 integration), #1124, #1125. Corpus v2 **frozen** (author,
2026-07-27): the four outstanding OECD targets are phantoms or genuinely
offline, documented no_url — 0311/0312/0313 close on that basis, no rebuild.
Title settled: count-free *A Curated Multi-Source Corpus*. Remaining:
**0283** letter reconciliation (5 items vs the post-#1120 text) + sign-off,
**0292** archive scripts (blocks the Zenodo repack), then 0274's integration
review against the ledger. Open author call: **0297** language nulls at 4.0%
— fixable to ~0.4%, but the fix is a Phase-1 rerun that moves
`lang_english_pct`, so it lands before the letter or after resubmission, not
between. Œconomia: awaiting editor; 0306/0309 parked.

## Status
<!-- refreshed 2026-07-27T08:10Z · as of 4471da85 -->
**Tickets:** 24 ready · 39 blocked — `erg ready tickets/` for full list
  next: 0283 letter reconciliation · 0292 archive scripts / Zenodo repack
**In flight:** branch t0317-temporal-coverage (0317 + 0314 + 0319), no open PRs
**Done today:** 0317 coverage metric · 0314 Flag-6 hard guard · 0319 filed
**Housekeeping:** `.claude/worktrees/t0066-null-csv-schema/` is an unregistered
leftover dir (not in `git worktree list`) — author to remove.

## Submissions

- RDJ-26561 (RDJ4HSS data paper): R&R round 1, due ~2026-10-20
- Œconomia manuscript v2.0.5: resubmitted 2026-07-21, awaiting editor

## Corpus (v2, frozen 2026-07-24)

- 8 sources; 43,179 unified → 33,344 refined; 38,736×1024 embeddings;
  1,087,209 refined citations; core (≥50 cites) 2,644
- Citation coverage 40% / 47% / 69% across the three periods (all-works
  denominator); DOI carriage 46% → 85% is what drives the gradient
- Keydocs: UNFCCC 225 + OECD 33; pools DVC-pushed; 1992 Manual OCRed
- data/book/riomarkers/: 6 CRS zips (503 MB) — book chapter, NOT the paper
