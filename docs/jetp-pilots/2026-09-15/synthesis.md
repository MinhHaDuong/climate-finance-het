# Causal-design pilot synthesis and comparative-panel decision brief

Prepared 15 September 2026 after the three bounded lender pilots were merged on
`main` at `30d9a9a9`. This document integrates their findings. It is a
design-only handoff: it neither admits new source material to the JETP knowledge
base nor selects an estimator, computes an effect, publishes an analytical
output, or authorises new acquisition.

## What the pilots established

| Pilot | Evidence retained | Supported finding | Decisive limit |
|---|---|---|---|
| [AFD / 0737](afd/report.md) | Exact financing identities across legacy, portal and XML exports; reported signature and payment observations; anomalies and bounded retrieval log | **NARROW:** retrospective reported signatures and milestones can be measured with their source semantics intact. | **DEFER:** dated historical membership, pending/withdrawn risk sets, legally defined stage clocks and a causal design. |
| [KfW / 0738](kfw/report.md) | BMZ IATI activity frame, raw transaction stamps including corrections, fixed documentary sample and inclusion wording | **NARROW:** current-snapshot activity and reporting-stamp diagnostics. | **DEFER:** complete historical contract populations, approval/signature clocks, first-payment intervals and a causal design. |
| [FCDO / 0739](fcdo/report.md) | Programme/component hierarchy, structured payloads, one document-corroborated programme start and bounded retrieval log | **NARROW:** individually documented programme starts. | **DEFER:** approval--procurement--start transitions, historical risk sets and a causal design. |

Their [AFD](afd/verification.md), [KfW](kfw/verification.md) and
[FCDO](fcdo/verification.md) verification records show frozen selection,
provenance-preserving source handling, offline reproduction and independent
checks. The pilots must not be pooled: AFD's unit is a financing, KfW's is an
IATI activity, and FCDO retains a programme/component hierarchy. Those are not
interchangeable independent treatment observations.

The common finding is useful and negative: current exports and retrospectively
reported events do not prove who was pending, cancelled, withdrawn, or retained
at a historical landmark. Nor do they supply a common, legally defined approval
or payment clock. More rows from one donor do not create more independently
treated countries.

## Question and boundary

The research question remains whether JETPs accelerate investment and a just
transition. The pilots do **not** answer it. A single-donor study can assess
whether that donor has a usable measurement series; it cannot establish a JETP
causal effect because it lacks multi-country treatment variation and a defended
counterfactual.

The first potentially publishable causal target is deliberately narrow:

> Did JETP-linked concessional approvals change after a defensible operational
> start, relative to a pre-specified comparable country panel?

This is not a claim about all investment, disbursements, project delivery, coal
retirement, or justice outcomes. Those remain separate possible outcomes. A
null, adverse, or inconclusive result is equally reportable if its scope and
assumptions are explicit.

## Next decision artifact: comparative country-quarter feasibility screen

The next step toward MVP v0.2 and the short paper is one **design-only
feasibility screen** for a country-quarter concessional-approval panel. It is a
decision artifact for ticket 0729, not ticket 0730 implementation.

### Data contracts

The screen must freeze, before outcome comparison:

1. **Source facts:** source version, retrieval/snapshot date, locator, byte hash,
   issuer, and evidence qualification for every input observation.
2. **Country-quarter observation:** country, quarter boundary and date precision;
   approval amount and currency basis; financier and instrument; recipient or
   project identifier where available; energy-transition sector rule;
   concessionality rule; status; source references; and explicit missingness,
   lost-visibility and denominator states. A pledge, approval, signature,
   disbursement and implementation event remain distinct.
3. **Treatment timeline:** separately evidenced announcement, agreement, plan,
   operational/facility and first-approval dates. The proposed operational date,
   alternatives and interpretation are all retained; no date is silently
   substituted for another.
4. **Comparison-pool record:** inclusion/exclusion reason, JETP/negotiation
   exposure status, coal and power-system context, income/finance conditions,
   shared-lender or regional-spillover risk, and concurrent policy, debt,
   election, crisis and finance interventions.
