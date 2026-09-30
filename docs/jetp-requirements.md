# JETP system: purpose and requirements

Status: draft for review, revised with the author's decisions of 2026-09-30.

This document says what the JETP system is for, who uses what it produces,
and what it must deliver to them. Every other document of the specification
is reviewed against it: for each requirement, a reviewer says met or not
met; for each design rule elsewhere, a reviewer says which requirement it
serves, and a rule that serves none is a candidate for removal or for a
later milestone. It names no storage and no screen layout. How the ledger is
stored is the storage contract's business; how results are shown is the
observatory presentation's.

The specification set:

| Document | Subject |
|---|---|
| Purpose and requirements (this document) | What the system must deliver, and to whom |
| Language (`jetp-language.md`) | The ODEM frame and the builders' vocabulary |
| Ontology (`jetp-ontology.md`) | What the ledger talks about |
| Collection (`jetp-collection.md`) | How documents are found and fetched |
| Extraction (`jetp-extraction.md`) | How statements are read from documents |
| Fusion (`jetp-fusion.md`) | How statements are combined, weighed and revised |
| Storage (`jetp-ledger-storage.md`) | How the ledger is kept |
| Results and releases (`jetp-results.md`) | What is computed, frozen and cited |
| Presentation (`jetp-observatory-presentation.md`) | What readers of the observatory see |
| Operation (`jetp-operation.md`) | Which machine runs what, with which budgets |

## 1. Purpose

Four Just Energy Transition Partnerships (South Africa, Indonesia, Viet Nam,
Senegal) promise money for energy transitions, and report on it in plans,
progress reports, project pages, registers and news, in four languages, each
publisher in its own way. The structured channels (OECD CRS, IATI) arrive one
to three years late and rarely carry a JETP label. The system reads what
these publishers said, keeps each statement with its publisher, date and
page, judges which statements describe the same projects, payments and
events, and computes from them counts and accounts that state their unit,
perimeter, knowledge cutoff and uncertainty. The question it serves is where
the partnerships stand: what was planned, financed, implemented and
disclosed, by whom, and when. Its products are a public observatory and three
papers, all resting on frozen, citable releases; the machinery is meant to
be reused by AEDIST.

## 2. How to read this document

**Principles.** Taken from the author's framing of the specification, and
applied to every requirement below.

- "What we are working towards is a complete system specification. The idea
  is to write it explicit and review the heck out of it before we launch
  extraction."
- "We want something that works first, then M4 will polish." The M2 and M3
  requirements are the minimum that produces correct, traceable results.
  Anything else is tagged M4 or later and is not built before it.
- "Pragmatic programmer, results-oriented over theoretical purity." A
  requirement earns its place by a product that needs it, not by
  completeness of the design.

**Milestones.** Every requirement names the first milestone that must meet
it; once met, it stays met at every later milestone.

| Milestone | What it delivers |
|---|---|
| M2, the instrument | An extraction pipeline that works on every document held: it replays the documents already extracted, re-running changes nothing, and every document ends with statements or a recorded disposition |
| M3a, discover and freeze | Discovery to a cutoff date under a stopping rule stated in advance, then a frozen registry, with a recall estimate and the list of unreachable sources |
| M3b, extract, reconcile, release | The documents new since M2 extracted, reconciliation with CRS and IATI, joins of finance to assets and outcomes, and a released dataset that cites its release identifier |
| M4, operation | Scheduled refresh, link-rot checks, the pass launcher, the move of the document store, shared code for AEDIST |
| later | Not scheduled; stated so that earlier design does not preclude it |

**Identifiers.** Product questions are numbered by product (OBS, DP, SP, LP,
AED, OP). Requirements are functional (F), data (D), quality (Q),
constraints (C) and non-requirements (N). Each requirement ends with its
milestone and a test a reviewer can decide.

## 3. Users, products and their questions

### 3.1 Public observatory readers

Researchers, journalists and practitioners who know that a figure rests on
documents. They ask:

