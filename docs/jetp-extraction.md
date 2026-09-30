# JETP extraction: how statements are extracted from documents

Extraction turns the bytes of a held document into statements. The
[ontology](jetp-ontology.md) fixes what a statement (the ontology's line) is;
the [fusion rules](jetp-fusion.md) fix how statements are combined once
extracted. This document fixes how they are extracted: what a statement must carry when it
leaves extraction, which methods may produce it, what happens to a document
that yields none, how a run is shown to be correct, and how a statement is
then read into observations. Extraction turns bytes into statements (step D2
of the [language](jetp-language.md) document); reading turns statements into
observations (D3). The Observatory's Statements page shows observations; this
document's statements appear there as Document rows.

Its rules are conceptual. They hold whether statements are kept as RDF
triples, as sentences of flat text or as rows; how they are stored is the
[storage contract](jetp-ledger-storage.md), and how they are shown is the
[Observatory](jetp-observatory-presentation.md). Words follow the
[language](jetp-language.md) document: a statement's documentary support is
its justification, a language model is an LLM, and the ledger's own output is
a release.

Every rule carries, in square brackets, the milestone that needs it: M2 (an
extraction pipeline that works on every document held), M3a (discovery to a
cutoff, then the register frozen), M3b (the new documents extracted,
matched and released), M4 (operation), or later. A rule tagged after M2 is
not built before its milestone.

## 1. Principles

**Extract, do not interpret.** Extraction records what the publisher printed, as
printed: the label in its language, the status word in the publisher's
vocabulary, the number with its printed unit and scale. Conversion,
normalisation, crosswalking and matching come later, each as its own step
with its own method. An extractor that is unsure writes unknown; a guess is
never recorded as an extraction. [M2]

**Traceable to bytes.** Every statement resolves to one snapshot and one
place in it, so that anyone holding the bytes can find the text it rests on.
A statement whose place cannot be found again in its snapshot is not a
statement. [M2]

**Every registered document accounted for.** A run ends with statements or
a recorded disposition for every document the register holds, whether or not
the ledger holds its bytes. Silence is never an outcome. [M2]

**Complete within a declared extraction scope.** An extraction states in
advance which parts of a document it covers. Inside that scope every item is
extracted; outside it nothing is, and the scope stays on record so that a
later extraction can extend it. [M2]

**Append only.** An extraction adds statements. It never edits, deletes or
renumbers an earlier one. The ledger's own errors are corrected by
supersession ([fusion](jetp-fusion.md), section 2), and the superseded
statement stays readable. [M2]

**Declared method.** Every statement names the method and version that
extracted it: a parser, an assisted reading, a transcription or a person. Changing a
method makes a new version, and its effect on earlier output is reviewed
before it is adopted. [M2]

**Reproduced where possible, reviewed where not.** A parser is checked by
running it again and comparing. An LLM read cannot be reproduced byte for
byte, so its checked output is the record and its checks are of another
kind (section 6.3 and section 10). [M2]

**Extraction mints nothing.** Extraction produces statements and dispositions.
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

Extraction receives a registered document and returns statements citing one
of its snapshots, or a disposition. A document is *registered* when it is in
the register, and *held* when at least one of its retrievals yielded a
snapshot ([collection](jetp-collection.md) section 2); a registered document
that is not held receives the disposition `no_snapshot`. It does not fetch
anything: fetching, retries and the choice of what to collect belong to the
collection specification. Reading statements into observations is a
later step with its own rules (section 11). [M2]

Three things are settled before any statement is extracted.

- **Document deduplication.** A duplicate extracted twice doubles every statement
  and every count downstream, so the document judgements of
  [fusion](jetp-fusion.md) section 3 (`same_as`, `edition_of`,
  `translation_of`) are made first. Statements are extracted from the canonical
  member of a `same_as` group and from one language of a translation pair.
  Extraction applies the outcome; it does not restate the proposers. If a
  document judgement is later revoked, the document it had folded becomes
  pending again and is extracted like any other. [M2]
- **Canonical member.** The canonical member is chosen among the members
  that hold a snapshot. In a `same_as` group, the member already extracted
  stays canonical, so that no statement moves; when none has been extracted, the
  publisher's own address is canonical over a mirror. [M2]
- **Annex held alone and inside a bundle.** When an annex is held as a
  document of its own and also inside a bundle, the bundle's declared
  extraction scope excludes the annex and names the document where it was
  extracted, so its statements are not extracted twice. [M2]
- **Language extracted in a translation pair.** The version the publisher
  designates as authoritative is extracted; failing that, the member already
  extracted; failing that, the version in the country's official language, whose
  labels match other national sources best. [M2]
- **Language.** The document's language is recorded, because the translation
  rule needs it and because the LLM readers and the arbiter must handle that
  language. [M2]
- **Edition.** A document that is a later edition of one already extracted is its
  own document, related by `edition_of`. Its statements are new statements
  of the new document; they are never merged into the earlier edition's.
  Statements of two editions, or of two issues of a series, are paired only
  as candidate matches of [fusion](jetp-fusion.md) section 3, never as
  restatements (section 8). [M2; the pairing, M3b]

The input of every run is the pending list. A snapshot is pending when it
has no statements and no snapshot-level disposition, and its document has no
document-level disposition (section 7): so a snapshot of a `duplicate` or
`out_of_scope` document is never pending. A registered document with no
snapshot and no disposition is pending as a document, and its only outcome
is `no_snapshot`. A backlog run and a later periodic run start from the same
list and use the same pipeline. Sections 7 and 12 and requirement F5 use
this definition. [M2]

## 3. What a statement carries

A statement leaving extraction carries the following, and nothing else is
required of it at this step.

- **Country**: the recipient country the statement is about, or none for a
  statement about no recipient country (a donor's method note). [M2]
- **Snapshot**: the fingerprint of the exact bytes extracted. Never a web address
  and never a retrieval. [M2]
- **Locator**: the place of the assertion in those bytes, precise enough to
  be unique within the snapshot and never the whole document. Its syntax per
  format is fixed by the storage contract; its meaning is fixed in section 5.
  [M2]
- **Ordinal**: the counter under which the statement was minted within its
  document and sequence, in extraction order, counted from one and never
  reassigned. Its position in the document is carried by the locator, not
  by the ordinal, so a missed item found later takes the next ordinal
  wherever it stands on the page. A number the publisher prints beside the
  item is a verbatim field and may differ from the ordinal (gaps, repeats,
  restarts). [M2]
- **Label as printed**: the item's name or description in the publisher's
  language and spelling, with whitespace joined but no other change. [M2]
- **Classification**: one value from the closed list of the
  [ontology](jetp-ontology.md) (section 4): `named_item`, `unnamed_item`,
  `quota`, `heading`, `submission`, `evaluation`, `register_allocation`,
  `count`, `envelope`, `absence`, `target`, `event`, `decision`. It is
  assigned by the extraction from what the publisher presents, never
  inferred from words in the label. A statement is admitted only with a
  classification. When the extraction cannot tell, the proposal takes no
  default: for an assisted reading it goes to the arbiter, and if the
  arbiter cannot tell either it ends undetermined and is not admitted
  (section 6.3); for a parser, the document is not admitted (section 6.1).
  A reader or the arbiter may also answer "cannot classify" when no value
  of the list fits what the publisher asserts. Such a statement is not
  admitted; it is recorded with its readings, and the panel (the two readers
  and the arbiter) groups the unclassified statements of a run and proposes
  new classes for them, each with a stance and a confidence. A proposed
  class is a candidate and classifies nothing. A new class is adopted only
  by the author, since it changes the contract, and its adoption is a new
  method version, which lists the statements recorded as unclassifiable
  under earlier versions and reads them again. Between two method versions
  the list is closed: no run admits a statement under a class not yet
  adopted. A classification is never added to an admitted statement
  afterwards. [M2]
- **The publisher's own status word**, copied as printed, when the publisher
  prints one. The axis it belongs to is set only by a parser's reviewed,
  versioned status list for its series (adopted as crosswalk rows at M3b);
  it is empty for an assisted reading, a transcription and a person's
  reading, and an LLM reader is never asked for it. Replay reproduces the
  axis from the parser's configuration. The shared status is never assigned
  here; it lives only in the crosswalk. [M2]
- **The publisher's own sector word**, copied as printed, when there is one.
  [M2]
- **Group**: the heading statement that governs it, when one does (a
  programme heading, a method note, a section title that conditions every
  item under it). The heading is a statement of the same snapshot. [M2]
- **Verbatim fields**: everything else the publisher printed for the item,
  field by field. The list of fields is fixed by the method version for
  each document class or series, never by a reader, and applies per table
  (the table segment of the statement identifier); every statement of that
  table conforms to it. Each document's declared list is copied from its
  class or series. Each field keeps the header as printed, with
  its unit and scale wording; a parser may map a printed header to a field
  name under a declared, versioned mapping, and the printed header stays
  beside the mapped name. Replay treats a mapped rename as explained. A
  mapping shared across publishers (one publisher's annex read under
  another's field names) is a defect, corrected by a new declaration, not an
  explained difference. A value keeps its printed form: "3.92" under a
  heading "USD billion" stays 3.92 with the heading, and a cell naming
  several funders stays one cell. Contact details (an email address, a
  telephone number, a personal postal address) are out of the declared
  extraction scope of every document and are not extracted. [M2]
- **Method and version** that extracted it, and, for an assisted reading or a
  transcription, every reader's and the arbiter's answer and any person who
  decided on it (section 6.3). [M2]
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
  judgement of fusion, not a merge at extraction.
- Prose is extracted when it asserts something in scope: a signature, an approval,
  an amount, a date, a state. Each assertion is one statement anchored on its
  own words, attributed to its speaker when the publisher quotes someone. A
  quoted speaker is recorded as the office or institution the publisher
  prints; a person's name is recorded only when the publisher prints it as
  the signatory of an in-scope document. The label of a prose statement is
  the shortest verbatim span of the text that carries the assertion. Its
  verbatim fields are the fixed list of its document class or series
  (section 3), for prose at least the speaker, the date and the amount as
  printed, each a verbatim substring of the text layer. Amounts and dates
  stay as printed at extraction; typing them is reading (section 11).
  Prose statements made by hand before this rule, with composed labels and
  paraphrase locators, keep their identifiers under a named legacy method
  and are re-anchored by supersession when read again. [M2 for the
  statement shape; M3b for typed values]
- A record page (a project page of a development bank, a portal's entry for
  one project) is one item statement for its subject; its labelled fields
  are its verbatim fields under the printed labels, and its description
  follows the rule for prose.
- Navigation, boilerplate, legal notices, contents pages and repeated
  page furniture are out of scope unless the extraction declares otherwise.
  Page furniture that carries a date, an issue number, a period or the
  publisher's name governing the statements (a dateline, a masthead date, an
  issue period) is in scope by default, and is extracted as a heading
  statement that the statements it governs name as their group. Nothing
  missing from the page is completed from the register.

**Declared extraction scope.** Before extracting, the extraction names the
parts of the document it covers (an appendix, the list of submissions, the body of a news
item) and states why the rest is out of scope. Relevance is judged against
the purpose of the ledger: statements about the partnerships' projects,
money, perimeters, parties and states. An extraction may stop short of a
whole document; it may not stop short of a whole part it declared. [M2]

**Printed totals as controls.** Where the document prints how many items a
part holds, or a total the items should sum to, the extraction compares and
fails when they disagree. The disagreement is resolved by extracting again, or
recorded as the publisher's own inconsistency with both figures kept. [M2]

## 5. Text layers by format

A text layer is what a method reads when it does not read the bytes
directly: characters with their positions, cells, records. It is derived
from the snapshot and never the record. Each text layer names the snapshot
it came from and the adapter and exact version that produced it; a locator
resolves against the stored bytes through that named adapter version. The
adapter is pinned by exact version with the pipeline's other dependencies.
[M2]

**Retained layers.** A locator resolves only against the text layer of one
adapter version, and an adapter version may become unavailable, so the text
layer of every snapshot with admitted statements is retained beside its
snapshot, keyed by snapshot, adapter, version and the layer's own hash. A
later adapter version produces a second layer beside the first; moving a
statement to it goes through the reviewed mapping of section 9, old layer to
new layer. A layer is never discarded while a statement resolves through it.
[M2]

**Locators.** A locator is derived by the pipeline, never written freehand.
For a table cell, it is the page (or sheet), the table and the row. For
prose, it is the page index plus start and end anchors that code derives
from the reader's verbatim quote, after whitespace is normalised and the
page furniture the method declares is removed; the anchors must be unique in
the text layer, or carry an occurrence index. The folio the publisher
printed is recorded only when the adapter reads it. The locator check
(section 6.3) resolves the anchors in the text layer and compares the text
between them with the quote under the same normalisation; there is no
character cap on the quote. Locators admitted before this rule stay valid
under their method version, and replay lists them as outside the reach of
the new check (section 10). [M2]

The declared content type of a retrieval is a hint. The format is decided
from the bytes, so an object served as a generic byte stream that is in fact
a PDF is read as a PDF, and the declared type stays on the retrieval as
received. [M2]

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
  6). An extraction that meets one records it in its scope note so the gap is
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
  verbatim fields. [M2 for the documents held, including the comparator
  snapshots already held (CRS, IATI and World Bank records), which are read
  and replayed at M2 by the ingestion run of section 6.2; new comparator
  draws, M3b]
- **Scripts.** Data embedded as a literal inside a script (an array behind a
  dashboard) is read as a structured record from the literal. A script is
  never executed to obtain data. [M2]
- **Corrupt or empty bytes** yield a disposition (section 7), never a crash
  of the run. [M2]

## 6. Extraction methods

Four methods produce statements. Each signs what it reads with its name and
version, and each has its own check of correctness. [M2 for all four]

### 6.1 A parser per repeated series

Where a publisher repeats one format (a quarterly progress update, a monthly
register, the appendices of successive plans, or a page template shared by
its project pages or portal entries), one purpose-built parser reads the
whole series. The parser is the artifact under review; its output is
reviewed as a difference against what was there before.

- A parser declares which snapshots it can read and refuses others: it checks
  the fingerprint of a document it was written for, or the landmarks of the
  layout it expects, and stops when they are absent. It never guesses its
  way through an unfamiliar layout. [M2]
- It uses the printed totals and part boundaries as controls (section 4) and
  fails the whole document when a control fails. No partial set of
  statements is admitted from a failed extraction. [M2]
- It assigns classifications from the publisher's own presentation or from a
  reviewed list of items. When it cannot justify a value for an item, it
  does not choose one: the document fails and is not admitted until the
  parser or its list is revised (section 3, classification). [M2]
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
data, it is a shell around a service, or it holds nothing to read. The
verdict precedes any LLM call on the portal's content, so a portal bundle
that is a shell is never sent to an LLM reader. [M2 for the portals held]

**Count control.** An ingestion run compares, for each snapshot, the number
of records it read with the number the service or the file states (a total
returned by the API, a row count, the records of a declared query slice);
when they differ the run fails for that snapshot and admits nothing from
it. A later draw of the same query slice is a new document dated by its
draw and related to the previous draw by `edition_of`, not a new snapshot
of one living document. The comparator snapshots already held (CRS, IATI
and World Bank records) are read and replayed at M2 by an ingestion run
under this control; what the comparator tag of M3b adds is new draws and
the use of comparator records in matching and results. [M2 for the held
comparator snapshots; M3b for new draws]

### 6.3 Assisted reading of one-off documents

Where no series justifies a parser (a single investment plan, an approval
document, a project page, a news item), two LLM readers from different
model families read every document independently, and a stronger LLM, the
arbiter, settles what they leave open. The judged statements are the
record, and no item waits for the author.

- **Untrusted input.** Documents are written by interested parties. LLM
  readers and the arbiter are called without tools, network or file access,
  and receive the text layer as quoted data, never as instructions. [M2]
- **Two readers.** Each reader is given the document's text layer, the
  declared scope and the field list that the method version fixes for the
  document's class or series (a reader never proposes one), and, blind to
  the other,
  proposes statements with a label, a verbatim quote of the assertion, a
  classification, the verbatim fields and a likelihood that the proposal is
  right. The two readings are aligned on their derived locators. [M2]
- The locator of every proposal is derived by code from its quote, as
  section 5 states, and checked against the text layer: it must resolve, and
  the text there must contain the proposed label and values. A proposal
  whose locator fails gets one repair call to the reader, with the failure
  stated; if it still fails, it is marked as failed. The failure and its
  reason are recorded. [M2]
- **Agreement.** The readers agree on an item when both propose it with
  the same derived locator, classification and verbatim fields, each at a
  calibrated likelihood at or above the extraction acceptance level (for
  example "likely or more"). An item on which they agree stands. [M2]
- **Arbiter.** Every other item (proposed by one reader only, proposed by
  both with a difference, or below the acceptance level for either reader)
  goes to the arbiter, a stronger hosted LLM, with both readings, their
  likelihoods, any failure of the locator check and the pages concerned, in
  the document's language, whatever that language is. The arbiter states
  whether the item is right, with a quoted basis. A proposal marked as
  failed is never admitted; a person may read the item directly (section
  6.4). [M2]
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
  sampling settings. The results are served sorted by likelihood and
  confidence; the author examines them when he chooses, and a decision he
  makes is recorded as a judgement like any other, beside the machine
  readings, never over them. [M2]
- **Calibration.** Before any unattended run, each reader and the arbiter
  are scored on held-out reference answers, and each model's raw
  self-scores are mapped to the likelihood terms from those scores; a model
  that fails its positive controls is weighted out. How the readers are
  selected and where they run is in [operation](jetp-operation.md) section
  5. [M2]
- **Reference answers, the only human check.** No person reviews admitted
  items one by one, high-impact items included; the reference answers are
  the human check of the method. They are the lines of the extracted
  documents made by hand (requirement Q17), split once, by a recorded
  seed, into a tuning part, which prompt writing and model selection may
  read, and a held-out part, which they never read. The held-out part is
  stratified by country, language and classification, frozen with the
  method version it calibrates, and changed only by a new method version;
  any change of reader, arbiter or prompt is scored on it again. Each
  calibration records, per model and per stratum, the observed precision of
  each likelihood term with its Wilson interval, the calibration error (the
  terms whose observed precision falls outside their stated range), and the
  agree-but-wrong rate: the share of held-out items on which both readers
  agreed at or above the acceptance level and were wrong, the error that
  escalation cannot catch, since readers of two families still share
  training data. A stratum with fewer than 30 held-out items is reported as
  uninformative, not as calibrated. The calibration record of every method
  version a release uses is part of its validation reports
  ([results](jetp-results.md) section 4). [M2]
- **Parts.** A document too long for one reading is read
  in parts, and a part is a declared scope part (section 4: an appendix, a
  section, a page range), so parts never overlap. An item that runs across
  the boundary of two parts is one statement whose locator spans the
  boundary, owned by the part where it starts, as for a page break; the
  statements of adjacent parts are de-duplicated on their derived locators.
  Each part inherits the headings and method notes that govern it. Each
  reader reads within its part only, and a printed total that covers
  several parts is checked after the parts are merged. [M2]
- Before the method is used on held documents it passes a test: a document
  with a planted item that must be found and a named absent item that must
  not be invented (section 12). [M2]
- **Replacement readers.** A reader or the arbiter replaced by another LLM
  (a retired, repriced or unavailable one) is a new method version. It is
  admitted only after passing the controls of section 12 and its
  calibration on the held-out reference answers (requirement Q17),
  stratified by language. The coverage report states which method version
  read each document class. [M2]

### 6.4 Transcription

A scan, an image or a chart is read by transcription, and only after
collection has searched for a born-digital copy and found none
([collection](jetp-collection.md) section 8). A recogniser produces a text
layer; two vision-capable LLM readers from different model families, each
blind to the other, read the page images and that layer under the protocol
of section 6.3, and the arbiter settles what they leave open. Each
transcribed statement names the transcription as its method and version,
records its likelihood and confidence, and has a locator that gives the
page and the region transcribed. No author sitting is needed. A
transcribed label has the same standing as a printed one once checked; its
pedigree says it was transcribed. The held scan without a text layer, the
Vietnamese plan decision (Decision 458, 23 pages), is transcribed at M2 by
this method. [M2 for the held documents that need it]

A person may also read a document directly, without a proposing method. The
statement then names the person as its method, and the same automatic
check of locators applies. [M2]

## 7. Dispositions

A disposition here is the outcome of a registered document, or of a
snapshot of a held one, that yields no statements; a candidate's outcome before admission is collection's triage
outcome, a different list. [M2]

Every registered document ends with statements or a disposition, and every
snapshot of a document that is extracted ends with statements or a disposition of
its own. A disposition is a record, like a judgement: it names its kind, its
reason in words, who or what decided it, by which method and version, and
when. It is revised by a later disposition that names it, never erased. [M2]

The kinds, closed and grown only by decision:

| Kind | Applies to | Meaning |
|---|---|---|
| `duplicate` | document | a non-canonical member of a `same_as` group; its statements are those of the canonical member, and its snapshots stay citable |
| `translation_not_canonical` | document | the member of a translation pair that is not extracted |
| `no_snapshot` | document | the document is registered and the ledger holds no bytes for it; the reason cites the latest retrieval status, and collection owns the gap |
| `wrong_content` | snapshot | the bytes are not the document (an error page, a login wall, a consent screen), which is handed back to collection |
| `unreadable` | snapshot | corrupt, truncated or in a format no adapter handles, with the format named |
| `no_extractable_content` | snapshot | readable, but nothing in scope is stated in text: a shell around a service, a page of links, a chart with no text behind it; the reason says which |
| `out_of_scope` | document | held for context, and nothing in it concerns the partnerships' projects, money, perimeters, parties or states |
| `deferred` | snapshot | held and in scope, not extracted yet; names the milestone it waits for and why (a run budget reached, a format no method reads yet) |

A snapshot that is byte-identical to one already extracted is not a new snapshot
and needs neither statements nor a disposition; nor does a new snapshot
whose normalised text is identical (section 8). [M2]

A `deferred` disposition closes a document for the purpose of a run's
completeness, but a run reports the deferred documents apart, by country and
type, and a milestone's acceptance names them. [M2]

## 8. Dated snapshots and restatements

A document may be fetched many times, and a living document (a project page,
a register) changes between fetches. The rules below apply
[fusion](jetp-fusion.md) section 2 at the moment of extraction.

- **Identical bytes.** A later retrieval that returns the same bytes shares
  the earlier snapshot. Nothing is extracted again. The later retrieval date is
  itself the dated justification that the publisher still printed every statement
  of that snapshot on that date. [M2]
- **Identical text.** Bytes can differ where the text does not: a page that
  carries a new token or timestamp on every request. A new snapshot whose
  normalised text within the declared scope, under a named adapter version
  and furniture rule, equals that of the last extracted snapshot is treated
  as identical bytes: nothing is extracted, and the persistence of every
  statement is dated by the new retrieval and recorded as a restatement of
  the whole snapshot, carrying the adapter version so that replay
  regenerates the verdict. [M2]
- **New bytes.** A later retrieval whose normalised text differs forms a new
  snapshot, which is extracted in full, as if for the first time, under the same
  declared scope. Its statements cite the new snapshot. The statements of
  earlier snapshots are not touched. [M2]
- **Restatement.** A statement of the new snapshot whose item and verbatim
  content match a statement of an earlier snapshot of the same document is a
  restatement. It is kept, under its own snapshot, and linked to the
  statement where that content first appeared (its origin), never to the
  previous restatement, so every restatement is one step from its origin.
  The ledger can then answer every date on which a content was printed. A
  restatement is persistence, not corroboration. Restatement is judged
  between snapshots of one document only; statements of two editions or two
  issues of a series are paired as candidate matches (section 2). The
  *statements of a document*, wherever they are counted, are its origin
  statements; restatements are counted apart. [M2]
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
  across the periodic collection]