5. **Analysis snapshot:** immutable input revision IDs, outcome definition,
   transformations, coverage audit and design decision. It is derived and
   regenerable, never an editable authority.

The source knowledge base remains the authority for documents and observed
facts. The panel, treatment calendar, comparison definition, diagnostics and
event-study output belong to a separate derived analytical layer. No source fact
may be relabelled "additional investment" merely because it follows a JETP.

### Country screen

Score every candidate JETP country and potential comparison country before
inspecting the proposed outcome difference. Retain the score and exclusions.
The screen evaluates:

- usable length, continuity and definition stability of the pre-treatment series;
- precision and documentary support for operational treatment timing;
- common approval and concessionality definitions, identifiers, currency/date
  semantics and retention coverage;
- plausibility of an untreated or differently timed comparison pool, with
  negotiation exposure documented rather than assumed;
- concurrent country shocks and policy/finance interventions;
- shared-lender reallocation, regional-grid and other interference risks; and
- country-unit support, missingness and historical denominator status.

Indonesia and South Africa are candidates, not preselected cases. Documentation
volume or an apparently favourable trajectory is not a selection criterion.

### Required diagnostics and figure specification

The feasibility artifact specifies, but does not render as a result, three
aligned panels:

| Panel | Display | Required guardrail |
|---|---|---|
| Levels | Calendar and event-time concessional-approval levels for each retained treated country and comparison aggregate | Show treatment-date alternatives and sources/coverage; do not equate missing values with zero. |
| Difference | Treated-minus-comparison event-time contrast with uncertainty intervals | State estimator, weights/matching, event window, clustering and assumptions. Until the protocol passes, this is a diagnostic, not an effect. |
| Coverage | Country-quarter observation coverage, missingness, lost visibility and denominator status | Make changed disclosure visible; never display unsupported historical membership as zero. |

The frozen plan must also pre-specify exclusion and falsification checks: pre-trend
diagnostics; alternative defensible treatment dates; placebo dates; valid placebo
outcomes; leave-one-comparison-country/lender tests; sensitivity to currency,
coverage and missingness rules; and documented concurrent-shock and spillover
assessments. Good pre-trends or matching support, but never prove,
exchangeability.

## Decision rule

The screen ends with one of these evidence-backed dispositions:

| Disposition | Acceptance criteria |
|---|---|
| **GO** | A frozen, auditable candidate panel has common outcome and retention contracts; an evidenced operational treatment definition; a documented eligible comparison pool; informative pre-period coverage; explicit shock/spillover assessment; and a preregisterable protocol with exclusions, falsification and uncertainty plan. It may then be proposed to the author for 0729 scope approval before any 0730 work. |
| **NARROW** | A reproducible descriptive country-quarter approval series is supported, but the comparison pool, treatment timing, measurement comparability or causal assumptions are not. Its descriptive scope, missingness and prohibited causal interpretation are stated. |
| **DEFER** | The required common source coverage, historical retention, treatment timing, comparison eligibility or assumption evidence is absent. Record which condition failed and the specific evidence that could change it; do not substitute an effect estimate or a descriptive gap. |

No estimator, effect, public analytical output, new pilot acquisition, code/data
pipeline, MVP v0.2 feature, or research collection is selected or executed by
this document.

## Consequences for MVP v0.2 and the short paper

MVP v0.2 should first expose the knowledge base's strengths: versioned source
facts, dated finance/project/policy observations, provenance and explicit
unknowns. The comparative panel is an optional derived layer with its own
versioned snapshot and cannot change canonical facts or live public claims.

The short paper can move from aspiration to analysis only after the 0729 GO
decision freezes the estimand, treatment, population, outcome, comparison pool,
assumptions and diagnostics. Ticket 0730 then implements that authorised
protocol; ticket 0732 writes from its reproducible output. If the screen returns
NARROW or DEFER, the observatory and data-paper strands continue, while the
short paper returns to the author for an explicit scope decision rather than
presenting a descriptive gap as an effect.

This handoff therefore designs the next discriminating decision without
prejudging it or extending the completed pilot acquisition caps.
