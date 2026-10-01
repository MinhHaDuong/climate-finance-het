# REL lane over the local RePEc mirror (ReDIF)

Ticket 1810, child of 0700; harvest lane, step 1 of the protocol
`conception/rel-audit-finalisation-corpus.md`. Run on padme, 2026-10-01.
Delivery: `data/rel_intake/t1810-repec-local/2026-10-01/` (DVC), checked by
`scripts/qa_rel_intake.py` (exit 0). Producer commit `a5d285fa`, on this
branch. Three earlier deliveries were never merged and are not kept:

- round 1 (producer `72a22eb`): 1,441 malformed `record_id`s and
  mixed-encoding mojibake;
- round 2 (producer `44b59d8a`): handles cut at their first inner space, which
  merged distinct works;
- round 3 (producer `cdaf0884`): 4 `sos` records taken from a byte-shifted
  copy.

The details are below.

**For the screen.** The recall pre-filter of step 5 (below) is experimental and
**not applied (MOE recommendation, pending author decision)**: it removes
nothing from the delivery or the pool. The MOE recommends that Qwen stage 1
screen every record of this delivery directly; the author has not yet decided.

## Mirror and table

The mirror is the `RePEc-ReDIF` module of `rsync://rsync.repec.org/`, at
`/data/mirrors/RePEc/` on padme. It was refreshed on 2026-10-01 (started
00:04 CEST; log `/data/mirrors/RePEc_refresh_2026-10-01.log`). Files that the
refresh replaced or removed are kept in
`/data/mirrors/RePEc_replaced_2026-10-01/`: 403,356 files, which is the
344,437 updated plus the 58,919 deleted files. The itemized counts below were
read from the log by `scripts/catalog_rel_repec_redif.py --rsync-log`:

- 86,275 new files;
- 344,437 updated files: 79,680 changed in size and time, 264,704 in time
  only (mostly `index.html`), and 53 with other attribute changes;
- 58,919 deleted files and 198 deleted directories;
- 1,084 new directories.

Caveat: rsync ran without `--stats`, so the log has no summary line and the
remote exit code was not captured. Completion rests on two observations: no
rsync process remained, and the log runs through the last archive (`zur/`)
with no error line.

`scripts/catalog_rel_repec_redif.py` (parser `scripts/_redif.py`) walks the
mirror and keeps every file whose first 64 KB open a ReDIF template. The
mirror stores ReDIF under `.rdf`, `.redif`, `.RDF`, `.txt` and no extension,
next to PDFs and HTML.

A value runs on until the next line that opens a known ReDIF attribute, so
`Purpose:` or `https://` at the start of an abstract line stays in the
abstract. A file that is not valid UTF-8 is decoded line by line: each line
is read as UTF-8 when it decodes and as cp1252 when it does not, so a single
cp1252 line no longer turns the UTF-8 templates of its file into mojibake.

The `Handle` value is cleaned before use. Only its first line counts (a
following unprefixed line is stray text, not part of the id), an inline
`# comment` is cut, non-printable characters and every whitespace are removed,
and the prefix is written `RePEc`. Whitespace is removed rather than split on,
because an inner space can belong to the id (`…:i:Special 12:p:827`,
`eeep10-2-von der Fehr`). A cleaned handle
that still lacks the `RePEc:aaa:series:item` form is malformed at the source
(an empty series in `bre/` and `aoo/`, an `oai:` id, a `UCEMA:` prefix). Such
a row is kept, because the item is real, and flagged `handle_valid = 0`.

**Handles merged by cleaning (round-2 check N2).** Round 2 kept only the first
token of a handle. Over all 663 duplicate rows that this rule created, the
dropped copy was re-read from its source file and its title compared with the
kept row (token Jaccard ≥ 0.5 = same work). 414 rows (250 handles) were
distinct works. The bulk were whole issues or series collapsed onto one id:
an Amfiteatru special issue, `eeep10-2-von der Fehr` with `…-von Hirschhausen`,
plus series in `cep`, `exl`, `rsc`, `bla`, `gyz` and `akw`. Removing
whitespace instead brings 238 rows back to the table. Of the 486 merges that
cleaning still creates, 251 are the same work and 6 copies could not be re-read.
The other 229 rows are not 229 lost works:

- 218 are in `sos:sosjrn`. That archive holds its articles twice: in
  `sosjrn.rdf`, which decodes cleanly (1,024 templates), and in `sosjrn.txt`, a
  byte-shifted UTF-16 copy (270 templates). In the shifted copy every handle
  and 156 titles carry NUL or U+0A00, and the titles belong to neighbouring
  records. These rows are a corrupt duplicate of the same works under the
  same handles, not distinct works.
- 7 are in `mmb:journl`, which reuses item numbers `1` to `7` across issues;
  RePEc itself shows one page per handle.
- 4 are in other archives (`azz`, `sur`, `aaa`, and one `noHandle`).

Together with the 6 copies that could not be re-read, the residual true loss
is therefore 17 rows or fewer out of 5.6 M.

Up to round 3, the fuller-copy rule kept the shifted `sos` copy for 33
handles, because that copy had more filled fields; 4 of those records were in
the delivery. Since round 4, a copy with a non-printable character in its raw
handle or title loses to a clean copy. No delivery record now comes from
`sosjrn.txt`: all 49 delivered `sos` records come from `sosjrn.rdf`. The
table keeps one `sosjrn.txt` row, a handle without a clean copy.

Probe: `probe_n2v3.py` in the session scratchpad, not committed.

Table: `~/data/projets/climate-finance-het/rel_repec/2026-10-01d/redif.parquet`
on padme, with `redif.counts.json` and `redif.duplicates.csv` next to it.

| | count |
|---|---:|
| files seen (PDF, images and archives skipped by extension) | 2,093,590 |
| files holding ReDIF | 2,051,375 |
| files skipped: over 512 MB / unreadable | 2 / 1 |
| of which read entirely as cp1252 / mixed UTF-8 and cp1252 / UTF-16 | 96,777 / 329 / 12,050 |
| ReDIF-Article templates | 4,638,644 |
| ReDIF-Paper templates | 1,414,420 |
| ReDIF-Chapter templates | 339,190 |
| ReDIF-Book templates | 77,605 |
| work templates without a handle (not kept) | 1,306 |
| handle repeated in another file (fuller copy kept) | 861,204 |
| **rows (one per RePEc handle)** | **5,607,349** |
| articles / papers / chapters / books | 3,847,667 / 1,355,640 / 334,642 / 69,400 |
| handles changed by cleaning (prefix case included) | 112,951 |
| rows kept with a handle malformed at source (`handle_valid = 0`) | 5,035 |

The four template counts sum to 6,469,859. Removing the 1,306 rows without a
handle and the 861,204 repeats leaves the 5,607,349 rows. Elsevier (`eee/`)
accounts for 756,987 of the repeats, because its per-journal files overlap.
When copies of a handle differ, the table keeps the one with the most
non-empty fields, without merging fields across copies.

Eleven work templates carry a type misspelled beyond repair (`edif-paper`,
`kedif-paper`, `medif-paper`, `redif-ppaer`, `redif-bookreview`) and are not
kept.

## Queries

`config/rel_repec_search.yaml` adds no new vocabulary. It replays strings that
other lanes already declared:

- **1652 causal-map matrix** (`config/rel_causal_search.yaml`): every family
  and theme string (IM, IO, SY, CS, TH; en, fr, es). The SI rows cite tuning
  sentinels in OpenAlex; the mirror has no citation index, so they are
  replayed as title searches of those tuning sentinels, as the EconLit twin of
  1652 did. Also the per-family JEL rows that 1652 wrote for EconLit (the
  family's JEL codes AND its mediator group).
- **1530 ICF terms of the protocol** (`config/rel_sud_search.yaml`): themes
  T1 to T4 in all ten languages, plus the global gap-fill string.
- **A declared JEL filter**, fixed before the run: `(Q54 or Q56) and (F35 or O19)`,
  `Q54 and (F2 or F3)`, `F35 and (Q4 or Q5)`.

Local matching (`scripts/_rel_local_query.py`) stands in for OpenAlex
`title_and_abstract.search`:

- Title, abstract and keywords are each folded for case and accents on their
  own, so a phrase cannot run across two fields.
- A phrase matches on word boundaries, and its last word also matches with a
  plural "s".
- In Indic scripts, vowel signs stay inside their word. In the first
  delivery, dropping them had produced one false Hindi hit (`RP-SUD-T3-hi`).
- No year and no language filter is applied.

It differs from OpenAlex in three ways: it does not stem, it searches
keywords, and it matches phrases literally.

| source | units | hits (sum over units) |
|---|---:|---:|
| 1652 text strings (RC) | 132 | 14,805 |
| 1652 JEL rows (RE) | 22 | 76,034 |
| 1530 T1–T4 and gap-fill (SUD) | 41 | 17,958 |
| declared JEL filter | 3 | 631 (195 / 321 / 115) |

Twenty-seven units retrieved nothing. Each has a positive control in
`zero_hit_controls.csv` (next to the table): the hit count of each of its AND
groups taken alone, and for non-Latin scripts the number of table titles in
that script. The 27 fall into five groups:

- **Ten 1652 rows whose groups never meet.** The nine French and Spanish rows
  and `RP-RC-land_spillovers-CS-en`: every AND group matches records, but never
  the same record. For `RP-RC-grid-IM-fr`, 439 records hit the ICF group and
  6,121 the mediator group. For `land_spillovers-CS-en` the counts are 44,556,
  17,583, 7,330 and 93,022.
- **Three SI title searches** that name tuning sentinels absent from RePEc.
- **Arabic T1, T2, T4 and Hindi T1 to T4.** The table holds 1,736
  Arabic-script and 1,230 Devanagari titles, but none carries an ICF phrase.
  The Indic word-boundary fix is unit-tested on a Hindi phrase
  (`tests/test_catalog_rel_repec_search.py`).
- **Bengali T1 to T4.** The table holds no Bengali title.
- **Indonesian T2 and T4, and Russian T4.** No record carries those phrases.
  For Russian this is a real null, since the table holds 83,189 Cyrillic
  titles.

## Delivery

| | count |
|---|---:|
| records (`records.csv`) | 79,522 |
| excluded `no_dedup_key` (no DOI, no year; title-only in the pool) | 915 |
| excluded `not_retrievable` (template without a title) | 1 |
| records with a DOI | 19,767 |
| records with an abstract | 98.1 % |
| articles / working papers / chapters / books | 57,410 / 19,909 / 1,806 / 397 |
| records whose handle is malformed at source (`lane_note`) | 11 |

`record_id` is the cleaned RePEc handle. No id now carries a space, a `#` or
a control character; the first delivery had 1,441 such ids.

Change from the first delivery's 79,543 records to 79,522:

- cleaning merged 4 of the first delivery's ids into others, leaving 79,539;
- 29 of those are no longer retrieved:
  - 14 have an unchanged text. They had matched only through a phrase running
    across the end of the title and the start of the abstract, which the
    per-field matching no longer allows.
  - 12 have a handle that now merges with another row or is re-keyed.
  - 3 have a text changed by decoding or by the fuller-copy rule.
- 14 records are new, mostly re-keyed ids, for example handles carrying a
  stray RTF `\par`.

That gave 79,543 − 4 − 29 + 14 = 79,524 in round 3. Round 4 loses 2 more
`sos` records, which had matched only through a neighbour's title in the
shifted copy, giving 79,522. Residual
mojibake sits in 16 titles and 36 abstracts, against 36 and 88 in the first
delivery, and U+FFFD in 16 titles and 134 abstracts. These are presumed to be
in the source files.

A RePEc handle is not a CNRI Handle, and the contract counts an EconPapers or
IDEAS page as a landing page, not a key. So `url` carries the DOI resolver when
the record has a DOI and the EconPapers handle page otherwise. It is blank for
the 9 records whose handle is malformed at source and that have no DOI, since
such handles have no EconPapers page. A record with
neither a DOI nor a year cannot be keyed and goes to `no_dedup_key`. The extra
column `query_ids_all` (`;`-joined, as in 1530 and 1653) lists every unit that
retrieved the record.

**The JEL rows: a recall-first, uncalibrated choice.** 63,364 records (80 %)
come only from the per-family JEL rows, and none of them needs an ICF term.
These rows pair a family's JEL codes with its mediator group; for example,
`F35 or O4 or Q43` with "emissions" or "GDP". 1652 wrote them for EconLit and
could never run them: EconLit is not licensed, and the EDS RePEc index returned
0 records on every one. Their precision has therefore never been measured. They
are delivered because the lane does not screen, and the ICF screen is what
sorts them out. The text strings and the declared JEL filter account for the
other 16,158 records.

Pool merge, run on padme with this delivery and the 1652 replacement
2026-09-30b (output not committed): 77,487 pool works. Of these, 2,905 are in
the catalogue, 9,602 are in another lane only, and 64,980 are new to the pool.
2,950 rows fall into the same work as another row of the delivery, usually a
working paper and its article sharing a DOI.

The lane is appended last, provisionally, to `lane_order` in
`config/rel_pool.yaml` and to `stage1.lane_priority` in `config/rel_screen.yaml`;
its placement is the author's call. The lanes added before it without a
placement (`t1650-sommaires`, `t1653-sud-hors-openalex`, both 1790 lanes) are
now listed above it in the order the merge already gave them, so 1810 outranks
none of them. `tests/test_rel_lane_wiring.py` fails when a committed
`data/rel_intake/*.dvc` lane is missing from either list. Once this delivery's `.dvc` pointer is on `main`, `make rel-pool`
includes it. To build the pool without it, point the merge at an intake
directory that leaves it out:

```bash
X=$(mktemp -d)
for d in data/rel_intake/t*/; do n=$(basename "$d"); [ "$n" = t1810-repec-local ] || ln -s "$PWD/$d" "$X/$n"; done
uv run python scripts/corpus_rel_pool.py --intake-dir "$X" --output-dir data/rel_pool_without_1810
```

## Recall

Sentinel recall is computed by `catalog_rel_repec_search.py recall`, which
writes `recall.json` and `recall.sentinels.csv` next to the table. "In mirror"
means that a DOI or normalised-title match exists in the table, which shows the
parser sees the record. Reserve (hold-out) sentinels are reported apart and
were never used to change a query.

| sentinel file | set | n | in mirror | retrieved |
|---|---|---:|---:|---:|
| `rel_causal_sentinels.csv` (1652) | tuning and other | 18 | 12 | 12 |
| `rel_causal_sentinels.csv` (1652) | **reserve** | 31 | 19 | **16** |
| `rel_sud_sentinels.csv` (1530) | tuning, retention, other | 41 | 9 | 9 |
| `rel_sud_sentinels.csv` (1530) | **reserve** | 14 | 1 | **1** |

The three reserve sentinels that are in the mirror but were missed show limits
of the queries, not of the parser:

- C02, "Higher cost of finance exacerbates a climate investment trap in
  developing economies", carries no ICF or aid term.
- C09, "Debt-for-climate swaps for small islands", has the SY phrase but none
  of its debt-outcome terms.
- C33, "The effect of aid on growth", has no emissions or energy term. Neither
  its text strings nor the `growth_scale` JEL row (O4 AND mediator) reach it.

RePEc holds few of the southern sentinels (10 of 55): the strength of this
lane is economics indexed by JEL, not the South.

American Economic Review 1990–1998: 1650 delivered 990 items of these years
from OpenAlex only, without a DOI. The mirror holds AER for those years
(160–194 records a year, series `RePEc:aea:aecrev`), and 910 of the 990
(92 %) match a mirror record on normalised title and year ±1. 187 of the 910
have an abstract in RePEc, but none of the 187 lacked an abstract in 1650, so
the mirror adds no abstract. The 80 misses are mostly titles that OpenAlex
truncates ("Agency costs, net worth, and business fluctuations: A"). RePEc has
no DOI for these years either, so the mirror confirms 1650's items but
resolves none of them to a DOI.

## What this lane adds

- **To 1652 (RePEc through bibCNRS EDS).** The replacement 1652 delivery
  (2026-09-30b) holds 2,225 RePEc records from EDS, capped at 500 per query
  (two queries hit the cap). This lane finds 1,992 of them (90 %), and 5,955
  of its 77,487 works share a pool work with 1652. The local replay has no cap
  and can be rerun. Most of its extra volume comes from the 1652 JEL rows,
  which returned nothing through EDS (above).
- **To 1650 (tables of contents).** 5,870 works shared with 1650. For AER
  1990–1998, see above.
- **To the pool.** 64,980 works new to the pool, unscreened as the contract
  requires.

## Recall pre-filter (step 5): experimental, not applied (MOE recommendation, pending author decision)

`scripts/corpus_rel_repec_prefilter.py` is the classifier the author asked for
on 2026-09-30. It feeds bge-m3 embeddings (`title + ". " + abstract[:2000]`,
256 tokens, CPU) to a logistic regression that predicts the Opus label "out"
(*hors sujet*). It could only ever drop records. It is **not applied (MOE
recommendation, pending author decision)**: on the measures below, the MOE
judges it not good enough to remove records before Qwen.

**Training.** 5,257 works:

- 4,631 Opus stage-2 labels from `icf_screen` (1530);
- the Jev-pilot labels in `config/rel_prefilter_labels.csv` (written by
  `scripts/corpus_rel_prefilter_labels.py`): 399 of the register's 400 Opus
  labels from the stratified random sample, and 227 of its 250 non-held-out
  adjudicated reference rows.

The missing labels are one sample work and two reference works that have no
text in the pool. Likewise 244 of the register's 245 held-out rows have a pool
text, hence the 244 in the validation table. The other 21 reference works are left out because they are
sentinels: **every sentinel work, of every set, is kept out of training**. In
the first fit, 12 of the 45 reserve sentinels and 7 of the 24 tuning sentinels
had been training rows. Label counts: icf 2,540, aux 2,056, out 482, unsure
179.

The training labels and the validation labels below both come from Opus,
either directly or through the adjudicated set where Opus is one judge of
four. The agreement they measure is therefore agreement with Opus, not with
an independent judge.

**Threshold.** A record is dropped when `p_out > 0.958911`. That value is the
largest out-of-fold score (5-fold) of any ICF-labelled training work or tuning
sentinel, so nothing that scores at or below a known ICF work is dropped. One
work sets it: a French title-only CDM paper, "Le Polycentrisme : un concept
heuristique pour l'analyse d'instruments de marché tel que le Mécanisme de
Développement Propre". The next ICF score is 0.933, and the top tuning
sentinel scores 0.955 (C31). The training out-of-fold row loses 0 ICF by
construction, so it is not a validation.

| set | n | dropped | ICF lost | share of "out" dropped |
|---|---:|---:|---:|---:|
| training, out of fold (not a validation) | 5,257 | 61 (51 out, 6 aux, 4 unsure) | 0 by construction | 11 % |
| Jev-pilot control (Opus, 200; 197 in pool) | 197 | 23 (22 out, 1 aux) | 0 of 22 | 20 % |
| Jev-pilot reference, held out (adjudicated) | 244 | 5 (5 out) | 0 of 88 | 10 %; weighted share dropped 3.4 % |
| sentinels, pool text: tuning / reserve / other | 24 / 45 / 35 | 0 / **0** / 0 | 0 | max `p_out` 0.955 / 0.832 / 0.828 |
| sentinels, the lane's RePEc record: non-reserve / reserve | 22 / 21 | 0 / **0** | 0 | max `p_out` 0.950 / 0.733 |

**Which delivery.** The pre-filter was fitted and scored on the round-2
delivery: 79,520 records plus 915 `no_dedup_key`, 80,435 rows, from producer
`44b59d8a`. The round-4 delivery has 2 more records (79,522) and differs in 238 table rows plus 33 `sos` rows now taken from the clean copy.
The pre-filter is not applied, so it was not refitted; the figures below are
those of round 2. Reproducing the fit needs that delivery, which stays in the
DVC cache and remote as directory md5 `ba7a05b0be485b843608ff2cf1929464`.

**On this lane (sample, not applied).** The CPU embedding throughput,
measured on padme while other jobs ran (load 15 to 18), was 4.3 to 5.6
texts a second at 16 to 20 threads, and 5.4 a second with four processes of
five threads. At that rate the 80,435 delivered rows (79,520 records and 915
`no_dedup_key` rows) would take 4.0 to 5.2 hours, over the three-hour CPU
budget.

The model was therefore scored on a simple random sample of 10,000
delivered rows (seed 1810), embedded for the first delivery. 9,990 of them
carry over to this delivery with the same id after cleaning and a
byte-identical text (`remap-embeddings`); 4 are absent and 6 changed text. The
model drops 628 of the 9,990, **6.3 %**. Extrapolated (derived, not run), that
is about 5,060 of the 80,435 rows.

| threshold | training ICF lost (OOF) | reserve sentinels lost (pool / lane record) | share of the RePEc sample dropped |
|---|---:|---:|---:|
| 0.80 | 8 | 1 / 0 | 46.2 % |
| 0.90 | 2 | 0 / 0 | 24.0 % |
| 0.95 | 1 | 0 / 0 | 8.8 % |
| **0.9589 (rule)** | **0** | **0 / 0** | **6.3 %** |
| 0.98 | 0 | 0 / 0 | 1.5 % |

**The Opus sample against distribution shift, re-read at the new threshold.**
The 200 records drawn for the first fit were reused with their Opus labels;
this cost nothing. That sample was stratified by the first fit's decision: 120
drawn at random from its 402 dropped rows and 80 from its 9,598 kept rows. One
record has no counterpart in the re-delivery. All 400 of the first fit's
dropped rows still in the sample stay dropped. The new fit also drops 228 rows
that the first fit kept.

| region of the new drop decision | rows in the 9,990 sample | Opus-labelled | out | aux | icf | ICF rate, 95 % upper bound |
|---|---:|---:|---:|---:|---:|---:|
| dropped by both fits | 400 | 119 | 118 | 1 | **0** | 2.5 % (rule of three); 3.1 % (Clopper–Pearson) |
| dropped by the new fit only | 228 | 4 | 4 | 0 | 0 | not informative (75 %) |
| kept | 9,362 | 76 | 43 | 30 | 3 | 11.1 % |

What "0 of 119" implies, as derived figures:

- The region dropped by both fits is about 3,220 of the 80,435 rows. At the
  2.5–3.1 % upper bound, up to **roughly 80–100 ICF works** could be lost
  there.
- The 228-row region the new fit adds, about 1,840 rows, is barely sampled.
  At the same rate the total bound over the ~5,060 drops would be about 130.
  That is comparable with the 122 ICF works the v2 filter lost.
- The kept rows hold ICF works at about 4 % (3 of 76), roughly 3,000 across
  the delivery, again derived.

Spend: USD 0.32 in total, all for the original Opus sample, summed from the
per-call `usage.cost`. The OpenRouter account moved from USD 120.7997 to
121.1231 used of 140, a difference of USD 0.3235. The re-read cost nothing.

**How this differs from the v2 filter.** The refined-corpus v2 filter scored
every work against a fixed query ("climate policy and financial mechanisms")
with a reranker. It cut at a threshold chosen for the corpus as a whole, and
122 of the 489 works it had dropped (and the Sud search found again) were ICF
on rereading. This pre-filter is fitted to the review's own ICF labels and
predicts "out" rather than relevance. Its threshold is the largest that loses
no known ICF work, but one work sets it, and its out-of-sample loss bound on
RePEc is of the same order as v2's loss. Hence **not applied (MOE
recommendation, pending author decision)**.

