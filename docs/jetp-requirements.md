# JETP Observer: purpose and requirements

Status: draft for review, revised with the author's decisions of 2026-09-30.

This document says what the JETP Observer is for, who uses what it
produces, and what it must deliver to them. The Observer is the whole
system: collection, extraction, reading, judgement, releases. The ledger is
its Data (the tables of steps D1 to D4); the Observatory is its public
website, one of its outputs. Every other document of the specification
is reviewed against it: for each requirement, a reviewer says met or not
met; for each design rule elsewhere, a reviewer says which requirement it
serves, and a rule that serves none is a candidate for removal or for a
later milestone. It names no storage and no screen layout. How the ledger is
stored is the storage contract's business; how results are shown on the
Observatory is the presentation's.

The specification set:

| Document | Subject |
|---|---|
| Purpose and requirements (this document) | Why the Observer exists, what it must deliver, and to whom |
| Language (`jetp-language.md`) | The ODEM frame and the builders' vocabulary |
| Ontology (`jetp-ontology.md`) | What the ledger talks about |
| Collection (`jetp-collection.md`) | How documents are found and fetched |
| Extraction (`jetp-extraction.md`) | How statements are extracted from documents |
| Fusion (`jetp-fusion.md`) | How statements are combined, weighed and revised |
| Storage (`jetp-ledger-storage.md`) | How the ledger is kept |
| Results and releases (`jetp-results.md`) | What is computed, frozen and cited |
| Presentation (`jetp-observatory-presentation.md`) | What readers of the Observatory see |
| Operation (`jetp-operation.md`) | Which machine runs what, with which budgets |

## 1. Purpose: a theory of change

**Impact.** Climate finance promised to developing countries is delivered,
or visibly not delivered, because people who can act on the difference
know it: a better society and planet is the motive, and this is the part
of it the Observer can serve.

**The problem it answers.** A Just Energy Transition Partnership is a
promise of money announced at a summit and then reported, if at all, in
plans, progress reports, project pages, registers and news, in four
languages, each publisher in its own way. The structured search channels (OECD
CRS, IATI) arrive one to three years late and rarely carry a JETP label.
Anyone who asks what was promised, signed and paid, to whom and when, must
rebuild the record alone, and the record rebuilt by one party is doubted
by the others.

**Outcomes: who does what differently because the Observer exists.** In
the author's order of priority.

- *Think tanks and journalists* quote a dated statement attributed to its
  publisher, instead of a figure from a press release; they put a precise
  question to a partner, such as why an amount stayed announced for two
  years, with the page to point to; and they establish the state of a
  partnership in hours rather than weeks.
- *Researchers* start from a frozen, citable release instead of collecting
  documents again, reproduce each other's figures, and test explanations
  against a record that keeps stalled and cancelled cases beside the
  successes.
- *Negotiators* of the next packages and of the new climate finance goal,
  on both sides, see what earlier packages delivered, stage by stage, from
  a record that neither side wrote.
- *Publishers* see their own statements as others read them, and correct
  errors through a channel that leaves a trace.

**Outputs.**

- The immediate goal: a maintained dataset on the partnerships, released as
  frozen, citable releases for a declared horizon (C10).
- The Observatory, the public website that shows each release.
- Research articles on JETPs (a data paper, a short paper on progression,
  finance and operation histories, a long political-economy paper), on
  international climate finance, and on artificial intelligence for energy
  statistics, within AEDIST (also referred to as AIRLET).
- A book for a general readership on the USD 300 billion climate finance
  promise, in which the partnerships are a few chapters.
- Checked statements, with the machine readings and the human decisions kept
  side by side, which serve as reference answers for research on machine
  reading within AEDIST (Q17).

**Activities.**

- Find and fetch the documents: Collection.
- Extract statements from them, and read them into observations: Extraction.
- Define what the ledger talks about: Ontology and Language.
- Combine, weigh and revise statements into referents and accounts: Fusion.
- Keep the ledger: Storage.
- Compute, freeze and cite results: Results and releases.
- Show them to readers: Presentation.
- Run all this on two machines within budgets, and maintain it through the
  repository by development agents under the author's direction: Operation.

**Assumptions and risks.**