- **OBS-1** Where does each partnership stand: what was pledged, announced,
  approved, signed and disbursed, to which projects, by which funders, as
  of which date?
- **OBS-2** What does this figure rest on: which statements, by which
  publisher, in which document, at which page, read on which date, computed
  how?
- **OBS-3** Which projects, funders and operators are named, and what is on
  the record about each?
- **OBS-4** What does this word, status or measure mean, where does the
  definition come from, and when did it change?
- **OBS-5** What changed since the last edition, and is it a development in
  the world, a late report or a correction?
- **OBS-6** What was sought and not found, not published, or blocked?

### 3.2 JETP data paper

Documents the dataset: collection, identity decisions, provenance,
validation, coverage, uncertainty and maintenance. Its contribution is
consistent observation and transparent limits, not proof of acceleration.

- **DP-1** How were documents found, to which cutoff, with what recall, and
  which sources could not be reached?
- **DP-2** How were identities decided, by whom or what, and with what
  confidence?
- **DP-3** What is the coverage by country, document type, publisher and
  financial state; where is information missing or in conflict?
- **DP-4** Can an independent reader reconstruct one published country total
  and one timeline from the frozen release and its source locators?
- **DP-5** How is the dataset maintained, and how do editions differ?

### 3.3 Short paper: progression, public and private finance, operation histories

Which components of a just transition progress within the partnerships, with
which public and private finance, and from which pre-existing operations? The
unit is the operation and, where needed, its component.

- **SP-1** Progression: which operations, by transition function (energy
  infrastructure, fossil exit, social support), reach which documented
  milestones, with unknowns visible?
- **SP-2** Public and private: who finances the same operations, through
  which instruments, with which owner, beneficiary and operator; which
  amounts are known per contributor and which are mixed and not allocable?
- **SP-3** History: which milestones of the same operations precede and
  follow the partnership, with uncertain dates kept uncertain?
- **SP-4** Denominators: how many unique operations are in the documented
  scope, with known and unknown counts for each dimension, at a stated
  cutoff?

### 3.4 Long paper: comparative political economy

Explains observed country and project trajectories through financial
instruments, domestic institutions, negotiation and ownership arrangements,
with rival explanations and negative cases.

- **LP-1** For a proposed mechanism, what dated statement supports each
  premise, and what evidence would disconfirm it?
- **LP-2** How did official accounts of a country or project change over
  time, and who changed them?
- **LP-3** Which cases are stalled, cancelled or contradictory, so that
  selected successes never stand in for the portfolio?
- **LP-4** Where do disclosure and implementation diverge, with the
  observation process (what was sought, published, blocked) kept apart from
  financial and physical statements?

### 3.5 AEDIST reuse

AEDIST turns fragmented sources into persistent, revisable, auditable
statistical knowledge; JETP is a demanding test of that method.

- **AED-1** Can a new document produce a justified, inspectable change to the
  ledger, with fewer serious errors and less human work than the assisted
  process?
- **AED-2** Which parts of the machinery (acquisition, text layer,
  provenance, adjudication) run unchanged for a second consumer?
- **AED-3** What does an accepted change cost, in model spend and in human
  minutes?

### 3.6 The author as operator

One researcher runs the system and is not its checker.

- **OP-1** What is pending, what failed, and which judgements need me,
  sorted by likelihood and confidence?
- **OP-2** Did every scheduled or launched run finish, and if not, why?

## 4. Functional requirements

What the system must be able to answer or do.

**F1. Every statement names where it was read.** Each statement carries its
document, the snapshot read, its locator in that snapshot, its publisher,
the method and version that read it, and the date read. *M2.* Test: pick
any statement; its snapshot's bytes and its locator are reachable, and the
printed text at the locator supports it.

**F2. Every registered document is accounted for.** Every document ends with
statements or a recorded disposition and its reason (duplicate of a
canonical document, non-canonical translation, no snapshot, no extractable
content). *M2.* Test: the count of documents with neither is zero.

