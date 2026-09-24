---
paths:
  - "scripts/**"
  - "build/**"
  - "config/**"
  - "Makefile"
  - "**/*.mk"
  - "dvc.yaml"
  - "enrich_cache/**"
  - "data/derived/**"
  - "data/catalogs/**"
  - "tests/test_arch_compliance.py"
  - "tests/test_phase_layout.py"
  - "tests/test_layering.py"
  - "tests/test_doc_contract_consistency.py"
---

# Architecture

Pipeline phases, Phase-2 rules and artifact homes. Scoped siblings: `deliverables.md` (project structure, `DOC_VARS`, `paths.mk`), `data-location.md`, `openalex-corpus.md`, `null-model.md`.

## Pipeline phases

The pipeline has four phases. Each phase's scripts follow a naming convention and have clear input/output contracts. **Never let a later phase trigger an earlier one.**

**Phase 1 — Corpus building** (slow, API-dependent, run rarely on padme).
- Scripts: `catalog_*`, `enrich_*`, `qa_*`, `qc_*`, `corpus_*`
- Four steps with intermediate artifacts:
  1. **corpus-discover**: merge sources → `unified_works.csv`
  2. **corpus-enrich**: enrich DOIs/abstracts/citations → `enriched_works.csv`
  3. **corpus-extend**: flag all works (no rows removed) → `extended_works.csv`
  4. **corpus-filter**: apply policy, audit → `refined_works.csv`
- Phase 1 → Phase 2 **contract**: `refined_works.csv`, `refined_embeddings.npz`, `refined_citations.csv`

**Phase 2 — Analysis & figures** (fast, deterministic, run often):
- Scripts: `analyze_*`, `plot_*`, `compute_*`, `export_*`, `summarize_*`, `build_het_core.py`
- Reads Phase 1 outputs; produces `deliverables/_shared/figures/`, `deliverables/_shared/tables/`, `deliverables/_shared/_includes/`, and each doc's `deliverables/<x>/*-vars.yml` (writing deliverables) and analysis intermediates under `data/derived/` (not destined for a document)

### Phase 2 rules

1. **1 invocation = 1 output.** Each Make target calls one script that writes one file. No side-effect outputs.
2. **Schema-validated.** New CSV artifacts get a Pandera schema in `scripts/schemas.py` (strict=True, coerce=True). Validate at write time — if the schema fails, the script fails, Make stops. (Legacy scripts are migrated as touched.)

   **Deposited artifacts additionally publish their schema and are checked on the written bytes** (ticket 0354). `scripts/_deposit_variables.py` holds the deposit's column contract as structured data (dtype, nullable, enum, range, per-column measured missingness); `scripts/_deposit_schema.py` renders it to a Frictionless Data Package, and `make deposit-validate` runs `frictionless validate` against the CSV as serialised. `build_datapaper_archive.sh` emits the descriptor, validates, and only then packages, so an archive whose data contradicts its own documentation cannot be built. Pandera and this are complementary, not redundant: Pandera guards the *frame* at write time, the descriptor guards the *file* a reuser downloads — the first run of the gate found integers serialised as `2026.0`, which no frame-level check can see. Two consequences worth knowing. Frictionless matches schema fields to columns **by position**, so the descriptor must be ordered by the file and omit fields for columns a build does not produce. And a value coerced to blank in a column the schema declares nullable validates cleanly, so strictness against malformed input belongs at the write step (`errors="raise"`), not in the descriptor.
3. **Modular Makefiles.** Each analysis concern gets its own `.mk` file under `scripts/analysis/` (`divergence.mk`, etc.; ticket 0239), `-include`d by the main Makefile. Adding a new analysis = adding a `.mk`, not editing a 400-line Makefile.
4. **Compute / Plot / Include are separate.** A compute script produces a table. A plot script reads a table and produces a figure. An include reads tables/figures and produces prose. Never mix.
5. **`save_figure()` mandatory.** All plot scripts use `save_figure(fig, stem, dpi=N)` from `pipeline_io.py` — strips metadata for byte-reproducible PNGs. Never call `fig.savefig()` directly.
6. **Config-driven parameters.** All research parameters in `config/analysis.yaml`, read via `load_analysis_config()`. No hardcoded constants for values that might change (windows, seeds, thresholds).
7. **Random seeds from config.** Every stochastic operation reads its seed from `config/analysis.yaml`. No hardcoded `seed=42` or `RandomState(42)`.
8. **Dispatcher pattern.** When multiple methods share data loading and output contract, use a single dispatch script with `--method X` (e.g., `compute_divergence.py`). Method implementations live in private modules (`_divergence_semantic.py`, etc.). Shared I/O helpers in `_divergence_io.py`.
9. **Corpus access through loaders only.** Never call `pd.read_csv()` / `np.load()` / `pd.read_feather()` on contract files (`refined_works`, `refined_embeddings`, `refined_citations`) directly. Use `pipeline_loaders`: `load_refined_works()` (thin read + type coercion), `load_analysis_corpus()` (filtered + optional embeddings), `load_refined_embeddings()`, `load_refined_citations()`. Direct reads bypass Feather acceleration, type coercion, and error hints — and create coupling points that break when the corpus format changes. (Legacy scripts are migrated as touched.)


