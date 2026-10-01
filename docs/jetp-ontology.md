# JETP ledger ontology

It fixes what the ledger talks about: its classes, relations, value lists and
status axes, and the ontology tables that define and revise them. How
statements are combined is [`jetp-fusion.md`](jetp-fusion.md); the tables,
validation rules and engine are the
[storage contract](jetp-ledger-storage.md); what readers see is
[`jetp-observatory-presentation.md`](jetp-observatory-presentation.md). The
author's design decisions, with their reasons, are in the
[attic](attic/jetp-ontology-decisions-2026-09.md).

History: version 2 of the ontology, decided by the author on 2026-09-22
and 2026-09-23 and migrated by the 0870 train.

## 0. Frame

The ledger is the Data of the ODEM frame (Ontology, Data, Evidence, Models),
guided by the Ontology this document defines; Evidence is computed on top,
and there is no Model. Data is a pipeline of four steps: D1 register, D2
lines, D3 observations, D4 referents ([`jetp-language.md`](jetp-language.md)).

**Reading in W3C PROV.** The justification chain maps onto W3C PROV without
a PROV engine or an RDF store: snapshots, lines, observations, decision
rows, results and releases are *Entities*; retrievals, runs, readings,
judgements and release builds are *Activities*; publishers, method
versions, LLM readers and persons are *Agents*; a line and its snapshot, a
result and its inputs are *wasDerivedFrom*; a snapshot and its retrieval
*wasGeneratedBy*; a run and what it read *used*; a run or judgement and its
method version, LLM and person *wasAssociatedWith*; a document and its
publishers *wasAttributedTo*; a superseding row and the row it supersedes
*wasRevisionOf*. The mapping is what the RO-Crate option of
[results](jetp-results.md) section 5 would export. [M4]

## 1. Why a new schema

The four partnerships publish lists, not project registries, and the
previous schema read every list as projects, so that no count stated its
unit. The case is in the [attic](attic/jetp-ontology-decisions-2026-09.md).

## 2. Vocabulary

Terms are ordered from the document register outward: who says it, in what,
then what it is about.

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
proposed schema change. A consulting firm that wrote a document for a publisher is
linked as `author`, with the publisher as `commissioner`. [M2]

### Document

A logical publication: a title, a document type, a canonical URL, and one
or more publishers. The document types are `political_declaration`,
`investment_plan`, `implementation_plan`, `annual_report`, `progress_update`,
`project_list`, `project_page`, `approval_document`, `financing_agreement`,
`operator_report`, `official_news`, `secondary_news` and `data_portal`.
Publication is a relation, not a column, so a declaration co-signed by a
government and the International Partners Group names every publisher. A
document may have editions; an edition is a document related to its
predecessor, either a revised edition or the next issue of a series. The
successive versions of a living page are snapshots of one document, not
editions. [M2]

### Retrieval

One attempt to fetch one document at one time: the date, the HTTP outcome,
the headers that matter and, when bytes came back, the fingerprint of the
snapshot they form. A retrieval may fail and hold no snapshot; two
retrievals may return the same bytes and share one snapshot. A retrieval's
status is `collected`, `not_modified`, `blocked`, `missing`,
`invalid_content`, `invalid_response`, `retryable_http_error`, `http_error`,
`fetch_error`, `not_published` or `not_applicable`. The last two are not
outcomes of a fetch: the terminal verdict that closes a search is
collection's ([collection](jetp-collection.md) section 3), and how the two
lists relate is a proposed schema change. [M2]

### Snapshot

Exact bytes under a SHA-256 fingerprint, with the storage path. A snapshot
belongs to the documents whose retrievals returned it, which for a mirror is
two. A statement in the ledger cites a snapshot, never a URL or a retrieval,
so that what was read can be re-read. [M2]

### Line

One publisher's dated assertion at one locator in one snapshot. A row of the
South African grants register, a line of a plan appendix, a submission in a
list of submissions, a heading that groups such lines, a count the publisher
gives without naming what is counted. The line is the first-class unit of
the ledger: every identity below is minted from lines, every observation
cites one, and nothing is ever counted except lines and the identities that
reviewed matches have produced from them. [M2]

A line carries what every line has in common: country, snapshot, locator,
ordinal in its table, the label the publisher printed, its classification
(section 4), the publisher's own status word and which axis that word belongs
to, and, when its document attributes the part that carries it to one of its
publishers or to another party it names, that party; otherwise the line is its
document's publishers', jointly. Everything else the publisher printed for
that line is kept verbatim, field by field as printed. [M2]

