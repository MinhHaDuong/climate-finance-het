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
| `no_dedup_key` | title known, but no DOI, OpenAlex id, year or persistent URL (see `url` below) exists in the source |

Unlike the other reasons, `no_dedup_key` rows are **not** dropped from the pool.
They are listed here only because `records.csv` requires a deduplication key
they cannot carry. The pool merge (ticket 1731) takes them in as title-only
works, so the ICF rule still sees them and screens them on title. Their `title`
must be non-empty. A record with a persistent URL is not `no_dedup_key`: it
goes in `records.csv` with that URL in `url` (see below). A title-only row
joins the one pool work with the same normalized title, in any year; several
such works leave it apart (ambiguous), and a generic title (fewer than 4
words and 25 characters, or one of *introduction, editorial, preface,
foreword, book review(s), conclusion(s), index, erratum, corrigendum,
contents*) never joins: the row stays its own work.

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
| `url` | | the most persistent http(s) identifier available: a Handle URL (`https://hdl.handle.net/…` or the repository's `<host>/handle/…`), a DOI resolver URL; else the landing page |
| `affiliation_countries` | | `; `-separated ISO 3166-1 alpha-2 codes of author affiliations |
| `version_hint` | | `;`-separated pointers to other versions of the same work (DOI, OpenAlex id, or a `record_id` of the same lane), e.g. working paper → article |
| `lane_status` | | the lane's own disposition, information only (`candidate`, `already_in_pool`, `unresolved`, …) |
| `lane_note` | | free text |

At least one of `doi`, `openalex_id`, `year` or a persistent `url` must be
non-empty on every row: a record with none of them cannot be deduplicated.
Only three kinds of URL are persistent, and so keys:

- a DOI resolver URL naming a DOI (`https://doi.org/10.…`): read as that DOI;
- an OpenAlex work URL (`https://openalex.org/W…`): read as that id;
- a Handle: `hdl.handle.net/X` or `handle.net/X` is the Handle `X`, joined
  across repositories; a repository's `<host>/handle/X` keeps its host,
  because local prefixes (DSpace's default `123456789`) are reused, so the
  same `X` on two hosts can be two works.

URLs are canonicalised before comparison (query and fragment dropped, `http`
read as `https`, host lowercased without `www.`, trailing slash dropped).
A landing page, an issue page, a bare host, or a resolver URL that names no
id is no key: as a record's only identifier it fails the check, and such a
record goes to `excluded.csv` as `no_dedup_key`. A Handle join never fuses
two different DOIs or OpenAlex ids, and a URL never keeps records apart: only
a DOI or OpenAlex id disagreement vetoes a title + year join.

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

- `counts.records` is a JSON integer equal to the number of rows of `records.csv`;
  `counts.excluded` equals the per-reason counts of `excluded.csv`.
- `coverage` is `complete` or `incomplete`. `incomplete` lists what was not
  covered and why (`{"unit": "...", "reason": "..."}`): a paywall, a licence, a
  budget cap, a missing API. A limit is never reported as saturation.
- `needs_human` lists items that only the author can unblock
  (`{"item": "...", "reason": "..."}`); they do not block the delivery.

## What 1655 does with a delivery: the per-source merge report

The pool merge (ticket 1731, `make rel-pool`, `scripts/corpus_rel_pool.py`)
reads the pinned catalogue (`data/catalogs/unified_works_rel_pin.csv`, catalog_merge
run 20260729T161924Z, 43,179 works, fetched by hash with `make rel-pool-data`;
not the `unified_works.csv` that `dvc.lock` currently pins) and every delivery
no other supersedes, and writes `data/rel_pool/pool.csv`,
`data/rel_pool/merge_report.json` and a readable `merge_report.md`. For each
delivery, per source (a work two lanes found counts in both):

| field | meaning |
|---|---|
| `records` | rows in `records.csv` |
| `excluded` | per-reason counts from `excluded.csv` |
| `with_doi`, `doi_malformed`, `with_openalex_id`, `with_handle`, `title_year_only` | identifier coverage (DOIs are compared as strings, never resolved) |
| `title_only_from_excluded`, `title_only_joined` | `no_dedup_key` rows taken in as title-only works, and how many joined the one existing work with the same normalized title (several such works: ambiguous, kept separate, counted in the pool reconciliation as `ambiguous_title_only`; generic titles kept apart are counted as `generic_title_only`) |
| `dup_within_delivery` | rows (records and title-only rows) that land in the same pool work as another row of the same delivery |
| `in_catalogue` | matched to the catalogue (by DOI, OpenAlex id, Handle, then title + year, `by_title_only` when a `no_dedup_key` row joined on the catalogue row's title, or `via_other_lane` when only another lane's record bridges them; each count reported) |
| `in_other_lane_only` | not in the catalogue, matched to another delivery |
| `new_to_pool` | matched to nothing else: the lane's unique yield |
| `already_screened` | of the delivery's works, how many already carry an ICF label in `icf_screen` |

Then the pool totals after deduplication, the works per number of sources, and
the works still to screen. Records enter the ICF screen (ticket 1733) with the
same rule and prompts as every other record; nothing is admitted to REL by the
lane that found it.

The ICF labels live in `data/rel_screen/icf_screen.csv`, an append-only table
with its sidecar `icf_screen.manifest.jsonl` (byte length and sha256 after
each append). Both are tracked together by `data/rel_screen.dvc` (`dvc add`,
never a `dvc.yaml` out): the manifest only anchors the table to itself, so the
DVC hash committed to git is the real tamper anchor. Fetch the table before
writing (`make rel-pool-data`); the writers refuse to start a new table where
`data/rel_screen.dvc` tracks one, unless `--new-table` is given.
Stage-2 answers in the version-2 wrapper (ticket 1840) also append their discipline
fields (`contrib`, `field`, `contrib_type`) to `data/rel_screen/rel_dimensions.csv`, a
second append-only table with its own manifest, same key and same DVC pointer.
`make rel-screen-import-1530` appends the ticket 1530 labels (idempotent), and
`make rel-view` regenerates `data/rel_pool/rel_view.csv` and `rel_counts.json`
from the pool and the table. Paths, the 1530 archive, the stage-2 chunking and
the audit sample are set in `config/rel_screen.yaml`, with the screen rule
(which stage-1 labels leave, whether works still unsure after stage 2 stay in
REL flagged) that the view applies and records in `rel_counts.json`. The view
counts REL in works and in work families: works linked by `version_hint` count
once, represented by an included member, a published article first.

Each pool work also gets a venue seriousness tier and registry flags (ticket
1841). `make rel-venue-registries` pulls the four hard registries
(Kanalregisteret level X, Scopus discontinued, DOAJ withdrawals, the hijacked
journal checker) into a read-only dated directory under
`~/data/projets/climate-finance-het/rel_venue_registries/` with
`MANIFEST.sha256`, recorded in `config/rel_venue_registry_pulls.csv`.
`make rel-venue-enrich` extends the OpenAlex venue cache
`data/rel_venues/openalex_work_venues.csv`, tracked by `data/rel_venues.dvc`
like the screen table (a paid, dated API snapshot, fetched by
`make rel-pool-data`); it stops before the day's budget would fall below
0.2 USD. `make rel-venues` writes `rel_venues.csv` (per venue),
`rel_work_venues.csv` (per work) and `rel_venue_counts.{json,md}` into
`data/rel_pool/`, deterministically, from the pool, the cache, the configured
pull and `config/rel_venue_tiers.yaml` (the versioned B list). Ticket 1843
joins the work table through `_rel_venues.load_work_venues`; the per-work
`flags` cell (`registry:entry_id[match]`) already applies the per-work rules
below, so the venue table is for explanation only.

- Tiers: A, B, C and `unknown`. `unknown` is a work with no resolvable venue;
  it is never folded into C (C means a venue known and not serious). A work
  in `unknown` or C whose own URL is on a B institution's site
  (`b_domains`) is B with rule `b_domain`.
- Kanalregisteret level X is per year and provisional (in the 2026-10-01 pull
  every X is in `Nivå 2026`). A work is flagged only when the journal's level
  for the work's publication year is X; a year with no level takes the
  journal's nearest year with one (the earlier on a tie); an undated work is
  not flagged. The venue row keeps every yearly level in `flag_details`.
- The hijacked check reads every URL of a work: the landing page of each of
  its OpenAlex rows (with or without a source) and the URL of each intake
  record. Only 32% of pool works have a URL on a host other than doi.org, so
  a zero hijacked count is a lower bound, not an absence.
- The Scopus flag is broader than "discontinued for publication concerns":
  Elsevier's list gives no per-title cause, so it also holds titles dropped
  for low metrics. DOAJ withdrawals are mostly the 2014-2016 "best practice"
  purge. Both are flags, not evidence of malpractice.

Three author decisions are pending switches: (a) which registries exclude
(`exclusion` in `config/rel_venue_registries.yaml`; a title match never
excludes), (b) whether the NGO research series are tier B
(`ngo_research_in_b`), (c) whether `unknown` works are kept, flagged, or
excluded (`no_venue` in `config/rel_venue_tiers.yaml`, applied by the loader's
`no_venue` argument). Every flag, both NGO tiers and the `unknown` state are
written whatever the settings, so a sensitivity table can recompute any other.