**Phase 3 — Render** (Quarto → PDF/DOCX):
- Reads Phase 2 outputs. Each deliverable's PDF/DOCX renders next to its `.qmd` under `deliverables/<x>/` (gitignored).

**Phase 4 — Release & archives** (reproducibility packaging):
- Scripts: `build/build_*_archive.sh`
- Templates: `build/templates/` (Makefiles, READMEs, Dockerfiles shipped in archives)
- Reads Phase 2/3 outputs; produces `*.tar.gz` reproducibility archives

Submission *records* (cover/decision letters, frozen PDFs, deposit archives) are
not engine — they live outside the repo under `papiers/<state>/<track>/` (0159).

## Artifact homes by phase

Each phase writes to one place, so an artifact's directory tells you its phase:

| Phase | Produces | Lives in |
|-------|----------|----------|
| **1 — Corpus** (`catalog_/enrich_/qa_/corpus_`) | the corpus contract | `data/catalogs/` (DVC) |
| **2 — Analysis** (`analyze_/compute_/plot_/export_`) | writing deliverables | `deliverables/_shared/{figures,tables,_includes}/`, `deliverables/<x>/*-vars.yml` |
| | analysis **intermediates** (not for a document) | `data/derived/` |
| **3 — Render** (Quarto) | PDF / DOCX | `deliverables/<x>/` next to source (gitignored) |
| **4 — Release** (`build/build_*_archive.sh`) | reproducibility archives | `*.tar.gz` |

The split inside Phase 2 is the crux: it emits two kinds of file — things a paper
renders (→ `deliverables/_shared/`) and intermediates only other scripts read (→ `data/derived/`).
Mixing them is what bloated the shared tables dir (ticket 0208) and hid Phase-2 outputs
in `data/catalogs/` (ticket 0219).

### Phase is semantic, not a filename prefix (ticket 0227)

The prefix table above is a heuristic. A script's phase is what it *does*, not the
letters that start its name. Known exceptions:

- `compute_reranker_calibration.py` — `compute_` prefix, but Phase-1: it scores
  corpus relevance and writes `reranker_calibration.csv` / `reranker_hitl_review.csv`
  to `CATALOGS_DIR`. Correctly a Phase-1 corpus artifact.
- `qa_embeddings.py`, `qa_detect_type.py` — `qa_` prefix (a Phase-1 corpus prefix in
  the table), but their derived outputs are Phase-2: they write to
  `DERIVED_TABLES_DIR` (`semantic_clusters.csv`, `qa_type_report.csv`).

Guard coverage boundary: `tests/test_phase_layout.py` reads the Makefile and checks
only Makefile-wired targets. A script that writes to a hardcoded `CATALOGS_DIR`
default with no Make target is invisible to it — `compute_reranker_calibration.py`
is exactly that case. The guard is a net for wired producers, not a complete phase
audit; the ~20-basename allowlist an exhaustive scanner would need was judged not
worth the upkeep against a low leak probability.

## Incremental caches vs DVC outputs

- **`enrich_cache/`** — persistent cache directory (gitignored, not a DVC output). Survives `dvc repro`.
- **`data/derived/`** — Phase-2 derived data (analysis intermediates, derived tables). Gitignored, non-DVC, regenerable by `make`. Split by phase from `data/catalogs/` so the directory mirrors the pipeline phase (tickets 0208, 0219).
- **DVC output** — declared in `dvc.yaml` `outs:`. Ephemeral — DVC may delete it.

When adding a new enrichment script: put incremental state in `enrich_cache/<name>.csv`, write the DVC output separately.