- **Absence.** An item of an earlier snapshot with no counterpart in the new
  one is recorded as unpaired. No statement is invented for it, and its
  absence is not read as a cancellation; that too is a judgement of fusion.
  [M2]

## 9. Identifiers and corrections

- A statement's identifier is minted when it is admitted and is independent
  of its attributes. It is never reused and never renumbered, whatever
  happens to the extraction method. [M2]
- A new snapshot's statements get new identifiers. An extraction that later
  finds an item it missed in an already extracted snapshot appends it under a new
  identifier; the identifiers of the other statements do not move. [M2]
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
  from its stored bytes by the current pipeline, and the output is compared with the
  statements of record, statement by statement and field by field. Every
  difference is classified: the pipeline is wrong (fix the pipeline), the
  statement of record is wrong (correct it by supersession), or the
  difference is legitimate and explained in words. An unexplained difference
  fails the replay.
- **Idempotence.** Running the pipeline again over a snapshot already extracted
  changes nothing: no statement added, altered or renumbered, and no
  disposition added.
- **The limit.** An LLM read, a transcription and a person's reading are not
  reproducible byte for byte, so replay and idempotence bind the parsers,
  the ingestion runs and the step that admits statements, not a fresh
  extraction. For statements produced by those methods, replay verifies instead
  that each locator still resolves in its bytes and that the text there
  still contains the label and values of record. Replay lists these
  statements by method, so the reach of the oracle is stated. Statements
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
statement's printed fields into that typed form. It is a step after
extraction, with its own methods and checks, and it never changes the
statement it reads. The Observatory's Statements page shows these
observations (step D3). [M3b for all rules of this section]

