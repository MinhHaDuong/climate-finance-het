# State

Last updated: 2026-07-27T08:30Z

## Current goal

**RDJ-26561 R&R — corpus frozen, three items to resubmission.** Tracker 0274,
due ~2026-10-20. Friday's queue landed (#1120 restructure/TF-IDF map/count-free
title, #1116 corpus v2, #1124–#1126). Corpus v2 **frozen** (author,
2026-07-27): the four outstanding OECD targets are phantoms or genuinely
offline, documented no_url — 0311/0312/0313 close on that, no rebuild.
Remaining: **0320** stale verification claim (paper 99.0% vs v2 97.0% —
factual error), **0283** letter reconciliation (list in ticket log) +
sign-off, **0292** archive scripts (blocks Zenodo repack), then 0274's
integration review against the ledger. Open author call: **0297** language
nulls at 4.0%, fixable to ~0.4%, but the fix is a Phase-1 rerun that moves
`lang_english_pct` — lands before the letter or after resubmission, not
between. Pre-resub dress rehearsal available: wide panel + external referees
(key fixed). Œconomia: awaiting editor; 0306/0309 parked.

## Status
<!-- refreshed 2026-07-27T08:30Z · as of 875c3203 -->
**Tickets:** 26 ready · 39 blocked · 2 awaiting author — `erg ready tickets/`
  next: 0320 verification claim · 0283 letter reconciliation · 0292 repack
**In flight:** PR #1127 (0317 + 0314), local `make check` green but for 0321
**New today:** 0319 snapshot date · 0320 verification claim · 0321 main red on
ruff + a tier-3 import (no CI workflows exist here — `make check` is local-only)
**Housekeeping:** stale dir `.claude/worktrees/t0066-null-csv-schema/`, not in
`git worktree list` — author to remove.

## Submissions

- RDJ-26561 (RDJ4HSS data paper): R&R round 1, due ~2026-10-20
- Œconomia manuscript v2.0.5: resubmitted 2026-07-21, awaiting editor

## Corpus (v2, built 2026-07-24, frozen 2026-07-27)

- 8 sources; 43,179 unified → 33,344 refined; 38,736×1024 embeddings;
  1,087,209 refined citations; core (≥50 cites) 2,644
- Citation coverage 40/47/69% by period (all-works denominator); DOI carriage
  46→85% is what drives the gradient
- Keydocs: UNFCCC 225 + OECD 33; pools DVC-pushed; 1992 Manual OCRed
- data/book/riomarkers/: 6 CRS zips (503 MB) — book chapter, NOT the paper
