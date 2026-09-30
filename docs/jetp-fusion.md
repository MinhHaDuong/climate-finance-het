# JETP information fusion: methods and rules

Status: draft for author review, 2026-09-30.

Information fusion is what turns statements printed by many publishers into
referents, assessments and accounts; the assessments are the occurrence and
preference judgements of sections 4 and 5. The [ontology](jetp-ontology.md) fixes
the words; this document fixes how statements expressed in those words are
combined, weighed and revised. Its rules are conceptual: they hold whether the
statements are kept as RDF triples queried with SPARQL, as sentences of flat
text, or as rows of a table, and whether the result is read on a screen, in a
paper or not at all. How statements are stored is the storage contract's
business; how results are shown is the Observatory's.

A **statement** here is what the ontology calls a line: one publisher's dated
assertion at one locator in one snapshot. An **observation** is a statement
read into a subject, a measure and a value.

In the ODEM frame ([language](jetp-language.md)), identity decisions are the
last step of Data (D4) and accounts are Evidence. Both are methods: each rule below
has a version, and every result names the versions it was computed under.
Several rules describe the target, not what is built today; building them is
tracked outside this document.

## 1. Principles

**Judgement, not automation.** Fusion is done by reading and reasoning:
LLM readers and people, who look at the statements in their
documents and weigh them. No rule below selects a value or merges two things
on its own. The rules say what a judgement must consider, how it is
expressed, and what it must record. Publishers make material errors (a
journalist's misreading, a clerk's mistyped figure), and secondary documents
sometimes contain justified harmonisation (a statistician who corrected a
series, converted units or aligned definitions); only a reader can tell which
is which. [M2]

**Documentary accounting.** The ledger reconstructs from public documents;
it is not a lender's double-entry books. It cannot require debit and credit
counterparts that no document discloses. It can require identities,
comparable scopes, explicit movements and stated differences. An item in a
plan is a statement of intention: it proves neither financing, nor admission
to a later cohort, nor physical progress. [M3b]

**Statements, not facts.** "The loan was signed on 3 May" enters as "this
publisher stated, in this document read on this date, that the loan was
signed on 3 May". Fusion combines statements; it never promotes one to a fact
by erasing the others. [M2]

**Traceable.** Every referent, assessment and account resolves to the
statements it rests on, the judgements that combined them, who or what made
each judgement, by which method and version, when, and on what stated basis.
The full chain is always within reach of the reader of a result. A result
whose chain does not resolve is not a result. [M2 for statements and document judgements; M3b for referents, assessments and accounts]

**Defeasible.** Every judgement can be revised by a later one, which records
what it revises and why. Nothing is revised by erasure: the earlier judgement
stays readable, so a result computed before the revision can be reproduced. [M2]

**Uncertainty accepted.** A value may be a range and a date an interval.
Disagreement between publishers may remain unresolved in a released result, and
no preferred figure is manufactured to fill a gap. Unknown is not zero, and a
missing document is not a missing event: the absence is recorded as such,
with the search that failed to find it. [M2 for ranges and date precision in statements; M3b for results]

