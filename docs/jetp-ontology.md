# JETP ledger ontology

Status: in force. Version 2 of the ontology, drafted 2026-09-22, reviewed by
four independent panels
([`jetp-study/ontology-review-2026-09-22/`](jetp-study/ontology-review-2026-09-22/))
and migrated by the 0870 train (closed 2026-09-30).
It fixes what the ledger talks about: its classes, relations, value lists and
status axes, and the ontology tables that define and revise them. It holds
no rule for combining statements, no storage and no presentation:

- [`jetp-fusion.md`](jetp-fusion.md), how statements are combined, weighed and revised;
- [`jetp-ledger-storage.md`](jetp-ledger-storage.md), the storage contract: tables, validation rules, engine, matching, translations;
- [`attic/jetp-ledger-migration.md`](attic/jetp-ledger-migration.md), the migration from the previous tables;
- [`jetp-observatory-presentation.md`](jetp-observatory-presentation.md), what readers see.

The author's design decisions of 2026-09-22 and 2026-09-23, with their
reasons, are kept in
[`attic/jetp-ontology-decisions-2026-09.md`](attic/jetp-ontology-decisions-2026-09.md);
their effect is the text below.

## 0. Frame

The ledger is the Data of the ODEM frame (Ontology, Data, Evidence, Models),
guided by the Ontology this document defines; Evidence is computed on top,
and there is no Model. Data is a pipeline of four steps: D1 register, D2
lines, D3 observations, D4 referents. The frame, the step-to-table map and the
terms the design documents and schema use or avoid are
[`jetp-language.md`](jetp-language.md). What readers of the Observatory see is
[`jetp-observatory-presentation.md`](jetp-observatory-presentation.md).

## 1. Why a new schema

The four partnerships publish lists, not project registries, and the
previous schema read every list as projects, so that no count stated its
unit. The case, from four reviews, is in the
[attic](attic/jetp-ontology-decisions-2026-09.md).

## 2. Vocabulary

Terms are ordered from the document register outward: who says it, in what, then what it
is about.

### Publisher

The party that publishes a document and answers for what it states: the JETP
Indonesia Secretariat, the JET Project Management Unit, the Ministry of Industry
and Trade, ANER, Senelec, the Asian Development Bank. A publisher is not a
table of its own: it is a party (below) in a publishing role, linked to the
document by a publication row, so the Asian Development Bank that publishes a
report and the one that funds a loan are one organisation. The party carries
an authority category, `national_government`, `jetp_secretariat`, `ipg`,
`bilateral_funder`, `multilateral_funder`, `private_finance`, `operator` or
`secondary_source`, and a country (`ZAF`, `IDN`, `VNM`, `SEN`) or
`international`. The category `secondary_source` keeps a word the
[language](jetp-language.md) document retires for publishers; its rename is a
proposed schema change (ticket 1702). A consulting firm that wrote a document for a publisher is
linked as `author`, with the publisher as `commissioner`. [M2]

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
predecessor. [M2]

### Retrieval

One attempt to fetch one document at one time: the date, the HTTP outcome,
the headers that matter and, when bytes came back, the fingerprint of the
snapshot they form. This is the current manifest row. A retrieval may fail
and hold no snapshot; two retrievals may return the same bytes and share one
snapshot, as the manifest already shows with a `not_modified` re-fetch three
minutes after a collection. A retrieval's status is `collected`,
`not_modified`, `blocked`, `missing`, `invalid_content`, `invalid_response`,
`retryable_http_error`, `http_error`, `fetch_error`, `not_published` or
`not_applicable`. The last two are not outcomes of a fetch: the terminal
verdict that closes a search is collection's ([collection](jetp-collection.md)
section 3), and how the two lists relate is a proposed schema change (ticket
1702). [M2]

### Snapshot

Exact bytes under a SHA-256 fingerprint, with the storage path. A snapshot
belongs to the documents whose retrievals returned it, which for a mirror is
two. A statement in the ledger cites a snapshot, never a URL or a retrieval,
so that what was read can be re-read. [M2]

### Line

