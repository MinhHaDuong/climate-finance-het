# South Africa MVP reporting baseline — 14 September 2026

## Bounded documentary check

Question: does the MVP reflect JET-IP-2026-Q1-Progress-Report-final, or an
available Q2 successor? Routes: the JET PMU quarterly-report index, resource hub,
Q1 PDF and dashboard, and searches for the exact Q2 filename and 30 June 2026
report. Budget: ten web calls; stop after checking both official indexes and the
identified report. Four web calls used. No Q2 edition was found on these routes;
this is a dated search outcome, not proof of universal absence.

Acceptance: verify issuer, report period and publication separately; compare
reported financing perimeters and Table 5 with the archived register and exported
MVP. Preserve discrepancies. Do not infer project events from aggregate tables.

## Evidence and result

- Official report index: https://justenergytransition.co.za/monitoring-evaluation-and-learning
- Resource hub: https://justenergytransition.co.za/resource-hub
- Q1 report: https://justenergytransition.co.za/wp-content/uploads/2026/06/JET-IP-2026-Q1-Progress-Report-final.pdf
- Existing archive: source `zaf-jet-quarterly-2026-q1`, collected 12 September;
  SHA-256 `1b62a65fd70c70b0234379fcc4fcda064e9175fc9aee21a37c97b283e1b8dc13`.
- Reporting cutoff: 31 March 2026. Official publication listing: 26 June 2026.
  Corrected `sources.csv` publication date; the headline retains the report cutoff.

The MVP already used Q1's USD 6.12bn allocation headline and contained all 257
imported register rows. The visible narrative lacked a named reporting baseline,
Q2 search outcome and reconciliation of report versus register status counts.
The updated country view now supplies these, plus the distinction between the
257 register rows and the catalogue's 263 identities (six additional records).

| Measure | Q1 report | Archived register |
|---|---:|---:|
| Planned records | 23 | 23 |
| Approved records | 18 | 18 |
| Implementation records | 129 | 128 |
| Completed records | 87 | 88 |
| Total | 257 | 257 |

Report locator: Table 5, printed page 14. Register counts are calculated from the
257 events with source `zaf-jet-investment-register-q1-2026`, using their original
Status labels. The individual identity behind the net difference is unresolved;
no event or project identity is changed to force equality.

Section 3 and Tables 3–4, printed pages 12–13, distinguish USD 6.12bn instrument
allocations from USD 4.32bn project/portfolio allocations. The latter is a subset;
no sum of project events is used to reconstruct either aggregate. Both report
claims are retained in `source-claims.csv` with locators and context-only status.
This update verifies the MVP baseline and these aggregates; it is not a claim that
every narrative milestone in all 36 report pages has been coded as an event.

## Validation

The initial documentary check failed because the exported country narrative had
neither the Q1 baseline nor the 128/88 discrepancy. Rebuild and verify the Q1
headline, publication date, separate reported status counts, unchanged register
rows, and exported source hashes. Run the existing fast and adherence tiers for
the prose/config/data change; no pipeline implementation changes are involved.

Validation result: documentary acceptance and all exported input hashes pass.
The fast run had 1,547 passes and ten skips; two failures were missing archived
fixtures in the fresh worktree. Both pass after linking the existing local archive.
The adherence tier has 329 passes and fourteen skips. `git diff --check` passes.
