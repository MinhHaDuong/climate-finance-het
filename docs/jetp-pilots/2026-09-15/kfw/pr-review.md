# Review-pr round 1 — PR #1375, ticket 0738

**Panel verdict: APPROVE.** Five independent perspectives reported; none missing.
Reviewed implementation through `2eca971bdba217f811b7a4b72699f62569cf9605`.
No merge or primary causal-design approval is implied.

The correctness reviewer independently replayed all six calculation artifacts
byte-for-byte and inspected all 49,442 event rows. Consistency checked input and
source hashes and evidence-reference integrity. Scope confirmed the bounded
pilot, frozen sample and preserved nonresponse. Red team independently checked
4,036 activities, 19,072 type-3 entries and 432 corrections, with no unsupported
exact date or historical-member count. Documentation review confirmed the
4,036/521/517 populations, sample/attempt denominators, original/rebased freeze
and explicit causal limitations. A separate scientific review checked originals,
sampling, historical inclusion/retention and comparator admissibility.

One nonblocking correctness observation was resolved before synthesis:

> consider: the equal-start test exercised an unused helper; checking emitted
> event fields would protect the actual output boundary more directly.

Commit `2eca971b` removes that helper and tests `events_for` directly. The original
reviewer inspected the change, reran all five acceptance tests and reaffirmed
approval. No calculation mapping or generated table changed. No dissent remains.

Validation evidence: five acceptance tests pass; deliberately naive mappings
produce the four intended failures. Final fast gate: **1,805 passed, 9 skipped**;
adherence: **330 passed, 15 skipped**. Full `make check`: **2,722 passed, 54 skipped,
9 sandbox-dependent failures**; all nine passed focused reruns with the required
network/worktree/UV environment access. This is not represented as a zero-exit
full-suite run. No unresolved regression remains; unchanged slow computation was
not rerun after removing an unused helper and strengthening a fast test.

Exit-criterion evidence:

- Naive/corrected mappings: `tests/test_jetp_kfw_pilot.py`, all five named tests;
  original red commit `761c0b72`, preserved by the selection-freeze tag.
- Frozen inputs and common tables: `input-manifest.json`, `selection.csv`, DVC
  pointers for units/events/coverage, and `evidence.csv` under the KfW pilot path.
- Mandatory cases: `cases.json`, `anomalies.csv`, `document-coverage.csv`, E13/E14
  originals and the report's four-case dispositions.
- Bounded acquisition: `acquisition-log.csv` units 1–16, four unused reserve units;
  ten sample cases explicitly not attempted. No reviewer source retrieval.
- Offline replay and gates: `scripts/analyze_jetp_kfw_pilot.py`, versioned
  documentary builder, `gate-results.md`; new DVC objects published.
- Independent reproduction/original checks: `verification.md` and this panel.
- Stage/design decisions: `report.md` gives NARROW/DEFER and exact missing
  documents; historical denominator, stage clocks and untreated comparators
  remain unestablished.

Verdict roster:

- Correctness: approve — high confidence; minor test suggestion resolved.
- Consistency: approve — high confidence.
- Scope: approve — high confidence.
- Red team: approve — high confidence within frozen-input scope.
- Doc propagation: approve — high confidence.
