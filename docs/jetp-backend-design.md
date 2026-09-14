# JETP backend: evidence, reported positions and reconciled accounts

Design note — 14 September 2026. Plan phase. This specifies extensions to the
existing backend; it does not claim that the proposed schemas or migrations are
implemented. It develops the [storage contract](jetp-storage.md) and the
[tracking contract](jetp-tracking.md). The publication programme remains under
0726–0728; observation and analytical feasibility remain under 0729/0735.

## 1. Decision and purpose

Keep structured evidence in Git-versioned CSV, interpretation in Markdown, and
original source bytes in the existing content-addressed DVC archive. Generate
reconciled accounts, website JSON and any SQLite export from reviewed inputs.
SQLite is an optional local query/export format, never a second editable store.
The public website remains static and requires no database service.

Two evidence layers support the account:

1. **Event journal:** documentary assertions that something happened, with an
   event date or supported date interval.
2. **Reported positions:** what a source says about an entity at a reporting
   cutoff, whether or not the underlying event history is available.

The **reconciled account** is generated from these layers, stable identities,
reviewed relationships and explicit adjudications. It is not a third collection
of independently edited facts. Human interpretation remains authored, with its
supporting evidence identified.

An inventory entry can enter as a reported proposal before it has a lender,
agreement or known event. Official report inventories define the starting
population; project pages enrich and verify it. A project without a web page is
still a record. Inclusion in a plan does not prove financing, admission to a
later implementation cohort, or physical progress.

This is a documentary accounting system, not a replacement for a lender's
double-entry books. We cannot require debit/credit counterparts that public
sources do not disclose. We can require identities, comparable measurement
perimeters, explicit movements and transparent reconciliation differences.

## 2. Stores, formats and authority

Paths in this table are repository-relative. New filenames are proposed.

| Store | Format and location | Authority and persistence |
|---|---|---|
| Source catalogue and retrieval history | `data/jetp/sources.csv`, `manifest.csv` | Git; catalogue identifies publications/URLs, manifest preserves each acquisition attempt |
| Original documents and register snapshots | `data/jetp/documents/objects/<prefix>/<sha256>.<ext>` | Immutable bytes; existing `documents.dvc` pointer in Git; archive ownership remains on padme |
| Extracted text, OCR and table intermediates | Content-addressed extraction artifacts under `data/derived/jetp/` | Regenerable; retain extraction recipe, tool/version and input/output hashes |
| Identities, relationships and financing agreements | Existing `projects.csv`; new `agreements.csv`, `entity-relations.csv`, `perimeters.csv` | Git; reviewed identifiers and links, independent of observation dates |
| Event assertions | Existing `events.csv`, `implementation-events.csv`, `event-timing.csv`, with extensions | Git; retain original observations and explicit correction history |
| Reported positions | New `reported-positions.csv` | Git; one assertion about one measure/status, subject and reporting cutoff |
| Evidence and adjudications | New `evidence-links.csv`, `adjudications.csv`, `adjudication-members.csv` | Git; exact source support and reviewed decisions, including unresolved conflicts |
| Legacy staging | `plan-projects.csv`, country-specific observation tables and `source-claims.csv` | Retained during migration with stable crosswalks; no competing long-term ownership of the same assertion |
| Narrative and editorial dependencies | `data/jetp/editorial/` Markdown; new `editorial-evidence.csv` | Git; authored summaries with evidence references and review state |
| Schema and interpretation policies | Existing configuration plus proposed versioned schema/metric definitions | Git; one canonical definition per field, vocabulary and computation |
| Reconciled accounts and query exports | `data/derived/jetp/`; optional `<edition_id>.sqlite` | Generated; disposable, deterministic within a pinned build environment |
| Website payloads and code | `deliverables/jetp-observatory/` | Generated JSON plus HTML/CSS/JS; existing small handoffs remain reviewable in Git |
| Frozen editions | `data/jetp/releases/<edition_id>/release.json` and versioned public artifacts | Immutable descriptor and checksummed payloads; new correction edition for changed published content |

CSV conventions: UTF-8, header row, LF endings, standard quoting, stable column
order, and deterministic row ordering on export. Identifiers are strings. Money
is a decimal string plus currency; no binary-float rounding in canonical amounts.
Do not add new semicolon-separated identifier lists: use relationship rows.

