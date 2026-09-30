# JETP Observer: specification

The JETP Observer is the system that finds the public documents on the Just
Energy Transition Partnerships, reads what their publishers state, judges how
those statements combine, keeps the result and releases it. The Observatory
is its website. This page is the entry to the specification: ten documents,
read in the order below. Tracker: ticket 1703.

## Reading order

| # | Document | Question it answers | State |
|---|---|---|---|
| 0 | [Requirements](jetp-requirements.md) | What is the Observer for, for whom, and what must it deliver at each milestone? | draft, PR #1597 |
| 1 | [Language](jetp-language.md) | Which words do the documents, schema and code use, and in which sense? | in force |
| 2 | [Ontology](jetp-ontology.md) | What does the ledger talk about: classes, relations, value lists, status axes? | in force |
| 3 | [Collection](jetp-collection.md) | How are documents sought, fetched and registered, and when does a search stop? | draft, PR #1598 |
| 4 | [Extraction](jetp-extraction.md) | How is a publisher's statement read from a document into a line and an observation? | draft, PR #1596 |
| 5 | [Fusion](jetp-fusion.md) | How are statements matched to identities, weighed against each other and revised? | draft for author review |
| 6 | [Storage](jetp-ledger-storage.md) | Which tables hold the ledger, which rules validate them, which engine builds them? | in force |
| 7 | [Results and releases](jetp-results.md) | Which results are computed, and how is a release frozen, versioned and corrected? | being drafted (ticket 1707) |
| 8 | [Presentation](jetp-observatory-presentation.md) | What do readers of the Observatory see, and how are its pages organised? | in force |
| 9 | [Operation](jetp-operation.md) | Who runs the Observer, on which machine, on which schedule, and how does it recover? | being drafted (ticket 1708) |

## Structure

The documents follow the flow of the work: **collect, read, judge, keep,
release, show, run**. Collection (3) collects, extraction (4) reads, fusion
(5) judges, storage (6) keeps, results (7) release, presentation (8) shows,
operation (9) runs. Requirements (0) state what the flow is for; language (1)
and ontology (2) fix the words it is written in.

Documents 0, 2, 3, 4 and 5 are conceptual: they hold whether statements are
kept as rows, triples or text, and name no storage and no presentation.
Documents 6 to 9 carry the implementation: tables, engines, release
packages, pages and machines. A conceptual rule that needs an implementation
is stated once, in the conceptual document, and realised in the
implementation document that cites it.

The frame is ODEM, defined in the [language](jetp-language.md) document:
**Ontology** (what the ledger talks about), **Data** (what publishers said, as
the ledger read it, in steps D1 to D4), **Evidence** (results computed from
Data under a declared ontology version) and **Models** (candidate causal
explanations, which the Observer does not contain). Collection and
extraction produce Data, fusion closes Data and opens Evidence, results
release Evidence.

## Milestones

Every rule carries the milestone that needs it: M2, M3a, M3b, M4 or later
(ladder in ticket 0725). The M2 and M3 slice is the minimum that produces
correct, traceable results; a rule tagged M4 or later is specified now and
not built before its milestone. Documents 0, 3, 4, 7 and 9 are written with
tags; documents 1, 2, 5, 6 and 8 receive theirs after the vocabulary
alignment pass (ticket 1709).

## Around the specification

Design history, superseded plans and dated review records are in
[`attic/`](attic/README.md): provenance, never authority. Reviews of the
specification itself are tickets 1710 and 1711; version 1 is tagged
`jetp-spec-v1` once the author accepts it.
