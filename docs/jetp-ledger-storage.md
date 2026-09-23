# JETP ledger storage contract

The tables that store the ledger, the rules the validator enforces, the build
engine, the matching record and the derived translation tables. Split from
[`jetp-ontology.md`](jetp-ontology.md) on 2026-09-23; the decisions listed
there govern this document. What the ledger's words mean is the
[ontology](jetp-ontology.md); how the current tables become these is the
[migration](jetp-ledger-migration.md).

## 1. Tables and rules

One file is one table, joins happen at read time, nothing is materialised
(ticket 0858, kept). Data tables under `data/jetp/`, ontology tables under
`data/jetp/ontology/` ([ontology](jetp-ontology.md) section 5), CSV, columns in this order.
A table too large for the repository's file ceiling, 512 000 bytes per
file in `.githooks/pre-commit`, is chunked by country and year into
`<table>.d/<CODE>-<year>.csv`, which stays one table. The `.d` suffix keeps a
chunk directory apart from a directory that shares a table's name:
`data/jetp/documents/` is the snapshot store under DVC, not the chunks of the
`documents` table, and the writer deletes only the `<CODE>-<year>.csv` files of
its own `.d` directory.

| Table | Key | Columns |
|---|---|---|
| `parties` | `party_id` | authority_category, country, notes |
| `party-names` | `name_row_id` | party_id, name, form_type, language, document_id, line_id, recorded_at, decided_by, status, supersedes, notes |
| `documents` | `document_id` | country, document_type, language, title, url, published_date, edition_of, active, notes |
| `document-publishers` | (document_id, party_id) | role, name_row_id (the form of the party's name this document prints) |
| `retrievals` | `retrieval_id` | document_id, retrieved_at, status, http_status, content_type, etag, last_modified, final_url, error, sha256 (nullable) |
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
| `external-ids` | (scheme, external_id) | kind, id, line_id, recorded_at (for a party: its IATI organisation identifier, ROR, LEI or Wikidata item, tier 1 of section 4) |
| `adjudications` | `adjudication_id` | decision_type (`occurrence_membership`, `flow_coverage`, `perimeter_compatibility`, `identity`), subject_kind, subject_id, verdict, status, decided_at, decided_by, supersedes, notes |
| `adjudication-members` | (adjudication_id, kind, id) | role |
| `rates` | (currency, date, basis) | rate_to_usd, line_id, recorded_at (a publisher's own conversion, printed beside the original, is a `rates` row citing that line, so the ledger records that the publisher converted, at what rate) |
| `deflators` | (series, year) | value, line_id, recorded_at |
| `line-field-specs` | `document_id` | columns (the ordered list of a document's own column names, written at extraction, against which each `line-fields/<document_id>` header is validated) |
| `routes` | `old_id` | kind, new_id |
| `coverage` | (referent_kind, referent_id) | review_status, checked_at, route, document_ids, notes |
| `dry-searches` | as today | |
| `decisions.md` | as today | |

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
  `rates`, `deflators`, `party-names` and every decision table carries
  `recorded_at`. An
  as-of state at cutoff K is the set of rows with `recorded_at` on or
  before K that are in force under the supersession rule.
- `measure`, `basis`, `flow_type`, `modality`, `classification`, `relation`,
  `date_role` and every axis take values from the terms in force ([ontology](jetp-ontology.md)
  section 5); a new value is a `terms` row, with its definition, before
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
  `perimeters`. The one exception is a party in a publishing role, which the
  document register mints: its justification is the `party-names` row that
  cites the document printing its name.
- One organisation is one `parties` row, whatever its roles: a publisher is a
  party that `document-publishers` links to a document, and a joint
  publication is one row per party. A party's names are `party-names` rows,
  one per form as printed, each citing the document or line it was read from;
  exactly one `preferred` form is in force per party, under the in-force rule
  of the decision tables. The party row carries no name of its own. A
  publication names the form its document prints (`name_row_id`), and a page
  that shows a document's publisher shows that form, not the preferred one.
- `own_status` is copied, never normalised. `shared_status` appears only in
  `status-crosswalk`.
- No column holds a semicolon-separated list; a list is rows in a relation
  table.
- `routes` maps every identifier the observatory has ever served to its new
  kind and identifier, so no public route breaks.
- Every count exported names its unit: lines of a document, referents of a
  kind, or a perimeter observation.

## 2. What the observatory serves

Every table of section 1 is served, one file per table, or named on the
observatory's methods page as not served, with the reason. The ontology tables
are served too, as the observatory's glossary. Nothing on a page adds lines of
one document to lines of another or to referents, and every count states its
unit. How the site is organised and worded is
[`jetp-observatory-presentation.md`](jetp-observatory-presentation.md).

## 3. Engine

The author asked on 2026-09-22 whether the settled ontology is the moment to
move from CSV files to a graph or SQLite engine. The answer is a division of
labour, not a replacement.

**CSV in git stays the system of record.** The ledger's rows are adjudicated
by reading a diff in a pull request; a database file has no diff, and a
database that is regenerated from files is not a record of anything. The
tables in section 1 hold about 8 000 rows today, but they will not stay
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

The one DDL of section 1 declares the common tables. It does not declare
the per-document field tables, whose headers are the publisher's; each is
declared by its row in `line-field-specs`, written at extraction, and the
validator checks the file header against it. Two mechanisms, one contract.

**SQLite becomes the schema, the validator and the build engine.** One DDL file
under `config/` declares every table, key, foreign key and check of section 1.
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
its ingestion is the controlled classification of the [ontology](jetp-ontology.md), section 4. What the graph
world offers that is worth taking is its vocabulary. An RDF projection of the
SQLite file over PROV-O for the justification chain and SKOS for the status
crosswalk is a derived export, built when a consumer asks for it, and it costs
one script. If that consumer ever runs SPARQL over several ledgers, the
engine question reopens on their data, not on this one.

## 4. Matching

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
chain when its status is `accepted` (section 1, rules). A reviewer revokes a
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

**Organisations.** Parties are under authority control, in the manner of
a library's name authority file or the ROR and GLEIF registries: one record
per organisation, every form of its name attached to it, one form preferred
(decided by the author on 2026-09-23). The tiers apply with two rules of
their own.

- Tier 1 is an external identifier: an IATI organisation identifier, a ROR
  identifier, an LEI or a Wikidata item, held in `external-ids` with kind
  `party`. Two names carrying the same identifier are one party.
- Forms that differ only by case, diacritics or spacing (Senelec and
  SENELEC) are merged when the party is minted: one party, several
  `party-names` rows of form type `spelling_or_case_variant`, never two
  parties and a `same_as`.
- Tier 2 runs only on real variants: an acronym against its expansion (AFD
  and Agence française de développement, PLN and Perusahaan Listrik Negara),
  a translation (Vietnam Electricity and Tập đoàn Điện lực Việt Nam), a
  former name. It writes `same_as` candidates between the two parties,
  reviewed by hand. Accepting one folds the parties: the retained party
  gains the other's forms as `party-names` rows of the matching form type,
  and `routes` sends the retired party identifier to it.

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

## 5. Language, translation and summaries

The four partnerships publish in Indonesian, Vietnamese, French and English,
and some documents exist in two languages. The ledger records the language of
every document and keeps every line's label in the language it was printed
in. A translation pair is two documents related by `translation_of`, with one
of them canonical for extraction (section 4). Nothing in the ledger is a
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

## 6. Consequences for the backend design

`jetp-backend-design.md` is revised, not replaced. Its sections 1, 5 to 8 and
10 stand. Sections 2 to 4 adopt the tables of section 1: `entity` becomes the three
identity kinds; `subject_type` gains `line`; `source` becomes publisher,
document and snapshot; `reported-positions` and the event journal merge into
`observations`. Its section 5 accounts keep their adjudications as the
`adjudications` and `adjudication-members` tables and their accounts as
derived outputs (section 1). Section 9 adopts the [migration](jetp-ledger-migration.md) table. Per the schema
review, the first executable metric is restated as a commitment measure until
a disbursement observation exists, the provenance index of section 8 is
declared a build-time validation artifact and never a served file, and the
source-editions triple, the alias chain rules, the dependency table between justifications (`evidence-dependencies` there) and the
concept-mapping profile leave the implementation scope until a metric needs
them. Tickets 0762, 0768 and 0769 closed on the previous contract; their
readers are retired at step 7.
