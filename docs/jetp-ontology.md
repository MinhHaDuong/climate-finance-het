# JETP ledger ontology

Status: design for author review, 2026-09-22. Version 2 of the ontology first
drafted the same day and reviewed by four independent panels
([`jetp-study/ontology-review-2026-09-22/`](jetp-study/ontology-review-2026-09-22/)).
It fixes what the ledger talks about: its classes, relations, value lists and
status axes, and the ontology tables that define and revise them. Three
documents carry the design, split on 2026-09-23 at the author's request:

- this one, the ontology;
- [`jetp-ledger-storage.md`](jetp-ledger-storage.md), the storage contract: tables, validation rules, engine, matching, translations, and the consequences for [`jetp-backend-design.md`](jetp-backend-design.md);
- [`jetp-ledger-migration.md`](jetp-ledger-migration.md), the migration from the current tables, which the 0870 train consumes.

The decisions below govern all three.

The author's decisions of 2026-09-22 and 2026-09-23 shape it:

1. Split the identity registry now rather than tag it. The current
   `projects.csv` mixes four kinds of row; a column would only name the mix.
2. The published line is the first-class unit, and its storages are unified.
3. Statuses follow each publisher's practice. The publisher's word is stored
   verbatim and crosswalked; it is never overwritten or inferred.
4. Design the target, then migrate. No incremental patching of the current
   tables.
5. Line identifiers are minted, not keyed on fingerprint and locator
   ([storage contract](jetp-ledger-storage.md) section 1).
6. The party table is built in the identity split, minimal, with funder and
   channel roles populated first ([migration](jetp-ledger-migration.md), step 4).
7. Matching is a tiered, defeasible, traceable process ([storage contract](jetp-ledger-storage.md) section 4).
   The record format is designed now; the matcher starts at its simplest tier.
8. Translations are managed as document relations and derived text
   ([storage contract](jetp-ledger-storage.md) section 5). Automatic summaries and translations are derived aids, never
   justification, and are nice-to-have.
9. After the fit-for-purpose review (review 5): amount semantics are closed
   vocabularies (measure, basis, flow type, modality, period roles); every
   record row carries `recorded_at`; external identifiers and the comparator
   pools (World Bank, CRS, IATI) enter as lines of API snapshots; the
   adjudications and accounts of the backend design keep their tables;
   rates and deflators are sourced records. The storage contract's section 3 volume projection is
   corrected.
10. After the proofing review (review 6, 36 random pages of 12 documents):
    sector is a shared axis coded with the OECD DAC purpose list and reached
    by crosswalk from each publisher's own scheme; Rio and policy markers
    are a measure with a sourced coefficient table; targets and counts in
    publisher units are measures; roles exist on any subject; lines relate
    to lines; locator syntax is defined per format; a delivery axis for
    agreements is aligned to the IATI activity status list; ranges have
    bounds; a publisher's own modality scheme stays a verbatim field. What
    stays out of scope is named in section 6. The delivery axis and the
    section 6 list were proposed as defaults and approved by the author on
    2026-09-22.
11. On 2026-09-23, after the ODEM acceptance review
    ([`jetp-odem-acceptance-review-2026-09-23.md`](jetp-odem-acceptance-review-2026-09-23.md)):
    the ledger is Data guided by Ontology, Evidence comes on top, and there
    is no Model (section 0). The ontology is a set of tables with
    definitions, external mappings and revisions (section 5). The builders'
    language, including five retired terms, is
    [`jetp-language.md`](jetp-language.md); the observatory's organisation
    and page vocabulary are
    [`jetp-observatory-presentation.md`](jetp-observatory-presentation.md).

## 0. Frame

The ledger is the Data of the ODEM frame (Ontology, Data, Evidence, Models),
guided by the Ontology this document defines; Evidence is computed on top,
and there is no Model. Data is a pipeline of four steps: D1 register, D2
lines, D3 observations, D4 referents. The frame, the step-to-table map and the
terms the design documents and schema use or avoid are
[`jetp-language.md`](jetp-language.md). What readers of the observatory see is
[`jetp-observatory-presentation.md`](jetp-observatory-presentation.md).

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
authority category, `national_government`, `jetp_secretariat`, `ipg`,
`bilateral_funder`, `multilateral_funder`, `private_finance`, `operator` or
`secondary_source`, and a country (`ZAF`, `IDN`, `VNM`, `SEN`) or
`international`. The registry holds 103 distinct publishers today,
as free text in a column.

A publisher is what the project has so far called a source. The word source is
retired from column names and page copy, because it has meant a URL since the
first harvest.

### Document

