# Repository layout — target state and migration

> **Status (2026-07-10, author-adjudicated).** Canonical rules live in
> `.claude/rules/architecture.md`, governed by tracker `0221`. This note covers
> the **code + prose** axis (tracker `0223`, deferred to post-Œconomia-resubmit).
> Decisions:
> - **`deliverables/` per-paper Quarto — RATIFIED.** Replaces the one-`content/`
>   multi-doc project; update `architecture.md` § Project structure when it lands.
> - **`src/climatefinance/` — DECLINED.** The existing library convention stands:
>   `_`-private modules + `pipeline_*` loaders in `scripts/`, and `libs/` for
>   cross-repo sharing. No top-level package, no `python -m` flip.
> - **Shared harvest + indexing for AEDIST → `libs/`.** Cross-repo sharing grows
>   `libs/openalex-corpus`, not a top-level `src/`. Seed `0229`.
>
> The **data-layout axis** (`data/catalogs` = Phase 1 / `data/derived` = Phase 2)
> is owned by `0221`/`0218`/`0222` and is *en cours* (a parallel session is
> executing it). Where this note and `architecture.md` disagree,
> `architecture.md` wins.

The top level grew to 43 entries with two flat mega-directories (`scripts/`,
173 files; `content/`, ~7 deliverables). This note fixes the target tree, the
rule that decides where a file goes, and the migration checklist.

## Target tree

```
scripts/                       # all Python; grouped by dataflow phase
  harvest/                     # Phase 1: catalog_*, enrich_*, corpus_*, scout, openalex
  analysis/                    # Phase 2 compute: analyze_*, compute_* + _-private
                               #   library modules (_divergence_*, _permutation_*,
                               #   clustering_methods, …) + analysis.mk
  figures/                     # rendering: plot_*, export_*
  qa/                          # qa_* audits
  (shared infra: utils, schemas, pipeline_* loaders, script_io_args)
tests/                         # unchanged
tickets/                      # unchanged
deliverables/
  manuscript/                  # .qmd + _quarto.yml + vars.yml + manuscript.mk
  data-paper/  agentic/  multilayer/  zoo/
  slides-gide/  slides-eshet/     # slides are deliverables, not papers
  _shared/                     # main.bib, _includes/, style-references/, figures/ (generated)
config/  data/                 # config, DVC data (data/ split by phase — 0221)
libs/openalex-corpus/          # separately-installable package; AEDIST-shared (0229)
Makefile                       # root orchestrator; -includes each fragment at its path
```

## The placement rule

Library vs entry point is a **semantic** boundary — authorial intent (reuse vs
run), not a syntactic property. Decide per file:

1. **Imported by another module → library.** It stays in `scripts/` as a
   `_`-private module (the existing convention), or moves to `libs/` if it is
   shared across repos. No top-level `src/`.
2. **Invoked by the Makefile, imported by nothing → entry point**, in the
   `scripts/<phase>/` that matches what it produces. Moving it there keeps its
   flat imports working: the repo resolves `from utils import …` /
   `import openalex_corpus` via the relative source roots `scripts` and
   `libs/openalex-corpus/src`. The single rule (ticket 0253): **these source
   roots are on the path in every execution context — pytest (`pythonpath`),
   make (`export`), test subprocesses (explicit env), containers (Dockerfile
   `ENV`), and archive scripts/Makefiles — never assumed ambient.** So a subdir
   entry point needs no `sys.path` hack and no `python -m` (pilot `scripts/figures/`).
3. **A script that *leaks* a helper** (imported ≥1 but authored to run) → extract
   the *helper* into a module in the owning `scripts/<phase>/`; the script stays.
   Import-count is a symptom; the docstring / `_`-prefix / pure-function-vs-`main()`
   reveal intent.

### Layering invariant

> The dependency arrow runs `deliverables → scripts/figures → scripts/analysis`
> (compute), never backward. A compute module must not import a plotter. A plot
> function imported by a *compute* module is an arrow pointing the wrong way —
> fix the importer, do not promote the plotter.

This is `architecture.md` rule 4 (compute/plot/include separate) restated as a
layering constraint. **Nothing that renders is imported by compute.**

### Makefile fragments

A build fragment lives next to what it *builds*, and the split is by phase:

- **Phase-3 render** fragments → the deliverable's own folder,
  `deliverables/<x>/<x>.mk` (`manuscript.mk`, `zoo.mk`, `multilayer.mk`, …).
  `make papers` invokes each via `$(MAKE) -f`, so the render process never
  parses the Phase-2 rules (ticket 0237).
- **Phase-2 analysis concern** fragments → `scripts/analysis/`, one file per
  concern (`divergence.mk`, `separation.mk`, `venues.mk`,
  `multilayer-detection.mk`, `zoo-figures.mk`), because what they build feeds
  several deliverables, not one (ticket 0239). They stay separate, not merged —
  the modular-Makefile rule (architecture.md Phase-2 rule 3) is one `.mk` per
  concern. The Phase-2 `zoo` fragment is `zoo-figures.mk` to disambiguate from
  the Phase-3 render `deliverables/zoo/zoo.mk`.
- `paths.mk` stays at the repo root — the shared variable interface `-include`d
  by both the Phase-2 Makefile and every Phase-3 render fragment.

Moving a `.mk` file is cheap: `-include`d rules resolve relative to the *root*
Makefile, so paths inside are unchanged — only the `-include` line edits.
Moving the referenced *scripts* is the real edit (prereq paths).

## Definitive Tier-2 / Tier-3 classification (ticket 0254)

> **This table is the contract wave-1 moves (0255–0258) consume.** It supersedes
> the 2026-07-10 "19 flagged dual-role files" checklist (which predates the
> two-tier rule and proposed phase-subdir destinations for *imported* files — a
> contradiction the ratified rule resolves: **imported by another script ⇒ stays
> flat**). Built mechanically from the `scripts/*.py` import graph; the gate test
> `tests/test_script_classification.py` pins it.

**The rule.** A top-level `scripts/*.py` is **Tier-2 (stays flat)** iff it is
imported by any other top-level script (test-only importers do not count);
otherwise it is **Tier-3 (a pure entry point that moves to `scripts/<phase>/`)**.
`_`-prefix, a `__main__` guard, or filename prefix are heuristics, not the test —
being imported is.

**Reconciliation.** 177 top-level `scripts/*.py` (174 audited + 3 modules 0254
extracted) = **45 Tier-2 (flat)** + **132 Tier-3 (movers)**. Movers by phase:
figures 62 · harvest 25 · analysis 34 · qa 11.

### Tier-2 — flat library surface (45, stay at `scripts/` root)

**Private `_`-modules (21):** `_citation_methods`, `_companion_plot_utils`,
`_corpus_predicates`, `_course_dedup`, `_divergence_backend`, `_divergence_c2st`,
`_divergence_citation`, `_divergence_community`, `_divergence_io`,
`_divergence_lexical`, `_divergence_semantic`, `_null_separation`,
`_permutation_accel`, `_permutation_c2st`, `_permutation_citation`,
`_permutation_graph`, `_permutation_io`, `_permutation_lexical`,
`_permutation_semantic`, `_pre2007_traditions`, `_venue_naming`.

**Named libraries, no `__main__` (18):** `clustering_methods`, `filter_flags`,
`filter_flags_llm`, `openalex_pool`, `pipeline_io`, `pipeline_loaders`,
`pipeline_progress`, `pipeline_text`, `plot_style`, `qa_near_duplicates`,
`schemas`, `script_io_args`, `syllabi_config`, `syllabi_crossref`,
`syllabi_harvest`, `syllabi_io`, `syllabi_process`, `utils`.

**Dual-role reclassified Tier-2 (6, have a thin `main()` but are genuinely
reused computational libraries — extraction would fracture a tight cluster):**
`compute_divergence` (`METHODS` dispatch registry, rule 8), `compute_null_model`
+ `compute_divergence_bootstrap` (permutation drivers imported across the
divergence family), `compute_changepoints` (convergence computation reused by
`compute_convergence.py`), `corpus_merge_citations` (`merge_citations` reused by
the cache-migration one-off), `enrich_dois` (`find_doi` cached-lookup API reused
by `syllabi_process`). Extracting any is a viable future refinement but not
required; the flat classification already makes every mover import-leaf.

### Tier-3 — movers by phase (132; each an entry point imported by no script)