One publisher's dated assertion at one locator in one snapshot. A row of the
South African grants register, a line of a plan appendix, a position in an annex, a submission
in a list of submissions, a heading that groups such lines, a count the
publisher gives without naming what is counted. The line is the first-class
unit of the ledger: every identity below is minted from lines, every observation
cites one, and nothing is ever counted except lines and the identities that
reviewed matches have produced from them. [M2]

A line carries what every line has in common: country, snapshot, locator,
ordinal in its table, the label the publisher printed, its classification
(section 4), the publisher's own status word and which axis that word belongs
to. Everything else the publisher printed for that line is kept verbatim,
field by field as printed. [M2]

Every observation names the method and version that read it from its line,
or the person who wrote it by hand. [M3b]

Proposition and programme are classifications of lines, not kinds. A proposition is a line whose publisher puts something forward for a
decision not yet taken: a Senegal Annex 2 submission, a Viet Nam Annex I.2
partner proposal. A programme heading is a line that groups other lines under
a governance or budget envelope. Neither is an identity. Two propositions may
describe one future project and a proposition may die without one. [M2]

### Project

An undertaking with a scope, an owner and a duration, that creates or changes
assets or delivers something non-physical. Minted only by a reviewed match
across lines, never by ingestion. Classified as `project`, `programme` or
`component` by a dated assertion, with `component_of` carrying containment on
the relations table. A technical-assistance project has no asset; a programme
may have none of its own. [M3b]

### Asset

A physical thing at a site: a plant, a unit within a plant, a transmission line,
a substation, a mini-grid. Carries capacity, technology, location and operator,
and moves through an asset lifecycle aligned to Global Energy Monitor's
status list, so that early retirement, mothballing and fuel conversion are
expressible as asset states. Coal retirement is a unit fact: an asset may be a
unit whose `part_of` is a plant. Minted only by a reviewed match. An asset can
exist with no project: the plan line for Pelabuhan Ratu names a plant and a
retirement year and matches no undertaking. [M3b]

### Agreement

Funder-side money: a party commits an amount under an instrument to a
counterparty. A grant line of the South African grants register, a loan, a results-based lending
operation, a term sheet before signature. States are states of the document
that embodies it: announced, MoU, approved, signed, cancelled, withdrawn.
Money movements are flows on the agreement, typed by the IATI transaction list:
pledge, commitment, disbursement, expenditure. A plan cost estimate is not an
agreement state; it is an observation on a line ([storage contract](jetp-ledger-storage.md) section 1). An agreement
may be a tranche of another (`tranche_of`) and finances zero or more projects
(`finances`); the hierarchy never splits money. [M3b]

An agreement carries a `modality`, the OECD DAC type-of-aid code: budget support (`A01`, `A02`), core contributions (`B01`,
`B02`, `B03`, `B04`), project-type interventions (`C01`), experts and
technical assistance (`D01`, `D02`), scholarships (`E01`), debt relief
(`F01`), and `unknown` when no line states it. Modality is a classification assigned from a line through a referent
decision, never inferred from the instrument word. Loan terms, interest rate,
maturity, grace period and the resulting grant element, are observations on
the agreement, because a publisher reports them at a date and another may
contradict them. A conditionality is an observation on the agreement of
measure `condition`, whose value is the condition as printed and whose
`concerns` relation names the party it binds, so that an AFD loan tied to a
tariff reform at Senelec is one agreement, one condition, one party. [M3b]

### Party

One organisation, whatever its roles: `funder`, `channel`, `promoter`,
`implementing_entity`, `beneficiary`, `contractor`, `operator`, or publisher of
a document. A funder and the channel its money passes through are two
parties in two roles: "Canada via World Bank and ADB" names three. [M2]

Parties are under authority control, as in a library's name authority file
or the ROR and GLEIF registries. A party row holds no name;
its names are party name rows, one per form as printed, each with a form type,
`preferred`, `acronym`, `translation`, `spelling_or_case_variant` or
`former_name`, a language, and the document or line it was read from. Exactly
one form is preferred at a time; a form is revised by supersession like any
decision row. [M2 for the names of publishers; M3b for other parties]

### Perimeter

