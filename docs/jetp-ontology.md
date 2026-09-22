# JETP ledger ontology and storage contract

Status: design for author review, 2026-09-22. Version 2 of the ontology first
drafted the same day and reviewed by four independent panels
([`jetp-study/ontology-review-2026-09-22/`](jetp-study/ontology-review-2026-09-22/)).
It fixes the vocabulary the ledger uses, the tables that store it, and the
migration from the current tables. It is the reference against which
[`jetp-backend-design.md`](jetp-backend-design.md) sections 2 to 4 and 9 are to
be revised (section 8 below), and the reference the observatory
([`../deliverables/jetp-observatory/README.md`](../deliverables/jetp-observatory/README.md))
serves.

Four decisions by the author on 2026-09-22 shape it:

1. Split the identity registry now rather than tag it. The current
   `projects.csv` mixes four kinds of row; a column would only name the mix.
2. The published line is the first-class unit, and its storages are unified.
3. Statuses follow each publisher's practice. The publisher's word is stored
   verbatim and crosswalked; it is never overwritten or inferred.
4. Design the target, then migrate. No incremental patching of the current
   tables.
5. Line identifiers are minted, not keyed on fingerprint and locator
   (section 5).
6. The party table is built in the identity split, minimal, with funder and
   channel roles populated first (section 6, step 4).
7. Reconciliation is a tiered, defeasible, traceable process (section 11).
   The record format is designed now; the matcher starts at its simplest tier.

## 1. Why the current model fails

The evidence is in the four reviews; the short form is this. The four
partnerships never publish a project registry. They publish lists: a grants
register keyed by funder and sequence (South Africa, 257 rows), plan appendices
of capacity lines by system (Indonesia, 1 579 rows over two editions), plan
annexes of positions and task groups (Viet Nam, 279 rows), promoter submissions
and quick wins (Senegal, 49 rows). The ledger read all of these as projects.
The result is one foreign key, `events.project_id`, that resolves to a funder
tranche in 257 cases, a donor facility or programme in about 40, and a physical
undertaking in about 60, so that no count and no sum in the ledger states its
unit. The register's own status letters were dropped into a notes string. The
21 Viet Nam count slots, a cardinality assertion, sit in the registry as rows.
The partnership pledges, which are the headline of every country page, have no
table and live in configuration. Asset attributes exist in three tables but
no asset does. The same kind of thing, a published line, lives in four
storages with three schemas.

## 2. Vocabulary

Terms are ordered from the evidence outward: who says it, in what, then what it
is about.

### Publisher

The body that publishes a document and answers for what it states: the JETP
Indonesia Secretariat, the JET Project Management Unit, the Ministry of Industry
and Trade, ANER, Senelec, the Asian Development Bank. A publisher has an
authority category (`config/jetp_tracking.yaml` `authority_categories`) and a
country or `international`. The registry holds 103 distinct publishers today,
as free text in a column.

A publisher is what the project has so far called a source. The word source is
retired from column names and page copy, because it has meant a URL since the
first harvest.

### Document

A logical publication: a title, a document type (`source_types` in the
vocabulary, renamed `document_types`), a canonical URL, and one or more
publishers. The Resource Mobilisation Plan 2023, the Q1 2026 investment
register, an EVN project page. Publication is a relation, not a column, so a
declaration co-signed by a government and the International Partners Group, or
a report issued jointly by a secretariat and a ministry, names every publisher.
A document may have editions; an edition is a document row related to its
predecessor.

### Snapshot

One retrieval of one document: exact bytes under a SHA-256 fingerprint, the
retrieval date, the HTTP outcome and the storage path. This is the current
manifest row. A statement in the ledger cites a snapshot, never a URL, so that
what was read can be re-read.

### Line

One publisher's dated assertion at one locator in one snapshot. A row of the
grants register, a line of a plan appendix, a position in an annex, a submission
in a list of submissions, a heading that groups such lines, a count the
publisher gives without naming what is counted. The line is the first-class
unit of the ledger: every identity below is minted from lines, every observation
cites one, and nothing is ever counted except lines and the identities that
reviewed matches have produced from them.