Dates use ISO dates; timestamps use UTC with an explicit timezone. Unknown values
are empty CSV fields with a typed missingness field where the distinction matters,
and JSON `null` on export. Zero is a measured value. Distinguish `not_reported`,
`not_applicable`, `withheld`, `unreadable` and `unresolved` rather than substituting
zero. Estimated and rounded values carry a qualifier and, when supplied, bounds.

The current vocabulary file is `config/jetp_tracking.yaml`; proposed measures,
value types, units and aggregation rules should be defined in a versioned metric
dictionary, referenced by validators and exporters. Documentation describes that
dictionary rather than maintaining another executable taxonomy.

## 3. Identities and relationships

Preserve every existing `project_id` and public project route. Extend the project
registry with an `entity_type` distinguishing `project`, `programme` and
`component`. An unreviewed legacy row may temporarily have `unknown` type; it must
not be counted as a unique asset by default. A technical-assistance project is a
project with a purpose, not automatically a physical asset.

Use a typed subject reference, `subject_type` plus `subject_id`, wherever an
observation can concern several kinds of entity. The allowed targets are explicit:

| Subject type | Identifier resolves to |
|---|---|
| `partnership` | Country code in the country configuration |
| `perimeter` | A row of `perimeters.csv` describing a reporting population |
| `project`, `programme`, `component` | `projects.csv`, with matching entity type |
| `agreement`, `tranche` | `agreements.csv`, with matching agreement kind |

Validators must resolve these typed foreign keys; arbitrary free-text subject
types are not allowed. A derived SQLite database can construct a subject index
and enforce the same constraints during loading.

`agreements.csv` minimum fields:

`agreement_id`, `country`, `agreement_kind`, `parent_agreement_id`, `instrument`,
`funder_name`, `recipient_name`, `source_agreement_identifier`, `review_status`.

An agreement or tranche has its own stable ID. A named financing proposal may
have an ID before signature; its presence in this table does not assert legal
execution. Amounts and lifecycle states belong to observations, not a mutable
"current balance" column here. Party names may initially remain text; adopt a
party registry only when identity matching requires it.

`entity-relations.csv` minimum fields:

`relation_id`, `from_type`, `from_id`, `relationship`, `to_type`, `to_id`,
`valid_from`, `valid_to`, `date_precision`, `review_status`.

Relationships include `component_of`, `finances`, `tranche_of`, `same_as` and
`successor_of`. An agreement may finance several projects; a project may have
several agreements. The hierarchy alone never authorises splitting an amount.
Any project-specific share requires its own sourced observation. Superseding or
merging identities retains old IDs as aliases/redirects and preserves the history.
Review must distinguish equality, partial overlap and succession.

`perimeters.csv` defines the population and financial coverage of an observation:

`perimeter_id`, `country`, `name`, `scope`, `definition`, `parent_perimeter_id`,
`membership_basis`, `report_edition_id`.

Here `scope` retains the existing `jetp_strict` / `ipg_energy_extended`
distinction. A perimeter further distinguishes, for example, IPG-only pledges,
all-partner instrument allocations and project-register allocations. Explicit
membership uses relationship rows; an aggregate whose constituents are not
disclosed remains a source-defined perimeter, not a fabricated membership list.
Programme and component populations may overlap and are not automatically additive.

## 4. Observation schemas

The following are minimum contracts, not final column declarations. Extensions
must have schema validation at read/write boundaries and documented compatibility
with the current files.

### Shared assertion fields

Each event or position needs a stable assertion ID, typed subject reference,
`perimeter_id`, `measure`, typed value fields, review state and provenance links.
Retain the original source term alongside any harmonised classification.

Use `value_type` (`money`, `number`, `count`, `status`, `text`), `value_decimal`,
`value_text`, `unit`, `currency`, `value_qualifier` and `missing_reason` as applicable.
Exactly one value representation is populated, unless an explicit missing value
is recorded. Monetary measures require currency; counts require a declared unit
such as source rows, projects or agreements. A status uses a controlled vocabulary
within its dimension. Financing, preparation, implementation and disclosure remain
separate dimensions.

Each assertion carries `recorded_at`, `recorded_by`, `review_status`,
`supersedes_id` and `correction_reason` when applicable. Review decisions reference
assertions rather than silently rewriting their source meaning. Derived values
are distinguishable from reported ones and identify the derivation and inputs.

### Event journal

Keep `events.csv` and `implementation-events.csv` initially. Existing `event_id`
and `implementation_event_id` values remain stable assertion IDs. Extend their
contract with subject/agreement references, measure, `amount_basis`, and an
optional `occurrence_id` assigned through reconciliation.

