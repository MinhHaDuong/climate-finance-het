# JETP information fusion: methods and rules

Status: draft for author review, 2026-09-30 (ticket 1701).

Information fusion is what turns statements printed by many publishers into
identities, assessments and accounts. The [ontology](jetp-ontology.md) fixes
the words; this document fixes how statements expressed in those words are
combined, weighed and revised. Its rules are conceptual: they hold whether the
statements are kept as RDF triples queried with SPARQL, as sentences of flat
text, or as rows of a table, and whether the result is read on a screen, in a
paper or not at all. How statements are stored is the storage contract's
business; how results are shown is the observatory's.

In the ODEM frame ([language](jetp-language.md)), identity decisions are the
last step of Data and accounts are Evidence. Both are methods: each rule below
has a version, and every result names the versions it was computed under.

## 1. Principles

**Documentary accounting.** The ledger reconstructs from public documents;
it is not a lender's double-entry books. It cannot require debit and credit
counterparts that no document discloses. It can require identities,
comparable perimeters, explicit movements and stated differences. An item in
a plan is a statement of intention: it proves neither financing, nor
admission to a later cohort, nor physical progress.

**Statements, not facts.** The ledger holds what a publisher printed, at a
locator, in a snapshot, on a date. "The loan was signed on 3 May" enters as
"this publisher stated, in this document read on this date, that the loan was
signed on 3 May". Fusion combines statements; it never promotes one to a fact
by erasing the others.

**Traceable.** Every identity, assessment and account resolves to the
statements it rests on, the decisions that combined them, who or what took
each decision, by which method and version, and when. A result whose chain
does not resolve is not a result.

**Defeasible.** Every decision can be revised by a later one, which records
what it revises and why. Nothing is revised by erasure: the earlier decision
stays readable, so a result computed before the revision can be reproduced.

**Uncertainty accepted.** A value may be a range and a date an interval.
Disagreement between sources may remain unresolved in a released result, and
no preferred figure is manufactured to fill a gap. Unknown is not zero, and a
missing document is not a missing event: absence of evidence is recorded as
such, with the search that failed to find it.

**Pedigree.** Each statement carries a qualitative assessment of where it
comes from, in the sense of the NUSAP pedigree: how close its publisher is to
the event (the party that did it, the party that paid, a secretariat that
compiled, a database that aggregated, a newspaper that reported), how
independent it is of other statements, how it was produced (a register, a
plan estimate, a press release), and how it entered the ledger (parser,
assisted reading, transcription, human review). Pedigree weighs statements
against each other; it never deletes one.

**Independence of sources.** Two statements confirm each other only if they
are independent. A mirror, a reprint, a translation, a copied report or a
secondary source quoting a primary one adds no confirmation, and one payment
described by several documents stays one payment.

**Two times.** Every conclusion is dated twice: the time of the world it
describes, and the time the ledger knew it. A result at knowledge cutoff K
uses only statements and decisions admitted on or before K, so a later
discovery never changes what an earlier result said.

**Declared method.** A rule that selects, weighs or transforms is a method
with a version. Changing it produces a new result under a new version; it
never silently rewrites an old one.

**Storage and presentation independence.** No rule depends on how statements
are stored or how results are shown. A rule that only makes sense for one
storage layout or one screen belongs to the storage contract or to the
observatory, not here.

## 2. Revision

A publisher's new statement never revises an earlier one. When a later
snapshot of a document prints a different value, that is a new dated
statement beside the old one, and whether it records a change in the world, a
late report or the publisher correcting itself is an interpretation, taken by
a decision that says which (section 8). When a later snapshot prints the same
content again, the restatement is kept under its own date: it is weak
confirmation that the earlier statement still held on the later date.

Supersession, where one entry replaces another in force, is reserved for the
ledger's own errors: a misread value, a wrong locator, a false match, an
extraction rule found faulty. The superseded entry stays readable; what is in
force is the end of the chain.

## 3. Identity

Matching mints an identity from statements, attaches a statement to an
existing identity, or relates a statement to one in another edition. An
identity (project, asset, agreement, party, perimeter) exists only because a
reviewed decision minted it; reading a document never mints one. A statement
with no identity yet stays a subject of observations in its own right; it
does not dissolve into an aggregate.

The author set the requirements on 2026-09-22: multilingual recognition of
named entities in the labels, matching with a confidence, escalation to a
large language model (LLM) and then to a person, defeasibility and
traceability. What is fixed now is the shape of a decision, so that one taken
by the simplest matcher today and one taken by a person in two years can be
compared and overturned the same way.

**The decision.** A matching decision names who or what decided (a program, an
LLM, a person), by which method and version, with what confidence between 0
and 1, on which justifying statements, and when. It is accepted, a candidate
or rejected. A decision is never altered: a later decision names the one it
revises, and what is in force is the end of the chain when that end is
accepted. A false match is revoked by a rejection that revises it, and
nothing else needs to be created. A candidate below the acceptance threshold
stays a candidate, counted apart; it never changes a count of accepted
identities.