**Scope.** Reading is bounded by the results it serves. Only statements that
print a measure and belong to a declared counting scope (the strict scope
of a partnership, or a declared reference pool) are read into observations;
the others are listed, not counted. Matching is bounded the same way
([fusion](jetp-fusion.md) section 3): only statements that feed a declared
result are matched, against the top candidates per statement. Reading and
matching run on the two local readers ([operation](jetp-operation.md)
section 5: one model per GPU, the calibrated winners); a hosted model is
called only as the arbiter, on escalation.

**How many.** A statement yields zero, one or several observations, one per
measure it prints. A plan item that prints a capacity and a cost estimate
yields a `capacity` and an `estimate`; a heading that only groups items
yields none. Nothing is read that the statement does not print. A column
the publisher derives from another by a printed rate (an amount in US
dollars beside the same amount in rand) is the same measure, not a second
one: the reading rule declares which column is the original, and each
derived column becomes a conversion-rate record citing the statement when
the rate can be recovered, and nothing otherwise.

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
from the closed list of date roles of the [ontology](jetp-ontology.md)
(section 2, Observation), a precision (`day`, `month`, `quarter`, `year`, `unknown`) and
bounds. "Q1 2026" is precision `quarter` with bounds on the first and last
day of the quarter; "approved in 2024" is precision `year` with the year's
bounds. A date printed elsewhere in the snapshot and governing the statement,
such as a reporting cutoff on the cover of a register, becomes a timing that
names the statement it was read from, which is then the group heading or
another statement of the same snapshot. No date is invented: a value printed
without a date has only the timings the document gives. A figure printed as
cumulative or "to date" is a flow whose `period_end` is its as-of date and
whose `period_start` has precision `unknown`, bounded below by the
agreement's earliest printed date when one exists; fusion section 7 treats
it as a closing position, never a movement.

