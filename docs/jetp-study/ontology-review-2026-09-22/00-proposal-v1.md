# Proposed JETP ledger ontology (draft, 2026-09-22, for review)

Context: the JETP observatory ledger in repo climate-finance-het tracks four Just Energy
Transition Partnerships (ZAF, IDN, VNM, SEN). Canonical tables under data/jetp/*.csv;
contract in docs/jetp-tracking.md; proposed target data model in docs/jetp-backend-design.md
(esp. section 3 "Identities and relationships", section 4 "Observation and research schemas").

## Six kinds

Asset. A physical thing at a place: a plant, a line, a substation, a coal unit. Has capacity,
operator, location; moves through implementation states (proposed ... operational ... retired).
Outlives any project (Tri An expansion is a project on an existing asset).

Project. A bounded undertaking with scope, budget, owner, that creates or changes assets, or
produces something non-physical (study, training). The unit plans list and funders finance.
May concern one asset, several, or none (technical assistance).

Programme. A governance and budget envelope containing projects or components
(JT-Mpumalanga, PUELEC, Just Transition Support Programme). Relation component_of. In the backend
model project/programme/component are one entity kind with a dated classification.

Proposition. An intent put forward by a promoter for adoption or financing, before any decision.
The state before a project exists: a Senegal Annex 2 submission, a position in the Viet Nam RMP
annexes, an unsigned financing proposal. Two propositions can describe the same future project;
a proposition can die without becoming one.

Plan. A dated document by an authority enumerating propositions and projects it intends to see
realised, with ranking and estimates (CIPP 2023, RMP 2023, Senegal IP, IDN progress report 2025).
A source edition with a cutoff, not an entity. Defines a perimeter; plans succeed one another.

Agreement. The money side: funder, instrument, amount, counterparty; states need, announced, mou,
approved, signed, disbursed. Finances one or many projects; a project draws on many agreements.
No table yet; financial events are keyed to projects.

## Relations

- plan LISTS propositions and projects (one line each; the line is the plan's assertion)
- proposition BECOMES project on a reviewed decision (plan line `matched` reconciliation)
- programme CONTAINS projects and components
- project CONCERNS assets (zero or more)
- agreement FINANCES projects; a financial event is an observation about an agreement at a date;
  an implementation event is an observation about an asset at a date
- partnership DEFINES the perimeter within which plans and agreements count as JETP

## Current storage and known blurs

| Kind | Lives now | Blur |
|---|---|---|
| Asset | nowhere; capacity_mw on implementation-events.csv | needed for retirement questions (Cirebon-1) |
| Project | projects.csv (404) | mixes projects, programmes, components, and 257 ZAF funder-side register lines |
| Programme | projects.csv by name repetition | 21 names repeat; 13 rows for one skills programme |
| Proposition | plan-projects.csv plan_only (1 561); VNM 21 count slots | slots are a perimeter count, not 21 propositions |
| Plan | sources.csv rows typed investment_plan / progress_update | a plan's list is a perimeter, not modelled as one |
| Agreement | events.csv via funder/instrument columns | ZAF register lines are closer to tranches than projects |

Open calls: reclassify ZAF register lines as agreements/tranches? keep matched plan lines as
proposition records or fold into project history? asset identity table now or at migration?

## Amendment (author, 2026-09-22): source vs document

"Source" means a responsible entity: the body that publishes and answers for a statement
(JETP Indonesia Secretariat, JET PMU, MOIT, ANER, Senelec, ADB). "Document" means the artefact:
a PDF or an HTML page, with editions over time and byte-exact snapshots.

Current ledger chain, which conflates the two: sources.csv = one row per curated URL (301 rows,
with publisher and authority_category columns; 103 distinct publishers); manifest.csv = one
row per retrieval attempt (314); data/jetp/documents/ = content-addressed bytes (264 distinct
sha256). Twelve tables carry a source_id column that in fact names a URL-level document.

Proposed kinds: Publisher (the source, with authority_category) -> Document (logical publication:
title, type, URL, publisher_id; may have editions) -> Snapshot (bytes: sha256, retrieved_at,
storage_path). A statement in the ledger cites a document snapshot at a locator and is
answered for by the publisher. The backend design's source-editions / edition-snapshots
already separate document from bytes; it still calls the responsible entity a "source".

Amendment 2 (author): a document may have several publishers. Publication is a many-to-many
relation document <-> publisher (joint reports, co-signed declarations, secretariat + ministry
publications), not a publisher_id column on the document. A statement is then answered for
by every publisher of the document unless the document attributes it to one of them.