An occurrence identifies one underlying event supported by one or more assertions.
Different sources reporting the same payment are multiple assertions, not multiple
payments. Until identity is adjudicated, do not sum possible duplicates. A repeated
publication of the same cumulative amount is also not a new movement.

Supported event timing uses the existing `event-timing.csv` concepts:
`event_start`, `event_end`, `event_precision`, and `date_role`. Add or formalise
`recorded_at` separately. An unknown event date remains unknown. A report saying
"operational at quarter-end" belongs primarily to reported positions and cannot
supply an invented commissioning date.

`amount_basis` distinguishes an incremental payment, agreement face value,
adjustment, cancellation and other supported quantities. The metric definition
must specify which movements affect which account. Signing a loan is not an
addition to cumulative disbursement; approval and signature amounts must not be
added to each other.

### Reported positions

`reported-positions.csv` minimum fields, in addition to shared assertion fields:

`position_id`, `report_edition_id`, `as_of_start`, `as_of_end`, `as_of_precision`,
`basis`, `original_label`.

`basis` distinguishes cumulative amount, period flow, balance, status and inventory
membership. A month-only observation carries month precision and bounds; do not
claim an exact event on its last day. Publication and retrieval dates come from
source/edition and acquisition records, never from the reporting cutoff by default.

One report row with project name, status and amount may generate several positions
sharing a source-row locator. One monetary position may be supported by several
documents. A missing amount can coexist with an identified project and a known
status. Inventory order and original labels survive extraction and reconciliation.

For reported aggregate counts with undisclosed members, retain the count and its
perimeter. Existing Vietnamese unnamed slots remain addressable legacy records,
but do not become inferred projects or get paired to RMP names without evidence.

### Evidence and source editions

`sources.csv` remains the curated source identity. Extend acquisition metadata
with stable `acquisition_id`; introduce an edition/snapshot index if needed to map
`report_edition_id`, `source_id`, publication date, document hash and acquisition.
One URL may serve different editions; the same document may have several mirrors.
Do not identify a document solely by its URL or "latest successful retrieval".

`evidence-links.csv` minimum fields:

`evidence_id`, `record_kind`, `record_id`, `source_id`, `report_edition_id`,
`acquisition_id`, `document_sha256`, `locator`, `extraction_id`, `support_role`,
`review_status`.

`record_kind` selects a validated target table: event, position, relation, claim
or adjudication. `support_role` distinguishes supporting, contradicting and
contextual evidence. Existing source IDs/hashes/locators remain readable while
these links are introduced. A project-source association alone does not support
every claim about that project.

PDF locators specify both printed page and PDF page index where they differ, plus
table/row/cell or section. HTML locators retain a heading and stable element or
embedded-table row identifier. Extraction records identify input hash, parser/OCR
version and configuration, output hash and any manual correction. Preserve the
original-language text; a translation is an attributed derivative, not the source.

## 5. Reconciliation and generated accounts

Store human decisions, not a second set of balances. `adjudications.csv` contains
`decision_id`, `decision_type`, `verdict`, `reason`, `reviewer`, `reviewed_at`,
`policy_version`, `supersedes_id`. `adjudication-members.csv` links each decision
to typed records and their roles. Decisions cover identity, duplicate occurrences,
source corrections, perimeter compatibility and preferred interpretations.

Generate an account for a declared subject, perimeter, measure, currency, valid
cutoff and evidence-availability cutoff. It includes:

- reported positions, without discarding contrary sources;
- opening position and applicable documented movements;
- reconstructed closing position, when the evidence supports one;
- reported-versus-reconstructed difference and coverage limitations;
- contributing assertion/occurrence IDs, exclusions and adjudications;
- separate financial, preparation and implementation status assessments.

An opening position plus movements is valid only for a compatible measure and
perimeter. Do not add payments already included in the opening cumulative figure.
If the opening position or applicable movement history is unknown, the closing
position is not reconstructible. Keep the reported position available.

**Illustrative account:** a source reports cumulative disbursement of EUR 20m at
30 June. Independent documents establish EUR 15m of distinct payments over the
same period with a verified zero opening balance. The EUR 5m difference is an
unexplained reconciliation residual. It is neither an invented payment nor proof
of an error. Without the verified opening balance, even that reconstruction is
not justified. Currency conversions require an explicit rate, date, source and
rounding rule; original-currency observations remain canonical.

