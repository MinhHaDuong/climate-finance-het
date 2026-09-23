# Astra review of PR #1449, round 1 (2026-09-22)

Reviewer: GPT-6 Astra through the Codex CLI, run by the author with the `review-pr` skill; posted on the PR under the author's login. Reviewed head `7d891e76`. Archived verbatim; dispositions in `astra-round1-response.md`.

## Review body

Review round 1 — **changes requested in the design contract** (posted as comments; no merge action).

Reviewed `7d891e7671ca58fe68e855b0f11cc228cc529f64`, including the language/translation update added during review. Five inline findings identify contracts that cannot represent existing data or reverse an adjudication. This is a design-only review; deferred implementation and the planned backend-document rewrite are not findings.

Validation:
- Direct checks against the committed manifest, financial events, timing records and plan lines support the examples.
- `make lint`: 338 passed, 10 skipped.
- `make check-fast`: package suite 25 passed; main suite 2111 passed, 13 skipped, 1 failed. The failure is the already-reported missing pinned commit `3b432ef3` in `test_reviewed_evidence_records_are_distinct_non_aggregate_and_traceable`.
- `make check`: stopped at preflight because corpus artifacts and the reranker cache are not materialized, and the sandbox restricts sockets/Git administration. Full-suite success is not claimed.
- Tests ran at `c6091a39`; the subsequent diff to the reviewed head changes only this Markdown document (language metadata and §12), and was inspected separately.

Verdict roster:
- Correctness: request-changes.
- Consistency: request-changes.
- Scope: approve; all six changed files belong to the stated design scope.
- Red-team: request-changes.
- Doc-propagation: request-changes.

All perspectives reported; duplicate findings were consolidated. Review workflow: local `review-pr` skill; its Sonnet model is unavailable, so the panel used the available session model.






## Inline findings

### docs/jetp-ontology.md:239 (comment 4073624177)

[P1] Separate retrieval identity from content identity

Correctness + red-team; high confidence. `sha256` cannot key a table defined as one retrieval per row while preserving the existing manifest. `data/jetp/manifest.csv` contains 314 rows but only 264 distinct nonempty hashes: nine hashes occur twice and 41 failed retrievals have no hash. For example, `zaf-jet-implementation-plan-2023-2027` has a collected retrieval at `2026-09-11T20:39:00Z` and a `not_modified` retrieval at `20:42:35Z` with the same SHA. The proposed primary key either rejects these rows or discards retrieval provenance, contrary to the unchanged-content migration. Please give retrievals their own identifier, with a nullable content hash, or separate content objects from retrieval history. Cover repeat retrievals, failed fetches and mirrors in the migration contract.

### docs/jetp-ontology.md:430 (comment 4073624183)

[P1] Resolve supersession before filtering for accepted decisions

Red-team + consistency; high confidence. Serving the newest accepted row does not revoke a false match: if A accepts line L → agreement X and a reviewer appends B (`status=rejected`, `supersedes=A`), A remains the newest accepted row. The erroneous identity link still affects counts; a rejected document-deduplication decision can likewise continue suppressing extraction. Please define the effective terminal decision before testing acceptance, including the distinction between a pending candidate and definitive revocation. The contract needs to make accepted A → rejected B remove the previously accepted relation even when there is no replacement identity.

### docs/jetp-ontology.md:248 (comment 4073624190)

[P2] Store each party's role on its agreement relation

Consistency; high confidence. `party_in` is specified as a relation 'with role', and migration step 4 requires funder/channel roles, but this exhaustive relations schema has no role column or companion role table. `parties.kind` is not an agreement-specific role: one organisation can fund one agreement and channel another. For the existing `Canada via World Bank and ADB` record (`data/jetp/events.csv:274`), three party links retain the organisations but lose who funded and who channelled the money. Please add an agreement-specific role field or association table, allowing multiple roles per party/agreement.

### docs/jetp-ontology.md:249 (comment 4073624196)

[P2] Preserve event timing separately from the reporting cutoff

Correctness + doc-propagation; high confidence. A single `date`/`date_role`/`date_precision` cannot replace the existing timing facts losslessly. `data/jetp/event-timing.csv:272` records approval during 2022 (bounds `2022-01-01`–`2022-12-31`), a reporting cutoff of `2025-11-30`, and report date `2025-12-02` for `idn-approved-mrt-north-south-jica-2025`. Choosing either approval time or cutoff loses the other; document publication metadata cannot recover that cutoff. These fields are separately served by `scripts/jetp/_observatory_data.py:53–69`. Please retain a timing relation or independent role-specific dates/bounds before retiring `event-timing.csv`; duplicating the amount for each date role also needs explicit grouping to avoid double counting.

### docs/jetp-ontology.md:193 (comment 4073624203)

[P2] Allow unmatched plan lines to carry perimeter membership

Consistency; high confidence. Section 6 promises to migrate `ruptl` to `member_of` a RUPTL perimeter, but this relation only accepts project, asset or agreement subjects. The current plan table has 230 `ruptl=YES`, `reconciliation_status=plan_only` rows without canonical identities; `data/jetp/plan-projects.csv:2` (`idn-cipp-bioenergy-001`) is one example. The proposed domain forces either dropping their membership evidence or minting identities without the required reviewed matches. Please permit `line` as a membership subject, or specify a typed line observation and its migration mapping.