A line carries what every line has in common: country, snapshot, locator,
ordinal in its table, the label the publisher printed, its classification
(section 4), the publisher's own status word and which axis that word belongs
to. Everything else the publisher printed for that line is kept verbatim in a
per-document fields table, one column per source column, as the M1a export
already does with its pass-through columns.

Proposition and programme, two kinds in the first draft, are classifications
of lines. A proposition is a line whose publisher puts something forward for a
decision not yet taken: a Senegal Annex 2 submission, a Viet Nam Annex I.2
partner proposal. A programme heading is a line that groups other lines under
a governance or budget envelope. Neither is an identity. Two propositions may
describe one future project and a proposition may die without one.

### Project

An undertaking with a scope, an owner and a duration, that creates or changes
assets or delivers something non-physical. Minted only by a reviewed match
across lines, never by ingestion. Classified as `project`, `programme` or
`component` by a dated assertion, with `component_of` carrying containment on
the relations table. A technical-assistance project has no asset; a programme
may have none of its own.

### Asset

A physical thing at a site: a plant, a unit within a plant, a transmission line,
a substation, a mini-grid. Carries capacity, technology, location and operator,
and moves through an asset lifecycle aligned to Global Energy Monitor's
status list, so that early retirement, mothballing and fuel conversion are
expressible as asset states. Coal retirement is a unit fact: an asset may be a
unit whose `part_of` is a plant. Minted only by a reviewed match. An asset can
exist with no project: the plan line for Pelabuhan Ratu names a plant and a
retirement year and matches no undertaking.

### Agreement

Funder-side money: a party commits an amount under an instrument to a
counterparty. A grant line of the register, a loan, a results-based lending
operation, a term sheet before signature. States are states of the document
that embodies it: announced, MoU, approved, signed, cancelled, withdrawn.
Money movements are flows on the agreement, typed by the IATI transaction list:
pledge, commitment, disbursement, expenditure. A plan cost estimate is not an
agreement state; it is an observation on a line (section 5). An agreement
may be a tranche of another (`tranche_of`) and finances zero or more projects
(`finances`); the hierarchy never splits money.

### Party

A named organisation in a role: funder, channel, promoter, implementing entity,
beneficiary, contractor, operator. Replaces 61 free-text funder strings that
conflate funder with channel ("Canada via World Bank and ADB"). A party may
also be a publisher; the two registries share an organisation identifier when
they do.

### Perimeter

A coverage definition the ledger can count against: the partnership pledge
envelope and its revisions, a source-defined portfolio of 24 records of which
21 are unnamed, a procurement quota of 250 MW, a plan's list at a cutoff.
Membership is evidence, not a list. A count slot is a perimeter observation,
"this publisher counted 24 at this date", not 21 rows in a registry.

### Observation

One dated statement about one subject, cited to one line: a flow on an
agreement, a state of an asset, a stage of a project, a capacity, an estimate
on a plan line, a count on a perimeter, an envelope on a partnership. The
subject is typed, `(subject_kind, subject_id)`, and may be a line itself when
no identity has been minted. The date carries a role (event, reporting cutoff,
register date, planned) and a precision. Values are the publisher's, in the
publisher's unit and currency; conversion is a derivation.

### Crosswalk

A reviewed, dated mapping from one publisher's status vocabulary to one shared
axis. The publisher's word stays on the line and on the observation; the
crosswalk row is the only place a shared status is asserted, and it names who
decided it and when.

## 3. Relations

