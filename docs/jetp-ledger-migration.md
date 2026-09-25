# JETP ledger migration

How the current `data/jetp/` tables become the tables of the
[storage contract](jetp-ledger-storage.md), under the
[ontology](jetp-ontology.md). Split from `jetp-ontology.md` on 2026-09-23. The
tracker is ticket 0870, one child per step; this document is updated with the
migration's real counts at its close and retired once the old tables are gone.

## Tables retired

What disappears: `sources.csv` (becomes `parties`, `party-names`,
`documents`, `document-publishers`), `manifest.csv` (becomes `retrievals` and `snapshots`),
`plan-projects.csv` (lines), `events.csv` and `implementation-events.csv`
(observations), `project-source-links.csv` (lines with classification
`named_item` and a `refers_to` of basis `discovery`), `source-claims.csv`
(lines of classification `named_item`, `envelope`, `count`, `absence` or `heading`, with
observations), `idn-portfolio-observations.csv`, `vnm-pilot-manifest.csv` and
`vnm-pilot-observations.csv` (lines and observations of their documents),
`project-coverage.csv` and `authority-coverage.csv` (`coverage`),
`data/jetp/comparison/*.json` (documents of publisher World Bank, one snapshot
per API response, lines per record, P-numbers in `external-ids`),
`event-timing.csv` (becomes `timings`, one row per date role of an observation). The M1a
inventory builder becomes the line ingestion for its four documents; the
frozen M1a release stays as the archived release it is.

## Rebuild

The migration is a rebuild from snapshots, not a rename of columns. Each
current table is read once, its rows become lines and observations under the
target contract ([`jetp-ledger-storage.md`](jetp-ledger-storage.md)), and the result is checked against the current served views
before the current tables are removed. Counts below are from the tables on
2026-09-22.

| Current | Rows | Target | Notes |
|---|---|---|---|
| `sources.csv` | 301 | 94 parties with 95 name forms, 301 documents, 307 publications | case variants merged at minting; three joint publisher texts split into two parties each; "X via Y" and "X / Y" texts resolved to publisher X, three consulting firms linked as `author`; acronym pairs are tier-2 candidates |
| `manifest.csv` | 314 | 314 retrievals, 264 snapshots | 41 failed retrievals carry no snapshot; 9 snapshots are yielded by two retrievals each |
| `projects.csv` ZAF register | 257 | 257 lines of the Q1 2026 register, `register_allocation`; 257 agreements minted by basis `register_row`; projects minted only where the reviewed name match holds | the register's own status letter becomes `own_status`, axis delivery |
| `projects.csv` VNM count slots | 21 | 1 perimeter, 2 observations of measure `count` (7 initial, 17 screened) citing the portfolio lines | the 21 unpublished slot identifiers have dispositions, not browser redirects |
| `projects.csv` SEN | 43 | 49 lines already exist; 43 referents re-decided from the plan's own submission and quick-win lines | quick win is a classification of a line, not a kind |
| `projects.csv` IDN | 74 | 44 grant lines become agreements; 19 pipeline and 9 finance rows become projects or agreements on review; 2 monitoring rows become lines | |
| `projects.csv` remainder | 9 | projects | |
| `plan-projects.csv` | 1 628 | 1 628 lines in two IDN and two SEN documents; 67 `matched` become `refers_to` rows; capacity and estimates become observations on the line | the 230 `plan_only` lines flagged `ruptl` become `member_of` a RUPTL perimeter from the line itself, with no identity minted |
| Viet Nam RMP release | 279 | 279 lines; the 73 programme rows are `heading`, the 181 unresolved are `unnamed_item` | |
| `events.csv` | 380 | 380 observations, axis money; the 34 `need` rows become observations of measure `estimate` on their plan lines | subject is the agreement minted from the same line |
| `implementation-events.csv` | 71 | 71 observations on assets or projects after the subject review | `suspended` on a retirement becomes an asset state, not a project stage |
| `event-timing.csv` | 451 | 451 timings, one per date role, on the observations migrated from the two event tables | an approval bounded to a year and the cutoff of the report that states it become two rows of one observation |
| `project-source-links.csv` | 315 | 315 `refers_to` rows of basis `discovery` or `possible_match` | the 11 `project_page_component` rows become `component_of` relations |
| `source-claims.csv` | 151 | lines and observations; the two finance aggregates become perimeter observations that replace the hard-coded headlines | |
| `config/jetp_observatory.yaml` headlines | 4 | perimeter observations citing their lines | configuration keeps only display choices |
| `data/jetp/comparison/*.json` | 1 119 records, 97 in the reference pool | lines of World Bank API snapshots, external identifiers, comparator status crosswalk | the reference pool is a perimeter whose members are those lines |
| `config/jetp_tracking.yaml` vocabularies and the value lists of the ontology's sections 2 to 4 | about 98 lines of YAML | `terms` rows under `data/jetp/ontology/`, each with a definition and, where one exists, an external mapping | the YAML keeps display choices only |
| `news-leads.csv` | 18 | kept as today: a working file of the watch, not a ledger table | named as not served, with that reason, on the observatory's How we did this page |
| figure scripts' inline exchange rates | 1 unsupported (`2500 * 1.09`) | `rates` rows citing their source line | the Senegal package percentage is withdrawn until a cited EUR/USD rate is selected; the script carries no rate |

