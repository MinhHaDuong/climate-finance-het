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
| `event-timing.csv` | 451 | one disposition per legacy row: a typed timing only when its date role is supported by ontology v2; otherwise an explicit pending disposition | an approval bounded to a year and the cutoff of the report that states it become two timings of one observation; an unknown event date or a page-observation date is not relabelled as `event` or `report_date` (author decision, 2026-09-24) |
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
   with the publishers under authority control (decision 12 of the ontology design, now in the
   [attic](attic/jetp-ontology-decisions-2026-09.md)), gains the funders and channels here, each
   with its `party-names` rows and, where one exists, its external identifier
   (IATI organisation identifier, ROR, LEI, Wikidata), and the `party_in`
   relation with a role. The 61 funder strings and the register's 14 funder prefixes
   are adjudicated into funder and channel roles in this step; promoter,
   implementing entity, beneficiary and contractor are filled only as their
   lines are reviewed. A party is minted from a line like every other
   identity, so the table cannot grow ahead of its justification. Decided by the
   author on 2026-09-22.
5. Observations and event timing replace the old event tables. The 451
   legacy timing rows must reconcile one for one to a typed timing or an
   explicit pending disposition; there is no target of 451 typed timings.
   Ticket 0876 writes 443 cited observations and 362 timings from 360 typed
   source rows (two cutoff rows also provide a bounded approval year);
   `0876-timing-reconciliation.csv` accounts for the other 91 legacy timing
   rows. The four served views project the accepted v2 events and their exact
   cited lines into the browser contract. Eight unsupported physical claims
   remain in the pending register and are absent from those views; all 315
   project-source-links were retained until ticket 0878 retired their legacy reader.
   Tickets 0887
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
   Ticket 1620 (2026-09-29) gave the 91 pending timing dispositions, the five
   pending citations of 1160 and the 54 coverage dispositions of 0884 an owner
   or a disposition each. The original scope comprised 145 distinct semantic
   rows; `1620-register-dispositions.csv` now holds 152 decision records after
   preserving overlaps, splitting the composite DEG/Proparco application and
   recording the follow-up Nagajaya review:
   31 timings typed from the documents' own text (29 annex proposals dated by
   the annexes' version table, the AfDB approval's report_date by the article dateline (its event day rejected), the Saloum
   tender by its bid deadline as `planned`), 52 terminal (the plan's own date
   cannot be read from its version table; the MAF period; page-observation
   dates; the undated Diass factsheet), 7 pending physical claims rejected,
   the previously accepted Nagajaya claim revoked by a superseding row, and 1
   left with ticket 0920; every read judgment verified by a three-reader panel
   (storage contract § 4, `matching.panel` version 1) with the stance and
   confidence recorded per row; 33 authorities attached to parties (8
   minted from lines that print their names), 4 left uncovered for want of a
   line, 17 project identifiers handed to M1b.
6. Perimeter observations replace configured headlines.
7. Remove the retired tables and the compatibility readers.

## Current migration census (0870, 2026-09-30)

These are actual current canonical rows at `dd98e868`, including comparator
imports and decisions made after the migration waves. They are not targets,
counts of distinct projects or sums of the historical inputs above. Shards
are read as one table; superseded and rejected rows remain in this census.

| Canonical table | Rows | Canonical table | Rows |
|---|---:|---|---:|
| `terms` | 233 | `status-crosswalk` | 15 |
| `sector-crosswalk` | 30 | `perimeters` | 7 |
| `marker-coefficients` | 12 | `parties` | 193 |
| `party-names` | 195 | `documents` | 392 |
| `document-publishers` | 403 | `retrievals` | 426 |
| `snapshots` | 369 | `lines` | 13 092 |
| `line-field-specs` | 97 | `projects` | 64 |
| `assets` | 2 | `agreements` | 315 |
| `line-referents` | 382 | `relations` | 4 021 |
| `observations` | 48 367 | `timings` | 24 230 |
| `external-ids` | 12 840 | `adjudications` | 0 |
| `adjudication-members` | 0 | `rates` | 0 |
| `deflators` | 20 | `routes` | 1 907 |
| `coverage` | 145 | | |

The 1620 record contains 152 rows: 52 `terminal`, 31 `resolved`, 25 `covered`,
17 `moved_to_owner`, 11 `rejected`, 9 `minted_and_covered`, 4 `left_uncovered`,
2 `pending_owner` and 1 `revoked`. These are decision records, preserving
overlap and supersession, not 152 distinct legacy items.

The observatory's Methods inventory names every storage-contract §1 table,
its keys, complete raw CSV downloads or its reason for not being fully
served. Complete lines and observations retain their canonical country-year
shards. Bulk timings, external identifiers and per-document fields are
explicitly omitted; partial projections are labelled. The 152 decisions are downloadable
verbatim and browsable by stance confidence, lowest first, with their
justification and readers. The Viet Nam count links follow the two accepted
perimeter observations (`7` initial and `17` newly screened proposals), their
exact local-record lines and original locator notes, the one perimeter
coverage row, and its three documents. They do not create unnamed project
pages or infer a 24-project tally.

Migration reads each old register once into reviewed, append-only records.
Routine site builds read the current canonical tables and decisions; they
never rerun those register ingestions. The frozen M1b release remains the
release originally reviewed, independently of subsequent live ledger changes.
