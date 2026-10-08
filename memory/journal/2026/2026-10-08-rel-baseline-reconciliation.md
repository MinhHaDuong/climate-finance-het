# REL baseline reconciliation

PR 1710 closed baseline integration ticket 1655 after two byte-identical rebuilds on padme. The dedicated REL pool has 389,291 works; the fully graded view includes 7,499 works / 7,484 observed families. The complete-year research window has 5,354 works / 5,339 families. These counts describe baseline membership, not final saturation.

Fresh-worktree bulk provisioning needed a separate rel-pool-data fetch for the screening cache. Ordinary gates passed. The optional local-CI helper was unavailable because this project has no ci-local/common.sh. The initial raid full-gate preflight also needed the existing primary reranker cache copied into the populated worktree and execution outside the socket/Git-restricted sandbox; a full baseline gate was then started.

Incremental chaining screening remains ticket 1654; final dating, provenance package and historical identity reconciliation remain 1656. The audit waiver and accepted baseline residues were recorded as author decisions, not successful checks. Review identity limitations and raw attempts are retained in docs/reviews/pr1710.md.

Roar examined 17 recently merged PRs, parsed six close claims across four PRs and found zero dropped or unresolved claims; three PR bodies had no recognized ticket line. Attribution backfill found no covered earlier records (appended=0, no-match=0, unresolved=0). Related stale upper-bound language is already assigned to freeze ticket 1656. Parent 0700 remains open while 1654/1656 remain open.
