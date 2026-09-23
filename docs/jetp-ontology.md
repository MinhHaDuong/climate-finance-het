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

The author's decisions of 2026-09-22 and 2026-09-23 shape it:

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
7. Matching is a tiered, defeasible, traceable process (section 11).
   The record format is designed now; the matcher starts at its simplest tier.
8. Translations are managed as document relations and derived text
   (section 12). Automatic summaries and translations are derived aids, never
   justification, and are nice-to-have.
9. After the fit-for-purpose review (review 5): amount semantics are closed
   vocabularies (measure, basis, flow type, modality, period roles); every
   record row carries `recorded_at`; external identifiers and the comparator
   pools (World Bank, CRS, IATI) enter as lines of API snapshots; the
   adjudications and accounts of the backend design keep their tables;
   rates and deflators are sourced records. Section 10's volume projection is
   corrected.
10. After the proofing review (review 6, 36 random pages of 12 documents):
    sector is a shared axis coded with the OECD DAC purpose list and reached
    by crosswalk from each publisher's own scheme; Rio and policy markers
    are a measure with a sourced coefficient table; targets and counts in
    publisher units are measures; roles exist on any subject; lines relate
    to lines; locator syntax is defined per format; a delivery axis for
    agreements is aligned to the IATI activity status list; ranges have
    bounds; a publisher's own modality scheme stays a verbatim field. What
    stays out of scope is named in section 13. The delivery axis and the
    section 13 list were proposed as defaults and approved by the author on
    2026-09-22.
11. On 2026-09-23, after the ODEM acceptance review
    ([`jetp-odem-acceptance-review-2026-09-23.md`](jetp-odem-acceptance-review-2026-09-23.md)):
    the ledger's language is pinned to the ODEM frame (section 0), and five
    confusing terms are retired or restricted, starting with evidence, which
    becomes justification. The observatory has no Model. It is Data guided by
    Ontology, and Evidence comes on top. The four objects organise the
    observatory, and Data reads as a pipeline, but the pages speak the
    reader's language: they assume a reader who knows how empirical work
    proceeds, and never name the framework (section 7). The ontology is a
    set of tables with definitions, external mappings and revisions
    (section 5), and the observatory presents it as its definitions.

## 0. Language: the ODEM frame

ODEM (Ontology, Data, Evidence, Models) is the framework of the author's
design note of 22 September 2026 on interactive causal inquiry. It names four
objects, each versioned, and keeps them apart. The ledger adopts its four
words and uses them in no other sense.

| ODEM object | In the JETP observatory | Where it lives |
|---|---|---|
| **O, Ontology** | What the ledger talks about and how it records it: classes, relations, closed value lists, status and sector axes, perimeter definitions, crosswalks and conversion rules. Every term has a definition, an external mapping where one exists, and a revision history | `data/jetp/ontology/` (section 5); the observatory's Glossary |
| **D, Data** | What publishers said, as the ledger read it. A pipeline of four steps, below | `data/jetp/` tables; the observatory's paper trail: Documents, Entries, On the record, Projects / Funding / Who's who |
| **E, Evidence** | Results computed from D under a declared O version: every count shown with its unit and perimeter, the accounts of backend-design section 5, descriptive tables. E comes on top of D and never edits it | `data/derived/jetp/`, with a run record naming its inputs, cutoffs and ontology version |
| **M, Models** | Candidate causal explanations. The observatory has none. A causal study, deferred in ticket 0729, would consume a frozen release from outside the ledger | none |

The observatory is Data, guided by Ontology. Evidence comes on top.

**D is a pipeline.** Each step reads the steps before it, writes its own
tables and never edits an upstream row.

| Step | Name | Content | Tables |
|---|---|---|---|
| D1 | Register | What was fetched, byte for byte: publishers, documents, retrieval attempts, snapshots, and the record of how they were sought | `publishers`, `documents`, `document-publishers`, `retrievals`, `snapshots`, `coverage`, `dry-searches` |
| D2 | Lines | One publisher's statement at one locator in one snapshot, with its own fields verbatim | `lines`, `line-fields/<document_id>`, `line-field-specs` |
| D3 | Observations | A line read into a typed statement, measure, value and timings, by a named method version | `observations`, `timings`, `external-ids`, `rates`, `deflators` |
| D4 | Referents | Identities minted by matching decisions over lines, and the relations between them | `projects`, `assets`, `agreements`, `parties`, `line-referents`, `relations`, `adjudications`, `adjudication-members`, `routes` |

D3 and D4 both read D2. An observation's subject is a line until matching
attaches that line to a referent. The migration order of section 6 builds D4
before rewriting D3 because the old tables key observations on old
identities.

**Five terms retired or restricted.**

