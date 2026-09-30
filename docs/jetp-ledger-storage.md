# JETP ledger storage contract

The tables that store the ledger, the rules the validator enforces, the build
engine, the matching record and the derived translation tables. How statements are
combined and judged is [fusion](jetp-fusion.md). What the ledger's words mean is the
[ontology](jetp-ontology.md); how the current tables become these is the
[migration](attic/jetp-ledger-migration.md).

## 1. Tables and rules

One file is one table, joins happen at read time, nothing is materialised.
Data tables under `data/jetp/`, the five ontology tables under
`data/jetp/ontology/`, CSV, columns in this order. What the ontology tables
mean, and how they are revised, is the [ontology](jetp-ontology.md)
(section 5); their keys, columns and paths are here.
A table too large for the repository's file ceiling, 512 000 bytes per
file in `.githooks/pre-commit`, is chunked by country and year into
`<table>.d/<CODE>-<year>.csv`, with numbered `-02`, `-03` shards when one
country-year still exceeds the ceiling. The build joins those shards in
numeric order, preserving row order within that country-year. The shard
key is read from fields that never change: the year of the row's own
`recorded_at` (of `decided_at` where the table does not carry `recorded_at`
yet), and the row's own `country` column. `observations` and
`timings` get their shard country from the cited `line_id`, since those tables
have no country column; no shard key is an inferred or judged value. The `.d` suffix keeps a
chunk directory apart from a directory that shares a table's name:
`data/jetp/documents/` is the document store (the snapshot bytes) under DVC, not the chunks of the
`documents` table, and the writer deletes only its `<CODE>-<year>[-NN].csv` files of
its own `.d` directory.
For rows such as party-alias relations that have no country, `GLB` is the shard
filename's storage bucket. It asserts no country for the relation. A global
method-source line may use `country=GLB` because `lines.country` is required;
`GLB` means no recipient country, not a fifth JETP country.
The writer stages complete shard bytes before publishing them. A temporary
`<table>.d.pending` marker makes an interrupted layout change a named ledger
error; a missing first or numbered shard also fails validation. [M2]
The per-document fields table `line-fields/<document_id>` has no country or
year to shard on. When it exceeds the ceiling it is split into
`line-fields/<document_id>.d/NN.csv`, numbered from `01` and joined in
numeric order, under the same pending-marker rule. The fields table of a
living document, which grows with every snapshot, is split by the year of
the lines' `recorded_at` instead (`<document_id>.d/<year>.csv`, with numbered
`-02`, `-03` shards when one year exceeds the ceiling). `readings` is
split by run (`readings.d/<run_id>.csv`, then `-02` shards), since a rejected
proposal cites no line to take a country from. [M2]

