# Broader lifecycle-data audit: second-pass findings

14 September 2026. **Substantially stronger observations exist beyond World Bank,
energy and JETP countries. Prioritize an AFD panel feasibility pilot, with ADB and
EIB as complementary stage-history sources. No causal design is selected.**

Three scouts each used 30 external units, followed by 12/15 permitted parent
verification units. The parent obtained eight original payloads and a complete
AFD export through permitted public downloads. This changed the scout-only AFD
access verdict: schema-only leads became demonstrated financing records. See
[the frozen brief](brief.md), [verification log](parent-verification-log.csv),
[byte manifest](source-byte-manifest.json) and [AFD profile](afd-data-profile.json).
Scout reports retain their own discovery limits: [ADB](adb/report.md),
[AfDB](afdb/report.md), [EIB/AFD](eib-afd/report.md).

## Evidence by institution

| Source | Demonstrated lifecycle evidence | Coverage beyond the initial slice | Population limit and acquisition priority |
|---|---|---|---|
| AFD bulk export | Award, convention signature and first-payment date fields on actual financing records; 1,911 award/signature pairs and 1,820 signature/first-payment pairs | 2,080 financing IDs, 1,492 project IDs; loans and grants; agriculture, health, education, transport, water, energy and other sectors; 80 geography labels including MULTI-PAYS | First priority for a reproducible coverage pilot. All rows are signed; consent, observation window and removal rules prevent treating it as the complete proposal population. |
| ADB sovereign catalogue + original PCRs | Appraisal/negotiation, Board approval, loan agreement, actual effectiveness and initial disbursement are separately observable in specific originals | Indonesian transmission and Indian urban investment; Indian report includes water/sanitation and transport components, not independent sector-specific loans | Use all-sector catalogue to select cases, then supplement with PDS/legal documents and PCRs. Rich completed reports alone induce completion selection; proposed/fully cancelled histories remain unverified. |
| EIB project pages + pipeline notes | DOM-confirmed approval/signature pair; separate signature transactions; approval-only record; partial-cancellation/closure evidence from a PCR | Tunisia energy, Morocco water credit line, Egypt urban transport, Senegal historical transport | Good second route for approval-to-signature coverage. Entry is appraisal-dependent, confidentiality exclusions exist, and pipeline entries leave six months after signature. No historical denominator demonstrated. |
| AfDB portals/evaluations + borrower records | Official IATI dashboard read; borrower audit confirms a grouped financing-agreement reference. Most individual milestone leads remain unverified | Kenya water, Morocco health/transport and South African energy leads; all-sector and cancelled-project catalogue routes identified | Do not count the 25 snippet-derived stage rows as observations. Original portal/evaluation access remains problematic; no same-loan milestone pair is accepted in this pass. |

## AFD: an acquired dataset, not a schema promise