**Methods.** Three methods may read observations, each signing with its name
and version.

- A reading rule per series: a versioned mapping from a series' verbatim
  fields to measures, units and timings, used where a parser read the
  statements. It is preferred wherever a series repeats.
- An LLM reading of one-off statements, judged as in section 6.3: two
  readers from different model families on every observation, the arbiter
  on what they leave open, each observation ending with a stance, a
  likelihood and a confidence.
- A person, named as the method.

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
  automatically. The control document also carries a planted instruction
  addressed to the reader, which must not alter any proposal.
- **Calibration.** Each reader and the arbiter are scored on held-out
  reference answers before use; the set carries a planted misreading that
  each must reject, and a model that fails a positive control is weighted
  out. A prompt revised after reading a held-out item makes that item part
  of the tuning set, and the calibration is rerun without it.
- **Parts.** A fixture cut so that an item straddles the boundary of two
  parts yields one statement.
- **Retained layers.** Replay against a snapshot whose retained text layer
  is deleted and whose adapter version is unavailable fails loudly; it
  never reports the statements as unresolvable in silence.
- **The adapters** turn a corrupt or empty object into a disposition, not a
  crash.
- **Ingestion runs** fail on a snapshot whose records read differ in number
  from the count the service or file states (section 6.2).
- **The pending list** lists a snapshot with neither statements nor a
  disposition, and stops listing it once either exists; a run over a
  document with the disposition `duplicate` leaves nothing of it pending.
