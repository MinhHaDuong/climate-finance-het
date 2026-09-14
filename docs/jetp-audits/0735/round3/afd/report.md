# AFD: source reconciliation and historical retention pilot

14 September 2026. **AFD remains the strongest immediate lender pilot, but use
versioned source reconciliation, not the old export alone.** This pass acquired
three full portal tables and seven country XML files. It found stable signatures,
retained records previously marked completed or reporting zero payments, one missing sample financing, and incompatible
payment-date granularity. This is an audit sample, not a matching sample.

## Sources and versions

The [official catalogue](https://opendata.afd.fr/api/explore/v2.1/catalog/datasets?limit=100)
contains separate tables with 2,319 unique project IDs, 3,277 unique financing IDs,
and 9,696 transaction rows. They are not interchangeable units. The financing
table overlaps 2,061 of the legacy export's 2,080 IDs; 19 legacy IDs are absent.
See [flat profile](flat-profile.json), including all missing IDs. Two of those
19 were previously marked completed. Missing does not establish cancellation.

The catalogue labels financing/transaction tables as modified in November 2023
and explicitly disables updates to those labels on data or metadata changes.
Its separate data-processing timestamps are 6 September 2026 for financings and
4 September 2026 for transactions; financing signatures extend to 5 August 2026.
Neither the frozen modified label nor processing time is an event cutoff. The 2024 legacy export was one
publication route, not the limit of AFD's publicly available history.

A separate [AFD publication on data.gouv.fr](https://www.data.gouv.fr/datasets/donnees-de-laide-au-developpement-de-lafd-1)
exposes 97 resources, an Open Licence, and September 2026 metadata. Its country
XML files have explicit project/financing hierarchies and transaction types.
The fixed sample covers Albania, Morocco, India, Senegal, South Africa, Indonesia
and Viet Nam. These choices test schema and retention across sectors/countries;
they do not assert common support or that any country is an untreated control.
Country files were generated on 17 August 2026; upload dates differ. We did not
acquire all 97 resources or infer their combined portfolio size.

## A concrete, limited retention test

Exact financing-ID joins yield **317 current financing records**, under 225
project records, versus **224 legacy financing records** in these countries.
**223 of 224 are retained**, including 61 legacy-completed records and 30 with
missing legacy first-payment dates. There are 94 additional current financing
IDs. Of the 30 retained legacy zero-payment records, 24 now have positive
reported XML payments and six have no type-3 entries; this does not prove those
six remain unpaid. The 94 additional IDs are additions to this observed export,
not necessarily new financing
agreements or projects first approved since 2024.

The missing ID is **CMA123501**, PLAN SOLAIRE MASEN (CSP ET PV), legacy signature
28 June 2019, award 15 June 2017, no first-payment date and reported cumulative
payments zero. It is absent from both the current financing table and Moroccan
XML. Its parent is CMA1235; related components cannot replace the missing ID.
The source labels this energy-titled operation under a social-services sector,
an additional reason not to match mechanically on one sector field.

This demonstrates retention of some closed and payment-missing records, while
refuting universal retention in the tested sample. It is not proof of an earlier
complete population or of why CMA123501 disappeared. The old payload was
retrieved now with 2024 metadata, not independently archived by us in 2024.
Current status codes in this sample are only implementation and closed. An
approved-but-unsigned or cancelled risk set is not demonstrated.

## Dates: agreement, ambiguity and a falsified shortcut

[Record-level comparisons](legacy-xml-comparisons.json) and the
[XML profile](xml-profile.json) preserve the exact joins.

- All 223 overlapping signatures equal the XML commitment transaction date.
  This is strong within-source-system agreement, not independent legal validation.
  Across the full flat-table overlap, 2,059 of 2,061 signatures agree; one has a missing current value (CTN129703), and one changes
  from 2021-11-16 to 2024-10-29 (CZZ276103). Both require source reconciliation before any transformation is finalized.
- All 210 nonmissing legacy award dates equal the XML commitment `value-date`.
  But IATI defines `value-date` as the date for currency conversion, not approval.
  The 13 missing legacy awards instead have later XML value dates, often the
  generation date. Do not impute awards from this field: agreement on populated
  records does not validate the missing-data fallback.
- There are 647 XML disbursement entries in the sample; 577 are dated 31 December,
  with remaining entries on 31 July 2026. **None of the 193 nonmissing legacy
  first-payment dates equals the earliest reported XML disbursement date.**
  The full flat transaction table likewise has 5,771 of 6,420 type-3 rows dated
  31 December. This falsifies using the minimum XML payment date as an exact
  first-payment day; annual/reporting-period aggregation is the working
  interpretation, to be confirmed with publisher transformation specifications.

An inspected example, FR-3-CAL101901, has a commitment transaction date of
6 June 2023, a value date of 17 November 2021, an actual-start field of
13 December 2023, and a disbursement entry dated 31 December 2023. These are
four distinct source fields. The operation is a policy loan tranche under
FR-3-CAL1019, not a construction project. Do not interpret actual start as
signature, or standardize policy lending and physical infrastructure clocks.
The [IATI value definition](https://iatistandard.org/en/iati-standard/203/activity-standard/iati-activities/iati-activity/transaction/value/)
is the authority for the generic field, even where AFD reuses it differently.

## Disclosure and remaining evidence

The [2018 AFD transparency policy](https://www.afd.fr/sites/default/files/2025-04/politique-transparence-afd.pdf),
sections 2 and annex 2, conditions disclosure on client agreement and describes
expansion beyond sovereign operations after 2017. Annex 2 traces project IATI
publication to June 2014. This is evidence of a changing disclosure regime, not
a fixed public population. Neither this policy nor the inspected exports proves
permanent retention or complete coverage of unsigned/cancelled financings.

Next bounded pilot:

1. Reconcile the 19 missing legacy IDs, one missing signature proxy and one
   changed signature proxy against
   source history; preserve disappearances as observation events, not outcomes.
2. Obtain the AFD transformation dictionary for award/value-date, signature,
   actual start and aggregated payment dates. Resolve the seven legacy
   award/signature reversals rather than sorting them into chronological order.
3. Acquire dated predecessor XML snapshots and an inclusion/retention rule for a
   fixed pre-JETP signed cohort. Assess loans/grants and policy/investment strata
   separately; include unpaid records and trace disclosure changes.
4. Retain exact legacy milestones and reporting-period transactions as separate
   observation types. Stage speed may require interval-censored endpoints;
   do not claim exact first payment from an annual aggregate or silently bridge
   an unobserved initial period.

The next decision is which stage-specific population is defensible. This pass
selects neither disbursement as the sole outcome nor a causal estimator.

## Audit trail

26 external discovery/definition units used, below the 30-unit cap. Source log
and hashes accompany this report. Initial discovery preceded the written brief;
that sequencing deviation is explicit in the parent brief. Raw bytes are retained
locally and included in the round-3 archival inventory. No canonical ledger or
website total changed. XML/JSON counts, exact-ID retention, field comparisons and
period-end clustering were recomputed from the original payloads.