The [official metadata endpoint](https://opendata.afd.fr/api/explore/v2.1/catalog/datasets/donnees-aide-au-developpement-afd)
and [full JSON export](https://opendata.afd.fr/api/explore/v2.1/catalog/datasets/donnees-aide-au-developpement-afd/exports/json)
returned successfully. Export length and unique `id_concours` count both equal
the metadata count, 2,080. This verifies completeness of this delivered export,
**not completeness of the lender's portfolio**.

| Record group | Financing records | Distinct project IDs within group | Award + signature | Signature + first payment | All three dates |
|---|---:|---:|---:|---:|---:|
| All | 2,080 | 1,492 | 1,911 | 1,820 | 1,663 |
| Loans | 366 | 336 | 346 | 311 | 294 |
| Grants | 1,714 | 1,262 | 1,565 | 1,509 | 1,369 |
| Four JETP country labels | 128 | 106 | 122 | 113 | 109 |

Project IDs can occur under both loan and grant groups; do not add their distinct
counts. The four-country row describes location, not JETP attribution. It includes
86 Senegal, 23 Viet Nam, 14 Indonesia and five South Africa financing records.
There are 620 MULTI-PAYS rows. The other geography labels include countries and
territories; they are not automatically eligible or unexposed controls.

The [nine example records](afd-example-records.csv) use fixed country choices and
the first financing ID alphabetically within each, without selecting on dates or
speed. They include Burkina Faso agriculture, Indian rail, Moroccan roads and
Tunisian social services alongside energy and governance cases. They are audit
examples, not a matching sample. Product, sector and parent-financing distinctions
remain visible. No duration means, country ranking or effect estimates were made.

The metadata is dated **27 May 2024**, despite retrieval in September 2026. Its
scope text describes executing sovereign/non-sovereign projects with counterparty
consent; the actual status domain also contains **612 Achevé** and **1,468
Exécution** records. This mismatch needs clarification. Monthly updating is an
announced intention, not demonstrated currency. Raw signature dates span October
2018–May 2024; awards span December 2014–February 2024. These ranges do not establish
complete histories for those periods.

All 2,080 rows have signatures, 169 lack awards and 260 lack first-payment dates.
No pending-signature population is demonstrated. There are **seven signatures
preceding the recorded award** and one first payment preceding award; none precedes
signature. The profile preserves the exact financing IDs and source field names for each
anomalous pair, so process order cannot be mistaken for chronological order. These could involve
recording errors, amendments or administrative semantics; do not repair them by
sorting dates or silently dropping rows. Missing payment dates do not prove no
payment. Actual field definitions, coverage revisions and exceptions need checking
before interpreting delays.

## Checks on pivotal originals

ADB Loan3083 (Indonesia, operation42362-013) has separate recorded approval,
agreement, actual effectiveness and initial-disbursement dates. Loan8276's initial
payment is separately labelled and belongs to its cofinancier. The PCR's appraisal
end follows Board approval; preserve this source anomaly and seek its legal/
appraisal records. The Indian PCR's Tranche3 is operation40031-053/Loan2725,
distinct from parent40031-013/M0015. Parent verification read the downloaded PDF
tables; events were not joined from the parent facility.

EIB20170028's HTML has three labelled milestone columns, an empty appraisal date,
13 December2023 in the approval column and30 December2023 in the signature column.
This resolves the flattened-text ambiguity. Its 2025 grant signature is a separate
transaction; do not reset the earlier loan's clock. EIB's downloaded population
notes confirm appraisal-dependent entry, confidentiality exclusions and six-month
post-signature pipeline removal.

AfDB's direct evaluation download remained HTTP403. A35MB Kenyan parliamentary
copy of the borrower audit was retrieved and read locally. It groups multiple
loan/grant IDs with agreement dates27January2014 and19June2019; this is not an
unambiguous same-loan pair. Its program-start date is not promoted to approval or
effectiveness. Scout rows remain unverified until an exact source-to-event mapping
is established. First-disbursement eligibility is not actual first payment.

## What this changes for the short paper

The first WB slice was too narrow to characterize data availability. We now have
a concrete bulk source and independently inspected examples of several lifecycle
stages across institutions and sectors. **Proceed with data-feasibility work;
do not equate the absence of a randomized allocation rule with the impossibility
of every causal design.** Country selection, anticipation, concurrent reforms,
sector spillovers and sample inclusion still need a substantive counterfactual.

1. **AFD panel feasibility, first priority:** freeze the export and its disclosure
   rules; separate loans/grants, countries/multi-country and parent/financing IDs;
   test historical retention and the earliest usable common observation window.
   Seek an older official snapshot and inclusion/removal specifications. Inspect
   the seven reversed award/signature pairs against their source records.
2. **Stage-specific risk sets:** approval-to-signature requires approved but
   unsigned cases absent here. Signature-to-first-payment has a more promising
   starting point, but requires proof that unpaid and completed contracts remain
   visible and a population fixed before exposure. This is a feasibility lead,
   not adoption of disbursement as the paper's sole outcome.
3. **ADB/EIB cross-check:** verify the ADB all-sector export and a small sample
   including pending/withdrawn operations; seek dated EIB lists and retain
   approved-only projects. Match concepts and instruments within lenders before
   considering pooled stage outcomes. Do not force agreement between definitions.
4. **Country/sector comparison:** evaluate broader borrower strata using historical
   conditions and exposure histories. Non-energy operations can inform common
   administrative shocks, but cannot simply be labelled untreated. Contemporary
   comparison support and country-level uncertainty remain decisions under0729.

These are concrete next acquisition priorities, not a frozen estimator or a
silently started third search round. A historical population can be complete for
a defined observable stage without containing every latent proposal; define that
estimand explicitly. A current consent-selected export alone does not prove it.

## Archival and validation status

Eight original payloads (44,515,286 bytes) are in the separate DVC bundle
`data/jetp/audit-evidence/0735-round2.dvc`; SHA-256 hashes are committed in the byte
manifest. The bundle is separate because the older canonical documents directory
is only partly materialized locally; its DVC pointer was not rewritten. No ledger,
source-coverage rating or website totals changed.

The configured `padme` DVC push failed: connection refused at127.0.1.1:22. The nine
new cache objects (eight payloads plus directory metadata) are preserved in both
the audit worktree cache and the primary local DVC cache. **Remote replication is
pending**; the Git pointer alone does not make these bytes remotely retrievable.
Original source URLs and observed API routes remain in the manifest.

## Reproducible checks

The parent recomputed the profile from the archived full JSON: unique financing/
project counts, instrument/status groups, date presence/ranges, anomalous ID lists
and fixed-country first-ID examples. All eight payload hashes were recalculated.
Each scout log contains30units and the parent log12. CSV parsing and date-format
checks pass; these are coverage checks, not tests of identification.

Fresh branch gates: **1,549 fast tests passed, ten skipped;330 adherence checks
passed, thirteen skipped**. Specific DVC bundle status is clean. The documentation
and provisional-data diff does not require a full pipeline suite. Raw bundle
replication failure is disclosed above rather than treated as successful archival
on the remote. Independent review is recorded separately on PR1347.