- **Document deduplication** finds a known mirror already in the document register
  before a null result on other documents is believed ([fusion](jetp-fusion.md)
  section 3).

## 13. The M2 slice

M2 is the minimum that extracts every held document correctly and traceably.
It comprises:

1. The preconditions of section 2: deduplication applied, languages
   recorded, canonical members and translation languages chosen by rule,
   the pending list as the input of every run. The document judgements
   still pending are decided, and in force, before the first run.
2. Statements carrying everything in section 3, including the method, the
   version, every reader's and the arbiter's answer, and any decision the
   author chose to make.
3. The text layers of section 5 for every format present among the held
   snapshots, each other format given a disposition that names it; the held
   scan transcribed (section 6.4); the held comparator snapshots read and
   replayed by the ingestion run of section 6.2, with its count control.
4. The four methods of section 6, with the automatic locator check and,
   for assisted readings, two readers from different model families on
   every row and the arbiter on what they leave open, both readers and the
   arbiter calibrated on held-out reference answers first.
5. The dispositions of section 7, so that every registered document ends
   with statements or a disposition with its reason.
6. The snapshot rules of section 8 with key-based pairing: a second dated
   snapshot of a living document appends dated statements, records
   restatements under both dates and leaves the earlier statements
   untouched. Since no held document has a genuine second version, the
   rule is tested on a fixture (a held snapshot with one value changed) and
   on the held page whose bytes change on every request, which must be
   treated as identical text.