| Term | Use instead | Why |
|---|---|---|
| *evidence*, for documentary support | **justification**: the line and locator a row cites (a justification link, justification lines). *Evidence cutoff* becomes **knowledge cutoff**: rows recorded on or before K | In ODEM, Evidence is the computed result. Documentary support belongs to D |
| *model*, for a schema or a language model | **schema** for tables and columns; **LLM** for a language model used in matching or translation | Model is reserved for ODEM's M, which the observatory does not contain |
| *reconciliation* | **matching** for D4 decisions that mint or attach identities (section 11); **account** for the E computation of opening, movements, closing and residual | One word named two operations at two ODEM levels |
| *edition*, for the ledger's own output | **release** for a frozen package of ledger and site (`data/jetp/releases/<release_id>/`). *Edition* keeps only its document sense: a publisher's successive issue (`edition_of`) | "Evidence edition", "monthly edition" and "document edition" were three different objects |
| *layer*, *stage* (*étage*), *fact* | **step D1 to D4** for the levels of the pipeline; **observation** for what a publisher stated | *Layer* named M1a sub-tables and *stage* the MVP levels; a ledger row is a publisher's statement read by a method, not a fact |

Domain words that coincide are unaffected: a *project stage* is a value of
the OC4IDS axis, and a PDF's *text layer* is its extractable text.

This section governs this document, the observatory's page copy and the
schema: the DDL (ticket 0871) declares no table or column named `evidence`,
`model`, `reconcil*`, `layer` or `fact`. The older design documents
([`jetp-backend-design.md`](jetp-backend-design.md),
[`jetp-backend-implementation-plan.md`](jetp-backend-implementation-plan.md),
[`jetp-storage.md`](jetp-storage.md), [`jetp-tracking.md`](jetp-tracking.md))
predate it and carry a note mapping their terms onto this one.

## 1. Why the current schema fails

The four reviews make the case; the short form is this. The four
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

Terms are ordered from the register outward: who says it, in what, then what it
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

### Retrieval

One attempt to fetch one document at one time: the date, the HTTP outcome,
the headers that matter and, when bytes came back, the fingerprint of the
snapshot they form. This is the current manifest row. A retrieval may fail
and hold no snapshot; two retrievals may return the same bytes and share one
snapshot, as the manifest already shows with a `not_modified` re-fetch three
minutes after a collection.

### Snapshot

Exact bytes under a SHA-256 fingerprint, with the storage path. A snapshot
belongs to the documents whose retrievals returned it, which for a mirror is
two. A statement in the ledger cites a snapshot, never a URL or a retrieval,
so that what was read can be re-read.

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

Reading a line into observations is itself a method. For a register or a
plan appendix the observations are generated by a rule per document type,
one version of which is named on every observation it writes, so that a
changed rule is a new method version and its observations supersede the old
ones under section 11's record. A hand-written observation names its author
instead.

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

An agreement carries a `modality`, the OECD DAC type-of-aid code that Paper A's
result turns on: budget support (A01, A02), core contributions (B01 to B04),
project-type interventions (C01), experts and technical assistance (D01,
D02), scholarships (E01), debt relief (F01), and `unknown` when no line states
it. Modality is a classification assigned from a line through a referent
decision, never inferred from the instrument word. Loan terms, interest rate,
maturity, grace period and the resulting grant element, are observations on
the agreement, because a publisher reports them at a date and another may
contradict them. A conditionality is an observation on the agreement of
measure `condition`, whose value is the condition as printed and whose
`concerns` relation names the party it binds, so that an AFD loan tied to a
tariff reform at Senelec is one agreement, one condition, one party.

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
Membership is a justified relation, not a list. A count slot is a perimeter observation,
"this publisher counted 24 at this date", not 21 rows in a registry.

### External identifier

A code another register uses for one of the ledger's identities or lines: a
World Bank P-number, a CRS `crs_id` or `donor_project_id`, an IATI activity
identifier, a GEM unit id, an OECD organisation id for a party. One table
holds them all, typed by scheme, so a comparator record and a ledger
identity meet on a key rather than on a name.

### Comparator record

A record from an external database admitted to the register: a World Bank
project from the projects API, a CRS activity, an IATI activity. It is a
line of a snapshot whose document is the dataset edition and whose publisher
is the institution, with its own fields verbatim, its identifiers in the
external-identifier table and its statuses crosswalked like any publisher's.
The 97 closed World Bank energy operations of the reference pool are such
lines; nothing in the ledger treats them as projects of the partnership.

### Observation

