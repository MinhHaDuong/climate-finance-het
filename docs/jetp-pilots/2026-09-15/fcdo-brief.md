# FCDO programme component and documentary-stage feasibility

Prepared 14 September for 15 September 2026. Phase: Plan; not launched.

## Question, inputs and unit

Can business-case approval, procurement and start be linked at a coherent unit
with documented coverage? Use archived round-3 `us-uk/fcdo-catalogue.json`, the
three structured programme/component payloads and guidance, with the US/UK
report and data profile. Scope: FCDO/legacy DFID reporting under `GB-GOV-1`.
Freeze 7,327 programme IDs and 17,955 component IDs separately. Main 12-case
sample unit: programme in the common seven-country frame. Component follow-up
must use explicit related-activity IDs and cannot increase programme sample N.

## First test and mandatory challenges

First failing test: component GB-1-112151-101 retains its own start date; its
parent's different date cannot replace it. Its pre-2010 expenditure prevents
later first type-3 records from being labelled first spending. Also assert that
pipeline status alone cannot establish approved-but-unsigned financing.

Mandatory challenge set: GB-1-112151 and component, plus all six pipeline
programmes in the acquired catalogue, including GB-GOV-1-400397. These may fall
outside the common countries and remain a separately reported challenge set.
Do not drop completed programmes from the sample frame. Flattened parallel arrays
must not be positionally zipped into milestone pairs; use structured records.

## Routes, budget and stop decisions

Maximum 20 external units:

1. Up to 6 for source retention/redaction/status definitions and historical
   snapshots through acquired FCDO guidance, IATI publisher and DevTracker routes.
2. Up to 10 for documents: use existing structured challenge payloads first, then
   uninspected pipeline programmes in ID order, then sample rank order. Follow
   exact DevTracker document links for business cases/approval summaries and
   procurement records. Each fetched document is a unit; no assumption that one
   programme costs one request. Procurement portals are searched only with an
   operation/contract identifier. Retain linkage confidence and contrary evidence.
3. Reserve 4 for verification/follow-up; unused earlier calls can move forward.

For each sample/challenge programme report whether approval, procurement and
start documents exist locally, were attempted, retrieved and validate each stage.
Record missing and not-attempted cases separately; do not extrapolate coverage
from this purposive sample. If stages cannot be linked at one unit, NARROW to
individually supported stages or DEFER the transition. This does not establish
coverage of all UK finance or approved-but-unsigned loans.

## Fixed documentary sample

Profile all acquired records locally. For documentary coverage, restrict the
sample frame to AL, MA, IN, SN, ZA, ID, VN at the lender unit below. Partition by
country, DAC energy/non-energy/mixed-or-unmapped, and raw instrument code (missing
is its own value). Sort strata lexicographically, then IDs within each stratum.
Take one ID from each stratum per round, cycling until 12 distinct IDs are chosen
or the frame is exhausted. Save all candidates, ranks and selected flags; no
outcome/date/status filtering or replacement after failed retrieval. Exclude
mandatory challenge IDs from this sample and report them separately. This is a
purposive coverage probe, not an estimate of population document availability.
Report local-document coverage for all 12, and external-attempt coverage with
its own denominator. If the call cap prevents inspecting a selected case, label
it not attempted. Continue first in sample rank order within the assigned budget.

Read and apply `docs/jetp-pilots/2026-09-15/protocol.md` for baseline alternatives,
observation states, source/selection freeze, output schemas and review. That
protocol is part of this assignment, not optional background. Parent trackers:
0735 / GitHub #1345 and 0729 / #1337. No effect estimation or outreach. A DEFER
with precise missing evidence can satisfy every pilot exit criterion.

## Exit criteria

- First acceptance tests fail on naive mappings and pass on the corrected implementation.
- Input hashes, frozen selection and the common units/events/coverage/evidence tables are delivered.
- Every mandatory challenge has an evidenced disposition or a precise unresolved gap.
- Acquisition stays within the cap with failed/not-attempted cases retained.
- Versioned calculations rerun offline from archive paths, with relevant repository gates recorded.
- A separate verification pass reproduces pivotal counts and checks originals.
- Report returns GO/NARROW/DEFER by stage and inputs to the common design matrix.

Outputs: `docs/jetp-pilots/2026-09-15/fcdo/`; new originals in a separate
`data/jetp/audit-evidence/0739-pilot` DVC bundle. No canonical data changes.

Planning issue: https://github.com/MinhHaDuong/climate-finance-het/issues/1351