**Frozen.** The script is `scripts/corpus_rel_repec_prefilter.py` and the label
register is `config/rel_prefilter_labels.csv`. The model is `prefilter/fit/model.npz`,
sha256 `620b3c174c23053aa9549d398ebe3cdf3b0c8bf9f245b339bf68db5b848c5e58`, with
its threshold inside. It sits with `report.json`, `scores.csv`,
`opus_rescore.json`, the texts and the embeddings under
`~/data/projets/climate-finance-het/rel_repec/2026-10-01b/` on padme,
fingerprinted in `MANIFEST.sha256` there. The original Opus sample and its
call log stay under `rel_repec/2026-10-01/prefilter/`. The round-4 ReDIF
table that produced the delivery is `rel_repec/2026-10-01d/redif.parquet`,
sha256 `053080c1414305cf134dc3a0ae09abdb22c5ce47c1a5e6eaf390a93e1b22fe65`,
fingerprinted with its counts, recall and controls in `2026-10-01d/MANIFEST.sha256`.

**Not done (open).**

- The classifier is not registered as a labeller in `icf_screen`. That
  table's schema accepts labellers `llm` or `human` and stages `1`, `2` or
  `audit`, and a classifier score fits none of them cleanly.
- The pre-filter is not applied (MOE recommendation, pending author
  decision), and it was scored on a 10,000-row sample
  only.