**F3. Duplicates are resolved before reading.** One publication under two
addresses or two exports is one document; succession and translation are
recorded as relations; statements are read from one canonical member.
*M2.* Test: a report fetched twice or mirrored yields one set of statements
and no added corroboration.

**F4. Living documents append, never overwrite.** A new dated snapshot of a
document already read adds statements tied to that snapshot; earlier
statements never change; content restated unchanged is kept under the later
date as persistence, not corroboration. *M2.* Test: a second snapshot of a
living document runs through the pipeline; the earlier statements are
byte-identical afterwards and the restated ones appear under the new date.

**F5. The pending work is computable.** The set of snapshots without
statements or disposition is derivable at any time and is the input of every
run, so that later recurring passes reuse the M2 pipeline. *M2.* Test: after
a new snapshot is registered, the pending set contains exactly it.

**F6. All disagreeing statements stay retrievable.** No statement is deleted
or replaced because another disagrees with it; a result that prefers one
names why, and the others are one step away. *M2* for keeping statements,
*M3b* for results. Test: for a subject with two conflicting values, both are
retrievable, and a released figure using one links to the other with the
stated reason.

**F7. Discovery proposes, a decision admits.** A candidate document found by
any search is admitted only by a recorded decision, never automatically.
*M3a.* Test: a candidate from a discovery run is absent from the registry
until an admission decision exists.

**F8. The observation process is recorded.** For each authority and listed
project in the discovery frame, the system records a terminal verdict
(collected, not published, blocked, not applicable), and keeps not
published, blocked, unreadable, not sought and loss of visibility distinct.
Absence of a document is recorded with the search that failed to find it.
*M3a.* Test: every entry of the frame has a verdict; a blocked retrieval
does not appear as a missing event or a stalled project.

**F9. Each release states two dates.** The discovery cutoff (date of the last
search) and the newest document date. *M3a.* Test: both dates appear in the
release and in every product citing it.

**F10. Results at a knowledge cutoff.** Any result can be computed as the
system knew it at a cutoff K, using only what was admitted on or before K; a
later discovery never changes an earlier result. *M3b.* Test: add a
statement dated after K; the result at K is unchanged.

**F11. Identities by judgement, counted at a declared cutoff.** Projects,
components, assets, agreements, parties and publisher-stated perimeters exist
only by a recorded judgement with likelihood and confidence; each result
declares the match cutoff it applies, and may report figures at a cautious
and an inclusive cutoff. Candidate matches below the cutoff are listed and
counted apart. *M3b.* Test: a match judged "about as likely as not" changes
no figure at a "likely" cutoff and is listed.

**F12. Organisations under authority control.** One identity per
organisation with all its name forms; an external identifier decides where
one exists. *M3b.* Test: "Senelec" and "SENELEC" are one party; "PLN" and
"Perusahaan Listrik Negara" are one party only through a recorded judgement.

