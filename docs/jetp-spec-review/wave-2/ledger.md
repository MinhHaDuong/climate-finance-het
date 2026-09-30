# Specification review wave 2: findings ledger

Specification at commit d4dd1ef8 (main, draft v0.2). Seven lenses, reviewers
on Fable, each lens verified on Sonnet, deduplicated into 57 rows by a Fable
ledger agent (batch 1, W2-01 to W2-57); three external reviews of the same
draft on OpenRouter (batch 2, E2-01 to E2-09, only the findings new to both
ledgers that passed the merge rules). The merge rules are in the
[README](README.md).

## Summary

Batch 1: 54 applied (13 of them in part, the rejected part and its reason in
the row), 0 rejected whole, 2 deferred to M4 (W2-46, W2-55), 1 decided by
the author's default (W2-04, 2026-09-30). Batch 2: 8 applied, 1 folded into
W2-04; 21
groups of external findings not admitted, listed with their reasons. The
blocker W2-01 is applied, so the ledger agent's verdict ("no: one blocker
remains") becomes: ready for the author's acceptance; W2-04 took its default on
2026-09-30.
The specification did not grow: docs/jetp-*.md held 82 773 words before the
merge and 82 727 after (wc -w).

The ledger agent's own summary, as produced (`ledger.json`):

1. One blocker, found by all seven lenses: W1-01's decided fix landed by half. The readings and runs journals exist, but the storage contract has no `dispositions` table and `lines` has no status, supersedes or hidden column, so the pending list, F2's count, the correction overlay and the in-force rule for lines have nothing to run on and a DDL builder would invent them (W2-01, agent-applicable in one storage-contract commit).

2. Two other wave-1 fixes were applied as sentences without the record or key they need (restatements have no home and the identical-text snapshot never leaves the pending list, W2-02; the field-list key 'document class or series' collides with the reserved M3a class, W2-03), and the autonomy correction left pre-autonomy text standing in storage §4 matching, operation §5 to §7 cost bases and provider keys, operation §4's prohibition on admitting documents, and results §5's personal-data screen (W2-16, W2-17, W2-26, W2-41).

3. The M2 assisted-reading loop is under-stated exactly where it is now unattended: the held-out set cannot be derived, matched or stratified for the documents M2 reads and has no start rule (W2-04); the reading-to-judgement rule, the alignment rule, the calibration of the installed quantised artifact and the transcription of the one held scan are named but not stated (W2-05 to W2-09); recall is measured nowhere (W2-08); and three journal rules fail on the first run (killed run, single-reader admission, file ceiling: W2-11, W2-12, W2-21).

4. M3a and M3b are under-specified rather than wrong: triage needs bytes before admission and the schema forbids it (W2-15), archive captures have two homes and no rule makes one (W2-43), F18's transition functions exist in no document (W2-18), context-only documents never enter a release (W2-42), and the deposit's status and withdrawal are not what Zenodo and DataCite can carry (W2-52).

5. Four rows need the author (W2-04 calibration fallback or one blind labelling sitting; W2-09 a hosted vision pair for the one scan; W2-17 who sees personal-data hits; W2-43 archive-capture requests at retrieval), each with a recommended default; the other 53 rows are agent-applicable wording, target rows, terms lists and cross-references whose proposals converge across lenses. Merged 90 lens findings into 57 rows: 1 blocker, 17 major (14 M2, 1 M3a, 2 M3b), 39 minor.

Commits are cited by subject: (A) "dispositions and restatements journals, line status, journal corrections"; (B) "the reading protocol stated once, in extraction 6.3"; (C) "autonomy residue, cost bases after local readers, Zotero at M2"; (D) "collection rules for M2 scans, admission, captures and blind lists"; (E) "M3b gaps: transition functions, pledge, deposit status, word list"; (G) "DA5 counts the documents with no language over the whole register"; and (F) "cut duplicated rules and provenance prose to pay for wave 2".

## Question for the author (W2-04)

The calibration set is the hand-made lines (about 130 today: Indonesia and
Senegal, English and French, almost all named items). It holds no Vietnamese
prose, no South African prose and no transcription, and no human reads any
more, so those strata stay uninformative unless answers are made; the prose
they miss is where most M2 statements are (pending: South Africa 49, Senegal
28, Viet Nam 25, Indonesia 13). What does an unattended run do in a stratum
with no informative calibration?

- (a) Run with a declared fallback: the stratum's items use the pooled
  mapping of their language (else the global one), every one of them goes to
  the arbiter whatever the agreement, and the run report and every release
  name the stratum as uncalibrated, listing strata by size.
- (b) One labelling sitting before the first unattended run, blind to any
  machine reading: at least 30 held-out items each of Vietnamese prose and
  South African prose in the target shape (about two to three hours), then
  (a) for the rest.
- (c) Block M2 until every stratum of the pending set reaches 30. Not
  recommended: it recreates the attention bottleneck the autonomy rule
  removed.
- (d) Coarsen the strata to language x statement shape (table row, record
  page, prose span, transcription), so that pooled strata can reach 30
  sooner (external finding E2-09); combinable with (a) or (b).

Recommended default: (a), with (d) as the stratification it reports on, and
(b) offered as the one sitting that would make the M2 calibration record say
something about the documents M2 reads. Until decided, nothing of W2-04 is
applied; its author-independent parts (the person-versus-assisted flag on
legacy lines, the match rule between a proposal and a paraphrase reference
line) wait with it, since they depend on which set is calibrated.

## Rows, batch 1

| ID | Severity | Milestone | Outcome |
|---|---|---|---|
| W2-01 | blocker | M2 | applied |
| W2-02 | major | M2 | applied in part |
| W2-03 | major | M2 | applied |
| W2-04 | major | M2 | default accepted by the author 2026-09-30 |
| W2-05 | major | M2 | applied in part |
| W2-06 | major | M2 | applied |
| W2-07 | major | M2 | applied |
| W2-08 | major | M2 | applied |
| W2-09 | major | M2 | applied |
| W2-10 | major | M2 | applied |
| W2-11 | major | M2 | applied in part |
| W2-12 | major | M2 | applied |
| W2-13 | major | M2 | applied in part |
| W2-14 | major | M2 | applied |
| W2-15 | major | M3a | applied |
| W2-16 | major | M3b | applied |
| W2-17 | major | M3b | applied |
| W2-18 | major | M3b | applied |
| W2-19 | minor | M2 | applied in part |
| W2-20 | minor | M2 | applied in part |
| W2-21 | minor | M2 | applied in part |
| W2-22 | minor | M2 | applied |
| W2-23 | minor | M2 | applied |
| W2-24 | minor | M2 | applied |
| W2-25 | minor | M2 | applied in part |
| W2-26 | minor | M2 | applied |
| W2-27 | minor | M2 | applied |
| W2-28 | minor | M2 | applied |
| W2-29 | minor | M2 | applied |
| W2-30 | minor | M2 | applied |
| W2-31 | minor | M2 | applied |
| W2-32 | minor | M2 | applied in part |
| W2-33 | minor | M2 | applied |
| W2-34 | minor | M2 | applied |
| W2-35 | minor | M2 | applied |
| W2-36 | minor | M2 | applied in part |
| W2-37 | minor | M2 | applied |
| W2-38 | minor | M2 | applied in part |
| W2-39 | minor | M2 | applied |
| W2-40 | minor | M2 | applied |
| W2-41 | minor | M3a | applied |
| W2-42 | minor | M3a | applied |
| W2-43 | minor | M3a | applied in part |
| W2-44 | minor | M3a | applied |
| W2-45 | minor | M3a | applied |
| W2-46 | minor | M3a | deferred to M4 |
| W2-47 | minor | M3a | applied |
| W2-48 | minor | M3b | applied |
| W2-49 | minor | M3b | applied |
| W2-50 | minor | M3b | applied in part |
| W2-51 | minor | M3b | applied |
| W2-52 | minor | M3b | applied |
| W2-53 | minor | M3b | applied |
| W2-54 | minor | M3b | applied |
| W2-55 | minor | M3b | deferred to M4 |
| W2-56 | minor | M3b | applied |
| W2-57 | minor | M3b | applied |

### W2-01 (blocker, M2)

*Lenses:* within-file, cross-file, state-of-the-art, data-held, data-to-come, implementation, dead-angles. *Files:* jetp-ledger-storage.md §1 (target schema, `lines` row, Times per table), §2; jetp-extraction.md §2, §5, §7, §9, §12, §15; jetp-ontology.md §4; jetp-language.md D2; jetp-requirements.md F2, F5, F23

**Finding.** W1-01's decided fix landed by half. The storage contract has no
`dispositions` table, current or target (the word does not occur in it),
although extraction §7 makes a disposition a record with kind, reason,
decider, method, version, time and supersession, the pending list (§2, F5),
F2's count, DA2's acceptance, the run-output gate and the decision-authority
table are all defined over dispositions, and the ontology lists no
disposition kinds as terms. `lines` gained run_id, method and method_version
only: no `status`, `supersedes` or `hidden`, although §9 and §15 supersede a
misread line, §4 re-anchors the 261 legacy prose lines by supersession, the
Times-per-table row lets an overlay correct `lines`, and §5/§12 require a
hidden-markup flag. The in-force rule is written for decision rows only, so
what 'in force' means for a line is undefined. Seven lenses found it
independently; a DDL builder would invent both, which is what W1-01 was
meant to stop.

**Proposed fix.** Storage §1 target [M2]: add a `dispositions` journal
(disposition_id, document_id, sha256 nullable, kind as a `terms` row,
reason, method, method_version, run_id, decided_by, decided_at, recorded_at,
status, supersedes) under the in-force rule, with a validator check that the
kind's applies-to (document or snapshot) matches sha256 nullness, a Times-
per-table row (enters the state by recorded_at, overlay yes), an F23 served-
or-not line and a language D2 entry; let a `readings` row point to the
disposition it proposed. Add `status`, `supersedes`, `hidden` (set by the
adapter) and `adapter_version` to the `lines` target row [M2], state that a
line is in force under the same chain rule as a decision row and that counts
read in-force lines only, with a DDL test that a superseded line is absent
from the in-force view and present in the as-of state before the
supersession. Define the pending list (extraction §2, §12) over snapshots,
in-force lines and in-force dispositions. Add the eight disposition kinds as
`terms` rows (ontology §4). Add both to ticket 1702's exit criteria and
record in the wave-1 ledger that W1-01 (a) and (b) were applied here.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections": `dispositions` journal and the `lines` columns
`status`, `supersedes`, `hidden`, `adapter_version` as M2 targets, the in-
force rule extended to lines and dispositions, counts over in-force lines,
the pending list over in-force rows (extraction 2), the D2 row of the
language document; ticket 1702 exit criteria added. The disposition kinds
become `terms` rows with the DDL (exit criterion), not in the ontology now,
which spares the terms table and its derived views a change no M2 rule reads
yet. Wave-1 ledger W1-01 annotated.

### W2-02 (major, M2)

*Lenses:* within-file, cross-file, state-of-the-art, data-held, data-to-come, dead-angles. *Files:* jetp-extraction.md §2, §7, §8, §12, §13 item 6; jetp-ledger-storage.md §1 (target schema, Times per table), §4; jetp-ontology.md §3; jetp-requirements.md F4, F5, F13, Q2

**Finding.** The two M2 records introduced by W1-14's fix have no home: the
line-to-origin restatement link (star, depth one) and the whole-snapshot
restatement of an identical-text snapshot carrying the adapter version.
Ontology §3 has no restatement relation (`same_as` between lines means the
same published item in two places, not persistence), the storage target
schema lists neither (W1-14's outcome says the target was written; it is not
there), and storage §4 tags line matching M3b while extraction §8 makes key-
based pairing across snapshots M2. Worse, an identical-text snapshot 'needs
neither statements nor a disposition' (§7) yet §2 defines pending as no
statements and no snapshot-level disposition, so the held nonce page (zaf-
ntcsa) is pending on every run, F5's test and Q2 idempotence fail on the
fixture M2 must pass, and from M4 every unchanged weekly refetch accumulates
as pending.

