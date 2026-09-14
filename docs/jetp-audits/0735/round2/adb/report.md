# ADB second-pass source audit

Source trail: [30-unit call log](call-log.csv), [operation/event evidence](evidence.csv), and [pre-search adaptation](brief-adaptation.md).

Candidate findings for parent verification, 14 September 2026. Execute phase;
30/30 external query/URL units consumed, including failures, repeated opens and
screenshots. No further discovery within this assignment. No source bytes were
collected: successful official web text extraction remains **unarchived**. The
local Python command unavailable before Python3 made no network request and is
not a budget unit. No Git, forge, shared ledger or other-agent mutations.

## Documentary result

**ADB passes the actual-milestone feasibility check for individual loans. It does
not yet pass the historical-population check.** Two official completion reports
were successfully opened, one Indonesian energy operation and one Indian urban
operation. Actual pairs are demonstrated in original text; screenshots failed.
The evidence CSV preserves exact loan identities and distinguishes plans and
search-only leads. Parent verification must inspect the pivotal originals.

[Java–Bali PCR](https://www.adb.org/sites/default/files/project-documents/42362/42362-013-pcr-en.pdf),
February 2021, identifies project 42362-013, ADB loan 3083 and AIF loan 8276.
Basic Data pp i–ii gives approval, agreement, actual effectiveness, loan closing,
financial closing and separate initial disbursements for each loan. ADB 3083 has
approval 2013-12-03, agreement 2013-12-30, actual effectiveness 2014-09-29,
initial disbursement 2015-12-14, loan close 2019-09-30 and financial close
2020-01-09. Expected effectiveness was 2014-03-30. This is a completed operation
with substantial **partial** cancellation, not an entirely cancelled project.
Appraisal ends after board approval in the reported table: retain the anomaly,
do not silently repair it. The agreement-date label is not a separately inspected
signed legal instrument.

[Rajasthan PCR](https://www.adb.org/sites/default/files/project-documents/40031/40031-013-pcr-en.pdf),
July 2019, covers parent 40031-013/M0015 and Tranche 3, 40031-053/loan 2725.
Use the latter's Basic Data pp iii–iv: approval 2010-12-13, agreement/signature
2011-03-17, actual effectiveness 2011-06-16, initial disbursement 2011-08-17,
actual loan closing 2017-06-30, financial closing 2017-11-24. Paragraph 2
explicitly calls the agreement date signed. Water/sanitation and urban transport
are identifiable components, not separate loans. Page vi distinguishes planned
and actual procurement. The parent framework agreement predates parent board
approval; never substitute parent dates for tranche events.

## Country, sector and stage coverage

The attempt covered IDN/VNM and three non-JETP borrowers: PHL, BGD and IND.
Two non-energy sector families were attempted (water/sanitation and transport),
with both present in India's opened urban report. Original actual pairs are
confirmed only for IDN and IND. The aim of original pairs in two non-JETP
countries remains **unmet**; PHL/BGD failed retrievals must not count as successes.
No standalone social-sector case was inspected. Country strata are not controls;
historical income/eligibility and JETP exposure have not been audited.

PHL 41665-013 Grant0477, BGD 42169-013 Loan4284 and VNM 39595-023 Loan2353
have detailed search-extracted milestones, but all direct PDS opens failed.
BGD road project 34415-013 Loan2021 has a promising completion-report lead;
both original and normalized PDF URLs failed. These remain explicitly unverified
rows. The current BGD lead has a revised future closing date and no actual
closing, useful for an unfinished-case check only after original retrieval.

| Stage | Demonstrated in opened original? | Limit |
|---|---|---|
| Project/loan identity | Yes | Parent/tranche and cofinancing require separate keys |
| Concept/entry | No | VNM/PHL PDS concept dates remain leads |
| Appraisal | Yes | Indonesian chronology anomaly requires review |
| Approval | Yes | Not commitment/signature |
| Signature | Yes, India narrative | Indonesian table labels agreement date |
| Effectiveness | Yes | Planned and actual explicitly distinct |
| Procurement | Yes, India schedule | Award date is not first disbursement |
| First disbursement | Yes | Loan-specific, not a cumulative-flow observation |
| Administrative closure | Yes | Loan and financial closing distinct |

## Population, bulk acquisition and history

The [official sovereign catalogue](https://data.adb.org/dataset/adb-sovereign-projects)
metadata describes coverage from 2005 through 27 January 2026, annual updates,
and downloadable CSV/XLSX. Publication date is 12 February 2018 and last update
9 March 2026. It names all five country strata. Active means effectiveness of at
least one funding source, so it cannot prove effectiveness of every loan. Proposed
records are tentative. Download and metadata-JSON clicks failed, and local
retrieval encountered DNS failure without escalation. Neither schema nor rows,
status frequencies, keys, missingness, deletions or historical snapshots were
verified. JSON is advertised for metadata, not demonstrated as an operation API.

The [official operations index](https://data.adb.org/taxonomy/term/236) provides
annual-report resources, including historical commitments tables. Its explanatory
text flags the 2017 shift toward signed commitments. Those amount tables are an
archive route, not demonstrated project-event histories. Definition stability
across years and completeness of proposed/dropped operations remain untested.

A search for cancelled project status returned no usable official case, which
says nothing about institutional absence. Completion reports demonstrate retained
completed operations and partial cancellations; they cannot establish coverage of
fully cancelled loans or proposals removed before approval. No historical entry
or removal rule was found. A current catalogue filtered by later completion would
not supply the historical risk set.

## Acquisition order and next discriminating documents

1. Retrieve the catalogue's CSV/XLSX original from a working network route, then
   inspect identifiers, status domain, approval dates and all-sector row coverage.
   Request no institutional contact in this assignment. Compare an official older
   snapshot or annual operational list to test removal and revision rules.
2. Retrieve BGD `34415-013-pcr.pdf` (Basic Data, Loan2021-BAN(SF)) and PHL
   `41665-013/main` (loan/grant milestones), using official downloadable PDS or
   signed agreements if direct HTML remains blocked. These specific originals
   can establish the second non-JETP pair; extra broad keywords cannot.
3. Inspect Indonesia Loan3083's signed loan agreement and effectiveness notice,
   and reconcile the PCR appraisal-end anomaly. Retrieve VNM Loan2353's
   9 October 2007 agreement linked from `39595-023/main`.
4. Establish a retained proposed and a fully cancelled/dropped operation from the
   catalogue and archival operational programme, including its entry/removal date.

Catalogue-first plus loan-level PDS is the potentially scalable route; PCRs are
rich retrospective supplements with stronger completion-selection risk. Access
failures currently raise acquisition cost. No API scalability, denominator,
saturation, construction result, effect estimate or causal design is certified.

Parent handoff update: the parent reports a successful escalated public GET of the
Indonesian PCR after this scout exhausted its budget. Archive/hash provenance
belongs to the parent's separate verification log. This demonstrates that the
scout's local DNS failure was a route constraint, and should temper the access-cost
finding; it does not establish that the other failed URLs or exports are reachable.