**F13. Counts name their unit and population.** Every count names its unit
(statements, identities of a kind, a publisher's stated count) and its
perimeter or counting scope. The strict JETP scope requires explicit
attribution in the source; any extended scope is reported separately and
never fills the strict one. No count is summed across countries. *M3b.*
Test: every count in a release carries a unit and a scope; no strict-scope
figure includes a statement lacking JETP attribution.

**F14. Financial states are selected, not added.** Need, announced,
memorandum, approved, signed and disbursed are a chronology; an aggregate
selects one state explicitly. Physical state is a separate dimension and
never follows from a financial one. *M3b.* Test: no released figure adds
signed and disbursed amounts; no physical state is inferred from a
disbursement.

**F15. Money in the publisher's currency.** Values stay in their unit and
currency; a conversion uses a rate a document printed, cited like any
statement. *M3b.* Test: every converted value cites its rate's statement; a
third party's conversion is excluded from sums in original currency.

**F16. Operation timelines with honest dates.** For an operation, the system
returns its dated milestones before and after the partnership, each with its
date precision or interval, keeping the date an event happened apart from
the date it was published or observed. *M3b.* Test: a milestone known only
by the year of a report is an interval ending at the report date, not a day.

**F17. Funding roles kept apart.** Funder ownership, instrument, beneficiary
and operator are distinct; a mixed package amount not broken down stays
mixed; observed co-financing and mobilisation attributed by a source are
distinct statements. *M3b.* Test: a public bank's commercial loan is not
counted as private; an unallocated mixed amount appears in no per-contributor
total.

**F18. Transition functions.** An operation can be tagged with one or more
transition functions (energy infrastructure, fossil exit, social support);
an operation with several functions is counted once in any total across
functions. *M3b.* Test: an operation tagged with two functions contributes
its amount once to the all-functions total.

**F19. Reconciliation with CRS and IATI.** Ledger operations are matched to
CRS and IATI records as candidate matches under F11; the gaps between
announced, signed, reported and disbursed amounts are produced per country
and funder; a public traceability rate is computed; the reporting lag of the
structured channels is measured, not assumed. Structured channels have no
precedence over the source closest to the event. *M3b.* Test: each
reconciled aggregate links to the events and documents it is made of; no CRS
value overrides a primary statement without a stated judgement.

**F20. Finance joined to assets.** An operation joins a physical asset only by
a stable identifier or a documented judgement, so that a chronology from
financing to realisation can be reconstructed. *M3b.* Test: four cases are
represented correctly: an effective closure, a retirement cancelled or
reassigned, low-carbon infrastructure under construction, a new fossil asset
commissioned during the partnership.

**F21. Excerpts for qualitative work.** For any operation, party or country,
the system returns the statements with their verbatim text, language,
publisher, date and locator, so that a codebook-based coding done outside
the ledger can cite them. Codebooks and codings stay outside the ledger;
the ledger holds only the statements they cite. *M3b.* Test: for one country, a list of excerpts about
negotiation or ownership can be produced, each resolving to its snapshot.

**F22. Change between releases is attributed.** When a later release changes
a figure, the change is attributed to one of: a development in the world, a
late report, a publisher's correction, a changed interpretation, a ledger
error, a changed method. M3b delivers a single release; attribution between
editions begins with the second one. *M4.* Test: for each figure that differs between
two consecutive releases, one attribution is recorded.

**F23. What the observatory serves.** Every table of the ledger is served to
readers or named as not served with the reason; the definitions of terms are
served as a glossary with their sources and revision history. *M3b.* Test:
the list of served and not-served items covers every table.

**F24. Each country has its principal reference.** For each country, the
principal official reference and the latest subsequent official news are
pinned to their snapshots, with publication and selection dates; where no
later official item exists, the gap is stated. *M3b.* Test: each of the four
countries has both, or a stated gap.

## 5. Data requirements

What the system must hold and handle.

**D1. Four countries.** South Africa, Indonesia, Viet Nam and Senegal. *M2.*
Test: every document and statement belongs to one of the four, or to no
recipient country for global method sources.

**D2. The documents held.** 392 registered documents, 369 with a snapshot,
254 already read (13,089 statements from 253 snapshots), 115 with a snapshot
and nothing read yet (South Africa 49, Senegal 28, Viet Nam 25, Indonesia
13), 23 without a snapshot. *M2.* Test: every one of the 392 satisfies F2.

**D3. Document types.** At least: progress updates, project pages, data
portals, official news, annual reports, operator reports, project lists,
implementation plans, investment plans, approval documents, secondary news.
Repeated series get a dedicated reader; one-off documents get an assisted
reading with row-by-row review. *M2.* Test: every type among the 115 has
a reading path, and each document read by a dedicated reader belongs to a
repeated series.

**D4. Formats.** HTML, PDF with a text layer, scanned PDF read by
transcription, spreadsheets, JSON, JavaScript data files, and bytes of
undetermined type. A value that exists only in a chart with no text is not
read (N2). *M2.* Test: every format among the 369 snapshots has a reader, or
its documents carry a disposition that names the format.

**D5. Languages.** English, Indonesian, Vietnamese and French. The language
of every document is recorded; every statement keeps its label in the
language printed; one member of a translation pair is canonical for reading.
*M2.* Test: no document has an unknown language (20 of the 115 have none
today); no statement cites a translation.

**D6. Three document classes.** Fixed (collected once, then checked),
living (re-collected, each version kept as a dated snapshot) and series
(each issue fixed, the series having an expected next issue). *M3a* for
recording the class, *M4* for acting on it. Test: every admitted document has
a class; at M4, a late issue of a series is signalled.

**D7. The discovery frame.** Per country: the national JETP portal or
responsible ministry; the lead partner governments and every public partner
named in the package; the multilateral and private windows named in
official financing tables; the national electricity operator and named
project operators; every project in an official plan, pipeline or progress
list. *M3a.* Test: each class of the frame has at least one entry per
country, or a recorded reason it has none.

**D8. A known-item list.** A list of documents known to exist, compiled
before the discovery rounds, against which recall is estimated. *M3a.* Test:
the list predates the first round and its recovery rate is reported.

**D9. Unreachable sources are data.** The list of sources that could not be
reached, with the reason, is released with the registry. *M3a.* Test: the
release contains it, including sources blocked by terms of use or access
controls.

**D10. Structured channels.** CRS and IATI records for the four countries,
held as comparator records beside the documentary statements, never merged
into them. *M3b.* Test: every CRS or IATI record used in a result is
identified by its channel identifier and retrieval date.

**D11. Expected volume.** After M3a and three years of
refresh, the system handles about ten times the documents held today and a
weekly snapshot of each living document, with no change of design. *Later*
(stated so that M2 does not preclude it). Test: the design documents name no
limit that the current volume already approaches.

**D12. Reference operations outside the partnerships.** Milestones of JETP
operations dated before the partnership, and operations of partner lenders
in the four countries that carry no JETP attribution, are held in a counting
scope of their own: the pre-existing history of JETP operations and a
reference pool. They never enter a strict JETP figure (F13). *M3b.* Test: a
strict-scope figure recomputed without this scope is unchanged.

## 6. Quality requirements

**Q1. Replay.** The pipeline reproduces the statements of the 254 documents
already read, byte for byte, or every difference is explained. *M2.* Test:
the replay report lists zero unexplained differences.

**Q2. Idempotence.** Re-running on a snapshot already read changes nothing and
never renumbers a statement's identifier. *M2.* Test: two consecutive runs
produce identical outputs.

**Q3. Readers are red-tested.** Each extractor is tested by replaying a defect
it must reject. *M2.* Test: every extractor has such a test, and the test
fails when the defect is re-introduced.

**Q4. Language-model readings are recorded as readings.** A language-model
read is not byte-reproducible; its recorded output is the record, with the
model, version, prompt version, inputs and cost. Replay and idempotence bind
the deterministic readers and the writer, not a fresh read. *M2.* Test: every
statement read by a language model names its model and version; re-running
does not replace a recorded reading.

**Q5. The author is not the checker.** Every item read or judged by a
language model (a statement read, a match, a preference, a classification)
is read by one reader and checked by a second reader from another vendor,
blind to the first, with its likelihood and confidence recorded. The author
sees only the items where the two disagree and a random sample of those
where they agree, sorted by likelihood and confidence. The full panel of
independent readers with positive controls (Fusion § 3) is M4. *M2* for
statements read, *M3a* for discovery and admission judgements, *M3b* for
identity and preference judgements. Test: every language-model item in a
release carries two readings from two vendors; the author's queue holds only
disagreements and the sample, in that order.

**Q6. Released figures trace both ways.** Every published number, status and
substantive narrative claim resolves to the statements and the named
calculation it rests on, down to the snapshot bytes that supported it; from
any statement, the published figures that use it are reachable. The latest
snapshot of a document never stands in for the one that supported an older
statement. *M3b.* Test: sample figures from the observatory and from each
paper; each resolves to snapshots and locators, and each sampled statement
lists the figures that use it.

**Q7. Corrections propagate.** A correction reaches every published claim it
touches, and those claims are identifiable before the next release. *M3b.*
Test: revoke one match; the list of affected figures is produced.

**Q8. Releases are frozen and reproducible.** A release has an identifier;
from it, a paper result and an observatory figure reproduce exactly. A
corrected current account never silently refreshes a released result. *M3b.*
Test: an independent reader reconstructs one country total and one timeline
from the release, its dictionary and its locators; any undocumented choice is
a failure.

**Q9. Every method has a version.** Every reading, judgement, scope and
calculation names its method and version; changing one produces a new result
under a new version. *M2* for reading methods, *M3b* for judgements and
calculations. Test: every result names the versions it was computed under.

**Q10. Recall is stated.** Discovery follows a stopping rule stated before
the first round; every round is logged, empty rounds included; the recall
estimate against the known-item list is reported; the share of the main
secondary trackers' quantitative claims traced to a primary source is
reported. *M3a.* Test: the author accepts the protocol, the recall estimate
and the unreachable list before M3b starts.

**Q11. Uncertainty is never hidden.** A value may be a range and a date an
interval; judgements use the calibrated likelihood and confidence scales;
unknown is not zero; an unresolved disagreement is carried into the result
with the condition that blocks comparison; no preferred figure is
manufactured to fill a gap. *M2* for keeping ranges and date precision in
statements, *M3b* for results. Test: a released figure over a subject with
unresolved disagreement shows both values; no missing value is summed as
zero.

**Q12. Computed and published numbers are told apart.** A number the system
computed and a number a publisher printed are always distinguishable, each
with its own attribution. *M3b.* Test: every number in the observatory and
the papers is marked as one or the other.

**Q13. Observation is kept apart from inference.** No product presents an
association as a cause, a stage difference as speed, or a documentary gap as
an actual absence of finance. *M3b.* Test: the integration review finds no
causal or speed claim in the observatory and none unsupported in the papers.

**Q14. No silent run.** Every run, launched or scheduled, ends with a report
that says what it did, what it found, what failed and what it deferred; a
run that finds nothing says so. *M3a* for discovery rounds, *M4* for
scheduled passes. Test: kill a run midway; the failure is reported, and no
report reads as an all-clear.

**Q15. Cost and effort are measured.** Each run records its model spend and the human minutes spent on
its review, so that the cost of an accepted change can be computed. *M3b.*
Test: the M3b release states spend and review time per document class.

## 7. Constraints

**C1. One researcher's attention.** The author is the only person; the
author's time is the scarcest resource. Decisions are batched; weekends are
off. Before M4, the author's review of machine readings is bounded by Q5:
disagreements between the two readers and a random sample of agreements,
nothing else. *M2.* Test: no design rule requires the author to review every
item of a class; each queue for the author states its expected size and is
sorted by likelihood and confidence.

**C2. Two machines, one direction.** padme, a personal workstation with GPUs
and the document bytes, runs every job that reads bytes or models; doudou, a
laptop, supervises, verifies and defers a run when padme is unreachable, and
says so. Data flows from padme to doudou only. *M2* for jobs, *M4* for
supervision of scheduled runs. Test: no design rule moves data from doudou
to padme or requires the laptop to hold all document bytes.

**C3. Local compute first.** padme serves a local language model on two
consumer GPUs (16 GB and 12 GB). Bulk reading fits that model or a paid
interface within budget (C4); cross-vendor judgement panels use paid
interfaces. *M2.* Test: each reading method names where it runs.

**C4. Budgets.** Paid interfaces (language-model readers, search, bibliographic
APIs) run under a budget stated before the run, per document and per run; a
run that reaches its budget stops and reports. *M2.* Test: every paid call
belongs to a run with a stated budget. The amounts are set in Operation.

**C5. Open access.** The released dataset and the papers are open access, the
papers in diamond open access without article processing charges; each
release carries its reuse terms and its citation. *M3b.* Test: the release
states reuse terms, citation and deposit identifier.

**C6. Terms of use of sources.** Automated link-following obeys each
site's robots rules. A single fetch of a known document that the author
could open in a browser goes ahead, and the site's stated position (robots
rules, terms of use) is recorded with the retrieval. A change of a site's
terms or robots rules is signalled, never silent. Access checks and logins
are passed by the author in person, never by automation. Document bytes are
redistributed only where the source's terms allow; otherwise a release
carries the address, hash and locator. *M3a.* Test: no automated crawl
fetches a path the site's robots rules exclude; every single fetch records
the site's stated position; the release lists which bytes are redistributed
and on what terms.