A coverage definition stated by a publisher: the partnership pledge envelope
and its revisions, a publisher-defined portfolio of 24 records of which 21 are
unnamed, a procurement quota of 250 MW, a plan's list at a cutoff.
Membership is a justified relation, not a list. A count slot is a perimeter observation,
"this publisher counted 24 at this date", not 21 rows in a table. A scope
that the analysis defines to count against, such as a reference pool of
comparator operations, is a method choice, not a perimeter of the ontology
([fusion](jetp-fusion.md), section 6). [M3b]

### External identifier

A code another identifier scheme uses for one of the ledger's identities or
lines: a
World Bank P-number, a CRS `crs_id` or `donor_project_id`, an IATI activity
identifier, a GEM unit id; for a party, an IATI organisation identifier, a ROR
identifier, an LEI or a Wikidata item. One table holds them all, typed by
scheme, so a comparator record and a ledger identity meet on a key rather than
on a name. What an identifier decides is a fusion rule
([fusion](jetp-fusion.md), section 3). [M3b]

### Comparator record

A record from an external database admitted to the register: a World Bank
project from the projects API, a CRS activity, an IATI activity. It is a
line of a snapshot whose document is the dataset edition and whose publisher
is the institution, with its own fields verbatim, its identifiers in the
external-identifier table and its statuses crosswalked like any publisher's.
Nothing in the ledger treats a comparator record as a project of a partnership. [M3b]

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
it, and the same `status` and `supersedes` as a decision row. Supersession
corrects the ledger's own errors (a misread value, a false match, a faulty
extraction rule), never a publisher: a later statement that prints a
different value is a new observation beside the old one, and one that prints
the same value again is a dated restatement ([fusion](jetp-fusion.md),
section 2).
Subjects also include `country`, for macro-fiscal indicators (GDP, external debt;
a utility's debt ratio is on a `party`), each with its indicator code from the publisher's own list. [M3b]

### Crosswalk

A reviewed, dated mapping from one publisher's status vocabulary to one shared
axis. The publisher's word stays on the line and on the observation; the
crosswalk row is the only place a shared status is asserted, and it names who
decided it and when. [M2 for keeping the publisher's word; M3b for the crosswalk]

## 3. Relations

| Relation | From | To | Meaning |
|---|---|---|---|
| `published_by` | document | party | many-to-many; role optional (`author`, `co_signatory`, `host`, `commissioner`); a joint publication is one row per party; in a text "X / Y" the publisher X is `commissioner` and the consulting firm Y `author` |
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

[M2 for the relations among documents, retrievals, snapshots and lines; M3b for the others]

## 4. Line classifications and status axes

A line's classification says what kind of statement it is, in the publisher's
own terms, from a closed list:

`named_item`, `unnamed_item`, `quota`, `heading`, `submission`, `evaluation`,
`register_allocation`, `count`, `envelope`, `absence`.

The list is grown when a publisher's practice needs a value; it is never
inferred from the label. [M2]

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
the plant is. [M2 for the publisher's own sector word on the line; M3b for the crosswalk and the assigned sector]

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
year. The coefficient is a sourced parameter of a derived account, not a
word of the ontology ([fusion](jetp-fusion.md), section 7); it is kept for
now in the `marker-coefficients` table of section 5. A value may be a range: `value_low` and
`value_high` bound it, as the timing bounds bound a date, and a scalar has
both equal. [M3b]

Money observations carry a `basis`, `gross`, `net` or `unknown`, and a flow carries
its interval through two timing roles, `period_start` and `period_end`, so a
quarterly register total states the quarter it covers and the account
of the [fusion rules](jetp-fusion.md) (section 7) can test coverage. A point flow has one
`event` timing. [M3b]

Four shared status axes, each sourced from an external list and extended only
where the four publishers' practice requires it:

| Axis | Subject | External list | Local additions |
|---|---|---|---|
| `project_stage` | project | OC4IDS `projectStatus`: `identification`, `preparation`, `implementation`, `completion`, `maintenance`, `decommissioning`, `decommissioned`, `cancelled` | none |
| `asset_state` | asset | Global Energy Monitor: `announced`, `pre_permit`, `permitted`, `construction`, `shelved`, `cancelled`, `operating`, `mothballed`, `retired` | `retirement_proposed`, `retirement_agreed` |
| `money` | agreement | states: `announced`, `mou`, `approved`, `signed`, `cancelled`, `withdrawn`; flows: IATI `pledge`, `commitment`, `disbursement`, `expenditure` | none |
| `delivery` | agreement | IATI activity status: `pipeline`, `implementation`, `finalisation`, `closed`, `cancelled`, `suspended` | none; the South African register's letters A to D crosswalk here |
| comparator statuses | comparator lines | World Bank project status (pipeline, active, closed, dropped), CRS and IATI activity status | crosswalked onto the axes above, never merged | 

[M3b for the axes and their crosswalks]

The publisher's own words, all of them, are kept: the South African
register's `A. Planned`
to `D. Completed`, Indonesia's modality and approval, Viet Nam's published or
not published, Senegal's submitted, evaluated and quick win. Each maps through
the crosswalk to at most one axis. A publisher's own scheme that reuses a
word of this design, such as Indonesia's "Modality A" and "Modality B",
stays a verbatim field of the line; `modality` on an agreement is only ever
the DAC type-of-aid code. Where a publisher reports one axis only, the
other two are absent for that line: the ledger states which axes a publisher
reports rather than filling the others. [M2 for keeping the words; M3b for the crosswalk]

## 5. Ontology tables

The ontology is data about the ledger's words, stored like the ledger itself
([storage contract](jetp-ledger-storage.md)), reviewed by diff, revised by
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
sentences, written for a reader of the Observatory. A relation term also
states its `domain` and `range`. The DDL's checks read the terms in force; no
script or configuration file carries its own copy of a list. Sections 2 to 4
write every value in code type, which is what the alignment test reads; an
axis's `term_id` names the list of its values, and the OECD DAC purpose codes
that `sector-crosswalk` maps onto are cited by their five digits, not copied
as terms. [M2]

**Traceability.** A term taken from an external vocabulary names its scheme
(IATI, OC4IDS, GEM, OECD DAC, PROV-O, SKOS), the concept's URI or code, and a
`mapping_relation` from SKOS: `exactMatch`, `closeMatch`, `broadMatch`,
`narrowMatch`, `relatedMatch`, or `local` for a word the ledger defines
itself. Similar labels do not justify `exactMatch`. A crosswalk row maps a
publisher's word onto a term; a perimeter row defines a population that
counts are made against. Both name who decided and when. [M2]

**Revision.** The in-force rule of the decision tables applies: a row is in
force when it is the accepted terminal row of its chain. Rewording a
definition or correcting a mapping supersedes the row under the same chain
key. A change of meaning mints a new `term_id` or `perimeter_id`, and the old
one stays valid for every row that used it; a count made against the old
perimeter is never silently moved to the new one. The ontology as of cutoff K
is the set of rows in force at K, so an as-of query reconstructs the words as
well as the data. `decisions.md` keeps the reasons in prose and cites the row
it explains. [M2]

**Reference from E.** Every derived result names the ontology version it was
computed under, and a result is never recomputed under a later ontology
without a new run record. [M3b]

### English and formal specification

This document is the English specification: it gives the reasons and the
rules. The formal specification is the DDL of the [storage contract](jetp-ledger-storage.md) (section 3) together with the
`terms` table. Nothing else is: no OWL file, no SHACL shapes and no second
prose glossary. Alignment is checked, not trusted. A test (ticket 0880) fails
when a value listed in sections 2 to 4 is not a term in force, or a term in
force appears nowhere in this document, and when a table or column declared
in the storage contract differs from the DDL. The Observatory's Glossary and a SKOS export
(storage contract, section 3) are generated from the `terms` table, so the words a reader sees
are the words the validator enforces. [M2 for the DDL and the alignment test; M3b for the Glossary and M4 for the SKOS export]

LinkML was considered as the single source instead, generating the DDL, JSON
Schema, OWL and documentation from one YAML file. It is not adopted now,
because it adds a toolchain whose extra outputs have no consumer. The question
reopens when an external consumer asks for OWL or JSON Schema. [later]

## 6. Out of scope, by decision

The following classes are out of scope by decision (2026-09-22), and the
ledger says so rather than holding them badly: [M2]

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
  people, generation, tonnage, hectares. When one is needed, it enters
  as a measure by decision with its unit and the IPCC or ILO list it maps to.
