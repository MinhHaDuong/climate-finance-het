# JETP Observer: results and releases

A **result** is what the JETP Observer computes from the ledger: a count, an
account, a timeline, a gap between financial states, a descriptive table, a
list of excerpts. In the ODEM frame of the [language](jetp-language.md) it
is Evidence: it comes on top of Data and never edits it. A **release** is a
frozen package of results, the data they were computed from and the
Observatory pages that show them, identified once and never changed. The
release is the Observer's unit of citation.

This document states what a result must carry, how results are frozen into a
release, and how a release is identified, cited, corrected, restored and
finally archived. Each rule names the milestone that first needs it and, in
parentheses, the requirements of [purpose and
requirements](jetp-requirements.md) it serves. The minimum for one correct,
citable release is the M3b slice (section 13); monthly releases and the
attribution of change between them are M4.

## 1. Principles

**A result is reproducible or it is not a result.** Everything a result
depends on is named in it: the inputs, the times, the versions of the words
and of the methods, the thresholds applied to judgements. Given the same
names, the same result comes out, exactly for the deterministic parts; an
LLM reading is reproduced from its recorded output, not by reading again.

**Frozen bytes.** A release is a set of bytes. Once published, no byte of it
is replaced, whatever is found later. A correction is a new release beside
the old one.

**Pinned, never moving.** A citation points to a release and to the version
of the inputs it was built from, never to a current or latest address.

**One release, one view.** The Observatory shows one release at a time, and
everything it shows comes from that release.

**Declared, not implicit.** A choice that selects, weighs, thresholds or
converts is a declared method with a version, and a result names it; a
result never inherits a choice silently from the state of the ledger on the
day it was built.

## 2. What a result carries

Each result carries, in machine-readable form, the following. A result that
lacks one of them is not released.

**Its inputs, pinned.** The version of the ledger it was computed from,
identified so that the exact rows can be retrieved again, and the version of
the document store holding the snapshots those rows cite. *M3b* (Q8, Q19,
F32). A derived output of an earlier milestone, such as an extraction run,
names its input version in the same way. *M2* (Q19).

**Two times.** A result is dated twice (fusion § 1, Two times; § 8):

- *World time*: the time of the world the result describes, a date for a
  position ("disbursed as of 30 June 2026") or an interval for a movement.
  Statements whose events fall outside it do not enter it; a statement whose
  event date is an interval straddling the boundary blocks an exact figure
  (fusion § 7). *M3b* (F10, F16).
- *Knowledge time*: the knowledge cutoff K. The result uses only statements
  and judgements admitted on or before K, and each chain of judgements is
  taken to its state at K. *M3b* (F10).

**The ontology version** under which it was computed, identified so that
the definitions of every term, measure and perimeter in force can be
retrieved as they stood. A result is never recomputed under a later ontology
without becoming a new result. *M3b* (Q9, OBS-4).

**Its method versions.** Every method that selected, weighed, transformed or
counted: the extraction and reading methods of the statements it uses, the
proposers and the rule that turned readings into judgements, the counting
scope, the account rules, the conversion rule. *M3b* (Q9).

**Its match threshold.** The likelihood and confidence a candidate match, an
occurrence, a coverage or a compatibility judgement needs in order to count
(fusion § 3, Threshold per result). The candidate matches below the
threshold that would have changed the result are listed and counted apart.
*M3b* (F11).

**Likelihood and confidence where judgements enter.** A result resting on
judgements carries, or resolves to, the calibrated likelihood and confidence
of each judgement it counted, on the scales of fusion § 1. *M3b* (Q5, Q11).

**Uncertainty as ranges.** A value is a range where its inputs are: rounded
inputs carry their bounds, a date its interval, a figure at two match
thresholds its low and high values (section 3). An unresolved disagreement is
carried with both values and the condition that blocks comparison. Unknown
is never zero, and a figure blocked by an open question is reported as
blocked, with the reason, while the others stand. *M3b* (Q11, F6).