Every observation names the method and version that read it from its line,
or the person who wrote it by hand. [M3b]

Proposition and programme are classifications of lines, not kinds. A
proposition is a line whose publisher puts something forward for a decision
not yet taken: a Senegal Annex 2 submission, a Viet Nam Annex I.2 partner
proposal. A programme heading is a line that groups other lines under a
governance or budget envelope. Neither is an identity. [M2]

### Project

An undertaking with a scope, an owner and a duration, that creates or changes
assets or delivers something non-physical. Minted only by a reviewed match
across lines, never by ingestion. Classified as `project`, `programme` or
`component` by a dated assertion, with `component_of` carrying containment on
the relations table. A technical-assistance project has no asset; a programme
may have none of its own. [M3b]

### Asset

A physical thing at a site: a plant, a unit within a plant, a transmission line,
a substation, a mini-grid. Carries capacity, technology and location; its
operator is a party attached by a dated `party_in` row, so a change of
operator is a new row, not an edited attribute. It moves through an asset
lifecycle aligned to Global Energy Monitor's status list, so that early
retirement, mothballing and fuel conversion are expressible as asset states.
Coal retirement is a unit fact: an asset may be a unit whose `part_of` is a
plant. Minted only by a reviewed match. An asset can exist with no project:
the plan line for Pelabuhan Ratu names a plant and a retirement year and
matches no undertaking. [M3b]

### Agreement

Funder-side money: a party commits an amount under an instrument to a
counterparty. A grant line of the South African grants register, a loan, a
results-based lending operation, a term sheet before signature. States are
states of the document that embodies it: announced, MoU, approved, signed,
cancelled, withdrawn. Money movements are flows on the agreement, typed by
the IATI transaction list: pledge (IATI's incoming and outgoing pledge,
since version 2.03 of the standard), commitment, disbursement, expenditure,
loan repayment, credit guarantee.
An operation, in the lenders' sense ([language](jetp-language.md)), is an
agreement; a tranche or a successive loan under one programme is an
agreement of its own related by `tranche_of`, never an amount split within
one agreement. A plan cost estimate is not an agreement state; it is an
observation on a line. An agreement finances zero or more projects
(`finances`); the hierarchy never splits money. [M3b]

An agreement carries a `modality`, the OECD DAC type-of-aid code: budget
support (`A01`, `A02`), core contributions (`B01`, `B02`, `B03`, `B04`),
project-type interventions (`C01`), experts and technical assistance
(`D01`, `D02`), scholarships (`E01`), debt relief (`F01`), and `unknown`
when no line states it. Modality is assigned from a line through a referent
decision, never inferred from the instrument word. Loan terms, interest
rate, maturity, grace period and the resulting grant element, are
observations on the agreement, because a publisher reports them at a date
and another may contradict them. A conditionality is an observation on the
agreement of measure `condition`, whose value is the condition as printed
and whose `concerns` relation names the party it binds. [M3b]

An agreement's instrument is to be read as a finance type, the OECD DAC CRS
finance type as IATI publishes it (FinanceType, standard 2.03), imported whole
as a closed list of its 56 instrument codes and cited by code: grants and
subsidies `110`, `210`, `310`, `311`; debt `421`, `422`, `4221`, `4222`,
`423`, `424`, `425`; mezzanine `431`, `432`, `433`, `434`; equity `510`,
`520`, `530`; debt relief `610`, `611`, `612`, `613`, `614`, `615`, `616`,
`617`, `618`, `620`, `621`, `622`, `623`, `624`, `625`, `626`, `627`, `630`,
`631`, `632`, `633`, `634`, `635`, `636`, `637`, `638`, `639`; guarantees
`1100`, `1101`, `1102`, `1103`, `1104`, `1105`, `1106`, `1107`, `1108`; direct
provider spending `2100`; subsidies and similar transfers `3100`. The
publisher's instrument word ("highly concessional", "grants/TA") stays
verbatim on the line and maps onto a code through a reviewed crosswalk, never
by a reader; until that crosswalk exists, `instrument` stays the publisher's
free word. Concessionality is not an instrument: it is the `grant_element`
observation. An imported external list keeps its own labels as published, so
finance-type labels are IATI's names, not the ledger's short lowercase labels.
[M3b]

