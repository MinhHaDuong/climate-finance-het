# JETP Observer: specification

The JETP Observer is the system that finds the public documents on the Just
Energy Transition Partnerships, extracts and reads what their publishers
state, judges how those statements combine, keeps the result and releases it.
The ledger is its Data, the tables of steps D1 to D4; the Observatory is its
website. The [language](jetp-language.md) document defines these words. This page is the entry to the specification: ten documents,
read in the order below.

## Reading order

| # | Document | Question it answers | State |
|---|---|---|---|
| 0 | [Requirements](jetp-requirements.md) | What is the Observer for, for whom, and what must it deliver at each milestone? | reviewed |
| 1 | [Language](jetp-language.md) | Which words do the documents, schema and code use, and in which sense? | in force |
| 2 | [Ontology](jetp-ontology.md) | What does the ledger talk about: classes, relations, value lists, status axes? | in force |
| 3 | [Collection](jetp-collection.md) | How are documents sought, fetched and registered, and when does a search stop? | reviewed |
| 4 | [Extraction](jetp-extraction.md) | How is a publisher's statement extracted from a document into a line, and read into an observation? | reviewed |
| 5 | [Fusion](jetp-fusion.md) | How are statements matched to referents, weighed against each other and revised? | reviewed |
| 6 | [Storage](jetp-ledger-storage.md) | Which tables hold the ledger, which rules validate them, which engine builds them? | in force |
| 7 | [Results and releases](jetp-results.md) | Which results are computed, and how is a release frozen, versioned and corrected? | reviewed |
| 8 | [Presentation](jetp-observatory-presentation.md) | What do readers of the Observatory see, and how are its pages organised? | in force |
| 9 | [Operation](jetp-operation.md) | Who runs the Observer, on which machine, on which schedule, and how does it recover? | reviewed |

State is one of *draft* (complete, under review), *reviewed* (review findings
answered, awaiting acceptance) or *in force* (accepted, and what the build
implements or targets). The State column is the one record of a
document's state; the documents carry no status line of their own.

**Provenance.** Normative text carries no ticket numbers and no dates. Who
decided a rule, when, and under which ticket is written in a line headed
"History" at the end of the section the rule belongs to, and in the
[`attic/`](attic/README.md); a History line is provenance, never a rule.

## Structure

The documents follow the flow of the work: **collect, extract, judge, keep,
release, show, run**. Collection (3) collects, extraction (4) extracts, fusion
(5) judges, storage (6) keeps, results (7) release, presentation (8) shows,
operation (9) runs. Requirements (0) state what the flow is for; language (1)
and ontology (2) fix the words it is written in.

Documents 0, 2, 3, 4 and 5 are conceptual: they hold whether statements are
kept as rows, triples or text, and name no storage and no presentation.
Documents 6 to 9 carry the implementation: tables, engines, release
packages, pages and machines. A conceptual rule that needs an implementation
is stated once, in the conceptual document, and realised in the
implementation document that cites it. Where the implementation does not
yet realise a rule, the storage contract lists the change as a target
(section 1, target schema). The ontology tables follow the same rule: the
ontology says what they mean, and the storage contract (section 1) defines
their keys, columns and paths.

The frame is ODEM, defined in the [language](jetp-language.md) document:
**Ontology** (what the ledger talks about), **Data** (what publishers said, as
the ledger read it, in steps D1 to D4), **Evidence** (results computed from
Data under a declared ontology version) and **Models** (candidate causal
explanations, which the Observer does not contain). Collection and
extraction produce Data, fusion closes Data and opens Evidence, results
release Evidence.

## Milestones

Every rule carries the milestone that needs it: M2, M3a, M3b, M4 or later
(requirements, section 2.2). The M2 and M3 slice is the minimum that produces
correct, traceable results; a rule tagged M4 or later is specified now and
not built before its milestone. A rule already in force, implemented by the
migration, carries the earliest milestone that relies on it.

History: the milestone ladder is ticket 0725.

## Around the specification

Design history, superseded plans and dated review records are in
[`attic/`](attic/README.md): provenance, never authority. Reviews of the
specification itself are archived with their findings ledgers under
[`jetp-spec-review/`](jetp-spec-review/wave-1/README.md); version 1 is tagged
`jetp-spec-v1` once the author accepts it. The [legal note](jetp-legal-note.md)
is a supporting document: the legal basis under French law for collecting,
redistributing, reading with language models, publishing the site and
licensing the releases, with the open points for the CNRS legal service; it
is not legal advice.

History: the specification was assembled under tracker ticket 1703; its
reviews are tickets 1710 (wave 1) and 1711 (wave 2). The legal note was
added by the author on 2026-09-30, on finding W1-29.
