# REL corpus completion

Reviewed by GPT-6 Astra at high effort on 8 October 2026. This document closes
the baseline integration of ticket 1655; it does not freeze the REL corpus.

## Amendment of 2026-10-10

The sequence below was rescoped by the author on 2026-10-10. Step 2 (citation
chaining and incremental screening) no longer includes screening: the staged
screening is retired and new works are scored by the pipeline redesign. The order
of work is now the staged plan in `docs/rel-pipeline-redesign-2026-10-10.md`,
section 12 (tracker 2070). Steps 3 and 4 (reconciliation and freeze, ticket 1656)
follow the end-to-end run and chaining round two. The text below is kept as the
record of the baseline reconciliation of 2026-10-08.

## Corrected execution sequence

1. **1655 — baseline integration.** Restore the pinned inputs on padme and
   rebuild the pool, venues and REL view. Reconcile the tracker with its merged
   children, the accepted screening residues and the final-audit waiver.
2. **1654 — citation chaining and incremental screening.** Archive the seed
   roster, including retained ICF, uncertain works and sentinels, and record
   why each seed is used. Do not restrict discovery to the fully graded REL
   set: missing abstracts or discipline grades must not hide citation routes.
   Run backward and forward searches; retain provenance, exact queries,
   pagination and interruptions. Deliver all retrieved records under the
   intake contract, merge them and screen new or re-keyed works with the
   existing procedures, preserving old labels. Refresh venue and discipline
   information for additions. Decide the eligible, duplicate-aware yield
   before advancing each round's frontier. Run two rounds; run a third if
   round two adds admissible works. Record unresolved references and the
   evidence for stopping, including any further chaining required by the
   protocol's closure rule.
3. **1656 — counting and coverage reconciliation.** Reconcile version hints,
   unresolved work families, unmatched historical screening keys, document
   types, publication dates and first
   dissemination years. Report complete annual series through 2025 and 2026
   separately. Reconcile the final search date with the dated registries:
   `config/rel_review.yaml` still says 2026-09-28, preceding later searches;
   it is retained here to reproduce the baseline. Resolve the catalogue-pin
   versus `dvc.lock` discrepancy without regenerating the pinned catalogue.
   Account for inaccessible/partial sources, missed sentinels, language and
   regional coverage, and aggregator records assigned tier C. Existing
   decisions permit declared gaps; they do not establish saturation.
4. **1656 — freeze deliverables.** Rebuild final PRISMA counts from registries
   and tables at consistent units; update the protocol, methods and sensitivity
   results. Archive configurations, model routes, prompts, decisions and raw
   outputs. Include the dated external code snapshot and its script-to-artifact
   map: 63 payloads comprise 50 Python files, 6 shell files and 7 communications
   files (56 code files; 65 total files including README and MANIFEST). These
   inventory counts do not establish executed runs; committed input builders
   alone do not reproduce the complete production history. Publish a manifest of file
   hashes, code revision and DVC pointers and verify reconstruction in a clean
   populated checkout.

Each execution conversation handles one ticket. The 1654 work owns the merge,
screening and reconciliation of its additions; it does not reopen 1655.
Checks follow AGENTS.md: documentation changes use `make check-fast` and
`make lint`; domain changes add the affected domain gate; shared pipeline or
test-selection changes use `make check` alone. Data and domain/full gates run
in populated clean padme worktrees. Each change lands through a PR.

## Screening evidence and limits

The baseline uses the actual dated screening sequence recorded in 1733 and
1995: design B with a joint drop threshold of 0.90; Opus for the Southern
pilot, Sol for the other stage-2 works, then Fable and Opus corrections of
uncertain cases; discipline through the separate 1842 catch-up. Models,
run ids and prompt hashes remain in the append-only tables. This is not a
claim that every record received identical prompts or judges.

The final stage-2 sample audit was **waived by the author on 7 October**, not
passed. Fable's recorded agreement applies to pre-correction labels. The
discipline gold-set agreement is a separate measurement. Automated discipline
exclusions have an observed over-exclusion risk; their count is not a proven
upper bound on true exclusions.

