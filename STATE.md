# State

Last updated: 2026-07-23T19:43Z

## Current goal

**RDJ-26561 (data paper) R&R round 1 — prose complete.** Tracker **0274**,
deadline ~2026-10-20. Session 2026-07-23: 16 PRs merged, 14 tickets closed
(0275-0281, 0286, 0287, 0300, 0301, 0304, 0307, 0310). All referee/editor
remarks covered in paper or letter material. Remaining: corpus-v2 rebuild
(`make corpus` on padme, with author → 0288 counts), author OECD browser
session (11 docs, ticket 0311 context), 0294 run report, **word-budget cut
pass ~4,100 → 2,500**, then **0283** response letter + Zenodo deposit (kit
ed04 ready) + resubmission. Œconomia: v2.0.5 resubmitted 2026-07-21 —
awaiting editor; next round folds in 0306/0309 (three-traditions claim,
null-artifact regen, l.305 metric).

### Also open (details live in the tickets)
- **0290/0291/0292** roar-filed: includes audit, Zotero pass, archive scripts.

## Status
<!-- generated 2026-07-23T19:43Z · as of 38a466a4 -->

**Tickets:** 18 ready · 38 blocked · 2 awaiting author — `erg ready tickets/` for full list
  next: 0272 Extract shared derive_companion_path() helper f… · 0273 load_cluster_labels() ignores --input, reads cl…
**In flight:** no open PRs
**Recent (first-parent):**
  38a466a4 Merge pull request #1112 from MinhHaDuong/t277-cite-quality
  096a3ff8 Merge pull request #1111 from MinhHaDuong/t310-fix-stub-cluster
  4ac529b2 Merge pull request #1109 from MinhHaDuong/t310-lit-confirmations

## Corpus (v1.1.1)

- 6 sources; 42,922 raw → 31,713 refined works, 38,479 embeddings, 968,871 citations
- v1.1.2 being re-generated on padme (GROBID reference extraction + DOI matching)

## Health

check-fast 1081+ / lint 165 green on merged branches. Known real-data
failures: language-null 4.1% (0297, amplified by 0304 harvest),
test_bias_flag flaky under xdist, divergence S2_energy. 16 agent worktrees
(merged branches) awaiting next /molt GC. data/catalogs/{unfccc,oecd}_works.csv
untracked pending 0288 rebuild + dvc commit.

## Next actions

- Corpus-v2 rebuild on padme (author + 0288); then 0311 anchors, 0305 DOI
  resolution, 0294 run report.
- Cut pass + **0283** response letter; author: OECD exports, Zenodo deposit.