**Proposed fix.** Ontology §3: add `restates` [M2] (line to origin line,
depth one; snapshot to the last extracted snapshot, adapter version in
method_version) as a `terms` row, and say persistence is a record, not a
`same_as`. Storage §1: a target row [M2] for both records (a `relations` row
or a small table with sha256, restates_sha256, adapter_version, run_id,
retrieval_id) with its Times-per-table line, and a validator check that a
restatement's target is an origin, never another restatement. Extraction §2
and §12: a snapshot cited by an in-force whole-snapshot restatement is not
pending; add the control that refetching the nonce page leaves nothing
pending and adds one restatement row. Storage §4: retag 'M2 for key-based
pairing across snapshots of one document; M3b for other line matching'.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections": one `restatements` journal holds the line-to-
origin link and the whole-snapshot restatement with its adapter version; a
snapshot with an in-force restatement is not pending; storage 4 retags key-
based pairing across snapshots M2. Rejected in part: a `restates` ontology
relation and term (the journal is the home; a term would change the terms
table for no rule that reads it); the extra section 12 control (the M2 slice
already tests the nonce page).

### W2-03 (major, M2)

*Lenses:* within-file, cross-file, data-held, dead-angles. *Files:* jetp-extraction.md §3 (Verbatim fields), §4, §6.3 (Two readers, Replacement readers), coverage report; jetp-ledger-storage.md §1 (`line-field-specs`); jetp-language.md (reserved term 'document class'); jetp-requirements.md Q15

**Finding.** W1-12's decision keys the fixed field list and the declared
scope on 'document class or series' (four occurrences in extraction), but
'document class' is a reserved term of the language document meaning frozen,
living or series, assigned as a dated judgement only from M3a (collection
§10, operation §8, `documents.class` M3a target). A field list keyed on
frozen/living is meaningless (Decision 1009 and the ZAF plan would share the
ADB project page's list), and at M2 the 115 pending documents have no class,
so the M2 method version cannot declare the lists the decision requires; the
reader ends up declaring them, which is the defect the decision removed
(spike: 57/59 kept became 13/46 after one reader-chosen field change). §4
also never says who declares the scope of a one-off document, and no storage
row holds the class-level or series-level list `line-field-specs` copies
from. Q15 and §6.3 ('which method version read each document class') carry
the same collision.

**Proposed fix.** In extraction §3, §4, §6.3 and the coverage report, and in
Q15, replace 'document class or series' with 'document type (ontology §2) or
series', a series overriding its type's list; leave 'document class' to the
DA6 sense everywhere. Define the versioned unit that holds the field list
and the default scope per (document type, or series), declared by the method
version, never proposed by a reader, and extend `line-field-specs` with the
unit each per-document list was copied from. State that the scope of a one-
off document is declared by the run's method version from the type's
default.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections" (`line-field-specs` names the type or series
its list came from) and (B) "the reading protocol stated once, in extraction
6.3" (field list and default scope keyed on document type or series, a
series overriding its type; "document class" left to its reserved sense).
Q15 is unchanged: its "document class" is the DA6 sense, which the M3b cost
record legitimately uses.

### W2-04 (major, M2)

*Lenses:* within-file, state-of-the-art, data-held, implementation, dead-angles. *Files:* jetp-extraction.md §6.3 (Reference answers, Calibration), §12; jetp-operation.md §5 (Selection and calibration); jetp-ledger-storage.md §1 (identifier families); jetp-results.md §4; jetp-requirements.md Q17