**Its unit and population.** Every count names its unit (statements,
referents of a kind, a publisher's stated count) and its perimeter or
counting scope; every sum names the financial state it selects and its
currency (fusion § 6–7). A result that counts by shared status or sector
states the weakest mapping strength among the crosswalk rows it used
(ontology § 5). *M3b* (F13, F14, F15).

**Its origin kind.** Whether each number is the Observer's calculation or a
figure a publisher printed, each with its own attribution. *M3b* (Q12, Q16).

**Its trail.** A result resolves to the statements and the named calculation
it rests on, down to the snapshot bytes and locators that support them; and
from any statement the results that use it can be listed. The latest
snapshot of a document never stands in for the one that supported an older
statement. *M3b* (Q6).

**An identifier stable within its release.** A figure, a table cell or a
sentence of the Observatory or of a paper is cited as the pair of the
release identifier and the result's identifier. *M3b* (Q6).

The kinds of result the M3b release must contain are those the requirements
name: counts per country, state and scope (F13); accounts, the opening,
movements, closing and residual of fusion § 7 (OBS-1, F19); operation
timelines (F16); the gaps between announced, signed, reported and disbursed
amounts and the matching coverage rate to CRS and IATI (F19, fusion § 5);
lists of excerpts for qualitative work (F21); and the coverage report
(DP-3). Other results are added when a product needs them. Accounts at M3b
are in the publishers' currencies and current prices: deflators are
deferred. The Markers account and its coefficients (fusion § 7) are M4,
unless the comparison of F19 uses CRS climate-marked amounts, in which case
they are M3b.

## 3. Two match thresholds

A result whose figure depends on identity, occurrence or coverage judgements
is computed at two match thresholds, both declared in advance:

- a **cautious** threshold, counting only what the judgements support strongly
  (default: likely or more, medium confidence or more);
- an **inclusive** threshold, counting also what they support weakly (default:
  about as likely as not or more, low confidence or more).

Both are conjunctions of a likelihood of sameness and a confidence level
(fusion § 3); an undetermined judgement counts at neither. The result's
range runs from the smaller to the larger of the two figures; which
threshold gives which end depends on the kind of result, since accepting
more matches raises a sum of matched amounts but lowers a count of referents
or a de-duplicated sum. The range is the result's sensitivity to the
declared thresholds, not a probability interval on the true value. Where the
two figures coincide, one figure is shown with the note that matching does
not move it. The candidate matches between the two thresholds are listed
with the result. *M3b* (F11, Q11).

A result may declare a single threshold when it does not depend on matching;
it says so. The two defaults are method choices with a version, set by the
author before the M3b release and not moved afterwards without a new
version.

## 4. What a release contains

A release is complete when it contains all of the following. *M3b* unless
stated.

- **The data**: every table of the ledger that the storage contract serves
  (storage contract § 2), frozen at the release's knowledge cutoff, and the
  definitions of the terms in force (the glossary). (F23, F32)
- **The results** of section 2, each with its metadata.
- **A data dictionary** defining every field of every file. (F31)
- **The method list**: every method and version named by a result, with
  a pointer to its specification. (Q9)
- **Provenance** in machine-readable form: for every statement, the hash of
  the snapshot it was extracted from, its locator and its extraction method; for
  every result, its inputs, times and versions. (F32)
- **The collection record**, carried from the M3a collection report that
  the author accepted (collection § 12): the declared protocol and its
  recorded revisions, the round log, the terminal verdict of every expected
  authority and listed project, the statement "stopped by cap" with the
  unmet conditions when a cap stopped discovery, the discovery cutoff, the
  newest document date, the recall estimate, the tracker traceability rate
  with the distribution of claim outcomes, and the list of documents and
  search channels that could not be reached, with the reason. (F8, F9, DA9,
  Q10)
- **The redistribution list**: for every document, whether its bytes are in
  the release or only cited, on which terms, and its public copy:
  redistributed bytes, a public archive capture, or none with the reason
  (section 7). (C6, F27)
- **The share of support by public copy**: for each result and for the
  release as a whole, the share of the supporting statements whose document
  has its bytes redistributed, a public archive capture, a live address
  only, a registration route only, or no public copy. (Q8, C6, F27)
- **The validation and coverage reports**, and an editorial note in plain
  language saying what the release contains and what it does not. The
  validation reports include the calibration record of every method version
  the release uses, with its agree-but-wrong rate and calibration error per
  stratum ([extraction](jetp-extraction.md) § 6.3). (Q5)
- **The cost record**: LLM spend and compute time per document class,
  document type and extraction method. (Q15, AED-3)
- **The Observatory pages** of the release, built from the release alone and
  readable from its files alone. (C7)
- **The descriptor** (section 5). The deposit's metadata record (section 6)
  is not part of the frozen package: it sits beside it in the deposit and is
  the one place that later gains citations, supersession pointers and a
  status.
- The count of error reports received and corrections made since the
  previous release. *M4* (F25)

A release states four dates, and keeps them apart: its knowledge cutoff; the
world time its headline results describe; the discovery cutoff (the date of
the last search, on or before the knowledge cutoff); and the newest document
date. The publication date is a fifth, recorded in the descriptor. *M3b*
(F9, F10).

## 5. How a release is built

**Inputs first, descriptor after.** The inputs of a release are frozen and
committed before it is built: the ledger rows, the ontology, the method
settings, the editorial texts. The package is built from that committed
state, verified, and only then is the descriptor written and committed,
naming the input version. The descriptor is never part of the inputs it
describes, and no file of the package refers to the descriptor's hash.
*M3b* (Q8, Q19).

**The descriptor** pins the written bytes. It records:

- the release identifier, the previous release, and the release it supersedes
  when it is a correction, with the rows of its correction overlay (section
  9);
- the four dates of section 4, the publication date and the named reviewer
  who accepted it;
- the full input version and the pinned version of the document store;
- the ontology version, the schema version and the method versions;
- every file of the package, with its relative path, byte size, SHA-256 hash
  and immutable address;
- the licence, the redistribution exclusions and the persistent identifier;
- references to the validation and coverage reports and the editorial note.

A branch name, a moving address or a pointer to the document store alone
does not identify a release. *M3b* (Q8, F32).

**Named formats.** The descriptor is a Frictionless Data Package
(`datapackage.json`), one resource per file, each shard its own resource
with its own hash; the data dictionary is its Table Schema for each file,
generated from the DDL for the common tables and from `line-field-specs`
for the per-document fields tables. The metadata record is the DataCite
record deposited through Zenodo, which relates the release chain and the
code (IsNewVersionOf, IsPreviousVersionOf, IsSupplementTo) and a correction
to what it corrects (IsObsoletedBy, Obsoletes). The persistent identifier
is reserved before the build, so the descriptor can name it. RO-Crate, with
W3C PROV for the run record, is the M4 option. *M3b* for the Data Package
and DataCite; *M4* for RO-Crate (F29, F31).

**Validation before publication.** The build checks, before anything is
published, that every result carries section 2 in full, that every trail
resolves, that every file listed exists with its hash, and that the
redistribution list excludes every document whose terms forbid it. A failed
check stops the build and publishes nothing. The validation also screens the
release's text for email addresses and telephone numbers, and the speaker
and verbatim fields of prose statements for the names of natural persons
other than signatories printed as such. Each hit is judged under the
protocol of extraction § 6.3: a natural person's contact details, or a name
recorded where the office should be (extraction § 4), are removed by
supersession and recorded as readings; the build report counts the hits,
and nothing is queued. *M3b* (Q6, Q8, C6, N2).

**A reviewed act.** No program publishes a release on its own. A named
reviewer accepts the validated package; acceptance is recorded in the
descriptor. *M3b* (N4, N6).

**The current release advances last.** The address that points readers to
the current release moves only after the complete release has passed
validation and been accepted, so a failed build leaves the last accepted
release in place. *M3b* (Q8).

**Rebuildable.** Any release can be rebuilt from the repository at its input
version and the archived documents, byte-identical for its deterministic
parts; recorded LLM readings are reused, never redone. *M3b* (Q4, Q19).

## 6. How a release is identified

**Release identifier.** A regular release is named `YYYY-MM`, the year and
month of its knowledge cutoff. A correction is `YYYY-MM-rN`, where N is an
ordinal counted from r1, keeps the knowledge cutoff of the release it
corrects, and names the release it supersedes. Every file of a release
carries its identifier. *M3b* (Q8).

**Persistent identifier.** Each release is deposited in a public data
repository under a persistent identifier that resolves to the deposit, and
whose metadata remains resolvable even if the data must be withdrawn. The
release identifier and the persistent identifier are recorded in each
other's metadata. *M3b* (F28).

**Metadata.** The deposit carries a metadata record in the DataCite schema,
deposited through Zenodo, with at least: title, creator, publisher (as the
legal review names it), resource type, version (the release identifier),
countries, discovery cutoff, newest document date, knowledge cutoff, method
versions, licence, the related persistent identifiers (the previous release,
the superseded release, the code), the papers that cite it, added as they
appear, and, as a version note since DataCite has no status field: current,
superseded by a named correction, or withdrawn with the reason. *M3b* (F29).

**Licence.** The release is published under an open licence that requires no
more than attribution, stated in its metadata and in its files; the code
that produced it is under an open-source licence, stated likewise. *M3b*
(F30, C5).

**Open formats.** Tables are in open, plain-text formats readable with free
software; every field is in the dictionary (the Table Schema of section 5);
country, currency, organisation, CRS and IATI codes follow their external
standards or are marked as local. *M3b* (F31).

## 7. What is redistributed and what is only cited

The Observer publishes what it made and cites what others made. The legal
basis for each case (short quotation assessed per use, database right
assessed per table and producer, public-sector re-use, per-publisher terms)
and the export review at each release are stated in the [legal
note](jetp-legal-note.md) §2 and §6. The open licence of the release (CC BY)
covers the Observer's own contributions; publisher text reproduced in the
release (verbatim labels, excerpts, the per-document fields) is quoted data,
reproduced under attribution to its publisher, and is not relicensed. Each
retrieval records the site's terms position, robots position and the free
registration used, and each document its access route kind (storage
contract § 1, target schema), so that the redistribution list reads its
cases from the ledger. *M2* for the columns; *M3b* for the redistribution
list (C6, F27, F30).

- **Redistributed**: the Observer's own tables, results, dictionary,
  provenance, reports and pages; the statements, including their verbatim
  labels and short excerpts, each attributed to its publisher, document and
  locator. *M3b* (F21, F30).
- **Redistributed only where the publisher's terms allow**: the bytes of a
  document, and the records of a structured search channel. Where the terms
  do not allow it or are unknown, the release carries the address, the
  public archive record if one exists (the capture recorded with the
  retrieval), the hash and the locator. The redistribution list states, for
  every document, which case applies and why, and whether a public copy
  exists; the reconstruction test of Q8 is stated over documents that have
  one. *M3b* (C6, F27).
- **Never in a release**: closed material of any kind, and credentials.
  *M2* (N13, C9).

Terms unknown are treated as terms that forbid redistribution. *M3b* (C6).

## 8. How a release is cited

**A product pins a release and its input version.** A paper, a chapter of
the book or a report cites the release identifier and its persistent
identifier, and records the input version beside it, never a current or
latest address. Its own sample selection and code carry their own version
references beside the release. *M3b* (Q8, BK-2, DP-4).

**A figure is cited by its result.** A figure quoted in a product resolves
to a result identifier in the pinned release; a figure that does not is
the product's own calculation and says so. A product citing a release
supplies a machine-readable list of the results it quotes, as pairs of the
result identifier and the place of the quotation in the product; the list
is kept with the release's metadata (F29) and not served (F23), and the list
of claims a correction touches (section 9) is produced from it. *M3b* (Q6,
Q7, Q12).

**One release per writing period.** A long work, such as the book, may pin
one release for its whole writing period; a later release changes nothing in
it. When the work moves to a later release, it moves every figure at once,
and the change of each figure is explained as in section 11. *M3b* (BK-2).

**Products show the dates.** A product citing a release states its discovery
cutoff and newest document date. *M3b* (F9).

## 9. Correction and restoration

**A correction is a new release.** When an error is found in a published
release (a misread value, a false match, a faulty rule, a missing file), the
correction is published as a new release `YYYY-MM-rN` that names what it
supersedes and why. It keeps the knowledge cutoff K of the release it
corrects and applies a named correction overlay: the supersession rows that
correct ledger errors, recorded after K, in rows recorded on or before K
(fusion § 8). Nothing else recorded after K enters it. The bytes at the old
release's addresses are never replaced, and its persistent identifier keeps
resolving to them; the old deposit's metadata record, not its package, gains
a pointer to the correction and the status "superseded". *M3b* (Q8, F28).

**Withdrawal.** When a release must be withdrawn (a legal demand, content
that should never have been published), the author removes its Observatory
pages and asks the repository to remove its files, which only the
repository can do, leaving a record to which the persistent identifier
resolves; its descriptor, file hashes and reason are kept, and the version
note says "withdrawn" with the reason. A withdrawal is followed by a
correction release where the data allow one; history is never rewritten. A
banner on the pages of an earlier release that points to its correction is
M4. *M3b* (F28).

**A correction reaches every claim it touches.** Before a correction is
published, the list of results, Observatory pages and cited figures it
changes is produced from the trails, and the correction's editorial note
lists them. *M3b* (Q7, Q6).

**A reported error ends in a judgement.** An error reported by a publisher or
a reader is recorded and answered by an accepted or rejected judgement (fusion
§ 2). An accepted report that changes a released figure produces a
correction release `YYYY-MM-rN`; otherwise it enters the next regular
release. Either names the report. Each reported error is one ticket, and
the ticket number is the report identifier cited from the correction row;
the reporter's identity stays in the ticket and no personal data enters the
ledger ([operation](jetp-operation.md) § 4). A report ends in one of three
outcomes: a ledger error accepted and corrected; rejected, with the reason;
or reported, awaiting a public source, when only a publisher's revision not
yet public would settle it (N13, F27). A request to remove personal data or
content (a takedown) is a report like any other: when granted, the ledger
rows are superseded with the reason and released content is withdrawn as
above, followed by a correction release. *M3b* for tracing, *M4* for
publishing the counts and a table derived from the tickets (F25).

**Restoration after a failed publication.** When a publication fails midway,
the last accepted complete release is served again, whole. A failed
publication is never repaired by replacing a few files of the live site, by
re-enabling a retired writer, or by reversing a migration. Restoring the
Observatory rolls back nothing in the ledger: newer statements and
judgements, and who made them, are kept for the next release. A restored
release shows its own, real cutoffs, not the date of the restoration; any
fix is a later release. *M3b* (Q8, Q19).

## 10. The Observatory as a view of one release

The Observatory shows exactly one release at a time. *M3b* (C7, Q8).

- Every page states the release identifier, its knowledge cutoff and its
  discovery cutoff, and links to the release's deposit.
- Every number, status and narrative claim on a page resolves to a result or
  a statement of that release; the site computes nothing the release does
  not contain and fetches nothing from outside it.
- A page of an earlier release remains readable at an address that names
  that release, so a link cited in a product keeps showing what it showed.
  *M4* for serving earlier releases beside the current one; at M3b, the
  deposit of each release suffices.
- A corrected current account never silently refreshes a released page: a
  page changes only when a new release is published.

## 11. Change between releases

From the second regular release onwards, each release explains how it
differs from the previous one. *M4* (F22, OBS-5, DP-5).

- Every figure that differs between two consecutive releases carries an
  attribution to the reasons of fusion § 8. Where several reasons combine,
  the change is split into parts, each with one reason.
- A change of method is isolated by recomputing the previous release's inputs
  under the new method, so that what the method changed is told apart from
  what the new inputs changed.
- A failed retrieval is not a change in the world: a referent present in the
  previous release is kept in the next one, with its last known state and
  the failed retrieval recorded, unless a judgement retires it.
- A release with no scientific change is a legitimate release and says so.

The cadence of regular releases (monthly), the review calendar and the
reviewer's duties belong to Operation. *M4*.

## 12. Horizon and final release

The Observer is maintained to a declared end: by default through 2030, with
a decision on extension in 2028. At the end, a final release is published
and archived like every other, with an editorial note stating that no
further release will follow. After the end, every release that a product
cites keeps resolving through its persistent identifier, and its Observatory
pages remain readable from the deposited files alone. *M4* (C10, C7).

## 13. The M3b slice

The first correct, citable release needs, and needs only: results that
carry section 2 and section 3, with the collection record of the M3a
collection report; one release built inputs first and descriptor after,
validated and accepted before the current release advances (sections 4 and
5); a persistent identifier, a harvestable metadata record, an open licence
and open formats (section 6), with document bytes redistributed only where
terms allow (section 7); citation by release and input version, and
correction as a new release that lists the claims it touches (sections 8
and 9); an Observatory that shows that one release and nothing else
(section 10). Everything else here is M4.

## 14. Checks a release must pass

Each check is a constructed situation and the outcome a correct release
process produces.

| Situation | Correct outcome |
|---|---|
| A candidate match judged "about as likely as not" joins two projects. | The project count differs between the inclusive and the cautious threshold; the candidate is listed between the two. |
| An error is found in release `2026-11` after publication. | A new release `2026-11-r1` names what it supersedes and keeps the cutoff of `2026-11`; the bytes of `2026-11` are unchanged, and its deposit's metadata record points to the correction. |
| A ledger error in a row of `2026-11` is corrected after its cutoff, when new statements have also been admitted. | `2026-11-r1` carries the correction as a named overlay row and none of the new statements. |
| A line is extracted after the cutoff of `2026-11` from a snapshot retrieved before it. | It is a new line, not a correction: `2026-11-r1` does not carry it, and it first counts in the next regular release. |
| A revoked match touches three country totals and one paper figure. | The correction's editorial note lists all four before it is published. |
| The build of a new release fails halfway through writing the site. | The previous accepted release is served whole; no page mixes the two; the ledger keeps its newer rows. |
| A release is restored a week after its cutoff. | It shows its own cutoffs, not the restoration date. |
| A paper cites "the latest data" at the Observatory's current address. | Not a valid citation; the paper must pin a release identifier and its input version. |
| The book pins a release; two later releases revise a figure it quotes. | The book's figure still reproduces from its pinned release. |
| A figure rises between two releases because of a new disbursement and a revised match. | M4: the change is split into a development in the world and a changed interpretation, each with its share. |
| A living page could not be fetched for the new release. | M4: the referents it supported stay, with their last known state and the failed retrieval recorded. |