Order of work, each step a ticket with its own byte-level check:

0. Ontology tables: `terms`, the two crosswalks, perimeters and marker
   coefficients under `data/jetp/ontology/`, with their revision columns and
   the alignment test of the [ontology](jetp-ontology.md), section 5 (ticket 0880). Built right after the DDL
   tooling (ticket 0871), whose value checks then read the terms in force.

1. Parties in their publishing role, their name forms, documents,
   publications, snapshots. Read-only rebuild of the register (step D1); the
   observatory's Documents page is the check.
2. Lines and line fields for the four M1a documents, replacing the M1a
   builder's product with the same rows under the new contract. The inventory
   tab is the check: same rows, same order, same fields. Done by ticket 0873:
   2 164 lines in six documents (ZAF 257, IDN 1 579, VNM 279, SEN 49), their
   fields in `line-fields/`, and 1 907 `routes` for the plan and Viet Nam row
   identifiers the export served; the eight exported files are unchanged byte
   for byte. The export's count of unknown field values is now taken over the
   columns each document prints, not over the extractor's bookkeeping columns.
3. Remaining lines (ticket 0874, 2026-09-24): the 1,628 plan lines from step 2
   retain their printed columns, including `ruptl`; 46 Indonesia portfolio
   rows, 66 Viet Nam pilot acquisition rows, 46 pilot observation rows and
   146 source claims add 304 lines. Five claims lack a collected snapshot and
   remain in `data/jetp/migration/0874-pending.csv`. The 304 legacy discovery
   links are preserved in `0874-link-candidates.csv`; 35 documents without a
   previous line get one minimal line with a specific locator. Nineteen links
   lack snapshots and 31 have no precise locator, so those 50 remain pending.
   The two local pilot CSVs are frozen byte for byte under
   `data/jetp/ledger-snapshots/`; their lines cite those local records and
   retain each original source identifier, locator and hash. No project or
   `line-referents` row is minted in this step.
4. Identity split: referents and the five identity tables. The 404 identifiers
   from the unpublished preview have dispositions without new `routes` rows
   (author decision, 2026-09-24). The party table, which step 1 starts
   with the publishers under authority control (decision 12 of the
   [ontology](jetp-ontology.md)), gains the funders and channels here, each
   with its `party-names` rows and, where one exists, its external identifier
   (IATI organisation identifier, ROR, LEI, Wikidata), and the `party_in`
   relation with a role. The 61 funder strings and the register's 14 funder prefixes
   are adjudicated into funder and channel roles in this step; promoter,
   implementing entity, beneficiary and contractor are filled only as their
   lines are reviewed. A party is minted from a line like every other
   identity, so the table cannot grow ahead of its justification. Decided by the
   author on 2026-09-22.
5. Observations and event timing replace the old event tables. Tickets 0887
   and 0888 have already written the independent status and sector crosswalks:
   four South African register status words and Indonesia's approval word,
   plus four Indonesia technology groups with one clear CRS purpose. Broad
   source labels remain verbatim without a forced CRS code: the Indonesia
   solar and bioenergy groups include several technologies or grid contexts,
   and South African portfolios span different interventions. The supposed
   Viet Nam suspended retirement in ticket 0887 does not
   occur in the current event table; the Indonesia Cirebon case stays unmapped
   pending review. The Observations tab and each record's justification
   fold-out are the check for the remaining observation step.
6. Perimeter observations replace configured headlines.
7. Remove the retired tables and the compatibility readers.