| Relation | From | To | Meaning |
|---|---|---|---|
| `published_by` | document | publisher | many-to-many; role optional (author, co-signatory, host) |
| `edition_of` | document | document | succeeds a previous edition |
| `snapshot_of` | snapshot | document | bytes of one retrieval |
| `in_snapshot` | line | snapshot | with locator and ordinal |
| `groups` | line | line | a heading line groups the lines under it in the same document |
| `refers_to` | line | project, asset, agreement, party, perimeter | the reviewed match that minted or attached an identity; dated; never deletes the line |
| `component_of` | project | project | containment; acyclic |
| `part_of` | asset | asset | unit within plant |
| `concerns` | project | asset | zero or more |
| `finances` | agreement | project | many-to-many |
| `tranche_of` | agreement | agreement | at most one active parent |
| `party_in` | party | agreement | with role |
| `member_of` | project, asset, agreement | perimeter | dated evidence of membership |
| `same_as` | any | same kind | equality evidence; does not choose a route |
| `about` | observation | any subject | typed |
| `cites` | observation | line | exactly one |

## 4. Line classifications and status axes

A line's classification says what kind of statement it is, in the publisher's
own terms, from a closed list:

`named_item`, `unnamed_item`, `quota`, `heading`, `submission`, `evaluation`,
`register_allocation`, `count`, `envelope`, `absence`.

The list is grown when a publisher's practice needs a value; it is never
inferred from the label.

Three shared status axes, each sourced from an external list and extended only
where the four publishers' practice requires it:

| Axis | Subject | External list | Local additions |
|---|---|---|---|
| project stage | project | OC4IDS `projectStatus`: identification, preparation, implementation, completion, maintenance, decommissioning, decommissioned, cancelled | none |
| asset state | asset | Global Energy Monitor: announced, pre-permit, permitted, construction, shelved, cancelled, operating, mothballed, retired | `retirement_proposed`, `retirement_agreed` |
| money | agreement | states: announced, mou, approved, signed, cancelled, withdrawn; flows: IATI pledge, commitment, disbursement, expenditure | none |

The publisher's own words, all of them, are kept: the register's `A. Planned`
to `D. Completed`, Indonesia's modality and approval, Viet Nam's published or
not published, Senegal's submitted, evaluated and quick win. Each maps through
the crosswalk to at most one axis. Where a publisher reports one axis only, the
other two are absent for that line. The reviews established that today each
country populates one axis: South Africa the money axis with the delivery axis
discarded, Indonesia approval, Senegal estimates, Viet Nam none. The ledger
states this rather than filling it.

## 5. Storage contract

One file is one table, joins happen at read time, nothing is materialised
(ticket 0858, kept). Tables under `data/jetp/`, CSV, columns in this order.
A table too large for the repository's file ceiling is chunked by country
into `<table>/<CODE>.csv`, which stays one table.

| Table | Key | Columns |
|---|---|---|
| `publishers` | `publisher_id` | name, authority_category, country, notes |
| `documents` | `document_id` | country, document_type, title, url, published_date, edition_of, active, notes |
| `document-publishers` | (document_id, publisher_id) | role |
| `snapshots` | `sha256` | document_id, retrieved_at, status, http_status, content_type, size_bytes, storage_path, final_url, error |
| `lines` | `line_id` | country, sha256, locator, ordinal, label, classification, own_status, own_status_axis, groups, notes |
| `line-fields/<document_id>` | `line_id` | the document's own columns, verbatim, header as printed |
| `projects` | `project_id` | country, canonical_name, aliases, classification, classified_at, notes |
| `assets` | `asset_id` | country, name, technology, location, operator_party_id, part_of, notes |
| `agreements` | `agreement_id` | country, instrument, currency, tranche_of, notes |
| `parties` | `party_id` | name, kind, country, publisher_id |
| `perimeters` | `perimeter_id` | country, name, scope, definition, notes |
| `line-referents` | `referent_row_id` | line_id, referent_kind, referent_id, status, method, method_version, confidence, evidence_line_ids, decided_at, decided_by, supersedes, notes |
| `relations` | `relation_id` | from_kind, from_id, relation, to_kind, to_id, valid_from, valid_to, status, method, method_version, confidence, decided_at, decided_by, supersedes, line_id |
| `observations` | `observation_id` | subject_kind, subject_id, axis, measure, value, unit, currency, own_status, date, date_role, date_precision, line_id, notes |
| `status-crosswalk` | (publisher_id, own_status) | axis, shared_status, decided_at, decided_by, notes |
| `routes` | `old_id` | kind, new_id |
| `coverage` | (referent_kind, referent_id) | review_status, checked_at, route, document_ids, notes |
| `dry-searches` | as today | |
| `decisions.md` | as today | |

