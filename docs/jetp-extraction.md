# JETP extraction: how statements are extracted from documents

Extraction turns the bytes of a held document into statements (step D2 of
the [language](jetp-language.md) document); reading turns statements into
observations (D3, section 11). The [ontology](jetp-ontology.md) fixes what
a statement (the ontology's line) is; the [fusion rules](jetp-fusion.md)
fix how statements are combined once extracted. This document fixes what a
statement must carry when it leaves extraction, which methods may produce
it, what happens to a document that yields none, and how a run is shown to
be correct. The Observatory's Statements page shows observations; this
document's statements appear there as Document rows.

Milestone tags in square brackets follow the [index](jetp-spec.md).

## 1. Principles

**Extract, do not interpret.** Extraction records what the publisher printed, as
printed: the label in its language, the status word in the publisher's
vocabulary, the number with its printed unit and scale. Conversion,
normalisation, crosswalking and matching are later steps, each with its own
method. An extractor that is unsure writes unknown; a guess is never
recorded as an extraction. [M2]

**Traceable to bytes.** Every statement resolves to one snapshot and one
place in it. A statement whose place cannot be found again in its snapshot
is not a statement. [M2]

**Every registered document accounted for.** A run ends with statements or
a recorded disposition for every document the register holds, whether or not
the ledger holds its bytes. [M2]

**Complete within a declared extraction scope.** An extraction states in
advance which parts of a document it covers. Inside that scope every item is
extracted; outside it nothing is, and the scope stays on record in the run
report ([operation](jetp-operation.md) section 8). [M2]

**Append only.** An extraction adds statements. It never edits, deletes or
renumbers an earlier one. The ledger's own errors are corrected by
supersession ([fusion](jetp-fusion.md), section 2). [M2]

**Declared method.** Every statement names the method and version that
extracted it: a parser, an ingestion run, an assisted reading, a
transcription or a person. Changing a method makes a new version, and its
effect on earlier output is reviewed before it is adopted. [M2]

**Reproduced where possible, reviewed where not.** A parser is checked by
running it again and comparing. An LLM read cannot be reproduced byte for
byte, so its checked output is the record (sections 6.3 and 10). [M2]

**Extraction mints nothing.** Extraction produces statements and dispositions.
It mints no project, asset, agreement, perimeter or party, and it decides no
match. A parser may propose a pairing it can see, such as a publisher's own
key repeated across editions, as a candidate match of
[fusion](jetp-fusion.md) section 3, signed with the parser's method. The one
exception is the party that publishes a document, which the document
register already names. [M2]

**Built from cases.** A parser is written for a publisher's repeated format
once two or three of its documents are in hand, and generalised only when a
second series needs the same logic. [M2]

## 2. Scope and preconditions

Extraction receives a registered document and returns statements citing one
of its snapshots, or a disposition. A document is *registered* when it is in
the register, and *held* when at least one of its retrievals yielded a
snapshot ([collection](jetp-collection.md) section 2); a registered document
that is not held receives the disposition `no_snapshot`. Extraction fetches
nothing: fetching belongs to collection. [M2]

Settled before any statement is extracted:

- **Document deduplication.** The document judgements of
  [fusion](jetp-fusion.md) section 3 (`same_as`, `edition_of`,
  `translation_of`) are made first. Statements are extracted from the canonical
  member of a `same_as` group and from one language of a translation pair.
  If a document judgement is later revoked, the document it had folded
  becomes pending again. [M2]
- **Canonical member.** Chosen among the members that hold a snapshot. In a
  `same_as` group, the member already extracted stays canonical, so that no
  statement moves; when none has been extracted, the publisher's own
  address is canonical over a mirror. [M2]
- **Annex held alone and inside a bundle.** The bundle's declared
  extraction scope excludes the annex and names the document where it was
  extracted. [M2]
- **Language extracted in a translation pair.** The version the publisher
  designates as authoritative; failing that, the member already extracted;
  failing that, the version in the country's official language. [M2]
- **Language.** The document's language is set by a versioned
  language-identification program over the text layer, the panel judging
  where it abstains. A document in a language no reader is calibrated for
  receives the disposition `deferred`, naming the language. [M2]
- **Edition.** A later edition of a document already extracted is its own
  document, related by `edition_of`; its statements are new statements,
  never merged into the earlier edition's. Statements of two editions, or of
  two issues of a series, are paired only as candidate matches of
  [fusion](jetp-fusion.md) section 3, never as restatements (section 8).
  [M2; the pairing, M3b]

**The pending list** is the input of every run. A snapshot is pending when it
has no statement, no snapshot-level disposition and no whole-snapshot
restatement (section 8) in force, and its document has no document-level
disposition in force (section 7): a snapshot of a `duplicate` or
`out_of_scope` document is never pending. A registered document with no
snapshot and no disposition is pending as a document, and its only outcome
is `no_snapshot`. A backlog run and a later periodic run start from the same
list and use the same pipeline (requirement F5). [M2]

## 3. What a statement carries

A statement leaving extraction carries the following, and nothing else is
required of it at this step.

- **Country**: the recipient country the statement is about, or none for a
  statement about no recipient country (a donor's method note). [M2]
- **Snapshot**: the fingerprint of the exact bytes extracted; never a web
  address and never a retrieval. [M2]
- **Locator**: the place of the assertion in those bytes, unique within the
  snapshot and never the whole document. Its syntax per format is the
  storage contract's; its meaning is section 5. [M2]
- **Ordinal**: the counter under which the statement was minted within its
  document and sequence, in extraction order, counted from one and never
  reassigned. Position in the document is carried by the locator, so a
  missed item found later takes the next ordinal wherever it stands. A
  number the publisher prints beside the item is a verbatim field. [M2]
- **Label as printed**: the item's name or description in the publisher's
  language and spelling, with whitespace joined but no other change. [M2]
- **Classification**: one value from the closed list of the
  [ontology](jetp-ontology.md) (section 4): `named_item`, `unnamed_item`,
  `quota`, `heading`, `submission`, `evaluation`, `register_allocation`,
  `count`, `envelope`, `absence`, `target`, `event`, `decision`. It is
  assigned from what the publisher presents, never inferred from words in
  the label, and never added to an admitted statement afterwards. When the
  extraction cannot tell, no default is taken: an assisted reading goes to
  the arbiter, and if the arbiter cannot tell either the item ends
  undetermined and is not admitted (section 6.3); for a parser, the
  document is not admitted (section 6.1). A reader or the arbiter may
  answer "cannot classify" when no value fits: the statement is recorded
  with its readings, not admitted, and the panel groups the unclassified
  statements of a run and proposes new classes, each with a stance and a
  confidence. A proposed class classifies nothing. A new class is adopted
  only by the author, as a new method version, which lists the statements
  recorded as unclassifiable under earlier versions and reads them again.
  Between two method versions the list is closed. [M2]
- **The publisher's own status word**, copied as printed, when the publisher
  prints one. Its axis is set only by a parser's reviewed, versioned status
  list for its series (adopted as crosswalk rows at M3b); it is empty for an
  assisted reading, a transcription and a person's reading, and an LLM
  reader is never asked for it. The shared status lives only in the
  crosswalk. [M2]
- **The publisher's own sector word**, copied as printed, when there is one.
  [M2]
- **Group**: the heading statements that govern it (a programme heading, a
  method note, a section title); a statement may sit under several. Each
  heading is a statement of the same snapshot. [M2]
- **Attributed party**, when the document attributes the part that carries
  the statement to one party (an annex signed by one partner, a chapter by
  one co-publisher, the consultant who wrote a commissioned report): one of
  the document's publishers or a party the document names. Otherwise the
  statement is its document's publishers', jointly. A quoted speaker is a
  verbatim field (section 4), not an attribution. [M2]
- **Verbatim fields**: everything else the publisher printed for the item,
  field by field. The list of fields is fixed by the method version for
  each document type ([ontology](jetp-ontology.md) section 2) or series, a
  series overriding its type, never by a reader, and applies per table (the
  table segment of the statement identifier). Each field keeps the header
  as printed, with its unit and scale wording; a parser may map a printed
  header to a field name under a declared, versioned mapping, the printed
  header staying beside the mapped name. Replay treats a mapped rename as
  explained; a mapping shared across publishers is a defect, corrected by a
  new declaration. A value keeps its printed form: "3.92" under a heading
  "USD billion" stays 3.92 with the heading, and a cell naming several
  funders stays one cell. Contact details (an email address, a telephone
  number, a personal postal address) are out of the declared extraction
  scope of every document. [M2]
- **Method and version** that extracted it, and, for an assisted reading or a
  transcription, every reader's and the arbiter's answer and any person who
  decided on it (section 6.3). [M2]
- **Recorded date**: when the ledger admitted the statement, the knowledge
  time of [fusion](jetp-fusion.md) section 8. The world time a statement
  speaks of is read later into timings (section 11); the date the ledger
  first held the bytes is the earliest retrieval that yielded the snapshot.
  [M2]

## 4. What becomes a statement

One statement is one assertion at one place. [M2 for all]

- An item of a list (a project of a plan appendix, a grant of a register, a
  submission of an annex) is one statement.
- A heading that groups items is a statement of classification `heading`,
  and the items it governs name it as their group. A method note that
  conditions a page or a list (a pro-rating, an exchange rate policy, a
  footnote on every row) is such a heading.
- A count the publisher gives without naming what is counted is one
  statement of classification `count`. A count of 24 with three items named
  gives three item statements and one count statement; nothing is invented
  for the other 21.
- An item that runs over a page break is one statement whose locator spans
  both pages.
- The same value printed in three places (a headline, a list, a caption) is
  three statements when all three places are in scope; relating them is a
  judgement of fusion.
- Prose is extracted when it asserts something in scope: a signature, an
  approval, an amount, a date, a state. Each assertion is one statement
  anchored on its own words, attributed to its speaker when the publisher
  quotes someone. A quoted speaker is recorded as the office or institution
  the publisher prints; a person's name is recorded only when the publisher
  prints it as the signatory of an in-scope document. The label is the
  shortest verbatim span of the text that carries the assertion. When one
  span carries several assertions, each is its own statement on the same
  anchors, told apart by an assertion index in its locator, numbered in the
  order the assertions appear and never reassigned (section 5). Its
  verbatim fields are the fixed list of its document type or series
  (section 3), for prose at least the speaker, the date and the amount as
  printed, each a verbatim substring of the text layer. Prose statements
  made by hand before this rule, with composed labels and paraphrase
  locators, keep their identifiers under a named legacy method and are
  re-anchored by supersession when read again. [M2 for the statement
  shape; M3b for typed values]
- A record page (a project page of a development bank, a portal's entry for
  one project) is one item statement for its subject; its labelled fields
  are its verbatim fields, and its description follows the rule for prose.
- Navigation, boilerplate, legal notices, contents pages and repeated page
  furniture are out of scope unless the extraction declares otherwise. Page
  furniture that carries a date, an issue number, a period or the
  publisher's name governing the statements is in scope by default, as a
  heading statement. Nothing missing from the page is completed from the
  register.

**Declared extraction scope.** Before extracting, the extraction names the
parts of the document it covers and states why the rest is out of scope.
Relevance is judged against the purpose of the ledger: statements about the
partnerships' projects, money, perimeters, parties and states. An
extraction may stop short of a whole document; it may not stop short of a
whole part it declared. [M2]

**Printed totals as controls.** Where the document prints how many items a
part holds, or a total the items should sum to, the extraction compares. A
parser fails the whole document (section 6.1). In an assisted reading the
printed total is itself a `count` or `envelope` statement: code sums the
admitted items of the part, and on a mismatch the part is read again once;
a mismatch that remains is recorded as the publisher's own inconsistency,
both figures kept, and flagged in the run report. [M2]

## 5. Text layers by format

A text layer is what a method reads when it does not read the bytes
directly: characters with their positions, cells, records. It is derived
from the snapshot and never the record. Each text layer names the snapshot
it came from and the adapter and exact version that produced it, pinned
with the pipeline's other dependencies; a locator resolves against the
stored bytes through that adapter version. [M2]

**Adapters in a closed room.** Adapters and renderers run without network
access and without the credentials of the pipeline, and never execute
macros, scripts, embedded objects or form actions, nor follow external
links or references. [M2]

**Retained layers.** The text layer of every snapshot with admitted
statements is retained beside its snapshot, keyed by snapshot, adapter,
version and the layer's own hash. A later adapter version produces a second
layer beside the first; moving a statement to it goes through the reviewed
mapping of section 9. A layer is never discarded while a statement resolves
through it. [M2]

**Locators.** A locator is derived by the pipeline, never written freehand.
For a table cell, it is the page (or sheet), the table and the row. For
prose, it is the page index plus start and end anchors that code derives
from the reader's verbatim quote, after whitespace is normalised and the
page furniture the method declares is removed; the anchors must be unique in
the text layer, or carry an occurrence index, and a span that carries several
statements adds an assertion index (section 4). The folio the publisher
printed is recorded only when the adapter reads it. The locator check
(section 6.3) resolves the anchors in the text layer and compares the text
between them with the quote under the same normalisation; there is no
character cap on the quote. Locators admitted before this rule stay valid
under their method version, and replay lists them as outside the reach of
the new check (section 10). [M2]

The declared content type of a retrieval is a hint. The format is decided
from the bytes; the declared type stays on the retrieval as received. [M2]

- **HTML.** The stored markup, parsed without running its scripts. A locator
  is a selector within the parsed markup or a text anchor, never a byte
  offset. What a browser would have loaded afterwards is not in the bytes
  and is not read; a page whose data arrives by script is a shell unless the
  data is inline (below). A capture of the rendered page is a separate
  snapshot, and collecting one is collection's business. Text that the
  markup itself hides (the `hidden` attribute, an inline `display:none`)
  is marked as hidden in the text layer, and a statement read from it
  records that it was hidden; finer detection of invisible text is M4.
  [M2]
- **PDF with a text layer.** The decoded characters with their page and
  position; the adapter reconstructs ligatures, rotated pages, wrapped cells
  and reading order, and its version is part of every statement's
  provenance. A locator gives the page index in the bytes and the printed
  folio when there is one, then the position in a grid or a text anchor.
  [M2]
- **PDF without a text layer, and images.** Read only by transcription
  (section 6.4). A machine-recognised text is a text layer like any other,
  named by its recogniser and version, and checked as in section 6.3
  before a statement rests on it. [M2 for the documents held that need it;
  the method may be a person's transcription]
- **Values shown only in a chart**, with no byte of text behind them, are out
  of scope until transcribed with provenance (ontology section 6). An
  extraction that meets one records it in its scope note. [M2 for the note;
  transcription of charts later]
- **Spreadsheets.** The cell values as stored by the publisher, sheet by
  sheet; formulas are not re-evaluated. A locator names the sheet and the
  cell or range. Hidden sheets, rows and cells are read like visible ones,
  and each statement read from them records that it was hidden. [M2]
- **JSON and other structured records.** Each record is read under its own
  key. A locator is the publisher's record identifier (a register code, an
  activity identifier, an SDMX key), and the record's fields are the
  verbatim fields. [M2 for the documents held, the comparator snapshots
  (CRS, IATI and World Bank records) included; new comparator draws, M3b]
- **Scripts.** Data embedded as a literal inside a script is read as a
  structured record from the literal. A script is never executed. [M2]
- **Corrupt or empty bytes** yield a disposition (section 7), never a crash
  of the run. [M2]

## 6. Extraction methods

Four methods produce statements. Each signs what it reads with its name and
version, and each has its own check of correctness. One method version may
combine a parser for a document's repeated frame with assisted reading of
its declared prose parts, each statement naming its part's method; the
statements of a snapshot are admitted together or not at all. [M2 for all
four]

### 6.1 A parser per repeated series

Where a publisher repeats one format (a quarterly progress update, a monthly
register, the appendices of successive plans, or a page template shared by
its project pages), one purpose-built parser reads the whole series. The
parser is the artifact under review; its output is reviewed as a difference
against what was there before.

- A parser declares which snapshots it can read and refuses others: it
  checks the fingerprint of a document it was written for, or the landmarks
  of the layout it expects, and stops when they are absent. [M2]
- It uses the printed totals and part boundaries as controls (section 4)
  and fails the whole document when a control fails. No partial set of
  statements is admitted from a failed extraction. [M2]
- It assigns classifications from the publisher's own presentation or from a
  reviewed list of items. When it cannot justify a value for an item, the
  document fails and is not admitted until the parser or its list is
  revised. [M2]
- A new parser version is run over every snapshot the previous version read
  before it is adopted, and the difference is reviewed under section 9. [M2]

### 6.2 Structured records read in bulk

A data portal or an export that holds many records in a stable structure is
read by an ingestion run. The run states the snapshot, the number of records
read, the declared fields and the counts it rejected, and the reviewer
reviews that statement of the run rather than each record. A bulk statement
is examined individually when an observation first cites it. Before a
portal is read, its snapshot is inspected and given a verdict (it holds
data, it is a shell around a service, or it holds nothing to read), before
any LLM call on its content. [M2 for the portals held]

**Count control.** An ingestion run compares, for each snapshot, the number
of records it read with the number the service or the file states, or,
where the source states none, the count recorded when the snapshot was
first read; when they differ the run fails for that snapshot and admits
nothing from it. A later draw of the same query slice is a new document
dated by its draw and related to the previous draw by `edition_of`, not a
new snapshot of one living document. The comparator snapshots already held
(CRS, IATI and World Bank records) are read and replayed at M2 under this
control; M3b adds new draws and the use of comparator records in matching
and results. [M2 for the held comparator snapshots; M3b for new draws]

### 6.3 Assisted reading of one-off documents

Where no series justifies a parser, two LLM readers from different model
families read every document independently, and a stronger LLM, the
arbiter, settles what they leave open. The judged statements are the
record, and no item waits for the author.

- **Untrusted input.** LLM readers and the arbiter are called without
  tools, network or file access, and receive the text layer as quoted data,
  never as instructions. [M2]
- **Local reading only.** A document whose recorded terms forbid
  third-party processing by an explicit reservation is read by local
  readers only and never sent to a hosted model; an item its readers leave
  open ends undetermined instead of going to the arbiter
  ([operation](jetp-operation.md) section 5). [M2 for the rule; M3a for
  the terms positions it reads]
- **Two readers.** Each reader is given the document's text layer, the
  declared scope and the field list that the method version fixes for the
  document's type or series (a reader never proposes one), and, blind to
  the other, proposes statements with a label, a verbatim quote of the
  assertion, a classification, the verbatim fields and a self-score that
  the proposal is right. [M2]
- **Locator check.** The locator of every proposal is derived by code from
  its quote (section 5) and checked against the text layer: it must
  resolve, and the text there must contain the proposed label and values.
  A proposal whose locator fails gets one repair call to the reader, with
  the failure stated; if it still fails, it is marked as failed, with the
  reason recorded. [M2]
- **Alignment and agreement.** Two proposals are one item when their
  derived spans overlap on the same page or cell and their classifications
  match. The readers agree on it when their verbatim fields are equal after
  whitespace and Unicode normalisation, each at a calibrated likelihood at
  or above the acceptance level (section 14); a difference of span only is
  agreement, and the shorter span is admitted. An item on which they agree
  stands. [M2]
- **Arbiter.** Every other item (proposed by one reader only, proposed by
  both with a difference, or below the acceptance level for either reader)
  goes to the arbiter, a stronger hosted LLM, with both readings in an
  order drawn at random and recorded, their likelihoods, any failure of the
  locator check and the pages concerned, in the document's language. The
  arbiter states whether the item is right, with a quoted basis. A proposal
  marked as failed is never admitted; a person may read the item directly
  (section 6.4). [M2]
- **Every item ends with a stance.** Admitted or rejected, with a
  likelihood that the proposal is right and a confidence on the calibrated
  scales of [fusion](jetp-fusion.md) section 1, mapped from the models' raw
  scores by their calibration; or undetermined, an abstention that carries
  no likelihood. An undetermined item is recorded and counted, never
  admitted and never dropped; a rejected proposal is recorded with its
  reason. Nothing is queued for the author. [M2]
- **Recorded and served by confidence.** Every reader's and the arbiter's
  answer is recorded on the item with the LLM identifier, the prompt
  version, the calibration version and, where the service allows, the
  sampling settings. The results are served in the order of
  [fusion](jetp-fusion.md) section 3; a decision the author makes is
  recorded as a judgement like any other, beside the machine readings,
  never over them. [M2]
- **Calibration and judgement rule.** Before any unattended run, each
  reader and the arbiter are scored on held-out reference answers, the
  arbiter on the items the readers escalate; which instance is scored is in
  [operation](jetp-operation.md) section 5. The method's versioned rule
  maps each model's raw self-scores to likelihood terms by monotone
  thresholds fitted on the tuning part, and sets confidence from agreement:
  high when the two readers agree, medium when the arbiter confirms one
  reader, low when it decides alone or against both. A model that fails its
  positive controls is weighted out. [M2]
- **Reference answers, the only check.** No person reviews admitted
  items one by one, high-impact items included. The reference answers are
  lines made by a blind cross-vendor panel, distinct from the readers and
  the arbiter, and named as panel agreement (requirement Q17); a decision the author makes on a served result
  is reported apart. They are split once, by a recorded seed, into a tuning
  part, which prompt writing and model selection may read, and a held-out
  part, which they never read. The held-out part is stratified by language
  and statement shape (table row, record page, prose span, transcription),
  so that strata fill sooner, frozen with the method version it
  calibrates, and changed only by a new method version; any change of
  reader, arbiter or prompt is scored on it again. Each calibration
  records, per model and per stratum, the observed precision of each
  likelihood term with its Wilson interval, the calibration error (the
  terms whose observed precision falls outside their calibration bin,
  [fusion](jetp-fusion.md) section 1), the recall (the held-out items that
  no reader proposed), the protocol's end-to-end precision, and the
  agree-but-wrong rate: the share of held-out items on which both readers
  agreed at or above the acceptance level and were wrong, the error that
  escalation cannot catch. A stratum with fewer than 30 held-out items is
  reported as uninformative; an unattended run in it uses the fallback:
  the pooled mapping of the items' language, every item escalated to the
  arbiter, and the stratum named uncalibrated in every release. The calibration record of every method version
  a release uses is part of its validation reports
  ([results](jetp-results.md) section 4). [M2]
- **Parts.** A document too long for one reading is read in parts, each a
  declared scope part (section 4), so parts never overlap. An item that
  runs across the boundary of two parts is one statement whose locator
  spans the boundary, owned by the part where it starts; the statements of
  adjacent parts are de-duplicated on their derived locators. Code computes
  the part plan of a snapshot, identical for both readers, on page
  boundaries (cells for a spreadsheet) within the smaller reader's context,
  and the run report records it. Each part inherits the headings and method
  notes that govern it; a printed total that covers several parts is
  checked after the parts are merged. [M2]
- Before the method is used on held documents it passes the planted-item
  control of section 12. [M2]
- **Replacement readers.** A reader or the arbiter replaced by another LLM
  is a new method version, admitted only after passing the controls of
  section 12 and its calibration on the held-out reference answers,
  stratified by language. The coverage report states which method version
  read each document type. [M2]

History: reference answers made by a blind cross-vendor panel instead of by hand, decided by the author on 2026-10-01 (interactive), after retracting the human gold set in front of its cost; ticket 1895.

### 6.4 Transcription

A scan, an image or a chart is read by transcription, and only after
collection has searched for a born-digital copy and found none
([collection](jetp-collection.md) section 8). A recogniser produces a text
layer; two vision-capable hosted LLM readers from different model families
([operation](jetp-operation.md) section 5), each blind to the other, read the
page images and that layer under the protocol of section 6.3. No reference
answers exist for transcription, so every transcribed item goes to the
arbiter, and the run report and the release name the method uncalibrated.
Each transcribed statement names the transcription as its method and
version, records its likelihood and confidence, and has a locator that gives
the page and the region transcribed. A transcribed label has the same
standing as a printed one once checked. The held scan without a text layer,
the Vietnamese plan decision (Decision 458, 23 pages), is transcribed at M2
by this method. [M2 for the held documents that need it]

A person may also read a document directly, without a proposing method. The
statement then names the person as its method, and the same automatic
check of locators applies. [M2]

## 7. Dispositions

A disposition is the outcome of a registered document, or of a snapshot of
a held one, that yields no statements; a candidate's outcome before
admission is collection's triage outcome, a different list. Every
registered document ends with statements or a disposition, and every
snapshot of a document that is extracted ends with statements or a
disposition of its own. A disposition is a record, like a judgement: it
names its kind, its reason in words, who or what decided it, by which method
and version, and when. It is revised by a later disposition that names it,
never erased. [M2]

The kinds, closed and grown only by decision:

| Kind | Applies to | Meaning |
|---|---|---|
| `duplicate` | document | a non-canonical member of a `same_as` group; its statements are those of the canonical member, and its snapshots stay citable |
| `translation_not_canonical` | document | the member of a translation pair that is not extracted |
| `no_snapshot` | document | the document is registered and the ledger holds no bytes for it; the reason cites the latest retrieval status, and collection owns the gap |
| `wrong_content` | snapshot | the bytes are not the document (an error page, a login wall, a consent screen), which is handed back to collection |
| `unreadable` | snapshot | corrupt, truncated or in a format no adapter handles, with the format named |
| `no_extractable_content` | snapshot | readable, but nothing in scope is stated in text: a shell around a service, a page of links, a chart with no text behind it; the reason says which |
| `out_of_scope` | document | registered for context, and nothing in it concerns the partnerships' projects, money, perimeters, parties or states |
| `deferred` | snapshot | held and in scope, in a format or a language no method reads yet, which it names with the milestone it waits for |

A snapshot byte-identical to one already extracted is not a new snapshot
and needs neither statements nor a disposition; a new snapshot whose
normalised text is identical is recorded as a restatement (section 8). A
`deferred` disposition closes a document for a run's completeness, but the
run reports the deferred documents apart, by country and type, and a
milestone's acceptance names them. [M2]

## 8. Dated snapshots and restatements

A document may be fetched many times, and a living document changes between
fetches. These rules apply [fusion](jetp-fusion.md) section 2 at extraction.

- **Identical bytes.** A later retrieval that returns the same bytes shares
  the earlier snapshot. Nothing is extracted again; the later retrieval date
  dates the persistence of every statement of that snapshot. [M2]
- **Identical text.** A new snapshot whose normalised text within the
  declared scope, under a named adapter version and furniture rule, equals
  that of the last extracted snapshot is treated as identical bytes: nothing
  is extracted, and the persistence of every statement is recorded as a
  restatement of the whole snapshot, dated by the new retrieval and
  carrying the adapter version so that replay regenerates the verdict. [M2]
- **New bytes.** A later retrieval whose normalised text differs forms a new
  snapshot, extracted in full under the same declared scope. Its statements
  cite the new snapshot; the statements of earlier snapshots are not
  touched. [M2]
- **Restatement.** A statement of the new snapshot whose item and verbatim
  content match a statement of an earlier snapshot of the same document is
  a restatement: kept under its own snapshot, and linked by a restatement
  record, never a `same_as`, to the statement where that content first
  appeared (its origin), never to the previous restatement. A restatement
  is persistence, not corroboration. Restatement is judged between
  snapshots of one document only (section 2 for editions). The *statements
  of a document*, wherever they are counted, are its origin statements;
  restatements are counted apart. [M2]
- **Change.** A statement of the new snapshot whose item matches an earlier
  one but whose content differs is a new statement beside the old one.
  Whether it is a development, a late report or a correction is a judgement
  of fusion. [M2]
- **Pairing across snapshots.** Deciding that two statements of two
  snapshots are the same item is a candidate match. When the publisher
  prints a stable key (a register code, a plan's ordinal within an
  unchanged appendix), the parser proposes the pairing on the key and it is
  virtually certain. Otherwise pairing goes through the proposers of
  [fusion](jetp-fusion.md) section 3. Content is compared field by field
  on the verbatim fields after whitespace is joined; any other difference
  is a change. [M2 for key-based pairing; M4 for pairing without a key]
- **Absence.** An item of an earlier snapshot with no counterpart in the new
  one is recorded as unpaired. No statement is invented for it, and its
  absence is not read as a cancellation. [M2]

## 9. Identifiers and corrections

- A statement's identifier is minted when it is admitted and is independent
  of its attributes. It is never reused and never renumbered, whatever
  happens to the extraction method. [M2]
- A new snapshot's statements get new identifiers. An item missed in an
  already extracted snapshot is appended under a new identifier; the other
  identifiers do not move. [M2]
- No two statements claim the same place in the same bytes. A locator too
  coarse to be unique is refused at admission. [M2]
- A new method version that moves the locator of an item whose meaning is
  unchanged keeps the statement's identifier through a reviewed mapping from
  old locator to new. When the new version shows the old extraction was wrong
  (a misread value, a wrong item, a wrong locator), the old statement is
  superseded with the reason, and results computed before the correction can
  still be reproduced. [M2]
- Neither a locator alone nor a fingerprint of content alone is a
  statement's identity. [M2]

## 10. Replay, idempotence and their limit

These are the correctness oracle of extraction. [M2 for all]

- **Replay.** Every document already extracted by a parser is extracted again
  from its stored bytes by the current pipeline, and the output is compared
  with the statements of record, statement by statement and field by field.
  Every difference is classified: the pipeline is wrong (fix the pipeline),
  the statement of record is wrong (correct it by supersession), or the
  difference is legitimate and explained in words. An unexplained difference
  fails the replay.
- **Idempotence.** Running the pipeline again over a snapshot already
  extracted changes nothing: no statement added, altered or renumbered, and
  no disposition added.
- **The limit.** An LLM read, a transcription and a person's reading are not
  reproducible byte for byte, so replay and idempotence bind the parsers,
  the ingestion runs and the step that admits statements. For statements
  produced by those methods, replay verifies instead that each locator still
  resolves in its bytes and that the text there still contains the label
  and values of record, and lists these statements by method. Statements
  admitted before the method columns existed are attributed to a method by
  their identifier family (storage contract, section 1), and statements
  whose locators predate the anchor rule of section 5 are listed as outside
  the reach of the locator check.
- **Positive control.** The replay itself is shown to fail when a snapshot or
  a statement of record is deliberately altered.

A run reports, by country and document type, the documents extracted, the
statements admitted, each kind of disposition and the documents that replay
exactly, differ with an explanation, or cannot be regenerated. [M2]

## 11. Reading statements into observations

An observation is one dated statement about one subject, cited to exactly
one statement ([ontology](jetp-ontology.md), Observation). Reading turns a
statement's printed fields into that typed form, after extraction, with its
own methods and checks, and never changes the statement it reads. [M3b for
all rules of this section]

**Scope.** Only statements that print a measure and belong to a declared
counting scope (the strict scope of a partnership, or a declared reference
pool) are read into observations; the others are listed, not counted.
Matching is bounded the same way ([fusion](jetp-fusion.md) section 3).

**How many.** A statement yields zero, one or several observations, one per
measure it prints. A plan item that prints a capacity and a cost estimate
yields a `capacity` and an `estimate`; a heading that only groups items
yields none. A column the publisher derives from another by a printed rate
(an amount in US dollars beside the same amount in rand) is the same
measure, not a second one: the reading rule declares which column is the
original, and each derived column becomes a conversion-rate record citing
the statement when the rate can be recovered, and nothing otherwise.

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

**Basis.** Money carries a basis, `gross`, `net` or `unknown`; `unknown`
unless the document states it or states a rule that settles it.

**Value, unit and currency.** The value is the publisher's, in its unit and
currency, with the printed scale applied (3.92 under "USD billion" is read
as 3 920 000 000 in USD, the printed form staying on the statement). A
printed range gives a low and a high bound; a single figure has both bounds
equal. A blank is unknown, never zero; a blank policy marker is
`not_screened`. A count names its unit as printed. No conversion is made at
reading: a conversion is a derivation through a rate that a document
printed.

**Own status.** The publisher's status word and its axis are carried from
the statement to the observation, unchanged. A shared status comes only
from the crosswalk.

**Timings.** Each date the statement gives becomes a timing with a role
from the closed list of date roles of the [ontology](jetp-ontology.md)
(section 2, Observation), a precision (`day`, `month`, `quarter`, `year`,
`unknown`) and bounds: "Q1 2026" is precision `quarter` with bounds on the
first and last day of the quarter. A date printed elsewhere in the snapshot
and governing the statement, such as a reporting cutoff on the cover of a
register, becomes a timing that names the statement it was read from (the
group heading or another statement of the same snapshot). No date is
invented. A figure printed as cumulative or "to date" is a flow whose
`period_end` is its as-of date and whose `period_start` has precision
`unknown`, bounded below by the agreement's earliest printed date when one
exists; fusion section 7 treats it as a closing position, never a movement.

**Methods.** Three methods may read observations, each signing with its name
and version: a reading rule per series (a versioned mapping from a series'
verbatim fields to measures, units and timings, preferred wherever a series
repeats); an LLM reading of one-off statements, judged as in section 6.3;
a person, named as the method.

**Checks.**

- Every value is found in its statement: the printed digits appear in the
  statement's label or verbatim fields, and the scale applied is one the
  statement, its heading or the printed header of its field states, never a
  mapped field name. A value that cannot be found is refused.
- Measure, basis, flow type, date role and precision are values of the
  terms in force.
- A reading rule is checked by replay and idempotence like a parser
  (section 10), and red-tested with defects it must reject: a scale applied
  twice or not at all, a blank read as zero, a planned date read as an event,
  an estimate read as an amount, and a register row printing a pledge in
  three money columns (as pledged, in US dollars, in rand), which yields one
  `amount`, not three.

**Correction.** A faulty reading (a wrong value, scale, measure, basis,
subject or date role, or a reading rule found faulty) is a ledger error: the
observation is superseded with the reason ([fusion](jetp-fusion.md) section
2). A new version of a reading rule is run over everything the previous
version read, and the differences are checked before it is adopted. A
publisher's later statement of a different value is never a correction: it
is a new statement, read into a new observation.

## 12. Red tests and controls

Each check below replays a defect that the method must reject. A method is
not used on held documents until its checks pass. [M2 for all]

- **Each parser** has a test on a fixture drawn from a real snapshot, and is
  red-tested with at least one defect it must reject: a shifted grid, a
  missing page, a duplicated item, a count that disagrees with the printed
  total, or bytes it was not written for.
- **The admission step** rejects a renumbered identifier, a statement whose
  verbatim fields disagree with its document's declared field list, two
  statements with one locator, or overlapping prose anchors, in one snapshot
  (two assertions of one span differ by their assertion index), and a
  statement citing a snapshot the ledger does not hold.
- **Assisted reading** passes the planted-item control (a planted item is
  found, a named absent item is not invented) and rejects a fabricated
  locator automatically; two readers quoting one sentence by different
  spans align as one item. The control document also carries a planted
  instruction addressed to the reader, which must not alter any proposal.
- **Calibration.** Each reader and the arbiter are scored on held-out
  reference answers before use; the set carries a planted misreading that
  each must reject, and a model that fails a positive control is weighted
  out. A prompt revised after reading a held-out item makes that item part
  of the tuning set, and the calibration is rerun without it.
- **Parts.** A fixture cut so that an item straddles the boundary of two
  parts yields one statement.
- **Retained layers.** Replay against a snapshot whose retained text layer
  is deleted and whose adapter version is unavailable fails loudly.
- **The adapters** turn a corrupt or empty object into a disposition, not a
  crash. A fixture carrying a macro, an embedded script and an external link
  is parsed with no network request and nothing executed.
- **Hidden text.** An HTML fixture with text under the `hidden` attribute
  and an inline `display:none` yields statements marked as hidden. White
  text on a white ground, overlaid objects, annotations and a text layer
  that disagrees with the rendered page are fixtures of the finer detection
  of section 5, at M4.
- **Ingestion runs** fail on a snapshot whose records read differ in number
  from the count the service or file states (section 6.2).
- **The pending list** lists a snapshot with neither statements nor a
  disposition, and stops listing it once either exists; a run over a
  document with the disposition `duplicate` leaves nothing of it pending.
- **Document deduplication** finds a known mirror already in the document
  register before a null result on other documents is believed
  ([fusion](jetp-fusion.md) section 3).

## 13. The M2 slice

M2 is the minimum that extracts every held document correctly and
traceably: sections 2 to 10 and 12 over the documents held, the held scan
transcribed (section 6.4), the held comparator snapshots replayed under the
count control (section 6.2), the four methods calibrated first, and the
snapshot rules of section 8 with key-based pairing, tested on a fixture with
one value changed and on the held page whose bytes change on every request,
since no held document has a genuine second version. M3a adds no extraction
rule. M3b extracts the documents new since M2 and new comparator draws with
the same pipeline, and reads statements into observations (section 11). M4
runs the pipeline on schedule, pairs statements across snapshots without a
publisher's key, and swaps the document store behind the same interface.
Later: transcription of values shown only in charts, and derived
translations of labels (never statements in their own right).

## 14. Open questions

- **The acceptance level**, declared per method version, which sends an
  item to the arbiter (section 6.3; fusion section 3 for matching).
  Default: "likely or more"; revisited once calibration has measured the
  observed precision of each likelihood term.

## 15. Checks an extraction must pass

Each check is a constructed situation and the outcome a correct extraction
produces.

| Situation | Correct outcome |
|---|---|
| A page is fetched again; the bytes differ only by a token the server changes on every request. | The normalised text is identical: nothing is extracted, and the retrieval dates the persistence of the snapshot's statements, with the adapter version recorded. |
| A register is fetched again; one amount changed, the other items are unchanged. | The new snapshot is extracted in full. Unchanged items are restatements linked to the earlier statements; the changed amount is a new statement beside the old one; no earlier statement is touched. |
| An item of the earlier snapshot is missing from the new one. | No statement is invented; the earlier item is recorded as unpaired, and nothing says it was cancelled. |
| A mirror was extracted before the publisher's own copy was found. | The mirror stays canonical; the publisher's copy has the disposition `duplicate`. |
| A dashboard's stored markup holds no data, which arrives by script. | Disposition `no_extractable_content`, reason "shell around a service"; collection may seek the data. |
| A decision is held only as a scan. | Collection searches for a born-digital copy and records the search; if one is found it is registered and extracted instead. Otherwise the scan is transcribed by a recogniser and two vision-capable readers, with the arbiter on escalation; every statement names the transcription as method, gives page and region, and records its likelihood and confidence. |
| The LLM proposes an item whose quote cannot be found in the text layer. | The derived locator fails; one repair call is made; if it still fails, the arbiter sees the proposal marked as failed, the failure is recorded, and the proposal is not admitted. |
| The two readers agree on 40 rows of a Vietnamese plan at "likely" or more and differ on 3. | The 40 stand; the arbiter reads the 3 with both readings and the pages; all 43 end with a stance, a likelihood and a confidence, recorded with every reader's answer; nothing is queued for the author. |
| The arbiter cannot decide one of the 3. | The item ends undetermined, recorded and counted, not admitted; it is served among the least certain results. |
| An appendix states it lists 37 items and the parser finds 36. | The extraction fails; no statement of that document is admitted until the difference is resolved or recorded as the publisher's own. |
| One cell names three funders. | One statement, the cell kept whole; the three parties are minted later by matching. |
| One sentence says that the plan was approved in March and that ADB disbursed USD 100 million in June. | Two statements on the same anchors, with assertion indexes 1 and 2; neither is refused as a duplicate locator. |
| An English version of a Vietnamese decision carries an annex the Vietnamese one lacks. | The content check of fusion section 3 finds the difference; the two are not a translation pair, and each is extracted as its own document. |
| A plan item prints a capacity of 50 MW and a cost of USD 120 million. | Two observations on the statement, a `capacity` and an `estimate`; no agreement and no identity. |
| A register prints "approved in 2024" and its cover gives a reporting cutoff of 31 March 2026. | One observation with two timings: `approval` at year precision, and `reporting_cutoff` at day precision naming the cover statement. |
| A project page prints "disbursements to date as of 30 June 2026: USD 40 million". | One flow observation of measure `flow`, type `disbursement`, with `period_end` on 30 June 2026 and `period_start` of precision `unknown`; not a movement on 30 June. |
