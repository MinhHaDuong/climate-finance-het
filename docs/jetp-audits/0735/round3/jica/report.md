# JICA: historical documents stronger than the current bulk milestones

2026-09-14. **Verified bulk acquisition and two original historical operation
reports; no complete lifecycle-risk population established.** All 20 external
request units are recorded in [the acquisition log](acquisition-log.csv).
The [brief](brief.md) discloses its late freezing after initial discovery.

## Acquired bulk source

JICA's [Operational Results page](https://www.jica.go.jp/english/activities/achievement/)
links directly to the [activity XML](https://iatipublisher-prod.s3.amazonaws.com/xml/mergedActivityXml/jica-activities.xml).
The acquired file contains **474 unique activity IDs**, generated
2026-06-29T02:41:43Z. It spans 86 recipient-country codes and 95 sector codes.
All 474 activities have status code2. Finance codes: 150 with421,304 with110,
20 with510; retain original codes until harmonized. There are474 start dates of
type1 and371 end dates of type3, **no actual activity-date entries**. There are
474 transactions, all type2 outgoing commitments;38 have value zero. No actual
first-payment series is present. Planned starts range2006-11-01–2026-05-20;
that range is not proof of portfolio history. Full counts are in
[bulk-profile.json](bulk-profile.json).

[Official date semantics](https://iatistandard.org/en/iati-standard/203/codelists/activitydatetype/)
identify1 and3 as planned dates; [transaction semantics](https://iatistandard.org/en/iati-standard/203/codelists/transactiontype/)
identify2 as outgoing commitment. Neither planned start nor commitment date is
accepted as an exact loan signature without an original cross-check. A recently
generated XML does not imply recently updated observations: record update times
range2024-03-13 to2026-06-29. All-status2 coding supplies no demonstrated completed,
cancelled, pending or unsigned denominator. This does not establish that JICA
never publishes such cases elsewhere.

## Verified historical originals

Eight month-precision event rows are in [event-evidence.csv](event-evidence.csv).
These are verification examples selected from discovered original reports,
not a random sample, not an estimated speed distribution.

| Operation | Original evidence | Identity and precision limits |
|---|---|---|
| Morocco Watershed Management Project | [FY2017 evaluation](https://www2.jica.go.jp/en/evaluation/pdf/2017_MR-P24_4_f.pdf), printed p3: Exchange of Notes March2007; loan signature March2007. Study September2017–December2018. | MR-P24 is in issuer filename; title, borrower and two-watershed scope confirmed in text. Monthly dates cannot establish same-day signing. |
| India Rengali Irrigation Project I,II,III | [FY2018 evaluation](https://www2.jica.go.jp/en/evaluation/pdf/2018_ID-P154_4_f.pdf), printed p3: phaseI Exchange of Notes October1997/signature December1997; phaseII March2004/March2004; phaseIII March2010/March2010. Study August2018–September2019. | FileID ID-P154 cannot be assigned to every phase: separate loan-ID mapping remains unresolved. Preserve phase labels and source identity; the report concerns Odisha Brahmani basin irrigation, not the separate Phase2 project listed as related. |

These operations are outside JETP countries and outside energy. Their Exchange
of Notes is a distinct intergovernmental agreement, **not Board approval**.
The tables also give cumulative disbursed amounts, which establish no first-payment
date. No exact effectiveness or first-payment event is accepted from this pass.

## Population and historical route

The [ODA visualization guide](https://www.jica.go.jp/oda/guide/index.html)
states instrument-specific inclusion windows. Loan coverage includes agreements
signed from2010-10-01, projects completed from that date, and projects evaluated
ex post fromFY2003. Technical cooperation has a200million-yen threshold for the
post2008-start route; older evaluated cases are also included. Grants have their
own post2008 agreement/postFY2005 evaluation routes. Thus the displayed historical
population mixes entry cohorts with evaluation-selected older projects; the rule
is not a complete pre-signature proposal register.

The [ODA loan catalogue](https://www2.jica.go.jp/en/yen_loan/index.php/module/search)
has country/sector and approval-financial-year filters, but warns its figures may
be abridged. This pass inspected the search interface, not a complete catalogue
export or its retention policy.

The acquired [official data book](https://openjicareport.jica.go.jp/pdf/12395323.pdf)
has table14-3, printed p31, listing ODA loans newly signed inFY2024, with a column
explicitly combining **signing/amendment dates** and separate amounts. It includes
Cambodia roads, Philippine health and Bangladeshi food safety as well as energy.
This is a promising dated cohort denominator, but amendments must be separated;
older annual volumes and stable IDs were not acquired here.

## Next discriminating pilot

Reconstruct one fixed historical signature cohort from an older official annual
data book, reconcile every row against the loan catalogue, and retrieve its
appraisal/ex-ante document and later legal/evaluation history regardless of
completion. Test retained cancelled/undisbursed cases explicitly. Record exact
loan IDs versus programme phases and keep month precision as intervals.
Compare count reconciliation with the current XML and visualization portal.
Only after that test whether Exchange-of-Notes→signature or signature→first-payment
has enough consistently observed transitions. The latter still needs actual
payment sources; the current XML cannot supply them. This recommends acquisition,
not a causal estimator or a label of untreated for non-energy projects.

Seven original payloads are preserved under `/tmp/jetp-round3-jica/`, with URLs,
bytes and SHA256 in [source-manifest.json](source-manifest.json). Local XML parsing
and PDF text-table inspection were successful; PDF rendering was not used.
Search-result publication timestamps were not substituted for report dates.
No canonical ledger, JETP attribution or website total was changed.
