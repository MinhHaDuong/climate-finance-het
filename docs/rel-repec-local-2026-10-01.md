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

PREFILTER

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
```

`PYTHONPATH=scripts:libs/openalex-corpus/src`; the pre-filter needs
`uv run --group corpus --extra cpu` and `CUDA_VISIBLE_DEVICES=""`.