7. The identifier rules of section 9.
8. Replay, idempotence and their stated limit (section 10), and the red
   tests of section 12.

After M2:

- **M3a** adds no extraction rule and keeps the M2 protocol of assisted
  readings. Discovery may bring formats or series not held at M2; they are
  extracted in M3b.
- **M3b** extracts the documents new since M2 with the same pipeline,
  extracts new comparator draws (CRS, IATI) as structured sources, and reads
  statements into observations (section 11).
- **M4** runs the pipeline on schedule from the pending list, pairs
  statements across snapshots without a publisher's key, and swaps the document store behind
  the same interface without changing an extraction method.
- **Later**: transcription of values shown only in charts, and derived
  translations of labels (never statements in their own right).

## 14. Open questions

- **The extraction acceptance level.** Default: "likely or more" on the
  calibrated scale (section 6.3); revisited once calibration has measured
  the observed precision of each likelihood term.

## 15. Checks an extraction must pass

Each check is a small constructed situation and the outcome a correct
extraction produces. An extraction that gives another outcome is wrong, whatever else it
does well.

| Situation | Correct outcome |
|---|---|
| A page is fetched again and the bytes are identical. | Nothing is extracted. The later retrieval dates the persistence of every statement of the snapshot. |
| A page is fetched again; the bytes differ only by a token the server changes on every request. | The normalised text is identical: nothing is extracted, and the retrieval dates the persistence of the snapshot's statements, with the adapter version recorded. |
| A register is fetched again; one amount changed, the other items are unchanged. | The new snapshot is extracted in full. Unchanged items are restatements linked to the earlier statements; the changed amount is a new statement beside the old one; no earlier statement is touched. |
| An item of the earlier snapshot is missing from the new one. | No statement is invented; the earlier item is recorded as unpaired, and nothing says it was cancelled. |
| The pipeline is run twice on the same snapshot. | The second run changes nothing. |
| A parser fix moves the locator of twelve items without changing what they say. | Their identifiers are kept through a reviewed mapping; nothing is renumbered. |
| A parser fix shows that one value was misread. | The old statement is superseded with the reason; results computed before remain reproducible. |
| A re-extraction finds an item the first extraction missed. | It is appended under a new identifier; the other identifiers do not move. |
| A report is held under the publisher's address and a partner's mirror, with the same bytes. | It is extracted once, from the canonical member; the other has the disposition `duplicate`. |
| A plan is held in English and in Vietnamese. | One language is extracted; the other has the disposition `translation_not_canonical`. |
| A dashboard's stored markup holds no data, which arrives by script. | Disposition `no_extractable_content`, reason "shell around a service"; collection may seek the data. |
| A decision is held only as a scan. | Collection searches for a born-digital copy (the official gazette, the ministry portal, the national legal database) and records the search; if one is found it is registered and extracted instead. Otherwise the scan is transcribed by a recogniser and two vision-capable readers, with the arbiter on escalation; every statement names the transcription as method, gives page and region, and records its likelihood and confidence; it is never skipped silently. |
| A figure appears only in a chart. | No statement; the extraction's scope note records the chart. |
| The LLM proposes an item whose quote cannot be found in the text layer. | The derived locator fails; one repair call is made; if it still fails, the arbiter sees the proposal marked as failed, the failure is recorded, and the proposal is not admitted. |
| The two readers agree on 40 rows of a Vietnamese plan at "likely" or more and differ on 3. | The 40 stand; the arbiter reads the 3 with both readings and the pages; all 43 end with a stance, a likelihood and a confidence, recorded with every reader's answer; nothing is queued for the author. |
| The arbiter cannot decide one of the 3. | The item ends undetermined, recorded and counted, not admitted; it is served among the least certain results. |
| A candidate reader fails its positive controls at calibration. | It is weighted out; no unattended run uses it. |
| A spreadsheet has a hidden row. | It is extracted, and its statement records that it was hidden. |
| A mirror was extracted before the publisher's own copy was found. | The mirror stays canonical; the publisher's copy has the disposition `duplicate`. |
| The LLM reader is given a document with a planted item and a named absent item. | The planted item is found; nothing is proposed for the absent one. |
| An appendix states it lists 37 items and the parser finds 36. | The extraction fails; no statement of that document is admitted until the difference is resolved or recorded as the publisher's own. |
| A figure of 3.92 is printed under the heading "USD billion". | The statement keeps 3.92 and the heading as printed; no conversion at extraction. |
| A register prints the status "B. In progress". | The word is copied as printed with its axis; no shared status is assigned. |
| A publisher counts 24 projects and names 3. | Three item statements and one count statement; nothing for the other 21. |
| A footnote conditions every row of a list. | A heading statement that the rows name as their group. |
| One cell names three funders. | One statement, the cell kept whole; the three parties are minted later by matching. |
| An item runs over a page break. | One statement whose locator spans both pages. |
| An object is served as a generic byte stream and is a PDF. | It is extracted as a PDF; the declared type stays on the retrieval. |
| A PDF is truncated. | Disposition `unreadable`, with the reason; the run continues. |
| A registered document has no bytes. | Disposition `no_snapshot`, whose reason cites the latest retrieval status. |
| An English version of a Vietnamese decision carries an annex the Vietnamese one lacks. | The content check of fusion section 3 finds the difference; the two are not a translation pair, and each is extracted as its own document. |
| Replay finds a difference nobody can explain. | The replay fails. |
| Replay meets a statement extracted by an LLM. | It is not regenerated; its locator is checked against the bytes and the statement is listed as outside the reach of replay. |
| A plan item prints a capacity of 50 MW and a cost of USD 120 million. | Two observations on the statement, a `capacity` and an `estimate`; no agreement and no identity. |
| A register prints "approved in 2024" and its cover gives a reporting cutoff of 31 March 2026. | One observation with two timings: `approval` at year precision, and `reporting_cutoff` at day precision naming the cover statement. |
| A cost field is blank. | Unknown, not zero; no observation value is invented. |
| A reading rule applied the "USD billion" scale twice. | A ledger error: the observation is superseded with the reason, and the rule's new version is rerun over everything it read. |
| A later snapshot prints a different amount. | A new statement and a new observation; the earlier observation is not superseded. |
| A project page prints "disbursements to date as of 30 June 2026: USD 40 million". | One flow observation of measure `flow`, type `disbursement`, with `period_end` on 30 June 2026 and `period_start` of precision `unknown`; not a movement on 30 June. |