- An equality claim (`same_as`) is evidence that two things are one; it does
  not choose which name or route prevails.
- The classification of an identity (project, programme or component) is a
  dated decision; a later classification does not change what earlier
  statements were about.

**The tiers.** Each tier works only on what the previous ones left undecided,
and signs its decisions with its own method name.

1. Exact identifier: a register's unique identifier, a plan's ordinal within
   an edition, an operator's project code. Confidence 1.
2. Normalised label: case, diacritics, technology prefixes and units removed
   (PLTU, PLTS, PLTBg; Nhà máy Thuỷ điện; centrale, poste), tokens compared
   within a country and a technology group. Confidence from the string
   distance and from the agreement of capacity and location where both
   statements give them.
3. Named entities in the four label languages (Indonesian, Vietnamese, French,
   English): place, operator, technology and capacity as typed spans, matched
   as tuples. Confidence from the agreement of the tuples.
4. LLM adjudication of the remaining candidates, given both statements and
   the pages they come from, returning a verdict, a confidence and a quoted
   basis. The LLM is named as the decider.
5. Adjudication by a person of what the LLM declines or contradicts.

A tier's thresholds are part of its method version. Before a tier may accept
matches unattended, its thresholds are tested on the hand-matched cases held
out as a test set; until it passes, it proposes candidates only.

**Verification and confidence (author, 2026-09-29).** The author is not the
checker. A tier-4 reading is verified by independent readers from different
vendors, on the same inputs, blind to each other's answers, choosing from a
closed list of options with a quoted basis and a self-assessed score.
Positive controls with a certain answer run first, and a reader that misses
one is weighted out. A versioned rule turns the readings into a stance and a
confidence. Every case gets a stance, applied as a defeasible decision that
names the panel and its version as decider, never as a silent overwrite, with
the confidence and the readers' verdicts kept beside it. In the author's
words: "take a stance, keep track of the confidence level, and let me examine
the results sorted by confidence level". A stance that implies a change in
what a term means is a proposed revision of that term, a candidate with the
same confidence, never an edit of the accepted definition.

**Organisations.** Parties are under authority control, as in a library's
name authority file or the ROR and GLEIF registries: one identity per
organisation, every form of its name attached to it, one form preferred
(author, 2026-09-23). Two rules of their own apply.

- Tier 1 is an external identifier: an IATI organisation identifier, a ROR
  identifier, an LEI or a Wikidata item. Two names that carry the same
  identifier are one organisation.
- Forms that differ only by case, diacritics or spacing (Senelec and
  SENELEC) are merged when the party is minted: one party with several name
  forms, never two parties joined by an equality claim.
- Tier 2 runs only on real variants: an acronym against its expansion (AFD
  and Agence française de développement, PLN and Perusahaan Listrik Negara),
  a translation (Vietnam Electricity and Tập đoàn Điện lực Việt Nam), a former
  name. It proposes equality claims between two parties, reviewed by a person.
  Accepting one folds the parties: the retained party gains the other's name
  forms, and the retired identity leads to it.

**Documents.** The same decisions apply one level up, to documents, and run
before any statement is read from them, because a duplicate document read
twice doubles every statement and every count downstream. One publication
under two addresses or two exports is `same_as`; succession is `edition_of`;
the same publication in another language is `translation_of`. Statements are
read from the canonical member of a `same_as` group and from one language of
a translation pair; the other members remain citable bytes. The tiers:

1. Identical fingerprint under two documents: one set of bytes, two
   addresses. Confidence 1.
2. Identical text after normalisation, or a near-duplicate fingerprint of the
   text with the same page count. Catches a re-export and a page whose
   timestamp changes on every visit.
3. Agreement of title, publisher, publication date, page count and any
   identifier the document prints. Catches a partner's mirror and, with a
   language detector, a translation.
4. LLM adjudication of the remaining pairs, given both first pages.
5. Adjudication by a person.

## 4. Occurrence

Several statements may describe one event. Deciding which describe the same
event is an adjudication, taken on the content and never on the order in
which statements were read or on publisher rank.

- Statements of one event not yet adjudicated as one are not added together.
- A repeated cumulative balance is not a new movement.
- A quarterly total is not split into months unless a statement does so.
- An observed completed state invents neither a commissioning date nor a
  payment.
- Signing, approval and disbursement are different measures, not steps of one
  ranked stage.

## 5. Conflicting values

When statements about the same subject, measure and time disagree, all of
them are kept. An adjudication may select one for a given result; it records
the criterion it applied.

- The default criterion is pedigree, and first closeness to the event: the
  primary source nearest to the event prevails over one further from it
  (ticket 1180). It is a criterion an adjudication applies and records, not an
  automatic selection, and it never reduces to the rank of a publisher.
- Secondary reporting is a lead toward a primary document. It stands as the
  only support of an event only when no primary document is public, and the
  event is then marked as supported by secondary sources only.
- Structured channels (OECD CRS, IATI) have no precedence of their own. They
  report one to three years late, and that lag is measured, not assumed.
