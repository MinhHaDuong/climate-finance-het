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

## Migration checklist — the 19 flagged dual-role files

Audited by intent (2026-07-10). 10 were false positives (declared libraries the
syntactic filter mis-flagged); 9 are genuinely dual-role. Destinations are
`scripts/<phase>/`, not `src/`.

### LIBRARY → stays in `scripts/` (relocated by phase), no split (10)

`clustering_methods`, `script_io_args`, `_companion_plot_utils`,
`_divergence_{citation,lexical,semantic}`,
`_permutation_{c2st,graph,lexical,semantic}`. Each self-declares as a library
(`_`-prefix + "no main" docstring, or "Pure algorithmic module"). No CLI, no
split — already the existing convention.

### SPLIT — extract leaked *computation* into `scripts/<phase>/`, script stays (5)

| Script (stays in `scripts/`) | Extract to | Leaked symbol(s) |
|---|---|---|
| `build_het_core.py` | `scripts/harvest/corpus_filters.py` | `is_global_south`, `is_non_english` |
| `build_teaching_yaml.py` | `scripts/harvest/teaching.py` | `_dedup_course_names` (private!) |
| `compute_changepoints.py` | `scripts/analysis/changepoints.py` | `compute_convergence` |
| `summarize_core_venues.py` | `scripts/analysis/venues.py` | `canonical_venue`, `venue_type`, `institution_group` |
| `plot_fig_traditions.py` | `scripts/analysis/traditions.py` | `build_pre2007_traditions` (network build + Louvain, not rendering) |

### MOVE — stays in `scripts/analysis/`, no split, no `-m` (2)

`compute_divergence` (`METHODS` registry + dispatch), `compute_null_model`
(permutation drivers). Import-clean, reused by multiple non-test callers; they
relocate by phase but keep path invocation.

### STAY in `scripts/figures/` — the importer is the bug (2)

`plot_fig_clustering_comparison`, `plot_fig_clustering_spaces`. What leaked is
pure rendering; the smell is that `compute_clustering_comparison.py` (a compute
script) imports a plotter — the backward arrow. Fix by severing the import
(compute writes tables; Make runs the plotter separately), not by relocating.

## Ordered moves (risk ascending)

1. **Analysis fragments** → `scripts/analysis/analysis.mk` (pure `-include` path
   edits; zero build-graph change). Do first.
2. **Phase sub-grouping** — `plot_*`/`export_*` → `scripts/figures/`;
   `analyze_*`/`compute_*` + `_`-private → `scripts/analysis/`;
   `catalog_*`/`enrich_*`/`corpus_*` → `scripts/harvest/`; `qa_*` → `scripts/qa/`.
3. **`deliverables/` co-location** + per-paper `_quarto.yml` (kills the
   exclusion-mask profile files; DVC-independent).
4. **The five extractions** land beside their phase; leaking scripts import them.
   Behind a full `make clean && make all` gate.
5. **`compute_clustering_comparison` dependency-inversion cleanup** — separate
   follow-up; not on the reorg critical path.