| Table | Key | Columns |
|---|---|---|
| `parties` | `party_id` | authority_category, country, notes |
| `party-names` | `name_row_id` | party_id, name, form_type, language, document_id, line_id, recorded_at, decided_by, status, supersedes, notes |
| `documents` | `document_id` | country, document_type, language, title, url, published_date, edition_of, active, notes |
| `document-publishers` | (document_id, party_id) | role, name_row_id (the form of the party's name this document prints) |
| `retrievals` | `retrieval_id` | document_id, retrieved_at, status, http_status, content_type, etag, last_modified, final_url, error, sha256 (nullable), collection_method (script, browser-session, browser-manual or local-record) |
| `snapshots` | `sha256` | storage_path, size_bytes, content_type |
| `lines` | `line_id` | country, sha256, locator, ordinal, label, classification, own_status, own_status_axis, own_sector, groups, recorded_at, notes |
| `line-fields/<document_id>` | `line_id` | the document's own columns, verbatim, header as printed |
| `projects` | `project_id` | country, canonical_name, aliases, classification, classified_at, sector, notes |
| `assets` | `asset_id` | country, name, technology, location, operator_party_id, part_of, notes (capacity is an observation, never a column) |
| `agreements` | `agreement_id` | country, instrument, modality, sector, currency, tranche_of, notes |
| `line-referents` | `referent_row_id` | line_id, referent_kind, referent_id, status, method, method_version, confidence, justification_line_ids, decided_at, decided_by, supersedes, notes |
| `relations` | `relation_id` | from_kind, from_id, relation, to_kind, to_id, role, valid_from, valid_to, status, method, method_version, confidence, decided_at, decided_by, supersedes, line_id |
| `observations` | `observation_id` | subject_kind, subject_id, axis, measure, flow_type, basis, value, value_low, value_high, unit, currency, own_status, indicator_code, line_id, method, method_version, recorded_at, status, supersedes, notes |
| `timings` | `timing_id` | observation_id, date_role, date, date_precision, lower_bound, upper_bound, line_id, recorded_at |
| `external-ids` | (scheme, external_id) | kind, id, line_id, recorded_at (for a party: its IATI organisation identifier, ROR, LEI or Wikidata item, tier 1 of fusion section 3) |
| `adjudications` | `adjudication_id` | decision_type (`occurrence_membership`, `flow_coverage`, `perimeter_compatibility`, `identity`), subject_kind, subject_id, verdict, status, decided_at, decided_by, recorded_at, supersedes, notes |
| `adjudication-members` | (adjudication_id, kind, id) | role (one of `candidate`, `accepted`, `excluded`, `occurrence`, `covering_flow`, `covered_movement`, `opening`, `closing`, `context`) |
| `rates` | (currency, date, basis) | rate_to_usd, line_id, recorded_at (a publisher's own conversion, printed beside the original, is a `rates` row citing that line, so the ledger records that the publisher converted, at what rate) |
| `deflators` | (series, year) | value, line_id, recorded_at |
| `line-field-specs` | `document_id` | columns (the ordered list of a document's own column names, written at extraction, against which each `line-fields/<document_id>` header is validated) |
| `routes` | `old_id` | kind, new_id |
| `coverage` | (referent_kind, referent_id) | review_status, checked_at, route, document_ids, notes |
| `dry-searches` | as today | |
| `decisions.md` | as today | | 
| `terms` | `term_row_id` | *term_id*, kind, *list*, label, definition, scope_note, domain, range, external_scheme, external_uri, mapping_relation, recorded_at, decided_by, status, supersedes, notes |
| `status-crosswalk` | `crosswalk_row_id` | *(publisher_id, own_status)*, axis, shared_status, recorded_at, decided_by, status, supersedes, notes |
| `sector-crosswalk` | `crosswalk_row_id` | *(publisher_id, own_sector)*, purpose_code, recorded_at, decided_by, status, supersedes, notes |
| `perimeters` | `perimeter_row_id` | *perimeter_id*, country, name, scope, definition, recorded_at, decided_by, status, supersedes, notes |
| `marker-coefficients` | `coefficient_row_id` | *(donor_party_id, marker, score, year)*, coefficient, line_id, recorded_at, decided_by, status, supersedes |

[M2 for the D1 and D2 tables, `parties`, `party-names`, the document relations of `relations`, and the ontology tables; M3a for the record of searches; M3b for the D3 and D4 tables, except `deflators`, later, and the rows of `marker-coefficients`, M4 unless the comparison of requirement F19 uses climate-marked amounts]

The last five rows are the ontology tables, one file each under
`data/jetp/ontology/` (`terms.csv`, `status-crosswalk.csv`,
`sector-crosswalk.csv`, `perimeters.csv`, `marker-coefficients.csv`). Each is
keyed by a row identifier; the columns in *italics* are the chain key that
successive revisions of one entry share. A term's `term_id` is unique within
its `list`, so `cancelled` can be a value of several axes. A test fails when
a table or column of this section differs from the DDL, and the ontology's
alignment test (ontology section 5) checks the values. [M2]

**Target schema.** The table above is the schema the DDL declares today.
The rules of the specification require the changes below, which the DDL
does not yet carry. Each is a target of this contract, with the milestone
that needs it; a rule of this section that relies on a target column says
so, and the table above changes when the DDL does. A requirement whose rule
needs a target change is not met at a milestone while that change is still
a target: the Milestone column is when the DDL must carry it.

| Table | Target change | Rule it serves | Milestone |
|---|---|---|---|
| `line-referents` | gains `recorded_at`, the ledger's write time, which the as-of rule reads; `decided_at` stays as the descriptive time of the judgement | as-of rule (below) | M2 |
| `relations` | gains `recorded_at`, as for `line-referents` | as-of rule (below) | M2 |
| `line-referents` | gains `stance`, `likelihood` and `basis` (the quoted basis) beside `confidence`; `status` stays the separate workflow axis, since an accepted judgement of difference is meaningful | the judgement of fusion section 3 | M2 |
| `relations` | gains `stance`, `likelihood` and `basis`, as for `line-referents` | the judgement of fusion section 3 | M2 |
| `line-referents` | `justification_line_ids` becomes rows of a relation table, one row per decision row and justification line | the no-list rule (below) | M2 |
| `adjudications` | gains `method`, `method_version`, `stance`, `likelihood`, `confidence`, `basis` and a justification | the judgement of fusion section 3 | M3b |
| `line-field-specs` | keyed by document and table segment; each row maps a printed header, with its printed unit and scale wording, to a field name under a versioned mapping declared by the parser, and names the document type or series its list was copied from | extraction section 3, verbatim fields | M2 |
| `lines` | `classification` is required (not null); no candidate status on a line | extraction section 3, classification | M2 |
| `lines` | gains `status`, `supersedes`, `hidden` (set by the adapter) and `adapter_version`; a line is in force under the in-force rule below, and every count reads in-force lines only | extraction sections 5, 9 and 10; requirement F2 | M2 |
| `documents` | loses `edition_of`; the `relations` row is the one home of an edition relation | one home per fact | M2 |
| `documents` | gains `class` (frozen, living or series), recorded as a dated judgement | collection section 10; requirement DA6 | M3a |
| `retrievals` | `collection_method` takes the names of the five rungs of the access ladder, `script`, `browser-session`, `browser-automated`, `browser-manual` and `web-archive`, plus `local-record` for bytes recorded from a local file, which is not a rung; today's four values map onto rungs 1, 2 and 4 and `local-record` | collection section 8 | M3a |
| `retrievals` | gains `archive_url`, the public archive capture of the document's address, which is the public archive record of requirement F27 | requirement F27 | M3a |
| `retrievals` | gains a nullable `candidate_id`, for a fetch made to triage a candidate before admission; a rejected candidate's bytes stay under their hash and are never extracted | collection section 9 | M3a |
| `frame-entries` | new table: one row per expected authority or listed project of the authority frame, keyed by its kind and by the `party_id` of the authority or the `line_id` of the plan line that lists the project, with its terminal verdict and the recorded search behind it; no new identifier family, and no project referent is needed before M3b | collection section 3 | M3a |
| `rounds` | new table: the round log (country, language, search channel class, routes and terms, date, effort spent, candidates found, documents newly admitted) | collection section 5 | M3a |
| `candidates` | new table: a candidate's pointer, the round that found it, and the document it became when admitted | collection section 2 | M3a |
| `triage-judgements` | new table: the triage outcome of a candidate as a judgement of the one shape of section 4, with `status`, `supersedes` and `recorded_at`; a document's admission is its accepted admit row | collection section 9; as-of rule | M3a |
| `known-items` | new table: the frozen known-item list, each item with what identifies it, the held document matched to it if any, and whether its recovery followed a revision of the frame; kept outside the repository, sealed by its hash, until the freeze | collection section 6 | M3a |
| `tracker-claims` | new table: each examined claim of a declared tracker, with its outcome and the primary document it was traced to | collection section 7 | M3a |
| `assets` | loses `operator_party_id`; an asset's operator is a dated `party_in` row | the Party roles of the ontology, section 3 | M3b |
| `party-names` | gains a `preferred` flag; the value `preferred` leaves the form-type list, so a preferred form can also be an acronym | ontology section 2, Party | M3b |
| `adjudications` | `decision_type` gains `revision` (members: the earlier and the later line; verdict: development, late report, correction or rounded restatement) and `preference` (members: candidates, the accepted one and the excluded ones; verdict: the reason of fusion section 5), as `terms` rows | fusion sections 2 and 5 | M3b |
| `status-crosswalk` | gains `mapping_relation` (the SKOS mapping strength), required when a row is accepted | ontology section 5, traceability | M3b |
| `sector-crosswalk` | gains `mapping_relation`, as for `status-crosswalk` | ontology section 5, traceability | M3b |
| `retrievals` | gains `terms_position` (open licence, public-sector reuse, rights reserved, processing reserved, unknown), `robots_position` (the site's robots rules for the path fetched: allowed, excluded, none published) and `registration_used` (the name of the free public registration used, never a credential); the validator requires them non-empty from M3a | requirements F27 and C6; results section 7 | M2 for the columns; M3a for the check |
| `documents` | gains `access_route_kind` (address, archive record, registration) and `registration` (the free public registration a registration route needs, named, never a credential); the validator requires a route kind on every document | requirement F27 | M2 for the documents held; M3a for documents admitted by discovery |
| `documents` | gains `hosted_reading` (`allowed`, `local_only`), set by rule: `local_only` when the latest retrieval's `terms_position` is processing reserved; a `local_only` document is never sent to a hosted model | operation section 5; extraction section 6.3 | M2 for the column; M3a for the rule, with the terms positions |
| `document-addresses` | new table: a document's recorded addresses, each with the date from which it holds, so a relocation is a new address of the same document | relocation rule (below) | M4 |
| `lines` | gains `run_id`, `method` and `method_version`: the run that admitted the line and the method version that extracted it | extraction section 3, method and version; requirement Q4 | M2 |
| `observations` | gains `run_id` beside `method` and `method_version` | extraction section 11; requirement Q4 | M3b |
| `observations` | gains `own_status_axis` and `missing_reason`, the typed reason of an unknown value, from a closed `terms` list | extraction section 11; target conventions (below) | M3b |
| `line-referents`, `relations`, `adjudications` | gain `run_id` beside `method` and `method_version` (which `adjudications` gains as above) | fusion section 3, traceable | M2 for `line-referents` and `relations`; M3b for `adjudications` |
| `lines` | the locator syntax gains an assertion index for a prose span that carries several statements; the (`sha256`, `locator`) check reads it | extraction sections 4 and 5 | M2 |
| `lines` | gains `attributed_party_id` (nullable): the party the document attributes the line's part to; empty means the document's publishers jointly | requirement F1; extraction section 3 | M2 |
| `line-groups` | new relation table (line_id, heading_line_id) replacing `lines.groups`, so a line can sit under several headings and method notes | the no-list rule; extraction section 3, group | M2 |
| `projects` | loses `aliases`, a list in one column; a project's other names are the labels of the lines attached to it | the no-list rule | M3b |
| `readings` | new append-only journal (below) | extraction section 6.3; collection section 9; fusion section 3; requirements Q4 and Q17 | M2 |
| `runs` | new append-only journal (below) | operation sections 8 and 10; requirement Q14 | M2 |
| `dispositions` | new append-only journal (below) | extraction sections 2 and 7; requirements F2 and F5 | M2 |
| `restatements` | new append-only journal (below) | extraction section 8; requirements F4 and Q2 | M2 |

**Target journals.** Four tables record how a line or a judgement was made
and what became of each document. A row is never edited or deleted; a
correction is a new row that supersedes it, under the in-force rule below.
[M2]

- `readings`: one row per proposal of a reader, per arbitration, and per
  decision of the author, with its role (`reader`, `second_reader`,
  `arbiter` or `author`). A row names its run, the snapshot, the line or
  disposition it produced (empty for a rejected or undetermined proposal,
  which keeps its row), the candidate it judges when it is a judgement, the
  LLM identifier or person, the prompt and calibration versions, the
  proposed locator, label, classification and verbatim fields, the stance
  (right, wrong, undetermined), likelihood, confidence and quoted basis, the
  outcome of the item (admitted, rejected, undetermined), the step at fault
  for a rejected proposal (a step of requirement Q17, or the locator check,
  agreement or arbitration), the tokens in and out, the cost in US dollars
  and the GPU seconds, the hash of the full raw model response, and
  `recorded_at`. The raw response is stored under its hash beside the
  document bytes, under DVC, and never copied into the row. The validator
  checks that every line of an assisted reading has a row from each reader
  that proposed it, and an `arbiter` row unless the two readers agreed.
- `runs`: one row per run, written by the launcher at the start with the
  state `running` and superseded at the end by a row with the final state
  of operation section 10; a `running` row whose session is gone is closed
  as `failed` by the next launch. It is the structured twin of the run report
  (operation section 8): run identifier, job, commit of the code, machine,
  start and end times, state, method and method version, prompt hash, LLM
  and routed provider with the endpoint and the data-collection and
  retention settings of its hosted calls, sampling settings and adapter
  version; spend and GPU time are the sums of its readings. Every `run_id`
  of another table names a row here.
- `dispositions`: one row per disposition of extraction section 7, naming
  the document, the snapshot (empty for a document-level kind), the kind (a
  `terms` row), the reason, method and version, run, who decided,
  `decided_at` and `recorded_at`; the validator checks that the kind's grain
  matches whether a snapshot is named.
- `restatements`: one row per restatement of extraction section 8, a line
  and its origin line, or a snapshot and the last extracted snapshot of the
  same document whose normalised text it repeats, with the adapter version,
  run and `recorded_at`. An origin is never itself a restatement.

A judgement of the [fusion rules](jetp-fusion.md), once recorded, is a
decision row: a `line-referents` row, a `relations` row, or an
`adjudications` row, which holds the typed decisions (occurrence, flow
coverage, perimeter compatibility, identity) with their members.
Adjudication member roles are typed by decision: `occurrence_membership`
uses `occurrence`, `excluded` or `context`; `flow_coverage` uses
`covering_flow`, `covered_movement`, `excluded`, `opening`, `closing` or
`context`; `perimeter_compatibility` and `identity` use `candidate`,
`accepted`, `excluded` or `context`; the target types `revision` and
`preference` use, respectively, roles naming the earlier and the later line,
and `candidate`, `accepted` and `excluded`. An accepted occurrence decision needs
at least two occurrence observations; accepted flow coverage needs a covering
flow and a covered movement. A rejected decision retains its members as
history but contributes none to the in-force view. [M3b]

Accounts, the openings, movements, closings, residuals and
coverage gaps per agreement or perimeter that the
[fusion rules](jetp-fusion.md) define (section 7), are derived: they are computed from observations, timings,
rates and adjudications at build time, written under `data/derived/jetp/`
with the run identifier, the two cutoffs (valid time and knowledge) and
the `ontology_ref` (the hash of `data/jetp/ontology/` and of the DDL), and never edited. The adjudications they depend on are records, in the table above. [M3b]

Text layers ([extraction](jetp-extraction.md) section 5) are derived but
retained: the text layer of every snapshot with admitted lines is a DVC
artifact keyed by the snapshot's `sha256`, the adapter, its exact version and
the layer's own hash, kept under `data/derived/jetp/` and backed up with the
document bytes. A later adapter version writes a second layer beside the
first; neither replaces the other. [M2]

**Times per table.** Which times each table holds, what places a row in
the as-of state at a knowledge cutoff K (the rule below), and whether a
correction overlay may correct it. World time, the time a statement speaks
of, is held only in `timings`, in a relation's validity and in a rate's
date; everything else is ledger time. [M2 for the D1 and D2 tables; M3b
for the others]

| Table | Times it holds | Enters the state at K by | Overlay |
|---|---|---|---|
| `documents` | `published_date`, as the publisher dates it; admission, dated by the earliest retrieval that yielded a snapshot, or from M3a by the in-force triage judgement of outcome admit or context only | admission | yes: a document wrongly admitted |
| `retrievals` | `retrieved_at` | `retrieved_at` | no: a retrieval is an event, not a judgement |
| `snapshots` | none of its own | the earliest retrieval that yielded it | no |
| `lines`, `dispositions`, `restatements` | `recorded_at`; a printed date stays a verbatim field until read | `recorded_at` | yes |
| `observations`, `timings` | world time in `timings` (event, period, report date, reporting cutoff and the other roles); `recorded_at` | `recorded_at` | yes |
| `line-referents`, `relations` | `decided_at`, the judgement's own time; `recorded_at` (target); a relation's `valid_from` and `valid_to`, world time | `recorded_at`, and `decided_at` until the target lands | yes |
| `adjudications`, `party-names`, `external-ids`, `rates`, `deflators` | `recorded_at` (and `decided_at` where the table has it); a rate's `date`, world time | `recorded_at` | yes |
| the ontology tables | `recorded_at` | `recorded_at` | no: a changed term is a new ontology version, hence a new result |
| `readings`, `runs` | `recorded_at`; a run's start and end | not part of the state: they record how its rows were made | no |

Rules that the validator enforces:

- An observation cites exactly one line and its subject exists. [M3b]
- A line's `sha256` exists in `snapshots`, the bytes exist in the store (the
  document store and the comparator data directories, both under DVC), and
  at least one retrieval of the line's document yields that snapshot. [M2]
- A document that moves to a new address stays one document: the relocation
  is a new row of its recorded addresses (target table `document-addresses`),
  never a second document folded by `same_as`, and a retrieval of any
  recorded address is a retrieval of that document for the rule above. [M4]
- A decision row (`line-referents`, `relations`, `adjudications`) is in
  force when it is the latest `accepted` row of its supersession chain whose
  successors are all still `candidate`, or when it is the terminal row and
  `accepted`. A chain is linear: a row supersedes at most one row and is
  superseded by at most one. An accepted row is no longer in force once a
  row that supersedes it is itself `accepted` or `rejected`: an accepted
  successor replaces it, and a terminal `rejected` row revokes whatever its
  chain previously accepted, with no replacement needed. While the only
  successor of an accepted row is a `candidate`, the accepted row stays in
  force and the candidate is pending, so a proposed revision never blanks an
  adopted judgement ([fusion](jetp-fusion.md) section 2). The same rule
  governs document deduplication, so a rejected `same_as` re-enables
  extraction of the document it had folded. Lines and dispositions follow
  it too: their rows are accepted when written, so one is in force until a
  row that supersedes it is recorded. The DDL's in-force views still
  apply the earlier rule, under which any successor ends an accepted row;
  they are to follow this one. [M2]
- An observation carries no date of its own. Each date it reports is a
  `timings` row with its role, precision and bounds; a value is stored once
  and never repeated per date role. A flow carries `period_start` and
  `period_end` or one `event` timing. [M3b]
- Every record row in `lines`, `observations`, `timings`, `external-ids`,
  `rates`, `deflators`, `party-names` and every decision table carries
  `recorded_at`, the time the ledger wrote it; `line-referents` and
  `relations` gain it as a target column, and until then their `decided_at`
  stands in for it. A row belongs to the as-of state at cutoff K when its
  `recorded_at` is on or before K and no row with `recorded_at` on or before
  K supersedes it in a way that ends it under the in-force rule; the status
  test applies to the chain as it stood at K, not to the chain as it stands
  today. So a row accepted before K and superseded after K is in the state
  at K. The DDL test replays that case: A accepted, B superseding A recorded
  after K, and the state at K returns A. [M2]
- A correction release ([results](jetp-results.md) section 9) keeps its
  cutoff K and adds a named correction overlay: supersession rows that
  correct ledger errors, recorded after K, whose superseded rows were
  recorded on or before K. Its state is the as-of state at K with those rows
  applied, and nothing else recorded after K: a line extracted after K,
  even from a snapshot retrieved before K, is a new line, not a supersession,
  and first counts in the next regular release. [M3b]
- A document is admitted, for the as-of rule, when the ledger first held it.
  At M2, holding is dated by the earliest retrieval that yielded one of its
  snapshots ([extraction](jetp-extraction.md) section 3). From M3a, admission
  is a defeasible decision with a status and a supersession chain, the
  triage judgement of [collection](jetp-collection.md) section 9, and the
  as-of rule reads its `recorded_at`. [M2 for the retrieval date; M3a for the
  admission decision]
- `measure`, `basis`, `flow_type`, `modality`, `classification`, `relation`,
  `date_role` and every axis take values from the terms in force ([ontology](jetp-ontology.md)
  section 5); a new value is a `terms` row, with its definition, before
  the validator accepts it. The date roles are the one closed list of nine
  of ontology section 2. [M2]
- A monetary conversion cites a `rates` row; a script never carries a rate. [M3b]
- A locator has a syntax per format, and the validator checks it: for a
  PDF, the PDF page index and the printed folio when the adapter reads one,
  then the table and row for a table cell, or for prose the start and end
  anchors that [extraction](jetp-extraction.md) section 5 derives from the
  verbatim quote, with an occurrence index when an anchor is not unique in
  the text layer; for HTML, a CSS path or the same anchors, never a byte
  offset; for an API snapshot, the record key (an SDMX key for CRS, a
  P-number for the World Bank, an activity identifier for IATI), or for a
  record with none its ordinal in the file and the hash of its canonical
  serialisation; for a transcribed page, the page index and a rectangle in
  page-normalised coordinates. The
  meaning of a locator and how it is derived are extraction's (section 5);
  this rule fixes only its syntax. Locators admitted before the anchor rule,
  such as text anchors of at most 80 characters and paraphrase anchors of
  hand-made lines, stay valid under their method version; the validator
  enforces the anchor syntax on lines admitted after it. [M2]
- A publisher's cell that lists several names stays verbatim in the
  per-document fields table; the no-list rule applies to the ledger's own
  columns, and the parties in such a cell are attached through `party_in`
  rows (a funder, a channel, a promoter, an operator of the agreement,
  project or asset the line is about) or `role_in` rows (a mandate), one per
  name, citing the line. [M2 for keeping the cell; M3b for minting the parties]
- A publisher's method note that governs a page or a table (a pro-rating,
  an exchange-rate policy, a footnote conditioning every row) is a line of
  classification `heading` that `groups` the lines it governs, so that an
  observation reads the note through its line. The relation is stored on the
  member: its `groups` column names the heading, a foreign key into `lines`,
  since a column holds one value and a heading governs many lines; the heading
  is a line of the same snapshot and never the member itself. A line may sit
  under several headings (a section title and a footnote): in the target
  schema `groups` becomes rows of the relation table `line-groups`, one per
  member and heading; until then the column names the nearest heading, and
  a heading may name the heading that governs it, so a line reads the
  chain. [M2]
- A `line_id` is a minted key, independent of a row's changing attributes.
  Document extractors mint `<document_id>-<table>-<ordinal>` in extraction
  order, where `ordinal` is the mint counter of that document and segment,
  never reassigned, and position in the document is carried by the locator;
  a re-extraction that finds a dropped row appends it under the next
  ordinal. For prose, which has no table, the `<table>` segment is `text`.
  API snapshot keys retain the publisher's record identifier (an
  SDMX key, P-number or IATI activity identifier or its hash). Reviewed
  additions of previously unextracted passages use decision-scoped keys
  (such as `idn-progress25-...` and `line-1160-...`). All three
  families are appended only and never renumbered. The pair
  (`sha256`, `locator`) is unique across `lines` as a check, not as the key,
  so no two lines claim the same place in the same bytes and a locator too
  coarse to be unique, such as a whole report, is refused at ingestion.
  A minted key keeps the row's identity independent of its attributes,
  which is the normal form; the fingerprint and locator stay on the row as
  provenance. No existing identifier is renamed. [M2]
- The method of a line admitted before the method columns existed is
  derived from its identifier family: an extractor-minted key names the
  extraction script and the commit that wrote it; an API snapshot key names
  the ingestion run; a decision-scoped key names a person's reading or an
  assisted reading and carries no recorded reading of another role. The first replay under
  this specification counts the lines of each family and method
  ([requirements](jetp-requirements.md) Q1). [M2]
- A referent is minted only by a `line-referents` row with a basis; no
  ingestion script writes to `projects`, `assets`, `agreements`, `parties` or
  `perimeters`. The one exception is a party in a publishing role, which the
  document register mints: its justification is the `party-names` row that
  cites the document printing its name. [M2]
- One organisation is one `parties` row, whatever its roles: a publisher is a
  party that `document-publishers` links to a document, and a joint
  publication is one row per party. A party's names are `party-names` rows,
  one per form as printed, each citing the document or line it was read from;
  exactly one preferred form is in force per party, under the in-force rule
  of the decision tables (today a row of form type `preferred`; in the
  target schema, a flag beside the form type). The party row carries no name of its own. A
  publication names the form its document prints (`name_row_id`), and a page
  that shows a document's publisher shows that form, not the preferred one. [M2]
- Equality between referents is bounded to depth one: the source of an
  accepted `same_as` between referents is never the target of another, and
  a would-be chain is refused and raised as a conflict for review
  ([fusion](jetp-fusion.md) section 3). [M3b]
- `own_status` is copied, never normalised. `shared_status` appears only in
  `status-crosswalk`. [M2]
- No column holds a semicolon-separated list; a list is rows in a relation
  table. [M2]
- Target conventions, not yet checked by the DDL: money is a decimal string in whole currency units
  plus a currency, never a binary float, so 3.92 in a table headed USD billion
  is `3920000000` USD with the printed value, scale and label kept in the
  line's verbatim fields; an unknown value is an empty field with a typed
  missingness reason, and `null` on export; zero is a measured value. [M3b]
- `routes` maps identifiers from a published release (the site published
  before the ledger migration) to their new kind and identifier, so no public page route breaks. It is
  reserved for identifiers retired after they appeared in a published
  release; a fold before publication needs no route. The
  prepublication preview IDs were never public and are recorded as retired in
  the migration report, not redirected. [M3b]
- Every count exported names its unit: lines of a document, referents of a
  kind, or a perimeter observation. [M3b]

History: one file per table, nothing materialised, is kept from ticket
0858; `GLB` as a storage bucket from ticket 0885; the heading relation on
the member from ticket 0873. The decision-scoped key families were minted
for tickets 0970 and 1160. The minted-key rule was decided by the author on
2026-09-22 and amended on 2026-09-29 to describe the API and
reviewed-decision families already present. The money and missingness
conventions are carried from the backend design of 2026-09-14. The
non-redirection of preview identifiers is the author's decision of
2026-09-24 (PR #1492 removed the browser forwards).

## 2. What the Observatory serves

Every table of section 1 is served, one file per table, or named on the
Observatory's methods page as not served, with the reason. The ontology tables
are served too, as the Observatory's glossary. Nothing on a page adds lines of
one document to lines of another or to referents, and every count states its
unit. How the site is organised and worded is
[`jetp-observatory-presentation.md`](jetp-observatory-presentation.md). [M3b]

## 3. Engine

Whether the settled ontology calls for moving from CSV files to a graph or
SQLite engine has a division of labour for answer, not a replacement.

**CSV in git stays the system of record.** Git is the ledger's audit log:
every row enters through a reviewed pull request, a database file has no
diff, and a database regenerated from files is not a record of anything.
The tables hold 13 092 lines today ([requirements](jetp-requirements.md)
DA2), and every edition appends more: the steady state is tens of thousands
of lines a year, and the record format is designed for it, in two ways.
Lines of assisted readings are reviewed through their readings and the run
report, in one pull request per run under the run-output gate of
[operation](jetp-operation.md) section 4, not row by row.
Lines of bulk API snapshots are written by the ingestion script with a
manifest naming the snapshot, the row count and the field spec, and the
pull request reviews the manifest; a bulk line is adjudicated only when an
observation cites it. The common `lines` table is chunked by country and
year. Bulky raw material (raw model responses,
text layers) is stored under DVC by its hash and named from the tables. If
the volume of rows or their review outgrows git, Dolt, a SQL database
versioned like git with row-level differences, is the option recorded for
M4. [M2; M4 for the Dolt option]

The one DDL of section 1 declares the common tables. It does not declare
the per-document field tables, whose headers are the publisher's; each is
declared by its row in `line-field-specs`, written at extraction, and the
validator checks the file header against it. Two mechanisms, one contract. [M2]

**SQLite becomes the schema, the validator and the build engine.** One DDL file
under `config/` declares every table, key, foreign key and check of section 1.
The CSV headers are generated from it, so a column exists in one place. At
build time the CSVs load into a SQLite file under `data/derived/jetp/`, the
foreign-key and check constraints run as the validator, and the Observatory's
served JSON views and the accounts (E) are SQL queries over that file.
The file is deterministic for a given input, disposable, and may ship as a
downloadable release artifact, never as a
committed file: the build's only query engine. In the browser the Observatory keeps serving one JSON file per table
and joining at read time; at this volume an in-browser SQL engine would add a
dependency without a query that needs it. [M2]

**A graph engine is not warranted.** Every question the ledger asks is a
fixed-length path: observation, line, snapshot, document, publisher; or a
containment tree at most three levels deep; or a `same_as` cluster that the
design bounds to depth one. A property graph or triple store wins on
unbounded traversal and on schema-free ingestion, and the ledger wants neither:
its ingestion is the controlled classification of the [ontology](jetp-ontology.md), section 4. What the graph
world offers that is worth taking is its vocabulary. An RDF projection of the
SQLite file over PROV-O for the justification chain and SKOS for the status
crosswalk is a derived export, built when a consumer asks for it, and it costs
one script. If that consumer ever runs SPARQL over several ledgers, the
engine question reopens on their data, not on this one. [later for the RDF export]

History: the author asked on 2026-09-22 whether the settled ontology was
the moment to change engine; the backend design of 2026-09-14 (deleted
2026-09-30) had reserved an optional `<release_id>.sqlite` (`<edition_id>`
there), promoted here to the build's only query engine.

## 4. Matching records

The matching rules (decision shape, tiers, panel verification,
organisations, document deduplication) are
[fusion](jetp-fusion.md) section 3. This section says only how their
decisions are stored.

- A matching decision is a `line-referents` row or a `relations` row, with
  `decided_by` (a script name, an LLM identifier, or a person), `method`,
  `method_version`, `confidence`, `justification_line_ids`, `decided_at`,
  `status` and `supersedes`, under the in-force rule of section 1, and the
  target columns `stance`, `likelihood`, `basis` and `recorded_at`. A
  candidate match stays a row, counted, as the earlier `possible_matches`
  did. [M3b]
- Every recorded judgement has that one shape (stance, likelihood,
  confidence, quoted basis, who, method, version, time): a triage outcome of
  [collection](jetp-collection.md) section 9 in the M3a triage table, and
  each reading of a proposed line or candidate match, whose role is
  `reader`, `second_reader`, `arbiter` or `author` (fusion section 3), the
  last only when the author chooses to decide. Each reading is a row of the
  target journal `readings` (section 1). The likelihood is always that of
  the positive proposition (the two are the same, the proposal is right),
  so a judgement of difference is a low likelihood of sameness, and
  `undetermined` is an abstention that carries no likelihood ([fusion](jetp-fusion.md)
  section 3). [M2 for readings; M3a for triage]
- The settings of the reading protocol (readers, arbiter, acceptance level,
  calibration mapping, part size) and the tier thresholds are one
  configuration, versioned with the method; the match threshold a result
  applies is declared by the result (fusion section 3). The Observatory
  serves the decision record in the order of fusion section 3. [M2 for the
  reading settings; M3b for the tiers]
- A person's adjudication is recorded in the same row shape and in
  `decisions.md`. [M3b]
- Party name forms are `party-names` rows (a case or diacritic variant has
  form type `spelling_or_case_variant`); party identifiers are
  `external-ids` rows of kind `party`. Two parties are folded physically
  only under the rules that fusion section 3 says never make two parties
  (the same identifier of a declared scheme, a case or diacritic variant): the retained
  party gains the other's forms as `party-names` rows, its preferred form is
  stated by superseding the other's, and the retired identifier is recorded.
  Every other `same_as` between parties stays a judgement, and each result
  computes its view of parties at its match threshold. [M3b]
- Document relations (`same_as`, `edition_of`, `translation_of`) are
  `relations` rows between documents. [M2]

**Scope of the first implementation.** For lines: tier 1 by adopted rule;
tiers 2 and 3 as deterministic proposers; tiers 4 and 5 as the panel of
fusion section 3, on the local readers with the hosted arbiter. The 257
register rows and 67 plan lines matched by hand are the reference answers
for matching, not a review scope. The pairing of the 437 lines of the Indonesian
plan (CIPP) with the 1 142 lines of its progress report, whose literal name
intersection is 3, is the test bed for tier 2 and the first case for tier 3:
it is a set of candidate matches between lines of two documents, not an
edition relation between the documents.
For documents, the one tagging of [fusion](jetp-fusion.md) section 3: at
M2, tiers 1 and 2 run as deterministic proposers at registration, so a
snapshot whose text already exists is recorded before extraction: identical
bytes are recorded `accepted` under the rule the author adopted (fusion
section 3, judgement by adopted rule), and tier 2 registers a `same_as`
candidate that the judgement protocol of [extraction](jetp-extraction.md)
section 6.3 decides; tier 3
generates a bounded candidate list over the registered documents (at most
about 30 pairs, sorted by likelihood), judged under the same protocol; tiers 4 and 5
start at M3a, with the checking rule of [extraction](jetp-extraction.md)
section 6.3, when discovery brings mirrors. [M3b for lines, except
key-based pairing across snapshots of one document (extraction section 8),
M2; M2 for document tiers 1 to 3; M3a for document tiers 4 and 5]

History: counting candidate matches as rows follows ticket 0833.

## 5. Language, translation and summaries

A scan with no text layer (the Vietnamese decision of 2026 is one) is read by
transcription at M2, once the search for a born-digital copy has found none,
and each of its lines names the transcription as its method and version,
with a locator of page and region, so that its label has the provenance the
translation tables give derived text ([extraction](jetp-extraction.md)
section 6.4). [M2]

The four partnerships publish in Indonesian, Vietnamese, French and English,
and some documents exist in two languages. The ledger records the language of
every document and keeps every line's label in the language it was printed
in. A translation pair is two documents related by `translation_of`, with one
of them canonical for extraction ([fusion](jetp-fusion.md) section 3). Nothing in the ledger is a
translation presented as an original. [M2]

Translated labels and summaries are derived text, produced by an LLM or a
person, stored under `data/derived/jetp/` in two tables, regenerable and
outside the system of record:

| Table | Key | Columns |
|---|---|---|
| `line-translations` | (line_id, language) | text, method, method_version, produced_at |
| `document-summaries` | (document_id, language) | text, method, method_version, produced_at, snapshot_sha256 |

Both carry the provenance columns of the matching record, so a served
translation can say which LLM produced it from which bytes. The Observatory
may show a translated label beside the original and a machine summary on a
document's page, each marked as derived, and a reader who clicks through
reaches the snapshot in its own language. No observation cites a translation
or a summary; the justification is the line in the publisher's language, at its
locator, in its snapshot. The first implementation is the language column and
the translation relation; the two derived tables are nice-to-have and wait for
a reader who needs them. [M2 for the language column and the translation relation; later for the two derived tables]
