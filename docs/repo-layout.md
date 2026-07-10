# Repository layout — target state and migration

> **Status (2026-07-10, author-adjudicated).** Canonical rules live in
> `.claude/rules/architecture.md`, governed by tracker `0221`. This note covers
> the **code + prose** axis. Decisions:
> - **`deliverables/` per-paper Quarto — RATIFIED.** Replaces the one-`content/`
>   multi-doc project; update `architecture.md` § Project structure when it lands.
> - **`src/climatefinance/` — DECLINED.** The existing library convention stands
>   (`_`-private + `pipeline_*` loaders in `scripts/`; `libs/` for cross-repo
>   sharing). The sections below that mention `src/` are superseded: LIBRARY-10
>   and MOVE-2 files stay in `scripts/` (relocated by phase), and the SPLIT-5
>   extractions land as plain/`_`-private modules **inside their phase subdir**
>   (`scripts/analysis/traditions.py`, etc.) — read every "`src/`" below as
>   "the owning `scripts/<phase>/` module."
> - **Shared harvest + indexing for AEDIST → `libs/`.** Cross-repo sharing grows
>   `libs/openalex-corpus`, not a top-level `src/`. Seed `0229`.
>
> The data-layout axis is owned by `0221`/`0218`/`0222`. Where this note and
> `architecture.md` disagree, `architecture.md` wins until it is updated.

The top level grew to 43 entries with two flat mega-directories (`scripts/`,
173 files; `content/`, ~7 deliverables). This note fixes the target tree, the
rule that decides where a file goes, and the migration checklist.

Tracking ticket: `tickets/0223-repo-layout-reorg.erg` (code + prose axis).

## Target tree

```
src/climatefinance/          # library — importable, no rendering, no CLI-only files
scripts/
  harvest/                   # Phase 1: corpus_*, catalog_*, enrich_*, scout, openalex
  analysis/                  # Phase 2 entry points: analyze_*, compute_* + analysis.mk
  figures/                   # rendering entry points: plot_*, export_*
  qa/                        # qa_* audits
tests/                       # unchanged
tickets/                     # unchanged
deliverables/
  manuscript/                # .qmd + _quarto.yml + vars.yml + manuscript.mk
  data-paper/  agentic/  multilayer/  zoo/
  slides-gide/  slides-eshet/     # slides are deliverables, not papers
  _shared/                   # main.bib, _includes/, style-references/, figures/ (generated)
config/  data/               # config, DVC data
libs/openalex-corpus/        # a separately-installable package the repo also ships
Makefile                     # root orchestrator; -includes each fragment at its new path
```

## The placement rule

`src/` vs `scripts/` is a **semantic** boundary — it signals authorial intent
(reuse vs run), not a syntactic property. Decide per file:

1. **Imported by another module → `src/`.** Even if it also has a CLI: keep the
   `if __name__ == "__main__":` guard and invoke it as `python -m
   climatefinance.<mod>`. Requiring an install to run is the installability
   discipline `src/` exists to enforce.
2. **Invoked by the Makefile, imported by nothing → `scripts/`.** Pure leaf
   entry points.
3. **A script that *leaks* a helper** (imported ≥1 but authored to run) → the
   *helper* moves to `src/`; the script stays in `scripts/`. Import-count is a
   symptom; the docstring / `_`-prefix / whether the export is a pure function
   vs a `main()` reveal intent.

### Layering invariant

> The dependency arrow runs `deliverables → scripts/figures → src/`, never
> backward. `src/` (computation) must not import a plotter. A plot function
> imported by a *compute* module is an arrow pointing the wrong way — fix the
> importer, do not promote the plotter to `src/`.

This is the project's existing compute/plot/include-separation rule restated as
a layering constraint. **Nothing that renders lands in `src/`.**

### Makefile fragments

A build fragment lives next to what it *builds*:

- Deliverable-scoped (`manuscript.mk`, `zoo.mk`, `multilayer-detection.mk`) →
  into that `deliverables/<x>/` folder.
- Shared analysis (`divergence.mk`, `separation.mk`, `venues.mk`) → with the
  analysis workpackage (`scripts/analysis/analysis.mk`), because what they build
  feeds several deliverables, not one.

Moving a `.mk` file is cheap: `-include`d rules resolve relative to the *root*
Makefile, so paths inside are unchanged — only the `-include` line edits.
Moving the referenced *scripts* is the real edit (prereq paths).

## Migration checklist — the 19 flagged dual-role files

Audited by intent (2026-07-10). 10 were false positives (declared libraries the
syntactic filter mis-flagged); 9 are genuinely dual-role.

### LIBRARY → `src/` intact (10)

`clustering_methods`, `script_io_args`, `_companion_plot_utils`,
`_divergence_{citation,lexical,semantic}`,
`_permutation_{c2st,graph,lexical,semantic}`. Each self-declares as a library
(`_`-prefix + "no main" docstring, or "Pure algorithmic module"). No CLI, no
split.

### SPLIT — extract leaked *computation* → `src/`, script stays in `scripts/` (5)

| Script (stays in `scripts/`) | Extract to `src/…` | Leaked symbol(s) |
|---|---|---|
| `build_het_core.py` | `corpus_filters.py` | `is_global_south`, `is_non_english` |
| `build_teaching_yaml.py` | `teaching.py` | `_dedup_course_names` (private!) |
| `compute_changepoints.py` | `changepoints.py` | `compute_convergence` |
| `summarize_core_venues.py` | `venues.py` | `canonical_venue`, `venue_type`, `institution_group` |
| `plot_fig_traditions.py` | `traditions.py` | `build_pre2007_traditions` (network build + Louvain, not rendering) |

### MOVE intact → `src/`, invoke via `python -m` (2)

`compute_divergence` (`METHODS` registry + dispatch; alt: extract just the
registry), `compute_null_model` (permutation drivers). Both import-clean, reused
by multiple non-test callers.

### STAY in `scripts/figures/` — the importer is the bug (2)

`plot_fig_clustering_comparison`, `plot_fig_clustering_spaces`. What leaked is
pure rendering; the smell is that `compute_clustering_comparison.py` (a compute
script) imports a plotter — the backward arrow. Fix by severing the import
(compute writes tables; Make runs the plotter separately), not by relocating.
Tracked separately.

## Ordered moves (risk ascending)

1. **Analysis fragments** → `scripts/analysis/analysis.mk` (pure `-include`
   path edits; zero build-graph change). Do first.
2. **Figures split** — `plot_*` → `scripts/figures/` (Makefile figure targets).
3. **`deliverables/` co-location** + per-paper `_quarto.yml` (kills the
   exclusion-mask profile files; DVC-independent).
4. **`src/` move** — the LIBRARY-10 + SPLIT-5 + MOVE-2, Makefile invocations
   flipped to `python -m`. Behind a full `make clean && make all` gate. Last,
   because it rewrites prereq paths and script imports.
5. **`compute_clustering_comparison` dependency-inversion cleanup** — separate
   follow-up; not on the reorg critical path.
