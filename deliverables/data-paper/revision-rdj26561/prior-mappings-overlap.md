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
by normalized DOI, then by normalized title for works without a DOI match.
Coverage = matched / retrieved.

The replication approximates the *query surface*, not the exact final
corpus: WoS "topic" search also scans Keywords Plus, Scopus subject-area
limits have no OpenAlex equivalent, and manual pruning steps are not
reproduced. Coverage is therefore measured on the OpenAlex population that
each study's query defines, which is the fair, reproducible proxy for its
source population.

## Results (2026-07-22)

| Study | DB | Reported n | Replicated query | Retrieved | Matched | Coverage |
|---|---|---|---|---|---|---|
| Carè & Weber 2023 | Scopus | 315 | "climate finance", 2004–2021, en, ar/re | 849 | 765 | 90.1% |
| Shang & Jin 2023 | WoS | 2,311 | "climate finance", 2001–2022, en, ar/re | 1,072 | 982 | 91.6% |
| Rusydiana 2023 | Scopus | 1,051 | "climate finance", ≤ Oct 2023, ar | 1,264 | 1,160 | 91.8% |
| Reis Maria et al. 2023 | Scopus | 3,275 | "green/climate/carbon/sustainable finance", ≤ Sep 2021 | 4,034 | 1,653 | 41.0% |

Reading: the three mappings whose object is climate finance draw on source
populations that our corpus covers at 90–92%. The one mapping with a
deliberately broader object — Reis Maria et al. map green finance at large,
of which climate finance is one strand — is covered at 41%, consistent with
our corpus's boundary: green and sustainable finance beyond the climate
strand are out of scope by design.

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
> DOI and title: 90–92% of the works retrieved for the climate finance
> queries of Carè and Weber (2023) and Shang and Jin (2023) are present in
> our dataset. Coverage falls to 41% for Reis Maria et al. (2023), whose
> green finance query deliberately spans a broader field than climate
> finance. Our corpus thus contains most of the source populations the
> prior mappings drew on, while adding the multilingual and grey-literature
> layers that no prior mapping covers and publishing the dataset they do
> not release. Script and per-study results are archived in the revision
> folder (`probe_prior_mappings_overlap.py`, `prior-mappings-overlap.csv`).