Rules that the validator enforces:

- An observation cites exactly one line and its subject exists.
- A line's `sha256` exists in `snapshots` and the bytes exist in the store.
- A `line_id` is minted by the extractor as `<document_id>-<table>-<ordinal>`,
  in extraction order, appended only and never renumbered: a re-extraction
  that finds a dropped row appends it under the next ordinal. The pair
  (`sha256`, `locator`) is unique across `lines` as a check, not as the key,
  so no two lines claim the same place in the same bytes and a locator too
  coarse to be unique, such as a whole report, is refused at ingestion.
  Decided by the author on 2026-09-22: a minted key keeps the row's identity
  independent of its attributes, which is the normal form; the fingerprint and
  locator stay on the row as provenance.
- A referent is minted only by a `line-referents` row with a basis; no
  ingestion script writes to `projects`, `assets`, `agreements`, `parties` or
  `perimeters`.
- `own_status` is copied, never normalised. `shared_status` appears only in
  `status-crosswalk`.
- No column holds a semicolon-separated list; a list is rows in a relation
  table.
- `routes` maps every identifier the observatory has ever served to its new
  kind and identifier, so no public route breaks.
- Every count exported names its unit: lines of a document, referents of a
  kind, or a perimeter observation.

What disappears: `sources.csv` (becomes `publishers`, `documents`,
`document-publishers`), `manifest.csv` (becomes `snapshots`),
`plan-projects.csv` (lines), `events.csv` and `implementation-events.csv`
(observations), `project-source-links.csv` (lines with classification
`named_item` and a `refers_to` of basis `discovery`), `source-claims.csv`
(lines of classification `envelope`, `count`, `absence` or `heading`, with
observations), `idn-portfolio-observations.csv`, `vnm-pilot-manifest.csv` and
`vnm-pilot-observations.csv` (lines and observations of their documents),
`project-coverage.csv` and `authority-coverage.csv` (`coverage`),
`event-timing.csv` (date_role and date_precision on the observation). The M1a
inventory builder becomes the line ingestion for its four documents; the
frozen M1a release stays as the archived edition it is.

## 6. Migration

The migration is a rebuild from snapshots, not a rename of columns. Each
current table is read once, its rows become lines and observations under the
target contract, and the result is checked against the current served views
before the current tables are removed. Counts below are from the tables on
2026-09-22.

| Current | Rows | Target | Notes |
|---|---|---|---|
| `sources.csv` | 301 | 103 publishers, 301 documents, 301 publications | joint publications added by review, none derivable from the free text |
| `manifest.csv` | 314 | 314 snapshots | unchanged content |
| `projects.csv` ZAF register | 257 | 257 lines of the Q1 2026 register, `register_allocation`; 257 agreements minted by basis `register_row`; projects minted only where the reviewed name match holds | the register's own status letter becomes `own_status`, axis delivery |
| `projects.csv` VNM count slots | 21 | 1 perimeter, 2 observations of measure `count` (7 initial, 17 screened) citing the portfolio lines | routes for the 21 slot identifiers point at the perimeter |
| `projects.csv` SEN | 43 | 49 lines already exist; 43 referents re-decided from the plan's own submission and quick-win lines | quick win is a classification of a line, not a kind |
| `projects.csv` IDN | 74 | 44 grant lines become agreements; 19 pipeline and 9 finance rows become projects or agreements on review; 2 monitoring rows become lines | |
| `projects.csv` remainder | 9 | projects | |
| `plan-projects.csv` | 1 628 | 1 628 lines in two IDN and two SEN documents; 67 `matched` become `refers_to` rows; capacity and estimates become observations on the line | `ruptl` becomes `member_of` a RUPTL perimeter |
| Viet Nam RMP release | 279 | 279 lines; the 73 programme rows are `heading`, the 181 unresolved are `unnamed_item` | |
| `events.csv` | 380 | 380 observations, axis money; the 34 `need` rows become observations of measure `estimate` on their plan lines | subject is the agreement minted from the same line |
| `implementation-events.csv` | 71 | 71 observations on assets or projects after the subject review | `suspended` on a retirement becomes an asset state, not a project stage |
| `project-source-links.csv` | 315 | 315 `refers_to` rows of basis `discovery` or `possible_match` | the 11 `project_page_component` rows become `component_of` relations |
| `source-claims.csv` | 151 | lines and observations; the two finance aggregates become perimeter observations that replace the hard-coded headlines | |
| `config/jetp_observatory.yaml` headlines | 4 | perimeter observations citing their lines | configuration keeps only display choices |

