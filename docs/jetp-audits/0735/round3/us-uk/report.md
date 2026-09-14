# USAID and UK: acquired lifecycle evidence, third pass

14 September 2026. **UK FCDO has an acquired all-sector catalogue with pipeline
and closed programmes; USAID has accessible dated financial records and IATI
payloads. Neither can be pooled uncritically with development-bank loan clocks.**
No design selected. Request budget25/25, including failures, is reconciled in
[acquisition-log.csv](acquisition-log.csv). The [brief](brief.md) transparently
records its late written freeze after13 requests. No canonical ledger changed.

## UK: a feasible catalogue and document-linked pilot

The [official DevTracker explanation](https://devtracker.fcdo.gov.uk/about) links
to the FCDO IATI service. Acquiring its activity query for reporting organisation
`GB-GOV-1`, with80,000 requested rows, returned **25,282 records and25,282 unique
activity IDs**, exactly matching `response.numFound`. This establishes completeness
of the delivered query, not disclosure completeness or an historical risk set.
Raw `fcdo-catalogue.json`, response/docs, is the count source; fields and query are
preserved in its responseHeader and request log.

| Hierarchy | Records | Status1 pipeline | Status2 implementation | Status4 post-completion |
|---|---:|---:|---:|---:|
|1 programmes|7,327|6|551|6,770|
|2 components|17,955|7|4,200|13,748|

The catalogue spans148 recipient-country codes and198 sector codes. These are
codes, not independent countries/sectors per project; recipient regions and
multi-country allocation need separate handling. Programmes and components must
not be added as independent observations. In particular, related activities and
aggregated parent spending can double-count the same financing chain.

The catalogue retains historical completed programmes and currently planned ones:
- `GB-1-112151`, Information Communication Technology for Development, is a
  hierarchy1 post-completion programme with exact related component
  `GB-1-112151-101`. [Programme](https://devtracker.fcdo.gov.uk/programme/GB-1-112151/summary).
- The component's structured `json.activity-date` reports planned/actual start
  2007-02-01, planned end2011-07-31 and actual end2013-01-31. Parent actual start
  differs (2007-03-09); do not overwrite the component clock with its parent.
- Its `json.transaction` has quarterly/year-end **aggregated expenditure** from
  2007-03-31, a zero commitment dated2009-09-10, positive commitment2009-11-05 and
  disbursement entries2010-08-11 and2010-12-16. An earliest type3 date here is
  demonstrably not the onset of all recorded spending. Do not infer a delay of
  three years before money moved, or treat the zero entry as funding approval.
- `GB-GOV-1-400397`, UK Caribbean Resilient Infrastructure Platform, has status1,
  planned start2025-03-31 and planned end2030-03-31, no parent transaction field,
  and child `GB-GOV-1-400397-301` whose catalogue title is Business Case design
  phase. This verifies a preimplementation record, not an approved-but-unsigned
  loan or proof of no preparation expenditure.

[The IATI definitions](https://iatistandard.org/en/iati-standard/203/codelists/transactiontype/)
separate outgoing commitments, recipient transfers and spending on goods/services;
transfers can occur between reported activities. Activity-start dates are not
Board approval or signature dates. Flattened arrays are unsafe: hierarchy1 date
type occurrences exceed the number of programmes. Use structured JSON fields or
original XML, not positional assumptions across independently flattened arrays.
The [profile](data-profile.json) separately counts occurrences and records with
each date type; these are not validated milestone pairs.

The official about page promises monthly FCDO updates; it is policy, not a tested
snapshot history. [Official guidance](https://devtracker.fcdo.gov.uk/docs/Guidance-and-FAQ-on-FCDO-Data.docx)
allows exceptional security/commercial redaction and prefers partial redaction
where possible. The catalogue contains no status3/5/6 records: this is an observed
status domain, **not evidence that cancelled or suspended operations never existed**.
Deletion, cancelled-programme mapping and historical revisions remain unverified.
No original monthly snapshots were acquired. Latest metadata timestamps alone
would not show whether past observations changed.

**Pilot recommendation:** freeze hierarchy1 and2 universes separately; draw
country/sector/start-period strata including all six pipeline programmes and
closed programmes, then inspect structured dates, business cases and approval
summaries. Test the transition from aggregated expenditure to individual transfers
by cohort before measuring stage durations. Ask whether business-case decisions,
procurement starts/awards and actual activity start can form a more consistent
stage sequence than first disbursement. This is a document-linked feasibility
pilot, not adopted outcomes or estimator.

Scope here is **FCDO/legacy DFID reporting under GB-GOV-1**, not all UK finance.
DevTracker also carries other departments and delivery partners with different
reporting frequencies. DESNZ/legacy BEIS, British International Investment and
export finance need institution/instrument-specific coverage checks; they were
not acquired in this bounded pass. Country-sector presence is not JETP exposure.

## USAID: accessible accounting data, temporal semantics unresolved

[ForeignAssistance.gov's official catalogue](https://foreignassistance.gov/data)
was available and advertised an update of31August2026 in search indexing. The
site's downloaded application source linked the actual3,753,448,682-byte
[complete CSV](https://s3.amazonaws.com/files.explorer.devtechlab.com/us_foreign_aid_complete.csv).
A requested3,000,000-byte prefix returned HTTP206, with Last-Modified2September2026
and an S3 version ID preserved in `fa-complete-headers.txt`. **Only a prefix was
acquired**, not the full portfolio. It has3,885 complete-width rows, all USAID
Afghanistan due to source ordering:422 activity IDs,1,397 obligations and2,488
disbursements, with312 negative amounts. The cut final row is excluded from this
prefix profile. This is a schema probe, not a representative sample or all
Afghanistan financing.

The [published API](https://foreignassistance.gov/api-docs) also returned actual
records. Query `complete-data.json?limit=5` ignored that parameter and returned100
records with pagination metadata advertising1,662,879 total records. Those100
records omit transaction-date although the CSV includes it. API metadata is not
a reproduced full count; API and CSV totals were not reconciled. The differing
schemas must be tested before choosing acquisition routes.

The [official data dictionary](https://s3.amazonaws.com/files.explorer.devtechlab.com/DataDictionary_ForeignAssistancegov.pdf),
fields Activity ID/Start Date/Transaction Date, establishes:
- Activity ID is an internal implementing-activity identifier; project number is
  separate. Neither establishes a legal financing contract or parent linkage.
- Activity start is a mechanism/activity start, not approval.
- Transaction date is an agency accounting-system date and is consolidated by
  quarter for some agencies. Subquarter speed cannot be inferred universally.

Actual first prefix record is USAID Afghanistan primary education,
Activity177765/project306-002, obligation$37,760 on01MAR2006; start/end are NULL.
Funding agency and managing agency are distinct fields. Full scope extends beyond
USAID and includes economic and military aid; filter reporting lineage and
instrument, not only the site's branding. Old country totals from1946 and sector
summaries from2001 are not evidence of equally long project-level histories.

A further [official IATI dashboard record](https://dev-dashboard.iatistandard.org/datasets/usaid-multiple-11/)
identified the publisher-hosted
[USAID Multiple Countries11 XML](https://s3.amazonaws.com/files.explorer.devtechlab.com/iati-activities-Multiple%20Countries-11.xml).
This was acquired, not merely a schema lead: **190 unique US-GOV-1 activities,
20,079 outgoing commitment and19,762 disbursement entries**, all default finance
type110. Generated/updated31July2026, but its financial dates cover only
2015-12-31–2017-09-30. Current generation emphatically does not mean current flows.
188 activities carry status3 and two status2;9,647 transactions have negative
values. These are accounting reversals/adjustments to preserve, not negative
physical progress or automatic cancellation.

The first XML activity `US-GOV-1-720201651500` is USAID Pay and Benefits, includes
State as funding organisation, USAID as reporting/accountable/extending agency,
country/sector allocations at transaction level, and implementing-partner
redaction under the cited disclosure exceptions. This fragment is a **multi-country
administrative allocation dataset**, not190 infrastructure projects or a
historical loan cohort. A single country's allocation is not a new independent
project. Exact IDs and transaction refs are available, but the CSV/internal-ID
crosswalk was not established.

**Pilot recommendation:** acquire one explicitly project-level USAID country file
plus matching CSV extract; reconcile original activity IDs, award/mechanism IDs,
agency lineage, instrument, positive/negative entries and quarterly consolidation.
Use annual/quarterly transition intervals until exact accounting granularity is
verified. Seek termination/cancellation retention and reporting continuity around
organisational changes before interpreting censoring. The current public service
and newly generated XML establish access continuity, not completeness of every
cancelled or unpaid award. AFD/loan signature clocks should not be imposed on
USAID grants, technical assistance or administration.

## Archival and limits

Raw originals, response headers and locally derived text are under
`/tmp/jetp-round3-us-uk/`; file hashes/lengths are in
[source-byte-manifest.json](source-byte-manifest.json). Bytes are locally preserved,
not claimed remotely archived. No source-to-canonical-project joins, JETP
attributions, effect estimates or website totals were changed. A failed website
render, oversized response, DOCX limitation and timeout are logged as acquisition
failures, not evidence of absent projects. Parent review should independently
recompute the delivered catalogue count and inspect the two linked UK identities
and USAID original before promoting these findings.
