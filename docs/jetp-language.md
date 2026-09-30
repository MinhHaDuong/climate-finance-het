# JETP ledger: language

How the JETP Observer's design documents, schema and code speak about it.
Decided by the author on 2026-09-23 (decision 11 of the ontology design,
[attic](attic/jetp-ontology-decisions-2026-09.md)), after the
[ODEM acceptance review](attic/jetp-odem-acceptance-review-2026-09-23.md),
and aligned across the ten specification documents on 2026-09-30 (ticket
1703). The ontology itself, what the ledger's classes, relations and values
mean, is [`jetp-ontology.md`](jetp-ontology.md). What readers of the
Observatory see is
[`jetp-observatory-presentation.md`](jetp-observatory-presentation.md): the
words below are for the people who build the Observer, not for its readers.

## The Observer, the ledger, the register, the Observatory

The **JETP Observer** is the whole system: collection, extraction, reading,
matching, results and releases ([requirements](jetp-requirements.md)). The
**ledger** is the Data of the ODEM frame: the tables of steps D1 to D4 below,
as [ontology](jetp-ontology.md) section 0 states; *ledger* in the titles of
the language, ontology and storage documents names these tables, not the
whole system. The **register** is step D1, a part of the ledger: the
documents the ledger holds, who published them, and how they were sought and
fetched; where a publisher's own register is nearby (the South African grants
register), it is the *document register*. The **Observatory** is the public
website that shows a release of the ledger and of the results computed from
it. The **document store** keeps the snapshot bytes the register points to;
it is not a table of the ledger.

## The ODEM frame

ODEM (Ontology, Data, Evidence, Models) is the framework of the author's
design note of 22 September 2026 on interactive causal inquiry. It names four
objects, each versioned, and keeps them apart. The Observer adopts its four
words and uses them in no other sense.

| ODEM object | In the JETP Observer | Where it lives |
|---|---|---|
| **O, Ontology** | What the ledger talks about and how it records it: classes, relations, closed value lists, status and sector axes, perimeter definitions, crosswalks and conversion rules. Every term has a definition, an external mapping where one exists, and a revision history | `data/jetp/ontology/` ([ontology](jetp-ontology.md) section 5); the Observatory's Glossary |
| **D, Data** | What publishers said, as the ledger read it. A pipeline of four steps, below | `data/jetp/` tables; the Observatory's paper trail: Documents, Document rows, Statements, Projects, Funding, Organisations |
| **E, Evidence** | Results computed from D under a declared O version: every count shown with its unit and perimeter, the accounts of [fusion](jetp-fusion.md) section 7, descriptive tables. E comes on top of D and never edits it | `data/derived/jetp/`, with a run record naming its inputs, cutoffs and ontology version |
| **M, Models** | Candidate causal explanations. The Observer has none. A causal study, deferred in ticket 0729, would consume a frozen release from outside the Observer | none |

The ledger is Data, guided by Ontology; Evidence comes on top; the
Observatory shows both.

**D is a pipeline.** Each step reads the steps before it, writes its own
tables and never edits an upstream row. [M2]

| Step | Name | Content | Tables |
|---|---|---|---|
| D1 | Register | What was fetched, byte for byte: publishers, documents, retrieval attempts, snapshots, and the record of how they were sought. A document is *registered* when it is in the register, and *held* when it is admitted and at least one of its retrievals yielded a snapshot | `parties`, `party-names`, `documents`, `document-publishers`, `retrievals`, `snapshots`, `coverage`, `dry-searches` |
| D2 | Lines | One publisher's statement at one locator in one snapshot, with its own fields verbatim | `lines`, `line-fields/<document_id>`, `line-field-specs` |
| D3 | Observations | A line read into a typed statement, measure, value and timings, by a named method version | `observations`, `timings`, `external-ids`, `rates`, `deflators` |
| D4 | Referents | Referents (projects, assets, agreements, parties, perimeters) minted by matching decisions over lines, and the relations between them | `projects`, `assets`, `agreements`, `parties`, `line-referents`, `relations`, `adjudications`, `adjudication-members`, `routes` |

D3 and D4 both read D2. An observation's subject is a line until matching
attaches that line to a referent. The order of the [migration](attic/jetp-ledger-migration.md) builds D4
before rewriting D3 because the old tables key observations on old
identities. [M3b]

**Activities.** Collection (discovery, triage and fetching;
[collection](jetp-collection.md)) fills D1; extraction writes D2; reading
writes D3; matching writes D4. Fusion is the set of rules for matching,
weighing and revising ([fusion](jetp-fusion.md)); results are computed as E
([results](jetp-results.md)).

**Words that span steps.**

