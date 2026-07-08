# Audit: manuscript computational-statistic provenance and v1 consistency

Ticket 0161 (R&R v2.0.5). Auditors: HDMX-coding-agent. Date: 2026-07-08.

## Scope

Every pipeline-derived number in `content/manuscript.qmd` — body and appendix A.2–A.6.
Out of scope (ticket invariant): historical / secondary-source figures the pipeline does
not produce (SCF "$340–650bn", "7,500 CDM projects", "$100bn", Türkiye rates, etc.).

The manuscript ships **corpus v1.0**: figure `fig_bars_v1.png` is built `--v1-only`
(the `in_v1==1` subset), `fig_composition.png` reads the frozen `config/v1_tab_alluvial.csv`
+ `config/v1_cluster_labels.json`, and `manuscript-vars.yml` is pinned ("Do not
auto-regenerate"). The audit asks, for each cited number: does it trace to that frozen
v1 baseline, or to the *current* corpus (v1.1.1, ~27,315 works) that the Phase-2 loaders read?

## Method

For each number: located its generator (`grep` over `content/_includes/`, `scripts/`,
`config/`, Makefiles), read that generator to see whether it reads the frozen v1 artifacts
or the live Phase-1→2 contract files (`refined_works` / `refined_citations` via
`pipeline_loaders`), and searched for a committed artifact recording the value.

Verdicts: **PINNED** (traces to a v1 archive/config, reproducible against the shipped
corpus) · **CURRENT-CORPUS** (computed on the live corpus, drifts as it grows; traceable
to a committed include) · **UNARCHIVED** (traceable only to a generator script; no committed
artifact records the value, so the prose is the sole record — the "0.68" failure mode) ·
**PINNED≈** (pinned but a loose approximation).

## Audit table

| # | Number (value · location) | Source (file:line) | Corpus | Archived v1 value | Verdict |
|---|---|---|---|---|---|
| 1 | silhouette −0.01, EN vs non-EN · A.3 L256 | `clustering-comparison.md:116` (−0.010) | CURRENT | none found | CURRENT-CORPUS |
| 2 | silhouette 0.025 at k=6 · A.3 L258 | `clustering-comparison.md:75,81,126` | CURRENT | none found | CURRENT-CORPUS |
| 3 | k=6 (matches 6 co-citation communities) · A.3 L258 | `clustering-comparison.md:79`; `config/analysis.yaml` | CURRENT | v1 uses 6 clusters (`config/v1_cluster_labels.json`) | PINNED (choice) |
| 4 | ~98% noise, HDBSCAN · A.3 L260 | `clustering-comparison.md:51,53,85` (97.7%) | CURRENT | none found | CURRENT-CORPUS |
| 5 | ARI 0.59 spectral · A.3 L260 | `clustering-comparison.md:49` (0.587) | CURRENT | none found | CURRENT-CORPUS |
| 6 | ARI 0.98 k-means · A.3 L260 | `clustering-comparison.md:47` (0.980) | CURRENT | none found | CURRENT-CORPUS |
| 7 | ~1 re-clustering in 10 · A.3 L260 | `clustering-comparison.md:65` | CURRENT | none found | CURRENT-CORPUS |
| 8 | ARI 0.06–0.22 cross-space · A.3 L260 | `clustering-comparison.md:104–106,137` | CURRENT | none found | CURRENT-CORPUS |
| 9 | ~3× more group structure (citation) · A.3 L260 | `clustering-comparison.md:79,135` | CURRENT | none found | CURRENT-CORPUS |
| 10 | 84 nodes, 369 edges · A.5 L276 | `compute_null_separation.py` → `tab_null_separation_pre2007.csv` (**uncommitted**) | CURRENT (`$(REFINED)`,`$(REFINED_CIT)`) | none | **UNARCHIVED** |
| 11 | within-tradition share 0.89 · A.5 L276 | same | CURRENT | none | **UNARCHIVED** |
| 12 | config-model null 0.37 · A.5 L276 | same | CURRENT | none | **UNARCHIVED** |
| 13 | z ≈ 25, N = 1000 · A.5 L276 | same (`n_perm` from `config/analysis.yaml:pre2007_separation`) | CURRENT | none | **UNARCHIVED** |
| 14 | ~3 co-citation-core nodes match · A.5 L276 | same (a-priori labelling path) | CURRENT | none | **UNARCHIVED** |
| 15 | 250-ref ceiling; resolution 1.0; weight<3 · A.5 L272 | `compute_temporal_communities.py:193`; `config/analysis.yaml`; `cocitation-communities.md:16` | CURRENT (method params, corpus-agnostic) | — | PINNED (params) |
| 16 | fewer than 50 works/yr pre-2007 · body L102 | `plot_fig1_bars.py --v1-only` (`in_v1==1`) → `fig_bars_v1.png` | v1 | v1 subset | PINNED |
| 17 | ~3% of pool, two hand-collected sources · A.2 L248 | `corpus-construction.md:27` (~900 works, ~3%; >500 overlap) | construction-stage (stable) | ~3% | CURRENT-CORPUS (low-risk) |
| 18 | "about 30,000" works · body L84, A.2 L248 (`{{< meta >}}`) | `manuscript-vars.yml:4` (pinned) | v1 (pinned) | 30,000 | PINNED≈ (actual: v1_tagged 26,355; current 27,315) |
| — | @fig-breaks (2007 sharp, 2013 weak, 2009 survives) · Method L86, A.4 L268 | `plot_fig2_breaks.py` + `$(REFINED)` | CURRENT | none | CURRENT-CORPUS (qualitative) |
| — | @fig-composition (thematic recomposition) · A.3 L262 | frozen `config/v1_tab_alluvial.csv` + `v1_cluster_labels.json` | v1 | v1 | PINNED |
| — | @fig-bars (growth of literature) · Method L80 | `fig_bars_v1.png` (`--v1-only`) | v1 | v1 | PINNED |
| — | @tbl-venues (venue concentration) · A.6 L284 | `tables/tab_venues.md` (include) | CURRENT | none found | CURRENT-CORPUS |

## Cross-cutting findings

1. **The structural inconsistency (core).** The manuscript's *figures* are correctly
   v1-pinned (`fig_bars_v1` via `--v1-only`; `fig_composition` from frozen config), but its
   *appendix prose numbers* (A.3 clustering, A.5 co-citation, A.6 venues, and `@fig-breaks`)
   are computed on the **current** corpus. Every appendix generator
   (`analyze_cocitation.py`, `compute_temporal_communities.py`, `compute_null_separation.py`,
   `plot_fig2_breaks.py`) reads `refined_works` / `refined_citations` — the live contract —
   not the v1 subset. A v1.0 manuscript therefore reports appendix statistics from a corpus
   it does not ship. This is the same *class* of defect as the dropped "0.68" modularity.

2. **The priority integrity fix — A.5 (rows 10–14).** These five numbers are the closest
   analogue to the 0.68 trap present in the current manuscript. They are **hand-transcribed
   into the prose** (`manuscript.qmd:276`); their generator's output table
   `content/tables/tab_null_separation_pre2007.csv` is **not committed and not on disk**; and
   the manuscript does not `{{< include >}}` it. The prose is the sole committed record of the
   values. They *are* deterministically reproducible in principle (script + seed + config all
   committed) — but only against the drifting current corpus, and with no archived value to
   check the transcription against. Added *after* this ticket was filed, by tickets 0182/0183.

   **A second committed source disagrees on the same graph.** The manuscript says the pre-2007
   co-citation network has **84 nodes, 369 edges** (`compute_null_separation.py` via
   `plot_fig_traditions.build_pre2007_traditions`). The committed include
   `cocitation-communities.md:26–29` — describing the *same* construction (top-250 references,
   weight ≥ 3, isolates removed, current corpus, generated by `compute_temporal_communities.py`) —
   reports **169 nodes, 1,056 edges, 18 communities, modularity 0.18**. Two code paths for "the
   pre-2007 graph" give figures ~2× apart. This is an *observation*, not yet a diagnosis: the
   two builders may legitimately differ (e.g. one restricts to tradition-labelled nodes, or the
   include predates a corpus refresh). Either way it must be reconciled — as written, a reader
   comparing the appendix with the technical-report include finds two different pre-2007 graphs,
   and 84/369 has no committed generator output to adjudicate between them. Reconciling this, and
   committing the generator output, is the non-negotiable fix regardless of the policy chosen.

   **Refined diagnosis (code read, no run).** The two builders are algorithmically equivalent on
   inspection: same cutoff (2006, both from `breaks[0]-1` via `pre2007_cutoff_year`), same
   `normalize_doi` applied to both `source_doi` and `ref_doi`, same `TOP_N=250`, `MIN_COCIT=3`,
   same isolate removal, same co-citation definition (group by `source_doi`, count co-citing
   source papers per reference pair). Nothing in the code explains a 2× gap. The most likely cause
   is therefore **not a code bug but two different `refined_citations` snapshots** at the two
   generation times — and `refined_citations` is precisely the artifact the in-progress v1.1.2
   GROBID reference-extraction pass regenerates. The co-citation graph is built entirely from that
   file, so it is far more sensitive to citation-extraction changes than the works count is. This
   is an inference from reading the code, not a proven cause; the confirming test is to run both
   builders on one frozen `refined_citations` and diff.

3. **A.3 is traceable but current (rows 1–9).** All nine clustering numbers match
   `clustering-comparison.md` exactly. That include is committed — but carries
   `<!-- WARNING: AI-generated, not human-reviewed -->` and a `STALE` note
   ("current analysis corpus is ~27,509; needs fresh `compute_clustering_comparison` run").
   So the manuscript matches a committed-but-stale, AI-generated, current-corpus include.

4. **"About 30,000" overstates (row 18).** The pinned value exceeds every actual count
   (v1 subset 26,355; current 27,315) by ~10%. It reads "about", so it is not a
   misstatement, but the reproducible figure is ~27,000. Consider "about 27,000" or
   "nearly 30,000".

5. **Figures and method params are sound.** Rows 3, 15, 16, and the two v1 figures need no action.

## Frozen-data policy decision (Action 4) — DECIDED: Option C (2026-07-08)

The author chose **C** in the working session that produced this PR (message "C then." in reply
to the drafted A/B/C options; "merge on approve" as sign-off on the resulting R&R prose PR #907):
keep the v1 figures frozen, disclose the appendix diagnostics as current-corpus robustness, and
give every cited number an archived source. Rationale for C over B (re-baseline): the current
corpus is mid-flight (v1.1.2 regenerating on padme), re-baselining would re-open the Errata 1
label-instability risk, and it would desync the frozen figures from the submission. Sequenced as
"C now, B once v1.1.2 is frozen" if single-version cleanliness is wanted later.

**Done in this PR (autonomous):**
- Disclosure paragraph added to A.2 (`manuscript.qmd`): states that the two v1 figures are frozen
  while `@fig-breaks` and the appendix statistics use the current working corpus, reproducible
  from the pipeline, and that nothing in the argument turns on the difference.
- `.gitignore` exception for `tab_null_separation_pre2007.csv` + `tab_pre2007_coverage.csv`, which
  *prepares* the A.5 generator output to be committed. The tables are not generated in this PR, so
  A.5 remains prose-only until the handoff step below runs and commits the CSV.

**Handoff — needs a pipeline run on your side (after v1.1.2 settles; no-heavy-compute rule). Tracked as ticket 0195:**
1. `make separation` → commit `tab_null_separation_pre2007.csv` (now un-ignored); check the A.5
   prose numbers (84/369/0.89/0.37/z≈25) against the committed CSV and fix any drift.
2. Reconcile the 84/369-vs-169/1,056 pre-2007 graph: run both builders on the same frozen
   `refined_citations`; if they still disagree it is a code bug (two canonical graphs), else it was
   citation-snapshot drift — either way, cite one construction.
3. Refresh the stale, AI-generated `clustering-comparison.md` (`compute_clustering_comparison`) and
   re-check the nine A.3 numbers.

---

### The three options as drafted (for the record)

The manuscript needs one coherent rule, applied to the whole appendix. Three options:

**Option A — Pin the appendix to v1.** Regenerate A.3/A.5/A.6/`@fig-breaks` on the frozen
v1.0 subset (`in_v1==1`), commit each output table under `content/tables/`, and cite from the
committed artifacts. *Pro:* the manuscript becomes internally consistent and every number
reproducible against the corpus it ships. *Con:* most work; A.5's null model and the
clustering-comparison must be re-run `--v1-only`, and some numbers will change.

**Option B — Re-baseline the whole manuscript onto the current corpus.** Rebuild
`fig_bars`/`fig_composition` on the live corpus, drop the v1 pinning, update
`manuscript-vars.yml`. *Pro:* one current corpus throughout; appendix already matches. *Con:*
abandons the "frozen submission snapshot" property; the submitted figures would no longer
match the v1.0 archive on Zenodo; re-opens label-stability questions (Errata 1).

**Option C — Keep figures v1-pinned; disclose the appendix as current-corpus robustness (recommended).**
The appendix is explicitly *confirmatory* methodology (A.1), not a load-bearing v1 result. Keep
the v1 figures; add one provenance sentence to A.1 stating the diagnostics are computed on the
current corpus (v1.1.1) as a robustness check, reproducible from the live pipeline; and **commit
the generating tables** (esp. `tab_null_separation_pre2007.csv`) so every cited number has an
archived record and A.5 stops being prose-only. Refresh the stale `clustering-comparison.md`.
*Pro:* least disruption, preserves the frozen submission, closes the integrity gap (rows 10–14).
*Con:* the manuscript openly mixes two corpus versions — must be stated, not hidden.

Whichever is chosen, the non-negotiable fix is rows 10–14: A.5's numbers must gain a
committed, archived source (either regenerated `--v1-only` under A, or the current table
committed under B/C). See [[feedback_manuscript_number_provenance]].

## Exit-criterion evidence

- **"Every pipeline-derived number has a documented, reproducible source"** — table above; all
  18 rows sourced to `file:line`. One class (rows 10–14) is unarchived, and its node/edge counts
  conflict with a second committed source (finding 2) — reconciliation deferred to ticket 0195.
- **"Mismatches resolved"** — policy C chosen (below). The corpus-version mismatch is resolved by
  disclosure (A.2 paragraph, this PR); the A.5 archiving + builder reconciliation run on the
  pipeline under ticket 0195. No v1-pinned number was rewritten (ticket invariant).
- **"Frozen-data policy decision recorded"** — DONE: Option C, chosen by the author (see below).