**Calibrated language.** Judgements are expressed on the qualitative scales
of the IPCC guidance note on the treatment of uncertainty (Mastrandrea et al.
2010). Likelihood: virtually certain (99–100 %), very likely (90–100 %),
likely (66–100 %), about as likely as not (33–66 %), unlikely (0–33 %), very
unlikely (0–10 %), exceptionally unlikely (0–1 %). Confidence, from the
amount and quality of evidence (the IPCC's words) and the agreement between
readers: very low,
low, medium, high, very high. Each likelihood term is a range, so a judgement
that knows nothing is "about as likely as not, very low confidence", never a
made-up point value. Finer formalisms (possibility, belief functions, lower
and upper probabilities) coincide at this grain and are not needed. [M2]

**Pedigree.** Each statement carries a qualitative assessment of where it
comes from, in the sense of the NUSAP pedigree: how close its publisher is to
the event (the party that did it, the party that paid, a secretariat that
compiled, a statistician who harmonised, a database that aggregated, a
newspaper that reported), how independent it is of other statements, how it
was produced (a register, a plan estimate, a press release), and how it
entered the ledger (parser, assisted reading, transcription, human review).
Pedigree informs judgement; it never deletes a statement. [M3b]

**Independence of publishers.** Two statements corroborate each other only
if they are independent. A mirror, a reprint, a translation, a copied report
or a secondary document quoting a primary one adds no corroboration, and one
payment described by several documents stays one payment. [M3b]

**Two times.** Every conclusion is dated twice: the time of the world it
describes, and the time the ledger knew it. A result at knowledge cutoff K
uses only statements and judgements admitted on or before K, so a later
discovery never changes what an earlier result said. [M2 for the knowledge time of each statement; M3b for results at K]

**Declared method.** A choice that selects, weighs or transforms is a method
with a version. Changing it produces a new result under a new version; it
never silently rewrites an old one. [M2]

**Storage and presentation independence.** No rule depends on how statements
are stored or how results are shown. A rule that only makes sense for one
storage layout or one screen belongs to the storage contract or to the
Observatory, not here. [M2]

## 2. Revision

A publisher's new statement never revises an earlier one. When a later
snapshot of a document prints a different value, that is a new dated
statement beside the old one; whether it records a change in the world, a
late report or the publisher correcting itself is a judgement, which says
which (section 8). When a later snapshot prints the same content again, the
restatement is kept under its own date. It shows that the publisher still
stood by the statement on the later date: persistence, not corroboration,
since a publisher repeating itself is not independent of itself. [M2]

Supersession, where one entry replaces another in force, is reserved for the
ledger's own errors: a misread value, a wrong locator, a false match, an
extraction rule found faulty. The superseded entry stays readable; what is in
force is the end of the chain. A revision that is only proposed does not take
the place of what it would revise until it is itself adopted. [M2]

## 3. Identity

Matching mints a referent from statements, attaches a statement to an
existing referent, or relates a statement to one in another edition. A
referent (project, asset, agreement, party, publisher-stated perimeter)
exists only because a judgement minted it; extracting a document never mints
one. A statement with no referent yet stays a subject of observations in its
own right; it does not dissolve into an aggregate. A recorded judgement is
what the storage contract calls a decision row. [M3b; the document judgements below, M2]

**A candidate match** is one pairing put up for judgement: two statements, a
statement and a referent, two parties, or two documents that may be the
same thing. Every judgement about identity is a judgement on a candidate
match, and each candidate match has its own chain of judgements. [M2]

**The judgement.** A judgement on a candidate match states a stance (the same,
different, or undetermined), its likelihood and confidence on the calibrated
scales, the statements it rests on, a quoted basis, who or what judged (a
program, an LLM reader, a panel, a person), by which method and
version, and when. It is never altered: a later judgement names the one it
revises. A false match is revoked by a later judgement that says so, and
nothing else needs to be created. [M2]

**Threshold per result.** No judgement is turned into a yes or a no when it
is recorded. Each result declares, as part of its method, its match
threshold: which likelihood and confidence a candidate match needs in order
to count, for example "likely or more, medium confidence or more". A result
may report its figures at two thresholds, a cautious and an inclusive one,
which turns matching uncertainty into a range on the figure. Candidate
matches below a result's threshold stay listed and counted apart; they never change the result's figure. [M3b]

- An equality claim (`same_as`) is a justified claim that two things are one; it does
  not choose which name or route prevails. [M2]
- The classification of a referent (project, programme or component) is a
  dated judgement; a later classification does not change what earlier
  statements were about. [M3b]

**Proposers.** Candidate matches come from proposers, each working only on
what the previous ones left open and signing with its own method name.

1. Exact identifier: a register's unique identifier, a plan's ordinal within
   an edition, an operator's project code. Virtually certain.
2. Normalised label: case, diacritics, technology prefixes and units removed
   (PLTU, PLTS, PLTBg; Nhà máy Thuỷ điện; centrale, poste), tokens compared
   within a country and a technology group. Likelihood from the string
   distance and from the agreement of capacity and location where both
   statements give them.
3. Named entities in the label languages (Indonesian, Vietnamese, French,
   English): place, operator, technology and capacity as typed spans, matched
   as tuples. Likelihood from the agreement of the tuples.
4. A reading by LLMs of the remaining candidate matches, given
   both statements and the pages they come from.
5. A person, for what the readers decline or contradict each other on.

A proposer's settings are part of its method version, and are tested against
matches already judged by hand before its judgements are used. [M3b]

**Reading and verification.** The author is not the checker. A reading is
done by independent readers from different vendors, on the same inputs, blind
to each other's answers, choosing from a closed list of options with a quoted
basis and a calibrated likelihood. Positive controls with a known answer run
first, and a reader that misses one is weighted out. A versioned rule turns
the readings into one judgement: the likelihood the readers support, and a
confidence that falls when they disagree. Every candidate match gets a
judgement, with the readers' answers kept beside it; the author examines the
results sorted by likelihood and confidence ("take a stance, keep track of
the confidence level, and let me examine the results sorted by confidence
level"). A judgement that implies a change in what a term means is a proposed
revision of that term, never an edit of the adopted definition. [M4 for the full panel of independent readers with positive controls; until then one reader and one checker from another vendor, as extraction section 6.3 provides]

**Organisations.** Parties are under authority control, as in a library's
name authority file or the ROR and GLEIF registries: one identity per
organisation, every form of its name attached to it, one form preferred.
Three rules of their own apply.

- An external identifier decides: an IATI organisation identifier, a ROR
  identifier, an LEI or a Wikidata item. Two names that carry the same
  identifier are one organisation.
- Forms that differ only by case, diacritics or spacing (Senelec and
  SENELEC) are one party with several name forms, never two parties joined by
  an equality claim.
- Real variants go through judgement: an acronym against its expansion (AFD
  and Agence française de développement, PLN and Perusahaan Listrik Negara),
  a translation (Vietnam Electricity and Tập đoàn Điện lực Việt Nam), a former
  name. In a result whose match threshold the judgement meets, the two parties are
  one organisation carrying both sets of name forms. [M3b]

**Documents.** The same judgements apply one level up, to documents, and come
before any statement is extracted from them, because a duplicate document
extracted twice doubles every statement and every count downstream. One publication
under two addresses or two exports is `same_as`; succession is `edition_of`;
the same publication in another language is `translation_of`. Statements are
extracted from the canonical member of a `same_as` group and from one language of
a translation pair; the other members remain citable. Proposers:

1. Identical bytes under two documents. Virtually certain.
2. Identical text after normalisation, or nearly identical text with the same
   page count: a re-export, or a web page whose timestamp changes on every
   visit.
3. Agreement of title, publisher, publication date, page count and any
   identifier the document prints: a partner's mirror and, with language
   detection, a translation.
4. A reading by LLMs of the remaining pairs, given both first
   pages.
5. A person.

Proposers 1 and 2 are deterministic and run at M2; proposer 3 runs at M2 as
a bounded list of candidate pairs sorted by likelihood, which the author
decides; proposers 4 and 5 start at M3a, with the checking rule of
[extraction](jetp-extraction.md) section 6.3, when discovery brings
mirrors. [M2 for proposers 1 to 3; M3a for proposers 4 and 5]

**Content check before a document judgement.** Before a `translation_of` or
a `same_as` between non-identical documents reaches "likely", the judgement
compares the two documents' content: the multiset of numerals with their
units, dates, percentages and printed identifiers, and the page and table
counts. The comparison is recorded as the quoted basis. Beyond a declared
tolerance the judgement is "different": a re-export that changed a figure
is an `edition_of`, both members are extracted, and the same-publisher rule
of section 5 handles their non-independence. An abridged or revised
translation with a different annex is two documents. [M2]

## 4. Occurrence

Several statements may describe one event. Whether they do is a judgement,
made on the content and never on the order in which statements were extracted or
on the rank of a publisher. [M3b for all]

- Statements of one event not yet judged to be one are not added together.
- A repeated cumulative balance is not a new movement.
- A quarterly total is not split into months unless a statement does so.
- An observed completed state invents neither a commissioning date nor a
  payment.
- Signing, approval and disbursement are different measures, not successive
  states of one chronology.

## 5. Conflicting values

When statements about the same subject, measure and time disagree, all of
them are kept. A judgement may prefer one for a given result; it states why,
and the others stay one step away from the reader of the result. No
preference is ever automatic. [M2 for keeping every statement; M3b for preferences, and for all the rules below]

- The reader first asks whether a statement is a material error: a figure
  that cannot be right against its own document, a transposed digit, a
  journalist's confusion of pledge and disbursement.
- Closeness to the event is the first consideration: the primary document
  nearest to the event carries more weight than one further from it. It is a
  consideration the judgement weighs and records, never a rank that decides.
- A secondary document that records a harmonisation (units converted,
  definitions aligned, a series corrected, as statistical agencies do) may be
  preferred to the primary figure it harmonises, for the purpose it serves,
  when the judgement states why.
- Between two statements by the same publisher, the later one describes the
  publisher's latest position; the earlier one stays, and the judgement says
  whether the change is a correction or a development.
- Two primary documents equally close to the event that disagree stay
  unresolved unless reading finds a reason to prefer one; the result carries
  both.
- Secondary reporting is a lead toward a primary document. It stands as the
  only support of an event only when the recorded search found no primary
  document, and the event is then marked as supported by secondary documents
  only.
- Structured search channels (OECD CRS, IATI) have no precedence of their own. They
  report one to three years late, and that lag is measured, not assumed.
- Where no judgement prefers one statement, a result carries the
  disagreement: both statements, and the condition that stops them from being
  compared (different scope, basis, currency, cutoff or measure).
- Differences between announced, signed, reported and disbursed amounts are
  findings about the gaps between financial states, not conflicts to resolve.

## 6. Perimeters and counting scopes

Counts and sums are made against a population. Two kinds enter fusion
differently.

- **A perimeter** is stated by a publisher: a pledge envelope and its
  revisions, a portfolio, a procurement quota, a plan's list at a cutoff. It
  is a statement like any other, with its publisher and date, and membership
  in it is a justified relation, not a list.
- **A counting scope** is defined by the analysis: a strict JETP scope, an
  extended scope of partner energy finance, a reference pool of comparable
  operations. The strict scope requires explicit JETP attribution in the
  document; the extended scope is reported separately and never fills the
  strict one. A counting scope is a method choice with a version; changing
  its definition makes a new scope, and a count made against the old one is
  never moved silently to the new one. [M3b]

Sharing a perimeter or a scope does not prove comparability: an account also
checks changes in membership, instrument and basis, and unknown compatibility
blocks the comparison without hiding the separate statements. [M3b]

## 7. Counting and accounts

**Counting.** Every count names its unit: statements of a document,
referents of a kind, or a count a publisher stated. There is no default sum
of projects, programmes and components, and a publisher's count of records is
not relabelled a count of assets. Overlapping hierarchies need an explicit
selection before any aggregate, and a hierarchy never splits money: a
project's share needs a statement that gives it. Financial states (need,
announced, memorandum, approved, signed, disbursed) form a chronology, not
additive categories: an aggregate selects one state explicitly. A physical
state never follows from a financial one, and a plan's priority ranking
implies neither finance nor physical progress. [M3b]

**Money.** Values stay the publisher's, in its unit and currency. A
conversion uses a rate that a document printed, cited like any statement; no
rate is assumed and no conversion is implicit. A conversion made by a third
party is kept as its statement and excluded from sums in original currency.
Gross flows are not reduced by refunds, repayments or cancellations, which
remain their own measures. Rounded inputs carry their bounds, and a rounding
difference is not a discrepancy. [M3b]

**Markers.** The climate finance a policy marker yields is the donor's score
times a coefficient that depends on the donor and the year. The coefficient is
a sourced parameter of the account, cited to the document that states it; it
is applied only in the account, so the same loan can move from 40 to 100
percent climate finance without any change in the loan. [M3b]

**Reconstruction.** An account of a subject between two dates starts from an
opening position with an exact cutoff (zero needs a justification), adds the
movements that certainly fall inside the interval, and reaches a closing
position. [M3b for all]

- A movement is inside only if its earliest possible date is after the
  opening and its latest on or before the closing. A possible overlap with a
  boundary blocks an exact result; an interval is reported only when the
  bounds justify one.
- The movements must form a disjoint cover: a quarterly total judged to
  cover some payments can stand for them, and they remain in the account but
  are not added again. Partially overlapping totals with no supported
  decomposition block the reconstruction.
- The closing is exact only when coverage is complete, and completeness is
  itself a judgement: a list of known payments does not prove it. Otherwise
  the account states the subtotal and the coverage gap.
- A residual (reported closing minus reconstructed closing) exists only when
  the two share cutoff, currency, coverage and basis; otherwise both are kept
  with the condition that failed.

Example: a verified zero opening and complete coverage of EUR 15m against an
exact reported closing of EUR 20m give a EUR 5m residual. The same EUR 15m
with unknown completeness gives a subtotal and a gap, not a residual. A
EUR 12m quarterly flow with three payments judged to be its components counts
once.

## 8. Knowledge time and change

A result at knowledge cutoff K is computed as follows. [M3b]

1. Admit the statements and judgements admitted on or before K, and only if
   what they refer to was admitted too.
2. Take each chain of judgements to its state at K. A revision takes effect
   only once it is itself admitted and adopted; a proposed revision leaves
   the judgement it would revise in place.
3. Apply the result's declared match thresholds to identity, occurrence, coverage and
   scope judgements, then the account's rules. An open question that matters
   to a figure blocks that figure, not the others.

When a new cutoff changes a result, the change is attributed to one of: a
development in the world, a late report of an old event, a publisher's
correction, a changed interpretation, a ledger error, or a changed method.
These are different reasons and are never reported as one. [M4]

## 9. Checks a method must pass

Each check is a small constructed situation and the outcome a correct method
produces. A method that gives another outcome is wrong, whatever else it does
well.

| Situation | Correct outcome |
|---|---|
| Two statements are judged to describe one payment on 10 September. | A result at knowledge cutoff 1 September still counts two; a result at 30 September counts one. |
| The opening position is unknown, or a payment may fall on either side of the opening date. | No exact closing position; a subtotal and a stated gap instead. |
| Two quarterly totals overlap in part and no document splits them. | No reconstruction for that interval. |
| One figure is gross and the other net, or they are in different currencies. | No comparison and no residual; both figures kept with the reason. |
| Inputs are rounded to the million. | The residual carries the rounding bounds; a difference within them is not a discrepancy. |
| The same report is found under two addresses, or fetched twice. | One document, one set of statements, no added corroboration. |
| A programme and its component both carry the same loan. | The loan is counted once. |
| A publisher gives a count of 24 projects and names 3. | Three referents and one stated count of 24; no invented referents for the other 21. |
| A later snapshot of a page prints the same value. | A dated restatement: the publisher still stood by the value, with no added corroboration. |
| A later snapshot prints a different value. | A new dated statement beside the old one, and a judgement on whether it is a correction or a development. |
| Two primary documents disagree and a judgement prefers one. | The other remains, with the stated reason for the preference. |
| A candidate match is judged "about as likely as not". | It counts in no result whose match threshold is "likely" or stricter, and it stays listed. |
| An accepted match has a later revision that is only proposed. | The accepted match stays in force and counts; the proposal is listed as pending until it is itself accepted or rejected. |
| A match accepted before cutoff K is superseded by a judgement admitted after K. | A result at K counts the accepted match; a result at a later cutoff applies the revision. |
