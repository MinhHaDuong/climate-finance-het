# State

Last updated: 2026-09-17T13:04Z

## Current goal

**REL literature review — the only work on a clock, due ~2026-12-06.** Ticket 0700
is the tracker; 0701 (outline) and 0705 (Œconomia non-overlap guard) are ready.
The RDJ-26561 data paper is published; Œconomia v2.0.5 remains with its editor.

## JETP checkpoint

The backend migration and recoverable local observatory baseline are on `main`;
no site deployment occurred. The 0736 selection audit, 0729 causal DEFER and
0814 feasibility DEFER preserve the evidence that no credible assignment
mechanism, common operational time zero or untreated comparison supports a JETP
causal-effect estimate; the author chose a JETP-only, non-causal comparative
programme. M1a is accepted on `main`: four frozen country inventories, 2,164
rows over six source layers with editions and cutoffs, unknowns displayed
separately, no identity fusion; its session closed 2026-09-17 with the full gate
green (3 070 project tests) and `t0820-jetp-discriminator-packet` pushed for the
M1b resume on doudou. Ticket 0833 is ready for the bounded M1b overlay (stable
IDs, common taxonomy, sourced `same_as` and `component_of` only); live refresh
and match resolution remain M2; tracker 0725 stays open through the short paper.
Author decisions pending: the M1b taxonomy (0833, first action) and the angle of
0732, whose ticket logs the advisor's recommendation (angles 1 and 2 in one
paper, angle 3 as an M2 child of 0725). The manual browser acceptance
(`tests/browser/jetp_observatory.py`) has not run on padme: Playwright is absent
from the project environment there; install it with `uv pip install playwright
&& playwright install chromium` where wanted, not with apt.

## Status
<!-- generated 2026-09-17T13:04Z · as of 2969e72e -->

**Tickets:** 54 ready · 51 blocked · 9 awaiting author — `erg ready tickets/` for full list
  next: 0272 Extract shared derive_companion_path() helper f… · 0273 load_cluster_labels() ignores --input, reads cl…
**In flight:** no open PRs
**Recent (first-parent):**
  2969e72e Merge pull request #1424 from MinhHaDuong/housekeeping-state-2026-09-17-m1a
  f796644a chore(jetp): close delivered M1a ticket (#1423)
  9ec04d92 feat(jetp): publish frozen M1a source inventories (#1422)

## Corpus and submissions

- Published v2 remains immutable at tag `rdj26561-revision1` (`9af9dc08`).
- V3 is unfrozen: Flag 5 publishes a non-removing per-language semantic distance; the Padme artifact is current and the 33,344-row refined corpus is unchanged.
- REL is invited; Œconomia v2.0.5 was resubmitted on 2026-07-21.