Order of work, each step a ticket with its own byte-level check:

1. Publishers, documents, publications, snapshots. Read-only rename of the
   evidence layer; the observatory's Documents page is the check.
2. Lines and line fields for the four M1a documents, replacing the M1a
   builder's product with the same rows under the new contract. The inventory
   tab is the check: same rows, same order, same fields.
3. Lines for the remaining documents (plan-projects, portfolio, pilot, claims).
4. Identity split: referents, routes, the five identity tables. Every old
   identifier resolves through `routes`. The party table is built here with
   its minimum shape (identifier, name, kind, country, optional external
   identifier from the IATI organisation registry) and the `party_in` relation
   with a role. The 61 funder strings and the register's 14 funder prefixes
   are adjudicated into funder and channel roles in this step; promoter,
   implementing entity, beneficiary and contractor are filled only as their
   lines are reviewed. A party is minted from a line like every other
   identity, so the table cannot grow ahead of the evidence. Decided by the
   author on 2026-09-22.
5. Observations and the status crosswalk, replacing events, implementation
   events and event timing. The Observations tab and each record's evidence
   fold-out are the check.
6. Perimeter observations replace configured headlines.
7. Remove the retired tables and the compatibility readers.

## 7. What the observatory serves

The three-stage MVP (ticket 0834) keeps its shape. Stage one is documents and
snapshots. Stage two is lines, per document, with the publisher's own fields.
Stage three is identities with their observations, each observation opening
the line and the snapshot page it cites. The inventory tab is a view on lines;
the Observations tab is a view on observations; a record page joins at read
time. Every count on a page states its unit. Nothing on a page adds lines of
one document to lines of another or to referents.

## 8. Consequences for the backend design

`jetp-backend-design.md` is revised, not replaced. Its sections 1, 5 to 8 and
10 stand. Sections 2 to 4 adopt the tables above: `entity` becomes the three
identity kinds; `subject_type` gains `line`; `source` becomes publisher,
document and snapshot; `reported-positions` and the event journal merge into
`observations`. Section 9 adopts the migration table above. Per the model
review, the first executable metric is restated as a commitment measure until
a disbursement observation exists, the provenance index of section 8 is
declared a build-time validation artifact and never a served file, and the
editions triple, the alias chain rules, the evidence-dependencies table and the
concept-mapping profile leave the implementation scope until a metric needs
them. Tickets 0762, 0768 and 0769 closed on the previous contract; their
readers are retired at step 7.

## 9. Open questions for the author

None at 2026-09-22 end of day. The three questions this section held, line
identifiers, the party table and the Indonesian edition relation, were decided
the same day (decisions 5 and 6, and section 11).


## 10. Engine

The author asked on 2026-09-22 whether the settled ontology is the moment to
move from CSV files to a graph or SQLite engine. The answer is a division of
labour, not a replacement.

**CSV in git stays the system of record.** The ledger's facts are adjudicated
by reading a diff in a pull request; a database file has no diff, and a
database that is regenerated from files is not a record of anything. The
tables in section 5 are small, about 8 000 rows across twenty files, and will
stay small: the four partnerships publish a few hundred lines a year.

