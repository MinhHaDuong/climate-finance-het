# Country-quarter approval feasibility screen — ticket 0814

15 September 2026 · **DEFER** · no outcome inspection or effect estimation.

## Freeze and boundary

The candidate-country record and treatment calendar were frozen before any
country-quarter outcome comparison. They use only the accepted selection audit
at commit [`0287d39f`](https://github.com/MinhHaDuong/climate-finance-het/blob/0287d39f/docs/jetp-audits/0736/report.md):
[candidate countries](candidate-countries.json) and
[treatment calendar](treatment-calendar.json). Both declare `outcome_inspection:
none`.

No operational/facility date is observed for any candidate. Declarations and
plan releases are retained as alternatives, not substituted as treatment time
zero. India and the Philippines are explicitly ineligible as untreated
comparators: the former has documented or unresolved negotiation exposure and
the latter's exposure and parallel programmes were not audited.

## Contract result

`scripts/jetp/_causal_feasibility.py` validates that every prospective
country-quarter approval record has a source version and locator, approval-date
semantics, currency basis, concessionality and instrument rules, and explicit
missingness, denominator and lost-visibility states. It rejects an untreated
label with unknown negotiation exposure. The contract is deliberately metadata
only; it cannot calculate an outcome, difference or effect.

There are **zero admissible country-quarter approval observations** in this
screen. That is an explicit coverage finding, not a zero approval value:

| Requirement | Existing evidence | Result |
|---|---|---|
| Common approval event across countries | AFD has reported award fields; KfW reports periodic payment stamps; FCDO retains programme/component documentary stages | No common approval definition or country-quarter source contract |
| Historical denominator and retention | 0735 and all three lender pilots retain partial/current frames only | Pending, cancelled, withdrawn and lost-visibility populations unresolved |
| Operational treatment time zero | 0736 records negotiation, declaration and plan milestones | No defensible operational/facility date; anticipation precedes declarations |
| Eligible unexposed comparison pool | India and Philippines fail the documentary screen; later JETP countries have exposure uncertainty | No comparison country admitted |
| Interference and concurrent shocks | Shared-lender channel and domestic/parallel interventions are documented or unknown | No no-interference or exchangeability argument |

The [0735 lifecycle reports](../../jetp-audits/0735/report.md) and the
[pilot synthesis](../../jetp-pilots/2026-09-15/synthesis.md) establish the
source-specific limits behind this table. Lender records are not pooled: an AFD
financing, KfW IATI activity and FCDO programme/component are different units.

## Conditional protocol if a future scope decision reopens the screen

Before any contrast, the next authorised work would have to freeze a candidate
universe, country eligibility/exposure record, treatment-date alternatives,
common approval definition, currency/concessionality rule, source versions and
historical denominator/retention assessment. It would pre-specify:

- pre-period coverage and definition-stability diagnostics;
- documented alternative treatment dates and placebo dates;
- valid placebo outcomes only where their exposure pathway is defensibly absent;
- leave-one-country and leave-one-lender sensitivity checks;
- sensitivity to coverage, currency, instrument, missingness and comparison
  membership rules; and
- a country-level uncertainty procedure whose limits are reported as precision,
  not as proof of identification.

Good pre-trends, matching or placebo ranks would be diagnostics only; they
cannot repair selection, anticipation, measurement or interference failures.

## Decision and exact next evidence

**DEFER.** A causal country-quarter approval comparison is not feasible from
the reviewed evidence. It would be misleading to narrow this result to a
descriptive difference because there is no common observation contract to
describe.

Only a separately authorised, bounded acquisition plan could change this
decision. It must name and retrieve: (1) a common cross-country approval source
with field definitions and versioned retention rules; (2) dated operational
support instruments or facility records; (3) country negotiation-closure and
parallel-intervention histories for potential controls; and (4) historical
denominator evidence covering pending, withdrawn and cancelled records. Until
then, ticket 0730 remains unauthorised and no causal figure may be rendered.