- **→ `scripts/figures/` (0255): 62** — all `plot_*` and `export_*`. Includes
  `export_core_venues_markdown` (now imports `_venue_naming`, not
  `summarize_core_venues`) and both clustering plotters (the former
  `compute_clustering_comparison` backward arrow was already severed by 0242).
- **→ `scripts/harvest/` (0256): 25** — all `catalog_*`, `enrich_*`, `corpus_*`,
  `scout_tradition_coupling`, plus the two Phase-1 teaching-harvest builders
  `build_teaching_yaml` / `build_teaching_canon`, and the semantic exception
  `compute_reranker_calibration` (Phase-1 despite its `compute_` prefix).
- **→ `scripts/analysis/` (0257): 34** — all `analyze_*`, the Tier-3 `compute_*`,
  `summarize_*`, `build_het_core`, plus `build_smoke_fixture` (test-fixture
  builder). `summarize_core_venues` and `build_het_core` are movers *because* 0254
  extracted their leaked helpers.
- **→ `scripts/qa/` (0258): 11** — all `qa_*` except `qa_near_duplicates` (a
  pure library, Tier-2).

### 0254 resolutions of the dual-role hazard

Nine files were entry-point-AND-imported. Three had a genuine helper leaked from
an output-producing entry point → **extracted to a neutral flat `_`-module (the
0250 pattern), byte-identical by construction**, freeing the entry point to move:

| Entry point (now Tier-3) | Extracted helper(s) → flat module | Repointed importer(s) |
|---|---|---|
| `summarize_core_venues` | `canonical_venue`/`venue_type`/`institution_group` → `_venue_naming.py` | `compute_venue_concentration`, `export_core_venues_markdown` |
| `build_het_core` | `is_global_south`/`is_non_english` → `_corpus_predicates.py` | `analyze_multilingual` |
| `build_teaching_yaml` | `_dedup_course_names` → `_course_dedup.py` | `analyze_syllabi` |

The other six were **reclassified Tier-2** (see above). One correction to the old
audit: `qa_near_duplicates` has no `__main__` and its docstring documents a
`from qa_near_duplicates import …` API — it is already a pure library (Tier-2),
never dual-role.

### Flags for the move tickets

- **Prefix gaps.** The move tickets key on filename prefixes, but three Tier-3
  entry points match no listed prefix: `build_teaching_yaml`, `build_teaching_canon`
  (→ harvest, above) and `build_smoke_fixture` (→ analysis). Route them by phase,
  not prefix.
- **Unwired orphans (4).** `analyze_alluvial`, `analyze_communities_clusters`,
  `compute_temporal_communities`, `plot_interactive_corpus` have no `__main__`
  guard and no Make target — they run at module top level and nothing invokes
  them. Classified Tier-3 (not library surface), but they are dead-code
  candidates: verify before moving, or triage separately. Out of 0254 scope.

## Ordered moves (risk ascending)

1. **Analysis fragments** → `scripts/analysis/analysis.mk` (pure `-include` path
   edits; zero build-graph change). Do first.
2. **Phase sub-grouping** — move only the Tier-3 entry points per the table
   above: `plot_*`/`export_*` → `scripts/figures/`; Tier-3 `analyze_*`/`compute_*`/
   `summarize_*`/`build_het_core`/`build_smoke_fixture` → `scripts/analysis/`;
   `catalog_*`/`enrich_*`/`corpus_*`/`scout*`/`build_teaching_*`/
   `compute_reranker_calibration` → `scripts/harvest/`; `qa_*` → `scripts/qa/`.
   Every Tier-2 module (all `_`-private and the named libraries) stays flat.
3. **`deliverables/` co-location** + per-paper `_quarto.yml` (kills the
   exclusion-mask profile files; DVC-independent).
4. **Dual-role extractions** — done in wave-0a as flat `_`-modules, not phase
   subdirs (0250 extracted `_pre2007_traditions`; 0254 extracted `_venue_naming`,
   `_corpus_predicates`, `_course_dedup`). The remaining six dual-role files stay
   flat as Tier-2 libraries; no phase-subdir extraction is required.
5. **`compute_clustering_comparison` dependency-inversion cleanup** — already
   severed by 0242; the two clustering plotters move as ordinary Tier-3 figures.