A logical publication: a title, a document type, a canonical URL, and one
or more publishers. The document types are `political_declaration`,
`investment_plan`, `implementation_plan`, `annual_report`, `progress_update`,
`project_list`, `project_page`, `approval_document`, `financing_agreement`,
`operator_report`, `official_news`, `secondary_news` and `data_portal`. The Resource Mobilisation Plan 2023, the Q1 2026 investment
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
minutes after a collection. A retrieval's status is `collected`,
`not_modified`, `blocked`, `missing`, `invalid_content`, `invalid_response`,
`retryable_http_error`, `http_error`, `fetch_error`, `not_published` or
`not_applicable`.

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
ones under the matching record ([storage contract](jetp-ledger-storage.md) section 4). A hand-written observation names its author
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
agreement state; it is an observation on a line ([storage contract](jetp-ledger-storage.md) section 1). An agreement
may be a tranche of another (`tranche_of`) and finances zero or more projects
(`finances`); the hierarchy never splits money.

An agreement carries a `modality`, the OECD DAC type-of-aid code that Paper A's
result turns on: budget support (`A01`, `A02`), core contributions (`B01`,
`B02`, `B03`, `B04`), project-type interventions (`C01`), experts and
technical assistance (`D01`, `D02`), scholarships (`E01`), debt relief
(`F01`), and `unknown` when no line states it. Modality is a classification assigned from a line through a referent
decision, never inferred from the instrument word. Loan terms, interest rate,
maturity, grace period and the resulting grant element, are observations on
the agreement, because a publisher reports them at a date and another may
contradict them. A conditionality is an observation on the agreement of
measure `condition`, whose value is the condition as printed and whose
`concerns` relation names the party it binds, so that an AFD loan tied to a
tariff reform at Senelec is one agreement, one condition, one party.

### Party