- No full-mirror semantic pass was made. The mirror has 5.6 M rows, not the
  2 M first assumed, which is about 280–360 h at the measured CPU rate
  (derived). The GPU rate was not measured, because the GPU was busy and no
  GPU job was run. A bge-m3 rate of 100–200 texts/s on the A4000 is an
  unmeasured assumption; it would give 8–16 h for 5.6 M. Timing 5,000 RePEc
  texts on the GPU once it is free would settle it.
- Known parser limits, low impact and not fixed:
  - A wrapped abstract line that starts with a known attribute name (`Note:`,
    `Year:`) ends the abstract.
  - An indented attribute is read as continuation text.
  - The fuller-copy rule counts filled fields and ignores `Revision-Date`.

## Reproduce (padme)

```bash
W=~/data/projets/climate-finance-het/rel_repec/2026-10-01d   # round-4 table and delivery
uv run python scripts/catalog_rel_repec_redif.py --mirror /data/mirrors/RePEc \
    --output $W/redif.parquet --provenance $W/provenance.json \
    --rsync-log /data/mirrors/RePEc_refresh_2026-10-01.log --jobs 16      # ~4 min
uv run python scripts/catalog_rel_repec_search.py search --table $W/redif.parquet \
    --counts $W/redif.counts.json --controls $W/zero_hit_controls.csv \
    --output-dir data/rel_intake/t1810-repec-local/2026-10-01 --retrieved-at 2026-10-01 --jobs 16   # ~25 min
uv run python scripts/catalog_rel_repec_search.py recall --table $W/redif.parquet \
    --delivery data/rel_intake/t1810-repec-local/2026-10-01 \
    --toc-1650 data/rel_intake/t1650-sommaires/2026-09-30 --output $W/recall.json
P=~/data/projets/climate-finance-het/rel_repec/2026-10-01b/prefilter   # round-2 fit; pool built WITHOUT this delivery (see Delivery), icf_screen from `make rel-pool-data`
O=~/data/projets/climate-finance-het/rel_repec/2026-10-01/prefilter   # first fit: 10k sample, Opus sample
uv run python scripts/corpus_rel_repec_prefilter.py texts --pool data/rel_pool_without_1810/pool.csv \
    --screen data/rel_screen/icf_screen.csv --delivery data/rel_intake/t1810-repec-local/2026-10-01 \
    --recall-sentinels ~/data/projets/climate-finance-het/rel_repec/2026-10-01b/recall.sentinels.csv --output $P/texts.jsonl
uv run python scripts/corpus_rel_repec_prefilter.py embed --texts $P/texts.jsonl \
    --roles train,heldout,control,sentinel --threads 8 --output-dir $P/emb_train
uv run python scripts/corpus_rel_repec_prefilter.py embed --texts $P/texts.jsonl \
    --roles sentinel_repec --output-dir $P/emb_sentinel_repec
uv run python scripts/corpus_rel_repec_prefilter.py remap-embeddings \
    --embeddings $O/emb_repec_sample10k/embeddings.npz --old-texts $O/texts.jsonl \
    --texts $P/texts.jsonl --output $P/emb_repec_sample10k_remapped.npz
uv run python scripts/corpus_rel_repec_prefilter.py fit --texts $P/texts.jsonl --output-dir $P/fit \
    --embeddings $P/emb_train/embeddings.npz $P/emb_sentinel_repec/embeddings.npz \
    $P/emb_repec_sample10k_remapped.npz
uv run python scripts/corpus_rel_repec_prefilter.py opus-rescore --opus-sample $O/opus_sample.jsonl \
    --scores $P/fit/scores.csv --output $P/opus_rescore.json
```

The first fit drew its sample with `embed --roles repec --limit 10000` and its
Opus labels with `opus-sample --n-drop 120 --n-keep 80`, which spends on the
API. The training embeddings of record were computed from
`texts_train.jsonl`, a texts file built without the delivery that has the same
rows for these roles. Set `PYTHONPATH=scripts:libs/openalex-corpus/src`; the
pre-filter needs `uv run --group corpus --extra cpu` and
`CUDA_VISIBLE_DEVICES=""`.