- Where no adjudication selects, a result carries the disagreement: both
  statements, and the condition that stops them from being compared
  (different perimeter, basis, currency, cutoff or measure).
- Differences between announced, signed, reported and disbursed amounts are
  findings about the gap between stages, not conflicts to resolve.

## 6. Perimeters

A perimeter is the population a count or a sum is made against. Two kinds
enter fusion differently.

- **Stated by a publisher**: a pledge envelope and its revisions, a
  portfolio, a procurement quota, a plan's list at a cutoff. It is a statement
  like any other, with its publisher and date, and membership in it is
  evidence, not a list.
- **Defined by the analysis**: the scopes a study or account counts against,
  such as a strict JETP scope and an extended scope of partner energy
  finance. The strict scope requires explicit JETP attribution in the
  source; the extended scope is reported separately and never fills the
  strict one. It is a method choice with a version; changing its definition
  makes a new perimeter, and a count made against the old one is never moved
  silently to the new one.

Sharing a perimeter does not prove comparability: an account also checks
changes in membership, instrument and basis, and unknown compatibility blocks
the comparison without hiding the separate statements.

## 7. Counting and accounts

**Counting.** Every count names its unit: statements of a document,
identities of a kind, or a count a publisher stated. There is no default sum
of projects, programmes and components, and a publisher's count of records is
not relabelled a count of assets. Overlapping hierarchies need an explicit
selection before any aggregate, and a hierarchy never splits money: a
project's share needs a statement that gives it. Financial states (need,
announced, memorandum, approved, signed, disbursed) form a chronology, not
additive categories: an aggregate selects one state explicitly. A physical
state never follows from a financial one, and a plan's priority ranking
implies neither finance nor physical progress.

**Money.** Values stay the publisher's, in its unit and currency. A
conversion uses a rate that a document printed, cited like any statement; no
rate is assumed and no conversion is implicit. A conversion made by a third
party is kept as its statement and excluded from sums in original currency. Gross flows are not reduced by
refunds, repayments or cancellations, which remain their own measures. Rounded
inputs carry their bounds, and a rounding difference is not a discrepancy.

**Markers.** The climate finance a policy marker yields is the donor's score
times a coefficient that depends on the donor and the year. The coefficient is
a sourced parameter of the account, cited to the document that states it; it
is applied only in the account, so the same loan can move from 40 to 100
percent climate finance without any change in the loan.

**Reconstruction.** An account of a subject between two dates starts from an
accepted opening position with an exact cutoff (zero needs evidence), adds the
movements that certainly fall inside the interval, and reaches a closing
position.

- A movement is inside only if its earliest possible date is after the
  opening and its latest on or before the closing. A possible overlap with a
  boundary blocks an exact result; an interval is reported only when the
  bounds justify one.
- The movements must form a disjoint cover: an adjudicated quarterly total can
  stand for the payments it covers, which remain in the account but are not added
  again. Partially overlapping totals with no supported decomposition block
  the reconstruction.
- The closing is exact only when coverage is complete, and completeness is
  itself a reviewed claim: a list of known payments does not prove it.
  Otherwise the account states the subtotal and the coverage gap.
- A residual (reported closing minus reconstructed closing) exists only when
  the two share cutoff, currency, coverage and basis; otherwise both are kept
  with the condition that failed.

Example: a verified zero opening and complete coverage of EUR 15m against an
exact reported closing of EUR 20m give a EUR 5m residual. The same EUR 15m
with unknown completeness gives a subtotal and a gap, not a reconciliation. A
EUR 12m quarterly flow with three payments adjudicated as its components counts
once.

## 8. Knowledge time and change

A result at knowledge cutoff K is computed as follows.

1. Admit the statements and decisions admitted on or before K, and only if
   what they refer to was admitted too.
2. Fold each chain of decisions to its state at K. A revision takes effect
   only once it is itself admitted; a pending revision does not erase an
   accepted decision.
3. Resolve identity, occurrence, coverage and perimeter decisions from that
   set, then apply the account's rules. An unresolved decision that matters to
   a figure blocks that figure, not the others.

When a new cutoff changes a result, the change is attributed to one of: a
development in the world, a late report of an old event, a publisher's
correction, a changed interpretation, a ledger error, or a changed method.
These are different reasons and are never reported as one.

## 9. Cases a method must pass

- A duplicate decision taken in September changes the September result and
  leaves an August result unchanged.
- An uncertain payment across an opening boundary, an unknown opening, partial
  coverage and partially overlapping flows each block exact reconstruction.
- Gross and net, different currencies, and mismatched status or basis fail
  comparison; rounded inputs cannot produce an exact residual.
- A mirror, a reprint or a re-fetch of the same bytes adds no confirmation.
- A programme and its component do not count their money twice; unknown count
  slots never become invented identities.
- A later snapshot restating a value adds a dated confirmation; one stating a
  new value adds a dated statement, and neither alters the earlier one.
- Two sources that disagree both survive an adjudication that selects one.
