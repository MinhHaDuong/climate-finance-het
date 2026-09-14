# Backend design review — 14 September 2026

Reviewed design: [`../jetp-backend-design.md`](../jetp-backend-design.md),
commit `962f4bb1ef65eaee564fa1f27cde1e8116c153f9`.
Input hashes, payload authorization and model metadata are in
[`inputs.json`](inputs.json).

Revision follow-up: [revision 2 response](revision-response.md) records the
subsequent design changes and research-sufficiency assessment. The panel findings
below describe revision 1 at the reviewed commit, not a review of revision 2.

## Outcome and independence

Both requested reviewers completed independent reviews and recommend **REVISE
before implementation**, while endorsing the storage architecture. Neither
received the other's report. The reviewed design remains unchanged; the repairs
below are the coordinator's recommendations, not applied changes or a merge gate.

- [Astra report](astra.md): `gpt-6-astra`, high reasoning effort; inspected the
  design and repository context read-only.
- [Fable report](fable.md): `claude-fable-5-1`, high effort; reviewed the approved
  packet with tools disabled. It contained the design, eight supporting files
  and CSV column headers, about 106 KB. The CLI confirms the requested Fable
  model and also reports auxiliary Haiku usage in its metadata.

Automatic approval review initially rejected the external Fable transfer. The
user then explicitly approved that exact payload, and the review was run through
Claude. No credentials or raw source documents were included.

## What to retain

Both reviewers support CSV and Markdown as authoritative, the DVC source archive,
and SQLite/website JSON as derived outputs. Both support separating documentary
assertions from underlying occurrences and generated accounts, preserving
unexplained reconciliation differences, and keeping principal-reference selection
independent of the evidence supporting a country headline. Neither proposes a
new database service or a replacement backend.

## Combined findings and recommended treatment

| Contract | Independent findings | Coordinator's recommendation |
|---|---|---|
| Historical knowledge and review | Astra 1; Fable F4 | Define assertion eligibility at an evidence cutoff, and date every consequential identity, relationship, occurrence and review decision. Distinguish acquisition, coding and acceptance. Specify supersession and unresolved branches. |
| Reporting time and movements | Astra 2; Fable F2 | Separate cutoff uncertainty from flow coverage. Explicitly allow sourced period totals as movement evidence where the metric permits; prevent overlap with itemised payments. Define uncertain opening/closing boundaries. |
| Source editions and evidence | Astra 3; Fable F1/F10 | Require an edition/snapshot model with explicit cardinalities and complete provenance-tuple validation. Preserve acquisition attempts, mirrors and upstream dependencies. Bind selected country references to an edition or evidence record. |
| Subject and timing keys | Astra 4; Fable F3/F9 | Separate stable identity from changing classification; type timing references across namespaces; define a directed canonical alias target without destroying equality evidence. |
| Occurrence and hierarchy ownership | Astra's additional decisions; Fable F5/F12 | Choose one canonical owner for occurrence membership and parentage. Any duplicated convenience column is generated and validated. Preserve occurrence identity through later decision revisions. |
| Metric and perimeter semantics | Astra's first-metric decision; Fable F6/F7/F8/F11/F13 | Start with one original-currency account. Specify money units, admissible status/measure/basis combinations, perimeter compatibility, refunds/cancellations and rounding. Distinguish subject identity from coverage. |
| Display and migration coverage | Astra 5 and migration decision | Link each semantic claim to all output occurrences. State exactly when a subject switches from legacy to new accounting so a crosswalk does not create two counted observations. |

The first three rows are direct areas of convergence, with complementary timing
findings: Astra identifies insufficient date fields, while Fable identifies the
missing treatment of aggregate quarterly movements. The identity row combines
different concerns, not an identical finding by both reviewers. Display occurrence
cardinality is Astra's distinct contribution. Money magnitude and typed timing
keys are particularly concrete additions from Fable.

## Remedies that need qualification

The findings are stronger than some of the proposed implementations:

- **Acquisition IDs:** Fable F1 proposes `(source_id, retrieved_at)` as unique.
  The harvester uses second-resolution timestamps and accepts a caller-supplied
  timestamp. Visiting each source once per run does not ensure uniqueness across
  runs. Use an attempt/run identifier or an explicit collision policy; validate
  migrated tuples before adopting a key.
- **Edition and document identity:** `(source_id, hash)` can identify a retrieved
  source version, but does not alone settle logical editions across mirrors.
  Declare those cardinalities rather than equating all four identities.
- **Quarterly totals:** Fable F2's proposed reuse of `as_of_start/end` conflicts
  with Astra's separation of flow coverage and cutoff uncertainty. Use distinct
  coverage fields. A flow's inclusion still requires compatible measure, currency
  and perimeter, and evidence that it does not overlap another included movement.
- **Perimeters:** Fable F6's same-ID presumption is insufficient for financial
  comparability. A register may change membership between quarters without a
  name change. Preserve definitions and membership over time; establish metric
  compatibility explicitly. F11's optional perimeter proposal likewise needs
  measure-specific rules: a subject ID does not describe gross/net coverage.
- **Occurrences:** equating an occurrence to a duplicate-decision ID (F5) leaves
  singleton events and superseding decisions underspecified. Prefer stable
  occurrence identity with dated membership decisions; a revised adjudication
  must not accidentally create a new payment.
- **Aliases and classifications:** a directed alias policy is useful, but
  equality remains legitimate evidence. Typed timing keys avoid requiring the
  renaming of stable legacy IDs just to introduce prefixes.

These qualifications come from coordinator inspection of the design and supplied
implementation, not from a second reviewer round. In particular, the harvester
really does retain prior hashes for HTTP 304 responses, and the current exporter
really does accept financial and implementation IDs in one `event_id` column.

## Proposed repair sequence and evidence

1. Settle identity, source-edition, timing and revision contracts together.
   Demonstrate that a September duplicate decision changes September's account
   without changing an August evidence-cutoff query; preserve an unknown entity's
   references when it is classified as a programme. Reject mismatched provenance
   tuples and colliding typed timing references.
2. Specify one original-currency disbursement account before mass migration.
   Demonstrate a known opening balance, quarterly flow, overlapping itemised
   payments, an uncertain boundary date and a reported closing position. State
   canonical money magnitude and retain an unresolved residual where warranted.
3. Define the migration ownership switch and output occurrence map. Demonstrate
   that one correction reaches both homepage and country-page claims, while a
   legacy row and its migrated position are never counted twice.

Other author decisions to settle in that revision are the count aggregation
level for programmes/components, IDs for extracted assertions across parser
changes, adjudication-member roles, and whether any cross-currency account is
in scope. No exchange-rate service is needed for the proposed first account.

The design is suitable for revision, then for bounded implementation tickets.
This panel review does not certify executable schema correctness: neither
reviewer ran the proposed backend, which does not yet exist.