History: finance type imported and the `owner` and `accountable` roles added
by the author's decisions of 2026-10-01 (ticket 1960), after the panel v1
fitness check; `accountable` because a held IATI-style page names it.

### Party

One organisation, whatever its roles: `funder`, `channel`, `promoter`,
`implementing_entity`, `beneficiary`, `contractor`, `operator`, `owner`,
`accountable`, or publisher of a document. The `owner` owns a project or an
asset and answers for it (a record page's project owner, chủ dự án); it is
neither the `promoter` nor `accountable`, IATI's oversight role, which a held
IATI-style page names. `funder`, `accountable` and `implementing_entity` carry
IATI's organisation-role codes 1, 2 and 4; `channel` carries none, since
IATI's Extending role (an agency managing the funder's money) is not the
pass-through intermediary. A funder and the channel its money passes through
are two parties in two roles: "Canada via World Bank and ADB" names three.
These roles attach to an agreement, a project or an asset through `party_in`;
a mandate outside any of them (a lead agency, a guarantor, a signatory) goes
through `role_in` (section 3). [M2 for publishers; M3b for the other roles]

Parties are under authority control. A party row holds no name; its names
are party name rows, one per form as printed, each with a form type,
`acronym`, `translation`, `spelling_or_case_variant` or `former_name` (or
none for the plain form), a language, the document or line it was read
from, and whether it is the preferred form. Being preferred is a flag, not a
form type, so a preferred form can also be an acronym (SENELEC). Exactly one
form is preferred at a time; a form is revised by supersession like any
decision row. The form type `preferred` is kept in force until the schema
carries the flag. [M2 for the names of publishers; M3b for other parties]

### Perimeter

A coverage definition stated by a publisher: the partnership pledge envelope
and its revisions, a publisher-defined portfolio of 24 records of which 21 are
unnamed, a procurement quota of 250 MW, a plan's list at a cutoff.
Membership is a justified relation, not a list. A count slot is a perimeter
observation, "this publisher counted 24 at this date", not 21 rows in a
table. A scope that the analysis defines to count against is a method
choice, not a perimeter of the ontology ([fusion](jetp-fusion.md), section
6). [M3b]

### External identifier

A code another identifier scheme uses for one of the ledger's identities or
lines: a World Bank P-number, a CRS `crs_id` or `donor_project_id`, an IATI
activity identifier, a GEM unit id; for a party, an IATI organisation
identifier, a ROR identifier, an LEI or a Wikidata item. One table holds
them all, typed by scheme, so a comparator record and a ledger identity meet
on a key rather than on a name. What an identifier decides is a fusion rule
([fusion](jetp-fusion.md), section 3). [M3b]

### Comparator record

A record from an external database admitted to the register: a World Bank
project from the projects API, a CRS activity, an IATI activity. It is a
line of a snapshot whose document is the dataset edition and whose publisher
is the institution, with its own fields verbatim, its identifiers in the
external-identifier table and its statuses crosswalked like any publisher's.
Nothing in the ledger treats a comparator record as a project of a
partnership. [M3b]

### Observation

One dated statement about one subject, cited to one line: a flow on an
agreement, a state of an asset, a stage of a project, a capacity, an estimate
on a plan line, a count on a perimeter, an envelope on a partnership. The
subject is typed, `(subject_kind, subject_id)`, and may be a line itself when
no identity has been minted. An observation has one or more timings, each with
a role from one closed list of nine (`event`, `approval`, `reporting_cutoff`,
`register_date`, `report_date`, `planned`, `target`, `period_start`,
`period_end`; the last two bound a flow over an interval, section 4), a
precision (`day`, `month`, `quarter`, `year`, `unknown`) and bounds. Values
are the publisher's, in the publisher's unit and currency; conversion is a
derivation through the sourced `rates` table. An observation names its
`measure` from the closed list of section 4, its `basis` (`gross`, `net`,
`unknown`) where money or a physical quantity is involved, and its `flow_type`
from the IATI list when the measure is a flow. It carries `recorded_at`, the
date the ledger wrote it, and the same `status` and `supersedes` as a decision
row. Supersession corrects the ledger's own errors, never a publisher: a later
statement that prints a different value is a new observation beside the old
one, and one that prints the same value again is a dated restatement
([fusion](jetp-fusion.md), section 2). Subjects also include `country`, for
macro-fiscal indicators (GDP, external debt; a utility's debt ratio is on a
`party`), each with its indicator code from the publisher's own list. [M3b]

