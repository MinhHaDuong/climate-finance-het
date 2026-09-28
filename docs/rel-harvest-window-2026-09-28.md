# REL collection window: 2025–2026 backfill

Run date: 2026-09-28 UTC. The publication-year backfill is bounded to
2025–2026; the cumulative pool still contains earlier research. The final
REL review treats 2025 as the last complete publication year and 2026 as
partial, through the search date in `config/rel_review.yaml`.

## Query register

| Route | Query source | Publication rule | Execution |
| --- | --- | --- | --- |
| OpenAlex | `config/openalex_queries.yaml`, all four tiers | `publication_year` 2025–2026; full pagination, existing ID deduplication; no `from_created_date` floor | `catalog_openalex.py --resume --full-scan --year-min 2025` |
| ISTEX | `config/corpus_collect.yaml`, `queries.istex` | `publicationDate` 1990–2026 | `catalog_istex.py --api` |
| Scopus | `config/corpus_collect.yaml`, `queries.scopus` | `PUBYEAR AFT 1989 AND PUBYEAR BEF 2027` | `catalog_scopus.py` |
| World Bank | `config/corpus_collect.yaml`, `queries.worldbank`; `config/grey_sources.yaml` | `dc.date.issued` 1990–2026, with client-side year check | `catalog_grey.py` |

The OpenAlex backfill uses `data/pool/openalex/_backfill_2025_2026.json`.
It does not advance the normal all-years `_query_dates.json`. An interrupted
query remains unfinished and is replayed; completed backfill queries are
skipped on restart. The source logs and the interrupted first attempt are held
on padme under `/tmp/rel-harvest-2026-09-28/`. The completed source run used
commit `b13baeed653b21899839b6d2f58bb681cb921edb`, from 15:15:37 to
15:19:28 UTC. An initial all-years request was stopped to preserve the daily
API allowance; eight completed 2025–2026 queries were retained in the separate
backfill checkpoint. The later run completed the remaining queries.

The analytic selector `classify_rel_review_works()` reports a disposition for
every refined work. It excludes years beyond 2026 and dates after the search,
and quarantines 2026 records with only a year or an unusable date. Exact
publication dates retained from OpenAlex, ISTEX, Scopus, and World Bank can
release a 2026 record from quarantine. Topical, institutional-document, and
working-paper/article-version screening are subsequent REL review decisions;
this dated window alone does not certify literature-review eligibility.

## Execution results

| Route | Result on 2026-09-28 | 2025 / 2026 in source CSV |
| --- | --- | --- |
| OpenAlex | All 52 query terms completed; zero incomplete. 56,478 distinct IDs after pool deduplication; 1,389,713 outgoing citation links. API allowance after run: $0.812. | 9,916 / 8,801 |
| ISTEX | API returned four records; cumulative pool extraction yielded 754 works, all dated through 2024. | 0 / 0 |
| Scopus | The collector found no API key on padme or doudou; no Scopus query ran. | unavailable |
| World Bank | Three queries returned 342 distinct items; with the curated seed list, the CSV contains 354 works. No query hit the 500-item safety cap. | 45 / 28 |

In the OpenAlex 2026 source records, 8,786 have an exact publication date;
three of those dates are later than 2026-09-28 and 15 records lack an exact
date. The REL selector excludes the former and quarantines the latter. The
28 World Bank 2026 records have exact dates no later than the search date.

The offline source merge produced 58,333 unified works: 9,966 dated 2025,
8,814 dated 2026, and one pre-existing future-dated 2027 record. These are
discovery counts before topic, document-type, version, and quality screening.
The previously published refined corpus has not yet been rebuilt from this
expanded pool; its 2025–2026 counts cannot stand in for the final REL review.
The unavailable Scopus route, EconLit working-paper searches, DAG-edge
searches, journal contents checks, and working-paper/article reconciliation
remain to be recorded in the corpus-finalization audit before the article
claims comprehensive retrieval.
