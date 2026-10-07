# State

Last updated: 2026-10-07T11:50Z

## Current goal

**REL literature review — the only work on a clock, due ~2026-12-06.** 0700 tracks it; the research plan is approved (#1558).
Stage-2 screening of the pool closed on 2026-10-07; the next step is importing its labels (1995). 0701 (article outline, revisable) and 0705 (Œconomia non-overlap) remain open.

## REL workstream

The dated 2025–2026 catch-up ran on OpenAlex, ISTEX and World Bank; Scopus was unavailable.
The analytic corpus is unfrozen, with merged/refined views pinned at 33,344 works;
annual series stop at 2025, while 2026 is partial.
Two-stage ICF screening of the pool (1733): stage 1 (design B) is finished with the joint drop threshold at 0.90; stage 2 is done for 158,636 works (icf 11,982 / aux 92,261 / out 49,138 / unsure 5,255), with 296 works left unlabelled as accepted residue.
Works without an abstract (icf 2,281, unsure 5,141) count in the bibliometric analysis only and are never deleted.
**Nothing is imported into `icf_screen` yet**: ticket 1995 carries the import; the labels live in `~/rel_pool_runs` on padme, outside git.
Open: discipline catch-up (1842), `no_abstract` facet (1843), PRs 1660 and 1662.
Then: Gavard/Schoch; DAG and independent EconLit/OpenAlex searches; 61-journal contents pilot, South/languages (including BRICS), versions and PRISMA; then map and synthesis.

## JETP migration

The JETP ledger, observatory and research outputs moved to
[MinhHaDuong/JETP-observer](https://github.com/MinhHaDuong/JETP-observer).
The legacy DVC store is retained for historical recovery.

## Status
<!-- generated 2026-10-01T10:46Z · as of de6f8e6f -->

**Tickets:** 73 ready · 86 blocked · 14 awaiting author — `erg ready tickets/` for full list
  next: 0272 Extract shared derive_companion_path() helper f… · 0273 load_cluster_labels() ignores --input, reads cl…
**In flight:** 3 open PRs, oldest #1660 0d
**Recent (first-parent):**
  de6f8e6f Merge pull request #1674 from MinhHaDuong/t1940-handoff
  18c29376 Merge pull request #1673 from MinhHaDuong/t1955-file-ontology-ticket
  8757f33c Merge pull request #1672 from MinhHaDuong/t1940-ontology-bound

## Corpus and submissions

- The Œconomia submission is archived as tags `v1.0-submission` and `v1.1-oeconomia-revised`; its branch is deleted (rejected 2026-09-16).
- The data paper is published; v2 remains immutable at tag `rdj26561-revision1` (`9af9dc08`).
- V3 is unfrozen: Flag 5 publishes a non-removing per-language semantic distance; the Padme artifact is current and the 33,344-row refined corpus is unchanged.
