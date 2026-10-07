# State

Last updated: 2026-10-07T20:49Z

## Current goal

**REL literature review — the only work on a clock, due ~2026-12-06.** 0700 tracks it; the research plan is approved (#1558).
Stage-2 screening and the discipline catch-up are done and the REL view is final for now (7,499 included); the next step is the review itself (see below). 0701 (article outline, revisable) and 0705 (Œconomia non-overlap) remain open.

## REL workstream

The dated 2025–2026 catch-up ran on OpenAlex, ISTEX and World Bank; Scopus was unavailable.
The analytic corpus is unfrozen, with merged/refined views pinned at 33,344 works;
annual series stop at 2025, while 2026 is partial.
Two-stage ICF screening of the pool (1733): stage 1 (design B) finished with the joint drop threshold at 0.90; stage 2 done for 158,636 works (judges: Opus for the t1530 works; Sol, then Fable and Opus on the unsure, for the rest), labels imported into `icf_screen` (1995).
Pool-wide ICF labels: icf 14,452, aux 94,060, out 49,683, unsure 5,400, pending stage 2 296 (accepted residue), unscreened 59.
Works without an abstract (8,207 icf or unsure) count in the bibliometric analysis only and are never deleted.
Discipline catch-up (1842): `rel_dimensions.csv` holds 11,645 works (all icf or unsure with an abstract); gold-set contribution kappa 0.790 unweighted; cost about USD 12.3 plus an unexplained USD 0.54 key-usage rise (may rise if an abandoned Batch bills).
REL view (1843), 389,291 works: seriousness_excluded 39,115, icf_excluded 335,652, icf_pending 351, discipline_pending 5,894 (all without abstract), discipline_excluded 780 (upper bound: Opus v2 over-excludes applied finance), included 7,499.
The Fable audit of a stage-2 sample is set aside by author decision (1733), not measured.
Open: 1830 and 1733 (closing).
Then: Gavard/Schoch; DAG and independent EconLit/OpenAlex searches; 61-journal contents pilot, South/languages (including BRICS), versions and PRISMA; then map and synthesis.

## JETP migration

The JETP ledger, observatory and research outputs moved to
[MinhHaDuong/JETP-observer](https://github.com/MinhHaDuong/JETP-observer).
The legacy DVC store is retained for historical recovery.

## Status
<!-- generated 2026-10-07T20:49Z · as of 397613e0 -->

**Tickets:** 42 ready · 54 blocked · 10 awaiting author — `erg ready tickets/` for full list
  next: 0272 Extract shared derive_companion_path() helper f… · 0273 load_cluster_labels() ignores --input, reads cl…
**In flight:** no open PRs
**Recent (first-parent):**
  397613e0 Merge pull request #1708 from MinhHaDuong/close-trackers
  c8f7c15b Merge pull request #1707 from MinhHaDuong/docs-rel-close
  c93c8701 Merge pull request #1706 from MinhHaDuong/t1842-rerun-152

## Corpus and submissions

- The Œconomia submission is archived as tags `v1.0-submission` and `v1.1-oeconomia-revised`; its branch is deleted (rejected 2026-09-16).
- The data paper is published; v2 remains immutable at tag `rdj26561-revision1` (`9af9dc08`).
- V3 is unfrozen: Flag 5 publishes a non-removing per-language semantic distance; the Padme artifact is current and the 33,344-row refined corpus is unchanged.