**C7. Static publication.** The observatory is published as static pages and
frozen data, with no server application required to read it. *M3b.* Test: the
observatory of a release opens from its files alone.

**C8. Works first.** A mechanism not needed by an M2 or M3 requirement is not
built before M4; code is shared with another project only when a second
consumer runs on it. *M2.* Test: every design rule tagged M2 or M3 cites a
requirement of that milestone.

**C9. Secrets.** Credentials are read at use and never written to logs,
reports or releases. *M2.* Test: no run report or release contains a
credential.

## 8. Non-requirements

Out of scope, so that no design rule is written to serve them.

**N1. No causal model.** The system estimates no effect of the partnerships
and holds no causal explanation. A causal study, if one is commissioned,
consumes a frozen release from outside the system.

**N2. Classes out of scope by decision.** Institutional events and
party-to-party relations beyond roles; natural persons as signatories or
delegates; values that exist only in a chart; a document as the subject of a
statement; recurrence; a publisher's own liabilities and budget; physical
outcomes beyond capacity, length and state (emissions, jobs, people,
generation). Each enters only by a decision that adds it as a measure.

**N3. Not a lender's books.** The ledger reconstructs from public documents;
it does not require debit and credit counterparts that no document
discloses.

**N4. No automatic truth.** No program admits a document, merges two
identities, prefers a value or publishes a release on its own.