One dated statement about one subject, cited to one line: a flow on an
agreement, a state of an asset, a stage of a project, a capacity, an estimate
on a plan line, a count on a perimeter, an envelope on a partnership. The
subject is typed, `(subject_kind, subject_id)`, and may be a line itself when
no identity has been minted. An observation has one or more timings, each
with a role (event, approval, reporting cutoff, register date, report date,
planned), a precision and bounds, so that an approval known only to the year
and the cutoff of the report that states it are both kept. Values are the
publisher's, in the publisher's unit and currency; conversion is a
derivation through the sourced `rates` table. An observation names its
`measure` from the closed list of section 4, its `basis` (gross, net,
unknown) where money is involved, and its `flow_type` from the IATI list when
the measure is a flow. It carries `recorded_at`, the date the ledger wrote
it, and the same `status` and `supersedes` as a decision row, so a corrected
publication is a new observation that supersedes the old one and an as-of
state at cutoff K is the set of rows recorded on or before K and in force.
Subjects also include `country`, for the macro-fiscal indicators the
absorbability block reads (GDP, external debt, a utility's debt ratio on a
`party`), each with its indicator code from the publisher's own list.

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
| `same_as` (document) | document | document | one publication under two URLs or two exports; the lines belong to the canonical one |
| `translation_of` | document | document | the same publication in another language; lines are extracted from one and cross-referenced, never doubled |
| `retrieval_of` | retrieval | document | one fetch attempt |
| `yields` | retrieval | snapshot | the bytes a successful retrieval returned; absent on failure |
| `in_snapshot` | line | snapshot | with locator and ordinal |
| `groups` | line | line | a heading line groups the lines under it in the same document |
| `refers_to` | line | project, asset, agreement, party, perimeter | the reviewed match that minted or attached an identity; dated; never deletes the line |
| `component_of` | project | project | containment; acyclic |
| `part_of` | asset | asset | unit within plant |
| `concerns` | project | asset | zero or more |
| `finances` | agreement | project | many-to-many |
| `tranche_of` | agreement | agreement | at most one active parent |
| `party_in` | party | agreement | one row per role; a party may fund one agreement and channel another |
| `role_in` | party | project, asset, perimeter, document, line | a mandate outside any agreement: lead agency, coordinating agency, guarantor, endorser, signatory, host, standards body; one row per role |
| `same_as` (line) | line | line | the same published item in two places: a CRS activity across reporting years (keyed on donor and donor project id), one amount printed in a headline, a table and a chart |
| `cites` (line) | line | document, line | a document's reference to another document or to a line of it, held or not |
| `member_of` | line, project, asset, agreement | perimeter | dated, justified membership; a line may be a member before any identity is minted |
| `same_as` | any | same kind | a justified equality claim; does not choose a route |
| `about` | observation | any subject | typed |
| `cites` | observation | line | exactly one |
| `timed` | observation | timing | one row per date role; the amount lives once on the observation |

## 4. Line classifications and status axes

A line's classification says what kind of statement it is, in the publisher's
own terms, from a closed list:

`named_item`, `unnamed_item`, `quota`, `heading`, `submission`, `evaluation`,
`register_allocation`, `count`, `envelope`, `absence`.

The list is grown when a publisher's practice needs a value; it is never
inferred from the label.

**Sector** is a shared axis, coded with the OECD DAC CRS purpose list (five
digits; the 231 to 236 group covers energy policy, generation by source,
distribution and efficiency), because CRS records carry it, IATI uses it by
default and the World Bank taxonomy crosswalks to it. It is handled like a
status axis: the publisher's own word, a South African window, an
Indonesian technology group, a plan appendix's label, a World Bank sector
code, stays verbatim on the line, and a reviewed, dated `sector-crosswalk`
row maps each publisher scheme onto a purpose code. Sector appears on a line
as `own_sector`, on an agreement and a project as `sector` assigned through
a referent decision, and on an observation by inheritance from its subject.
Technology is a separate attribute of assets, aligned to the Global Energy
Monitor list: a sector says what the money is for, a technology says what
the plant is.

The `measure` of an observation is from a closed list, extended by decision:

| Axis | Measures |
|---|---|
| money | `amount` (a state's amount, with `own_status`), `flow` (with `flow_type`: pledge, commitment, disbursement, expenditure, from IATI), `estimate` (a plan cost, no funder), `envelope` (a partnership or portfolio total), `interest_rate`, `maturity_years`, `grace_years`, `grant_element`, `condition` |
| physical | `capacity` (with unit), `length`, `state`, `target` (a physical or social objective with a `target` timing, such as a renewable share by 2030) |
| counting | `count` (with the publisher's unit named: rows, locomotives, officials trained, households), `absence` |
| macro | `indicator` (with the publisher's indicator code) |
| marker | `marker` (the publisher's policy-marker score: Rio mitigation, adaptation, biodiversity, desertification, and non-Rio markers such as gender; value 0, 1 or 2, or `not_screened` when the field is blank, which is not 0) |

A marker is the donor's own scoring of an activity, at a reporting year,
under the marker definition of that year. The "climate finance" that a
marker yields is the score times a coefficient, 100 percent for principal
and 40, 50 or 100 percent for significant depending on the donor and the
year; the coefficient is a rule, not an observation, so it belongs to the
ontology (section 0). It is recorded in the sourced `marker-coefficients`
table and applied only in a derived account, so that the same loan can be shown moving from 40 to 100 percent climate finance
without any change in the loan. A value may be a range: `value_low` and
`value_high` bound it, as the timing bounds bound a date, and a scalar has
both equal.

Money observations carry a `basis`, gross, net or unknown, and a flow carries
its interval through two timing roles, `period_start` and `period_end`, so a
quarterly register total states the quarter it covers and the account
of section 5 of the backend design can test coverage. A point flow has one
`event` timing.

Four shared status axes, each sourced from an external list and extended only
where the four publishers' practice requires it:

| Axis | Subject | External list | Local additions |
|---|---|---|---|
| project stage | project | OC4IDS `projectStatus`: identification, preparation, implementation, completion, maintenance, decommissioning, decommissioned, cancelled | none |
| asset state | asset | Global Energy Monitor: announced, pre-permit, permitted, construction, shelved, cancelled, operating, mothballed, retired | `retirement_proposed`, `retirement_agreed` |
| money | agreement | states: announced, mou, approved, signed, cancelled, withdrawn; flows: IATI pledge, commitment, disbursement, expenditure | none |
| delivery | agreement | IATI activity status: pipeline, implementation, finalisation, closed, cancelled, suspended | none; the South African register's letters A to D crosswalk here |
| comparator statuses | comparator lines | World Bank project status (pipeline, active, closed, dropped), CRS and IATI activity status | crosswalked onto the axes above, never merged |

The publisher's own words, all of them, are kept: the register's `A. Planned`
to `D. Completed`, Indonesia's modality and approval, Viet Nam's published or
not published, Senegal's submitted, evaluated and quick win. Each maps through
the crosswalk to at most one axis. A publisher's own scheme that reuses a
word of this design, such as Indonesia's "Modality A" and "Modality B",
stays a verbatim field of the line; `modality` on an agreement is only ever
the DAC type-of-aid code. Where a publisher reports one axis only, the
other two are absent for that line. The reviews established that today each
country populates one axis: South Africa the money axis with the delivery axis
discarded, Indonesia approval, Senegal estimates, Viet Nam none. The ledger
states this rather than filling it.

## 5. Storage contract

One file is one table, joins happen at read time, nothing is materialised
(ticket 0858, kept). Data tables under `data/jetp/`, ontology tables under
`data/jetp/ontology/` (below), CSV, columns in this order.
A table too large for the repository's file ceiling, 512 000 bytes per
file in `.githooks/pre-commit`, is chunked by country and year into
`<table>/<CODE>-<year>.csv`, which stays one table.

| Table | Key | Columns |
|---|---|---|
| `publishers` | `publisher_id` | name, authority_category, country, notes |
| `documents` | `document_id` | country, document_type, language, title, url, published_date, edition_of, active, notes |
| `document-publishers` | (document_id, publisher_id) | role |
| `retrievals` | `retrieval_id` | document_id, retrieved_at, status, http_status, content_type, etag, last_modified, final_url, error, sha256 (nullable) |
| `snapshots` | `sha256` | storage_path, size_bytes, content_type |
| `lines` | `line_id` | country, sha256, locator, ordinal, label, classification, own_status, own_status_axis, own_sector, groups, recorded_at, notes |
| `line-fields/<document_id>` | `line_id` | the document's own columns, verbatim, header as printed |
| `projects` | `project_id` | country, canonical_name, aliases, classification, classified_at, sector, notes |
| `assets` | `asset_id` | country, name, technology, location, operator_party_id, part_of, notes (capacity is an observation, never a column) |
| `agreements` | `agreement_id` | country, instrument, modality, sector, currency, tranche_of, notes |
| `parties` | `party_id` | name, kind, country, publisher_id |
| `line-referents` | `referent_row_id` | line_id, referent_kind, referent_id, status, method, method_version, confidence, justification_line_ids, decided_at, decided_by, supersedes, notes |
| `relations` | `relation_id` | from_kind, from_id, relation, to_kind, to_id, role, valid_from, valid_to, status, method, method_version, confidence, decided_at, decided_by, supersedes, line_id |
| `observations` | `observation_id` | subject_kind, subject_id, axis, measure, flow_type, basis, value, value_low, value_high, unit, currency, own_status, indicator_code, line_id, method, method_version, recorded_at, status, supersedes, notes |
| `timings` | `timing_id` | observation_id, date_role, date, date_precision, lower_bound, upper_bound, line_id, recorded_at |
| `external-ids` | (scheme, external_id) | kind, id, line_id, recorded_at |
| `adjudications` | `adjudication_id` | decision_type (occurrence membership, flow coverage, perimeter compatibility, identity), subject_kind, subject_id, verdict, status, decided_at, decided_by, supersedes, notes |
| `adjudication-members` | (adjudication_id, kind, id) | role |
| `rates` | (currency, date, basis) | rate_to_usd, line_id, recorded_at (a publisher's own conversion, printed beside the original, is a `rates` row citing that line, so the ledger records that the publisher converted, at what rate) |
| `deflators` | (series, year) | value, line_id, recorded_at |
| `line-field-specs` | `document_id` | the ordered list of a document's own column names, written at extraction, against which each `line-fields/<document_id>` header is validated |
| `routes` | `old_id` | kind, new_id |
| `coverage` | (referent_kind, referent_id) | review_status, checked_at, route, document_ids, notes |
| `dry-searches` | as today | |
| `decisions.md` | as today | |

### Ontology tables

The ontology is data about the ledger's words, stored like the ledger itself:
one CSV per table under `data/jetp/ontology/`, reviewed by diff, revised by
supersession and never edited in place. Each table is keyed by a row
identifier; the column in *italics* is the chain key that successive
revisions of one entry share.

| Table | Key | Columns |
|---|---|---|
| `terms` | `term_row_id` | *term_id*, kind, list, label, definition, scope_note, domain, range, external_scheme, external_uri, mapping_relation, recorded_at, decided_by, status, supersedes, notes |
| `status-crosswalk` | `crosswalk_row_id` | *(publisher_id, own_status)*, axis, shared_status, recorded_at, decided_by, status, supersedes, notes |
| `sector-crosswalk` | `crosswalk_row_id` | *(publisher_id, own_sector)*, purpose_code, recorded_at, decided_by, status, supersedes, notes |
| `perimeters` | `perimeter_row_id` | *perimeter_id*, country, name, scope, definition, recorded_at, decided_by, status, supersedes, notes |
| `marker-coefficients` | `coefficient_row_id` | *(donor_party_id, marker, score, year)*, coefficient, line_id, recorded_at, status, supersedes |

**Definition.** Every word the schema admits as a value is a `terms` row: the
classes and relations of sections 2 and 3, the line classifications, measures,
bases, flow types, modalities, date roles, roles, axes and axis values of
section 4. `kind` says which (class, relation, value); `list` names the closed
list a value belongs to. The definition is plain English, one or two
sentences, written for a reader of the observatory. A relation term also
states its `domain` and `range`. The DDL's checks read the terms in force; no
script or configuration file carries its own copy of a list.

**Traceability.** A term taken from an external vocabulary names its scheme
(IATI, OC4IDS, GEM, OECD DAC, PROV-O, SKOS), the concept's URI or code, and a
`mapping_relation` from SKOS: `exactMatch`, `closeMatch`, `broadMatch`,
`narrowMatch`, `relatedMatch`, or `local` for a word the ledger defines
itself. Similar labels do not justify `exactMatch`. A crosswalk row maps a
publisher's word onto a term; a perimeter row defines a population that
counts are made against. Both name who decided and when.

**Revision.** The in-force rule of the decision tables applies: a row is in
force when it is the accepted terminal row of its chain. Rewording a
definition or correcting a mapping supersedes the row under the same chain
key. A change of meaning mints a new `term_id` or `perimeter_id`, and the old
one stays valid for every row that used it; a count made against the old
perimeter is never silently moved to the new one. The ontology as of cutoff K
is the set of rows in force at K, so an as-of query reconstructs the words as
well as the data. `decisions.md` keeps the reasons in prose and cites the row
it explains.

**Reference from E.** Every derived result records an `ontology_ref`, the
hash of `data/jetp/ontology/` and of the DDL it was computed under, beside its
run identifier and its two cutoffs. A result is never recomputed under a
later ontology without a new run record.

### English and formal specification

This document is the English specification: it gives the reasons and the
rules. The formal specification is the DDL of section 10 together with the
`terms` table. Nothing else is: no OWL file, no SHACL shapes and no second
prose glossary. Alignment is checked, not trusted. A test (ticket 0880) fails
when a value listed in sections 2 to 4 is not a term in force, or a term in
force appears nowhere in this document, and when a table or column declared
here differs from the DDL. The observatory's Glossary and a SKOS export
(section 10) are generated from the `terms` table, so the words a reader sees
are the words the validator enforces.

LinkML was considered as the single source instead, generating the DDL, JSON
Schema, OWL and documentation from one YAML file. It is not adopted now,
because it adds a toolchain whose extra outputs have no consumer. The question
reopens when an external consumer asks for OWL or JSON Schema.

Accounts, the openings, movements, closings, residuals and
coverage gaps per agreement or perimeter that section 5 of the backend
design defines, are derived: they are computed from observations, timings,
rates and adjudications at build time, written under `data/derived/jetp/`
with the run identifier, the two cutoffs (valid time and knowledge) and
the `ontology_ref`, and never edited. The adjudications they depend on are records, in the table above.

Rules that the validator enforces:

- An observation cites exactly one line and its subject exists.
- A line's `sha256` exists in `snapshots`, the bytes exist in the store, and
  at least one retrieval of the line's document yields that snapshot.
- A decision row (`line-referents`, `relations`) is in force only when it is
  the terminal row of its supersession chain and its status is `accepted`.
  A chain is linear: a row supersedes at most one row and is superseded by at
  most one. A terminal `rejected` row revokes whatever its chain previously
  accepted, with no replacement needed; a terminal `candidate` row is
  pending and not in force; an `accepted` row that any row supersedes is no
  longer in force. The same rule governs document deduplication, so a
  rejected `same_as` re-enables extraction of the document it had folded.
- An observation carries no date of its own. Each date it reports is a
  `timings` row with its role, precision and bounds; a value is stored once
  and never repeated per date role. A flow carries `period_start` and
  `period_end` or one `event` timing.
- Every record row in `lines`, `observations`, `timings`, `external-ids`,
  `rates`, `deflators` and every decision table carries `recorded_at`. An
  as-of state at cutoff K is the set of rows with `recorded_at` on or
  before K that are in force under the supersession rule.
- `measure`, `basis`, `flow_type`, `modality`, `classification`, `relation`,
  `date_role` and every axis take values from the terms in force (ontology
  tables, above); a new value is a `terms` row, with its definition, before
  the validator accepts it.
- A monetary conversion cites a `rates` row; a script never carries a rate.
- A locator has a syntax per format, and the validator checks it: for a
  PDF, the PDF page index and the printed folio when one exists, then the
  table and row for a table cell or a text anchor of at most 80 characters
  for prose; for HTML, a CSS path or a text anchor, never a byte offset;
  for an API snapshot, the record key (an SDMX key for CRS, a P-number for
  the World Bank, an activity identifier for IATI). A value printed in three
  places is three lines related by `same_as`.
- A publisher's cell that lists several names stays verbatim in the
  per-document fields table; the no-list rule applies to the ledger's own
  columns, and the parties in such a cell are minted through `role_in` or
  `party_in` rows, one per name, citing the line.
- A publisher's method note that governs a page or a table (a pro-rating,
  an exchange-rate policy, a footnote conditioning every row) is a line of
  classification `heading` that `groups` the lines it governs, so that an
  observation reads the note through its line.
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
`document-publishers`), `manifest.csv` (becomes `retrievals` and `snapshots`),
`plan-projects.csv` (lines), `events.csv` and `implementation-events.csv`
(observations), `project-source-links.csv` (lines with classification
`named_item` and a `refers_to` of basis `discovery`), `source-claims.csv`
(lines of classification `envelope`, `count`, `absence` or `heading`, with
observations), `idn-portfolio-observations.csv`, `vnm-pilot-manifest.csv` and
`vnm-pilot-observations.csv` (lines and observations of their documents),
`project-coverage.csv` and `authority-coverage.csv` (`coverage`),
`data/jetp/comparison/*.json` (documents of publisher World Bank, one snapshot
per API response, lines per record, P-numbers in `external-ids`),
`event-timing.csv` (becomes `timings`, one row per date role of an observation). The M1a
inventory builder becomes the line ingestion for its four documents; the
frozen M1a release stays as the archived release it is.

## 6. Migration

The migration is a rebuild from snapshots, not a rename of columns. Each
current table is read once, its rows become lines and observations under the
target contract, and the result is checked against the current served views
before the current tables are removed. Counts below are from the tables on
2026-09-22.

| Current | Rows | Target | Notes |
|---|---|---|---|
| `sources.csv` | 301 | 103 publishers, 301 documents, 301 publications | joint publications added by review, none derivable from the free text |
| `manifest.csv` | 314 | 314 retrievals, 264 snapshots | 41 failed retrievals carry no snapshot; 9 snapshots are yielded by two retrievals each |
| `projects.csv` ZAF register | 257 | 257 lines of the Q1 2026 register, `register_allocation`; 257 agreements minted by basis `register_row`; projects minted only where the reviewed name match holds | the register's own status letter becomes `own_status`, axis delivery |
| `projects.csv` VNM count slots | 21 | 1 perimeter, 2 observations of measure `count` (7 initial, 17 screened) citing the portfolio lines | routes for the 21 slot identifiers point at the perimeter |
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
| `config/jetp_tracking.yaml` vocabularies and the value lists of sections 2 to 4 | about 98 lines of YAML | `terms` rows under `data/jetp/ontology/`, each with a definition and, where one exists, an external mapping | the YAML keeps display choices only |
| `news-leads.csv` | 18 | kept as today: a working file of the watch, not a ledger table | named as not served, with that reason, on the observatory's How we did this page |
| figure scripts' inline exchange rates | 1 known (`2500 * 1.09`) | `rates` rows citing their source line | a script never carries a rate |

Order of work, each step a ticket with its own byte-level check:

0. Ontology tables: `terms`, the two crosswalks, perimeters and marker
   coefficients under `data/jetp/ontology/`, with their revision columns and
   the alignment test of section 5 (ticket 0880). Built right after the DDL
   tooling (ticket 0871), whose value checks then read the terms in force.

1. Publishers, documents, publications, snapshots. Read-only rename of the
   register (step D1); the observatory's Documents page is the check.
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
   identity, so the table cannot grow ahead of its justification. Decided by the
   author on 2026-09-22.
5. Observations and the status crosswalk, replacing events, implementation
   events and event timing. The Observations tab and each record's justification
   fold-out are the check.
6. Perimeter observations replace configured headlines.
7. Remove the retired tables and the compatibility readers.

## 7. What the observatory serves

The four ODEM objects of section 0 are the observatory's organising
principle: they decide what is grouped with what, in which order, and what
may link to what. They are not its vocabulary. The pages assume a reader who
knows how empirical work proceeds, that a figure rests on documents and that
words need definitions, and they never put the framework's names in front of
that reader. "Ontology", "Evidence", "Model", the letters O, D, E, M and the
step codes D1 to D4 appear in code, data attributes and these documents, not
in page copy.

The page vocabulary is a newsroom's, decided by the author on 2026-09-23:
data desks organise document-based work the same way, and their words are
plain. It keeps to the neutral side of that vocabulary, attribution rather
than suspicion, because the readers are researchers as well as journalists.

| ODEM object | What the reader sees | Label on the page |
|---|---|---|
| O | What each word, status, measure and relation means, where the definition comes from, and when it changed | **Glossary** |
| D | The documented route from a figure back to the page that supports it, walked in both directions | **The paper trail**: **Documents** → **Entries** → **On the record** → **Projects**, **Funding**, **Who's who** |
| E | Counts and totals computed by the ledger, each with its unit, its perimeter and a link to what it was computed from | **By the numbers** |
| M | Nothing | none |
| (methods) | What was done, what was not, and which tables are not served | **How we did this** |

- **Glossary.** The terms in force, grouped by list: each class, relation
  and value with its definition, its external source and its revision
  history. A relation shows what it connects. Every term used elsewhere on
  the site links to its glossary entry. Generated from `data/jetp/ontology/`.
- **The paper trail.** Documents is D1 (publishers, documents, retrievals,
  snapshots). Entries is D2: a row of a register, a line of a plan annex, a
  submission in a list. On the record is D3: each item reads "according to"
  its publisher, with the date. Projects, Funding and Who's who are D4:
  projects and assets, agreements, and parties. Each page shows where it
  sits on the trail and lets the reader step one stage up or down, from a
  project to what is on the record about it, to the entries, to the page of
  the document, and back.
- **By the numbers.** A number the ledger computes is visibly set apart from
  a number a publisher printed: it states its unit and perimeter and opens
  the items on the record it was computed from. Accounts, when they exist,
  appear only here.
- **No models.** The observatory tests no causal explanation, and its
  navigation has no place for one. How we did this says in plain words what
  the observatory does not do.

Words avoided on the pages: *claims* (it implies doubt about a publisher's
statement), *deals* and *players* (loaded), *sources* (a source is also a
person, and the ledger retired the word), *entities* and *records* (opaque to
a general reader).

Every table of section 5 is served, one file per table, or named on How we
did this as not served, with the reason. Nothing on a page adds lines of one
document to lines of another or to referents.

## 8. Consequences for the backend design

`jetp-backend-design.md` is revised, not replaced. Its sections 1, 5 to 8 and
10 stand. Sections 2 to 4 adopt the tables above: `entity` becomes the three
identity kinds; `subject_type` gains `line`; `source` becomes publisher,
document and snapshot; `reported-positions` and the event journal merge into
`observations`. Its section 5 accounts keep their adjudications as the
`adjudications` and `adjudication-members` tables and their accounts as
derived outputs (section 5 above). Section 9 adopts the migration table above. Per the schema
review, the first executable metric is restated as a commitment measure until
a disbursement observation exists, the provenance index of section 8 is
declared a build-time validation artifact and never a served file, and the
source-editions triple, the alias chain rules, the dependency table between justifications (`evidence-dependencies` there) and the
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

**CSV in git stays the system of record.** The ledger's rows are adjudicated
by reading a diff in a pull request; a database file has no diff, and a
database that is regenerated from files is not a record of anything. The
tables in section 5 hold about 8 000 rows today, but they will not stay
small: every edition is a new document and lines are appended, never
renumbered. A monthly register edition adds about 3 000 lines a year for
South Africa alone, the Indonesian plan appendices add 1 500 per edition
pair, and the comparator pools add 1 100 World Bank records now and, for the
four countries' energy sector, about 8 000 CRS rows and 1 800 IATI
activities. The steady state is tens of thousands of lines a year, and the
record format has to be designed for it, in two ways. Lines of hand-read
documents stay per-document files reviewed row by row in a pull request.
Lines of bulk API snapshots are written by the ingestion script with a
manifest naming the snapshot, the row count and the field spec, and the
pull request reviews the manifest; a bulk line is adjudicated only when an
observation cites it. The common `lines` table is chunked by country and
year. Review by diff holds where it matters, on what the ledger asserts, and
not on what a database published.

The one DDL of section 5 declares the common tables. It does not declare
the per-document field tables, whose headers are the publisher's; each is
declared by its row in `line-field-specs`, written at extraction, and the
validator checks the file header against it. Two mechanisms, one contract.

**SQLite becomes the schema, the validator and the build engine.** One DDL file
under `config/` declares every table, key, foreign key and check of section 5.
The CSV headers are generated from it, so a column exists in one place. At
build time the CSVs load into a SQLite file under `data/derived/jetp/`, the
foreign-key and check constraints run as the validator, and the observatory's
served JSON views and the accounts (E) are SQL queries over that file.
The file is deterministic for a given input, disposable, and may ship as a
downloadable release artifact, never as a
committed file. This is what the backend design already reserves as an optional
`<release_id>.sqlite` (`<edition_id>` there), promoted from optional to the build's only query
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
SQLite file over PROV-O for the justification chain and SKOS for the status
crosswalk is a derived export, built when a consumer asks for it, and it costs
one script. If that consumer ever runs SPARQL over several ledgers, the
engine question reopens on their data, not on this one.

## 11. Matching

Matching is the step that mints an identity from lines, attaches a line
to an existing identity, or relates a line to a line in another edition. The
author named it on 2026-09-22 as one of the hard points and set its
requirements: multilingual named-entity recognition over the labels, matching
with a confidence, escalation to a large language model (LLM) and then to human
adjudication, defeasibility, and traceability. The perfect system is not the
target now. What is fixed now is the record, so that a decision taken by the
simplest matcher today and one taken by a person in two years sit in the same
table with the same columns and can be overturned the same way.

**The record.** A `line-referents` row or a `relations` row is a decision. It
carries who or what decided (`decided_by`: a script name, an LLM identifier,
or a person), by which method and version, with what confidence in [0, 1], on
which justification lines, and when. Its `status` is `accepted`, `candidate` or
`rejected`. A decision is never edited or deleted: a later row names the
earlier one in `supersedes`, and what is in force is the terminal row of the
chain when its status is `accepted` (section 5, rules). A reviewer revokes a
false match by appending a `rejected` row that supersedes it; nothing else
has to be minted for the revocation to take effect. A candidate below the
acceptance threshold stays a candidate, counted and visible, as ticket 0833
already requires for its `possible_matches`; it never alters a count of
accepted identities.

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
4. LLM adjudication of the remaining candidates, given both lines
   and their snapshot pages, returning a verdict, a confidence and a quoted
   basis. The LLM identifier is the `decided_by`.
5. Human adjudication of what the LLM declines or contradicts, recorded in
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

**Document deduplication.** The same matching record applies one level
up, to documents, and runs before any line is extracted, because a duplicate
document extracted twice doubles every line and every count downstream. The
registry already holds three mirrors and two repeated titles; the harvests
will add re-exported PDFs, pages that change a timestamp on every retrieval,
and the Vietnamese and English versions of one plan. The relations are
`same_as` between documents for one publication under two URLs or two exports,
`edition_of` for succession, and `translation_of` for the same publication in
another language. Lines are extracted from the canonical document of a
`same_as` cluster and from one language of a translation pair, and the other
members keep their snapshots as citable bytes. The tiers, in the same row
shape and with the same defeasibility:

1. Identical fingerprint under two documents: one snapshot, two URLs.
   Confidence 1.
2. Identical extracted text after normalisation, or a near-duplicate hash of
   the text layer with the same page count. Catches the re-export and the
   timestamped page.
3. Metadata agreement: title, publisher, publication date, page count, and
   any identifier the document prints. Catches the mirror hosted by a partner
   and the translation, when paired with a language detector.
4. LLM adjudication of the remaining pairs, given both first pages.
5. Human adjudication.

The first implementation is tiers 1 and 2 at harvest time, so a snapshot
whose text already exists is registered as a `same_as` candidate before it is
extracted; tier 3 as a candidate generator on the current 301 documents.

## 12. Language, translation and summaries

The four partnerships publish in Indonesian, Vietnamese, French and English,
and some documents exist in two languages. The ledger records the language of
every document and keeps every line's label in the language it was printed
in. A translation pair is two documents related by `translation_of`, with one
of them canonical for extraction (section 11). Nothing in the ledger is a
translation presented as an original.

Translated labels and summaries are derived text, produced by an LLM or a
person, stored under `data/derived/jetp/` in two tables, regenerable and
outside the system of record:

| Table | Key | Columns |
|---|---|---|
| `line-translations` | (line_id, language) | text, method, method_version, produced_at |
| `document-summaries` | (document_id, language) | text, method, method_version, produced_at, snapshot_sha256 |

Both carry the provenance columns of the matching record, so a served
translation can say which LLM produced it from which bytes. The observatory
may show a translated label beside the original and a machine summary on a
document's page, each marked as derived, and a reader who clicks through
reaches the snapshot in its own language. No observation cites a translation
or a summary; the justification is the line in the publisher's language, at its
locator, in its snapshot. The first implementation is the language column and
the translation relation; the two derived tables are nice-to-have and wait for
a reader who needs them.

## 13. Out of scope, by decision

The proofing review read 36 random pages of 12 documents and found 23
percent of their information items not representable. The following classes
are out of scope by decision on 2026-09-22, because no paper reads them, and
the ledger says so rather than holding them badly:

- institutional events (a body founded, launched, staffed, merged) and
  party-to-party relations other than `role_in` and `party_in`;
- natural persons as signatories or delegates, distribution lists, seals
  and embedded signatures;
- values that exist only in a chart with no byte in the snapshot's text
  layer, until a transcription with provenance (section 12) is a line;
- a document as the subject of a statement (what a regulation says or is
  silent on), which is a citation between lines, not an observation;
- recurrence ("every year") and dates deferred to another plan's schedule;
- a publisher's own liabilities and budget;
- physical outcomes beyond capacity, length and state: emissions, jobs,
  people, generation, tonnage, hectares. When a paper needs one, it enters
  as a measure by decision with its unit and the IPCC or ILO list it maps to.

A scan with no text layer (the Vietnamese decision of 2026 is one) is
extracted by transcription, and each of its lines names the transcription
as its method and version, so that the label has the provenance the
translation tables give derived text.

