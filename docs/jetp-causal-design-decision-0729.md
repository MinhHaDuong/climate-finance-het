# JETP causal-design decision — ticket 0729

15 September 2026 · design checkpoint · **CAUSAL DEFER**

## Decision

No causal estimand is authorised for ticket 0730. In particular, the evidence
does not support a claim that JETP-labelled countries accelerated relative to
old completed projects, a country panel, or a supposedly untreated sector. The
appropriate decision is **DEFER**, not an estimate with wider caveats.

The next admissible decision is a *pre-outcome comparative country-quarter
feasibility screen* for a possible outcome of concessional approvals. It is not
an estimator, a panel construction, or a causal result. It may return GO,
NARROW (descriptive series only), or DEFER. Only a GO and the author's explicit
scope approval can freeze a causal protocol for 0730.

## First documentary acceptance check

The proposed naive comparison fails causal acceptance. JETP countries were
selected partly on persistent conditions and anticipated transition paths; the
selection audit records Senegal's expected demand growth and South Africa's
pre-existing transition agenda. South African financing talks preceded the
2 November 2021 declaration, so declaration time cannot rule out anticipation.
Meanwhile, old completed projects are selected on survival and maturity, not a
pre-treatment risk set. A common calendar shock can affect both comparison
groups while observed income balance says nothing about those mechanisms.

The check therefore **fails**, even if observed income groups balance. Evidence
that could distinguish these biases from a JETP effect is: a dated candidate
universe, selection criteria and rejected cases; first private negotiation and
support-instrument dates; historical lender frames retaining pending, withdrawn
and cancelled operations; and country--sector exposure histories that identify
parallel support and shared-lender reallocation. None is presently sufficient.