- *Statement* is the generic word for what a publisher asserted; when the
  step matters, **line** (D2) or **observation** (D3). The extraction and
  fusion documents say *statement* for the line; the Observatory's
  Statements page shows observations.
- *Referents* are the things of D4; an **identity decision** is the
  judgement that lines share one referent.
- A **judgement** (fusion's word for the act of weighing), once recorded, is
  a **decision** row: a line-referent, a relation or an adjudication
  ([storage contract](jetp-ledger-storage.md) section 1).
- An **operation** is a funder's unit of lending, as lenders use the word; in
  the ledger it is an agreement, with the project it finances where one is
  identified. A comparator operation is a comparator record. The Operation
  document and milestone M4 ("operation") use the word in its other sense,
  running the Observer.
- *Route* is always qualified: a **search route** (the way a search reached
  a document), a **public access route** (the address or public archive
  record at which a document can be reached), a **page route** (an
  Observatory address), and the `routes` table, which redirects retired
  identifiers.
- *Scope* is qualified likewise: what is **in scope** for the Observer
  (requirements), a **declared extraction scope** (the parts of a document an
  extraction covers), a **counting scope** (an analyst's population, fusion
  section 6), and a project's scope, a domain word.

**Terms retired or restricted.** [M2]

| Term | Use instead | Why |
|---|---|---|
| *evidence*, for documentary support | **justification**: the line and locator a row cites (a justification link, justification lines). *Evidence cutoff* becomes **knowledge cutoff**: rows recorded on or before K | In ODEM, Evidence is the computed result. Documentary support belongs to D |
| *model*, for a schema or a language model | **schema** for tables and columns; **LLM** for a language model used in extraction, matching or translation (**LLM reader** as a method name) | Model is reserved for ODEM's M, which the Observer does not contain |
| *reconciliation* | **matching** for D4 decisions that mint or attach referents ([fusion](jetp-fusion.md) section 3), including **matching to CRS and IATI**; **account** for the E computation of opening, movements, closing and residual; **gaps between financial states** for the differences between announced, signed, reported and disbursed amounts, where *reported* is the amount a comparator record (CRS or IATI) reports | One word named two operations at two ODEM levels |
| *edition*, for the ledger's own output | **release** for a frozen package of ledger and site (`data/jetp/releases/<release_id>/`). *Edition* keeps only its document sense: a publisher's successive issue (`edition_of`) | "Evidence edition", "monthly edition" and "document edition" were three different objects |
| *layer*, *stage* (*étage*), *fact* | **step D1 to D4** for the levels of the pipeline; **observation** for what a publisher stated | *Layer* named M1a sub-tables and *stage* the MVP levels; a ledger row is a publisher's statement read by a method, not a fact |
| *source*, for who publishes | **publisher**, the party that publishes and answers for a document; **document**, **snapshot** or URL when one of those is meant. The authority category `secondary_source` keeps the old word until the schema renames it (ticket 1702) | The word has meant a URL since the first collection |
| *harvest*, *acquisition*, *ingest*, for finding and fetching | **collection** for the activity; **discovery** for the finding part; **retrieval** for one fetch. *Ingestion* keeps only one sense: a script's bulk write of API lines to D2 | Three words named one activity |
| *registry* | **register** for step D1 | Two spellings named one step |
| *cutoff*, for a likelihood-and-confidence bar | **match threshold**: the likelihood and confidence a candidate match needs in order to count in a result, declared per result, often as a **cautious** and an **inclusive** threshold. *Cutoff* names dates only: knowledge cutoff, discovery cutoff, reporting cutoff | One word named a date and a bar |
| *reader*, for code | **parser** for purpose-built code that extracts one publisher's series; **extractor** for any extraction method; **reader** only for an LLM reader or a person reading | *Reader* named a program, a parser, an LLM and a person |
| *reading*, for bytes to lines | **extraction** for bytes to lines (D2); **reading** for lines to observations (D3) | One word named two steps |
| *fixed*, for a document class | **frozen**, **living** and **series**, the three document classes of [collection](jetp-collection.md) section 10 | Two documents named one class two ways |
| *disposition*, for a candidate's outcome | **triage outcome** (admit, context only, reject, duplicate) for a candidate; **disposition** only for a registered document, or a snapshot of a held one, that yields no lines ([extraction](jetp-extraction.md) section 7) | Two closed lists shared one name and the value `duplicate` |
| *channel*, for a way of finding documents | **search channel**; the ontology's party role `channel` keeps its sense | One word named a search route and a party role |

Domain words that coincide are unaffected: a *project stage* is a value of
the OC4IDS axis, and a PDF's *text layer* is its extractable text.

This document governs the design documents and the schema: the DDL (ticket 0871) declares no table or column named `evidence`,
`model`, `reconcil*`, `layer` or `fact`. [M2]
