# Response to the backend design review

Revision 2 of [the design](../jetp-backend-design.md) incorporates the independent
Astra/Fable findings and the coordinator's qualifications. The reports and their
input manifest remain unchanged as records of revision 1. This response records
an authoring pass, not a new independent review or executable implementation.

| Finding | Resolution in revision 2 |
|---|---|
| Astra 1; Fable F4 — historical eligibility | Section 6 defines admission, review, supersession and historical joins, including unknown migration times and pinned policy versions. Account-affecting metadata cannot change in place. |
| Astra 2; Fable F2 — cutoff versus coverage and flows | Sections 4–5 separate cutoff uncertainty from flow coverage and allow adjudicated aggregate movements without counting their itemised components twice. |
| Astra 3; Fable F1/F10 — editions and evidence tuples | Section 4 requires edition/snapshot/dependency tables, stable acquisition IDs and complete tuple validation. Timestamps alone are not unique attempt IDs. Section 8 pins both country source roles to editions/acquisitions. |
| Astra 4; Fable F3/F9 — identities and timing | Sections 3–4 separate entity identity from classification, use typed timing keys and define dated directed aliases while retaining equality evidence. Legacy IDs survive. |
| Astra 5 — display cardinality | Section 8 gives each semantic claim multiple uniquely identified output occurrences, with reverse dependencies and a two-location JSON example. |
| Fable F5/F12; Astra ownership decision | Sections 3–5 give occurrences stable registry IDs, derive membership from dated decisions, and put all parentage in relation rows. No second editable ownership column remains. |
| Fable F6/F11 — perimeters | Sections 3–5 separate edition-independent coverage definitions from temporal membership; compatibility is metric-specific. Money and aggregates require coverage; nonfinancial entity status can omit it. |
| Fable F7/F8/F13; Astra first metric | Sections 2 and 5 specify whole-unit decimal money and an original-currency gross disbursement metric with completeness, overlap, reversal and rounding rules. Cross-currency accounts are a later explicit extension. |
| Astra migration decision | Section 9 selects legacy or reconciled publication ownership per subject/measure/perimeter; crosswalks never double the counted population. |
| Fable author decisions | Sections 3, 5, 6 and 9 settle explicit counting levels, first-release currency scope, durable extraction IDs, adjudication roles and fixture-before-migration ordering. |

Section 10 states concrete acceptance cases for each contract. They are required
implementation evidence, not tests claimed to pass today.

The user's additional research-sufficiency request is addressed in section 11.
The architecture supports the observatory and documentary data paper, conditional
on implementation and inventory coverage. Descriptive durations require defined
endpoints and observation windows. Causal acceleration research additionally needs
frozen historical frames, exposure/baseline evidence and censoring contracts,
plus the identification decision already assigned to 0729 after 0735/0736.
These requirements extend the same stores; they do not justify a new database.

Validation for this revision is document consistency, review-finding coverage,
parseable JSON and working local links. No data migration, backend code or research
effect estimation is performed in this revision.