The underlying selection evidence is the accepted 0736 audit on commit
[`0287d39f`](https://github.com/MinhHaDuong/climate-finance-het/blob/0287d39f/docs/jetp-audits/0736/report.md),
especially its chronology, comparator and rival matrices. It separates South
African negotiations, declaration, plan release and conditional offer; treats
India as negotiation-exposed rather than untreated; and finds no usable
allocation rule. Its Council source (S01, pp. 2--3) and South African sources
(S02 and S04) are locators, not proof of random or as-if-random assignment.

## Evidence review and candidate-design matrix

The 0735 lifecycle audit found dated World Bank rosters but neither contiguous
historical frames nor original approval/signature pairs. Its broader and
bilateral passes found useful lender-specific lifecycle observations, but not a
shared historic risk set. The completed AFD, KfW and FCDO pilots corroborate
that result: their units and clocks differ, and none establishes a causal
country treatment contrast. See the [0735 round-one report](jetp-audits/0735/report.md),
[round two](jetp-audits/0735/round2/report.md), [round three](jetp-audits/0735/round3/report.md),
and [pilot synthesis](jetp-pilots/2026-09-15/synthesis.md).

| Candidate design | Required identification condition | Evidence bearing on it | Unresolved threat | Decision |
|---|---|---|---|---|
| Incumbent pipeline, fixed before intervention | Complete pre-anticipation historical membership; stable inclusion/removal rule; observed exits | WB 2010 and 2020 rosters contain unfinished cases; AFD/KfW/FCDO retain some retrospective stages | Missing 2015/2021 frames, unknown retention, no common legal clock, cancellations/withdrawals unresolved | DEFER |
| Pipeline throughput | Contiguous entry and exit frame independent of treatment | Some current lender populations and milestone records | Treatment can change composition; disappearance can be success, withdrawal or lost visibility | DEFER |
| Energy/non-energy triple difference | Comparable exposed energy and genuinely unexposed non-energy populations, with common shocks and no spillovers | Sectoral scope and water/industry leads are documented | JETP and related programmes cross sectors; water and other sectors are not cleared of exposure | DEFER |
| Country synthetic control or staggered country comparison | Defended treatment date, unexposed comparison pool, stable common outcome, no decisive concurrent shock | Political declarations and plan dates are documented; pilot work identifies potential approval fields | Negotiation precedes declarations; India and later partners are exposure-uncertain; selection and parallel interventions are documented | DEFER pending screen |
| Support-component allocation effect | Actual rule assigning otherwise comparable components to support | Indonesian screening description identifies a lead | No dated operative rule, accepted/rejected universe, score, exceptions or funding consequence | DEFER |

Observed balance, a good pre-period fit, or placebo ranks would support a
specified design but cannot repair these identification failures. Few treated
countries would also make conventional randomisation language untenable unless
exchangeability is independently defended.

## Comparator, falsification, sensitivity and uncertainty requirements

If the feasibility screen earns GO, it must freeze all of the following before
outcome comparison:

- A comparison record for every candidate country: inclusion/exclusion reason;
  JETP and negotiation exposure; income, finance eligibility, coal and power
  context; lender overlap; and concurrent policy, debt, election, crisis and
  finance interventions. A country considered for a JETP is a lead, never an
  automatic control.
- A treatment calendar that retains separately evidenced negotiation,
  declaration, plan, operational/facility and first-approval dates. The chosen
  operational date and each defensible alternative must remain visible.
- A country-quarter approval observation contract: lender and instrument,
  concessionality rule, currency basis, approval-date semantics, status,
  identifiers, source/version locator, precision, missingness, lost visibility
  and denominator state. Pledges, approvals, signatures, payments and delivery
  remain distinct.
- Falsifications: pre-period diagnostics; documented alternative treatment
  dates; placebo dates; substantively valid placebo outcomes; leave-one-country
  and leave-one-lender checks. Placebo ranks are descriptive diagnostics, not
  exact randomisation p-values absent exchangeability.
- Sensitivity: comparison membership/weights, calendar window, currency and
  concessionality definitions, coverage and missingness rules, country/lender
  exclusion, and recorded concurrent-shock and spillover assessments.
- A country-level uncertainty procedure justified for the number and dependence
  structure of treated and comparison countries. Its limits must be reported as
  precision limits; they do not turn failed identification into low power.

## Protocol proposal and outcome-inspection record

**Proposed question, conditional on GO:** did JETP-linked concessional
*approvals* change after a documented operational start relative to a
pre-specified, comparably measured country panel? The unit would be a
country-quarter approval observation. The proposed follow-up horizon, eligible
countries, outcome transformation, operational date and estimator are
deliberately blank until the screen verifies their contracts.

This checkpoint inspected no country-quarter outcome table, approval total,
trajectory, treatment-effect model, or effect sign. It reviewed only source
coverage, milestone semantics, documentary timelines and design threats in the
linked audits. That is the prior-outcome-inspection record. The screen must
freeze its source versions, candidate universe, exclusions, treatment-date
alternatives, outcome definition, missingness rules, uncertainty procedure and
falsifications before calculating any contrast. A derived analytical snapshot
would remain separate from canonical source facts.

The required three-panel output is specified but not rendered: levels with
coverage/timing, treated-minus-comparison diagnostic with stated method and
uncertainty, and coverage/missingness/denominator status. A missing observation
may never be displayed as zero. This protocol is compatible with the pilot
[handoff](jetp-pilots/2026-09-15/v0.2-and-short-paper-handoff.md).

## Author decision requested

The evidence does not permit the requested causal short-paper analysis now.
Please choose one scope:

1. **Authorise the bounded feasibility screen.** It can test the common
   country-quarter approval contract without estimating an effect; its result
   governs whether a 0730 causal protocol is possible.
2. **Narrow now to a descriptive, provenance-first approval series.** It must
   state that it has no JETP-effect interpretation.
3. **End the causal-paper path for now.** The observatory and data-paper work
   continue without a descriptive substitute for causality.

Until that decision, 0730 must not construct an effect estimate or present
descriptive differences as causal acceleration.