**Finding.** The calibration gate, since the autonomy rule the only human
check and the precondition of every unattended run ('no unattended run
starts before them'), cannot be met as written. (a) The set is not
derivable: storage's decision-scoped families mix a person's reading and an
assisted reading with no flag, so hand-made lines cannot be separated from
LLM-assisted ones. (b) It is not matchable: the hand-made prose lines have
composed labels and paraphrase locators under a legacy method while a
proposal is a shortest verbatim span with code-derived anchors, and no rule
says when a proposal hits a reference line, so per-term precision,
calibration error and the agree-but-wrong rate are undefined. (c) Measured
on the ledger, the hand-made lines number about 130 (Indonesia 84, Senegal
46, English and French, 128 `named_item`, 2 `quota`; 261 by the wave-1
count): no Vietnamese, no South African, no prose class, no transcription,
no document-identity answers, and strata are by country, language and
classification rather than statement shape, so the prose stratum that yields
most of M2's statements (pending set ZAF 49, SEN 28, VNM 25, IDN 13) is
absent or under 30 and reads 'uninformative'. (d) Nothing says whether a run
may start when a stratum is uninformative, or which mapping its items use;
X-01 applied the strata and the rates, not the set's derivation, the match
rule or the start condition.

**Proposed fix.** Extraction §6.3: derive a person-versus-assisted flag for
legacy lines from the minting decision record; state the match rule (same
snapshot and page, same classification, and the reference line's numerals,
dates and named party contained in the proposal's quote after whitespace
normalisation), or re-anchor the paraphrase reference lines before the
tuning/held-out split; add statement shape (table row, record page, prose
span, transcription) as a stratum. State the uninformative-stratum rule as a
declared method parameter with this default: the run proceeds; the stratum's
items use the pooled mapping of their language or the global mapping; every
item of that stratum goes to the arbiter regardless of agreement; items
carry `calibration: pooled` and are served among the least certain; the run
report and the release's calibration record name the stratum as uncalibrated
and list strata by size. Apply the same rule to transcription and identity
readers. Add a §12 control. Keep operation §5's 'no run before calibration'
as 'before the calibration record exists', not 'before every stratum is
informative'.

**Author question.** The set of hand-made answers covers neither Vietnamese
nor South African prose nor transcription, and no human reads any more, so
those strata stay uninformative to 2030 unless answers are made. Options:
(a) accept the fallback above (uncalibrated strata run with every item
arbitrated, named as such in every release); (b) one labelling sitting
before the first unattended run, blind to any machine reading, of at least
30 held-out items each for Vietnamese prose and South African prose in the
target shape (perhaps two to three hours), then (a) for the rest; (c) block
M2 until every stratum of the pending set reaches 30. Recommended: (a) now,
with (b) offered as the one sitting that would make the M2 calibration
record say something about the documents M2 reads; (c) is not recommended,
since it re-creates the attention bottleneck the autonomy rule removed.

**Outcome.** default accepted by the author 2026-09-30; applied in "docs(jetp): apply the author's defaults for the last five decisions and the licence": options (a) and (d), extraction 6.3 (strata by language
and statement shape; the fallback for an uncalibrated stratum).

### W2-05 (major, M2)

*Lenses:* within-file, implementation. *Files:* jetp-fusion.md §3 (Reading and verification, Threshold per result); jetp-extraction.md §6.3, §14; jetp-operation.md §1, §5

**Finding.** The versioned rule that 'turns the readings into one judgement'
is named but stated nowhere: (a) how a raw self-score becomes a likelihood
term (extraction §6.3 says only 'mapped to the likelihood terms from those
scores'); (b) how the five confidence levels are assigned to an item (two
readers agree, arbiter overrules one reader, arbiter alone, pooled
calibration); (c) whether the arbiter emits a self-score. Fusion §3's
escalation trigger ('below the match threshold') and combining rule ('at or
above the threshold') also depend on the match threshold, which the same
section declares per result at compute time, possibly two of them, so the
judgement-time trigger has no defined value; extraction solved this with a
named 'extraction acceptance level' (§14). Every M2 item must end with all
three values and every page is sorted by them, so two builders would ship
two incompatible rules under one method name.

**Proposed fix.** State the default rule once in extraction §6.3 and have
fusion §3 and operation §1/§5 cite it: (a) raw self-scores map to a term by
monotone thresholds fitted on the tuning part and reported on the held-out
part; (b) a short table assigns confidence from reader/arbiter agreement and
calibration status; (c) the arbiter emits a self-score mapped the same way.
In fusion §3 name an 'escalation level' declared per judgement method
version (default likely), used for the arbiter trigger and the agree-but-
wrong rate, and reserve 'match threshold' for results. Leave the numeric
thresholds to the method version and the reading configuration (W2-36).

**Outcome.** applied in (B) "the reading protocol stated once, in extraction
6.3": extraction 6.3 states the judgement rule once (monotone mapping of raw
self-scores fitted on the tuning part, confidence from agreement, the
arbiter's self-score mapped the same way); fusion 3, operation 5 and Q5 cite
it and their restatements are cut. Rejected in part: a new "escalation
level"; the existing acceptance level (extraction 14) now names the bar for
extraction and matching alike, and "match threshold" stays with results.

### W2-06 (major, M2)

*Lenses:* data-held, implementation. *Files:* jetp-extraction.md §6.3 (Two readers, Agreement), §12, §15; jetp-ledger-storage.md §1 (locator uniqueness check)

**Finding.** Readers agree 'when both propose it with the same derived
locator, classification and verbatim fields', and 'the two readings are
aligned on their derived locators'. Two LLMs quoting one assertion rarely
quote byte-identical spans, and a prose locator is the anchors of the quote,
so 'same derived locator' is exact anchor equality: nearly every prose item
splits into two single-reader proposals, each sent to the hosted arbiter
with its pages (the one paid step of M2), and each admissible at its own
locator since the (sha256, locator) uniqueness check does not see overlap;
the spike saw 'missed' items duplicating kept rows. No normalisation is
stated for the verbatim fields either, so a one-character difference in an
amount escalates. The equality rule fixes both the arbiter load (the M2
hosted budget) and the code the builder writes first, and duplicates at
overlapping anchors inflate every count downstream.

**Proposed fix.** In extraction §6.3 define alignment: proposals are the
same item when their derived spans overlap on the same page or cell and
their classifications match; they agree when their verbatim fields are equal
after whitespace and Unicode normalisation, the admitted quote being the
shorter span; a span-only difference is agreement, a field difference goes
to the arbiter. Refuse admission of a prose line overlapping an admitted
line unless the assertion index differs. Add a §12 red test with two quotes
of one sentence and a §15 row.

**Outcome.** applied in (B) "the reading protocol stated once, in extraction
6.3": alignment by overlapping spans and matching classification, agreement
on fields after whitespace and Unicode normalisation, the shorter span
admitted; the admission step refuses overlapping prose anchors unless the
assertion index differs; a section 12 control. No new section 15 row (the
section 12 control is the test).

### W2-07 (major, M2)

*Lenses:* implementation, dead-angles. *Files:* jetp-operation.md §5 (Selection and calibration before installation, One model per GPU); jetp-extraction.md §6.3 (Replacement readers), §14; runbook (Qwen example)

**Finding.** The calibration record is measured on OpenRouter's served
instance (full precision, the provider's sampling and template) and then
applied to a quantised llama.cpp instance sized to a 16 GB and a 12 GB card
with the thinking flag off, served by another stack; the runbook's Qwen
example already shows the local template changes behaviour. Extraction §6.3
makes 'any change of reader' a new method version scored again, yet nothing
re-scores the installed artifact, and 'the same model through OpenRouter' is
listed as the same method. Every likelihood the local readers emit at M2
would carry a mapping measured on something else, and a switch to the hosted
variant mid-campaign would change the method silently.

**Proposed fix.** Operation §5: the OpenRouter score is a selection score.
The installed artifact (exact weights, quantisation, context, sampling,
template and serving software named in the method version) is calibrated on
the held-out part before its first unattended run, and that record is the
method version's calibration. A change of quantisation, stack or routing
(local to hosted) is a new method version; the OpenRouter fallback reader is
a distinct method version. Cite from extraction §6.3 and §14.

**Outcome.** applied in (B) "the reading protocol stated once, in extraction
6.3": the OpenRouter selection and calibration stand (author decision); a
reader is its weights, quantisation, context, sampling, template and serving
software, so the installed pair is scored again on the held-out part before
its first unattended run and that score is the calibration it runs under; a
switch between local and hosted is a new method version.

### W2-08 (major, M2)

*Lenses:* dead-angles. *Files:* jetp-extraction.md §1, §6.3 (Calibration), §12; jetp-results.md §4 (validation report); jetp-requirements.md DA3

**Finding.** Recall of extraction is measured nowhere. W1-04 (e) had an
author-read sample of in-scope passages for recall and W1-50 noted that an
item both LLMs skip is never listed; the autonomy decision dropped the
sample and nothing replaced it, so the calibration record reports precision
only. Yet the held-out set allows a recall figure (reference lines neither
reader proposed). 'Complete within a declared extraction scope' and DA3's
coverage cannot be shown: a document where both readers skip a third of the
items ends 'accounted for' with a clean report.

**Proposed fix.** Add recall per stratum (by at least one reader, and by the
agreed pair) to the calibration record of extraction §6.3 and to the release
validation report of results §4, with its Wilson interval. Do not add a
floor that blocks runs; report it and serve it with the calibration record.
Record in the wave-1 ledger that W1-04 (e) and W1-50 were dropped without
replacement and are replaced here.

**Outcome.** applied in (B) "the reading protocol stated once, in extraction
6.3": recall (held-out items no reader proposed) joins the calibration
record, which the release's validation reports already carry; no floor.
Wave-1 ledger W1-04 and W1-50 annotated.

### W2-09 (major, M2)

*Lenses:* within-file, cross-file, data-held, implementation, dead-angles. *Files:* jetp-extraction.md §6.4 (Transcription), §13 item 3; jetp-operation.md §5 (Where each reader runs, Selection and calibration), §7.2; jetp-ledger-storage.md §1 (locator syntax), §5; jetp-requirements.md C3, DA2, DA5, OBS-1

**Finding.** W1-16's decision (transcribe Decision 458 at M2 without an
author sitting) was applied as a sentence and the machinery it needs is
absent. Operation §5 selects and installs one text model per GPU, scored on
text reference answers, and its 'Where each reader runs' table lists only
reader, second reader and arbiter: nothing says whether the two 'vision-
capable readers from different model families' are those models, hosted
models under `hosted_reading`, or a third pair, so C3's test ('each reading
method names where it runs') fails for transcription and the selection run
may install a pair that cannot transcribe at all. No hand-transcribed
reference answers exist, so the calibration rule of §6.3 and §12 cannot be
met for them. The locator 'page and region' has no syntax in storage §1's
locator rule, so the validator cannot check it. The only current Vietnamese
plan is thus read by readers the operation document does not place, budget
or calibrate, under the specification's own prohibition.

**Proposed fix.** Add a transcription row to operation §5's table and a
budget line in §7.2: two vision-capable readers of different families,
hosted through OpenRouter under the per-document budget unless the document
is `local_only` (Decision 458 is public), selected by the planted-item
control on a rendered page, the recogniser named in the run; extraction §6.4
cites that row. State that transcription is uncalibrated (no reference
answers) and falls under the uninformative-stratum rule of W2-04: every item
to the arbiter, flagged in the run report and the release. Define the page-
and-region locator syntax in storage §1 (page index plus a region rectangle
in page-normalised coordinates, or the OCR layer's line anchors).

**Author question.** The autonomy decision made local readers the default
and the hosted model the arbiter only; transcription of the one held scan
needs a vision-capable pair that the two installed text models are unlikely
to be. Options: (a) a hosted vision pair through OpenRouter for this one
public document, uncalibrated and arbitrated item by item, under the per-
document cap (a few dollars); (b) make vision capability a criterion of the
M2 model selection so the installed local pair transcribes, at the cost of
constraining the text selection and the calibration; (c) defer transcription
to M3a, reversing W1-16, with the M2 acceptance naming Decision 458 and the
reason. Recommended: (a); the scope is one document, the cost is bounded,
and it leaves the local selection untouched.

**Outcome.** applied, by the recommended default (a), which routes nothing
to the author: a hosted vision pair through OpenRouter for the one public
scan, uncalibrated, every item to the arbiter, named uncalibrated in the run
report and the release, within the per-document budget ((B) "the reading
protocol stated once, in extraction 6.3": extraction 6.4 and the operation 5
table; (A) "dispositions and restatements journals, line status, journal
corrections": the page-and-region locator syntax; (C) "autonomy residue,
cost bases after local readers, Zotero at M2": the legal note names the
pair). No separate budget line: the per-document cap covers it.

### W2-10 (major, M2)

*Lenses:* cross-file, implementation. *Files:* jetp-requirements.md F27, §2.2; jetp-ledger-storage.md §1 (target rows `documents.access_route_kind`, `registration`)

**Finding.** F27 binds at M2 for the documents held with a validator-style
test ('the check runs over the whole register and reports zero documents
without a public access route'), but the storage target that realises it
says 'the validator requires a route kind on every document from M3a | M2
for the columns; M3a for the check'. Under §2.2 (a requirement is not met
while a column its rules need is a target, X-27) F27's M2 part is either
unmet at M2 or the storage milestone is wrong; the builder does not know
whether to write the check now, and the 392 rows may stay empty until M3a.
Two documents today have no `url` (both `local-record`).

**Proposed fix.** Retag the check M2 in the two storage target rows: route
kind non-empty on every held document at M2, the two local-record documents
given `archive record` or `address` routes (one column fill over 392 rows);
M3a covers documents admitted by discovery. Write the same milestone in F27.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections": the route-kind check is M2 for the documents
held, M3a for documents admitted by discovery; F27 already read so.

### W2-11 (major, M2)

*Lenses:* within-file, implementation, dead-angles. *Files:* jetp-ledger-storage.md §1 (Readings and runs, `runs`; validator rules); jetp-operation.md §10 (Run states), §14

**Finding.** `runs` is 'one row per run, written when the run ends', but
operation §10 constructs a run killed by a power cut that has no final
state, is treated as failed, and whose completed documents 'may be admitted
through its pull request, each whole'. A killed process writes no row, yet
'every `run_id` of another table names a row here' and rejected or
undetermined readings 'keep their row', so the readings and lines of the
interrupted run either orphan their run_id or must be discarded, which Q4
discourages; the validator is the run-output gate, so the resumption path of
§10 and §14 silently loses completed work or the builder relaxes the
validator. The `runs` row also holds 'spend per vendor' as a list in one
column, against the contract's own no-list rule, and a list of raw-response
paths the hashes in `readings` already name.

**Proposed fix.** The launcher writes the `runs` row at start with state
`running`; the run supersedes it at the end (append-only); a `running` row
whose tmux session is gone, or past its budget, is closed as `failed` by the
rerun or the next launcher. Move spend per vendor to a `run-spend` relation
table (run_id, vendor, llm_id, tokens_in, tokens_out, usd, gpu_seconds).
Drop the raw-response path list. Align operation §10.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections" and (C) "autonomy residue, cost bases after
local readers, Zotero at M2": the `runs` row is written at the start as
`running` and superseded at the end; a `running` row whose session is gone
is closed as failed. Rejected in part: a `run-spend` table. Cut instead:
spend per vendor and the raw-response paths leave `runs`; spend and GPU time
are the sums of the readings (W2-23).

### W2-12 (major, M2)

*Lenses:* implementation. *Files:* jetp-ledger-storage.md §1 (file ceiling and shards, `readings`); .githooks/pre-commit (512 000-byte ceiling)

**Finding.** The shard rule reads the year of `recorded_at` and the row's
own `country` column, but `readings` has no country column and a rejected or
undetermined proposal cites no line, so the rule cannot apply to it. At
7,000 to 12,000 proposals per M2 pass, each with a quoted basis and fields,
`readings.csv` exceeds the pre-commit file ceiling within the first run and
the first run-output pull request cannot be committed.

**Proposed fix.** State beside the `line-fields` shard rule that `readings`
is sharded by run (`readings.d/<run_id>.csv`, `-02` shards when a run
exceeds the ceiling, joined in run order), and what the country of a reading
is when needed (the run's declared document). `runs`, `run-spend` and
`dispositions` stay single files until they near the ceiling.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections": `readings` is sharded by run.

### W2-13 (major, M2)

*Lenses:* data-held. *Files:* jetp-extraction.md §2 (pending list), §4 (record page), §6, §6.1, §6.3; jetp-requirements.md F5

**Finding.** Two holdings need two methods on one snapshot and the text
gives no route. The 13 MOIT newsletter issues are a repeated format
(masthead, headlines) around prose: §6.1 gives a repeated format a parser
and §6.3 applies 'where no series justifies a parser', so a prose series
falls between them (the spike's parser read only the masthead). A record
page (27 project pages) is 'one item statement for its subject; its labelled
fields are its verbatim fields under the printed labels, and its description
follows the rule for prose', which is a template parser plus the panel. Once
the first method writes a statement the snapshot leaves the pending list,
'the input of every run', so the second method never fires, and §6.1's 'no
partial set of statements is admitted from a failed extraction' does not say
whether it binds the other method's part.

**Proposed fix.** State in §6 that one method version may combine a parser
for the frame and the panel for declared prose parts, each part under its
own method and version on the line. Make pending per (snapshot, declared
scope part), or keep the snapshot pending until every declared scope part
has statements or a disposition; say that a failed part refuses only that
part's statements. Add a §12 control on one newsletter issue.

**Outcome.** applied in (B) "the reading protocol stated once, in extraction
6.3", in a smaller form: one method version may combine a parser for the
frame with assisted reading of declared prose parts, each statement naming
its part's method, and a snapshot's statements are admitted together or not
at all. Rejected in part: pending per scope part (whole-snapshot admission
makes it unnecessary) and the newsletter control.

### W2-14 (major, M2)

*Lenses:* data-held. *Files:* jetp-extraction.md §6.2 (Count control), §12; jetp-ledger-storage.md §1 (locator syntax); jetp-requirements.md Q1, DA2

**Finding.** The ingestion count control 'compares, for each snapshot, the
number of records it read with the number the service or the file states'
and fails 'when they differ', but most held bulk snapshots state no count:
the 81 CRS extracts and 6 World Bank exports are `local-record` CSV files,
the two JSON files and the two JavaScript bundles are literals. The control
can then neither pass nor fail and Q1's test ('each snapshot's record count
equal to the count it states') is undecidable for them; a JS-literal record
also has no publisher record identifier for the locator rule. The M2 replay
of the 10,452 comparator lines (W1-15's decision) hinges on this control,
and the route of the two 5-million-character JS bundles is decided by it.

**Proposed fix.** In §6.2 say what the declared count is when the source
states none: the count recorded in the run manifest when the file was first
read, declared by the person who recorded the file, and a later change
fails. Define the locator for a record with no publisher identifier (file,
ordinal within the file, and the hash of the record's canonical
serialisation). Add the case to §12.

**Outcome.** applied in (B) "the reading protocol stated once, in extraction
6.3" (where the source states no count, the count recorded when the snapshot
was first read) and (A) "dispositions and restatements journals, line
status, journal corrections" (locator for a record without a publisher
identifier).

### W2-15 (major, M3a)

*Lenses:* data-to-come. *Files:* jetp-collection.md §2, §9 (Candidate triage); jetp-fusion.md §3 (proposers 1, 2, 4); jetp-ledger-storage.md §1 (target `candidates`, `retrievals`); jetp-language.md D1; jetp-requirements.md F7, F27, C6

**Finding.** Triage needs bytes before admission and the schema forbids it.
§9 has the two readers 'receive a candidate's text', the arbiter judges 'the
candidate's text', the `duplicate` outcome is judged 'as in fusion section
3' whose proposers compare bytes and normalised text, and proposer 4 reads
'both first pages'. But a candidate 'is not in the register' (F7's test), a
retrieval is 'one attempt to fetch one document' keyed on document_id, and
the target `candidates` table holds only a pointer, the round and the
document it became. A fetch made to triage a candidate has no retrieval row,
breaking 'every attempt is recorded', C6's per-fetch terms position and
F27's route; every M3a discovery round fetches candidates to judge them.

**Proposed fix.** Let `retrievals` carry a nullable `candidate_id` beside
`document_id` (the smaller change; the alternative is registering every
candidate as a document with no accepted admit row). State that the bytes of
a rejected candidate stay under their hash, cited and never extracted.
Reword F7's test to 'absent from the admitted documents' and adjust language
D1 and the Times-per-table row to match.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections" (nullable `retrievals.candidate_id`, a rejected
candidate's bytes kept under their hash, never extracted) and (D)
"collection rules for M2 scans, admission, captures and blind lists" (F7's
test reads "absent from the admitted documents"). The language D1 and times-
row edits were not needed: a retrieval enters the state by `retrieved_at`
either way.

### W2-16 (major, M3b)

*Lenses:* within-file, cross-file. *Files:* jetp-ledger-storage.md §4 (Scope of the first implementation, matching records); jetp-fusion.md §3; jetp-requirements.md F19

**Finding.** The paragraph that says what the first matching implementation
builds predates the autonomy decision: 'tier 2 as a candidate generator
reviewed by hand; tiers 3 to 5 as method names reserved in the vocabulary'.
This contradicts 'no machine judgement is routed to the author' and fusion
§3, where proposers 4 and 5 run on the two local readers at M3b and are the
machinery that matches lines to CRS and IATI (F19). As written it builds a
hand-review queue and no LLM matching.

**Proposed fix.** Rewrite the lines part of storage §4: tier 1 by adopted
rule; tiers 2 and 3 as deterministic proposers; tiers 4 and 5 as the panel
on the local readers with the hosted arbiter; tier-2 candidates judged under
the panel protocol of fusion §3. The 257 register rows and 67 plan lines
matched by hand are reference answers, not a review scope.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections": tiers 2 and 3 deterministic proposers, tiers 4
and 5 the panel on local readers with the hosted arbiter; the 257 register
rows and 67 plan lines are reference answers, not a review scope.

### W2-17 (major, M3b)

*Lenses:* within-file, cross-file. *Files:* jetp-results.md §5 (Validation before publication), §9; jetp-requirements.md C1 (test), Q5; jetp-extraction.md §4

**Finding.** The personal-data screen 'lists every hit for the author, who
removes a natural person's contact details, or a name recorded where the
office should be, before acceptance'. That is a design rule requiring the
author to review every item of a class, which C1's test forbids ('no design
rule requires the author to review, audit or sample any item of a class');
X-09 added it after the autonomy decision without reconciling the two, and
the same section assigns acceptance to 'a named reviewer', a role the
sentence bypasses. The release validator would emit a queue for the author,
the one thing the settled rule excludes, or the hits go unhandled.

**Proposed fix.** Route the screen's hits as panel readings: an accepted
stance supersedes the offending line (office for name, field blanked for
contact details), the build report lists the hits sorted by confidence, and
the named reviewer receives the count and the residue below the acceptance
level, not every item. Alternatively write the personal-data screen as an
explicit, bounded exception in C1's test.

**Author question.** Personal data in a published release is a legal
responsibility, not only a machine judgement. Options: (a) the panel judges
every hit and the named reviewer sees the count and the unresolved residue
only (consistent with C1 as written); (b) an explicit C1 exception: the
personal-data screen is the one per-item author review, bounded by the
number of hits, which the build report states; (c) the release is blocked
while any hit is unresolved by the panel, no author view. Recommended: (a),
with the residue served on the pending-judgements page so the author can
look when he chooses; (b) if the legal review before go-live asks for a
named person to have seen each hit.

**Outcome.** applied in (C) "autonomy residue, cost bases after local
readers, Zotero at M2", by the rule the author set (automated removal, never
a queue): each hit of the personal-data screen is judged under the protocol
of extraction 6.3, a natural person's contact details or a name recorded
where the office should be removed by supersession and recorded as readings,
the build report counting the hits.

### W2-18 (major, M3b)

*Lenses:* cross-file. *Files:* jetp-requirements.md F18, SP-1, §9 table and reverse map; jetp-ontology.md §2 to §4; jetp-extraction.md §11; jetp-fusion.md §7

**Finding.** No document meets F18: 'transition function' appears only in
requirements (five occurrences) and nowhere else in the specification.
Ontology §2 to §4 define no such classification, term or relation;
extraction §11 never reads it; fusion §7 has no once-only counting rule
across functions; the reverse map lists F18 under no section. By §2.4 a
requirement no document meets is a gap; SP-1 and F18's M3b test ('an
operation tagged with two functions contributes its amount once') cannot be
built or checked, and the M3b DDL will lack the value list.

**Proposed fix.** Add `transition_function` as a closed list (energy
infrastructure, fossil exit, social support) in ontology §4, assigned like
`sector` by a reading rule in extraction §11 and a judgement at M3b; add a
fusion §7 counting rule for totals across functions (an operation counted
once); add F18 to the reverse-map rows of those sections.

**Outcome.** applied in (E) "M3b gaps: transition functions, pledge, deposit
status, word list": transition function is a classification of an agreement
or project assigned like sector (ontology 4), counted once across functions
(fusion 7), F18 in the reverse map. Its three values become `terms` rows
with the other M3b axes, not now.

### W2-19 (minor, M2)

*Lenses:* within-file, cross-file, state-of-the-art, data-held. *Files:* jetp-fusion.md §3 (Judgement by adopted rule; Who decides what, rows 1 and 2; Documents tag line); jetp-extraction.md §5, §7, §8 (Pairing across snapshots), §13 item 1; jetp-operation.md §4, §5; jetp-ledger-storage.md §4; jetp-requirements.md N4

**Finding.** The table that claims to be 'the one statement of decision
authority' (N4 cites it) leaves out or misroutes four M2 decision classes.
(1) Statements admitted by a parser or an ingestion run (about 80 % of M2
lines) fall under no row. (2) Key-based pairing across snapshots of one
document, which extraction §8 [M2] calls 'virtually certain' and the basis
of restatement, is not among the three adopted rules (identical bytes,
declared-scheme identifier, case or diacritic variant), so it is either an
unlisted rule or a candidate two LLM readers must judge thousands of times a
year. (3) Row 2 routes every disposition to the panel, while `no_snapshot`,
`unreadable`, `wrong_content`, `duplicate`, `translation_not_canonical` and
`deferred` are made by the register, the adapter, an earlier judgement or a
budget; only `out_of_scope` and `no_extractable_content` need a reading, and
the readings validator would fail on rule-made dispositions. (4) The
Documents tag line says proposer 3's bounded list is 'judged under the
protocol of extraction §6.3' at M2, which is exactly proposers 4 and 5,
while the next clause has them 'start at M3a' (introduced by W1-10's fix);
and identical normalised text is a rule in extraction §8 but a panel
candidate in storage §4.

**Proposed fix.** Add a row: program output under a method version, merged
through the code gate of operation §4 (parsers, ingestion, rule-made
dispositions). Add to row 1: a publisher's unique key repeated across
snapshots of one document under one declared field list, accepted under the
parser's method version with W1-31's tier-1 corroboration condition; keys
across documents or editions stay candidates. Split row 2 so that only
`out_of_scope` and `no_extractable_content` are panel dispositions. Reword
the Documents tag line: the panel protocol runs at M2 on proposer 3's
bounded list; proposers 4 and 5 as generators start at M3a. Align storage §4
with extraction §8 on identical normalised text (a rule).

**Outcome.** applied in (B) "the reading protocol stated once, in extraction
6.3": a decision-authority row for program output under a method version
merged through the code gate (parsers, ingestion runs, key-based pairing
across snapshots, rule-made dispositions); only `out_of_scope` and
`no_extractable_content` are panel dispositions; the Documents tag line
reworded. Rejected in part: "align storage 4 with extraction 8 on identical
normalised text"; the two cover different cases (two documents, a fusion
proposer; two snapshots of one document, an extraction rule), so there is no
contradiction to remove.

### W2-20 (minor, M2)

*Lenses:* cross-file, state-of-the-art. *Files:* jetp-ledger-storage.md §1 (target rows `retrievals.terms_position`, `documents.hosted_reading`); jetp-extraction.md §6.3 (Local reading only); jetp-operation.md §5 (What reaches a hosted model); jetp-legal-note.md §1, §4; jetp-requirements.md C6

**Finding.** The X-07 rule is vacuous for the whole M2 pass.
`hosted_reading` is `local_only` 'when the recorded terms forbid third-party
processing by an explicit reservation', but its input,
`retrievals.terms_position`, is recorded only from M3a (C6) and its
validator check is M3a; at M2 no held document has a recorded position, so
all 115 pending documents default to `allowed` and go to the hosted arbiter.
And no value of `terms_position` (open licence, public-sector reuse, rights
reserved, unknown) captures a TDM or third-party-processing reservation
(robots agent rules, tdmrep, ai.txt, terms wording), which the legal note §1
treats as evidence to record; who sets `local_only`, by which rule, is
undefined, so a hand-set flag is an unrecorded judgement (N4, Q21) and a
code-set one has no input.

**Proposed fix.** Add a `processing_reservation` column on `retrievals`
(none, machine_readable, terms, unknown) with the quoted signal in notes,
set `hosted_reading` from it by a named rule or a recorded author decision,
and have the validator check the two agree. Add a one-time bounded terms
pass over the sites of the held documents to the M2 slice (agent work,
recorded as retrievals rows), so the routing of document text to OpenRouter
is traceable before the first hosted call; the full C6 pass stays M3a.

**Outcome.** applied in part in (A) "dispositions and restatements journals,
line status, journal corrections" and (B) "the reading protocol stated once,
in extraction 6.3": `hosted_reading` is set by rule from the latest
retrieval's `terms_position`, which gains the value processing reserved
(instead of a new `processing_reservation` column); the rule reads terms
positions from M3a, when C6 records them. Rejected in part: the bounded M2
terms pass. M2 outputs are unpublished, every hosted call already requests
no collection and no retention, and the legal position on hosted calls is
settled at the legal review before go-live (author decision); no M2 result
needs the pass.

### W2-21 (minor, M2)

*Lenses:* data-held, implementation. *Files:* jetp-ledger-storage.md §1 (Readings and runs, validator rule on `reader` and `second_reader`); jetp-extraction.md §6.3 (escalation), §15

**Finding.** A `readings` row is 'one row per proposal of a reader', and the
validator requires 'a `reader` and a `second_reader` row' for every line of
an assisted reading. An item proposed by one reader only and admitted by the
arbiter (extraction §6.3's first escalation case) has no `second_reader`
row, so the validator, which is the run-output gate, rejects a line the
method admits, on every run.

**Proposed fix.** Have the alignment step write a `not_proposed` row for the
reader that did not propose (added to the outcome list), which also records
that the second reader saw the passage, as AED-2's step tally needs; keep
the arbiter-row requirement. Add the single-reader admission case to
extraction §15.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections" by rewording the validator (a row from each
reader that proposed the item, an arbiter row unless the readers agreed).
Rejected in part: a `not_proposed` outcome; the reworded rule admits the
single-reader case without a new value.

### W2-22 (minor, M2)

*Lenses:* within-file, cross-file, implementation. *Files:* jetp-ledger-storage.md §1 (Readings and runs; Rules that the validator enforces); jetp-extraction.md §1, §6, §10; jetp-ontology.md §4; jetp-requirements.md Q17 (test)

**Finding.** The closed lists of the M2 journals are stated inconsistently
and none is a `terms` list, although the validator accepts a value only when
it is a term in force and the ontology's alignment test fails on a value
that is not one. `lines.method` is listed three ways (four methods in §1
without ingestion; 'Four methods' in §6 listing ingestion with the person's
reading outside; §10 binds replay to 'the parsers, the ingestion runs'). The
rejected step is 'retrieval, extraction, reading, matching' in Q17 and
'locator check, agreement, arbitration' in `readings`. A reading carries a
`stance` with no closed list for an extraction proposal (fusion §3 defines
stances for matches only) and an `outcome` that may only repeat it; reading
role, run state, `hosted_reading` and the disposition kinds are likewise
unnamed as terms.

**Proposed fix.** In storage §1 state each list once as `terms` rows: method
(parser, ingestion, assisted reading, transcription, person; fix 'Four' in
extraction §6 and the §1 list), reading role, stance for an extraction
proposal (right, wrong, undetermined), outcome as the item's terminal state
(or drop it), rejected_step covering both grains (pipeline step and protocol
step, or two columns), run state, `hosted_reading`, disposition kind. Cite
the rejected_step list from Q17's test.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections" and (B) "the reading protocol stated once, in
extraction 6.3": extraction 1 lists ingestion among the methods; the stance
of an extraction proposal is right, wrong or undetermined; outcome is the
item's terminal state; the step at fault reads Q17's steps or the protocol
step. The lists become `terms` rows with the DDL (ticket 1702 exit
criterion). "Four methods" in extraction 6 stays: four subsections, the
person's reading sitting in 6.4.

### W2-23 (minor, M2)

*Lenses:* data-held. *Files:* jetp-ledger-storage.md §1 (`readings`, `runs`); jetp-operation.md §5, §8; jetp-requirements.md Q17, AED-3

**Finding.** Q17 [M2] and AED-3 require a cost per reading and per method,
and operation §5 says every call records tokens and cost, but `readings` has
no token or cost column and `runs` holds spend per vendor only; no table is
named for the call log, so Q17's M2 test ('every machine reading and the
decision are retrievable with method, version and cost') cannot pass from
the ledger.

**Proposed fix.** Add tokens_in, tokens_out, cost_usd and, where it applies,
gpu_seconds to `readings`; the `run-spend` table of W2-11 aggregates them.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections": tokens, cost and GPU seconds on each reading.

### W2-24 (minor, M2)

*Lenses:* within-file, state-of-the-art, data-to-come. *Files:* jetp-requirements.md Q5 (test), Q20; jetp-operation.md §1, §5, §14; jetp-fusion.md §3; jetp-extraction.md §6.3; jetp-collection.md §9; jetp-ledger-storage.md §4; jetp-observatory-presentation.md (Pending judgements)

**Finding.** Three statements about undetermined outcomes disagree. Q5, its
test ('every LLM judgement in a release carries ... a stance and a
calibrated likelihood and confidence') and operation §1/§5 give every item a
likelihood, while fusion §3, extraction §6.3 and storage §4 define
`undetermined` as an abstention that carries none, so the Q5 test fails on
the first undetermined item. The sort key of the served pages is 'by
confidence' in storage §4 and operation §14 but 'by likelihood and
confidence' in fusion §3, extraction §6.3, collection §9, Q5, Q20 and the
presentation, with no declared total order over two ordinal scales and no
place for items without a likelihood. And the pending-judgements page reads
'decision rows with a candidate status', while an undetermined extraction
proposal lives in `readings` with no line, so the page omits the bulk of
what the readers left open, which Q20's test and OP-1 require it to show.

**Proposed fix.** Reword Q5, its test and operation §1/§5: 'a stance, and a
calibrated likelihood and confidence unless the stance is undetermined'.
Declare the sort key once in fusion §3 (undetermined first, then ascending
likelihood, then ascending confidence) and cite it from storage §4,
operation §14 and the presentation. Have the pending-judgements page also
read `readings` rows with outcome undetermined, grouped by item; raw
responses stay unserved.

**Outcome.** applied in (B) "the reading protocol stated once, in extraction
6.3": Q5 and its test say "unless undetermined"; the served order is
declared once in fusion 3 (undetermined first, then ascending confidence, as
the author asked, then likelihood) and cited from extraction 6.3, collection
9, storage 4, Q20 and the presentation; the pending-judgements page also
reads the undetermined readings.

### W2-25 (minor, M2)

*Lenses:* cross-file, implementation, dead-angles. *Files:* jetp-operation.md §6 (Providers in use), §9 (The off-site copy: Zotero; Test of recovery), §11; jetp-legal-note.md §1

**Finding.** W1-22's decision made Zotero the M2 off-site copy ('each
snapshot is uploaded, one way, to the project's Zotero group, with its
SHA-256 ... when it is pushed to DVC', and the M2 recovery test restores one
snapshot from it), but §6 tags the `zotero` credential M4, so under §6's own
reading rule the M2 upload cannot authenticate. Three further gaps: the
group's visibility is unstated, although it holds bytes whose terms forbid
or leave unknown redistribution (a visible group would be a redistribution
before any legal review); the rule fires 'when pushed to DVC' and the 278
objects already pushed have no backfill; and the recovery test restores one
snapshot while nothing checks that every `snapshots` row has an item, so the
completeness of the only copy off padme's disk is never known.

**Proposed fix.** §6: tag `zotero` [M2] for the upload of snapshot bytes,
[M4] for its use as the document store. §9: the group is private with
attachments visible to members only; a one-time M2 backfill of the objects
already pushed; a completeness check (every sha256 in `snapshots` has an
item carrying that hash) reported at each milestone acceptance. Group
identifier and item shape stay in the runbook.

**Outcome.** applied in part in (C) "autonomy residue, cost bases after
local readers, Zotero at M2": `zotero` is an M2 provider; the group is
private, attachments visible to members only; a one-time upload of the
objects already pushed. Rejected in part: the completeness check at each
milestone; the per-push upload, the backfill and the machine backup already
cover the copy, and the recovery test restores from it.

### W2-26 (minor, M2)

*Lenses:* cross-file, implementation. *Files:* jetp-operation.md §5, §6 (Providers in use), §7.1 (measurements), §7.2 (Proposed amounts), §14; jetp-requirements.md C4

**Finding.** The cost bases and the provider list predate the autonomy
decision. §5 makes both readers local at cost zero and the hosted model the
arbiter only, yet §7.1 derives the M2 pass from 'USD 0.03 to 0.08 per
document with hosted readers', the per-document cap from 'the largest held
PDF read once by a frontier pair', and §7.2 the per-vendor budget from
'keeps the second vendor funded' when one hosted vendor is paid; §6 lists
five direct provider keys at M2 although every hosted call goes through
OpenRouter; the §14 row tests 'the Anthropic key is missing on padme', a key
no M2 run uses. The budgets are enforced by code (C4), the GPU-time budget
is now the binding one and has no measurement behind it, and the arbiter-
only cost is unmeasured.

**Proposed fix.** §6: `openrouter` [M2]; direct provider keys [M4 or when a
role uses one]. §7.1: restate the bases for local readers plus a hosted
arbiter (arbiter calls plus one selection run), paid spend measured on the
first calibration run and GPU time on the first installed-reader run; keep
the amounts as defaults. §7.2: reword the per-vendor basis as a cap on the
arbiter's maker. §14: 'the OpenRouter key is missing'.

**Outcome.** applied in (C) "autonomy residue, cost bases after local
readers, Zotero at M2": `openrouter` is the M2 provider, direct keys only
when a role uses one; the prototype's hosted-reader bases and the price
table are cut; paid spend is the arbiter, the hosted transcription and
selection runs, measured on the first calibration run; the per-vendor budget
caps the arbiter's maker; the section 14 check names the OpenRouter key.

### W2-27 (minor, M2)

*Lenses:* within-file. *Files:* jetp-operation.md §4 (Gates; Run outputs have their own gate)

**Finding.** Ten lines apart, §4 says 'a change that writes data, DVC
outputs or deposits also passes the full `make check` on padme before
merging' and 'a run-output pull request carries no code; its gate is lighter
than a code change's'. A run-output pull request writes data, so the two
rules prescribe different gates for the same pull request, which is exactly
what W1-20 asked the author to settle (option (a), one PR per run, lighter
gate).

**Proposed fix.** Reword the first gate to 'a change to code that writes
data, DVC outputs or deposits', and state that a run-output PR runs the
listed checks and the validator, not the full suite.

**Outcome.** applied in (C) "autonomy residue, cost bases after local
readers, Zotero at M2": the full-suite gate is for a change to code that
writes data.

### W2-28 (minor, M2)

*Lenses:* within-file, data-held. *Files:* jetp-collection.md §1, §7, §8 (Scans), §9, §11 (M2 before the campaign); jetp-operation.md §4; jetp-requirements.md F7

**Finding.** §8 requires, before the held scan (Decision 458) is transcribed
at M2, a search for a born-digital copy 'recorded like any recorded search
(section 7)', a copy found being 'registered and extracted instead'. But §11
says 'M2 discovers nothing' and allows only retries on rungs 1 and 2, §7's
recorded search is M3a, admission is a recorded triage judgement tagged M3a,
F7 admits a document only by a recorded decision from M3a, and operation §4
forbids agents to admit a document. The general rule W1-16 added cannot be
executed under the M2 rules, and a Công báo copy found would enter the
register with no admission path.

**Proposed fix.** Add one M2 exception to collection §11 for held scans: a
bounded look-up recorded as a `dry-searches` row; a copy found is registered
by the author as a register change and related to the scan by `edition_of`
or `same_as`. Cite it from §8.

**Outcome.** applied in (D) "collection rules for M2 scans, admission,
captures and blind lists": the one M2 exception, a bounded look-up recorded
as a dry search; a copy found enters by a register change, related to the
scan.

### W2-29 (minor, M2)

*Lenses:* within-file. *Files:* jetp-extraction.md §2 (pending list), §7 (`deferred`); jetp-operation.md §7 (per-document budget), §10; jetp-requirements.md F5

**Finding.** A `deferred` snapshot has a disposition and so leaves the
pending list, yet it is 'not extracted yet' and operation §7 defers at the
per-document budget; nothing says what re-pends it when the budget resets or
the milestone it names arrives, while operation §10 says documents a stopped
run did not reach 'stay pending' with no disposition. Budget-deferred
documents are therefore never revisited by the run that reuses the pending
list (F5).

**Proposed fix.** Reserve `deferred` for 'a format no method reads yet',
naming the milestone; a per-document budget stop leaves the snapshot pending
with the reason in the run report. Align operation §7 and §10. (W2-30 adds a
language reason to `deferred`.)

**Outcome.** applied in (B) "the reading protocol stated once, in extraction
6.3" and (C) "autonomy residue, cost bases after local readers, Zotero at
M2": `deferred` is for a format or language no method reads yet; a budget
stop leaves the snapshot pending with the reason in the run report.

### W2-30 (minor, M2)

*Lenses:* implementation, dead-angles. *Files:* jetp-requirements.md DA5 (test); jetp-extraction.md §2 (Language); jetp-fusion.md §3 (Who decides what); jetp-operation.md §5

**Finding.** DA5's test says '20 of the 115 have none today', but measured
on the ledger 59 of the 392 documents have no language (20 of the 115
pending, 16 of the 254 extracted, the rest among the 23 without snapshot),
and the M2 test binds all 392. Nobody is named to set the language:
extraction §2 says it 'is recorded', the decision-authority table lists
language identification neither as an adopted rule nor as a panel judgement,
and the readers are chosen to 'handle that language', so it must be set
before them. Three held documents are in German, Japanese and Chinese,
outside the four named languages, with no stated route.

**Proposed fix.** Correct the parenthesis to 59 of 392 (20 of the 115
pending). Add language identification to the adopted-rule row of fusion §3:
a versioned library over the text layer, recorded with method and version,
the panel judging only where the rule abstains; cite it from extraction §2.
Add that a held document in a language outside the four is read only if a
reader is calibrated for it, otherwise it receives the disposition
`deferred` naming the language.

**Outcome.** applied in (G) "DA5 counts the documents with no language over
the whole register" (59 of 392, 20 of the 115) and (B) "the reading protocol
stated once, in extraction 6.3" (a versioned language-identification program
sets the language, the panel where it abstains; a language no reader is
calibrated for gives `deferred`, naming it). The program falls under the new
program-output row of fusion 3 rather than the adopted rules, which only the
author adopts.

### W2-31 (minor, M2)

*Lenses:* data-held. *Files:* jetp-extraction.md §4 (Printed totals as controls), §6.1, §6.3 (Parts)

**Finding.** 'Where the document prints how many items a part holds, or a
total the items should sum to, the extraction compares and fails when they
disagree' is an M2 rule, but for assisted reading nothing says who
identifies the printed total and the items it covers (issue 8 prints 557 +
78 + 93 = 728 million; the spike found no step using it), whether 'fails'
refuses the whole document as §6.1 does for a parser or only the part, or
who chooses between 'extracting again' and 'recorded as the publisher's own
inconsistency' now that no item is queued for the author. On a 304-page plan
one mismatched subtotal would either block the whole document or be silently
ignored.

**Proposed fix.** Add a §6.3 step: readers propose a printed total as a
`count` or `envelope` statement with its span; code sums the admitted items
of the part; on mismatch, re-read the part once, then record the mismatch as
a readings outcome and flag the part in the run report. Only a parser
refuses the whole document.

**Outcome.** applied in (B) "the reading protocol stated once, in extraction
6.3": in an assisted reading the printed total is a statement, code sums the
part, one re-read on a mismatch, then the mismatch is recorded as the
publisher's and flagged; only a parser refuses the whole document.

### W2-32 (minor, M2)

*Lenses:* cross-file, implementation. *Files:* jetp-extraction.md §1, §4 (Declared extraction scope), §5 (Retained layers), §6.3 (Parts), §9 (Identifiers and corrections), §12; jetp-ledger-storage.md §1 (target schema)

**Finding.** Three M2 records have no home in the storage contract, and one
M2 computation has no rule. The declared extraction scope and its notes
('the scope stays on record so that a later extraction can extend it'; the
chart gap 'records it in its scope note'), the reviewed old-locator-to-new-
locator mapping of §9 and the old-layer-to-new-layer mapping of §5, and the
part boundaries of §6.3 are held nowhere (`line-field-specs` holds columns
only; a locator is a column append-only rules forbid editing), so a later
extraction cannot read the scope, identifiers cannot be remapped when the
pinned adapter changes (the §12 retained-layer red test presumes the
mapping), and a builder puts the scope in the run report. Who computes the
parts of a one-off document, at what size, is unstated, although twelve
pending documents exceed 100,000 characters, the largest text layer is about
950,000, the two readers have different contexts and alignment needs
identical parts.

**Proposed fix.** Add M2 target tables for extraction scopes (with notes)
and locator mappings under the in-force rule, or state that the run manifest
is their record and is read by later runs; cite the choice from extraction
§4, §5 and §9. State that code computes the part plan per snapshot from the
smaller reader's declared usable context less prompt overhead, cut on page
boundaries (cells for spreadsheets), identical for both readers, recorded on
each reading row as `part_index`; a parser-declared or scope-declared part
overrides it.

**Outcome.** applied in part in (B) "the reading protocol stated once, in
extraction 6.3" and (C) "autonomy residue, cost bases after local readers,
Zotero at M2": the run report is the record of the declared scope, its
notes, the part plan and any reviewed locator or layer mapping, read by
later runs; code computes the part plan, identical for both readers, on page
boundaries within the smaller context. Rejected in part: new scope and
mapping tables, and `part_index` on readings (the locator already places a
reading).

### W2-33 (minor, M2)

*Lenses:* data-held. *Files:* jetp-ledger-storage.md §1 (Rules that the validator enforces, `lines.sha256`); jetp-operation.md §9 (recovery test); jetp-requirements.md DA2

**Finding.** The validator requires that 'a line's `sha256` exists in
`snapshots`, the bytes exist in the store', but DA2 keeps 91 comparator
snapshots 'outside the document store' under the comparator data
directories, and 10,452 M2 lines cite them; 'the store' is not defined to
include those directories, and operation §9 lists 'structured bulk data' in
the DVC cache without naming where. The M2 validator either fails on 80 % of
the lines or passes on an undefined notion of the store, and the recovery
test restores 'the document store' and may leave the comparator bytes out.

**Proposed fix.** Define 'the store' in storage §1 as the document store
plus the comparator data directories, both under DVC and both restored by
the operation §9 test, or move the 91 snapshots into the document store.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections" and (C) "autonomy residue, cost bases after
local readers, Zotero at M2": "the store" is the document store and the
comparator data directories, both restored by the recovery test.

### W2-34 (minor, M2)

*Lenses:* cross-file. *Files:* jetp-ledger-storage.md §1 (milestone tag line after the table), §4 (last bullet); jetp-language.md (step table); jetp-ontology.md §2; jetp-extraction.md §13 item 1

**Finding.** The tag line reads the M2 DDL scope as 'the D1 and D2 tables
and the ontology tables', yet `relations` is a D4 table while storage §4
makes document relations (`same_as`, `edition_of`, `translation_of`)
`relations` rows at M2 and the target table gives `relations` four M2
targets; `parties`/`party-names` hold publishers at M2 and the language step
table lists `parties` under both D1 and D4. A builder following the line
leaves `relations` out of M2 and cannot store the three document judgements
extraction §13 item 1 requires before the first run.

**Proposed fix.** Amend the tag line to name `parties`, `party-names` and
`relations` (for document relations) as M2, and list `parties` once in the
language step table.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections": the tag line names `parties`, `party-names`
and the document relations of `relations` as M2; `parties` listed once in
the language step table.

### W2-35 (minor, M2)

*Lenses:* cross-file. *Files:* jetp-fusion.md §3 (Reading and verification); jetp-operation.md §5 (Selection and calibration); jetp-ledger-storage.md §4

**Finding.** 'The accepted and rejected match judgements of the M1b
catalogue' appears in normative text in fusion §3 and operation §5, but
'M1b' is not a milestone of requirements §2.2 and is defined nowhere in the
specification; the reference answers for matching (M2 selection, M3b use)
point at a set no document identifies, while storage §4 names it concretely
(the 257 register rows and 67 plan lines matched by hand).

**Proposed fix.** Replace 'the M1b catalogue' in both places with a
reference to the hand-made match judgements identified in storage §4.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections" and (B) "the reading protocol stated once, in
extraction 6.3": "the M1b catalogue" replaced by the matches decided by hand
of storage 4.

### W2-36 (minor, M2)

*Lenses:* implementation. *Files:* jetp-ledger-storage.md §4 (Matching records, tier thresholds); jetp-extraction.md §14; config/jetp_tracking.yaml (`matching.panel`)

**Finding.** Storage §4 points the panel's stance-and-confidence rule at
`matching.panel` in `config/jetp_tracking.yaml`, which holds the previous
design (three named hosted readers, majority vote, confidence as agreement
weight times mean self-score), not two local readers, an arbiter and IPCC
terms. No configuration location is named for the M2 extraction rule's
versioned settings (acceptance level, calibration mapping, part size), so a
builder following the pointer implements the wrong panel.

**Proposed fix.** In storage §4 say that `matching.panel` is superseded and
rewritten at M3b. Name one versioned reading configuration (for example
`config/jetp_reading.yaml`) for readers, arbiter, acceptance and escalation
levels, calibration mapping and part size, and cite it from extraction §14
and W2-05's rule.

**Outcome.** applied in part in (A) "dispositions and restatements journals,
line status, journal corrections": the stale `matching.panel` pointer is
removed and the reading settings (readers, arbiter, acceptance level,
calibration mapping, part size) are one configuration versioned with the
method. Rejected in part: naming a file (`config/jetp_reading.yaml`), an
implementation choice the specification need not fix.

### W2-37 (minor, M2)

*Lenses:* state-of-the-art. *Files:* jetp-fusion.md §1 (Calibrated language); jetp-extraction.md §6.3 (calibration error)

**Finding.** The IPCC likelihood ranges are nested (likely 66–100 % contains
very likely 90–100 %), so a model that answers 'likely' on everything at 95
% observed precision has zero calibration error and its terms carry no
information; the mapping from raw self-scores to terms is undefined on
overlapping bins, and the check 'the terms whose observed precision falls
outside their stated range' cannot fail for coarse terms. The acceptance
level 'likely or more' and the expected error a result derives from observed
rates both need disjoint bins.

**Proposed fix.** Fusion §1: state disjoint bins (for example 99–100, 90–99,
66–90, 33–66, 10–33, 1–10, 0–1) as the calibration target, keeping the IPCC
wording for display; extraction §6.3 defines the calibration error against
the disjoint bin.

**Outcome.** applied in (B) "the reading protocol stated once, in extraction
6.3": for calibration, each IPCC term stands for its range less the stronger
terms beside it, so the bins are disjoint; the words shown stay the IPCC's
(author decision kept); the calibration error is measured against the bin.

### W2-38 (minor, M2)

*Lenses:* state-of-the-art. *Files:* jetp-fusion.md §1 (Calibration); jetp-extraction.md §6.3, §12; jetp-requirements.md Q17

**Finding.** Fusion §1 admits to the calibration set 'the register rows and
plan lines matched by hand, and any decision the author chose to make'.
Decisions on served results are made after seeing the machine readings, on
items selected because they ranked low, and accrue after the split,
contradicting X-01's rule that the held-out part is frozen with the method
version; per-term precision, calibration error and the agree-but-wrong rate
become biased by selection on the outcome and by non-blind labels, so the
published calibration record would not measure what it claims.

**Proposed fix.** Fusion §1 and Q17: only reference answers made blind to
the machine readings enter the tuning or held-out sets; author decisions on
served results are readings of role `author`, reported apart as an overturn
stratum. Add a §12 check that refuses a held-out item whose readings show an
author row dated after a machine row.

**Outcome.** applied in (B) "the reading protocol stated once, in extraction
6.3": only answers made blind to any machine reading calibrate; the author's
decisions on served results are reported apart. Rejected in part: the
section 12 refusal check; the held-out part is frozen at the split, so a
later author decision cannot enter it.

### W2-39 (minor, M2)

*Lenses:* state-of-the-art. *Files:* jetp-operation.md §5 (Selection and calibration); jetp-extraction.md §6.3 (Calibration); jetp-results.md §4 (calibration record)

**Finding.** 'The arbiter, a stronger hosted model, is calibrated on the
same answers', that is on the whole held-out set, but it only ever sees
items the readers disagreed on or scored below the acceptance level. Its
precision on easy, agreed items says nothing about the escalated
distribution where every arbiter judgement is made, and the protocol's end-
to-end precision (agreed plus arbitrated), the number that bounds error in
the ledger, is never computed.

**Proposed fix.** Operation §5 and extraction §6.3: score the arbiter on the
escalated subset of the held-out set (readers run first), per stratum; add
the protocol's end-to-end precision per stratum with a Wilson interval to
the calibration record.

**Outcome.** applied in (B) "the reading protocol stated once, in extraction
6.3": the arbiter is scored on the held-out items the readers escalate; the
calibration records the protocol's end-to-end precision.

### W2-40 (minor, M2)

*Lenses:* data-to-come. *Files:* jetp-requirements.md §3.7 AED-3, Q17; jetp-operation.md §8

**Finding.** AED-3 asks what an accepted change costs 'in LLM spend and in
human minutes, per method', but no rule records human minutes any more:
W1-46's minute logging went with the autonomy correction, operation §8
records GPU time and paid spend only, and a `readings` row of role `author`
carries no time. The human side of the comparison AEDIST wants is not
captured.

**Proposed fix.** Reword AED-3 to 'in LLM spend, compute time and the count
of human decisions'. Do not add a minutes field, which would cut against the
autonomy rule.

**Outcome.** applied in (C) "autonomy residue, cost bases after local
readers, Zotero at M2": AED-3 counts LLM spend, compute time and human
decisions; no minutes field.

### W2-41 (minor, M3a)

*Lenses:* within-file, cross-file, data-to-come. *Files:* jetp-operation.md §4 (What agents may not do; run-output pull requests); jetp-collection.md §9; jetp-fusion.md §3 (row 2); jetp-requirements.md F7, C1

**Finding.** 'Admit a document' heads the list of what agents may not do,
beside accepting a milestone, freezing, releasing and publishing. Under the
settled autonomy, admission is a triage outcome the panel decides (fusion §3
row 2, collection §9 'nothing is queued for the author', F7 'which may be a
checked LLM judgement'), produced by runs agents launch and landing through
run-output pull requests agents may merge 'within a scope the author has
already decided'. Read literally the prohibition re-routes every M3a
admission to the author, which C1 forbids; a builder of the M3a gate cannot
tell which reading holds.

**Proposed fix.** Reword to 'admit a document by hand, outside the triage
protocol of collection §9'; triage admissions land through the run-output
gate like any other run product; milestone acceptance, freeze, release and
publication stay the author's.

**Outcome.** applied in (C) "autonomy residue, cost bases after local
readers, Zotero at M2": agents may not admit a document by hand, outside
triage.

### W2-42 (minor, M3a)

*Lenses:* cross-file, state-of-the-art. *Files:* jetp-collection.md §2 ('held'), §9 (context only); jetp-extraction.md §7 (`out_of_scope`); jetp-ledger-storage.md §1 (target `triage-judgements`, Times per table `documents`); jetp-language.md; jetp-requirements.md F2, F7 (test)

**Finding.** W1-26's decision (a context-only candidate is registered with
the disposition `out_of_scope`) left three definitions unaligned. A context-
only candidate is registered without the triage outcome 'admit', yet 'held'
requires admission; extraction §7 calls such a document 'held for context',
which it then is not; the Times-per-table row enters a document into the as-
of state only by 'the admit triage judgement from M3a', so context-only
documents, which F2 counts and DA9 and the redistribution list may cite, are
never in any release's state and a `cites` relation to one resolves to
nothing at K; and F7's test says a candidate is 'absent from the register
until an admission decision' while context-only enters on a non-admission
decision.

**Proposed fix.** Define admission as any triage outcome that registers the
document (`admit` or `context only`), with `out_of_scope` the disposition
that stops extraction; storage §1: a document enters the state at K by an
in-force triage row of outcome `admit` or `context only`, `reject` and
`duplicate` keeping it out. Apply across collection, language, extraction
§7, the Times-per-table row and F7.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections" (a document enters the state by an in-force
triage row of outcome admit or context only), (B) "the reading protocol
stated once, in extraction 6.3" (`out_of_scope`: "registered for context")
and (D) "collection rules for M2 scans, admission, captures and blind lists"
(admission covers context only).

### W2-43 (minor, M3a)

*Lenses:* state-of-the-art, data-to-come. *Files:* jetp-collection.md §2 (mirrors), §8 (Access ladder rung 5; Access and unreachable documents); jetp-ledger-storage.md §1 (targets `retrievals.archive_url`, `web-archive`); jetp-ontology.md §2 (Retrieval); jetp-results.md §7; jetp-operation.md §11; jetp-requirements.md F27, Q8, DP-4

**Finding.** An archive capture has two homes and no rule makes one. §2
makes 'a web archive copy' a second document (a mirror folded by `same_as`
with the archive as host party) while §8 rung 5 makes it a retrieval of the
same document with the archive as host and the target schema puts
`archive_url` on `retrievals` (W1-23's fix applied both options its text
offered); a builder following §2 registers archive copies as documents,
doubling the register, and no table records the host party of a rung-5
retrieval either way. Separately, results §7 and the redistribution list
assume 'the capture of the document's address recorded with its retrieval',
but no collection rule requests a capture when a document is fetched;
captures appear only as the M4 monthly link-rot retry. Since unknown terms
forbid redistribution and secretariats state no licence, most M3b documents
will be cited rather than served, their public copy reading 'live address
only', and from M4 link rot turns F27's present-tense check red on documents
lawfully held.

**Proposed fix.** Collection §2: remove 'a web archive copy' from the mirror
sentence and state that an archive capture is always a rung-5 retrieval; add
`host_party_id` to `retrievals` [M3a] and one sentence to ontology §2
Retrieval. Collection §8 [M3a]: at each successful retrieval of a document
whose bytes may not be redistributed, request an Internet Archive capture,
record `archive_url`, and record and retry a failure on the M4 schedule. Do
not touch F27.

**Author question.** Requesting a capture makes the Internet Archive fetch
the publisher's page on the project's behalf, and the collection rules say
any request to a publisher needs author authorisation. Options: (a) request
a capture at every successful retrieval of a non-redistributable document
from M3a (the archive fetches public pages as it does for anyone; the
capture is what makes releases reconstructible by third parties under Q8 and
DP-4); (b) captures only in the M4 link-rot job, as now, accepting that M3b
public copies mostly read 'live address only'; (c) no capture requests,
citation by live address only. Recommended: (a); it is the one step that
lets a third party check a release without the project serving bytes it may
not redistribute.

**Outcome.** applied in (D) "collection rules for M2 scans, admission,
captures and blind lists", by the recommended default (a), which routes
nothing to the author: an archive copy is always a rung-5 retrieval, and a
capture is requested at each successful retrieval of a document whose bytes
may not be redistributed, a failure retried at M4. The request goes to the
archive, not to the publisher, so the authorisation rule for publisher
requests does not apply. Rejected in part: `retrievals.host_party_id`; the
rung (`web-archive`) and `archive_url` already say where the copy is.

### W2-44 (minor, M3a)

*Lenses:* within-file. *Files:* jetp-collection.md §5 (Stopping rule, condition 3), §6 (Recall); jetp-requirements.md Q10

**Finding.** §6 defines two recall figures (frame as declared, frame as
widened) and a variant of each (with and without round-zero holdings), but
condition 3 of the stopping rule gates on 'the campaign's known-item recall'
without saying which; the rule must be decidable before round one (Q10) and
the code that fires it needs one figure.

**Proposed fix.** State in condition 3 which figure gates: the widened-frame
figure with round-zero holdings included, items whose own miss widened the
frame counted as missed. Publish the others beside it.

**Outcome.** applied in (D) "collection rules for M2 scans, admission,
captures and blind lists": the gate reads the widened-frame figure with
round-zero holdings included.

### W2-45 (minor, M3a)

*Lenses:* data-to-come. *Files:* jetp-collection.md §6 (Known items, Blind use); jetp-ledger-storage.md §1 (target `known-items`); jetp-requirements.md F23

**Finding.** 'Those who search do not see the list', but the target schema
makes the known-item list a ledger table (`known-items`) under `data/jetp/`,
committed in git, pulled into every worktree and served or named under F23,
while the searching agents work in that repository. The hash 'recorded in
the round log before the first round' proves the list existed, not that it
stayed unseen; the M3a stopping gate and the published recall figure become
circular in the way §6 itself warns about.

**Proposed fix.** State in §6 and in the storage row that the list is kept
outside the repository, sealed by its hash in the round log, until the
freeze; it is committed as `known-items` only then, and the checkpoint
comparisons run in the session that holds it.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections" and (D) "collection rules for M2 scans,
admission, captures and blind lists": the known-item list is kept outside
the repository, sealed by its hash, until the freeze.

### W2-46 (minor, M3a)

*Lenses:* data-to-come. *Files:* jetp-collection.md §10 (Document classes, series row); jetp-ledger-storage.md §1 (target `documents.class`); jetp-requirements.md DA6

**Finding.** The series row says 'the series' publisher and stated
periodicity are recorded', but there is no column or table for a series'
periodicity or expected next issue: `documents` gains only `class` at M3a
and `edition_of` relates issues without naming the series. DA6's M4 test ('a
late issue of a series is signalled') has no data to run on, and the M3a
class judgement is the moment the periodicity is read.

**Proposed fix.** Add a nullable `periodicity` (with the series publisher)
to the target `documents` class row, or a small `series` table, one row per
series, not per issue.

**Outcome.** deferred to M4 in (D) "collection rules for M2 scans,
admission, captures and blind lists": periodicity serves DA6's M4 test only,
so it moves to the M4 column of collection 10 instead of a new M3a column or
table.

### W2-47 (minor, M3a)

*Lenses:* within-file. *Files:* jetp-operation.md §9 (Test of recovery)

**Finding.** The sentence says 'once per milestone' the store is restored
and replayed; the tag says '[M2 once; M4 per release]', leaving M3a and M3b
out, while W1-22's fix asked for the test 'before each freeze and each
release'. Whether a restore-and-replay runs before the M3a freeze and the
M3b release is what the tag decides.

**Proposed fix.** Make the tag match the sentence: '[M2, then before the M3a
freeze, before each release from M3b]'.

**Outcome.** applied in (C) "autonomy residue, cost bases after local
readers, Zotero at M2": the recovery test runs at M2, then before the M3a
freeze and before each release.

### W2-48 (minor, M3b)

*Lenses:* within-file, cross-file. *Files:* jetp-fusion.md §7 (Counting, chronology); jetp-requirements.md F14, F19, OBS-1; jetp-ontology.md §4 (money axis)

**Finding.** After X-06 the ontology's money axis lists the flows as 'IATI
`pledge`, `commitment`, `disbursement`, `expenditure`', but the 'one closed
list' F14 says is stated in fusion §7 reads '(commitment, disbursement,
expenditure)' and F14 repeats the three-flow list, while OBS-1 asks 'what
was pledged' and F19's gaps start at 'announced'. A pledge flow read from
IATI has no place in the chronology, 'an aggregate selects one state
explicitly' cannot select it, and whether a partnership pledge is a `pledge`
flow, an `envelope` need or the `announced` state is unstated.

**Proposed fix.** State the list once in fusion §7 with `pledge` placed
first among the flows, align F14, and keep the list identical to the
ontology's. Whether partnership-level pledges are typed as envelopes belongs
to the pending X-06 decision on the measure list; add no reading rule here.

**Outcome.** applied in (E) "M3b gaps: transition functions, pledge, deposit
status, word list": pledge heads the flows of fusion 7, the one list; F14
cites it instead of repeating it. The envelope question stays with the
pending X-06 decision.

### W2-49 (minor, M3b)

*Lenses:* within-file. *Files:* jetp-requirements.md C10, C8 (test), §9 reverse map (Operation § 9 row); jetp-operation.md §9

**Finding.** C10 is tagged M4 but its test binds before the M3b release
('the handover note of Operation § 9 exists before the first release');
operation §9 tags the note [M3b]; the reverse map lists Operation §9 as
serving only Q19 (M2), so by C8's own test the M3b handover rule maps to M4,
after the release it must precede. Whether the note is written before the
first release identifier is minted (X-24's decision) depends on which of the
three statements the builder follows.

**Proposed fix.** Tag C10 'M3b for the handover note, M4 for the horizon'
and add C10 to the Operation § 9 row of the reverse map.

**Outcome.** applied in (C) "autonomy residue, cost bases after local
readers, Zotero at M2": C10 is M3b for the handover note, M4 for the
horizon; Operation 9 serves C10 in the reverse map.

### W2-50 (minor, M3b)

*Lenses:* cross-file. *Files:* jetp-requirements.md Q13 (test), §2.1 (finite review tests); jetp-observatory-presentation.md (Evaluative words)

**Finding.** §2.1 makes review tests finite by searching 'the list of
evaluative words of the presentation', but that list (on track, off track,
delayed, behind schedule, failed, broken promise, promise kept,
underperforming, success) holds no causal or speed word, so the finite form
of Q13's test ('no causal or speed claim in the Observatory') detects
nothing Q13 forbids; the M3b build search passes vacuously while pages may
say 'because', 'accelerated' or 'faster than'.

**Proposed fix.** Add a second word list for causal and speed terms to the
presentation, searched by the same build step, and have Q13's test name it.

**Outcome.** applied in (E) "M3b gaps: transition functions, pledge, deposit
status, word list" by extending the presentation's one evaluative list with
cause and speed words, which Q13's test now searches. Rejected in part: a
second word list.

### W2-51 (minor, M3b)

*Lenses:* within-file. *Files:* jetp-observatory-presentation.md (Organisation and vocabulary, release history); jetp-results.md §4, §10

**Finding.** The release-history page 'lists every release with its status'
(current, superseded by a named correction, withdrawn), a status that
changes after a release is frozen, but results §4 builds the Observatory
'from the release alone', §10 says the site 'computes nothing the release
does not contain', and §4 makes the deposit's metadata record 'the one
place' that gains a status. Whether the page is built from release data
(then it cannot show later statuses) or from deposit records (then it sits
outside the frozen package) is undecided.

**Proposed fix.** State that the release history is generated at publication
from the deposit metadata records and sits outside the frozen package, like
the deposit record.

**Outcome.** applied in (E) "M3b gaps: transition functions, pledge, deposit
status, word list": the release history is generated at publication from the
deposit records, outside any frozen package.

### W2-52 (minor, M3b)

*Lenses:* state-of-the-art, dead-angles. *Files:* jetp-results.md §6 (Metadata), §9 (Withdrawal); jetp-operation.md §9 (handover); jetp-requirements.md F29; jetp-legal-note.md (open point 2)

**Finding.** W1-36's status field is one the deposit cannot hold and its
withdrawal one the depositor cannot execute. DataCite has no status
property; supersession is the `IsObsoletedBy`/`Obsoletes` relatedIdentifier
pair, not `IsNewVersionOf`, which Zenodo sets automatically for versions of
one concept record. On Zenodo the depositor cannot remove files after
publication; a record is removed only by Zenodo staff on request, leaving a
tombstone, so 'the identifier resolves to that record' is a third-party act
the handover note must cover, and the legal-demand case needs a route the
author can act on within days. F29's field list also omits DataCite's
mandatory `publisher` and `resourceType`, the publisher being legal-note
open point 2.

**Proposed fix.** Results §6: express a correction as IsObsoletedBy and
Obsoletes and carry status as a description or version note; add `publisher`
and `resourceType` to F29's list (publisher per the legal review). Results
§9: rewrite withdrawal as a removal request to the repository, the
Observatory pages removed by the author, the §5 pre-publication screen named
as the real control; list the request in operation §9's handover as a step
that needs a third party.

**Outcome.** applied in (E) "M3b gaps: transition functions, pledge, deposit
status, word list" and (C) "autonomy residue, cost bases after local
readers, Zotero at M2": status as a version note, correction as
IsObsoletedBy/Obsoletes, publisher and resource type in F29 and results 6,
withdrawal as a removal request to the repository, listed in the handover
note.

### W2-53 (minor, M3b)

*Lenses:* state-of-the-art. *Files:* jetp-results.md §5 (Named formats, descriptor); jetp-ledger-storage.md §3; jetp-requirements.md F31

**Finding.** 'The data dictionary is its Table Schema for each file; both
are generated from the DDL', but the per-document `line-
fields/<document_id>` tables carry the publisher's headers and are declared
by `line-field-specs`, not by the DDL (storage §3: 'It does not declare the
per-document field tables'), so F31's test ('every field appears in the
dictionary') fails for every line-fields file; and a sharded table published
as one Frictionless resource with a `path` array carries one `hash`, while
§5 requires every file 'with its ... SHA-256 hash'.

**Proposed fix.** Results §5: Table Schemas for common tables come from the
DDL and those for `line-fields/<document_id>` from `line-field-specs`;
publish one Frictionless resource per shard file so each file carries its
own hash.

**Outcome.** applied in (E) "M3b gaps: transition functions, pledge, deposit
status, word list": Table Schemas from the DDL for common tables and from
`line-field-specs` for per-document fields; one resource per shard.

### W2-54 (minor, M3b)

*Lenses:* state-of-the-art. *Files:* jetp-ontology.md §5 (Traceability, crosswalks); jetp-results.md §2

**Finding.** 'A result that counts by shared status or sector states the
weakest mapping among the rows it used', but SKOS mapping relations are not
totally ordered: `broadMatch` and `narrowMatch` are incomparable and
`relatedMatch` is not weaker than either on any declared scale, so 'the
weakest' has no definition a build can apply and results §2's M3b statement
cannot be validated.

**Proposed fix.** Declare the order exactMatch, closeMatch, broad or narrow,
relatedMatch in ontology §5, or restrict accepted crosswalk rows to exact,
close and broad; report the count of rows used per relation beside the
weakest.

**Outcome.** applied in (E) "M3b gaps: transition functions, pledge, deposit
status, word list": the order exactMatch, closeMatch, broad or narrow,
relatedMatch, with the count of rows per relation.

### W2-55 (minor, M3b)

*Lenses:* data-to-come. *Files:* jetp-results.md §2 (identifier stable within its release), §8, §9, §11; jetp-requirements.md F22, Q7, BK-2, DP-5

**Finding.** Nothing makes a result's identity stable across releases. §11
attributes 'every figure that differs between two consecutive releases', §9
lists the figures a correction changes, and §8 moves the book's figures to a
later release with each change 'explained as in section 11'; all three must
pair the same figure in two releases, yet §2 says changing any method
version 'makes a new result under a new version', so every recalibration
breaks the pairing. Retrofitting cross-release identity at the second
release is what F22 will hit; BK-2 and DP-5 depend on figures being
followable.

**Proposed fix.** In §2 state that a result carries a release-independent
key built from its unit, scope, financial state, world time and threshold,
method versions staying attributes; §11 pairs on that key.

**Outcome.** deferred to M4: F22 begins with the second release, and every
M3b result already carries the unit, scope, financial state, world time and
threshold (results 2) that a release-independent key would be built from, so
nothing has to be retrofitted; the key is written when F22 is built.

### W2-56 (minor, M3b)

*Lenses:* cross-file. *Files:* jetp-ledger-storage.md §1 (`observations` row, Target conventions); jetp-extraction.md §11 (Own status, Value)

**Finding.** Two M3b rules of extraction §11 have no column: 'the
publisher's status word and its axis are carried from the statement to the
observation' (`observations` has `own_status` but no `own_status_axis`), and
the typed missingness reason of the target conventions ('an unknown value is
an empty field with a typed missingness reason') appears in no table or
target row, so no validator rule checks it.

**Proposed fix.** Add `own_status_axis` and `missing_reason` (a closed
`terms` list) to the `observations` target rows [M3b].

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections": `own_status_axis` and `missing_reason` as M3b
target columns of `observations`.

### W2-57 (minor, M3b)

*Lenses:* within-file. *Files:* jetp-legal-note.md §5 (AI-generated text); jetp-extraction.md §6.3; jetp-results.md §5; jetp-operation.md §5

**Finding.** The note argues the art. 50(4) exception from 'data with a
recorded human check (operation §5)', but operation §5 contains no human
check; under the autonomy rule the only human check is the held-out
reference answers (extraction §6.3), and the pages' 'human review and
editorial responsibility' rests on the authored page copy and the named
reviewer's acceptance, not on the readings.

**Proposed fix.** Cite extraction §6.3 (calibration on held-out reference
answers) and the named reviewer's acceptance (results §5) as the human
review, and drop 'operation §5'.

**Outcome.** applied in (C) "autonomy residue, cost bases after local
readers, Zotero at M2": the legal note cites the calibration on human
reference answers and the named reviewer's acceptance.

## Rows, batch 2: external reviews

Grok 4.7, GLM-5.3 and Qwen3.8-Max, each as a critical reviewer, on draft
v0.2; the reviews are in [`external/`](external/README.md). A finding became
a row only if it was new to the wave-1 and wave-2 ledgers and passed the
merge rules.

| ID | Severity | Milestone | Raised by | Outcome |
|---|---|---|---|---|
| E2-01 | minor | M3b | Grok 4.7 | applied |
| E2-02 | minor | M3b | Grok 4.7 | applied |
| E2-03 | minor | M2 | Grok 4.7; GLM-5.3 | applied |
| E2-04 | minor | M2 | Grok 4.7 | applied |
| E2-05 | minor | M3b | Grok 4.7 | applied |
| E2-06 | minor | M2 | Grok 4.7 | applied |
| E2-07 | minor | M2 | GLM-5.3 | applied |
| E2-08 | minor | M2 | Qwen3.8-Max | applied |
| E2-09 | minor | M2 | Grok 4.7 | default accepted by the author 2026-09-30 |

### E2-01 (minor, M3b)

*Raised by:* Grok 4.7. *Files:* jetp-fusion.md §3 (Referents at a threshold)

**Finding.** A would-be `same_as` chain is "raised as a conflict for
review", with no reviewer left once no machine judgement goes to the author.

**Proposed fix.** Say who resolves it: the panel, judging A against C.

**Outcome.** applied in (B) "the reading protocol stated once, in extraction
6.3".

### E2-02 (minor, M3b)

*Raised by:* Grok 4.7. *Files:* jetp-requirements.md §4 (Reproducible research)

**Finding.** The principle "every released result is reproducible from a
frozen release and the recorded methods" is stronger than Q8, which limits
reproducibility to the recorded readings and third-party inspection to
documents with a public copy; a data paper could cite the stronger sentence.

**Proposed fix.** Let the principle defer to Q8.

**Outcome.** applied in (E) "M3b gaps: transition functions, pledge, deposit
status, word list", by cutting the principle to "in the sense of Q8".

### E2-03 (minor, M2)

*Raised by:* Grok 4.7; GLM-5.3. *Files:* jetp-extraction.md §6.3 (Arbiter)

**Finding.** The arbiter is shown both readings, a pairwise setting where
position bias is documented; nothing controls it.

**Proposed fix.** Present the two readings in an order drawn at random and
recorded.

**Outcome.** applied in (B) "the reading protocol stated once, in extraction
6.3" (one clause).

### E2-04 (minor, M2)

*Raised by:* Grok 4.7. *Files:* jetp-ledger-storage.md §3 (Engine)

**Finding.** "The ledger's rows are adjudicated by reading a diff in a pull
request" contradicts the run-output gate and the autonomy rule, under which
nobody reads rows.

**Proposed fix.** Say git is the audit log; row review is the readings
protocol.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections", with the line-volume detail cut.

### E2-05 (minor, M3b)

*Raised by:* Grok 4.7. *Files:* jetp-legal-note.md (open point 6); jetp-results.md §7

**Finding.** The repository is public (checked: GitHub reports it PUBLIC),
so the ledger tables, per-document fields included, are published before any
release; the redistribution list of results 7 governs only releases. The
legal note does not say so.

**Proposed fix.** Put the fact before the go-live legal review, without
reopening its timing.

**Outcome.** applied in (C) "autonomy residue, cost bases after local
readers, Zotero at M2": open point 6 asks the review to weigh it. Making the
repository private, as proposed, would reopen the author's decision that the
legal review comes at go-live, and is not proposed here.

### E2-06 (minor, M2)

*Raised by:* Grok 4.7. *Files:* jetp-operation.md §4 (run-output gate)

**Finding.** The cross-family reviewer of a run-output pull request may be
the arbiter's maker, reviewing rows its own model decided.

**Proposed fix.** The reviewer is of a family other than the readers' and
the arbiter's.

**Outcome.** applied in (C) "autonomy residue, cost bases after local
readers, Zotero at M2".

### E2-07 (minor, M2)

*Raised by:* GLM-5.3. *Files:* jetp-requirements.md (FAIR, C6, DA2); jetp-results.md §7; jetp-operation.md §3, §7.1; jetp-extraction.md §6.2

**Finding.** Retired words survive in the specification: "source's terms"
for a publisher's terms, "reconcile" for counts adding up.

**Proposed fix.** Use the language document's words.

**Outcome.** applied in (E) "M3b gaps: transition functions, pledge, deposit
status, word list"; AEDIST's own terms in requirements 3.7 are left, as that
section declares them.

### E2-08 (minor, M2)

*Raised by:* Qwen3.8-Max. *Files:* jetp-ledger-storage.md §1 (locator rule)

**Finding.** The locator rule ends with "a value printed in three places is
three lines related by `same_as`", a fusion judgement stated as a storage
fact, in the wrong rule.

**Proposed fix.** Delete it; extraction 4 and ontology 3 already say that
relating the three is a judgement.

**Outcome.** applied in (A) "dispositions and restatements journals, line
status, journal corrections" (a cut).

### E2-09 (minor, M2)

*Raised by:* Grok 4.7. *Files:* jetp-extraction.md §6.3 (strata)

**Finding.** Strata of country x language x classification cannot be filled
from the hand-made answers; the published calibration will read
"uninformative".

**Proposed fix.** Coarsen the strata (language x method x statement shape).

**Outcome.** folded into W2-04 as option (d); default accepted by the author 2026-09-30; applied in "docs(jetp): apply the author's defaults for the last five decisions and the licence".

## External findings not admitted

| Finding | Raised by | Reason |
|---|---|---|
| Item-level human review of high-impact figures, a materiality queue or a seeded audit sample | all three | Reopens the author's autonomy decision (no machine judgement routed to the author). The brief sent to the external models still described "a sampled human review", which explains the convergence; agreement is weak evidence. |
| Release-blocking numeric floors on precision, recall or agree-but-wrong | Grok, Qwen | Reopens the autonomy decision (wave 1 W1-04, X-01): figures are published, not gated. |
| Recall gate on the Wilson lower bound, a larger known-item list, a minimum of items not held at round zero, capture-recapture at M3a | all three | The gate is the author's decision (W1-27); capture-recapture is pending as X-17. |
| Legal hard gates before M3b: private repository, no Zotero upload and no hosted call until agreements exist, per-table assessment now | all three | Reopens the author's decisions (Zotero off-site copy; legal review at go-live). The public-repository fact is carried to that review (E2-05). |
| Replace depth-one equality by connected components with conflict detection; cite Fellegi-Sunter | GLM, Qwen, Grok | Depth one is decided and reasoned (likelihoods do not compose); a star needs no pairwise closure, so the claimed O(n^2) growth does not arise. |
| Serve the cautious figure, the inclusive one as an annex | Grok | The two-threshold range is the decided design (W1-30); the range is the served figure. |
| Split M3b; cut accounts, markers and indicators from M3b | Grok, Qwen | Milestone scope is the author's ladder (0725); markers and deflators are already M4 unless F19 needs them. |
| Move to SQLite or Dolt as system of record before M4 | GLM, Qwen, Grok | Engine decided (storage 3); Dolt is the recorded M4 option. |
| Retire ODEM; merge the ten documents into five; generate the maps | GLM | The frame is the author's decision (language, 2026-09-23); consolidation adds work and serves no requirement. |
| JSON-LD and schema.org markup, SKOS export at M3b, RO-Crate earlier, CSL-JSON per document, PROV engine | GLM, Qwen, Grok | No requirement or milestone needs them; DataCite metadata carries discovery (F29); PROV and RO-Crate are decided M4 options. |
| Adversarial-document protocol, hidden-text fixtures for PDFs at M2, quarantine | Qwen, Grok | Decided M4 in wave 1 (W1-55, X-11); no new argument beyond agreement. |
| Source permission matrix; no automated fetch where terms forbid | Qwen | Contradicts the author's C6 (a single fetch of a public document goes ahead, the position recorded). |
| Redaction before hosted calls; hosted calls blocked on personal-data flags | Qwen | The legal position on hosted calls is settled at the go-live review (author decision); every call requests no retention. |
| Presentation UI mechanics moved to an implementation guide | Qwen, GLM | The presentation is in force, accepted by the author; not a defect. |
| A two-country joint document cannot be represented (DA1) | Grok | A statement carries its own country (`lines.country`); no held case needs a document-level list. |
| A validator check that comparator lines never enter a strict figure | Grok | F13's test already checks strict-scope figures for attribution; a second check adds nothing. |
| DA2 reconciliation does not add up (91 against 87) | GLM | It adds up: 81 + 6 + 4 = 91; the reviewer's extraction dropped the IATI term. |
| "No evidence" versus the inclusive threshold | GLM | The confidence floor (low or more) is what excludes a judgement made on no evidence; consistent as written. |
| Glossary of external references (B-cubed, NUSAP, AEDIST); "operation" overloaded; valid and transaction time | GLM | Cited at first use or defined in the language document; renaming serves no requirement. M1b is W2-35. |
| Workload model, recalibration effort, succession plan, served corrections table at M3b, F19 scoped to the horizon | Qwen, GLM, Grok | Covered or decided: costs are measured on the first calibration run (W2-26); the handover and deputy are X-24 (default accepted 2026-09-30); F25 counts are M4; Q16 wording already stops a gap reading as a verdict. |
| Findings already in the wave-1 or wave-2 ledgers (restatements, in-force DDL, IPCC bins, M1b, cost bases, captures at fetch time, personal-data screen, line-groups, recorded_at targets) | all three | Merged into the existing rows (W2-01, W2-02, W2-05, W2-26, W2-35, W2-37, W2-43, W2-17; X-22, X-27, W1-06). |