There are 296 accepted stage-2 residues and 59 accepted unscreened title-less
works. The no-abstract policy also leaves a separate discipline-pending
inventory. Such works are designated for bibliometric use by policy but are
not automatically members of the fully graded REL set. Counts below distinguish
ICF eligibility from final membership and research within the window. Families
are observed groups linked by explicit `version_hint`, not a certification
that every version pair has been found.

The committed builder criterion is met by `corpus_rel_pool.py`,
`corpus_icf_stage1_input.py`, and `corpus_icf_stage2.py`, with existing tests
for deduplication, unscreened/pending selection, title-less residues, chunking,
answer imports and audit sampling. The broader reproduction package remains
the responsibility of 1656.

## Astra review disposition

- Circular screening ownership: transferred to 1654 in its ticket and the
  intake contract.
- Work/family/window ambiguity: separate measurements below, using the final
  `reasons` counts rather than the ICF-only `rel` counts.
- No-abstract pending inventory: explicitly separated from retained works.
- Audit waiver and differing prompts/judges: recorded as limitations.
- Stale hashes and sensitivity: baseline rebuilt; final PRISMA update in 1656.
- Search date, coverage and unresolved versions: explicit 1656 obligations.
- Claimed numerical upper bound: replaced by an over-exclusion risk.
- Tested builders versus external production scripts: distinguished above.

## Measured baseline on padme

Code: `83af92b3`. Commands: `make data`, `make rel-pool-data`,
`make rel-pool`, `make rel-venues`, `make rel-view`. The initial local cache
lacked the screen artifact; the authoritative DVC pull restored all four files.
Detailed counts, per-delivery merge evidence, sensitivity and SHA-256 hashes
are in [the baseline evidence](rel-corpus-baseline-2026-10-08.json).

| Population | Works | Observed families |
|---|---:|---:|
| Pool | 389,291 | 389,261 |
| Seriousness excluded | 39,115 | 39,114 |
| ICF excluded | 335,652 | 335,642 |
| ICF pending | 351 | 350 |
| Discipline excluded | 780 | 779 |
| Discipline pending | 5,894 | 5,892 |
| Fully graded inclusion, all types/years | 7,499 | 7,484 |
| Fully graded research, complete-year window | 5,354 | 5,339 |
| Discipline-pending research, complete-year window | 2,788 | 2,786 |

Both the status partition and exclusion-reason partition sum to 389,291;
the family-reason partition sums to 389,261. All 11,645 dimension rows match
the pool, with no unused or disagreeing rows. All 7,499 fully graded works
have abstracts; 55 retain an ICF uncertainty flag. The 5,894 discipline-pending
works have no abstracts and remain outside this included set. Of 296 stage-2
residues, four already fail seriousness; 292 plus 59 unscreened works account
for the 351 ICF-pending works. There are 549 unresolved version hints whose
DOIs are absent from the pool.

Sensitivity, all types/years: default 7,499 works / 7,484 families; dropping
MDPI, Frontiers and Hindawi gives 7,244 / 7,229; excluding unknown venues
gives 6,437 / 6,422. These are baseline measurements, not final PRISMA counts.
The evidence JSON faithfully preserves generated warnings, including the old
"upper bound" wording; the interpretation above supersedes that wording.

## Verification

`make check-fast`: 2,169 passed, 7 skipped; `make lint`: 347 passed,
7 skipped. The skips are those selected by the ordinary gates, not evidence
for a domain or full gate. A supplemental `erg check tickets/` reports the
existing 1183 dependency on unknown 1182; the same violation reproduces on
main `83af92b3`. No new ticket IDs are introduced by this change.

A second `make rel-view` produced byte-identical `rel_view.csv`,
`rel_counts.json` and `rel_sensitivity.csv`. No screen, configuration or DVC
pointer was changed during baseline reconciliation.

Astra approved the implemented baseline reconciliation after independently
checking all ten artifact hashes and the embedded counts, merge report and
sensitivity against the generated files. The historical screen also has 1,156
unmatched label rows, grouped as 818 titled and 277 title-less works not in
the current pool; these are preserved in the table and assigned to 1656 for
key/provenance reconciliation. They are not added to the current pool counts.
