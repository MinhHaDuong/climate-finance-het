# JETP selection and intervention timing — bounded audit 0736

2026-09-14 · Phase: Execute, documentary review pending · ticket remains open.

The documentary acceptance check passes: South Africa has distinct negotiation,
declaration, plan-release and offer records, and India cannot be automatically
classified as untreated. The audit does **not** establish an assignment mechanism
sufficient for a causal claim. Several chronology fields remain explicitly
unknown. Read the matrices as evidence constraints, not a selected design.

- [Frozen brief](brief.md), committed before search: `844888af`.
- [Country chronology](chronology.md): four partnerships and India as a documented
  candidate with unresolved subsequent status.
- [Comparator admissibility](comparators.md), [rival explanations](rivals.md) and
  [allocation mechanisms](allocation.md).
- [Source metadata](sources.csv) and [unit-by-unit acquisition log](acquisition-log.csv).

The strongest distinction is between a country's place in a political process
and an actual financial intervention. Negotiation, conditional mobilization,
publication and later operations cannot be collapsed into one treatment date.
The Indonesian project-screening source supports further examination of an
operative rule, but does not itself show who received funding because of it.

This first round used **20 of 20 external units: 7 queries, 12 web opens and
1 shell URL retrieval attempt**. Batched queries/URLs count separately; the
second Viet Nam page opening counts again. No external call was made before the
brief commit. The call cap ended the round; it is not search saturation. The
elapsed-time cap was not binding. No institutional messages, shared-ledger edits,
estimation or software production changes were made.

No source bytes were archived: web-tool extractions are not locally archived
original bytes, and the sole shell PDF request failed DNS resolution. Empty
archive/hash fields are intentional, not missing hash calculations. The attempted
local target was `/tmp/jetp-0736-archive/senegal-plan.pdf`; no PDF exists there.
The repository contains paraphrases and source metadata, not bulk source text.
Search snippets are explicitly separated from inspected original extractions.

## Verification and exact gaps

A separate local pass checked the extracted original passages against the
chronology, source metadata and event labels. It retained the South African
webpage/date discrepancy and the Senegal event/publication distinction. It
rejected snippet-only Senegal plan and water-workshop leads as established facts.
It did not independently inspect the full investment-plan PDFs or signed support
instruments; original publication timestamps and private negotiation starts
remain unresolved.

The successful Council extraction is web reference `turn19view0`, URL in S01,
PDF p.2 lines 27–39 and p.3 lines 67–78 (web extraction locators), opened at
acquisition unit 3. These internal locators are supplementary reproducibility
metadata, not public links. Direct URL reopens by the parent failed, but opening the retained web reference
subsequently returned the original three-page extraction. The parent independently
checked its shortlist, negotiation and expected-demand passages, as well as the
Indian government original. This verifies the cited text, not original byte archival.

## New documents that could justify a further round

1. **G7 16 March 2022 selection decision and evaluation annexes**, held by the
   G7 presidency/co-leads: full candidate universe, rejected candidates, criteria
   and decision record. Obtain a reproducible Council 14114/22 copy as well.
2. **Dated Indonesian CIPP Chapter 5 and original longlist/decision records**,
   from the JETP Secretariat/MEMR/PLN: determine whether screens were operative,
   how exceptions worked, and whether priority status changed financing.
3. **Senegal MEPM plan publication/launch notice and original L4 document**:
   verify the 2025-04-02 lead via the government or ITIE document route and retain
   a byte hash. A changed network route can address this round's DNS failure.
4. **India negotiation status/closure record and Philippine ADB/government
   energy-transition operation histories**: clarify candidate exposure and
   parallel programmes before declaring either country a comparator.
5. **Bank-country-sector portfolio revisions and signed operation histories**:
   distinguish additional support, relabeling and displaced lending, including
   water-sector exposure. L03's MEPM water-energy-agriculture notice is a specific
   original to inspect, not yet an attribution result.

These are proposed discriminating routes, not a silently started second round.

## Repository validation

Fast gate: **1,549 passed, ten skipped**; adherence/lint: **330 passed, thirteen
skipped** in the isolated checkout. Two existing source-snapshot tests initially
failed because DVC document objects were absent from this worktree. Copying the
already available local archive into its ignored directory resolved both on a
fresh fast run; no code or tests changed. The full suite is not required for
this documentation/ticket diff.

The acquisition log contains exactly 20 units; CSV structure checks pass.
Review normalization to LF preserved every parsed CSV cell. The independent
scientific reviewer found all five documentary exit criteria addressed, with
no causal design approved. Source-byte archival remains a documented gap.