**Existing South Africa example:** Q1 reports 129 implementing and 87 completed
records; the archived register yields 128 and 88. Both total 257. Retain each
snapshot, identify the count basis, and investigate the underlying identity or
timing difference. Do not alter an individual project to force equality. The
USD 6.12bn instrument allocation and USD 4.32bn portfolio allocation also have
different perimeters; they are not a failed balance reconciliation.

The current exporter chooses the highest-ranked coded financing stage found for
a project. Replace this summary progressively with an as-of account that can show
mixed agreement stages, cancellations and reversals. A signed tranche must not
hide another tranche still awaiting approval. Status is not universally monotonic.

## 6. Time, corrections and change control

Maintain two independent time axes: the world described by the evidence and when
that evidence became available to this system. Record source publication and
retrieval separately from both. A backdated report can revise our understanding of
June in September without being treated as knowledge available in June.

New reporting dates create new positions. Source corrections and our coding
corrections create superseding assertions with reasons; original evidence remains
recoverable. Withdrawal is an explicit lifecycle assertion, not deletion. A
retraction of an erroneous assertion is an adjudication, not automatically an
economic cancellation. Never create a fictitious reversing payment to fix a typo.

Use append-only evidence semantics, with narrowly controlled changes to identity
metadata and review metadata. Git records exact file versions; explicit IDs,
supersession and validity fields make history understandable without mining Git.
Prevent supersession cycles. Breaking field/meaning changes increment schema
versions and require a migration crosswalk, compatibility tests and a release note.

All canonical edits pass through a branch and reviewed change. Stage extraction
results separately; validate before promotion. Give each new ID a deterministic
source key or collision-resistant allocation. Do not resolve CSV merge conflicts
by taking one entire file. Revalidate uniqueness, foreign keys and provenance after
merging. Preserve failed acquisition attempts and old successful snapshots.

Sources can disagree after review. `unresolved` is a publishable evidence verdict;
it is not permission to manufacture a preferred value. A releasable account may
therefore contain gaps. Documentation completeness and scientific certainty are
separate release conditions.

## 7. Updating and publication

1. **Discover:** check official report inventories and subsequent official news.
   Record the named document, routes, search date, budget and acceptance criteria.
   Recheck South Africa Q2 and other successor reports during refreshes; do not
   imply background monitoring merely because a refresh policy exists.
2. **Acquire:** fetch through the existing harvester, validate content type, save
   bytes by hash, append acquisition metadata. A failed or unchanged retrieval
   creates no new substantive event. DVC push remains padme's responsibility.
3. **Extract:** produce reproducible candidate inventory/position/event rows.
   Reconcile every official inventory section to extracted rows or explicit
   exclusions. Preserve source rows before identity matching.
4. **Review:** match entities and agreements, classify measure and timing, add
   evidence links and adjudications. Automated extraction does not ratify its own
   outputs. Repeated runs must be idempotent for unchanged source assertions.
5. **Reconcile:** rebuild affected accounts. Compute changes in values, statuses,
   perimeters and source availability; distinguish real developments, late reports,
   corrected source data and changed interpretation.
6. **Edit:** flag narratives and figures whose input assertions changed. Preserve
   relevant existing summaries; revise their interpretation and evidence links.
   A principal report need not be the sole source of a country summary.
7. **Freeze:** commit reviewed inputs first, then build the package and descriptor
   from that existing SHA. Include schema/policy versions, code/environment versions,
   DVC object references, row/coverage validation and artifact hashes.
8. **Publish:** validate the complete static package, then advance the current
   edition pointer. A failed build leaves the prior edition available. Corrections
   create `YYYY-MM-rN`; they never rewrite a previously published edition's bytes.

Collection, transformation and rendering remain separate stages. Extend each
Make/DVC target's declared inputs when adding tables, schemas or policies. Preserve
the repository's one-output-per-build-invocation convention. There is no network
fetch during website generation and no live database dependency for readers.

## 8. Full traceability to the web page

The required chain is bidirectional:

```mermaid
flowchart LR
    A[Archived source bytes and SHA-256] --> B[Acquisition and source edition]
    B --> C[Extraction and page or row locator]
    C --> D[Event or position assertion]
    D --> E[Identity links and adjudication]
    E --> F[Reconciled account or editorial claim]
    F --> G[Frozen JSON field and derivation]
    G --> H[Web page figure or sentence]
```