### Crosswalk

A reviewed, dated mapping from one publisher's status vocabulary to one shared
axis. The publisher's word stays on the line and on the observation; the
crosswalk row is the only place a shared status is asserted, and it names who
decided it and when. [M2 for keeping the publisher's word; M3b for the crosswalk]

## 3. Relations

| Relation | From | To | Meaning |
|---|---|---|---|
| `published_by` | document | party | many-to-many; role optional (`author`, `co_signatory`, `host`, `commissioner`); a joint publication is one row per party; in a text "X / Y" the publisher X is `commissioner` and the consulting firm Y `author` |
| `edition_of` | document | document | succeeds a previous edition; the relation's role says whether it is a revised edition or the next issue of a series; the successive versions of a living page are its snapshots, not editions |
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
| `party_in` | party | agreement, project, asset | one row per role, dated, from the Party roles of section 2: `funder` and `channel` attach to an agreement; `promoter`, `implementing_entity`, `beneficiary` and `contractor` to an agreement or a project; `operator` and `owner` to an asset or a project; `accountable` to an agreement or a project; a party may fund one agreement and channel another |
| `role_in` | party | project, asset, perimeter, document, line | a mandate outside any agreement: `lead_agency`, `coordinating_agency`, `guarantor`, `endorser`, `signatory`, `host`, `standards_body`; one row per role |
| `cites` | line | document, line | a document's reference to another document or to a line of it, held or not; an observation's citation of its one line is the observation's `line_id` column, not a relation |
| `member_of` | line, project, asset, agreement | perimeter | dated, justified membership; a line may be a member before any identity is minted |
| `same_as` | any | same kind | a justified equality claim; does not choose a route. Its cases: two documents, one publication under two URLs or two exports (which member is extracted is extraction's rule, not the relation's); two lines, the same published item in two places, such as a CRS activity across reporting years (keyed on donor and donor project id) or one amount printed in a headline, a table and a chart |
| `about` | observation | any subject | typed |
| `timed` | observation | timing | one row per date role; the amount lives once on the observation | 

[M2 for the relations among documents, retrievals, snapshots and lines; M3b for the others]

## 4. Line classifications and status axes

A line's classification says what kind of statement it is, in the publisher's
own terms, from a closed list:

`named_item`, `unnamed_item`, `quota`, `heading`, `submission`, `evaluation`,
`register_allocation`, `count`, `envelope`, `absence`, `target`, `event`, `decision`.

A classification is never inferred from the label. The list grows only by
decision of the author, on the panel's proposal, and is closed between
method versions ([extraction](jetp-extraction.md) section 3). [M2]

**Sector** is a shared axis, coded with the OECD DAC CRS purpose list (five
digits; the 231 to 236 group covers energy policy, generation by source,
distribution and efficiency), because CRS records carry it, IATI uses it by
default and the World Bank taxonomy crosswalks to it. It is handled like a
status axis: the publisher's own word stays verbatim on the line, and a
reviewed, dated `sector-crosswalk` row maps each publisher scheme onto a
purpose code. Sector appears on a line as `own_sector`, on an agreement and
a project as `sector` assigned through a referent decision, and on an
observation by inheritance from its subject. Technology is a separate
attribute of assets, aligned to the Global Energy Monitor list: a sector
says what the money is for, a technology says what the plant is. [M2 for
the publisher's own sector word on the line; M3b for the crosswalk and the
assigned sector]

A **transition function** (requirement F18) is a classification of an
agreement or a project, assigned like `sector` through a referent decision,
from the three functions F18 names; its values become terms with the other
M3b axes. [M3b]

Mobilised and co-financing amounts are `amount` observations whose
`party_in` funding roles say whose money it is (F17); refinancing is out of
scope. [M3b]

The `measure` of an observation is from a closed list, extended by decision:

| Axis | Measures |
|---|---|
| money | `amount` (a state's amount, with `own_status`), `flow` (with `flow_type`: `pledge`, `commitment`, `disbursement`, `expenditure`, `loan_repayment`, `credit_guarantee`, from IATI), `estimate` (a plan cost, no funder), `envelope` (a partnership or portfolio total), `interest_rate`, `maturity_years`, `grace_years`, `grant_element`, `condition` |
| physical | `capacity` (with quantity kind, unit and basis, below), `length`, `state`, `target` (a physical or social objective with a `target` timing, such as a renewable share by 2030) |
| counting | `count` (with the publisher's unit named: rows, locomotives, officials trained, households), `absence` |
| macro | `indicator` (with the publisher's indicator code) |
| marker | `marker` (the publisher's policy-marker score: Rio `mitigation`, `adaptation`, `biodiversity`, `desertification`, and non-Rio markers such as `gender`; value `0`, `1` or `2`, or `not_screened` when the field is blank, which is not 0) |

A `capacity` or an energy amount carries a quantity kind, a unit and a
basis, so that no two numbers of different kinds are ever added. The
quantity kinds are `electric_power`, `peak_electric_power` (a module's
rated output under standard test conditions, printed Wp or Wc, never mixed
with grid output), `thermal_power`, `apparent_power`, `energy`,
`energy_storage_capacity` and `electric_charge`; the units are `W`, `VA`,
`Wh`, `J` and `Ah`, with SI prefixes as a rule on the unit, not as terms.
They follow the Open Energy Ontology (v2.13.0) and the Units of Measurement
Ontology where those name the concept, and are marked local where they do
not (thermal and apparent power, peak power, VA, Ah). The basis is
`gross`, `net` or `unknown` for a physical quantity as for money, and a
value whose line states none is `unknown`, never read as gross or net. A
bound, a change or a rate printed with a value ("below 10 MW", "+0.7 GW
year-on-year", "88 MWh par jour") is not a quantity kind; it stays verbatim
on the line. An annual energy output is not observed. The `observations`
table carries the unit today; the quantity kind becomes a column with the
reader schema of the M2.3 reading lane. [M3b]

History: quantity kinds and units added, and the basis extended to physical
quantities, by the author's sign-off of 2026-10-01 (ticket 1960), after a
check on the 60 capacity values of panel v1
(`docs/jetp-study/1960-capacity-terms-proposal.md`).

A marker is the donor's own scoring of an activity, at a reporting year,
under the marker definition of that year. The "climate finance" that a
marker yields is the score times a coefficient, 100 percent for principal
and 40, 50 or 100 percent for significant depending on the donor and the
year. The coefficient is a sourced parameter of a derived account, not a
word of the ontology ([fusion](jetp-fusion.md), section 7); it is kept in
the `marker-coefficients` table (section 5), used from M4, or from M3b if
the comparison of requirement F19 uses climate-marked amounts. A value may
be a range: `value_low` and `value_high` bound it, as the timing bounds
bound a date, and a scalar has both equal. [M3b]

An observation of money or of a physical quantity carries a `basis`, `gross`,
`net` or `unknown`, and a flow carries its interval through two of the timing
roles of section 2, `period_start` and `period_end`, so the account of the
[fusion rules](jetp-fusion.md) (section 7) can test coverage. A point flow has
one `event` timing. [M3b]

Four shared status axes, each sourced from an external list and extended only
where the four publishers' practice requires it:

| Axis | Subject | External list | Local additions |
|---|---|---|---|
| `project_stage` | project | OC4IDS `projectStatus`: `identification`, `preparation`, `implementation`, `completion`, `maintenance`, `decommissioning`, `decommissioned`, `cancelled` | none |
| `asset_state` | asset | Global Energy Monitor: `announced`, `pre_permit`, `permitted`, `construction`, `shelved`, `cancelled`, `operating`, `mothballed`, `retired` | `retirement_proposed`, `retirement_agreed` |
| `money` | agreement | states: `announced`, `mou`, `approved`, `signed`, `cancelled`, `withdrawn`; flows: IATI `pledge`, `commitment`, `disbursement`, `expenditure`, `loan_repayment`, `credit_guarantee` | none |
| `delivery` | agreement | IATI activity status: `pipeline`, `implementation`, `finalisation`, `closed`, `cancelled`, `suspended` | none; the South African register's letters A to D crosswalk here |
| comparator statuses | comparator lines | World Bank project status (pipeline, active, closed, dropped), CRS and IATI activity status | crosswalked onto the axes above, never merged | 

[M3b for the axes and their crosswalks]

The publisher's own words, all of them, are kept: the South African
register's `A. Planned` to `D. Completed`, Indonesia's modality and
approval, Viet Nam's published or not published, Senegal's submitted,
evaluated and quick win. Each maps through the crosswalk to at most one
axis. A publisher's own scheme that reuses a word of this design, such as
Indonesia's "Modality A" and "Modality B", stays a verbatim field of the
line; `modality` on an agreement is only ever the DAC type-of-aid code.
Where a publisher reports one axis only, the other two are absent for that
line: the ledger states which axes a publisher reports rather than filling
the others. [M2 for keeping the words; M3b for the crosswalk]

## 5. Ontology tables

The ontology is data about the ledger's words, stored like the ledger itself,
reviewed by diff, revised by supersession and never edited in place. Five
tables hold it: `terms`, `status-crosswalk`, `sector-crosswalk`,
`perimeters` and `marker-coefficients`. Their keys, columns, chain keys and
paths are defined in the [storage contract](jetp-ledger-storage.md)
(section 1); this section says what they mean and how they are revised.

**Definition.** Every word the schema admits as a value is a `terms` row: the
classes and relations of sections 2 and 3, the line classifications, measures,
bases, flow types, finance types, modalities, date roles, roles, axes and axis
values of section 4. `kind` says which (`class`, `relation`, `value`); `list`
names the closed list a value belongs to. The definition is plain English, one
or two sentences, written for a reader of the Observatory. A relation term
also states its `domain` and `range`. The DDL's checks read the terms in
force; no script or configuration file carries its own copy of a list.
Sections 2 to 4 write every value in code type, which is what the alignment
test reads; an axis's `term_id` names the list of its values, and the OECD DAC
purpose codes that `sector-crosswalk` maps onto are cited by their five
digits, not copied as terms. [M2]

**Traceability.** A term taken from an external vocabulary names its scheme
(IATI, OC4IDS, GEM, OECD DAC, PROV-O, SKOS), the concept's URI or code, and a
`mapping_relation` from SKOS: `exactMatch`, `closeMatch`, `broadMatch`,
`narrowMatch`, `relatedMatch`, or `local` for a word the ledger defines
itself. Similar labels do not justify `exactMatch`. A crosswalk row maps a
publisher's word onto a term; a perimeter row defines a population that
counts are made against. Both name who decided and when. A crosswalk row
also states its mapping strength with the same SKOS relations, required when
the row is accepted; the two crosswalk tables gain `mapping_relation` as a
target of the storage contract (section 1), and a result that counts by
shared status or sector states the weakest mapping among the rows it used,
in the order exactMatch, closeMatch, broadMatch or narrowMatch,
relatedMatch, with the count of rows per relation. [M2 for terms; M3b for
crosswalk rows]

**Revision.** The in-force rule of the decision tables applies (storage
contract, section 1), so a proposed revision leaves the adopted row in
force. Rewording a definition or correcting a mapping supersedes the row
under the same chain key. A change of meaning mints a new `term_id` or
`perimeter_id`, and the old one stays valid for every row that used it; a
count made against the old perimeter is never silently moved to the new
one. The ontology as of cutoff K is the set of rows in force at K, so an
as-of query reconstructs the words as well as the data. `decisions.md`
keeps the reasons in prose and cites the row it explains. [M2]

**Reference from E.** Every derived result names the ontology version it was
computed under, and a result is never recomputed under a later ontology
without a new run record. [M3b]

### English and formal specification

This document is the English specification. The formal specification is the
DDL of the [storage contract](jetp-ledger-storage.md) (section 3) together
with the `terms` table; there is no OWL file, no SHACL shapes and no second
prose glossary. A test fails when a value listed in sections 2 to 4 is not
a term in force, or a term in force appears nowhere in this document, and
when a table or column declared in the storage contract differs from the
DDL. The Observatory's Glossary and a SKOS export (storage contract,
section 3) are generated from the `terms` table; the SKOS export covers the
value lists only (`kind` = `value`), one concept scheme per `list`. LinkML
as a single source generating the DDL, JSON Schema, OWL and documentation
is not adopted, since its extra outputs have no consumer; the question
reopens when an external consumer asks for OWL or JSON Schema. [M2 for the
DDL and the alignment test; M3b for the Glossary; M4 for the SKOS export;
later for LinkML]

History: the alignment test was written under ticket 0880; the ontology
tables' keys and columns moved to the storage contract in review wave 1
(W1-41).

## 6. Out of scope, by decision

The following classes are out of scope by decision, and the ledger says so
rather than holding them badly: [M2]

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

History: these exclusions were decided by the author on 2026-09-22.
