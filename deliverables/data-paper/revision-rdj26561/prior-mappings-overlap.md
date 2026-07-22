# Prior bibliometric mappings vs refined corpus — overlap probe (ticket 0289)

Empirical check behind the added-value claim of the RDJ-26561 revision
(editor ED-02, referee R1-18; tickets 0278/0283): the corpus does not just
outnumber the prior climate finance bibliometric mappings, it contains most
of what they mapped.

Probe: `probe_prior_mappings_overlap.py`. Output: `prior-mappings-overlap.csv`
(committed beside this note). Raw OpenAlex pulls cached in
`data/raw/prior_mappings/` (gitignored, regenerable). Corpus:
`refined_works.csv`, 30,987 works, of which 23,309 carry a DOI. Run
2026-07-22 with the OpenAlex premium key.

## Method

For each prior mapping, the published search query was transcribed from the
local PDF (`docs/articles/`, read-before-cite norm) and replicated against
OpenAlex (`title_and_abstract.search`, plus the study's date, type, and
language limits). Each retrieved work was matched into `refined_works.csv`
by normalized DOI, then by normalized title for works without a DOI match;
a title match must also agree on publication year (±1) with the corpus row,
so cross-decade title collisions cannot inflate coverage. Coverage =
matched / retrieved.

The replication approximates the *query surface*, not the exact final
corpus: WoS "topic" search also scans Keywords Plus, Scopus subject-area
limits have no OpenAlex equivalent, and manual pruning steps are not
reproduced. Coverage is therefore measured on the OpenAlex population that
each study's query defines, which is the fair, reproducible proxy for its
source population.

## Results (2026-07-22)

| Study | DB | Reported n | Replicated query | Retrieved | Matched | Coverage |
|---|---|---|---|---|---|---|
| Carè & Weber 2023 | Scopus | 315 | "climate finance", 2004–2021, en, ar/re | 849 | 758 | 89.3% |
| Shang & Jin 2023 | WoS | 2,311 | "climate finance", 2001–2022, en, ar/re | 1,072 | 975 | 91.0% |
| Rusydiana 2023 | Scopus | 1,051 | "climate finance", ≤ Oct 2023, ar | 1,264 | 1,152 | 91.1% |
| Reis Maria et al. 2023 | Scopus | 3,275 | "green/climate/carbon/sustainable finance", ≤ Sep 2021 | 4,034 | 1,618 | 40.1% |

Reading: the three mappings whose object is climate finance draw on source
populations that our corpus covers at 89–91%. The one mapping with a
deliberately broader object — Reis Maria et al. map green finance at large,
of which climate finance is one strand — is covered at 41%, consistent with
our corpus's boundary: green and sustainable finance beyond the climate
strand are out of scope by design.

## Decomposition of the misses (run 2026-07-22, `prior-mappings-misses.csv`)

Crossing each miss against `extended_works.csv` (the pre-filter corpus) and
`corpus_audit.csv` splits the gap into two very unequal classes:

| Study | Misses | Filtered out by our policy | Never captured | Discovery coverage |
|---|---|---|---|---|
| Carè & Weber 2023 | 91 | 87 | 4 | 99.5% |
| Shang & Jin 2023 | 97 | 91 | 6 | 99.4% |
| Rusydiana 2023 | 112 | 101 | 11 | 99.1% |
| Reis Maria et al. 2023 | 2,416 | 211 | 2,205 | 45.3% |

Discovery coverage (captured by at least one source, before filtering) of
the climate finance populations is above 99%. The headline 89–91% is our
own curation: the removed works carry the flags `citation_isolated_old`
(66 of 76 audited unique works), `no_abstract_irrelevant` (8), or
`llm_irrelevant` (1), with a median of 1 citation and none at 50 or more.
The prior mappings included them because a raw query does not curate. For
Reis Maria et al. the decomposition quantifies the boundary instead: only
211 of their 2,416 misses were ever candidates (seen then excluded); 2,205
never matched our climate finance vocabulary at all.

## Why the never-captured escaped — and what to change in the process

Full OpenAlex records of the 11 unique climate finance never-captured works
(fetched 2026-07-22), against our last harvest date (2026-03-22, per-query
`_query_dates.json`):