- *Transparency does not by itself produce accountability.* A public record
  changes behaviour only when actors with standing and leverage use it
  (Fox, J. 2007, "The uncertain relationship between transparency and
  accountability", *Development in Practice* 17(4-5): 663-671). The Observer
  can make the record available and usable; the impact depends on users it
  does not control. It therefore watches for signs of use it can see, such
  as reported errors and citations of releases (F25), and does not claim
  impact it cannot observe.
- *Publishers keep publishing.* If disclosure shrinks, moves behind logins
  or disappears, that loss of visibility is itself a finding (F8), not a
  gap to fill by inference.
- *A neutral record is trusted by all sides.* This holds only if the
  Observer never takes a position of its own (design rule below).
- *Machine reading is accurate enough at a bearable cost.* Diverse readers
  calibrated on held-out reference answers, with escalation of what they
  leave open (Q5), test this continuously, and the costs are logged (Q15,
  Q17).
- *One researcher can sustain it to the horizon.* The horizon is declared
  and ends with an archived release (C10); no machine judgement is routed
  to the author (C1).
- *The partnerships continue.* A partner withdrawing or a partnership
  lapsing is a development the record documents, not a reason to stop
  documenting.

**Design rule: a neutral documentary record.** The Observer records who
stated what, where and when, and computes figures whose method is declared.
It does not grade partners, judge whether a promise was kept, or recommend
policy. Its impact comes from use by others. The papers and the book are
the author's own arguments; they cite the Observer, and the Observer does
not argue back (Q16).

## 2. Conventions and principles

### 2.1 Requirements, identifiers and tests

A requirement states what the Observer must deliver, not how. Each carries a
short identifier, the milestone that must first meet it, and a test phrased
so that a reviewer can decide, from the specification or from the running
Observer, whether it is met. User questions are numbered by user (OBS, OP,
DP, SP, LP, BK, AED). Requirements are functional (F), data (DA), quality (Q)
and constraints (C); non-requirements (N) state what is out of scope.
Identifiers are stable: regrouping never renumbers them, and a withdrawn
identifier is not reused. The data requirements were prefixed D until
2026-09-30 and are now DA, so that D1 to D4 name only the steps of Data.

### 2.2 Milestones and incremental delivery

Delivery is incremental. Each milestone delivers a slice of the Observer
that works end to end and whose results are correct and traceable; it does
not deliver a partial version of every component. Refinement, automation
and operational convenience are deferred to operation (M4) unless a
requirement of an earlier milestone needs them. A requirement names the
first milestone that must meet it; once met, it stays met at every later
milestone. Where a requirement binds in part earlier and in full later, it
names both milestones.

| Milestone | What it delivers |
|---|---|
| M2, the instrument | An extraction pipeline that works on every document held: it replays the documents already extracted, re-running changes nothing, and every document ends with statements or a recorded disposition |
| M3a, discover and freeze | Discovery to a cutoff date under a stopping rule stated in advance, then a frozen register, with a recall estimate and the list of unreachable documents |
| M3b, extract, match, release | The documents new since M2 extracted, matching to CRS and IATI, joins of finance to assets and outcomes, and a released dataset that cites its release identifier |
| M4, operation | Scheduled refresh, link-rot checks, the pass launcher, the move of the document store, code shared with AEDIST |
| later | Not scheduled; stated so that earlier design does not preclude it |

### 2.3 Fitness for purpose over completeness

A requirement is admitted because an outcome of section 1 or a user question
of section 3 needs it, and not because a complete design would include it.
Among designs that meet a requirement at its milestone, the simplest is
preferred; generality with no present consumer is deferred until a second
consumer exists. Measured results take precedence over theoretical
elegance: a mechanism is judged by whether its outputs pass the tests below.

### 2.4 Relation to the other specification documents

The specification is complete and reviewed before extraction code is
written. Section 9 names, for each requirement, the documents expected to
meet it. The review applies two checks in both directions: a requirement
that no document meets is a gap in the specification; a rule in another
document that serves no requirement is removed or moved to a later
milestone. Where a requirement and another document disagree, the
disagreement is resolved in one of them, never left standing.

### 2.5 Documents in scope

A document is in scope, and is admitted to the register, when it states
something about a Just Energy Transition Partnership's projects, money,
perimeters, parties or states, or when it belongs to the reference pool of
DA12 (milestones of JETP operations dated before the partnership, and
operations of partner lenders in the four countries that carry no JETP
attribution). A document of the reference pool is counted in its own
counting scope and never in a strict JETP figure (F13). A document kept for
context only is registered and given the disposition `out_of_scope`
(Collection § 9, Extraction § 7). N2, N12 and N13 still exclude what they
name. *M3a* for triage; *M2* for the documents held.

## 3. Users and their questions

### 3.1 Observatory readers

Think tanks and journalists first, then researchers, then negotiators: readers
who know that a figure rests on documents. They ask:

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
- **OBS-5** What changed since the last release, and is it a development in
  the world, a late report or a correction?
- **OBS-6** What was sought and not found, not published, or blocked?
- **OBS-7** How do I tell the Observer that a statement is misread, and what
  became of my report?

### 3.2 The author and the development agents

The Observer is built and run through its repository by agentic
development. Coding agents write the code and run the passes; tickets record
decisions and their reasons; tests and reviews by LLMs from other vendors
gate every change; the author steers, arbitrates and accepts each milestone.
The Observatory serves the author and the agents as well as the public: it
is the instrument through which the author inspects the ledger and notices
anomalies. Every output of section 1 depends on the back end remaining
correct and modifiable, over the whole horizon, by agents that did not write
it and by a researcher who cannot read every line. Maintainability is
therefore a first-class requirement, not an operational afterthought
(Q18 to Q21, C1, C2).

- **OP-1** What is pending, what failed, and which judgements are least
  certain, in order of likelihood and confidence?
- **OP-2** Did every launched or scheduled run finish, and if not, why?
- **OP-3** Does something look wrong (a total that jumped, a country with no
  new documents, a figure whose trail does not resolve), and where does it
  come from?
- **OP-4** Why is this rule or this value what it is: which decision, by
  whom, on what grounds, against which alternatives?
- **OP-5** Can an agent that has never seen this part of the Observer change
  it safely: is the rule written, is the test meaningful, is the change
  reviewable?
- **OP-6** Can any release, or any intermediate result, be rebuilt from the
  repository and the archived documents?

### 3.3 JETP data paper

Documents the dataset: collection, identity decisions, provenance,
validation, coverage, uncertainty and maintenance. Its contribution is
consistent documentation and transparent limits, not proof of acceleration.

- **DP-1** How were documents found, to which cutoff, with what recall, and
  which documents could not be reached?
- **DP-2** How were identities decided, by whom or what, and with what
  confidence?
- **DP-3** What is the coverage by country, document type, publisher and
  financial state; where is information missing or in conflict?
- **DP-4** Can an independent reader reconstruct one published country total
  and one timeline from the frozen release and its locators?
- **DP-5** How is the dataset maintained, and how do releases differ?

### 3.4 Short paper: progression, public and private finance, operation histories

Which transition functions (F18) progress within the partnerships, with
which public and private finance, and from which pre-existing operations? The
unit is the operation, as the [language](jetp-language.md) document defines
it, and, where needed, its component.

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

### 3.5 Long paper: comparative political economy

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
  record of the search (what was sought, published, blocked) kept apart from
  financial and physical statements?

### 3.6 Book on the USD 300 billion promise, and the climate-finance article

A book for a general readership on the climate finance promise, written over
several years, and an article on international climate finance; both use
the partnerships as a case study.

- **BK-1** Which dated statements can be cited, each traceable to its
  publisher, document and page?
- **BK-2** Do the figures quoted reproduce from one frozen release for the
  whole writing period, whatever later releases say?
- **BK-3** What does each term mean, in plain language a general reader
  follows?

### 3.7 AEDIST: artificial intelligence for energy statistics

AEDIST (AI-driven Energy Data Integration for Sustainable Transition)
evaluates artificial-intelligence methods for producing energy statistics
where statistical offices cannot. Its benchmark case is the inventory of
Viet Nam's thermal power plants, against which it compares many LLMs in single-shot, multi-turn, retrieval-augmented and web-augmented
configurations, measuring recall, precision, cost and latency. A method,
there, is the whole chain of acquisition, extraction, reconciliation and
verification; the model is one parameter. Its standard is that
research-quality data is not correct data but data whose errors are
locatable. Its motivating application is an Energy Transition Monitoring
system, whose evidence storage layer keeps source documents identifiable,
versioned and locatable, so that an earlier answer can be traced to the
evidence it used after a source is revised or read again. In this section,
acquisition, reconciliation, model, evidence and stage are AEDIST's own
terms.

The Observer is a second domain for that method: financial rather than
physical, in four languages, with documents that change. AEDIST needs from
it checked statements that serve as reference answers, with every machine
reading and human decision kept (Q17); the cost of each method (Q15);
errors located at the stage that made them (Q17); evidence that stays
locatable across revisions (F1, F4, F10); and, from M4, the shared code
(C8).

- **AED-1** Can a new document produce a justified, inspectable change to the
  record, with fewer serious errors and less human work than the assisted
  process?
- **AED-2** Against the human decisions, how often was each machine reading
  right, and at which step did the wrong ones fail?
- **AED-3** What does an accepted change cost, in LLM spend and in human
  minutes, per method?
- **AED-4** When a document is revised or read again, can the justification
  behind an earlier result be found in the right version, and a change in the
  document be told from a change in processing?
- **AED-5** Which parts of the machinery (collection, text layer,
  provenance, decisions) run unchanged for a second consumer?

## 4. Functional requirements

### Reproducible research

The Observer's outputs are research outputs, and it follows the principles
of reproducible research throughout. Every result is traceable to the
inputs it was computed from. Every released result is reproducible from a
frozen release and the recorded methods. Nothing is overwritten: statements,
judgements and releases are appended and versioned. Every method that
selects, weighs or transforms is declared with a version. Uncertainty is
reported, not resolved away. The functional requirements below and the
quality requirements of section 6 make these principles testable.

**FAIR assessment.** The FAIR principles (findable, accessible,
interoperable, reusable; Wilkinson et al. 2016, "The FAIR Guiding Principles
for scientific data management and stewardship", *Scientific Data* 3:
160018) apply fully to the released datasets, which are the Observer's
citable data output (F28 to F32). They apply to the archived documents only
in part: metadata, addresses and hashes are always findable and accessible,
but bytes are redistributed only where the source's terms allow (C6). They
apply to the Observatory through the releases it shows, not as a separate
object. The working ledger between releases is not an output, and FAIR does
not bind it. The papers and the book follow their publishers' open-access
terms (C5).

### 4.1 Discovery and holdings

Know what exists, what was fetched, by which route, and what became of it.

**F7. Discovery proposes, a decision admits.** A candidate document found by
any search is admitted only by a recorded decision, never automatically.
*M3a.* Test: a candidate from a discovery run is absent from the register
until an admission decision, which may be a checked LLM judgement under Q5,
exists.

**F8. What was sought is recorded.** For each authority and listed
project in the discovery frame, the Observer records a terminal verdict
(collected, not published, blocked, not applicable), and keeps not
published, blocked, unreadable, not sought and loss of visibility distinct:
not published and blocked are verdicts of the frame; unreadable is an
extraction disposition of a held document; not sought cannot occur for an
entry of the frame, which the stopping rule requires to be searched, and is
stated for what lies outside the frame; loss of visibility, a publisher that
stops publishing, is measured between campaigns from M4. Absence of a
document is recorded with the search that failed to find it.
*M3a.* Test: every entry of the frame has a verdict; a blocked retrieval
does not appear as a missing event or a stalled project.

**F27. Public documents only.** The Observer is an open-source intelligence
instrument: it collects only material that the public can legitimately
reach, and must be able to prove that its dataset comes from such documents
and from no other. A document is public when anyone can reach it without
payment or selection: an open page, a public archive record, or a site
behind a login that anyone can obtain by free public registration (a
procurement portal, for example). Content the public cannot reach is
excluded: paid subscriptions, invitation-only or institution-only access,
leaked or private material (N13). Every document records its public access
route: the address at which it can be reached, or the public archive record
that preserves it, and, for a registration site, the free registration used,
never its credentials. A check fails when any document lacks a route. A
retrieval may use the author's own browser session or registered account to
reach a public site. *M2* for the documents held, *M3a* for discovery.
Test: the check runs over the whole register and reports zero documents
without a public access route; a document added without one makes it fail;
no access route contains a credential.

**F3. Duplicates are resolved before extraction.** One publication under two
addresses or two exports is one document; succession and translation are
recorded as relations; statements are extracted from one canonical member.
*M2.* Test: a report fetched twice or mirrored yields one set of statements
and no added corroboration.

**F2. Every registered document is accounted for.** Every document ends with
statements or a recorded disposition and its reason (duplicate of a
canonical document, non-canonical translation, no snapshot, no extractable
content). *M2.* Test: the count of documents with neither is zero.

**F5. The pending work is computable.** The pending list, as the extraction
document defines it (a snapshot with no statements and no disposition of its
own, whose document has no document-level disposition), is derivable at any
time and is the input of every run, so that later recurring passes reuse the M2 pipeline. *M2.* Test: after
a new snapshot is registered, the pending set contains exactly it.

### 4.2 Statements and traceability

Keep every statement with the place it was extracted from, and never
overwrite one. Here, as in the extraction document, a statement is a line
(step D2); an observation (D3) is read from it.

**F1. Every statement names where it was extracted.** Each statement carries
its document, the snapshot extracted, its locator in that snapshot, its
publisher, the method and version that extracted it, and the date extracted. *M2.* Test: pick
any statement; its snapshot's bytes and its locator are reachable, and the
printed text at the locator supports it.

**F4. Living documents append, never overwrite.** A new dated snapshot of a
document already extracted adds statements tied to that snapshot; earlier
statements never change; content restated unchanged is kept under the later
date as persistence, not corroboration. *M2.* Test: a second snapshot of a
living document runs through the pipeline; the earlier statements are
byte-identical afterwards and the restated ones appear under the new date.
Since no held document has yet changed between snapshots, the test runs on
a fixture (a held snapshot with one value changed) and on a held page whose
bytes change on every request without a change of text.

**F6. All disagreeing statements stay retrievable.** No statement is deleted
or replaced because another disagrees with it; a result that prefers one
names why, and the others are one step away. *M2* for keeping statements,
*M3b* for results. Test: for a subject with two conflicting values, both are
retrievable, and a released figure using one links to the other with the
stated reason.

**F21. Excerpts for qualitative work.** For any operation, party or country,
the Observer returns the statements with their verbatim text, language,
publisher, date and locator, so that a codebook-based coding done outside
the ledger can cite them. Codebooks and codings stay outside the ledger;
the ledger holds only the statements they cite. *M3b.* Test: for one
country, a list of excerpts about negotiation or ownership can be produced,
each resolving to its snapshot.

**F25. Reported errors are traced.** A publisher or a reader can report an
error. Each report is recorded as one ticket, whose number identifies it,
and answered by a judgement: accepted, with the correction made as a
revision that names the report; rejected, with the reason; or reported,
awaiting a public source, when only a publisher's revision not yet public
would settle it. No personal data of a reporter enters the ledger. An
accepted correction reaches every published claim it touches
(Q7). An accepted report that changes a released figure produces a
correction release; otherwise it enters the next regular release (Results
and releases § 9). The number of reports received and corrections made is
published with each release, as a signal of use and of quality gained.
*M3b* for receiving and tracing reports, *M4* for publishing the counts.
Test: a report submitted against a released statement ends with a recorded
judgement, and, if accepted, the correction release or the next release
shows the correction and names the report.

### 4.3 Identities and judgements

Decide which statements describe the same thing, and say how sure.

**F11. Referents by decision, counted at a declared match threshold.**
Projects, components, assets, agreements, parties and publisher-stated
perimeters exist only by a recorded judgement with likelihood and confidence;
each result declares the match threshold it applies, and may report figures
at a cautious and an inclusive threshold. Candidate matches below the
threshold are listed and counted apart. *M3b.* Test: a match judged "about
as likely as not" changes no figure at a "likely" threshold and is listed.

**F12. Organisations under authority control.** One identity per
organisation with all its name forms; an external identifier decides where
one exists. *M3b.* Test: "Senelec" and "SENELEC" are one party; "PLN" and
"Perusahaan Listrik Negara" are one party only through a recorded judgement.

**F20. Finance joined to assets.** An operation joins a physical asset only by
a stable identifier or a documented judgement, so that a chronology from
financing to realisation can be reconstructed. *M3b.* Test: four cases are
represented correctly: an effective closure, a retirement cancelled or
reassigned, low-carbon infrastructure under construction, a new fossil asset
commissioned during the partnership.

### 4.4 Observations, accounts and results

Compute figures that state their unit, population, cutoff and basis.

**F10. Results at a knowledge cutoff.** Any result can be computed as the
Observer knew it at a cutoff K, using only what was admitted on or before K;
a later discovery, meaning a new record, never changes an earlier result. A
correction release keeps K and applies only the named correction overlay of
Fusion § 8. *M3b.* Test: add a
statement dated after K; the result at K is unchanged.

**F13. Counts name their unit and population.** Every count names its unit
(statements, referents of a kind, a publisher's stated count) and its
perimeter or counting scope. The strict JETP scope requires explicit
attribution in the document; any extended scope is reported separately and
never fills the strict one. No count is summed across countries. *M3b.*
Test: every count in a release carries a unit and a scope; no strict-scope
figure includes a statement lacking JETP attribution.

**F14. Financial states are selected, not added.** A need (a plan's estimate
or an envelope), the agreement states of the ontology's money axis
(announced, memorandum of understanding, approved, signed) and its flows
(commitment, disbursement, expenditure) are a chronology, one closed list
stated in Fusion § 7; an aggregate selects one state explicitly. Physical state is a separate dimension and
never follows from a financial one. *M3b.* Test: no released figure adds
signed and disbursed amounts; no physical state is inferred from a
disbursement.

**F15. Money in the publisher's currency.** Values stay in their unit and
currency; a conversion uses a rate a document printed, cited like any
statement. *M3b.* Test: every converted value cites its rate's statement; a
third party's conversion is excluded from sums in original currency.

**F16. Operation timelines with honest dates.** For an operation, the
Observer returns its dated milestones before and after the partnership, each
with its date precision or interval, keeping the date an event happened
apart from the date it was published or observed. *M3b.* Test: a milestone
known only by the year of a report is an interval ending at the report date,
not a day.

**F17. Funding roles kept apart.** Funder ownership, instrument, beneficiary
and operator are distinct; a mixed package amount not broken down stays
mixed; observed co-financing and mobilisation attributed by a publisher are
distinct statements. *M3b.* Test: a public bank's commercial loan is not
counted as private; an unallocated mixed amount appears in no
per-contributor total.

**F18. Transition functions.** An operation can be tagged with one or more
transition functions (energy infrastructure, fossil exit, social support);
an operation with several functions is counted once in any total across
functions. *M3b.* Test: an operation tagged with two functions contributes
its amount once to the all-functions total.

**F19. Matching to CRS and IATI, and the gaps between financial states.** Operations are matched to CRS and
IATI records as candidate matches under F11; the gaps between announced,
signed, reported and disbursed amounts are produced per country and funder,
where *reported* is the amount a comparator record (CRS or IATI) reports;
a public matching coverage rate (Fusion § 5) is computed; the reporting lag of the structured
channels is measured, not assumed. Structured search channels have no precedence
over the document closest to the event. *M3b.* Test: each matched aggregate
links to the events and documents it is made of; no CRS value overrides a
primary statement without a stated judgement.

**F22. Change between releases is attributed.** When a later release changes
a figure, the change is attributed to one of: a development in the world, a
late report, a publisher's correction, a changed interpretation, an error of
the Observer, a changed method. M3b delivers a single release; attribution
between releases begins with the second one. *M4.* Test: for each figure
that differs between two consecutive releases, one attribution is recorded.

### 4.5 Releases and reuse

Freeze results into citable releases that others can find, open, combine and
reuse.

**F9. Each release states two dates.** The discovery cutoff (date of the last
search) and the newest document date. *M3a.* Test: both dates appear in the
M3a collection report; from M3b, in the release and in every product citing
it.

**F28. Persistent identifier.** Each release is deposited in a public data
repository under a persistent identifier that resolves to it, and whose
metadata remains resolvable even if the data must be withdrawn. *M3b.* Test:
the identifier of the M3b release resolves to its deposit.

**F29. Rich metadata.** Each release is described by a metadata record in a
standard, harvestable schema, giving at least its title, creator, version,
countries, discovery cutoff, newest document date, method versions, licence,
and the papers that cite it. *M3b.* Test: the deposit's metadata record
contains each of these fields.

**F30. Open licence.** Each release is published under an open licence stated
in its metadata and in its files, and the code that produced it under an
open-source licence. *M3b.* Test: both licences are stated, and neither
restricts reuse beyond attribution.

**F31. Open formats and shared vocabularies.** Release files use open,
non-proprietary formats readable without special software; a data
dictionary defines every field; terms are mapped to external vocabularies
where one exists (country codes, currency codes, organisation identifiers,
CRS and IATI codes). *M3b.* Test: every file opens with free software; every
field appears in the dictionary; every country, currency and funder code
follows its external standard or is marked as local.

**F32. Provenance in the release.** A release carries its provenance in
machine-readable form: the code version, the method versions, the cutoffs,
and for each statement the hash of the snapshot it was extracted from.
*M3b.* Test: from the release alone, the snapshot hash and the extraction
method of any statement can be read.

**F23. What the Observatory serves.** Every table of the ledger is served to
readers or named as not served with the reason; the definitions of terms are
served as a glossary with their sources and revision history. *M3b.* Test:
the list of served and not-served items covers every table.

**F24. Each country has its principal reference.** For each country, the
principal official reference and the latest subsequent official news are
pinned to their snapshots, with publication and selection dates; where no
later official item exists, the gap is stated. *M3b.* Test: each of the four
countries has both, or a stated gap.

**F26. Definitions a general reader follows.** Each term shown to readers has
a plain-language definition beside its formal one. *M4.* Test: every
glossary entry has a plain-language definition of at most a few sentences,
free of the builders' vocabulary.

## 5. Data requirements

What the Observer must hold and handle.

**DA1. Four countries.** South Africa, Indonesia, Viet Nam and Senegal. *M2.*
Test: every document and statement belongs to one of the four, or to no
recipient country for global method sources.

**DA2. The documents held.** 392 registered documents, 369 with a snapshot,
254 already extracted (13,092 statements from 253 snapshots), 115 with a
snapshot and nothing extracted yet (South Africa 49, Senegal 28, Viet Nam 25, Indonesia
13), 23 without a snapshot. *M2.* Test: every one of the 392 satisfies F2.

The counts reconcile as follows. At M2 the table is produced by a script over
the register and cited here, from Operation § 7.1 and from the storage
contract § 3; the figures below were counted from the ledger tables when the
specification was reviewed.

| Count | Value |
|---|---|
| Registered documents | 392 |
| Documents with a snapshot (held) | 369 |
| Distinct snapshots | 369 |
| Snapshots shared by two documents (a mirror) | 1 |
| Documents with two snapshots | 1 |
| Snapshots in the document store | 278 |
| Snapshots kept outside the document store | 91: 81 CRS extracts and 6 World Bank and ledger exports recorded by hand (`local-record`), 4 IATI country files fetched by script, each under the comparator data directories |
| Documents without a snapshot | 23 |
| Statements (lines) | 13,092 |
| Snapshots with statements | 253 |
| Documents with statements | 254 (the mirror shares its snapshot) |
| Documents with a snapshot and no statement | 115 |

The number of statements per identifier family and extraction method is
added here once the first replay has counted it (Q1). Of the 13,092
statements, 10,452 are comparator records (CRS, IATI and World Bank) in the
snapshots kept outside the document store; they are read and replayed at M2
by the ingestion run of Extraction § 6.2, with a count control per
snapshot, and count among the extracted statements of this requirement.

**DA3. Document types.** At least: progress updates, project pages, data
portals, official news, annual reports, operator reports, project lists,
implementation plans, investment plans, approval documents, secondary news.
Repeated series get a dedicated parser; one-off documents get an assisted
reading judged row by row (Q5). *M2.* Test: every type among the 115 has
an extraction path, and each document extracted by a dedicated parser
belongs to a repeated series or a repeated format of one publisher (a page
template).

**DA4. Formats.** HTML, PDF with a text layer, scanned PDF read by
transcription, spreadsheets, JSON, JavaScript data files, and bytes of
undetermined type. A value that exists only in a chart with no text is not
extracted (N2). *M2.* Test: every format among the 369 snapshots has an
extractor, or
its documents carry a disposition that names the format.

**DA5. Languages.** English, Indonesian, Vietnamese and French. The language
of every document is recorded; every statement keeps its label in the
language printed; one member of a translation pair is canonical for extraction.
*M2.* Test: no document has an unknown language (20 of the 115 have none
today); no statement cites a translation.

**DA6. Three document classes.** Frozen (collected once, then checked),
living (re-collected, each version kept as a dated snapshot) and series
(each issue frozen, the series having an expected next issue). *M3a* for
recording the class, *M4* for acting on it. Test: every admitted document has
a class; at M4, a late issue of a series is signalled.

**DA7. The discovery frame.** Per country: the national JETP portal or
responsible ministry; the lead partner governments and every public partner
named in the package; the multilateral and private windows named in
official financing tables; the national electricity operator and named
project operators; every project in an official plan, pipeline or progress
list. *M3a.* Test: each class of the frame has at least one entry per
country, or a recorded reason it has none.

**DA8. A known-item list.** A list of documents known to exist, compiled
before the discovery rounds, against which recall is estimated. *M3a.* Test:
the list predates the first round and its recovery rate is reported.

**DA9. Unreachable documents are data.** The list of documents and search
channels that could not be reached, with the reason, is released with the
register. *M3a.* Test: the M3a collection report contains it, and from M3b
the release does, with each entry's reason taken from the reasons of
Collection § 8, including documents reachable only through paths the
site's robots rules exclude, with the robots position recorded on their
retrieval.

**DA10. Structured search channels.** CRS and IATI records for the four countries,
held as comparator records beside the documentary statements, never merged
into them. *M3b.* Test: every CRS or IATI record used in a result is
identified by its record identifier and retrieval date.

**DA11. Expected volume.** After M3a and three years of refresh, the Observer
handles about ten times the documents held today and a weekly snapshot of
each living document, with no change of design. *Later* (stated so that M2
does not preclude it). Test: the design documents name no limit that the
current volume already approaches.

**DA12. Reference operations outside the partnerships.** Milestones of JETP
operations dated before the partnership, and operations of partner lenders
in the four countries that carry no JETP attribution, are held in a counting
scope of their own: the pre-existing history of JETP operations and a
reference pool. They never enter a strict JETP figure (F13). *M3b.* Test: a
strict-scope figure recomputed without this scope is unchanged.

## 6. Quality requirements

### 6.1 Correctness and reproducibility

**Q1. Replay.** The pipeline reproduces the statements of the 254 documents
already extracted, byte for byte, or every difference is explained. *M2.* Test:
the replay report lists zero unexplained differences for statements minted
by extractors and written by ingestion runs (the held comparator records
included, each snapshot's record count equal to the count it states), and, for the others, the result
of the locator-and-text check, listed by method; it counts the statements
of each identifier family and method.

**Q2. Idempotence.** Re-running on a snapshot already extracted changes nothing and
never renumbers a statement's identifier. *M2.* Test: two consecutive runs
produce identical outputs.

**Q3. Parsers are red-tested.** Each parser is tested by replaying a defect
it must reject; the other extractors have the controls of Extraction § 12.
*M2.* Test: every parser has such a test, and the test fails when the defect
is re-introduced.

**Q4. LLM readings are recorded as readings.** An LLM reading is not
byte-reproducible; its recorded output is the record, with the LLM, version,
prompt version, inputs and cost. Replay and idempotence bind the parsers and
the writer, not a fresh reading. *M2.* Test: every statement extracted by an
LLM names its LLM and version; re-running
does not replace a recorded reading.

**Q6. Released figures trace both ways.** Every published number, status and
substantive narrative claim resolves to the statements and the named
calculation it rests on, down to the snapshot bytes that supported it; from
any statement, the published figures that use it are reachable. The latest
snapshot of a document never stands in for the one that supported an older
statement. *M3b.* Test: sample figures from the Observatory and from each
paper; each resolves to snapshots and locators, and each sampled statement
lists the figures that use it.

**Q7. Corrections propagate.** A correction reaches every published claim it
touches, and those claims are identifiable before the next release. *M3b.*
Test: revoke one match; the list of affected figures is produced.

**Q8. Releases are frozen and reproducible.** A release has an identifier;
from it, a paper result and an Observatory figure reproduce exactly. A
corrected current account never silently refreshes a released result. *M3b.*
Test: an independent reader reconstructs one country total and one timeline
from the release, its dictionary and its locators, over documents that have
a public copy (redistributed bytes or a public archive capture); any
undocumented choice is a failure.

**Q9. Every method has a version.** Every extraction, reading, judgement,
scope and calculation names its method and version; changing one produces a
new result under a new version. *M2* for extraction methods and document
judgements, *M3a* for triage, *M3b* for the other judgements and for
calculations. Test: every result names the versions it was computed under.

**Q10. Recall is stated.** Discovery follows a stopping rule stated before
the first round; every round is logged, empty rounds included; the recall
estimate against the known-item list is reported; the tracker traceability
rate, the share of the main secondary trackers' quantitative claims traced to
a primary document read by the Observer, is reported with the distribution
of all claim outcomes. *M3a.* Test: the author accepts the protocol, the recall estimate
and the unreachable list before M3b starts.

### 6.2 Judgement and uncertainty

**Q5. Machine judgements are automated, diverse, calibrated and recorded.**
Judgements made by LLMs (a statement extracted, a match, a preference, a
classification) are made without the author. They are automated; diverse,
read independently by models of different families; calibrated, since
readers are selected and calibrated on held-out reference answers before
use and a reader that fails its positive controls is weighted out;
escalated, since what the readers disagree on or hold with too little
likelihood goes to a stronger arbiter; recorded, since every item ends with
a stance, possibly undetermined, and a calibrated likelihood and
confidence, with every reader's answer; and served sorted by likelihood and
confidence. No item is queued for the author: he examines the results when
he chooses, and a decision he makes is recorded like any other judgement.
Only a question that changes what a term or the contract means goes to
him, with the panel's stance. The readers, the escalation and the
milestone at which each part applies are specified in Extraction,
Collection and Fusion § 3. *M2* for statements extracted and for document
identity judgements, *M3a* for discovery and admission judgements, *M3b*
for the other identity judgements and for preference judgements. Test:
every LLM judgement in a release carries readings from more than one model
family, a stance and a calibrated likelihood and confidence; every reader
used has a recorded calibration on held-out reference answers; no design
rule queues an item for the author.

**Q11. Uncertainty is never hidden.** A value may be a range and a date an
interval; judgements use the calibrated likelihood and confidence scales;
unknown is not zero; an unresolved disagreement is carried into the result
with the condition that blocks comparison; no preferred figure is
manufactured to fill a gap. *M2* for keeping ranges and date precision in
statements, *M3b* for results. Test: a released figure over a subject with
unresolved disagreement shows both values; no missing value is summed as
zero.

**Q17. Machine readings and human decisions side by side.** Every machine
reading of a statement or judgement, and every human decision on it, is
kept; neither overwrites the other, and each names its method, version and
cost. A decision that rejects a reading names the step at fault (retrieval,
extraction, reading, matching), so that errors are locatable. The reference
answers for research on machine reading (AEDIST) are the hand-made
readings: lines read by hand, match judgements decided by hand, and any
decision the author chose to make. A statement admitted on machine readings
alone carries that flag and is not a reference answer, and the readers and
the arbiter are named, so that a benchmark can exclude the Observer's own
readers. The
cost per method can be compared. *M2.* Test: for a sample
of checked statements, every machine reading and the decision are
retrievable with method, version and cost; a decision that disagrees with a
reading leaves the reading intact and names a step.

### 6.3 Integrity of the record

**Q12. Computed and published numbers are told apart.** A number the
Observer computed and a number a publisher printed are always
distinguishable, each with its own attribution. *M3b.* Test: every number in
the Observatory and the papers is marked as one or the other.

**Q13. What is documented is kept apart from inference.** No product presents an
association as a cause, a stage difference as speed, or a documentary gap as
an actual absence of finance. *M3b.* Test: the integration review finds no
causal or speed claim in the Observatory and none unsupported in the papers.

**Q16. A neutral documentary record.** Everything the Observer outputs is
either a statement attributed to its publisher or a figure labelled as the
Observer's calculation under a declared method. The Observer does not grade
partners, judge whether a promise was kept, or recommend policy. *M2.* Test:
no rule in any specification document makes the Observer assert a finding in
its own voice other than a declared calculation; the Observatory contains no
evaluative wording about a partner.

### 6.4 Maintainability and operation

**Q18. Maintainable by agents and one researcher.** Every behaviour of the
Observer is governed by a rule written in a specification document or a
recorded decision, implemented in code that names that rule, and guarded by
a test that an agent can run without the author. An agent new to a part of
the Observer can find, for any behaviour, its rule, its code and its test.
*M2.* Test: for a sample of behaviours, the rule, the code and the test are
each found from the specification in one step; the tests run without the
author's intervention.

**Q19. Every change reviewable and reproducible.** Every change to code,
rules or data enters through a reviewed change that states its reason and
passes the tests, reviewed by an LLM of another family than the one that
wrote it. Any release or intermediate result can be rebuilt from the
repository at its recorded version and the archived documents, identically
for deterministic steps. *M2.* Test: for a sampled merged change, its
reason, review and test run are found; a sampled result rebuilt from its
recorded version is byte-identical.

**Q20. Anomalies are visible in the Observatory.** Besides its public role,
the Observatory shows the author and the agents what needs attention: figures whose
trail does not resolve, documents and countries without new statements,
the least certain and the undetermined judgements, and changes between runs
large enough to check. *M3b* for broken trails, in the build and run
reports, and for judgements, on a page sorted by likelihood and confidence;
*M4* for countries and documents without new statements and for changes
between runs. Test: a deliberately broken trail appears in the build report
and stops the release, and an undetermined judgement appears on the sorted
page of judgements; at M4, an injected jump in a total is flagged.

**Q21. Decisions are traceable.** Every decision that shapes the Observer (a
rule adopted, a scope changed, a value preferred by the author, a milestone
accepted) is recorded with its author, date, reason and the alternatives
considered, and is reachable from what it governs. *M2.* Test: for a
sampled rule of a specification document and a sampled decision of the
author, the decision record is found and states its reason.

**Q14. No silent run.** Every run, launched or scheduled, ends with a report
that says what it did, what it found, what failed and what it deferred; a
run that finds nothing says so. *M2* for hand-launched runs (C4), *M3a*
for discovery rounds, *M4* for scheduled passes. Test: kill a run midway; the failure is reported, and no
report reads as an all-clear.

**Q15. Cost and effort are measured.** Each run records its LLM spend and
its local compute time, so that the cost of an accepted change can be
computed. *M2* for the record, *M3b* for stating it in the release. Test:
the M3b release states spend and compute time per document class, document
type and extraction method.

## 7. Constraints

**C1. One researcher's attention.** The author is the only person working on
the Observer, and the author's attention is its scarcest resource.
Decisions are batched, and no machine judgement is routed to the author
(Q5): he examines results sorted by likelihood and confidence when he
chooses. *M2.* Test: no design rule requires the author to review, audit or
sample any item of a class; only questions that change what a term or the
contract means are put to him, batched with a recommended default.

**C2. Two machines, one direction.** padme, a personal workstation with GPUs
and the document bytes, runs every job that reads bytes or runs LLMs; doudou, a
laptop, supervises, verifies and defers a run when padme is unreachable, and
says so. Data flows from padme to doudou only. *M2* for jobs, *M4* for
supervision of scheduled runs. Test: no design rule moves data from doudou
to padme or requires the laptop to hold all document bytes.

**C3. Local compute first.** padme serves local LLM readers on two
consumer GPUs (16 GB and 12 GB). Bulk reading runs on them, or on a paid
interface within budget (C4); escalation to a stronger model uses a paid
interface. *M2.* Test: each reading method names where it runs.

**C4. Budgets.** Paid interfaces (LLM readers, search, bibliographic
APIs) run under a budget stated before the run, per document and per run; a
run that reaches its budget stops and reports. *M2.* Test: every paid call
belongs to a run with a stated budget. The amounts are set in Operation.

**C5. Open access.** The papers are published in diamond open access without
article processing charges; each release carries its reuse terms and its
citation (F28 to F30). *M3b.* Test: the release states reuse terms,
citation and deposit identifier.

**C6. Terms of use of sources.** Automated link-following obeys each site's
robots rules. A single fetch of a known document that the public can open
in a browser goes ahead, and the site's stated position (robots rules, terms
of use) is recorded with the retrieval. Technical checks and logins on
public sources, including sites behind a free public registration, are
passed by the author in person, never by automation, and the registration
used is recorded without its credentials; content the public cannot reach
(paid subscription, invitation-only or institution-only access) is not
fetched (F27, N13). A change of a site's terms or robots rules is signalled, never
silent. Document bytes are redistributed only where the source's terms
allow; otherwise a release carries the address, hash and locator. *M3a.*
Test: no automated crawl fetches a path the site's robots rules exclude;
every single fetch records the site's stated position; the M3a collection
report states the position recorded per site, and from M3b the release lists
which bytes are redistributed and on what terms.

**C7. Static publication.** The Observatory is published as static pages and
frozen data, with no server application required to read it. *M3b.* Test: the
Observatory of a release opens from its files alone.

**C8. Build to the milestone.** A mechanism not needed by an M2 or M3
requirement is not built before M4; code is shared with another project
only when a second consumer runs on it. *M2.* Test: every section of a
specification document that holds a rule tagged M2 or M3 maps, in the
reverse map of section 9, to at least one requirement of that milestone; a
section that maps to none moves to M4.

**C9. Secrets.** Credentials are read at use and never written to logs,
reports or releases. *M2.* Test: no run report or release contains a
credential.

**C10. A declared horizon.** The Observer is maintained to a declared end,
not indefinitely. The initial partnership periods run three to five years
(South Africa to 2027, Indonesia and Viet Nam 2025 to 2027, Senegal 2026 to
2028); structured search channels report one to three years late. Default:
maintained through 2030, an extension decision in 2028, and an archived
final release at the end, after which every release cited by a product stays
retrievable. *M4.* Test: Operation and Results and releases state the end
date, the date of the extension decision, and how the final release is
archived; a release identifier cited in a paper resolves after the end.

## 8. Non-requirements

Out of scope, so that no design rule is written to serve them.

**N1. No models.** In the Ontology, Data, Evidence, Models frame of Language,
the Observer is focused on Data, guided by the Ontology; Evidence (counts,
accounts, descriptive tables) is computed on top of Data and never edits
it; there are no Models. The Observer estimates no effect of the
partnerships and holds no causal explanation. A causal study, if one is
commissioned, consumes a frozen release from outside the Observer.

**N2. Classes out of scope by decision.** Institutional events and
party-to-party relations beyond roles; natural persons as signatories or
delegates; values that exist only in a chart; a document as the subject of a
statement; recurrence; a publisher's own liabilities and budget; physical
outcomes beyond capacity, length and state (emissions, jobs, people,
generation). Each enters only by a decision that adds it as a measure.

**N3. Not a lender's books.** The Observer reconstructs from public
documents; it does not require debit and credit counterparts that no
document discloses.

**N4. No automatic truth.** No program, and no rule without a recorded
judgement, admits a document, merges two identities, prefers a value or
publishes a release on its own. A program that applies a rule the author
adopted by version applies the author's judgement (Fusion § 3).

**N5. No claim of completeness.** Coverage is quantified; universal
completeness is never claimed.

**N6. No real-time monitoring and no unattended publication.** Refresh is
weekly at most (a working assumption the author may change), from M4;
publication is always a reviewed act.

**N7. No countries beyond the four** before M4. *Later:* adding a country
requires a discovery frame and data, not a change of design.

**N8. No translations or summaries as requirements.** Machine translations of
labels and summaries of documents may be added for readers; nothing depends
on them. *Later.*

**N9. No move of the document store before M4.** The move to a dedicated
reference library is M4; earlier milestones only keep fetching behind one
seam so that the move rewrites nothing else.

**N10. No welfare or justice measurement.** A budget allocation to a social
objective is recorded as such; it does not measure an improvement in
welfare.

**N11. No writing or submitting of papers.** The Observer supplies dated statements
and reproducible results; manuscripts and journal submission are outside it.

**N12. Not a general climate-finance tracker.** The Observer stays specific
to the Just Energy Transition Partnerships. The climate-finance article and
the book use it as a case study; they do not extend its scope.

**N13. No closed material.** Nothing the public cannot reach enters the
Observer, whoever offers it: no content behind a paid subscription, no
invitation-only or institution-only access, no leaked or confidential
document, no non-public dataset, no private communication. A site behind a
free public registration is not closed (F27). Such material, where known to
exist, may be listed as unreachable (DA9); it is never read.

## 9. Requirements and the documents expected to meet them

A requirement may be met by more than one document; the first named carries
it. "Extraction § observations" is the M3b section of the extraction
document that reads statements into observations.

| Requirement | Milestone | Expected to be met by |
|---|---|---|
| **4.1 Discovery and holdings** | | |
| F7 Discovery proposes, a decision admits | M3a | Collection |
| F8 What was sought recorded | M3a | Collection; Ontology |
| F27 Public documents only | M2, M3a | Collection; Operation |
| F3 Duplicates resolved before extraction | M2 | Fusion § 3; Extraction |
| F2 Every document accounted for | M2 | Extraction |
| F5 Pending work computable | M2 | Extraction; Operation |
| **4.2 Statements and traceability** | | |
| F1 Statement names where it was extracted | M2 | Extraction; Storage |
| F4 Living documents append | M2 | Extraction; Fusion § 2 |
| F6 Disagreeing statements retrievable | M2, M3b | Fusion § 5; Extraction |
| F21 Excerpts for qualitative work | M3b | Results and releases |
| F25 Reported errors are traced | M3b, M4 | Results and releases § 9; Fusion § 2 (the judgement); Operation § 4 (the intake: a ticket per report) |
| **4.3 Identities and judgements** | | |
| F11 Referents by decision, counted at a match threshold | M3b | Fusion § 3 |
| F12 Organisations under authority control | M3b | Fusion § 3; Ontology |
| F20 Finance joined to assets | M3b | Fusion § 3; Ontology |
| **4.4 Observations, accounts and results** | | |
| F10 Results at a knowledge cutoff | M3b | Fusion § 8; Results and releases |
| F13 Counts name unit and population | M3b | Fusion § 6–7; Results and releases |
| F14 Financial states selected, not added | M3b | Extraction § observations; Fusion § 7; Ontology § 4 |
| F15 Money in publisher's currency | M3b | Extraction § observations; Fusion § 7 |
| F16 Operation timelines with honest dates | M3b | Fusion § 7 (timelines); Extraction § observations; Ontology |
| F17 Funding roles kept apart | M3b | Extraction § observations; Ontology; Fusion § 7 |
| F18 Transition functions | M3b | Extraction § observations; Ontology |
| F19 Matching to CRS and IATI, gaps between financial states | M3b | Fusion § 5; Results and releases |
| F22 Change between releases attributed | M4 | Fusion § 8; Results and releases |
| **4.5 Releases and reuse** | | |
| F9 Two dates per release | M3a | Results and releases; Collection |
| F28 Persistent identifier | M3b | Results and releases |
| F29 Rich metadata | M3b | Results and releases |
| F30 Open licence | M3b | Results and releases |
| F31 Open formats and shared vocabularies | M3b | Results and releases; Ontology |
| F32 Provenance in the release | M3b | Results and releases; Storage |
| F23 What the Observatory serves | M3b | Storage § 2; Presentation |
| F24 Principal reference per country | M3b | Presentation |
| F26 Definitions a general reader follows | M4 | Ontology § 5; Presentation |
| **5 Data** | | |
| DA1 Four countries | M2 | Ontology; Collection |
| DA2 Documents held | M2 | Extraction |
| DA3 Document types | M2 | Extraction |
| DA4 Formats | M2 | Extraction |
| DA5 Languages | M2 | Extraction; Storage § 5 |
| DA6 Three document classes | M3a, M4 | Collection; Operation |
| DA7 Discovery frame | M3a | Collection |
| DA8 Known-item list | M3a | Collection |
| DA9 Unreachable documents are data | M3a | Collection; Results and releases |
| DA10 Structured search channels | M3b | Collection; Ontology |
| DA11 Expected volume | later | Storage; Operation |
| DA12 Reference operations outside the partnerships | M3b | Collection; Fusion § 6 |
| **6 Quality** | | |
| Q1 Replay | M2 | Extraction |
| Q2 Idempotence | M2 | Extraction; Storage |
| Q3 Parsers red-tested | M2 | Extraction |
| Q4 LLM readings recorded | M2 | Extraction |
| Q6 Released figures trace both ways | M3b | Results and releases; Presentation |
| Q7 Corrections propagate | M3b | Results and releases |
| Q8 Releases frozen and reproducible | M3b | Results and releases |
| Q9 Every method has a version | M2, M3b | Extraction; Extraction § observations; Fusion § 1 |
| Q10 Recall stated | M3a | Collection |
| Q5 Machine judgements automated, diverse, calibrated, recorded | M2, M3a, M3b | Extraction; Collection; Fusion § 3 |
| Q11 Uncertainty never hidden | M2, M3b | Extraction § observations; Fusion § 1; Results and releases |
| Q17 Machine readings and human decisions side by side | M2 | Extraction; Fusion § 3; Storage |
| Q12 Computed and published numbers apart | M3b | Presentation; Results and releases |
| Q13 Documented apart from inference | M3b | Language; Presentation |
| Q16 A neutral documentary record | M2 | every document; Presentation |
| Q18 Maintainable by agents and one researcher | M2 | Operation; every document |
| Q19 Every change reviewable and reproducible | M2 | Operation; Results and releases |
| Q20 Anomalies visible in the Observatory | M3b, M4 | Presentation (pending judgements); Results and releases § 5 and Operation § 8 (broken trails in the build and run reports); Operation § 11 (M4) |
| Q21 Decisions traceable | M2 | Operation; every document |
| Q14 No silent run | M2, M3a, M4 | Operation; Collection |
| Q15 Cost and effort measured | M2, M3b | Operation; Results and releases |
| **7 Constraints** | | |
| C1 One researcher's attention | M2 | Operation |
| C2 Two machines, one direction | M2, M4 | Operation |
| C3 Local compute first | M2 | Operation; Extraction |
| C4 Budgets, amounts set in Operation | M2 | Operation |
| C5 Open access | M3b | Results and releases |
| C6 Terms of use of sources | M3a | Collection; Results and releases |
| C7 Static publication | M3b | Presentation; Storage § 3 |
| C8 Build to the milestone | M2 | every document |
| C9 Secrets | M2 | Operation |
| C10 A declared horizon | M4 | Operation; Results and releases |
| **8 Non-requirements** | | |
| N1–N13 | — | every document: no rule may serve only these |

**Sections and the requirements they serve.** The reverse map, for the
sections that hold M2 or M3 rules, so that C8 can be checked at the grain of a
section. The sections of checks and of milestone slices serve the
requirements of the sections they test.

| Document § | Requirements served |
|---|---|
| Collection § 1 Principles | F7, F8, F27, C6, Q10 |
| Collection § 2 What collection handles | F2, F3, F27 |
| Collection § 3 The authority frame | F8, DA7 |
| Collection § 4 Search channel classes | DA7, Q10 |
| Collection § 5 Rounds and the stopping rule | Q10 |
| Collection § 6 Known items and the recall estimate | DA8, Q10 |
| Collection § 7 The secondary-to-primary pass | Q10, F6 |
| Collection § 8 Access and unreachable documents | F27, C6, DA9, F8 |
| Collection § 9 Candidate triage | F7, Q5 |
| Collection § 10 Document classes | DA6 |
| Collection § 11 Two published dates and the freeze | F9, F2 |
| Extraction § 1 Principles | F1, F2, Q9 |
| Extraction § 2 Scope and preconditions | F3, F5, DA5 |
| Extraction § 3 What a statement carries | F1, Q4, Q9, Q17 |
| Extraction § 4 What becomes a statement | F1, DA3 |
| Extraction § 5 Text layers by format | DA4, F1, Q1 |
| Extraction § 6 Extraction methods | DA3, Q3, Q4, Q5, Q17, C3 |
| Extraction § 7 Dispositions | F2, DA2, DA4 |
| Extraction § 8 Dated snapshots and restatements | F4, F6 |
| Extraction § 9 Identifiers and corrections | Q2, F1 |
| Extraction § 10 Replay, idempotence and their limit | Q1, Q2 |
| Extraction § 11 Reading statements into observations | F14, F15, F16, Q9, Q11 |
| Extraction § 12 Red tests and controls | Q3, Q1 |
| Fusion § 1 Principles | Q9, Q11, F6, F10 |
| Fusion § 2 Revision | F4, F6, F25 |
| Fusion § 3 Identity | F3, F11, F12, F20, Q5 |
| Fusion § 4 Occurrence | F13, F14 |
| Fusion § 5 Conflicting values | F6, F19 |
| Fusion § 6 Perimeters and counting scopes | F13, DA12 |
| Fusion § 7 Counting and accounts | F13, F14, F15, F16, OBS-1 |
| Fusion § 8 Knowledge time and change | F10 |
| Ontology § 2 to § 4 Vocabulary, relations, classifications | OBS-4, F13, F14, F17, F31 |
| Ontology § 5 Ontology tables | OBS-4, Q9, F23, F31 |
| Storage § 1 Tables and rules | F1, F2, F32, Q2, Q9, Q17 |
| Storage § 2 What the Observatory serves | F23 |
| Storage § 3 Engine | Q19, C7 |
| Storage § 4 Matching records | F3, F11, Q5, Q17 |
| Storage § 5 Language, translation and summaries | DA5 |
| Results § 1 to § 3 Principles, results, thresholds | Q6, Q8, Q9, Q11, F10, F11, F13 |
| Results § 4 to § 8 Releases: contents, build, identity, redistribution, citation | F9, F23, F28, F29, F30, F31, F32, C5, C6, Q8, BK-2 |
| Results § 9 Correction and restoration | Q7, F25, F28 |
| Results § 10 The Observatory as a view of one release | C7, Q8 |
| Presentation | Q6, Q12, Q20, F23, F24 |
| Operation § 1 to § 3 Principles, machines, data flow | C1, C2, C3, C4 |
| Operation § 4 The repository as control plane | Q19, Q21 |
| Operation § 5 LLM readers and the checking rule | Q5, Q17, C3 |
| Operation § 6 Secrets | C9 |
| Operation § 7 and § 8 Budgets, logging spend and compute time | C1, C4, Q14, Q15 |
| Operation § 9 Backups and recovery | Q19 |
| Operation § 10 Failure handling | Q14, C2 |
| Language | Q13, Q18 |
