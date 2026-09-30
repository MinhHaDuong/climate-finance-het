# JETP extraction: how statements are read from documents

Status: draft for author review.

Extraction turns the bytes of a held document into statements. The
[ontology](jetp-ontology.md) fixes what a statement (the ontology's line) is;
the [fusion rules](jetp-fusion.md) fix how statements are combined once read.
This document fixes how they are read: what a statement must carry when it
leaves extraction, which methods may produce it, what happens to a document
that yields none, how a run is shown to be correct, and how a statement is
then read into observations.

Its rules are conceptual. They hold whether statements are kept as RDF
triples, as sentences of flat text or as rows; how they are stored is the
[storage contract](jetp-ledger-storage.md), and how they are shown is the
[observatory](jetp-observatory-presentation.md). Words follow the
[language](jetp-language.md) document: a statement's documentary support is
its justification, a language model is an LLM, and the ledger's own output is
a release.

Every rule carries, in square brackets, the milestone that needs it: M2 (an
extraction pipeline that works on every document held), M3a (discovery to a
cutoff, then the registry frozen), M3b (the new documents extracted,
reconciled and released), M4 (operation), or later. A rule tagged after M2 is
not built before its milestone.

## 1. Principles

**Read, do not interpret.** Extraction records what the publisher printed, as
printed: the label in its language, the status word in the publisher's
vocabulary, the number with its printed unit and scale. Conversion,
normalisation, crosswalking and matching come later, each as its own step
with its own method. A reader who is unsure writes unknown; a guess is never
recorded as a reading. [M2]

**Traceable to bytes.** Every statement resolves to one snapshot and one
place in it, so that anyone holding the bytes can find the text it rests on.
A statement whose place cannot be found again in its snapshot is not a
statement. [M2]

**Every held document accounted for.** A run ends with statements or a
recorded disposition for every document the ledger holds. Silence is never an
outcome. [M2]

**Complete within a declared scope.** A reading states in advance which parts
of a document it covers. Inside that scope every item is read; outside it
nothing is, and the scope stays on record so that a later reading can extend
it. [M2]

**Append only.** A reading adds statements. It never edits, deletes or
renumbers an earlier one. The ledger's own errors are corrected by
supersession ([fusion](jetp-fusion.md), section 2), and the superseded
statement stays readable. [M2]

**Declared method.** Every statement names the method and version that read
it: a parser, an assisted reading, a transcription or a person. Changing a
method makes a new version, and its effect on earlier output is reviewed
before it is adopted. [M2]

**Reproduced where possible, reviewed where not.** A parser is checked by
running it again and comparing. An LLM read cannot be reproduced byte for
byte, so its checked output is the record and its checks are of another
kind (section 6.3 and section 10). [M2]

**Reading mints nothing.** Extraction produces statements and dispositions.
It mints no project, asset, agreement, perimeter or party, and it decides no
match. A parser may propose a pairing it can see, such as a publisher's own
key repeated across editions, but the proposal is a candidate match of the
[fusion rules](jetp-fusion.md) (section 3), signed with the parser's method.
The one exception is the party that publishes a document, which the document
register already names. [M2]

**Built from cases.** A parser is written for a publisher's repeated format
once two or three of its documents are in hand, and generalised only when a
second series needs the same logic. No general framework is written ahead of
the cases it would serve. [M2]

## 2. Scope and preconditions

Extraction receives a held document with at least one snapshot, and returns
statements citing that snapshot or a disposition. It does not fetch
anything: acquisition, retries and the choice of what to collect belong to
the collection specification. Reading statements into observations is a
later step with its own rules (section 11). [M2]

Three things are settled before any statement is read.

- **Document deduplication.** A duplicate read twice doubles every statement
  and every count downstream, so the document judgements of
  [fusion](jetp-fusion.md) section 3 (`same_as`, `edition_of`,
  `translation_of`) are made first. Statements are read from the canonical
  member of a `same_as` group and from one language of a translation pair.
  Extraction applies the outcome; it does not restate the proposers. If a
  document judgement is later revoked, the document it had folded becomes
  pending again and is read like any other. [M2]
- **Canonical member.** In a `same_as` group, the member already read stays
  canonical, so that no statement moves; when none has been read, the
  publisher's own address is canonical over a mirror. [M2]
- **Language read in a translation pair.** The version the publisher
  designates as authoritative is read; failing that, the member already
  read; failing that, the version in the country's official language, whose
  labels match other national sources best. [M2]
- **Language.** The document's language is recorded, because the translation
  rule needs it and because the readers and checkers must handle that
  language. [M2]
- **Edition.** A document that is a later edition of one already read is its
  own document, related by `edition_of`. Its statements are new statements
  of the new document; they are never merged into the earlier edition's.
  [M2]

The input of every run is the pending list: the snapshots of held documents
that have neither statements nor a disposition. A backlog run and a later
periodic run start from the same list and use the same pipeline. [M2]

## 3. What a statement carries

A statement leaving extraction carries the following, and nothing else is
required of it at this step.

- **Country**: the recipient country the statement is about, or none for a
  statement about no recipient country (a donor's method note). [M2]
- **Snapshot**: the fingerprint of the exact bytes read. Never a web address
  and never a retrieval. [M2]
- **Locator**: the place of the assertion in those bytes, precise enough to
  be unique within the snapshot and never the whole document. Its syntax per
  format is fixed by the storage contract; its meaning is fixed in section 5.
  [M2]
- **Ordinal**: the statement's position within its sequence in the snapshot,
  in reading order, counted from one. A number the publisher prints beside
  the item is a verbatim field and may differ from the ordinal (gaps,
  repeats, restarts). [M2]
- **Label as printed**: the item's name or description in the publisher's
  language and spelling, with whitespace joined but no other change. [M2]
- **Classification**: one value from the closed list of the
  [ontology](jetp-ontology.md) (section 4): `named_item`, `unnamed_item`,
  `quota`, `heading`, `submission`, `evaluation`, `register_allocation`,
  `count`, `envelope`, `absence`. It is assigned by the reading from what the
  publisher presents, never inferred from words in the label. When the
  reading cannot tell, the statement waits for review rather than taking a
  default. [M2]
- **The publisher's own status word**, copied as printed, and the axis it
  belongs to, when the publisher prints one. The shared status is never
  assigned here; it lives only in the crosswalk. [M2]
- **The publisher's own sector word**, copied as printed, when there is one.
  [M2]
- **Group**: the heading statement that governs it, when one does (a
  programme heading, a method note, a section title that conditions every
  item under it). The heading is a statement of the same snapshot. [M2]
- **Verbatim fields**: everything else the publisher printed for the item,
  field by field, under the publisher's own field names as printed. The list
  of field names is declared once per document at reading, and every
  statement of that document conforms to it. A value keeps its printed form:
  "3.92" under a heading "USD billion" stays 3.92 with the heading, and a
  cell naming several funders stays one cell. [M2]
- **Method and version** that read it, and, for an assisted reading or a
  transcription, the checking reader and any person who decided on it
  (section 6.3). [M2]
- **Recorded date**: when the ledger admitted the statement. This is the
  knowledge time of [fusion](jetp-fusion.md) section 8. The world time a
  statement speaks of (a reporting cutoff, a publication date) is read later
  into timings (section 11); the date the ledger first held the bytes is the earliest
  retrieval that yielded the snapshot. [M2]

## 4. What becomes a statement

One statement is one assertion at one place. The following rules settle the
cases that recur in the documents held. [M2 for all]

- An item of a list (a project of a plan appendix, a grant of a register, a
  submission of an annex) is one statement.
- A heading that groups items is a statement of classification `heading`,
  and the items it governs name it as their group.
- A method note that conditions a page or a list (a pro-rating, an exchange
  rate policy, a footnote on every row) is a heading statement grouping what
  it conditions, so that a later reading of any item sees the note.
- A count the publisher gives without naming what is counted is one
  statement of classification `count`. A count of 24 with three items named
  gives three item statements and one count statement; nothing is invented
  for the other 21.
- An item that runs over a page break is one statement whose locator spans
  both pages.
- The same value printed in three places (a headline, a list, a caption) is
  three statements when all three places are in scope. Relating them is a
  judgement of fusion, not a merge at reading.
- Prose is read when it asserts something in scope: a signature, an approval,
  an amount, a date, a state. Each assertion is one statement anchored on its
  own words, attributed to its speaker when the publisher quotes someone.
- Navigation, boilerplate, legal notices, contents pages and repeated
  page furniture are out of scope unless the reading declares otherwise.

**Declared scope.** Before reading, the reading names the parts of the
document it covers (an appendix, the list of submissions, the body of a news
item) and states why the rest is out of scope. Relevance is judged against
the purpose of the ledger: statements about the partnerships' projects,
money, perimeters, parties and states. A reading may stop short of a whole
document; it may not stop short of a whole part it declared. [M2]

**Printed totals as controls.** Where the document prints how many items a
part holds, or a total the items should sum to, the reading compares and
fails when they disagree. The disagreement is resolved by reading again, or
recorded as the publisher's own inconsistency with both figures kept. [M2]

## 5. Text layers by format

A text layer is what a method reads when it does not read the bytes
directly: characters with their positions, cells, records. It is derived
from the snapshot, regenerable, and never the record. Each text layer names
the snapshot it came from and the adapter and version that produced it; a
locator resolves against the stored bytes through a named adapter version.
A text layer may be kept to save time, keyed by snapshot and adapter
version, and is discarded when either changes. [M2]

The declared content type of a retrieval is a hint. The format is decided
from the bytes, so an object served as a generic byte stream that is in fact
a PDF is read as a PDF, and the declared type stays on the retrieval as
received. [M2]

- **HTML.** The stored markup, parsed without running its scripts. A locator
  is a selector within the parsed markup or a text anchor, never a byte
  offset. What a browser would have loaded afterwards is not in the bytes
  and is not read; a page whose data arrives by script is a shell unless the
  data is inline (below). A capture of the rendered page is a separate
  snapshot, and collecting one is collection's business. [M2]
- **PDF with a text layer.** The decoded characters with their page and
  position. Decoding is not a facsimile: ligatures, rotated pages, wrapped
  cells and reading order are reconstructed by the adapter, and the adapter
  version is part of every statement's provenance. A locator gives the page
  index in the bytes and the folio the publisher printed, when there is one,
  then the position in a grid or a text anchor of a few words. [M2]
- **PDF without a text layer, and images.** Read only by transcription
  (section 6.4). A machine-recognised text is a text layer like any other,
  named by its recogniser and version, and it is checked as in section 6.3
  before a statement rests on it. [M2 for the documents held that need it; the method may be a
  person's transcription]
- **Values shown only in a chart**, with no byte of text behind them, are out
  of scope until transcribed with provenance, as the ontology states (section
  6). A reading that meets one records it in its scope note so the gap is
  visible. [M2 for the note; transcription of charts later]
- **Spreadsheets.** The cell values as stored by the publisher, sheet by
  sheet. Formulas are not re-evaluated; a cell's stored value is what the
  publisher showed. A locator names the sheet and the cell or range. Hidden
  sheets, rows and cells are read like visible ones, and each statement read
  from them records that it was hidden, since a publisher who hid a row
  still published it. [M2]
- **JSON and other structured records.** Each record is read under its own
  key. A locator is the publisher's record identifier (a register code, an
  activity identifier, an SDMX key), and the record's fields are the
  verbatim fields. [M2 for the documents held; the comparator channels of
  CRS and IATI, M3b]
- **Scripts.** Data embedded as a literal inside a script (an array behind a
  dashboard) is read as a structured record from the literal. A script is
  never executed to obtain data. [M2]
- **Corrupt or empty bytes** yield a disposition (section 7), never a crash
  of the run. [M2]

## 6. Reading methods

Four methods produce statements. Each signs what it reads with its name and
version, and each has its own check of correctness. [M2 for all four]

### 6.1 A parser per repeated series

Where a publisher repeats one format (a quarterly progress update, a monthly
register, the appendices of successive plans), one purpose-built parser reads
the whole series. The parser is the artifact under review; its output is
reviewed as a difference against what was there before.

- A parser declares which snapshots it can read and refuses others: it checks
  the fingerprint of a document it was written for, or the landmarks of the
  layout it expects, and stops when they are absent. It never guesses its
  way through an unfamiliar layout. [M2]
- It uses the printed totals and part boundaries as controls (section 4) and
  fails the whole document when a control fails. No partial set of
  statements is admitted from a failed reading. [M2]
- It assigns classifications from the publisher's own presentation or from a
  reviewed list of items, and leaves a statement unclassified for review
  rather than choosing a value it cannot justify. [M2]
- A new parser version is run over every snapshot the previous version read
  before it is adopted, and the difference is reviewed under the rules of
  section 9. [M2]

### 6.2 Structured sources read in bulk

A data portal or an export that holds many records in a stable structure is
read by an ingestion run. The run states the snapshot, the number of records
read, the declared fields and the counts it rejected, and the reviewer
reviews that statement of the run rather than each record. A bulk statement
is examined individually when an observation first cites it. Before a
portal is read, its snapshot is inspected and given a verdict: it holds
data, it is a shell around a service, or it holds nothing to read. [M2 for
the portals held; the comparator channels, M3b]

### 6.3 Assisted reading of one-off documents

Where no series justifies a parser (a single investment plan, an approval
document, a project page, a news item), an LLM reads and a second LLM from
another vendor checks every row. The checked statements are the record.

- The reader is given the document's text layer, the declared scope and the
  declared field list, and proposes statements with a label, a locator that
  identifies the assertion, a classification and the verbatim fields. [M2]
- Every proposed locator is checked automatically against the stored bytes:
  it must resolve, and the text there must contain the proposed label and
  values. A proposal that fails is rejected before any further check, and
  the rejection is recorded. [M2]
- A checker, an LLM from a vendor other than the reader's, examines every
  surviving proposal against the document, in the document's language,
  whatever that language is. For each it states whether the proposal is
  right, with a likelihood and a confidence on the calibrated scales of
  [fusion](jetp-fusion.md) section 1, and a quoted basis. It also lists
  items of the declared scope that the reader missed. [M2]
- The author sees only the proposals on which reader and checker disagree,
  the items the checker says were missed, and a random sample of the
  proposals they agree on, all sorted by likelihood and confidence. The
  author accepts, corrects or rejects each. A proposal both readers agree on
  and the author does not overturn is admitted. A rejected proposal is
  recorded with its reason, never dropped. [M2]
- The method records, for reader and checker, the model identifier, the
  prompt version and, where the service allows, the sampling settings; the
  checker's stance and any decision by the author are recorded on every
  admitted statement. [M2]
- Each run states its budget for the author's attention: the number of
  disagreements and the size of the random sample it will present. A
  document that would exceed it is split into parts with their own scope, or
  deferred with that reason (section 7); it is never admitted unchecked.
  [M2]
- Before the method is used on held documents it passes a test: a document
  with a planted item that must be found and a named absent item that must
  not be invented (section 12). [M2]
- The full panel of [fusion](jetp-fusion.md) section 3 replaces the single
  checker: independent readers from different vendors reading blind, with
  positive controls run first and a reader that misses one weighted out.
  [M4]

### 6.4 Transcription

A scan, an image or a chart is read by transcription: a person, or a
recogniser whose output is checked as in section 6.3. Each transcribed statement names
the transcription as its method and version, and its locator gives the page
and the region transcribed. A transcribed label has the same standing as a
printed one once checked; its pedigree says it was transcribed. [M2 for the
held documents that need it]

A person may also read a document directly, without a proposing method. The
statement then names the person as its method, and the same automatic
check of locators applies. [M2]

## 7. Dispositions

Every held document ends with statements or a disposition, and every
snapshot of a document that is read ends with statements or a disposition of
its own. A disposition is a record, like a judgement: it names its kind, its
reason in words, who or what decided it, by which method and version, and
when. It is revised by a later disposition that names it, never erased. [M2]

The kinds, closed and grown only by decision:

| Kind | Applies to | Meaning |
|---|---|---|
| `duplicate` | document | a non-canonical member of a `same_as` group; its statements are those of the canonical member, and its snapshots stay citable |
| `translation_not_canonical` | document | the member of a translation pair that is not read |
| `no_snapshot` | document | the ledger holds no bytes for it; collection owns the gap |
| `wrong_content` | snapshot | the bytes are not the document (an error page, a login wall, a consent screen), which is handed back to collection |
| `unreadable` | snapshot | corrupt, truncated or in a format no adapter handles, with the format named |
| `no_extractable_content` | snapshot | readable, but nothing in scope is stated in text: a shell around a service, a page of links, a chart with no text behind it; the reason says which |
| `out_of_scope` | document | held for context, and nothing in it concerns the partnerships' projects, money, perimeters, parties or states |
| `deferred` | snapshot | held and in scope, not read yet; names the milestone it waits for and why (a scan awaiting transcription, a review budget exceeded) |

A snapshot that is byte-identical to one already read is not a new snapshot
and needs neither statements nor a disposition (section 8). [M2]

A `deferred` disposition closes a document for the purpose of a run's
completeness, but a run reports the deferred documents apart, by country and
type, and a milestone's acceptance names them. [M2]

## 8. Dated snapshots and restatements

A document may be fetched many times, and a living document (a project page,
a register) changes between fetches. The rules below apply
[fusion](jetp-fusion.md) section 2 at the moment of reading.

- **Identical bytes.** A later retrieval that returns the same bytes shares
  the earlier snapshot. Nothing is read again. The later retrieval date is
  itself the dated evidence that the publisher still printed every statement
  of that snapshot on that date. [M2]
- **New bytes.** A later retrieval that returns different bytes forms a new
  snapshot, which is read in full, as if for the first time, under the same
  declared scope. Its statements cite the new snapshot. The statements of
  earlier snapshots are not touched. [M2]
- **Restatement.** A statement of the new snapshot whose item and verbatim
  content match a statement of an earlier snapshot of the same document is a
  restatement. It is kept, under its own snapshot, and linked to the earlier
  statement, so the ledger can answer every date on which a content was
  printed. A restatement is persistence, not corroboration. [M2]
- **Change.** A statement of the new snapshot whose item matches an earlier
  one but whose content differs is a new statement beside the old one.
  Whether it is a development, a late report or a correction is a judgement
  of fusion, made later. [M2]
- **Pairing across snapshots.** Deciding that two statements of two
  snapshots are the same item is a candidate match. When the publisher
  prints a stable key (a register code, a plan's ordinal within an
  unchanged appendix), the parser proposes the pairing on the key and it is
  virtually certain. Otherwise pairing goes through the proposers of
  [fusion](jetp-fusion.md) section 3. Content is compared field by field
  on the verbatim fields after whitespace is joined; any other difference
  is a change. [M2 for key-based pairing; M4 for pairing without a key
  across the periodic harvest]
- **Absence.** An item of an earlier snapshot with no counterpart in the new
  one is recorded as unpaired. No statement is invented for it, and its
  absence is not read as a cancellation; that too is a judgement of fusion.
  [M2]

## 9. Identifiers and corrections

- A statement's identifier is minted when it is admitted and is independent
  of its attributes. It is never reused and never renumbered, whatever
  happens to the reading method. [M2]
- A new snapshot's statements get new identifiers. A reading that later
  finds an item it missed in an already read snapshot appends it under a new
  identifier; the identifiers of the other statements do not move. [M2]
- No two statements claim the same place in the same bytes. A locator too
  coarse to be unique is refused at admission. [M2]
- A new method version that moves the locator of an item whose meaning is
  unchanged keeps the statement's identifier through a reviewed mapping from
  old locator to new. When the new version shows the old reading was wrong
  (a misread value, a wrong item, a wrong locator), the old statement is
  superseded with the reason, and results computed before the correction can
  still be reproduced. [M2]
- Neither a locator alone nor a fingerprint of content alone is a
  statement's identity. [M2]

## 10. Replay, idempotence and their limit

These are the correctness oracle of extraction. [M2 for all]

- **Replay.** Every document already read by a parser is read again from its
  stored bytes by the current pipeline, and the output is compared with the
  statements of record, statement by statement and field by field. Every
  difference is classified: the pipeline is wrong (fix the pipeline), the
  statement of record is wrong (correct it by supersession), or the
  difference is legitimate and explained in words. An unexplained difference
  fails the replay.
- **Idempotence.** Running the pipeline again over a snapshot already read
  changes nothing: no statement added, altered or renumbered, and no
  disposition added.
- **The limit.** An LLM read, a transcription and a person's reading are not
  reproducible byte for byte, so replay and idempotence bind the parsers,
  the ingestion runs and the step that admits statements, not a fresh
  reading. For statements produced by those methods, replay verifies instead
  that each locator still resolves in its bytes and that the text there
  still contains the label and values of record. Replay lists these
  statements by method, so the reach of the oracle is stated.
- **Positive control.** The replay itself is shown to fail when a snapshot or
  a statement of record is deliberately altered.

A run reports, by country and document type, the documents read, the
statements admitted, each kind of disposition and the documents that replay
exactly, differ with an explanation, or cannot be regenerated. [M2]

## 11. Reading statements into observations

An observation is one dated statement about one subject, cited to exactly
one statement ([ontology](jetp-ontology.md), Observation). Reading turns a
statement's printed fields into that typed form. It is a step after
extraction, with its own methods and checks, and it never changes the
statement it reads. [M3b for all rules of this section]

**How many.** A statement yields zero, one or several observations, one per
measure it prints. A plan item that prints a capacity and a cost estimate
yields a `capacity` and an `estimate`; a heading that only groups items
yields none. Nothing is read that the statement does not print.

**Subject.** The subject is typed. It is the statement itself while no
identity has been attached to it, and becomes a project, asset, agreement,
party, perimeter or country only through a matching judgement already made
([fusion](jetp-fusion.md) section 3). Reading never chooses an identity. A
macro-fiscal indicator has the country as subject; a utility's ratio has
the party.

**Measure and axis.** The measure is a value of the closed list of the
[ontology](jetp-ontology.md) section 4, with its axis. A flow carries its
`flow_type` from the IATI list. A measure is chosen from what the publisher
states: a plan cost is an `estimate`, never an agreement's `amount`; a
signed loan is an `amount` with the publisher's status word, never a `flow`
unless money is said to have moved. A value outside the list stops the
reading; the list grows only by decision.

**Basis.** Money carries a basis, `gross`, `net` or `unknown`. The basis is
`unknown` unless the document states it or states a rule that settles it.

**Value, unit and currency.** The value is the publisher's, in its unit and
currency. The scale the publisher prints is applied, so 3.92 under "USD
billion" is read as 3 920 000 000 in USD, and the printed form stays on the
statement. A printed range gives a low and a high bound; a single figure has
both bounds equal. A blank is unknown, never zero; a blank policy marker is
`not_screened`. A count names its unit as printed (rows, locomotives,
households). No conversion is made at reading: a conversion is a derivation
through a rate that a document printed.

**Own status.** The publisher's status word and its axis are carried from
the statement to the observation, unchanged. A shared status comes only
from the crosswalk.

**Timings.** Each date the statement gives becomes a timing with a role
(`event`, `approval`, `reporting_cutoff`, `register_date`, `report_date`,
`planned`, `target`, or `period_start` and `period_end` for a flow over an
interval), a precision (`day`, `month`, `quarter`, `year`, `unknown`) and
bounds. "Q1 2026" is precision `quarter` with bounds on the first and last
day of the quarter; "approved in 2024" is precision `year` with the year's
bounds. A date printed elsewhere in the snapshot and governing the statement,
such as a reporting cutoff on the cover of a register, becomes a timing that
names the statement it was read from, which is then the group heading or
another statement of the same snapshot. No date is invented: a value printed
without a date has only the timings the document gives.

**Methods.** Three methods may read observations, each signing with its name
and version.

- A reading rule per series: a versioned mapping from a series' verbatim
  fields to measures, units and timings, used where a parser read the
  statements. It is preferred wherever a series repeats.
- An LLM reading of one-off statements, checked as in section 6.3: one
  reader, a checker from another vendor on every observation, the author on
  the disagreements and a random sample sorted by likelihood and confidence;
  the full panel at M4.
- A person, named as the method.

**Checks.**

- Every value is found in its statement: the printed digits appear in the
  statement's label or verbatim fields, and the scale applied is one the
  statement or its heading prints. A value that cannot be found is refused.
- Measure, basis, flow type, date role and precision are values of the
  terms in force.
- A reading rule is checked by replay and idempotence like a parser
  (section 10), and red-tested with defects it must reject: a scale applied
  twice or not at all, a blank read as zero, a planned date read as an event,
  an estimate read as an amount.

**Correction.** A faulty reading (a wrong value, scale, measure, basis,
subject or date role, or a reading rule found faulty) is a ledger error. The
observation is superseded with the reason, as [fusion](jetp-fusion.md)
section 2 provides, and the superseded one stays readable, so results
computed before remain reproducible. A new version of a reading rule is run
over everything the previous version read, and the differences are checked
before it is adopted. A publisher's later statement of a different value is
never a correction: it is a new statement, read into a new observation.

## 12. Red tests and controls

Each check below replays a defect that the method must reject. A method is
not used on held documents until its checks pass. [M2 for all]

- **Each parser** has a test on a fixture drawn from a real snapshot, and is
  red-tested with at least one defect it must reject: a shifted grid, a
  missing page, a duplicated item, a count that disagrees with the printed
  total, or bytes it was not written for.
- **The admission step** rejects a renumbered identifier, a statement whose
  verbatim fields disagree with its document's declared field list, two
  statements with one locator in one snapshot, and a statement citing a
  snapshot the ledger does not hold.
- **Assisted reading** passes the planted-item control (the item is found,
  the absent item is not invented) and rejects a fabricated locator
  automatically.
- **The adapters** turn a corrupt or empty object into a disposition, not a
  crash.
- **The pending list** lists a snapshot with neither statements nor a
  disposition, and stops listing it once either exists.
- **Document deduplication** finds a known mirror already in the register
  before a null result on other documents is believed ([fusion](jetp-fusion.md)
  section 3).

## 13. The M2 slice

M2 is the minimum that reads every held document correctly and traceably.
It comprises:

1. The preconditions of section 2: deduplication applied, languages
   recorded, canonical members and translation languages chosen by rule,
   the pending list as the input of every run.
2. Statements carrying everything in section 3, including the method, the
   version, the checking reader and any decision by the author.
3. The text layers of section 5 for every format present among the held
   snapshots, each other format given a disposition that names it.
4. The four methods of section 6, with the automatic locator check and,
   for assisted readings, a checker from another vendor on every row and the
   author on the disagreements and a random sample.
5. The dispositions of section 7, so that every held document ends with
   statements or a disposition with its reason.
6. The snapshot rules of section 8 with key-based pairing: a second dated
   snapshot of a living document appends dated statements, records
   restatements under both dates and leaves the earlier statements
   untouched.
7. The identifier rules of section 9.
8. Replay, idempotence and their stated limit (section 10), and the red
   tests of section 12.

After M2:

- **M3a** adds no extraction rule and keeps the M2 check of assisted
  readings. Discovery may bring formats or series not held at M2; they are
  read in M3b.
- **M3b** reads the documents new since M2 with the same pipeline, reads
  the comparator channels (CRS, IATI) as structured sources, and reads
  statements into observations (section 11).
- **M4** runs the pipeline on schedule from the pending list, pairs
  statements across snapshots without a publisher's key, replaces the single
  checker by the full panel with positive controls, and swaps the document store behind
  the same interface without changing a reading method.
- **Later**: transcription of values shown only in charts, and derived
  translations of labels (never statements in their own right).

## 14. Open questions

- **How large the random sample shown to the author is.** Each run states it
  with its budget (section 6.3); whether a floor should be fixed here, such
  as a share of agreed rows per document, is not settled.

## 15. Checks a reading must pass

Each check is a small constructed situation and the outcome a correct reading
produces. A reading that gives another outcome is wrong, whatever else it
does well.

| Situation | Correct outcome |
|---|---|
| A page is fetched again and the bytes are identical. | Nothing is read. The later retrieval dates the persistence of every statement of the snapshot. |
| A register is fetched again; one amount changed, the other items are unchanged. | The new snapshot is read in full. Unchanged items are restatements linked to the earlier statements; the changed amount is a new statement beside the old one; no earlier statement is touched. |
| An item of the earlier snapshot is missing from the new one. | No statement is invented; the earlier item is recorded as unpaired, and nothing says it was cancelled. |
| The pipeline is run twice on the same snapshot. | The second run changes nothing. |
| A parser fix moves the locator of twelve items without changing what they say. | Their identifiers are kept through a reviewed mapping; nothing is renumbered. |
| A parser fix shows that one value was misread. | The old statement is superseded with the reason; results computed before remain reproducible. |
| A re-reading finds an item the first reading missed. | It is appended under a new identifier; the other identifiers do not move. |
| A report is held under the publisher's address and a partner's mirror, with the same bytes. | It is read once, from the canonical member; the other has the disposition `duplicate`. |
| A plan is held in English and in Vietnamese. | One language is read; the other has the disposition `translation_not_canonical`. |
| A dashboard's stored markup holds no data, which arrives by script. | Disposition `no_extractable_content`, reason "shell around a service"; collection may seek the data. |
| A decision is held only as a scan. | It is transcribed with the transcription named as method, or deferred with that reason; it is never skipped silently. |
| A figure appears only in a chart. | No statement; the reading's scope note records the chart. |
| The LLM proposes an item whose locator does not contain its label. | The proposal is rejected before any further check, and the rejection is recorded. |
| The reader and the checker from another vendor agree on 40 rows of a Vietnamese plan and disagree on 3. | The author sees the 3 disagreements and a random sample of the 40, sorted by likelihood and confidence; the rest is admitted with the checker's stance recorded. |
| A spreadsheet has a hidden row. | It is read, and its statement records that it was hidden. |
| A mirror was read before the publisher's own copy was found. | The mirror stays canonical; the publisher's copy has the disposition `duplicate`. |
| The assisted reader is given a document with a planted item and a named absent item. | The planted item is found; nothing is proposed for the absent one. |
| An appendix states it lists 37 items and the parser finds 36. | The reading fails; no statement of that document is admitted until the difference is resolved or recorded as the publisher's own. |
| A figure of 3.92 is printed under the heading "USD billion". | The statement keeps 3.92 and the heading as printed; no conversion at reading. |
| A register prints the status "B. In progress". | The word is copied as printed with its axis; no shared status is assigned. |
| A publisher counts 24 projects and names 3. | Three item statements and one count statement; nothing for the other 21. |
| A footnote conditions every row of a list. | A heading statement that the rows name as their group. |
| One cell names three funders. | One statement, the cell kept whole; the three parties are minted later by matching. |
| An item runs over a page break. | One statement whose locator spans both pages. |
| An object is served as a generic byte stream and is a PDF. | It is read as a PDF; the declared type stays on the retrieval. |
| A PDF is truncated. | Disposition `unreadable`, with the reason; the run continues. |
| A held document has no bytes. | Disposition `no_snapshot`. |
| Replay finds a difference nobody can explain. | The replay fails. |
| Replay meets a statement read by an LLM. | It is not regenerated; its locator is checked against the bytes and the statement is listed as outside the reach of replay. |
| A plan item prints a capacity of 50 MW and a cost of USD 120 million. | Two observations on the statement, a `capacity` and an `estimate`; no agreement and no identity. |
| A register prints "approved in 2024" and its cover gives a reporting cutoff of 31 March 2026. | One observation with two timings: `approval` at year precision, and `reporting_cutoff` at day precision naming the cover statement. |
| A cost field is blank. | Unknown, not zero; no observation value is invented. |
| A reading rule applied the "USD billion" scale twice. | A ledger error: the observation is superseded with the reason, and the rule's new version is rerun over everything it read. |
| A later snapshot prints a different amount. | A new statement and a new observation; the earlier observation is not superseded. |
