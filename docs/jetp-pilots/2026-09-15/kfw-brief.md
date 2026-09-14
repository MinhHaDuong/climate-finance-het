# KfW BMZ historical cohort and reporting-period feasibility

Prepared 14 September for 15 September 2026. Phase: Plan; not launched.

## Question, inputs and unit

Can BMZ-mandated KfW activities support a historical contract population and
period-resolved transitions? Use archived round-3 `kfw/` XML and metadata plus
`round3/kfw/report.md`, `profile.json` and `examples.json`. Select participating
organisation ref exactly `XM-DAC-5-2`; unit is distinct IATI activity, not loan.
The observed 4,036 activities include 1,614 closed and 523 finalising records.
Separate instruments, regional allocations and KfW mandates outside this scope.
The 12-case documentary sample uses this seven-country activity frame.

## First test and mandatory challenges

First failing test: byte-identical Country and Region exports yield one population
of 4,036 activities, not 8,072. A transaction at quarter end or reporting date
must not become an exact first-payment day. Identical planned/actual starts must
not produce a validated zero-delay conclusion. Negative entries are corrections
of unknown substantive meaning unless documented, not automatic cancellation.

Mandatory separate cases: DE-1-201366764 and DE-1-201365154; plus the smallest-ID
record in each of MA and IN with a source-reported start before 2013. Those starts
are selection proxies for testing left truncation, not verified contract dates.
Inspect annual-to-quarterly reporting and 26 August 2026 partial-period entries.

## Routes, budget and stop decisions

Maximum 20 external units:

1. Up to 8 for BMZ publisher semantics and dated snapshots via archived catalogue,
   FAQ and KfW transparency URLs. Establish signed-since-2013 and ongoing-at-2013
   inclusion, cancellation/removal and commitment/start definitions. Retry a
   previously failed JavaScript page only via a named changed route.
2. Up to 8 for historical/legal cohort evidence: seek a dated official contract
   roster for calendar 2018 in MA and IN via KfW's project/transparency repository.
   Freeze the complete disclosed roster before following individual contracts,
   regardless of completion. If absent, record historical denominator unknown;
   the 12 current-record sample remains a separate documentary probe. Inspect the
   mandatory cases first, then the sample in rank order with remaining calls.
3. Reserve 4 for verification/follow-up; unused earlier calls can move forward.

If no fixed historical contract roster or inclusion rules can be established,
DEFER historical-population claims. Return retrospective activity counts and
period-resolution constraints. Missing approval/signature semantics preclude
those stage clocks; no identical-start shortcut. If the denominator or earlier
payment coverage is absent, do not claim a first-payment interval.

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

Outputs: `docs/jetp-pilots/2026-09-15/kfw/`; new originals in a separate
`data/jetp/audit-evidence/0738-pilot` DVC bundle. No canonical data changes.

Planning issue: https://github.com/MinhHaDuong/climate-finance-het/issues/1350
