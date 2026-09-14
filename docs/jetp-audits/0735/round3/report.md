# Bilateral sources: third-pass decision memo

14 September 2026. **Proceed with an AFD reconciliation pilot and complementary
KfW/FCDO population pilots. JICA offers a documentary cohort route; USAID needs
an identifier and reporting-granularity check first.** There is now ample evidence
to stop treating the World Bank energy slice as the available data universe.
There is not yet a selected causal design or a harmonized multi-lender panel.

## What was actually acquired

| Institution | Verified delivered data | Implication for the short paper |
|---|---|---|
| [AFD](afd/report.md) | Full tables: 2,319 project IDs, 3,277 financing IDs, 9,696 transaction rows. Seven country XML files: 317 financing IDs. Retains 223/224 legacy sample financings, including 61 completed and 30 with missing old payment dates. | Best immediate reconciliation test. All 223 overlapping signatures agree, but one financing with no recorded payment disappears. Do not infer universal retention. Preserve exact legacy milestones separately from annual/reporting-period payments. |
| [KfW through BMZ](kfw/report.md) | 4,036 distinct KfW-linked activities; 1,614 closed and 523 finalising. 19,072 disbursement entries, all at quarter ends or a single reporting date. | Substantial all-sector, multi-country population candidate. Reporting-period analysis is more plausible than exact payment-day timing. No verified approval/signature clock or cancelled/unsigned population yet. |
| [JICA](jica/report.md) | Current XML: 474 activities, planned dates and commitments only. Original Morocco/India evaluations: Exchange-of-Notes and signature months. Official annual loan signing/amendment list acquired. | Reconstruct an older signature cohort from annual lists, with original appraisal/legal records. The current XML is a discovery catalogue, not a demonstrated actual-stage panel. |
| [UK FCDO/legacy DFID](us-uk/report.md) | 7,327 programmes plus 17,955 components, including six pipeline and 6,770 post-completion programmes. Structured historical and pipeline records inspected. | Promising business-case/procurement/start-stage pilot. Parent/component relationships and historical expenditure aggregation must be resolved. This is not all UK financing. |
| [USAID](us-uk/report.md) | Official financial CSV prefix and API probe; 190-activity XML fragment with 39,841 transactions. Fragment is mainly an older administrative/multi-country allocation slice. | Access is established, but this is not a representative project population. Reconcile activity/award IDs and accounting periods before expanding acquisition. |

These counts have different units and scopes and **must not be added**. They are
not counts of comparable loans, JETP projects or causally valid controls. The
sample deliberately extends beyond energy and JETP countries; country and project
matching still require baseline conditions, instrument and institutional processes.

## AFD changes the immediate priority

The legacy export is not the only source. Current country XML is available via
[a separate official publication](https://www.data.gouv.fr/datasets/donnees-de-laide-au-developpement-de-lafd-1).
In the seven-country sample, 223 of 224 legacy financing IDs remain visible,
with 94 additional current IDs. Missing CMA123501 had no recorded first payment
and zero cumulative payments in the old source. Its disappearance is an
observation-process finding, not proof of cancellation. Across the full portal
financing table, 19 old IDs are absent; one signature proxy is missing and another has changed.

A useful falsification result: none of 193 populated legacy first-payment dates
matches the earliest XML disbursement date. Period-end aggregation makes the
minimum transaction date an unsafe exact-payment estimator. Separately, populated
legacy award dates agree with XML value dates, but IATI defines that field for
currency conversion; where the old award is absent, generation-like dates occur.
A generic field mapping would manufacture apparently precise lifecycle events.

This argues for source/version-specific date semantics, not abandoning stage
speed. Exact approval-to-signature dates, interval-bounded payment transitions,
and business-case/procurement milestones are separate candidate outcomes,
subject to verification of their definitions and coverage.
Their populations must be defined before an estimator is chosen.

## Next work and decision tests

These actions remain under historical-population ticket 0735 and design tracker
0729. They are acquisition/feasibility pilots, not an adopted identification plan.

1. **AFD first:** reconcile 19 missing legacy IDs and two signature discrepancies;
   determine whether missing awards have administrative fallback dates; retrieve
   an older XML snapshot and publisher retention/transformation specifications.
   First test: a known old payment-unobserved financing that disappears must be marked lost
   to observation, not cancelled or right-censored as if known still unpaid.
2. **KfW alongside AFD:** fix the exact BMZ/KfW agency/instrument scope, reconcile
   a historical signed cohort and document annual/quarterly payment reporting.
   First test: identical Country/Region exports cannot double the population;
   a quarter-end aggregate cannot pass as an exact first-payment day.
3. **FCDO:** freeze programme and component IDs separately; link a small cohort
   to business-case decisions, procurement records and activity-start evidence,
   including pipeline and completed cases. First test: pre-2010 expenditure in
   GB-1-112151-101 prevents interpreting its later first type-3 transaction as
   the beginning of all funding; parent dates cannot replace component dates.
4. **JICA:** reconcile one older annual signature cohort across the annual list,
   loan catalogue and originals, including unpaid/cancelled cases where present.
   First test: amendments and separate loan phases must not count as new loans;
   evaluation-selected old cases cannot define the whole historical population.
5. **USAID and broader UK scope:** before a large download, establish USAID
   project/award crosswalk and transaction granularity in one project-focused
   country slice. Add DESNZ/BEIS, BII or export finance only as separate scopes
   when justified by project comparability. First test: a recently generated
   administrative XML with only 2015–2017 transactions cannot count as a current
   infrastructure cohort. FCDO coverage cannot be labelled all UK finance.

The design-selection checkpoint should compare eligible country/project counts,
pre-exposure coverage, anticipation and concurrent-policy histories, inclusion
loss, and stage-definition stability. Greater record counts alone do not solve
country selection, spillovers into non-energy, or a small number of JETP-treated
countries. Conversely, non-random country selection does not rule out every
credible quasi-experimental design. This pass measures data feasibility.

## Verification and archive

Discovery used AFD 26/30, JICA 20/20, KfW 20/20, USAID/UK 25/25 external units:
91 units total. No further external verification calls were needed; parent
verification used the downloaded originals. The written briefs were frozen late
in this round; their deviations are disclosed rather than described as preregistration.
No saturation is claimed. No institutional requests were sent.

Parent independently recomputed the JICA, BMZ/KfW, FCDO and USAID pivotal counts,
read the original JICA milestone tables, inspected the linked FCDO structured
records and US dictionary, and checked the AFD source joins. Independent review
of the AFD profile and this synthesis is recorded separately. Counts establish
completeness of delivered exports/queries only, not disclosure completeness.

Original bytes and source manifests are preserved in a separate round-3 bundle.
Raw files are not placed in Git. DVC remote replication remains a separate
release requirement under 0726; a committed pointer is not a public deposit.
Canonical ledgers, website totals and production pipeline code are unchanged.

Local fast and adherence gates passed: 1,549 and 330 tests respectively. All
33 source/response archive entries (406,032,031 bytes) match their hashes;
34 DVC cache objects are preserved in both worktree and primary caches. The
remote push again failed at 127.0.1.1:22; replication remains pending. See
[verification record](verification.md) for scope and independent checks.
