# REL intake contract: how a search lane delivers records to the pool

Ticket 1730, child of 1655. Applies to every lane that feeds the REL pool:
1530 (South, OpenAlex), 1650 (tables of contents of the 61 journals),
1651 (Gavard–Schoch), 1652 (EconLit and causal families), 1653 (Southern
sources outside OpenAlex) and 1654 (citation chaining). Check a delivery with

```bash
uv run python scripts/qa_rel_intake.py data/rel_intake/<lane>/<delivery>
```

before opening the lane's PR. Exit 0 means the delivery meets this contract;
any other exit lists every violation.

## The one rule

**A lane delivers everything it retrieved, unscreened for relevance.** The ICF
rule is applied once, by 1655, to the whole pool (protocol
`conception/rel-audit-finalisation-corpus.md`, § Criblage ICF du pool). A lane
does not drop a record because it looks off-topic, because it is already in the
corpus, or because it falls outside the publication window: the pool merge
counts overlap per source (that is each lane's marginal yield), and the REL view
applies the window. A lane may still record its own opinion in `lane_status`
and `lane_note`; those columns are carried as information and never filter.

The only records a lane may leave out are listed, with a reason from this
closed list, in `excluded.csv`:

| reason | meaning |
|---|---|
| `duplicate_in_lane` | the same item retrieved twice by this lane (keep one row in `records.csv`, list the others) |
| `front_matter` | not an item at all: issue cover, editorial board, table of contents page, index, erratum notice |
| `not_retrievable` | the lane saw a reference to the item but could not obtain title-level metadata |

Book reviews, editorials with content, and institutional reports are **not**
front matter: deliver them, the screen's document-type label handles them.

## Location

```
data/rel_intake/<lane>/<delivery>/
    records.csv      required
    registry.csv     required
    excluded.csv     required (header only when nothing was left out)
    manifest.json    required
```

- `<lane>` is `t<ticket>-<slug>`, e.g. `t1650-sommaires`, `t1653-scielo`.
  A lane with several sources may use one lane directory per source.
- `<delivery>` is the delivery date, `YYYY-MM-DD`, with a suffix for a second
  delivery the same day (`2026-10-02b`). A delivery is **immutable** once its PR
  merges: corrections come as a new delivery that says what it supersedes
  (`manifest.json` → `supersedes`).
- The lane directory is tracked by DVC, never by git:
  `dvc add data/rel_intake/<lane>` then `dvc push` (remote `padme`). Commit the
  `data/rel_intake/<lane>.dvc` pointer (and the `.gitignore` DVC writes) in the
  lane's PR. Small registries or notes that humans review may also be copied
  under `docs/` or the lane's conception file; the DVC copy is the one the pool
  reads.

## `records.csv`

UTF-8 (a leading byte-order mark, as Excel writes, is tolerated), comma-separated,
RFC 4180 quoting, one header row. **Every column below
must be present in the header**, in any order; extra columns are allowed and
carried. Required columns must be non-empty on every row; the others may be
empty.

| column | required | content |
|---|---|---|
| `record_id` | yes | unique within the delivery, stable across re-deliveries of the same item |
| `query_id` | yes | the `registry.csv` row that retrieved it (a TOC unit, a query, a reference list) |
| `platform` | yes | where the metadata came from: `openalex`, `crossref`, `econlit`, `scielo`, `redalyc`, `ajol`, `publisher_toc`, `repository`, `manual`, … |
| `retrieved_at` | yes | ISO 8601 date or datetime of retrieval |
| `title` | yes | title as published |
| `platform_record_id` | | the platform's native id (Crossref DOI, EconLit accession number, SciELO pid) |
| `doi` | | bare DOI, `10.xxxx/...`, no `https://doi.org/` prefix |
| `openalex_id` | | `W` + digits, no URL prefix |
| `title_original` | | original-language title when `title` is a translation |
| `first_author` | | |
| `all_authors` | | `; `-separated |
| `year` | | four-digit publication year |
| `publication_date` | | ISO date if known |
| `journal` | | container title (journal, series, repository) |
| `issn` | | `; `-separated ISSNs |
| `doc_type` | | as the platform states it (`article`, `working-paper`, `book-chapter`, …) |
| `language` | | ISO 639-1 code of the full text if known |
| `abstract` | | as retrieved; empty is allowed and expected for some sources |
| `abstract_provenance` | | where the abstract came from when not `platform` |
| `url` | | landing page |
| `affiliation_countries` | | `; `-separated ISO 3166-1 alpha-2 codes of author affiliations |
| `version_hint` | | the lane's pointer to another version of the same work (DOI or `record_id`), e.g. working paper → article |
| `lane_status` | | the lane's own disposition, information only (`candidate`, `already_in_pool`, `unresolved`, …) |
| `lane_note` | | free text |

At least one of `doi`, `openalex_id` or `year` must be non-empty on every row:
a record with none of them cannot be deduplicated (the merge falls back on
normalized title + year).

## `registry.csv`

One row per search unit (a query string, a journal-year TOC, a reference list),
PRISMA-S style. Required columns: `query_id` (unique), `platform`, `query` (the
exact string, or the TOC unit such as `ISSN 1234-5678 vol 12 issue 3`),
`run_at`, `n_received`, `completed` (`true`/`false`). Recommended:
`filter`, `n_expected`, `stop_reason` (required non-empty when `completed` is
`false`). Extra columns (stratum, language, theme, …) are carried. Every
`query_id` cited in `records.csv` and `excluded.csv` must be in the registry.

## `excluded.csv`

Columns `record_id`, `query_id`, `reason`, `title`, `note`. `reason` from the
closed list above.

## `manifest.json`

```json
{
  "lane": "t1650-sommaires",
  "ticket": "1650",
  "delivery": "2026-10-02",
  "delivered_at": "2026-10-02T14:00:00Z",
  "producer": {"script": "scripts/…", "commit": "<git sha>", "machine": "padme"},
  "counts": {"records": 1234, "excluded": {"duplicate_in_lane": 3, "front_matter": 40}},
  "coverage": "complete",
  "incomplete": [],
  "needs_human": [],
  "supersedes": null,
  "notes": ""
}
```

- `counts.records` equals the number of rows of `records.csv`;
  `counts.excluded` equals the per-reason counts of `excluded.csv`.
- `coverage` is `complete` or `incomplete`. `incomplete` lists what was not
  covered and why (`{"unit": "...", "reason": "..."}`): a paywall, a licence, a
  budget cap, a missing API. A limit is never reported as saturation.
- `needs_human` lists items that only the author can unblock
  (`{"item": "...", "reason": "..."}`); they do not block the delivery.

## What 1655 does with a delivery: the per-source merge report

The pool merge (ticket 1731) reads the pinned `data/catalogs/unified_works.csv`
and every delivery, and writes `data/rel_pool/merge_report.json` plus a
readable table. For each delivery, **before cross-source deduplication**:

| field | meaning |
|---|---|
| `records` | rows in `records.csv` |
| `excluded` | per-reason counts from `excluded.csv` |
| `with_doi`, `with_openalex_id`, `title_year_only` | identifier coverage |
| `dup_within_delivery` | rows that collapse onto another row of the same delivery |
| `in_catalogue` | matched to `unified_works` (by DOI, OpenAlex id, then title + year; each count reported) |
| `in_other_lane_only` | not in the catalogue, matched to another delivery |
| `new_to_pool` | matched to nothing else: the lane's unique yield |
| `already_screened` | of the delivery's works, how many already carry an ICF label in `icf_screen` |

Then the pool totals after deduplication, the works per number of sources, and
the works still to screen. Records enter the ICF screen (ticket 1733) with the
same rule and prompts as every other record; nothing is admitted to REL by the
lane that found it.
