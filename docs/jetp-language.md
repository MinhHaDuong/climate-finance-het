# JETP ledger: language

How the ledger's design documents, schema and code speak about it. Decided by
the author on 2026-09-23 (decision 11 of [`jetp-ontology.md`](jetp-ontology.md)),
after the [ODEM acceptance review](jetp-odem-acceptance-review-2026-09-23.md).
The ontology itself, what the ledger's classes, relations and values mean, is
[`jetp-ontology.md`](jetp-ontology.md). What readers of the observatory see is
[`jetp-observatory-presentation.md`](jetp-observatory-presentation.md): the
words below are for the people who build the ledger, not for its readers.

## The ODEM frame

ODEM (Ontology, Data, Evidence, Models) is the framework of the author's
design note of 22 September 2026 on interactive causal inquiry. It names four
objects, each versioned, and keeps them apart. The ledger adopts its four
words and uses them in no other sense.

| ODEM object | In the JETP observatory | Where it lives |
|---|---|---|
| **O, Ontology** | What the ledger talks about and how it records it: classes, relations, closed value lists, status and sector axes, perimeter definitions, crosswalks and conversion rules. Every term has a definition, an external mapping where one exists, and a revision history | `data/jetp/ontology/` ([ontology](jetp-ontology.md) section 5); the observatory's Glossary |
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
attaches that line to a referent. The order of the [migration](jetp-ledger-migration.md) builds D4
before rewriting D3 because the old tables key observations on old
identities.

**Five terms retired or restricted.**

| Term | Use instead | Why |
|---|---|---|
| *evidence*, for documentary support | **justification**: the line and locator a row cites (a justification link, justification lines). *Evidence cutoff* becomes **knowledge cutoff**: rows recorded on or before K | In ODEM, Evidence is the computed result. Documentary support belongs to D |
| *model*, for a schema or a language model | **schema** for tables and columns; **LLM** for a language model used in matching or translation | Model is reserved for ODEM's M, which the observatory does not contain |
| *reconciliation* | **matching** for D4 decisions that mint or attach identities ([storage contract](jetp-ledger-storage.md) section 4); **account** for the E computation of opening, movements, closing and residual | One word named two operations at two ODEM levels |
| *edition*, for the ledger's own output | **release** for a frozen package of ledger and site (`data/jetp/releases/<release_id>/`). *Edition* keeps only its document sense: a publisher's successive issue (`edition_of`) | "Evidence edition", "monthly edition" and "document edition" were three different objects |
| *layer*, *stage* (*étage*), *fact* | **step D1 to D4** for the levels of the pipeline; **observation** for what a publisher stated | *Layer* named M1a sub-tables and *stage* the MVP levels; a ledger row is a publisher's statement read by a method, not a fact |

Domain words that coincide are unaffected: a *project stage* is a value of
the OC4IDS axis, and a PDF's *text layer* is its extractable text.

This document governs the design documents and the schema: the DDL (ticket 0871) declares no table or column named `evidence`,
`model`, `reconcil*`, `layer` or `fact`. The older design documents
([`jetp-backend-design.md`](jetp-backend-design.md),
[`jetp-backend-implementation-plan.md`](jetp-backend-implementation-plan.md),
[`jetp-storage.md`](jetp-storage.md), [`jetp-tracking.md`](jetp-tracking.md))
predate it and carry a note mapping their terms onto this one.