Every published number, status and substantive narrative claim must resolve to
assertion IDs or an explicitly identified calculation. Add an exported provenance
index keyed by stable `display_claim_id`, with JSON pointer, source assertion IDs,
derivation/policy ID, input/output hashes, and editorial evidence when applicable.
Generated HTML elements can carry `data-claim-id`; the page provides a quiet
evidence link/popover rather than displaying internal implementation details.

`editorial-evidence.csv` links a stable narrative claim ID and Markdown block ID
to supporting/contradicting assertions and review state. Give authored claims
stable block identifiers; a file/line alone is fragile across edits. Rewording a
claim requires review of its links. General explanatory prose needs no invented
numeric assertion, but substantive interpretation must identify its evidence.

A provenance entry must resolve through the exact observation evidence link to
the exact archived snapshot. The current source catalogue's latest retrieval is
useful discovery metadata, but cannot stand in for the document used to support
an older event. Export record-specific hashes and locators, not just a country-level
list of sources. Identical bytes from two mirrors do not constitute two independent
confirmations; derivative reports should retain their upstream evidence relationship.

The public package includes the evidence graph, IDs, source URLs, hashes, locators,
calculation definitions and editorial dependencies needed to inspect claims.
Redistribute raw documents only under applicable terms. Where raw bytes cannot
be public, retain internal archive availability and explain the public access
limit. Reproducing the website from a frozen package and independently examining
every original document are distinct capabilities.

The release descriptor must cover all assets that affect rendering: country and
overview JSON, HTML, JS, CSS, definitions, editorial payloads and provenance index.
Pin software/environment versions for byte-level regeneration; a Git SHA alone
does not identify external dependencies. Put output hashes in a later descriptor
commit to avoid a self-referential checksum/commit dependency. Semantic claims
remain reproducible even when an external live URL later changes or disappears.

### Country cards and pages

Preserve two source roles: **principal official reference** and **latest subsequent
official news**. Record source IDs, publication dates, selection/check date and
scope qualifications independently of the headline. The principal reference is
normally the latest comprehensive Secretariat report; Vietnam may need an
explicitly identified local substitute, and Senegal currently uses its plan.

The homepage country box links only to the principal reference. Its text is a
reviewed synthesis of the total evidence, not an extract constrained to that
reference. The country page shows both source roles, their dates, the incremental
update and the retained substantive summaries. A newer news figure must carry its
own evidence in the export even when the card's sole reference link remains older.
If no subsequent official item is located, retain an explicit gap rather than
mislabel an earlier article as later news.

For example, Indonesia's USD 3.92bn approval headline may be supported by the
8 September 2026 JDU newsletter while its principal reference remains the 2025
report with an older USD 3.1bn snapshot. They are different dated observations;
neither is a payment total. The source-role distinction must survive the JSON
handoff and cannot be encoded only in prose.

The country publication contract should expose `principal_reference_source_id`,
`latest_news_source_id`, `source_selection_checked_on`, `headline_claim_id` and
`summary_claim_ids`. Keep `headline_source` as a compatibility alias for the
principal reference until the frontend migrates; never interpret that alias as
exhaustive support for the headline. Each claim ID resolves to the exported
provenance index. Country-level claims must be exported even when they have no
project association; the current project-only claim selection is insufficient.

A generated provenance entry has this logical shape (illustrative IDs):

```json
{
  "display_claim_id": "idn-approved-finance-20260908",
  "payload": "data/IDN.json",
  "json_pointer": "/country/headline",
  "assertion_ids": ["position-idn-jdu-approved-20260908"],
  "adjudication_ids": [],
  "derivation": {"id": "format-money-billions", "version": "1"},
  "evidence_ids": ["evidence-idn-jdu-newsletter-1"],
  "editorial_claim_id": null
}
```

The evidence ID resolves to a document hash, acquisition and paragraph locator;
the release descriptor supplies the input revision and payload/code hashes. For
a computed aggregate, assertion IDs enumerate the contributing observations and
the derivation identifies exclusions and overlap rules. An authored summary uses
an editorial claim ID and its evidence joins instead of pretending to be a formula.

Terms such as allocation, approval, disbursement, record, project, plan and
programme can have short hover/focus/tap definitions generated from a shared
public glossary. Definitions explain the measures without changing source
semantics or implying cross-country equivalence. Keep methodological caveats in
the relevant account/evidence view; keep build and migration scaffolding out of
the country narratives.

## 9. Migration from the current backend

