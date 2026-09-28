# State

Last updated: 2026-09-28T16:56Z

## Current goal

**REL literature review — the only work on a clock, due ~2026-12-06.** Ticket 0700
is the tracker; 0701 (outline) and 0705 (Œconomia non-overlap guard) are ready.

## JETP checkpoint

No deployment; no causal model (0729 DEFER). M1a ticked (#1448). Ledger
migration 0870 (ontology v2): all 19 children are merged and closed; 0878
retired the legacy tables and readers (#1559, #1560). The local MVP now serves
64 reviewed projects and 315 separate agreements; nine changed JSON views
were approved by the author. **Next: 0870 integration review** — combined diff,
full suite, ZAF/VNM browser paths, final counts, routes and table coverage.
The MVP is not published. `make all` is blocked by corpus report ticket 0673,
being handled in another session.

## Process pilot

Since #1469, PRs verify in proportion to risk (AGENTS.md § Verify).
Review time to merge, follow-up fixes, and `/lair` failures after a week or two.

## Status
<!-- generated 2026-09-28T16:56Z · as of 93ba3edc -->

**Tickets:** 60 ready · 61 blocked · 11 awaiting author — `erg ready tickets/` for full list
  next: 0272 Extract shared derive_companion_path() helper f… · 0273 load_cluster_labels() ignores --input, reads cl…
**In flight:** no open PRs
**Recent (first-parent):**
  93ba3edc Merge pull request #1558 from MinhHaDuong/t0701-rel-research-plan
  7e37172c Merge pull request #1560 from MinhHaDuong/t0878-close-ticket
  6c718014 Merge pull request #1559 from MinhHaDuong/t0878-retire-legacy

## Corpus and submissions

- The data paper is published; v2 remains immutable at tag `rdj26561-revision1` (`9af9dc08`).
- V3 is unfrozen: Flag 5 publishes a non-removing per-language semantic distance; the Padme artifact is current and the 33,344-row refined corpus is unchanged.
