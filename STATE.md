# State

Last updated: 2026-09-17T15:37Z

## Current goal

**REL literature review — the only work on a clock, due ~2026-12-06.** Ticket 0700
is the tracker; 0701 (outline) and 0705 (Œconomia non-overlap guard) are ready.
The RDJ-26561 data paper is published; Œconomia v2.0.5 remains with its editor.

## JETP checkpoint

Backend migration and local observatory baseline are on `main`, no deployment.
The 0736 audit and the 0729/0814 DEFERs record that no credible assignment
mechanism or untreated comparison supports a causal JETP estimate; the author
chose a non-causal comparative programme. M1a is accepted on `main` (four frozen
inventories, 2,164 rows, six layers, unknowns shown, no identity fusion); its
session closed 2026-09-17, gate green, `t0820-jetp-discriminator-packet` pushed
for the M1b resume on doudou. 0833 is ready for the bounded M1b overlay; live
refresh and match resolution stay M2; tracker 0725 stays open through the paper.
Pending author decisions: the M1b taxonomy (0833, first action) and the 0732
angle (advisor recommendation logged in the ticket: angles 1 and 2, angle 3 as
an M2 child of 0725). The manual browser acceptance passed on padme on
2026-09-17 (97 historical records); Playwright is now a dev dependency, and
`uv run playwright install chromium` fetches its browser once per machine.

## Status
<!-- generated 2026-09-17T15:37Z · as of 3a5c32c9 -->

**Tickets:** 54 ready · 51 blocked · 9 awaiting author — `erg ready tickets/` for full list
  next: 0272 Extract shared derive_companion_path() helper f… · 0273 load_cluster_labels() ignores --input, reads cl…
**In flight:** no open PRs
**Recent (first-parent):**
  3a5c32c9 Merge pull request #1425 from MinhHaDuong/state-2026-09-17
  2969e72e Merge pull request #1424 from MinhHaDuong/housekeeping-state-2026-09-17-m1a
  f796644a chore(jetp): close delivered M1a ticket (#1423)

## Corpus and submissions

- Published v2 remains immutable at tag `rdj26561-revision1` (`9af9dc08`).
- V3 is unfrozen: Flag 5 publishes a non-removing per-language semantic distance; the Padme artifact is current and the 33,344-row refined corpus is unchanged.
- REL is invited; Œconomia v2.0.5 was resubmitted on 2026-07-21.