**SQLite becomes the schema, the validator and the build engine.** One DDL file
under `config/` declares every table, key, foreign key and check of section 5.
The CSV headers are generated from it, so a column exists in one place. At
build time the CSVs load into a SQLite file under `data/derived/jetp/`, the
foreign-key and check constraints run as the validator, and the observatory's
served JSON views and the reconciled accounts are SQL queries over that file.
The file is deterministic for a given input, disposable, and may ship as a
downloadable edition artifact through the release mechanism, never as a
committed file. This is what the backend design already reserves as an optional
`<edition_id>.sqlite`, promoted from optional to the build's only query
engine. In the browser the observatory keeps serving one JSON file per table
and joining at read time; at this volume an in-browser SQL engine would add a
dependency without a query that needs it.

**A graph engine is not warranted.** Every question the ledger asks is a
fixed-length path: observation, line, snapshot, document, publisher; or a
containment tree at most three levels deep; or a `same_as` cluster that the
design bounds to depth one. A property graph or triple store wins on
unbounded traversal and on schema-free ingestion, and the ledger wants neither:
its ingestion is the controlled classification of section 4. What the graph
world offers that is worth taking is its vocabulary. An RDF projection of the
SQLite file over PROV-O for the evidence chain and SKOS for the status
crosswalk is a derived export, built when a consumer asks for it, and it costs
one script. If that consumer ever runs SPARQL over several ledgers, the
engine question reopens on their data, not on this one.

## 11. Reconciliation

Reconciliation is the step that mints an identity from lines, attaches a line
to an existing identity, or relates a line to a line in another edition. The
author named it on 2026-09-22 as one of the hard points and set its
requirements: multilingual named-entity recognition over the labels, matching
with a confidence, escalation to a language model and then to human
adjudication, defeasibility, and traceability. The perfect system is not the
target now. What is fixed now is the record, so that a decision taken by the
simplest matcher today and one taken by a person in two years sit in the same
table with the same columns and can be overturned the same way.

**The record.** A `line-referents` row or a `relations` row is a decision. It
carries who or what decided (`decided_by`: a script name, a model identifier,
or a person), by which method and version, with what confidence in [0, 1], on
which evidence lines, and when. Its `status` is `accepted`, `candidate` or
`rejected`. A decision is never edited or deleted: a later row names the
earlier one in `supersedes`, and the ledger serves the newest accepted row
while keeping the chain. A candidate below the acceptance threshold stays a
candidate, counted and visible, as ticket 0833 already requires for its
`possible_matches`; it never alters a count of accepted identities.

**The tiers.** Each tier runs only on what the previous one left undecided,
and each writes its rows with its own method name.

1. Exact identifier: the register's unique id, a plan's ordinal within an
   edition, an operator's project code. Confidence 1. This is the first
   implementation and covers the 257 register rows and the 67 plan lines
   already matched by hand.
2. Normalised label: case, diacritics, technology prefixes and units stripped
   (PLTU, PLTS, PLTBg; Nhà máy Thuỷ điện; centrale, poste), tokens compared
   within a country and a technology group. Confidence from the string
   distance and the agreement of capacity and location where both lines
   carry them.
3. Named-entity recognition over the four label languages, Indonesian,
   Vietnamese, French and English, yielding place, operator, technology and
   capacity as typed spans, matched as tuples. Confidence from the tuple
   agreement.
4. Language-model adjudication of the remaining candidates, given both lines
   and their snapshot pages, returning a verdict, a confidence and a quoted
   basis. The model identifier is the `decided_by`.
5. Human adjudication of what the model declines or contradicts, recorded in
   the same row shape and in `decisions.md`.

Thresholds per tier live in configuration, are versioned with the method, and
are tested on the hand-matched rows as a held-out set before a tier is allowed
to write `accepted` rows. Until a tier passes that test it writes candidates
only.

**Scope of the first implementation.** Tier 1 in the identity split, tier 2 as
a candidate generator whose rows are reviewed by hand, tiers 3 to 5 as method
names reserved in the vocabulary. The Indonesian edition relation between the
437 CIPP lines and the 1 142 progress-report lines, where the literal name
intersection is 3, is the test bed for tier 2 and the first case for tier 3,
and it is not attempted in the migration.