- **7 of 11 entered OpenAlex after our harvest** (`created_date` between
  2026-03-27 and 2026-05-17): retroactive index growth — repository
  backfills (IRDB Japan, Zenodo, unattributed venues), not works newly
  published. A snapshot corpus decays even for its own period.
- **4 of 11 were in the index at harvest time but invisible to it**
  (created 2019–2025): the plausible channels are retroactive metadata
  enrichment (an abstract added after our pull makes the work findable
  today but not then) and tier-based relevance filtering at extraction.
- The tail is partly noise OpenAlex itself acquired late: a duplicated
  Zenodo deposit pair backdated to 2015 (created 2026-05), an IMF country
  report titled "Kenya", workshop notices.

Process implications (over completing the result list by hand):

1. **Cadence the incremental harvest.** The engine already tracks
   per-query `from_created_date` state; what is missing is a schedule
   (e.g. quarterly) in the v2 process. `from_created_date` alone misses
   the metadata-enrichment channel — a periodic `from_updated_date`
   catch-up pass covers it.
2. **Institutionalize this probe as a recall gate.** The prior mappings'
   published queries are free external ground truth, independent of our
   own vocabulary. A corpus-validate acceptance metric — discovery recall
   ≥ 95% against reference populations — would catch silent snapshot
   decay at each corpus rebuild.
3. **Do not inject the 11 DOIs directly.** The correct loop is
   re-harvest → normal filter funnel, which will also discard the noisy
   tail (the duplicated Zenodo deposits would not survive curation).

Not replicable from local sources: Deb & Chen 2024 (local PDF is an
image-only scan; corpus size and attributions were web-verified under
ticket 0152) and Singhania et al. 2023 (no local fulltext; DOI verified
under 0152).

## Sur-pièce verification of the comparison text (action 1)

Claims in `deliverables/_shared/_includes/bibliometric-context.md` and the
papers, checked against the local PDFs on 2026-07-22:

- Carè & Weber 2023: 315 articles, 2004–2021, Scopus
  TITLE-ABS-KEY("climate finance"), seven clusters, "ghettoization",
  VOSviewer, no dataset published ("No data was used" statement) — all
  confirmed. **The study uses Scopus, not WoS** (ticket body said WoS).
- Shang & Jin 2023: 2,311 papers, WoS SCI+SSCI topic "climate finance",
  2001–2022, English, CiteSpace, Q = 0.392, mean silhouette 0.7373 (≈0.74)
  — all confirmed.
- Reis Maria et al. 2023: 3,275 articles after giant-component filtering
  (3,663 retrieved), STM, three groups, international→national temporal
  shift — confirmed. **The study uses Scopus, not RePEc** — the include
  said "3,275 RePec articles" (corrected in this ticket). Their query has
  **no English-language restriction**; the data-paper's "cover English
  only" is corrected to "search in English only" (all three query strings
  are English phrases). Their GitHub repository
  (github.com/roneyfraga/2021-green-finance, checked 2026-07-22) publishes
  R scripts and a rendered report, not the bibliographic corpus — "do not
  publish reusable datasets" stands.
- Rusydiana 2023: 1,051 Scopus articles, five clusters as listed — confirmed.
- Alonso-Robisco et al. 2024: 217 articles, LDA, seven topics — confirmed.

## Response-letter bullet (feeds 0278/0283)

> The revision strengthens the comparison to prior bibliometric mappings
> beyond the corpus-size ratio. We replicated each study's published search
> query against OpenAlex and matched the retrieved works into our corpus by
> DOI and year-constrained title: 89.3% of the works retrieved for the
> query of Carè and Weber (2023) and 91.0% for that of Shang and Jin
> (2023) are present in our dataset. Coverage falls to 40.1% for Reis
> Maria et al. (2023), whose green finance query deliberately spans a
> broader field than climate finance. The replication covers each study's
> published query surface as OpenAlex resolves it, not its manually pruned
> final corpus; on that measure, our corpus contains most of the source
> populations the prior mappings drew on, while adding the multilingual
> and grey-literature layers that no prior mapping covers and publishing
> the dataset they do not release. Script and per-study results are
> archived in the revision folder (`probe_prior_mappings_overlap.py`,
> `prior-mappings-overlap.csv`).
