# REL lane over the local RePEc mirror (ReDIF)

Ticket 1810, child of 0700; harvest lane, step 1 of the protocol
`conception/rel-audit-finalisation-corpus.md`. Run on padme, 2026-10-01.
Delivery: `data/rel_intake/t1810-repec-local/2026-10-01/` (DVC), checked by
`scripts/qa_rel_intake.py` (exit 0).

## Mirror and table

The mirror is the `RePEc-ReDIF` module of `rsync://rsync.repec.org/`, at
`/data/mirrors/RePEc/` on padme. It was refreshed on 2026-10-01 (started
00:04 CEST; log `/data/mirrors/RePEc_refresh_2026-10-01.log`; files replaced
or removed by the refresh are kept in `/data/mirrors/RePEc_replaced_2026-10-01/`,
403,356 files). Itemized counts read from the log by
`scripts/catalog_rel_repec_redif.py --rsync-log`: 86,275 new files, 344,437
updated files (79,680 size and time, 264,704 time only, mostly `index.html`),
58,919 deleted files and 198 deleted directories, 1,084 new directories.
Caveat: rsync ran without `--stats`, so the log has no summary line and the
remote exit code was not captured. Completion rests on two observations: no
rsync process remained, and the log runs through the last archive (`zur/`)
with no error line.

`scripts/catalog_rel_repec_redif.py` (parser `scripts/_redif.py`) walks the
mirror and keeps every file whose first 64 KB open a ReDIF template. The
mirror stores ReDIF under `.rdf`, `.redif`, `.RDF`, `.txt` and no extension,
next to PDFs and HTML. A value runs on until the next line that opens a known
ReDIF attribute, so `Purpose:` or `https://` at the start of an abstract line
stays in the abstract. Files that are not UTF-8 are read as cp1252, and the
row records the encoding. Table: `~/data/projets/climate-finance-het/rel_repec/2026-10-01/redif.parquet`
on padme, with `redif.counts.json` and `redif.duplicates.csv` next to it.

| | count |
|---|---:|
| files seen (PDF, images and archives skipped by extension) | 2,093,590 |
| files holding ReDIF | 2,051,375 |
| of which read as cp1252 | 109,156 |
| ReDIF-Article templates | 4,638,624 |
| ReDIF-Paper templates | 1,414,412 |
| ReDIF-Chapter templates | 339,190 |
| ReDIF-Book templates | 77,605 |
| work templates without a handle (not kept) | 1,299 |
| handle repeated in another file (fuller copy kept) | 860,765 |
| **rows (one per RePEc handle)** | **5,607,795** |
| articles / papers / chapters / books | 3,848,034 / 1,355,716 / 334,645 / 69,400 |

Elsevier (`eee/`) accounts for 757,005 of the repeated handles, because its
per-journal files overlap. When copies of a handle differ, the table keeps
the one with the most non-empty fields.

## Queries

`config/rel_repec_search.yaml` adds no new vocabulary. It replays strings that
other lanes already declared:

- **1652 causal-map matrix** (`config/rel_causal_search.yaml`): every family
  and theme string (IM, IO, SY, CS, TH; en, fr, es). The SI rows cite tuning
  sentinels in OpenAlex; the mirror has no citation index, so they are
  replayed as title searches of those tuning sentinels, as the EconLit twin of
  1652 did. Also the per-family JEL rows that 1652 sent to EconLit (the
  family's JEL codes AND its mediator group).
- **1530 ICF terms of the protocol** (`config/rel_sud_search.yaml`): themes
  T1 to T4 in all ten languages, plus the global gap-fill string.
- **A declared JEL filter**, fixed before the run: `(Q54 or Q56) and (F35 or O19)`,
  `Q54 and (F2 or F3)`, `F35 and (Q4 or Q5)`.

Local matching replaces OpenAlex `title_and_abstract.search`
(`scripts/_rel_local_query.py`). It searches title, abstract and keywords,
folded for case and accents, with each phrase matched on word boundaries and
its last word also matched with a plural "s". It applies no year and no
language filter. OpenAlex stems words and this matcher does not; that is the
one known divergence.

| source | units | hits (sum over units) |
|---|---:|---:|
| 1652 text strings (RC) | 132 | 14,815 |
| 1652 JEL rows (RE) | 22 | 76,049 |
| 1530 T1–T4 and gap-fill (SUD) | 41 | 17,962 |
| declared JEL filter | 3 | 631 (195 / 321 / 115) |

Twenty-six units retrieved nothing. Each has a positive control in
`zero_hit_controls.csv` (next to the table): the hit count of each of its AND
groups taken alone, and the number of table titles written in the unit's
script. Two patterns cover them. In the French and Spanish 1652 strings, both
groups match records but never the same record: for `RP-RC-grid-IM-fr`, 439
records hit the ICF group and 6,122 the mediator group. In the Arabic and
Hindi T1, T2 and T4 strings, the table holds 1,732 Arabic-script and 1,231
Devanagari titles but no ICF phrase. The table holds no Bengali title. The
three SI title searches with zero hits name tuning sentinels that are not in
RePEc.

## Delivery

| | count |
|---|---:|
| records (`records.csv`) | 79,543 |
| excluded `no_dedup_key` (no DOI, no year; title-only in the pool) | 915 |
| excluded `not_retrievable` (template without a title) | 2 |
| records with a DOI | 19,769 |
| records with an abstract | 98.1 % |

`record_id` is the RePEc handle. A RePEc handle is not a CNRI Handle, and the
contract counts an EconPapers or IDEAS page as a landing page, not a key, so
`url` carries the DOI resolver when the record has a DOI and the EconPapers
handle page otherwise. A record with neither a DOI nor a year cannot be keyed
and goes to `no_dedup_key`. The extra column `query_ids` lists every unit
that retrieved the record.

Volume comes from the 1652 JEL rows. 63,376 records (80 %) are retrieved only
by them, because codes such as `F35 or O4 or Q43` combined with a mediator
group like "emissions" or "GDP" are broad. The text strings and the declared
JEL filter account for the other 16,167.

Pool merge (`make rel-pool` on padme with this delivery; not committed):
77,508 pool works, of which 2,905 are in the catalogue, 9,555 are in another
lane only, and 65,048 are new to the pool. 2,950 rows fall into the same
work as another row of the delivery, usually a working paper and its article
sharing a DOI.

## Recall

Sentinels, computed by `catalog_rel_repec_search.py recall`, with output in
`recall.json` and `recall.sentinels.csv` next to the table. "In mirror" means
that a DOI or normalised title match exists in the table, which shows the
parser sees the record. Reserve (hold-out) sentinels are reported apart and
were never used to change a query.

| sentinel file | set | n | in mirror | retrieved |
|---|---|---:|---:|---:|
| `rel_causal_sentinels.csv` (1652) | tuning and other | 18 | 12 | 12 |
| `rel_causal_sentinels.csv` (1652) | **reserve** | 31 | 19 | **16** |
| `rel_sud_sentinels.csv` (1530) | tuning, retention, other | 41 | 9 | 9 |
| `rel_sud_sentinels.csv` (1530) | **reserve** | 14 | 1 | **1** |

The three reserve sentinels in the mirror that the lane missed are query
limits, not parser limits:

- C02, "Higher cost of finance exacerbates a climate investment trap in
  developing economies", carries no ICF or aid term.
- C09, "Debt-for-climate swaps for small islands", has the SY phrase but none
  of its debt-outcome terms.
- C33, "The effect of aid on growth", has no emissions term, and its JEL codes
  are O1 and O4, without F35.

RePEc holds few of the southern sentinels (10 of 55): the strength of this
lane is economics indexed by JEL, not the South.

American Economic Review 1990–1998: 1650 delivered 990 items of these years
from OpenAlex only, without a DOI. The mirror holds AER in those years
(160–194 records a year, series `RePEc:aea:aecrev`), and 910 of the 990
(92 %) match a mirror record on normalised title and year ±1. 187 of the 910
have an abstract in RePEc, but none of those 187 was an item without an
abstract in 1650, so the mirror adds no abstract there. The 80 misses are
mostly titles that OpenAlex truncates ("Agency costs, net worth, and business
fluctuations: A"). RePEc has no DOI for these years either, so the mirror
confirms 1650's items but resolves none of them to a DOI.

## What this lane adds

- **To 1652 (RePEc through bibCNRS EDS).** 1652 received 2,231 RePEc records
  from EDS, capped at 500 per query. This lane finds 1,989 of them (89 %), and
  its 77,508 works include 5,907 that share a pool work with 1652. The local
  replay has no cap and can be rerun. Most of its extra volume comes from the
  1652 JEL rows, which EDS could not apply as EconLit does.
- **To 1650 (tables of contents).** 5,869 works shared with 1650. For AER
  1990–1998, see above.
- **To the pool.** 65,048 works new to the pool, unscreened as the contract
  requires. The pre-filter below estimates how many of them are surely off
  topic.

## Recall pre-filter (step 5)

`scripts/corpus_rel_repec_prefilter.py` is the classifier the author asked for
on 2026-09-30: bge-m3 embeddings (`title + ". " + abstract[:2000]`, 256 tokens,
CPU) fed to a logistic regression that predicts the Opus label "out" (*hors
sujet*). It only ever drops records: everything it keeps goes through stage 1
and then stage 2 under the protocol's rule. Opus stage 2 is on hold, pending
the router results.

**Training.** 5,278 works: 4,631 Opus stage-2 labels from `icf_screen`
(1530), plus the Jev-pilot labels exported to `config/rel_prefilter_labels.csv`
by `scripts/corpus_rel_prefilter_labels.py`. Those are 399 Opus labels from
the stratified random sample and the 248 `tune` rows of the adjudicated
reference set. Label counts: icf 2,557, aux 2,058, out 482, unsure 181. No
work used for validation is trained on.

**Threshold.** A record is dropped when `p_out > 0.96728`. That value is the
largest out-of-fold score of any ICF-labelled training work (5-fold) or tuning
sentinel. Nothing scoring at or below a known ICF work is dropped. One work
sets it: a French title-only CDM paper, "Le Polycentrisme : un concept
heuristique pour l'analyse d'instruments de marché tel que le Mécanisme de
Développement Propre". The next highest ICF score is 0.92. Reserve sentinels
and the validation sets were measured after the threshold was fixed and never
moved it.

| validation set | n | dropped | ICF lost | share of "out" dropped |
|---|---:|---:|---:|---:|
| training, out of fold | 5,278 | 42 (34 out, 5 aux, 3 unsure) | 0 | 7 % |
| Jev-pilot control (Opus, 200; 197 in pool) | 197 | 15 (14 out, 1 aux) | 0 | 13 % |
| Jev-pilot reference, held out (adjudicated) | 244 | 5 (5 out) | 0 | 10 %; weighted share dropped 3.4 % |
| sentinels, pool text: tuning / reserve / other | 24 / 45 / 35 | 0 / **0** / 0 | 0 | max `p_out` 0.957 / 0.840 / 0.836 |
| sentinels, the lane's RePEc record: non-reserve / reserve | 22 / 21 | 0 / **0** | 0 | max `p_out` 0.952 / 0.735 |

**On this lane.** The CPU embedding throughput, measured on padme while other
jobs ran (load 15 to 18), was 4.3 to 5.6 texts a second at 16 to 20 threads,
and 5.4 a second with four processes of five threads. At that rate the
80,458 delivered rows (records and `no_dedup_key`) would take 4.0 to 5.2
hours, over the three-hour CPU budget. The pre-filter was therefore applied to
a simple random sample of 10,000 delivered rows (seed 1810, 39 min). It drops
402 of them, **4.0 %**. Extrapolated (derived, not run), that is about 3,200
of the 80,458 rows. The sweep shows the cost of the zero-loss rule:

| threshold | training ICF lost (OOF) | reserve sentinels lost (pool / lane record) | share of the RePEc sample dropped |
|---|---:|---:|---:|
| 0.80 | 7 | 1 / 0 | 45.6 % |
| 0.90 | 2 | 0 / 0 | 23.6 % |
| 0.95 | 1 | 0 / 0 | 8.8 % |
| **0.967 (rule)** | **0** | **0 / 0** | **4.0 %** |
| 0.98 | 0 | 0 / 0 | 1.5 % |

**Fresh Opus sample against distribution shift.** 200 records of the 10,000
sample, stratified by the decision: 120 of the 402 dropped and 80 of the
9,598 kept. Opus 5.5 through OpenRouter used the stage-1 rule of
`config/rel_sud_screen.yaml` with the strict stage-2 wording of the Jev
pilot, in chunks of 40.

| stratum | n | out | aux | icf | ICF rate, 95 % upper bound |
|---|---:|---:|---:|---:|---:|
| dropped | 120 | 119 | 1 | **0** | 2.5 % (rule of three) |
| kept | 80 | 47 | 30 | 3 | 10.6 % (Clopper–Pearson) |

The pre-filter's errors on RePEc records point the safe way: what it drops is
almost all *hors sujet*. The kept stratum still holds ICF works at about 4 %
(3 of 80). If that rate held across the delivery it would mean roughly 2,900
ICF works among the kept rows, with a wide interval; this is a derived figure,
not a count. Spend: USD 0.32, summed from the per-call `usage.cost`
(`opus_sample.jsonl.calls.jsonl`). Before the run the OpenRouter account
showed USD 120.80 used of USD 140. A reading taken one minute after the run
had not yet moved, so it cannot confirm the spend.

**How this differs from the v2 filter.** The refined-corpus v2 filter scored
every work against a fixed query ("climate policy and financial mechanisms")
with a reranker. It cut at a threshold chosen for the corpus as a whole, and
122 of the 489 works it had dropped (and the Sud search found again) were ICF
on rereading. This pre-filter is fitted to the review's own ICF labels and
predicts "out" rather than relevance. Its threshold is the largest one that
loses no known ICF work, so it gives up volume (4 % dropped here) to keep
recall. It is a pre-filter only: it never admits a record, and stage 1 and
stage 2 still read everything it keeps.

**Frozen.** The script is `scripts/corpus_rel_repec_prefilter.py` and the label
register is `config/rel_prefilter_labels.csv`. The model is `prefilter/fit/model.npz`,
sha256 `3aae84dbd31b62adad12934447f93acdb1954b51ffeaef635ce47cde39556385`,
with its threshold inside. It sits with `report.json`, `scores.csv`, the
texts, the embeddings and the Opus sample under
`~/data/projets/climate-finance-het/rel_repec/2026-10-01/` on padme,
fingerprinted in `MANIFEST.sha256` there. The ReDIF table is `redif.parquet`,
sha256 `95dedff34c2f4e4c9404a6e0dc29e647eaaf441e9af17b55ef6a28a7200e1bfa`.

**Not done (open).**

- The pre-filter is not registered as a labeller in `icf_screen`. That
  table's schema accepts labellers `llm` or `human` and stages `1`, `2` or
  `audit`. A classifier score and threshold fit none of them cleanly, and the
  author asked for no extra labels.
- The pre-filter has run on a 10,000-row sample, not on all 80,458 rows. A
  full pass needs about 4–5 h of CPU or a GPU slot.
- Full-mirror semantic pass: the mirror has 5.6 M rows, not the 2 M first
  assumed. At the measured CPU rate that is about 280–360 h (derived). The GPU
  rate was not measured, because the GPU was busy (no GPU job was run). A
  bge-m3 rate of 100–200 texts/s on the A4000 is an unmeasured assumption, and
  it would give 8–16 h for 5.6 M or 3–6 h for 2 M. The experiment that
  settles it: time 5,000 RePEc texts on the GPU once it is free.

## Reproduce (padme)

```bash
W=~/data/projets/climate-finance-het/rel_repec/2026-10-01
uv run python scripts/catalog_rel_repec_redif.py --mirror /data/mirrors/RePEc \
    --output $W/redif.parquet --provenance $W/provenance.json \
    --rsync-log /data/mirrors/RePEc_refresh_2026-10-01.log --jobs 16      # ~3 min
uv run python scripts/catalog_rel_repec_search.py search --table $W/redif.parquet \
    --counts $W/redif.counts.json --controls $W/zero_hit_controls.csv \
    --output-dir data/rel_intake/t1810-repec-local/2026-10-01 --retrieved-at 2026-10-01 --jobs 16   # ~22 min
uv run python scripts/catalog_rel_repec_search.py recall --table $W/redif.parquet \
    --delivery data/rel_intake/t1810-repec-local/2026-10-01 \
    --toc-1650 data/rel_intake/t1650-sommaires/2026-09-30 --output $W/recall.json
P=$W/prefilter   # pool from `make rel-pool` WITHOUT this delivery, icf_screen from `make rel-pool-data`
uv run python scripts/corpus_rel_repec_prefilter.py texts --pool data/rel_pool/pool.csv \
    --screen data/rel_screen/icf_screen.csv --delivery data/rel_intake/t1810-repec-local/2026-10-01 \
    --recall-sentinels $W/recall.sentinels.csv --output $P/texts.jsonl
uv run python scripts/corpus_rel_repec_prefilter.py embed --texts $P/texts.jsonl \
    --roles train,heldout,control,sentinel --threads 16 --output-dir $P/emb_train
uv run python scripts/corpus_rel_repec_prefilter.py embed --texts $P/texts.jsonl \
    --roles sentinel_repec --output-dir $P/emb_sentinel_repec
uv run python scripts/corpus_rel_repec_prefilter.py embed --texts $P/texts.jsonl \
    --roles repec --limit 10000 --threads 20 --output-dir $P/emb_repec_sample10k
uv run python scripts/corpus_rel_repec_prefilter.py fit --texts $P/texts.jsonl --output-dir $P/fit \
    --embeddings $P/emb_train/embeddings.npz $P/emb_sentinel_repec/embeddings.npz \
    $P/emb_repec_sample10k/embeddings.npz
uv run python scripts/corpus_rel_repec_prefilter.py opus-sample --scores $P/fit/scores.csv \
    --texts $P/texts.jsonl --n-drop 120 --n-keep 80 --output $P/opus_sample.jsonl   # API spend
```

The training embeddings of record were computed from a texts file without the
delivery (`texts_train.jsonl`, same rows for these roles).

`PYTHONPATH=scripts:libs/openalex-corpus/src`; the pre-filter needs
`uv run --group corpus --extra cpu` and `CUDA_VISIBLE_DEVICES=""`.
