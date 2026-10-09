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
rule is applied to the whole baseline pool by 1655, then incrementally to
citation-chaining additions by 1654 using the same screening procedures (protocol
`conception/rel-audit-finalisation-corpus.md`, § Criblage ICF du pool). A lane
does not drop a record because it looks off-topic, because it is already in the
corpus, or because it falls outside the publication window: the pool merge
counts overlap per source (that is each lane's marginal yield), and the REL view
applies the window. A lane may still record its own opinion in `lane_status`
and `lane_note`; those columns are carried as information and never filter.
Ticket 1654 owns delivery, pool merge, screening and reconciliation of its
additions before measuring each round's eligible yield; closing the baseline
tracker 1655 does not exempt those additions from screening.

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

One further column is **optional** (it may be absent from the header; the
check validates it when present): `repec_handle`, a RePEc handle
`RePEc:<archive>:<series>:<item>` that the lane has verified against the RePEc
mirror (ticket 2040). It is an identifier of the work, kept apart from
`platform_record_id`, and is not yet a deduplication key: the pool merge does
not join on it.

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
The discipline catch-up (ticket 1842, `scripts/corpus_rel_discipline_catchup.py`)
writes the same fields there for works stage 2 labelled before version 2, under
stage `catchup`, which `icf_screen` refuses.
`make rel-screen-import-1530` appends the ticket 1530 labels (idempotent), and
`make rel-view` regenerates `data/rel_pool/rel_view.csv` and `rel_counts.json`
from the pool and the table. Paths, the 1530 archive, the stage-2 chunking and
the audit sample are set in `config/rel_screen.yaml`, with the screen rule
(which stage-1 labels leave, whether works still unsure after stage 2 stay in
REL flagged) that the view applies and records in `rel_counts.json`. Works no
local Qwen run takes get stage 1 by design B (author decision of 2026-10-01,
`scripts/corpus_icf_stage1_designb.py`, imported with `corpus_icf_import.py
stage1-designb`): two stage-1 rows per work, Gemma 4 and the Jev D1
classifier, and the work leaves only when both say `out` with Jev's P(out) at
least 0.90 (`stage1_joint` in `config/rel_screen.yaml`). Both rows carry
`labeller=llm`, the served model id, `machine=openrouter/<provider>` and the
same `run_id`; the Jev row's `why` starts with `p_out=<P(out)>` at full
precision. The view shows such a decision in its `stage1_joint` column
(`llm=…;classifier=…;p_out=…`) and tallies the design-B works, their
`stage1_out` and their `pending_stage2` under `stage1_joint` in
`rel_counts.json`. Precedence, recall first: a work carrying several stage-1
verdicts (Qwen rows, design-B pairs, in any order) leaves at stage 1 only
when every verdict is `out`; one verdict that sends it to stage 2 is enough.
The view
counts REL in works and in work families: works linked by `version_hint` count
once, represented by the member attaining the family's maximum membership
(ticket 1843), a published article first on ties.

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
  (`b_domains`; `=host` for one host only) is B with rule `b_domain`, unless
  that URL is a non-research page (blog post, speech, homepage, library
  guide, news issue, media compilation: the `nonresearch` list), which makes
  it C with rule `nonresearch`; `tier_without_nonresearch` keeps the tier
  the list would not have changed.
- Kanalregisteret level X is per year and provisional (in the 2026-10-01 pull
  every X is in `Nivå 2026`). A work is flagged only when the journal's level
  for the work's publication year is X; a year with no level takes the
  journal's nearest year with one (the earlier on a tie); a year after the
  register's last column, or an undated work, is not flagged. The venue row keeps every yearly level in `flag_details`.
- The hijacked check reads every URL of a work: the landing page of each of
  its OpenAlex rows (with or without a source) and the URL of each intake
  record. Only 32% of pool works have a URL on a host other than doi.org, so
  a zero hijacked count is a lower bound, not an absence.
- The Scopus flag is broader than "discontinued for publication concerns":
  Elsevier's list gives no per-title cause, so it also holds titles dropped
  for low metrics. DOAJ withdrawals are mostly the 2014-2016 "best practice"
  purge. Both are flags, not evidence of malpractice.

The author decided the five switches on 2026-10-01 (relayed by the MOE;
`status: decided (author 2026-10-01)` in the configs):

- (a) `exclusion.exclude` in `config/rel_venue_registries.yaml`: hijacked
  clones only; Scopus and DOAJ are flags (a title match never excludes);
- (a') `kanal_x`: `flag_only` (every X is a provisional 2026 level);
- (b) `ngo_research_in_b` in `config/rel_venue_tiers.yaml`: true;
- (c) `no_venue`: `keep_flagged` (applied by the loader's `no_venue`
  argument, helper `unknown_switch`);
- (d) `nonresearch`: `to_c` (helper `nonresearch_switch`).

The tiers also read as memberships in the set of serious venues
(`tier_membership`: A 1, B 1, unknown 0.5, C 0) cut at `alpha` 0.5, both
decided by the author on 2026-10-01; 1843 reads them with
`_rel_venues.tier_membership(cfg)` and `_rel_venues.alpha(cfg)`.

Every flag, both NGO tiers, `tier_without_nonresearch` and the `unknown`
state are written whatever the settings, so a sensitivity table can still
show any other setting.

**Index evidence, `mu_venue` (ticket 2042).** Author decisions of 2026-10-09:
series and publishers are tiered like journals (a series or press is in the
B list or a publisher pattern, else it is unlisted: tier C, see `tier_c_other_mu`); presence
in a trusted index counts as evidence of seriousness. The trusted indexes,
their coverage years and caveats are `trusted_indexes` in
`config/rel_venue_registries.yaml`: Kanalregisteret level 1 or 2, the Scopus
Sources sheet, DOAJ (from the change logs) and the university-press patterns
of `venue_evidence`; RePEc and NBER-class series are the B list. All but the
press patterns read the registry files already archived and hashed in the
pull (no new download). Each work gets, in `rel_work_venues.csv`, `index_hits`
(`index:entry_id[first-last]`, the span that holds the work's publication
year), `mu_venue` in {0, 0.5, 1}, `mu_rule` and `mu_rule_version` (every
setting and the pull); `--mu-log` appends the same to an append-only log
keyed by (work, version), refusing a changed row under one version. Rule
(`_rel_venues.mu_venue`), MOE-recommended and not yet confirmed by the author
except where marked: a hijacked clone domain is 0 whatever an index says
(decided 2026-10-01); tier A or B, or a listing at the publication year, is 1;
a listing is never needed for tier A or B; tier C with no listing keeps the decision of
2026-10-01 (0). Open switch `tier_c_other_mu` (`status: open`, MOE option, not
author-decided): 0.5 would read a tier C by the catch-all `other` (an unlisted
series, publisher or journal of unknown type) as unknown, not unserious; it
moves every such work from 0 to 0.5. Withdrawal and discontinuation stay flags. **Open switch**
`venue_evidence.conflict_c_in_index` (`status: open`, MOE option, not
author-decided): the value of a tier C venue listed in a trusted index, 0 by
default (the tier outranks the index; 0.5 neither, 1 the index outranks the
tier). At the defaults of both switches every work scores as under
`tier_membership`; change the
value and rebuild, no code change. The counts file reports works under
dropping or promoting each index and the works moved against the old tier
score by period (first act 1990-2006 apart) and language; the view takes
`mu_venue` as the seriousness facet and exposes `tier`, `index_hits` and the
reason (`rel_reason_detail`), with the same scenarios in `rel_sensitivity.csv`.

**Decision 2026-10-09 on `conflict_c_in_index`.** The author decided that a tier C
venue listed in a trusted index scores 0.5: the shipped value is 0.5 and the
status line reads `author decision`, superseding the "open", "MOE option" and "0 by
default" wording above for this switch only. `tier_c_other_mu` stays 0 (open).
Against the archived pool of 389,291 works the change moves 2,008 works from 0
to 0.5; every other work scores as under `tier_membership`. Revert: set the
value back to 0 and rebuild.

`make rel-view` (ticket 1843) then grades every work as a member of a fuzzy
set: its membership `mu` is the minimum over the facets seriousness, ICF and
discipline, evaluated in that order (cheapest first) and stopped at the first
0 or the first facet not graded yet; the crisp REL set is `mu >= alpha`
(`rel_final`). Each work gets one reason (`rel_reason`): `<facet>_excluded`
for the first facet attaining `mu` below alpha, `<facet>_pending` for the
first facet not graded (`icf_pending`, `discipline_pending` for a work with no
dimension row), else `included`. Membership values: seriousness per tier and
alpha in `config/rel_venue_tiers.yaml` (decided), ICF and discipline under
`membership` in `config/rel_screen.yaml` (proposed). The view needs
`rel_work_venues.csv` (`make rel-venues` first), counts reasons in works and
in families under `reasons` in `rel_counts.json`, counts the ICF-pending works
by tier under `stage2_skip` (those of seriousness 0 need no screening),
records the sha256 of the pool, both append-only tables and the venue table
under `inputs`, and writes `rel_sensitivity.csv`: under each seriousness
setting (publishers dropped, tier A only, Kanalregisteret flipped, Scopus and
DOAJ also excluding, NGO switch flipped, switch (c) flipped, switch (d)
flipped), the included works, families and mu-weighted count, and the works
missing only the discipline facet (`discipline_pending_*`, informative for the
works the 1842 catch-up cannot answer, those without abstract). The rules (which dimension row wins, the
family rule) are in the `scripts/_rel_reasons.py` docstring. A work whose pool abstract is blank after trimming
carries `abstract_flag` `no_abstract` (author decision 2026-10-07). This
raw trimmed-empty predicate remains unchanged; it does not assess whether
nonempty text is a substantive abstract.

For an included work without a selected policy disposition, `rel_use` is
`bibliometric_only` when the raw abstract
is empty (`rel_use_reason` `no_abstract`), or when the selected ICF assessment
has effective input quality `absent`, `nonabstract` or `truncated` (reason
`absent_input`, `nonabstract_input` or `truncated_input`). Nonempty source
text remains intact, including front matter or a source fragment; the quality
restriction does not recode it as an empty abstract. A selected local policy
ICF or dimension disposition also restricts an included work to
`bibliometric_only`, with `rel_use_reason` `local_screen_abstention`, even
when its abstract is nonempty. Its native answer is absent and policy input
quality is `unassessed`; neither is a model assessment. The view exposes
`local_screen_abstention` and selected policy scope, method, run, decision,
reason and proof gaps, backed by the append-only policy provenance table
configured as `policies_table` in `config/rel_screen.yaml` (ticket 2011).

Other included works use `synthesis`: assessed usable abstracts have reason
`usable_abstract`; nonempty legacy abstracts without an input-quality
assessment retain reason `legacy_abstract_unassessed`. These evidence-use
restrictions never move `mu`, `rel_reason` or `rel_final`. Independently
excluded works keep `rel_use` empty; a selected policy still exposes its flag,
provenance and `local_screen_abstention` reason without implying inclusion.
Restrictions follow the assessments actually selected by the view. A later
valid selected usable ICF assessment clears the earlier input-quality
restriction; policy restriction clears only when no policy ICF or dimension
disposition remains selected. A later ICF assessment alone therefore does
not clear a dimension-policy restriction if that policy remains the winning
catchup dimension row; a later valid selected dimension assessment replaces
it under the normal selection rule.
Final counts of 2026-10-07 (view rebuilt twice, byte-identical; measured, from the 1842 and 1843 logs): `seriousness_excluded` 39,115, `icf_excluded` 335,652, `icf_pending` 351, `discipline_pending` 5,894 (all without abstract), `discipline_excluded` 780 (an upper bound: Opus v2 tends to over-exclude applied finance), `included` 7,499; sum 389,291. `rel_dimensions.csv` holds 11,645 works.

### Approved native-titleless intake (ticket 2027)

Ordinary records still require a nonempty title. A separately approved exact
OpenAlex/DOI roster may carry a genuinely empty native title through intake.
The frozen `config/rel_titleless_policy.json` registers the intake manifest and
scientific authority hashes. Its `native_titleless` declaration binds the exact
roster and archived full provider pages. The checker validates the registered
manifest before allowing the exception, then verifies page/query/work hashes,
unique exact identities, native empty titles and complete source fields. Missing,
altered or unlisted evidence fails; a placeholder title is not a repair.

These are operator-approved local native archives. Hash checks establish source
correspondence to those archives, not independent authentication of arbitrary
provider JSON. No model answer, citation edge or document classification is
created by intake. Native `doc_type` and `is_paratext` metadata remain recorded;
these flags alone establish neither scientific irrelevance nor usable content.
The pool carries `native_titleless_provenance`, a portable lane/delivery manifest
locator and hash, so normal selection revalidates its exact source-family member.

The approved 177-member cohort has 110 nonempty reconstructed abstracts and 67
absent abstracts. Presence is not a usability assessment. The 110 can enter the
normal Stage1 selector using unchanged frozen prompts and their existing clipping
behavior. Only actual Stage1 outcomes establish pending Stage2 eligibility;
Stage2 retains complete-field public proof, full input and separate native and
quality-guarded judgments. Ordinary titleless records retain their existing
handling, and the historical 59-titleless waiver is not extended.

The exact 67-member source-absence subset has its own frozen policy authority,
bound to the actual post-admission pool and complete native admission evidence.
The method remains `policy:local-evidence-abstention-v1`; its basis and reason are
`native_titleless_absent_abstract`. It records uncertainty with no native answer,
assessed numerical ICF facets, failed-model attempt or invented public-proof gap.
Actual facet columns and `icf_values` remain blank. Existing uncertainty sentinels
are explicitly policy abstentions; the legacy 43/37 authority is unchanged.
Source-absence routes are reported separately from legacy titleless residue.

Window and seed eligibility are unchanged: `exclude_missing_title`, year/date
rules and normal seed requirements still apply. Intake and screening are distinct
from narrative eligibility. The existing evidence-use calculation is independent
of window disposition: a selected policy abstention may permit bibliometric use
while the titleless record remains outside the review window; exclusion on the
existing membership/venue/discipline rules keeps evidence use blank. Later valid
selected assessments clear the policy restriction. No titleless seed entitlement,
partial-2026 override, scientific closure or new retrieval license follows.
