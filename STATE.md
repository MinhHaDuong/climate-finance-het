# State

Last updated: 2026-09-16T15:41Z

## Current goal

**REL literature review — the only work on a clock, due ~2026-12-06.**
Ticket 0700 is the tracker; 0701 (agreed outline) and 0705 (Œconomia
non-overlap guard) are the two ready children, the rest queue behind them.
The RDJ-26561 data paper is published. Its corpus v2.0.0 source and archive
remain fixed at the pushed annotated tag `rdj26561-revision1`; development on
the corpus is open again on `main` for v3. Œconomia v2.0.5 remains with its
editor.

## JETP checkpoint

The backend migration train is accepted and tracker 0760 is closed. Tickets
0761–0770 and the 0726–0728 handoffs are merged; programme tracker 0725 remains
open. The recoverable MVP baseline is retained, four country migrations have
documented dispositions, publication provenance is sidecar-based, and the
prepared `2026-09` and fact-unchanged `2026-10` packages restore offline with
their routes and downloads. Both interruption and validation-rejection paths
preserve the earlier package byte-for-byte. No site deployment occurred.

The AFD, KfW and FCDO lender pilots establish bounded measurement findings, not
a JETP causal effect. Reviewed branches add the completed 0736 selection audit,
0729 CAUSAL DEFER and 0814 DEFER. The author has selected a JETP-only,
non-causal comparative measurement programme: protocol0816, source census0817,
country ingestion0818–0821, frozen snapshot0822, statistics0730, key figure0823,
MVP extension0824 and paper0732. Current scientific framing:
`conception/jetp-short-paper-framing-2026-09-15.md`: progression of transition
functions, public/private finance, and histories of the same operations; one
dominant result and three coordinated figure panels. Next 0816 deliverable is a
diagnostic joinability matrix from existing evidence. The v3 worktree protocol
is unapproved; the source census and primary analysis are not frozen.

Current iterative milestones: **M1** is a sourced four-country inventory of
proposed JETP objects; **M2** records the documentary state of each object with
date role, source and uncertainty; **M3** reconciles finance and histories only
where the evidence supports it. The MVP exposes the same evidence layers and
their coverage; it is not a parallel datastore or proof of an analytical result.

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
- RDJ-26561 data paper published; corpus v2.0.0 preserved at the pushed tag
  `rdj26561-revision1` (`9af9dc08`).
- Œconomia v2.0.5 resubmitted 2026-07-21 — awaiting editor.

## Corpus (v2 frozen release; v3 development unfrozen 2026-09-16)
- The published v2 corpus remains immutable at `rdj26561-revision1`; new
  pipeline, data and documentation changes belong to the v3 lineage on `main`.
- V3 now computes Flag 5 as a non-removing semantic-distance diagnostic using
  per-language centroids (global fallback below 30 works). The distance is
  published as `semantic_outlier_dist`; the rebuilt extended catalog is on
  Padme, while the 33,344-row refined corpus remains byte-identical.
- 8 sources; 43,179 unified → 33,344 refined; 38,736×1024 embeddings;
  1,087,209 refined citations; core (≥50 cites) 2,644
- Citation coverage 40/47/69% by period (all-works denominator), driven by
  DOI carriage 46→85%
- Keydocs: UNFCCC 225 + OECD 33; pools DVC-pushed; 1992 Manual OCRed
- data/book/riomarkers/: 6 CRS zips (503 MB) — book chapter, NOT the paper
