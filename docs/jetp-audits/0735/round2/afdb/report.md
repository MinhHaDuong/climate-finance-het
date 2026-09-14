# AfDB broader-source scout — 0735 round 2

14 September 2026. Documentary acceptance check: **unmet through tested routes**.
No operation-level milestone pair was independently verified from a readable
original. The search located precise, promising AfDB records covering water,
transport, power, multisector policy support and cancelled operations; their
numbers remain **unverified search leads**. Retrieval failure is not evidence
that the underlying dates or populations are unavailable to other readers.

The [frozen adaptation](brief.md) preceded external research. The audit used
**30 external units: 11 queries, 18 web retrievals (including one source-XML
click), and one escalated shell retrieval**. The call limit stopped the round;
the 60-minute limit was not binding. The [acquisition log](acquisition-log.csv)
records every unit, repeated endpoint and failure. No second round was started.
No Git, forge, institutional-message or shared-ledger changes were made.

## What was actually inspected

The [official IATI publisher dashboard](https://merged.dashboard.iatistandard.org/publishers/afdb/)
opened successfully (S01; unit 5). It lists AfDB publisher identity, IATI version
2.03, 57 datasets, 5,606 activities, country-specific exports and a separate
non-sovereign file. The dataset rows include all five country strata. It displays
179.8 MB across datasets and links a dashboard API. These are observed dashboard
metadata, not an independently parsed project population or AfDB milestone
schema. The Kenya XML source-link retrieval failed. No historical snapshot or
revision-archive capability was established.

All AfDB operation/catalogue/report facts below are leads from search results,
not original-document findings. [sources.csv](sources.csv) provides exact URLs,
publication/date roles, locators and status. [event-evidence.csv](event-evidence.csv)
contains 25 explicitly unverified candidate event rows for follow-up, not
promoted ledger events. Source dates are not replaced with crawler dates.

The original-access failures were concrete: repeated web internal errors, HTTP
402/502 responses, and a cache miss. The alternate **escalated** `curl` request
for the exact Thwake PDF returned **HTTP 403**; this was not an un-escalated DNS
failure. The Kenya Parliament borrower-audit PDF route failed the web tool's
content-length limit (35,388,797 bytes). No PDF/XML bytes were saved locally;
archive/hash columns are empty intentionally. The attempted shell target was
`/tmp/afdb-0735-archive/kenya-thwake-ipr.pdf`.

## Operation and sector coverage

| Acquisition stratum | Specific identified lead and two-date opportunity | Identity and date limitations | Acceptance |
|---|---|---|---|
| Kenya, water | L04: Thwake I **additional financing**, P-KE-EA0-006. Two loan IDs, 2000200003351 and 5050200000501, each display approval and signature; the table also distinguishes entry into force and effectiveness for first disbursement. | Original PDF blocked. AF must remain distinct from original Phase I. Effectiveness is a condition milestone, not payment. L13 borrower audit cover lists the instruments but was too large to open. | Precise loan-level lead; no verified pair. |
| Morocco, transport | L05: P-MA-D00-001, MapAfrica approval/signature fields. | Portal title is “Unknown”; no loan ID shown. Planned completion and PCR date are separate fields, neither proof of physical completion. | Second non-JETP country and second non-energy sector attempted; no verified pair. |
| South Africa, power | L10: Medupi P-ZA-FAA-001 evaluation-note table gives approval, signature, effectiveness and explicitly actual first disbursement. | Two instruments are listed together; original inspection must determine whether dates apply jointly or separately. No loan-specific duplicate observations authorized. | Power-sector lead; no verified pair. |
| South Africa, multisector | L09: P-ZA-K00-006, loan 2000300000855, energy-governance/climate-resilience IPR. | Classified **Multi-Sector**, despite energy in title. Report date, mission date and publication are distinct. Original not attempted after discovery within cap. | Additional lead; not relabelled Power. |
| Senegal | L07 historical portfolio table and L11 cancelled rice-value-chain preparation operation P-SN-A00-008. | No complete same-ID lifecycle pair inspected. Historical table uses mixed printed date formats; no normalization adopted. Power-specific original not obtained. | Stratum searched; acceptance missing. |
| Ghana | L08 transport PCR route and all-sector catalogue discovery; dedicated transport query at unit 23. | PR10741 title/operation ID not resolved; GoG wording is insufficient to join identity. Contractor-signature results rejected as loan-signature evidence. | Stratum searched; no accepted operation. |

The Kenya and Morocco attempts meet the requested *search coverage*, not the
stronger original-evidence requirement. No country is labelled untreated,
matched or currently eligible based on this discovery exercise. Historical
income/borrowing eligibility and JETP/parallel-programme exposure remain outside
what these inspected records establish.

## Population, archives and revisions

| Route | Lead revealed by search | What remains unverified |
|---|---|---|
| L01 old AfDB data portal and L02 project list | All-sector lists, statuses including approved/ongoing/completed/cancelled; historical-reach claim from 1967. | Current completeness, unique-ID rules, row export, proposed/dropped coverage and denominator. Different indexed portals have differing counts; do not merge or reconcile them without common snapshots. |
| L12 new MapAfrica projects | More recent all-sector entries, including 2026 approvals. | Update cadence, predecessor migration, removals, archived snapshots and meaning of completion fields. |
| L11 cancelled-project catalogue | Explicit cancelled rows include Kenyan JKIA second runway P-KE-DA0-001 and Senegalese preparation P-SN-A00-008. | Dates/reasons for cancellation, full cancellation coverage, and whether pre-approval abandonment is ever included. A cancellation *amount* in another table is not equivalent to a cancelled operation. |
| L06 Morocco 1999 portfolio and L07 Senegal 2003 portfolio | Dated historical cross-sector portfolio-table leads. | Original table alignment and identifiers; approved-only versus pipeline universe; exclusion rules. A historical report is a snapshot candidate, not a complete version archive. |
| L03 quarterly operational summaries | Quarterly archive and procurement-focus disclaimer in indexed text. | Original disclaimer and exact coverage; proposed-versus-approved flags. Do not equate a procurement roster with all lending or the whole risk set. |
| L15 repeated Thwake IPR index; L16 IPR collection | Multiple reports over time and an all-sector report collection. | Stable series completeness, unchanged/revised date fields, duplicate reports, administrative publication lag. Report count is not project count. |

No actual proposed or dropped-operation original was read. Unfinished operations
were deliberately sought through IPRs, rather than relying solely on completion
reports, but could not be independently validated. Cancellation and unfinished
status in this return are therefore candidate observations only.

## Field feasibility and evidence boundaries

| Field | Current result |
|---|---|
| Identification/concept, appraisal | No actual dated event independently verified. A report/document date is not the appraisal event. |
| Approval and signature | Several same-operation/same-loan candidate pairs; all original checks failed or remain unattempted as labelled. |
| Effectiveness / entry into force | Explicit candidate fields in L04/L09/L10; bank-specific semantics still require originals. |
| First payment | L10 explicitly labels an actual first-disbursement date in the snippet. L04/L09 instead show effectiveness for first disbursement. Neither is promoted to verified payment evidence. |
| Procurement | No accepted same-operation dated procurement event; contractor signatures are different legal objects from loan signatures. |
| Administrative closure | Original/revised deadlines and report dates appear as leads; none verifies administrative closure. Physical progress is outside this audit. |

## Acquisition ranking and costed next steps

Ranking concerns sources, not causal designs or observed durations. Estimates
below are planning judgments for a separately authorized pass, with no guarantee
of source access.

1. **AfDB country XML exports plus non-sovereign file**: strongest potential bulk
   population route. Inspect the dashboard's exact source links for Kenya,
   Morocco, Ghana, Senegal, South Africa and non-sovereign activities (six GETs,
   about 1–2 hours for field/identity/duplicate checks if retrieval works).
   First determine what each date code means in AfDB's export and whether actual
   start/end maps to approval, signature or another milestone. Schema presence
   alone cannot demonstrate field completeness. The API linked on the dashboard
   may expose metadata only; no project-level API/export was tested successfully.
2. **Exact L04 and L10 PDF originals**: highest-value milestone checks (two
   successful GETs plus table inspection, about 30–60 minutes). A different
   approved acquisition client/route is warranted by the recorded 402/403
   errors, not another broad keyword query. If borrower L13 is used instead,
   download its 35.4 MB PDF with a byte-capable client and inspect the instrument
   table; do not substitute a cover-page join for milestone verification.
3. **L11 cancellation catalogue and L06 historical portfolio**: denominator
   checks (two originals plus 2–4 linked cases, approximately 1–2 hours). Need
   documented cancellation dates and population boundaries, not merely an
   observed current status.
4. **L15 successive IPRs and L03 quarterly summaries**: revision/pipeline check
   (one index and three dated records, approximately 1 hour). Compare dates
   printed in successive versions and separate mission, report and posting
   dates. Determine whether abandoned proposed entries disappear. A country
   indicative operational programme remains a specific unsearched route for
   a future pipeline check; no such original was retrieved here.

Stop broad searching on the tested AfDB web route. The next discriminating work
is original retrieval and parsing of named documents, especially the milestone
PDFs and publisher XML. The current result is a source opportunity map with an
explicit access limitation, not a validated panel or a failed substantive
hypothesis.