**N5. No claim of completeness.** Coverage is quantified; universal
completeness is never claimed.

**N6. No real-time monitoring and no unattended publication.** Refresh is
weekly at most (a working assumption the author may change), from M4;
publication is always a reviewed act.

**N7. No countries beyond the four** before M4. *Later:* adding a
country requires a discovery frame and data, not a change of design.

**N8. No translations or summaries as requirements.** Machine translations of
labels and summaries of documents may be added for readers; nothing depends
on them. *Later.*

**N9. No move of the document store before M4.** The move to a dedicated
reference library is M4; earlier milestones only keep acquisition behind one
seam so that the move rewrites nothing else.

**N10. No welfare or justice measurement.** A budget allocation to a social
objective is recorded as such; it does not measure an improvement in
welfare.

**N11. No writing or submitting of papers.** The system supplies evidence and
reproducible results; manuscripts and journal submission are outside it.

## 9. Requirements and the documents expected to meet them

A requirement may be met by more than one document; the first named carries
it. "Extraction § observations" is the M3b section of the extraction
document that reads statements into observations.

| Requirement | Milestone | Expected to be met by |
|---|---|---|
| F1 Statement names where it was read | M2 | Extraction; Storage |
| F2 Every document accounted for | M2 | Extraction |
| F3 Duplicates resolved before reading | M2 | Fusion § 3; Extraction |
| F4 Living documents append | M2 | Extraction; Fusion § 2 |
| F5 Pending work computable | M2 | Extraction; Operation |
| F6 Disagreeing statements retrievable | M2, M3b | Fusion § 5; Extraction |
| F7 Discovery proposes, a decision admits | M3a | Collection |
| F8 Observation process recorded | M3a | Collection; Ontology |
| F9 Two dates per release | M3a | Results and releases; Collection |
| F10 Results at a knowledge cutoff | M3b | Fusion § 8; Results and releases |
| F11 Identities by judgement, counted at a cutoff | M3b | Fusion § 3 |
| F12 Organisations under authority control | M3b | Fusion § 3; Ontology |
| F13 Counts name unit and population | M3b | Fusion § 6–7; Results and releases |
| F14 Financial states selected, not added | M3b | Extraction § observations; Fusion § 7; Ontology § 4 |
| F15 Money in publisher's currency | M3b | Extraction § observations; Fusion § 7 |
| F16 Operation timelines with honest dates | M3b | Extraction § observations; Ontology; Fusion § 4 |
| F17 Funding roles kept apart | M3b | Extraction § observations; Ontology; Fusion § 7 |
| F18 Transition functions | M3b | Extraction § observations; Ontology |
| F19 Reconciliation with CRS and IATI | M3b | Fusion § 5; Results and releases |
| F20 Finance joined to assets | M3b | Fusion § 3; Ontology |
| F21 Excerpts for qualitative work | M3b | Results and releases |
| F22 Change between releases attributed | M4 | Fusion § 8; Results and releases |
| F23 What the observatory serves | M3b | Storage § 2; Presentation |
| F24 Principal reference per country | M3b | Presentation |
| D1 Four countries | M2 | Ontology; Collection |
| D2 Documents held | M2 | Extraction |
| D3 Document types | M2 | Extraction |
| D4 Formats | M2 | Extraction |
| D5 Languages | M2 | Extraction; Storage § 5 |
| D6 Three document classes | M3a, M4 | Collection; Operation |
| D7 Discovery frame | M3a | Collection |
| D8 Known-item list | M3a | Collection |
| D9 Unreachable sources are data | M3a | Collection; Results and releases |
| D10 Structured channels | M3b | Collection; Ontology |
| D11 Expected volume | later | Storage; Operation |
| D12 Reference operations outside the partnerships | M3b | Collection; Fusion § 6 |
| Q1 Replay | M2 | Extraction |
| Q2 Idempotence | M2 | Extraction; Storage |
| Q3 Readers red-tested | M2 | Extraction |
| Q4 Language-model readings recorded | M2 | Extraction |
| Q5 The author is not the checker | M2, M3a, M3b | Extraction; Collection; Fusion § 3 |
| Q6 Released figures trace both ways | M3b | Results and releases; Presentation |
| Q7 Corrections propagate | M3b | Results and releases |
| Q8 Releases frozen and reproducible | M3b | Results and releases |
| Q9 Every method has a version | M2, M3b | Extraction; Extraction § observations; Fusion § 1 |
| Q10 Recall stated | M3a | Collection |
| Q11 Uncertainty never hidden | M2, M3b | Extraction § observations; Fusion § 1; Results and releases |
| Q12 Computed and published numbers apart | M3b | Presentation; Results and releases |
| Q13 Observation apart from inference | M3b | Language; Presentation |
| Q14 No silent run | M3a, M4 | Operation; Collection |
| Q15 Cost and effort measured | M3b | Operation |
| C1 One researcher's attention | M2 | Operation |
| C2 Two machines, one direction | M2, M4 | Operation |
| C3 Local compute first | M2 | Operation; Extraction |
| C4 Budgets, amounts set in Operation | M2 | Operation |
| C5 Open access | M3b | Results and releases |
| C6 Terms of use of sources | M3a | Collection; Results and releases |
| C7 Static publication | M3b | Presentation; Storage § 3 |
| C8 Works first | M2 | every document |
| C9 Secrets | M2 | Operation |
| N1–N11 Non-requirements | — | every document: no rule may serve only these |
