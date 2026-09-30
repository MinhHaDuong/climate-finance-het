# JETP information fusion: methods and rules

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
low, medium, high, very high. Each likelihood term is a range, never a
made-up point value, and a reader who knows nothing abstains (the stance
`undetermined`, section 3) rather than stating "about as likely as not".
For calibration, a term stands for its range less the ranges of the
stronger terms beside it (likely 66–90 %, very likely 90–99 %), so the bins
are disjoint; the words shown stay the IPCC's. Finer formalisms (possibility, belief functions, lower and upper
probabilities) coincide at this grain and are not needed. [M2]

**Calibration.** The verbal terms mean something only once measured. For
each method version, the observed precision of each likelihood term is
measured on held-out reference answers made blind to the machine readings
(extraction section 6.3; for matching, the matches decided by hand of the
storage contract, section 4), and published with the method version; a result translates its threshold into an expected error
from those observed rates. [M2]

**Pedigree.** Pedigree, in the sense of NUSAP, is not a stored score. It is
what a judgement reads from what the ledger already records about a
statement: its publisher's authority category (how close the publisher is to
the event: the party that did it, the party that paid, a secretariat that
compiled, a statistician who harmonised, a database that aggregated, a
newspaper that reported), its document type (a register, a plan estimate, a
press release), its extraction method (parser, assisted reading,
transcription, a person's reading), and the relations that fold copies. A
judgement records, in its basis, which of these it weighed. Pedigree informs
judgement; it never deletes a statement. [M3b]

**Independence of publishers.** Two statements corroborate each other only
if they are independent. Two statements are independent supports when, after
folding the documents related by `same_as` and `translation_of` and the
statements related by a citation, they have different publishers. A mirror,
a reprint, a translation, a copied report or a secondary document quoting a
primary one adds no corroboration, and one payment described by several
documents stays one payment. Copying that no relation records is not
detected, and the rule does not claim to exclude it. Counts of independent
supports are published from M4, or at M3b if the comparison of requirement
F19 needs them. [M3b]

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

The judgement on a change between two statements of one publisher is a
revision judgement: its members are the earlier and the later statement,
and its verdict is a development in the world, a late report, a correction
by the publisher, or a rounded restatement. A judgement that prefers one
statement over others for a result (section 5) is a preference judgement:
its members are the candidates, the one preferred and the ones excluded, and
its verdict names the reason. Both are recorded from M3b, so that the change
between releases can later be attributed to a reason (section 8). A
publisher's correction notice, when one is first met, is related to the
statement it corrects by a citation whose role says so; no document type or
status is added for errata before a case needs one. [M3b]

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
version, and when. The likelihood is one judged quantity, always that of the
positive proposition (the two are the same): "different, very likely" is
recorded as a likelihood of sameness of "very unlikely", and the stance
follows from it. `undetermined` is an abstention: it carries no likelihood
and counts in no result. Confidence is the quality of the evidence and the
agreement between readers. A judgement is never altered: a later judgement names the one it
revises. A false match is revoked by a later judgement that says so, and
nothing else needs to be created. [M2]

**Threshold per result.** No judgement is turned into a yes or a no when it
is recorded. Each result declares, as part of its method, its match
threshold: which likelihood and confidence a candidate match needs in order
to count, a conjunction of a likelihood of sameness at or above a term and a
confidence at or above a level, for example "likely or more, medium
confidence or more". A result
may report its figures at two thresholds, a cautious and an inclusive one,
which turns matching uncertainty into a range on the figure. Candidate
matches below a result's threshold stay listed and counted apart; they never change the result's figure. The default inclusive threshold requires low confidence or more, so a judgement made on no evidence never counts (results § 3). [M3b]

**Matching scope.** Only statements that feed a declared result are
matched. Candidates are generated by deterministic blocking (country,
technology, capacity) and only the top candidates per statement, a number
declared by the method, are judged; the rest are listed, not counted, as
for candidates below a threshold. The judgements run on the two local
readers, with a hosted arbiter on escalation only
([operation](jetp-operation.md) section 5). [M3b]

**Referents at a threshold.** Matching is pairwise, and a result needs
clusters. At a result's threshold, the members of a referent are the
statements whose in-force attachment to it meets the threshold, and two
referents joined by an in-force `same_as` that meets it are one. Equality
between referents is bounded to depth one: the source of an accepted
`same_as` is never the target of another, so a chain of three (A same as B,
B same as C) is raised as a conflict, which the panel resolves by judging
A against C, never closed by transitivity. A rejected `same_as` between two
members of one would-be cluster is such a conflict too. The reason is that
a `same_as` judgement is pairwise evidence, not an equivalence: likelihoods
do not compose along a chain, so "A same as B" and "B same as C", each
likely, say nothing calibrated about A and C. [M3b]

- An equality claim (`same_as`) is a justified claim that two things are one; it does
  not choose which name or route prevails. [M2]
- The classification of a referent (project, programme or component) is a
  dated judgement; a later classification does not change what earlier
  statements were about. [M3b]

**Proposers.** Candidate matches come from proposers, each working only on
what the previous ones left open and signing with its own method name.

1. Exact identifier: a register's unique identifier, a plan's ordinal within
   an edition, an operator's project code. Virtually certain for a
   register's unique identifier; a plan ordinal or an operator's code,
   which publishers leave with gaps, repeat and reuse (extraction section
   3), is virtually certain only when the countries agree and one other
   attribute corroborates it (capacity, location or technology), and very
   likely otherwise.
2. Normalised label: case, diacritics, technology prefixes and units removed
   (PLTU, PLTS, PLTBg; Nhà máy Thuỷ điện; centrale, poste), tokens compared
   within a country and a technology group. Likelihood from the string
   distance and from the agreement of capacity and location where both
   statements give them.
3. Named entities in the label languages (Indonesian, Vietnamese, French,
   English): place, operator, technology and capacity as typed spans, matched
   as tuples. Likelihood from the agreement of the tuples.
4. A reading by two LLM readers of the remaining candidate matches, given
   both statements and the pages they come from.
5. The arbiter, a stronger LLM given both readings and the pages, for what
   the readers contradict each other on or hold below the acceptance level
   (extraction section 14).

A proposer's settings are part of its method version, and are tested against
matches already judged by hand before its judgements are used. Each method
version publishes, on the hand-judged set, its blocking recall (the share of
true pairs that the proposers put up at all), its pairwise precision and
recall, and one cluster metric, B-cubed precision and recall. [M3b]

**Judgement by adopted rule.** A program records an accepted judgement only
under a rule the author adopted, by version, in a recorded decision: identical
bytes, the same identifier of a declared scheme (Organisations, below), a
case or diacritic variant of one name. Such a rule is the author's judgement applied by a program, and its
rows name the rule as their method. Every other proposal, by a program or an
LLM, is recorded as a candidate match until the judgement protocol of
[extraction](jetp-extraction.md) section 6.3 accepts it, or the author,
when he chooses to, decides it. This
is how the first principle ("no rule below selects a value or merges two
things on its own") and the proposers above hold together. [M2]

**Who decides what.** Every decision of the Observer falls under one row
of this table, which is the one statement of decision authority;
requirement N4 cites it.

| Decision | Decided by | In force when | What downstream accepts | Reversed by |
|---|---|---|---|---|
| Identical bytes; the same identifier of a declared scheme (Organisations, below); a case or diacritic variant of one name | a program applying a rule the author adopted by version | recorded as accepted under that rule | every result, whatever its threshold | a later judgement of the panel or of the author, or a new version of the rule |
| A statement or disposition made by a parser, an ingestion run or a rule of the method (a pairing on a publisher's stable key across snapshots of one document; a disposition the register, the adapter or an earlier judgement determines) | the program, under its method version, merged through the code gate of operation section 4 | merged | every result | a new method version, or a supersession for a ledger error |
| A statement admitted or rejected by reading; a disposition `out_of_scope` or `no_extractable_content`; a document identity beyond the adopted rules; a triage outcome; a document's class | the panel: two readers, the arbiter on escalation (extraction section 6.3) | its final stance, admitted or accepted | an admitted statement, by every result; a document judgement, before extraction | a later judgement of the panel or of the author, naming the one it revises |
| A match, an occurrence, a coverage, a compatibility, a revision, a preference | the panel | accepted, with its likelihood and confidence | a result, only at or above its declared match threshold | as above |
| A new line classification, a new term or a changed meaning, a new disposition kind | the author, on the panel's proposal and its stance | adopted, as a new method or ontology version | runs under that version and after | a later decision of the author |
| The collection protocol, the recall estimate and the freeze; the publication of a release | the author | recorded in the collection report or in the release's descriptor | M3b; the products that cite the release | a recorded revision of the protocol; a correction release |
| Any item the author chooses to decide | the author, as a reading of the role *author* | recorded beside the machine readings, superseding the judgement it revises | as for the judgement it supersedes | a later judgement |

[M2 for the adopted rules, statements, dispositions, document judgements
and the author's rows; M3a for triage and classes; M3b for the other
judgements]

**Reading and verification.** The author is not the checker, and no
machine judgement is routed to him. A judgement is read under the protocol
of [extraction](jetp-extraction.md) section 6.3: two readers of different
model families, blind to each other, the arbiter on what they leave open or
hold below the acceptance level, and the calibration and versioned rule
that turn the readings into one judgement. Every candidate match gets a
judgement, with every reading kept beside it. Judgements are served
undetermined first, then by ascending confidence, then by ascending
likelihood ("let me examine the results sorted by confidence level"). A
decision the author makes is a reading of the role *author*. Only a
question that changes what a term or the contract means goes to him, with
the panel's stance, as a proposed revision of that term. [M2]

**Organisations.** Parties are under authority control, as in a library's
name authority file or the ROR and GLEIF registries: one identity per
organisation, every form of its name attached to it, one form preferred.
Three rules of their own apply.

- An external identifier decides when its scheme is declared, in the
  method version, as naming exactly one organisation at the grain of a
  party: an IATI organisation identifier, a ROR identifier, the LEI of a
  legal entity, a Wikidata item for an organisation. Two names that carry
  the same identifier of a declared scheme are one organisation. A code
  that can name a branch, a programme or a group of entities (an IATI
  identifier reused for an umbrella programme, an LEI of a branch) is a
  strong proposer, judged like any candidate match, never a decision.
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
4. A reading by two LLM readers of the remaining pairs, given both first
   pages.
5. The arbiter, for what the readers leave open.

Proposers 1 and 2 are deterministic and run at M2; proposer 3 runs at M2 as
a bounded list of candidate pairs, which the panel judges under the
protocol of [extraction](jetp-extraction.md) section 6.3; proposers 4 and
5, which read the pairs beyond that list, start at M3a, when discovery
brings mirrors. [M2 for proposers 1 to 3; M3a for proposers 4 and 5]

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
- An occurrence is never inferred from a state change: an observed later
  state implies no earlier one and no payment.

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
- The **matching coverage rate** is the share of a result's operations that
  have an accepted match to a CRS or IATI record at the result's match
  threshold, reported per country and funder; it is distinct from the
  tracker traceability rate of discovery (collection section 7).
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
project's share needs a statement that gives it. Financial states form a
chronology, not additive categories: in the terms of the
[ontology](jetp-ontology.md) (section 4), a need (a plan's estimate or an
envelope), then the agreement states of the money axis (announced, a
memorandum of understanding, approved, signed), then the flows of the IATI
list (commitment, disbursement, expenditure); an amount *reported* is the
amount a comparator record (CRS or IATI) reports for the same operation. An
aggregate selects one state explicitly. A physical
state never follows from a financial one, and a plan's priority ranking
implies neither finance nor physical progress. [M3b]

**Money.** Values stay the publisher's, in its unit and currency. A
conversion uses a rate that a document printed, cited like any statement; no
rate is assumed and no conversion is implicit. A conversion made by a third
party is kept as its statement and excluded from sums in original currency.
Since few documents print a rate, a total across currencies is often
impossible; a result then reports one figure per currency rather than
converting.
Gross flows are not reduced by refunds, repayments or cancellations, which
remain their own measures. Rounded inputs carry their bounds, and a rounding
difference is not a discrepancy. [M3b]

**Markers.** The climate finance a policy marker yields is the donor's score
times a coefficient that depends on the donor and the year. The coefficient is
a sourced parameter of the account, cited to the document that states it; it
is applied only in the account, so the same loan can move from 40 to 100
percent climate finance without any change in the loan. [M4, or M3b if the
comparison of requirement F19 uses CRS climate-marked amounts]

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
- An account that reaches no exact closing, or no residual, names its
  cause from one list: totals that overlap in part with no supported
  decomposition; an opening position unknown or with an open bound; a
  movement whose interval straddles a boundary; coverage not judged
  complete; a cutoff, currency, coverage or basis that differs between the
  reported and the reconstructed closing. A result counts its accounts per
  cause, so that what blocks the reconstruction is itself a finding.
- A figure printed as cumulative or "to date" is a closing-position
  candidate, never a movement: it is read as a flow over an interval whose
  end is its as-of date and whose start is unknown (extraction section 11),
  so successive snapshots of it are successive positions and are never
  added.

**Timelines.** A timeline is Evidence, built from observations and their
timings. An event stated without a date of its own gets an upper bound equal
to the report date or reporting cutoff of the statement that reports it, and
an open lower bound: a milestone known only from a report is an interval
ending at that report, never a day. [M3b]

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

A correction of a result keeps its cutoff K. It adds a named correction
overlay: the revisions admitted after K that correct ledger errors in
entries admitted on or before K. The state is the one at K with those
revisions applied, and nothing else admitted after K; a later discovery
never enters through an overlay. [M3b]

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
| An agreement is observed as signed, and no document states its approval or any disbursement. | No approval and no disbursement is inferred; a count of approved agreements does not include it unless a statement says it was approved. |
| A project page prints "disbursed to date: USD 40 million" in two successive snapshots, then USD 55 million. | Three closing-position candidates at three as-of dates; no movement of 95 million, and a movement of 15 million only if an account judges the two positions comparable. |
| A report of March 2026 says a plant was commissioned, without a date. | The commissioning is an interval with an open start ending in March 2026, not a day. |
| An accepted match has a later revision that is only proposed. | The accepted match stays in force and counts; the proposal is listed as pending until it is itself accepted or rejected. |
| A match accepted before cutoff K is superseded by a judgement admitted after K. | A result at K counts the accepted match; a result at a later cutoff applies the revision. |
| A partner announces its withdrawal from a partnership. | The announcement is a statement read as a dated event; the partner's `party_in` rows end at the date it gives, by later judgements that close them and cite the statement. Nothing earlier is deleted: a result at an earlier cutoff still shows the partner's role and the amounts it had stated. |