Audit baseline: `bbb3a215` on main. Related local MVP documentation/content commits
`a3e30848` and `aac1ff2b` clarify report baselines and source fallbacks; they do not
implement this data model. The two-link UI increment is also still pending.

| Current implementation | Required extension or migration |
|---|---|
| `projects.csv` holds projects and programmes with stable IDs | Add reviewed entity types and relationship edges; preserve IDs/routes and separate count slots |
| No dedicated agreement/tranche identities | Add agreement registry and many-to-many project links; leave unidentifiable agreements unresolved |
| `events.csv` mixes event assertions and register-derived observations | Classify each row; move/crosswalk reported states into positions; do not promote old register dates to event dates |
| `implementation-events.csv` contains dated reports of states | Preserve the source assertion; create event timing only where an actual transition is supported |
| `event-timing.csv` distinguishes date roles and precision | Extend consistent timing to positions and recording/revision history |
| `plan-projects.csv` and country observation tables retain source rows | Ingest into the shared position contract with source-row crosswalks; start with Vietnam's un-ingested RMP inventories |
| `source-claims.csv` includes structured facts in text and semicolon joins | Promote measurable assertions to typed positions and relational evidence links; preserve prose claims and legacy IDs |
| `project-source-links.csv` is broad, project-level linkage | Keep it for discovery/context; add assertion-specific evidence links and snapshot identity |
| Sources and manifest preserve hashes but lack stable acquisition IDs | Add IDs and source-edition mapping; deduplicate neither failed attempts nor distinct retrieval history |
| Exporter picks most advanced coded financing stage | Generate as-of multidimensional accounts; retain reported versus inferred distinctions |
| Country headline is manually configured with one source | Separate principal/news roles from headline claim IDs and its multiple evidence inputs |
| Country Markdown is exported without statement-level dependencies | Add editorial claim IDs and evidence joins, preserving useful existing prose |
| JSON contains source metadata and input hashes | Add exact assertion-to-display provenance and freeze all rendering assets |
| Release directories describe a future process | Implement immutable package/descriptor validation and a two-edition refresh rehearsal |

Migrate in bounded slices: (1) schema contracts and identity/evidence crosswalks;
(2) reported positions and report inventory ingestion; (3) agreement/occurrence
reconciliation; (4) account exports and editorial/display provenance; (5) frozen
release/update rehearsal. Keep compatibility readers until consumers switch. A
migration manifest records old table/ID, new table/ID, transformation, reason and
review status. Retire legacy write paths only after row-by-row reconciliation;
never maintain two independently editable versions of the same assertion.

The current `scripts/jetp/build_observatory.py` and `_observatory_data.py`, their
Make inputs and browser renderer are the extension points. Reuse the existing
harvester and DVC archive. Do not start with a new database service, application
framework or duplicate corpus. Update 0726–0728 handoffs from this note before
implementation; split substantial independently deliverable changes into their
own tickets rather than silently enlarging the pending UI increment.

## 10. Acceptance and first tests

The first schema/export test should combine one report-listed project without a
project page, two agreements at different stages, two sources reporting the same
payment, and a cumulative reported position. It must retain the inventory entry,
avoid duplicate movements, show mixed stages and expose any reconciliation gap.

Further acceptance checks:

- Every official inventory row is accounted for by a position, a reviewed mapping
  or an explicit exclusion; aggregate unnamed slots are never invented identities.
- Opening balance plus eligible movements is tested with known overlap and an
  unknown opening balance; unsupported totals remain unavailable.
- A reported completed state does not create a commissioning date or payment.
- Later cancellation and revised reporting remain visible; the account at an
  earlier evidence cutoff remains reproducible.
- A programme and component cannot double-count an agreement or be treated as
  two disjoint populations without evidence.
- Every published claim traverses to the correct saved source hash and locator;
  a changed live URL or newer acquisition cannot redirect historical provenance.
- A correction identifies affected narratives, displays and edition differences.
- Unknown typed references, ID collisions, supersession cycles, incompatible
  currencies/perimeters and unsupported amounts fail validation.
- A card can use newer reconciled evidence while linking to an older principal
  reference; its country page exposes both sources and their distinct dates.
- A frozen edition renders without network/DVC access, and raw-evidence replay
  succeeds separately against the pinned internal archive where access is allowed.

Implementation tests belong to the affected existing contracts and tickets.
This design note requires document/schema consistency review and working relative
links; it does not require running the data pipeline or adding placeholder tables.