A named organisation in a role: `funder`, `channel`, `promoter`,
`implementing_entity`, `beneficiary`, `contractor`, `operator`. Replaces 61 free-text funder strings that
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
with a role (`event`, `approval`, `reporting_cutoff`, `register_date`,
`report_date`, `planned`), a precision (`day`, `month`, `quarter`, `year`,
`unknown`) and bounds, so that an approval known only to the year
and the cutoff of the report that states it are both kept. Values are the
publisher's, in the publisher's unit and currency; conversion is a
derivation through the sourced `rates` table. An observation names its
`measure` from the closed list of section 4, its `basis` (`gross`, `net`,
`unknown`) where money is involved, and its `flow_type` from the IATI list when
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
| `published_by` | document | publisher | many-to-many; role optional (`author`, `co_signatory`, `host`) |
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
| `role_in` | party | project, asset, perimeter, document, line | a mandate outside any agreement: `lead_agency`, `coordinating_agency`, `guarantor`, `endorser`, `signatory`, `host`, `standards_body`; one row per role |
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
| money | `amount` (a state's amount, with `own_status`), `flow` (with `flow_type`: `pledge`, `commitment`, `disbursement`, `expenditure`, from IATI), `estimate` (a plan cost, no funder), `envelope` (a partnership or portfolio total), `interest_rate`, `maturity_years`, `grace_years`, `grant_element`, `condition` |
| physical | `capacity` (with unit), `length`, `state`, `target` (a physical or social objective with a `target` timing, such as a renewable share by 2030) |
| counting | `count` (with the publisher's unit named: rows, locomotives, officials trained, households), `absence` |
| macro | `indicator` (with the publisher's indicator code) |
| marker | `marker` (the publisher's policy-marker score: Rio `mitigation`, `adaptation`, `biodiversity`, `desertification`, and non-Rio markers such as `gender`; value `0`, `1` or `2`, or `not_screened` when the field is blank, which is not 0) |

A marker is the donor's own scoring of an activity, at a reporting year,
under the marker definition of that year. The "climate finance" that a
marker yields is the score times a coefficient, 100 percent for principal
and 40, 50 or 100 percent for significant depending on the donor and the
year; the coefficient is a rule, not an observation, so it belongs to the
ontology (section 5). It is recorded in the sourced `marker-coefficients`
table and applied only in a derived account, so that the same loan can be shown moving from 40 to 100 percent climate finance
without any change in the loan. A value may be a range: `value_low` and
`value_high` bound it, as the timing bounds bound a date, and a scalar has
both equal.

Money observations carry a `basis`, `gross`, `net` or `unknown`, and a flow carries
its interval through two timing roles, `period_start` and `period_end`, so a
quarterly register total states the quarter it covers and the account
of section 5 of the backend design can test coverage. A point flow has one
`event` timing.

Four shared status axes, each sourced from an external list and extended only
where the four publishers' practice requires it:

| Axis | Subject | External list | Local additions |
|---|---|---|---|
| `project_stage` | project | OC4IDS `projectStatus`: `identification`, `preparation`, `implementation`, `completion`, `maintenance`, `decommissioning`, `decommissioned`, `cancelled` | none |
| `asset_state` | asset | Global Energy Monitor: `announced`, `pre_permit`, `permitted`, `construction`, `shelved`, `cancelled`, `operating`, `mothballed`, `retired` | `retirement_proposed`, `retirement_agreed` |
| `money` | agreement | states: `announced`, `mou`, `approved`, `signed`, `cancelled`, `withdrawn`; flows: IATI `pledge`, `commitment`, `disbursement`, `expenditure` | none |
| `delivery` | agreement | IATI activity status: `pipeline`, `implementation`, `finalisation`, `closed`, `cancelled`, `suspended` | none; the South African register's letters A to D crosswalk here |
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

## 5. Ontology tables

The ontology is data about the ledger's words, stored like the ledger itself:
one CSV per table under `data/jetp/ontology/`, reviewed by diff, revised by
supersession and never edited in place. Each table is keyed by a row
identifier; the columns in *italics* are the chain key that successive
revisions of one entry share. A term's `term_id` is unique within its
`list`, so `cancelled` can be a value of several axes.

| Table | Key | Columns |
|---|---|---|
| `terms` | `term_row_id` | *term_id*, kind, *list*, label, definition, scope_note, domain, range, external_scheme, external_uri, mapping_relation, recorded_at, decided_by, status, supersedes, notes |
| `status-crosswalk` | `crosswalk_row_id` | *(publisher_id, own_status)*, axis, shared_status, recorded_at, decided_by, status, supersedes, notes |
| `sector-crosswalk` | `crosswalk_row_id` | *(publisher_id, own_sector)*, purpose_code, recorded_at, decided_by, status, supersedes, notes |
| `perimeters` | `perimeter_row_id` | *perimeter_id*, country, name, scope, definition, recorded_at, decided_by, status, supersedes, notes |
| `marker-coefficients` | `coefficient_row_id` | *(donor_party_id, marker, score, year)*, coefficient, line_id, recorded_at, decided_by, status, supersedes |

**Definition.** Every word the schema admits as a value is a `terms` row: the
classes and relations of sections 2 and 3, the line classifications, measures,
bases, flow types, modalities, date roles, roles, axes and axis values of
section 4. `kind` says which (`class`, `relation`, `value`); `list` names the closed
list a value belongs to. The definition is plain English, one or two
sentences, written for a reader of the observatory. A relation term also
states its `domain` and `range`. The DDL's checks read the terms in force; no
script or configuration file carries its own copy of a list. Sections 2 to 4
write every value in code type, which is what the alignment test reads; an
axis's `term_id` names the list of its values, and the OECD DAC purpose codes
that `sector-crosswalk` maps onto are cited by their five digits, not copied
as terms.

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
rules. The formal specification is the DDL of the [storage contract](jetp-ledger-storage.md) (section 3) together with the
`terms` table. Nothing else is: no OWL file, no SHACL shapes and no second
prose glossary. Alignment is checked, not trusted. A test (ticket 0880) fails
when a value listed in sections 2 to 4 is not a term in force, or a term in
force appears nowhere in this document, and when a table or column declared
in the storage contract differs from the DDL. The observatory's Glossary and a SKOS export
(storage contract, section 3) are generated from the `terms` table, so the words a reader sees
are the words the validator enforces.

LinkML was considered as the single source instead, generating the DDL, JSON
Schema, OWL and documentation from one YAML file. It is not adopted now,
because it adds a toolchain whose extra outputs have no consumer. The question
reopens when an external consumer asks for OWL or JSON Schema.

## 6. Out of scope, by decision

The proofing review read 36 random pages of 12 documents and found 23
percent of their information items not representable. The following classes
are out of scope by decision on 2026-09-22, because no paper reads them, and
the ledger says so rather than holding them badly:

- institutional events (a body founded, launched, staffed, merged) and
  party-to-party relations other than `role_in` and `party_in`;
- natural persons as signatories or delegates, distribution lists, seals
  and embedded signatures;
- values that exist only in a chart with no byte in the snapshot's text
  layer, until a transcription with provenance ([storage contract](jetp-ledger-storage.md) section 5) is a line;
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

## 7. Open questions for the author

None at 2026-09-22 end of day. The three questions this section held, line
identifiers, the party table and the Indonesian edition relation, were decided
the same day (decisions 5 and 6, and [storage contract](jetp-ledger-storage.md) section 4).
