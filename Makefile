# Makefile — Counting Climate Finance (Œconomia)
#
# Four-phase pipeline, namespaced by concern:
#   corpus-*      Phase 1: collection, enrichment, alignment (slow, API-dependent)
#   analysis-*    Phase 2: embeddings, clustering, figures (fast, deterministic)
#   manuscript-*  Phase 3: Oeconomia article rendering
#   datapaper-*   Phase 3: RDJ4HSS data paper rendering
#   archive-*     Phase 4: release & reproducibility packages
#
# Usage:
#   make                    Build manuscript (default)
#   make manuscript         Build manuscript only (PDF + DOCX)
#   make papers             Build all documents
#   make analysis-figures   Regenerate all figures
#   make analysis-stats     Recompute computed variables
#   make corpus             Full Phase 1 pipeline (padme only)
#   make corpus-handoff     Convert CSV→Feather for faster Phase 2 reads (optional)
#   make corpus-sync        Pull data from padme (doudou only)
#   make archive-manuscript Minimal package for Oeconomia reviewers
#   make archive-datapaper  Full pipeline package for data paper
#   make clean              Remove build outputs
#   make rebuild            Clean + rebuild everything

# ── Shared artifact-location interface (ticket 0237) ──────
# paths.mk holds the variable definitions (DERIVED, BIB, CSL, the per-doc
# *_INCLUDES and *_FIGS lists) shared between the analysis-side build (concern
# .mk at root) and the writing-side build (per-deliverable render .mk under
# deliverables/<x>/). Included FIRST so immediate (:=) uses below resolve.
-include paths.mk

# ── Paths ─────────────────────────────────────────────────
# data/ is split by dataflow phase (see .claude/rules/architecture.md § Data location):
#   data/catalogs/ (+ pool/ exports/ syllabi/) = Phase-1 corpus, DVC-managed.
#   data/derived/  = Phase-2 derived data, gitignored + regenerable.
# Python scripts resolve the same paths via utils.py (CATALOGS_DIR / DERIVED_TABLES_DIR).
# DERIVED, BIB, CSL now live in paths.mk (shared with the render workpackages).
DATA_DIR     := data/catalogs
CONFIG       := config/analysis.yaml
SRC         := deliverables/manuscript/manuscript.qmd

# Phase 1 artifact chain (the contract between phases)
UNIFIED     := $(DATA_DIR)/unified_works.csv
ENRICHED    := $(DATA_DIR)/enriched_works.csv
EXTENDED    := $(DATA_DIR)/extended_works.csv
REFINED     := $(DATA_DIR)/refined_works.csv
REFINED_EMB := $(DATA_DIR)/refined_embeddings.npz
REFINED_CIT := $(DATA_DIR)/refined_citations.csv

# Phase 2 derived data (regenerable, under data/derived/)
MOSTCITED   := $(DERIVED)/het_mostcited_50.csv

# Phase 1→2 handoff: Feather files for fast Phase 2 reads
REFINED_FTH := $(DATA_DIR)/refined_works.feather
REFINED_CIT_FTH := $(DATA_DIR)/refined_citations.feather

# ── Reproducibility ───────────────────────────────────────
# PYTHONHASHSEED=0  → deterministic dict/set iteration order
# SOURCE_DATE_EPOCH=0 → reproducible timestamps in PDF/PNG metadata
export PYTHONHASHSEED := 0
export SOURCE_DATE_EPOCH := 0

# ── Import source roots (ticket 0253) ─────────────────────
# Every script invocation resolves flat module names (from utils import …,
# import openalex_corpus) via two relative source roots, so an entry point keeps
# working after it moves into a scripts/<phase>/ subdir. `scripts` carries the
# pipeline modules; `libs/openalex-corpus/src` carries the openalex_corpus
# package as source (its non-editable wheel is retired). Exported once here so
# every recipe shell — and every subprocess a Make-invoked pytest spawns —
# inherits it. Mirrors [tool.pytest.ini_options] pythonpath. Prepended, so an
# ambient PYTHONPATH is preserved.
export PYTHONPATH := scripts:libs/openalex-corpus/src$(if $(PYTHONPATH),:$(PYTHONPATH),)

# ── Toolchain ─────────────────────────────────────────────
# Env policy: secrets sourced from project .env via uv --env-file;
# never via export KEY := $(shell ...) or command-line KEY=value.
#
# Named tool variables so invocations stay overridable and self-documenting.
# PATH export covers non-interactive shells (ssh, cron, systemd) where
# ~/.bashrc isn't sourced — uv lives in ~/.local/bin by default.
UV      ?= uv
UV_RUN  ?= $(UV) run $(if $(wildcard .env),--env-file .env,)
# Run Python through uv (via `python -m`, never the generated console scripts —
# their shebangs point at the building worktree and break when it is removed).
PYTHON  ?= $(UV_RUN) python
export PATH := $(HOME)/.local/bin:$(PATH)

# Pin the uv project environment to the symlink-resolved canonical path so a
# `uv sync` writes console-script shebangs (bin/pytest, bin/dvc, ...) naming the
# stable shared interpreter, not the throwaway worktree whose sync last ran
# (ticket 0158). realpath turns this worktree's `.venv` symlink into its /data
# target; on a machine with a real local .venv it is a harmless no-op. Empty
# (no .venv yet) → unexported, so uv falls back to its default discovery.
UV_PROJECT_ENVIRONMENT := $(realpath .venv)
ifneq ($(UV_PROJECT_ENVIRONMENT),)
export UV_PROJECT_ENVIRONMENT
endif

# ── Modular Makefile includes (Phase-2 concern .mk only) ─────
# The per-deliverable render .mk (Phase 3) are NOT included here: `make papers`
# calls them via `$(MAKE) -f deliverables/<x>/<x>.mk` so the render process never
# parses these Phase-2 rules (ticket 0237).
-include scripts/analysis/divergence.mk
-include scripts/analysis/multilayer-detection.mk
-include scripts/analysis/zoo-figures.mk
-include scripts/analysis/venues.mk
-include scripts/analysis/separation.mk
-include scripts/analysis/network-limitations.mk

# ── Quarto ───────────────────────────────────────────────
# The per-document include sets (*_INCLUDES) and figure sets (*_FIGS) live in
# paths.mk, shared with the render workpackages. NCC_FIGS is analysis-only.

NCC_FIGS        := deliverables/_shared/figures/fig_ncc_divergence.png \
                   deliverables/_shared/figures/fig_ncc_core_comparison.png \
                   deliverables/_shared/figures/fig_ncc_bimodality.png \
                   deliverables/_shared/figures/fig_ncc_alluvial.png

# Zoo figures (ZOO_SCHEMATICS / ZOO_RESULT_FIGS, defined in paths.mk) are
# deliberately excluded from ALL_FIGS / make figures: plot scripts not yet wired.
# Add them to ALL_FIGS when plot_schematic_*.py and plot_zoo_results.py have targets.
ALL_FIGS := $(MANUSCRIPT_FIGS) $(DATAPAPER_FIGS) $(MULTILAYER_FIGS) $(TECHREP_FIGS) $(NCC_FIGS)

# ── Default target ────────────────────────────────────────
.PHONY: all setup manuscript papers corpus-report technical-report data-paper multilayer-detection multilayer-techrep zoo figures figures-manuscript figures-datapaper figures-companion figures-techrep figures-ncc stats check check-package check-fast lint test-durations venv-canonicalize smoke benchmark determinism-check regression regression-update audit-pdf-content check-corpus check-manuscript-data data corpus corpus-sync corpus-discover corpus-enrich corpus-extend corpus-filter corpus-align corpus-filter-all corpus-tables corpus-validate deploy-corpus clean rebuild archive-analysis archive-manuscript archive-datapaper analysis-figures analysis-tables analysis-stats manuscript-render manuscript-figures datapaper-render datapaper-figures corpus-handoff

.DEFAULT_GOAL := manuscript

all: manuscript papers

# ═══════════════════════════════════════════════════════════
# PHASE 1 — Corpus Building (slow, API-dependent, run rarely)
# ═══════════════════════════════════════════════════════════
#
# Artifact chain (the contract between sub-phases):
#   1a unified_works.csv      raw merged catalog, no filtering
#   1b enriched_works.csv     metadata/abstract/DOI enrichment applied
#      + citations.csv        full citation graph (cache)
#      + embeddings.npz       sentence embeddings (cache)
#   1c extended_works.csv     diagnostic flags/protection columns added, no rows removed
#   1d refined_works.csv      keep/remove policy applied; corpus_audit.csv produced
#   1e refined_embeddings.npz embedding vectors aligned 1:1 with refined_works.csv rows
#      refined_citations.csv  citation edges restricted to refined DOIs (Phase 2 canonical)
#
# Phase 2 scripts read ONLY: refined_works.csv, refined_embeddings.npz, refined_citations.csv.
# (embeddings.npz and citations.csv are enrichment caches, not Phase 2 inputs.)
# het_mostcited_50.csv is a Phase 2 derived product (build_het_core.py).

# ── DVC workflow ─────────────────────────────────────────
#
# Phase 1 data is managed by DVC (see dvc.yaml for the pipeline DAG).
# DVC tracks file hashes: it skips stages whose inputs are unchanged.
#
# Padme is the data authority. Run the pipeline on padme, pull on doudou.
#
# On padme (pipeline run):
#   make corpus                      # dvc repro + push + commit lock
#
# On doudou (sync only):
#   make corpus-sync                 # git pull + dvc pull
#   make figures && make manuscript  # Phase 2 + 3 (no DVC needed)

# Full pipeline — run on padme only (GPU, API access).
# After dvc repro + push, auto-commits dvc.lock if it's the only change.
corpus:
	bash scripts/run_corpus_pipeline.sh

# Sync data from padme — run on doudou (never pushes).
corpus-sync:
	@[ "$$(hostname)" != "padme" ] || { echo "error: use 'make corpus' on padme, not corpus-sync."; exit 1; }
	git pull
	$(UV_RUN) dvc pull --force

# Populate this worktree's DVC data from the local cache (no network).
# Worktree creation no longer does this eagerly (it timed out copying ~1.7 GB);
# run this on demand when a worktree actually needs the corpus data. Use
# corpus-sync instead to also fetch from the padme remote.
data:
	$(UV_RUN) dvc checkout

# Individual stage aliases.
corpus-discover:
	$(UV_RUN) dvc repro catalog_merge

corpus-enrich:
	$(UV_RUN) dvc repro enrich_dois enrich_abstracts enrich_language summarize_abstracts join_enrichments enrich_citations qa_citations enrich_embeddings

corpus-extend:
	$(UV_RUN) dvc repro extend

corpus-filter:
	$(UV_RUN) dvc repro filter

corpus-filter-all:
	$(UV_RUN) dvc repro extend filter

corpus-align:
	$(UV_RUN) dvc repro align

# Upload artifacts to the DVC remote (padme).
deploy-corpus:
	$(UV_RUN) dvc push

# ── Corpus diagnostics (Phase 1 — reads enrichment caches) ──
deliverables/_shared/tables/qa_citations_report.json: scripts/qa/qa_citations.py scripts/qa/_crossref_qa.py scripts/utils.py \
		$(DATA_DIR)/citations.csv
	$(PYTHON) $< --output $@

# ═══════════════════════════════════════════════════════════
# PHASE 2 — Analysis & Figures (fast, deterministic, run often)
# ═══════════════════════════════════════════════════════════
# Inputs: Phase 1 outputs only (refined_works.csv, refined_embeddings.npz, refined_citations.csv).
# het_mostcited_50.csv is produced within Phase 2 by build_het_core.py.
# Outputs: deliverables/_shared/figures/*.png, deliverables/_shared/tables/*.csv, deliverables/<x>/*-vars.yml

# Gate for Phase 2: verify all three contract files exist.
# If any is missing, suggest dvc pull (data not synced) or make corpus (not built).
# Phase 1→2 handoff: convert CSV contract files to Feather for fast Phase 2 reads.
# Embeddings stay as .npz (already binary). One conversion pass (~5s) replaces
# ~48s of repeated CSV parsing across 25 Phase 2 script invocations.
$(REFINED_FTH): $(REFINED)
	$(PYTHON) -c "import pandas as pd; pd.read_csv('$<').to_feather('$@')"

$(REFINED_CIT_FTH): $(REFINED_CIT)
	$(PYTHON) -c "import pandas as pd; pd.read_csv('$<', low_memory=False).to_feather('$@')"

corpus-handoff: check-corpus $(REFINED_FTH) $(REFINED_CIT_FTH)

check-corpus:
	@ok=true; \
	for f in "$(REFINED)" "$(REFINED_EMB)" "$(REFINED_CIT)"; do \
		test -f "$$f" || { echo "MISSING: $$f"; ok=false; }; \
	done; \
	$$ok || { echo "Run '$(UV_RUN) dvc pull' to sync data, or 'make corpus' to rebuild."; exit 1; }

# Lighter gate for manuscript-only builds (no citations needed).
check-manuscript-data:
	@ok=true; \
	for f in "$(REFINED)" "$(REFINED_EMB)"; do \
		test -f "$$f" || { echo "MISSING: $$f"; ok=false; }; \
	done; \
	$$ok || { echo "Run '$(UV_RUN) dvc pull' to sync data, or 'make corpus' to rebuild."; exit 1; }

corpus-validate: $(REFINED)
	$(PYTHON) -m pytest tests/test_corpus_acceptance.py -v -s --tb=long

# ── Corpus reporting (Phase 2 — reads only refined data) ──
deliverables/_shared/tables/tab_citation_coverage.md: scripts/figures/export_citation_coverage.py scripts/utils.py $(REFINED)
	$(PYTHON) $< --output $@

deliverables/_shared/tables/tab_reference_counts.csv: scripts/analysis/compute_reference_counts.py scripts/utils.py $(REFINED) $(REFINED_CIT)
	$(PYTHON) $< --output $@

# Also reads the catalog_merge source catalogs discovered from dvc.yaml
# (read-only; not listed as prerequisites so a Phase-2 build never triggers
# Phase 1 — the catalogs are DVC-managed).
deliverables/_shared/tables/tab_dedup_error_estimates.csv: scripts/analysis/compute_dedup_error_estimates.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $@

deliverables/_shared/tables/tab_venues.md: scripts/figures/export_tab_venues.py scripts/utils.py $(REFINED) $(DERIVED)/tab_pole_papers.csv
	$(PYTHON) $< --output $@ --pole-papers $(DERIVED)/tab_pole_papers.csv

deliverables/_shared/tables/tab_corpus_sources.csv deliverables/_shared/tables/tab_corpus_sources.md &: scripts/figures/export_corpus_table.py scripts/utils.py $(REFINED)
	$(PYTHON) $< --output $@

deliverables/_shared/tables/tab_languages.md: scripts/figures/export_language_table.py scripts/utils.py $(ENRICHED)
	$(PYTHON) $< --output $@

# Variables table for the data paper (ticket 0279) — rendered from the deposit
# column contract, no corpus data needed.
deliverables/_shared/tables/tab_variables.md: scripts/figures/export_variables_table.py scripts/_deposit_variables.py
	$(PYTHON) $< --output $@

# Codebook / data dictionary for the Zenodo package (ticket 0287, R1-19) —
# missingness is measured on the real corpus, so this needs Phase-1 data.
deliverables/_shared/tables/codebook.md: scripts/figures/export_codebook.py scripts/_deposit_variables.py $(EXTENDED)
	$(PYTHON) $< --output $@

corpus-tables: deliverables/_shared/tables/tab_corpus_sources.csv deliverables/_shared/tables/tab_corpus_sources.md \
               deliverables/_shared/tables/tab_citation_coverage.md \
               deliverables/_shared/tables/tab_reference_counts.csv \
               deliverables/_shared/tables/tab_languages.md \
               deliverables/_shared/tables/tab_variables.md

# ── Statistics (computed from pipeline outputs) ──────────
# manuscript-vars.yml is pinned to v1.0 values — not auto-generated by compute_vars.py.
COMPUTED_STATS := deliverables/_shared/technical-report-vars.yml \
                  deliverables/data-paper/data-paper-vars.yml deliverables/multilayer/multilayer-detection-vars.yml

# Grouped target (&:) — one invocation writes all 3 files. Requires GNU Make >= 4.3.
$(COMPUTED_STATS) &: scripts/analysis/compute_vars.py scripts/utils.py $(REFINED) \
		$(DERIVED)/tab_bimodality.csv $(DERIVED)/tab_bimodality_core.csv \
		$(DERIVED)/tab_axis_detection.csv \
		$(wildcard $(UNIFIED)) \
		$(wildcard $(DATA_DIR)/corpus_audit.csv) \
		$(wildcard $(DATA_DIR)/embeddings.npz) \
		$(wildcard $(REFINED_EMB)) \
		$(wildcard $(DATA_DIR)/citations.csv) \
		$(wildcard $(REFINED_CIT)) \
		$(wildcard deliverables/_shared/tables/qa_citations_report.json) \
		$(DERIVED)/global_map_direct.json
	$(PYTHON) $< --output $@

stats: $(COMPUTED_STATS)

# ── Tables (generated, included by Quarto) ──────────────

# Core subset → venues table
$(MOSTCITED): scripts/analysis/build_het_core.py scripts/utils.py $(REFINED) $(REFINED_CIT)
	$(PYTHON) $< --output $@

deliverables/_shared/tables/tab_core_venues_top10.md: scripts/figures/export_core_venues_markdown.py scripts/analysis/summarize_core_venues.py scripts/utils.py $(MOSTCITED)
	$(PYTHON) $< --output $@

# ── Figures ──────────────────────────────────────────────

# -- Manuscript (Oeconomia article) --
# Fig 1 (bars): corpus growth per year
deliverables/_shared/figures/fig_bars.png: scripts/figures/plot_fig1_bars.py scripts/plot_style.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $@

# Fig 1 v1 variant: restricted to submission corpus for manuscript stability
deliverables/_shared/figures/fig_bars_v1.png: scripts/figures/plot_fig1_bars.py scripts/plot_style.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $@ --v1-only

# Fig 2 (composition): frozen v1 archive data + corrected labels
deliverables/_shared/figures/fig_composition.png: scripts/figures/plot_fig2_composition.py scripts/plot_style.py scripts/utils.py $(CONFIG) \
		config/v1_tab_alluvial.csv config/v1_cluster_labels.json
	$(PYTHON) $< --output $@ --input config/v1_tab_alluvial.csv --labels config/v1_cluster_labels.json

# Fig 2 wide variant (2x3 landscape) for slides — same frozen data, --wide layout
deliverables/_shared/figures/fig_composition_wide.png: scripts/figures/plot_fig2_composition.py scripts/plot_style.py scripts/utils.py $(CONFIG) \
		config/v1_tab_alluvial.csv config/v1_cluster_labels.json
	$(PYTHON) $< --wide --output $@ --input config/v1_tab_alluvial.csv --labels config/v1_cluster_labels.json

# -- Data paper --
# Semantic clusters (computation only — no figures)
SEMANTIC_CLUSTERS := $(DERIVED)/semantic_clusters.csv

$(SEMANTIC_CLUSTERS): scripts/analysis/analyze_embeddings.py scripts/utils.py $(CONFIG) $(ENRICHED) $(DATA_DIR)/embeddings.npz
	$(PYTHON) $< --output $@

# Semantic UMAP maps (one parameterized plot script, 3 invocations)
deliverables/_shared/figures/fig_semantic.png: scripts/figures/plot_semantic.py scripts/utils.py $(SEMANTIC_CLUSTERS)
	$(PYTHON) $< --color-by cluster --output $@

deliverables/_shared/figures/fig_semantic_lang.png: scripts/figures/plot_semantic.py scripts/utils.py $(SEMANTIC_CLUSTERS)
	$(PYTHON) $< --color-by language --output $@

deliverables/_shared/figures/fig_semantic_period.png: scripts/figures/plot_semantic.py scripts/utils.py $(SEMANTIC_CLUSTERS)
	$(PYTHON) $< --color-by period --output $@

# -- Companion paper (quantitative) --
# Structural break tables (independent of clustering)
$(DERIVED)/tab_breakpoints.csv: scripts/analysis/compute_breakpoints.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $@

$(DERIVED)/tab_breakpoint_robustness.csv: scripts/analysis/compute_breakpoints.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $@ --robustness

# Clustering + alluvial flow tables — full corpus (companion paper, tech report)
$(DERIVED)/tab_alluvial.csv $(DERIVED)/cluster_labels.json \
$(DERIVED)/tab_core_shares.csv &: \
		scripts/analysis/compute_clusters.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $(DERIVED)/tab_alluvial.csv

# Clustering — v1 frozen from reproducibility archive (not re-clustered).
# KMeans is unstable to small corpus perturbations; re-clustering the v1
# subset produces different assignments. These checked-in files are the
# source of truth for manuscript Figure 2.
# To update: copy from the reproducibility archive and commit.

# Breakpoints figure
deliverables/_shared/figures/fig_breakpoints.png: \
		scripts/figures/plot_fig_breakpoints.py scripts/utils.py $(CONFIG) \
		$(DERIVED)/tab_breakpoints.csv $(DERIVED)/tab_breakpoint_robustness.csv \
		$(DERIVED)/tab_alluvial.csv
	$(PYTHON) $< --output $@ --input $(DERIVED)/tab_breakpoints.csv $(DERIVED)/tab_breakpoint_robustness.csv $(DERIVED)/tab_alluvial.csv

# Alluvial figure (static PNG)
deliverables/_shared/figures/fig_alluvial.png: \
		scripts/figures/plot_fig_alluvial.py scripts/utils.py $(CONFIG) \
		$(DERIVED)/tab_alluvial.csv $(DERIVED)/cluster_labels.json
	$(PYTHON) $< --output $@ --input $(DERIVED)/tab_alluvial.csv

# Alluvial figure (interactive HTML)
deliverables/_shared/figures/fig_alluvial.html: \
		scripts/figures/plot_alluvial_html.py scripts/utils.py $(CONFIG) \
		$(DERIVED)/tab_alluvial.csv $(DERIVED)/cluster_labels.json
	$(PYTHON) $< --output $@

# Period divergence curves
deliverables/_shared/figures/fig_breaks.png: scripts/figures/plot_fig2_breaks.py scripts/plot_style.py scripts/utils.py $(CONFIG) \
		$(DERIVED)/tab_breakpoints.csv
	$(PYTHON) $< --output $@ --input $(DERIVED)/tab_breakpoints.csv

# Bimodality tables (computation only — figures are separate targets below)
$(DERIVED)/tab_bimodality.csv $(DERIVED)/tab_axis_detection.csv \
$(DERIVED)/tab_pole_papers.csv &: \
		scripts/analysis/analyze_bimodality.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $(DERIVED)/tab_bimodality.csv

# Bimodality figures (each reads tab_pole_papers.csv)
deliverables/_shared/figures/fig_bimodality.png: scripts/figures/plot_bimodality.py scripts/utils.py \
		$(DERIVED)/tab_pole_papers.csv
	$(PYTHON) $< --output $@

deliverables/_shared/figures/fig_bimodality_lexical.png: scripts/figures/plot_bimodality_lexical.py scripts/utils.py \
		$(DERIVED)/tab_pole_papers.csv
	$(PYTHON) $< --output $@

deliverables/_shared/figures/fig_bimodality_keywords.png: scripts/figures/plot_bimodality_keywords.py scripts/utils.py \
		$(DERIVED)/tab_pole_papers.csv
	$(PYTHON) $< --output $@

# Seed-axis violin (core, manuscript figure)
deliverables/_shared/figures/fig_seed_axis_core.png: scripts/figures/plot_fig_seed_axis.py scripts/plot_style.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $@

# PCA scatter (unsupervised)
deliverables/_shared/figures/fig_pca_scatter.png: scripts/figures/plot_fig45_pca_scatter.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $@

# Citation genealogy: model (lineage table) then renderers
$(DERIVED)/tab_lineages.csv: scripts/analysis/analyze_genealogy.py scripts/utils.py $(CONFIG) \
		$(REFINED) $(REFINED_CIT) $(DERIVED)/tab_pole_papers.csv $(SEMANTIC_CLUSTERS)
	$(PYTHON) $< --output $@

deliverables/_shared/figures/fig_genealogy.png: scripts/figures/plot_genealogy.py scripts/utils.py $(CONFIG) \
		$(DERIVED)/tab_lineages.csv $(REFINED_CIT)
	$(PYTHON) $< --output $@

deliverables/_shared/figures/fig_genealogy.html: scripts/figures/plot_genealogy_html.py scripts/utils.py $(CONFIG) \
		$(DERIVED)/tab_lineages.csv $(REFINED_CIT)
	$(PYTHON) $< --output $@

# -- Technical report (robustness, variants, supplementary) --
# Core-only: structural break tables
$(DERIVED)/tab_breakpoints_core.csv: scripts/analysis/compute_breakpoints.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $@ --core-only

$(DERIVED)/tab_breakpoint_robustness_core.csv: scripts/analysis/compute_breakpoints.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $@ --robustness --core-only

# Core-only: clustering + alluvial flow tables
$(DERIVED)/tab_alluvial_core.csv $(DERIVED)/cluster_labels_core.json &: \
		scripts/analysis/compute_clusters.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $(DERIVED)/tab_alluvial_core.csv --core-only

# Core-only figures
deliverables/_shared/figures/fig_breakpoints_core.png: \
		scripts/figures/plot_fig_breakpoints.py scripts/utils.py $(CONFIG) \
		$(DERIVED)/tab_breakpoints_core.csv $(DERIVED)/tab_breakpoint_robustness_core.csv \
		$(DERIVED)/tab_alluvial_core.csv
	$(PYTHON) $< --output $@ --core-only --input $(DERIVED)/tab_breakpoints_core.csv $(DERIVED)/tab_breakpoint_robustness_core.csv $(DERIVED)/tab_alluvial_core.csv

deliverables/_shared/figures/fig_alluvial_core.png: \
		scripts/figures/plot_fig_alluvial.py scripts/utils.py $(CONFIG) \
		$(DERIVED)/tab_alluvial_core.csv $(DERIVED)/cluster_labels_core.json
	$(PYTHON) $< --output $@ --core-only --input $(DERIVED)/tab_alluvial_core.csv

# Bimodality core variant tables
$(DERIVED)/tab_bimodality_core.csv $(DERIVED)/tab_axis_detection_core.csv \
$(DERIVED)/tab_pole_papers_core.csv &: \
		scripts/analysis/analyze_bimodality.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $(DERIVED)/tab_bimodality_core.csv --core-only

# Bimodality core variant figures
deliverables/_shared/figures/fig_bimodality_core.png: scripts/figures/plot_bimodality.py scripts/utils.py \
		$(DERIVED)/tab_pole_papers_core.csv
	$(PYTHON) $< --core-only --output $@

deliverables/_shared/figures/fig_bimodality_lexical_core.png: scripts/figures/plot_bimodality_lexical.py scripts/utils.py \
		$(DERIVED)/tab_pole_papers_core.csv
	$(PYTHON) $< --core-only --output $@

deliverables/_shared/figures/fig_bimodality_keywords_core.png: scripts/figures/plot_bimodality_keywords.py scripts/utils.py \
		$(DERIVED)/tab_pole_papers_core.csv
	$(PYTHON) $< --core-only --output $@

# Pre-2007 co-citation traditions network
deliverables/_shared/figures/fig_traditions.png: scripts/figures/plot_fig_traditions.py scripts/plot_style.py scripts/utils.py $(CONFIG) $(REFINED) $(REFINED_CIT)
	$(PYTHON) $< --output $@

# Global citation-network map (ticket 0307, R1-14): compute meta-graph JSON,
# then render. Direct map = data-paper figure; co-citation map = companion
# artifact (committed, not embedded).
GLOBAL_MAP_DIRECT := $(DERIVED)/global_map_direct.json
GLOBAL_MAP_COCIT  := $(DERIVED)/global_map_cocitation.json

$(GLOBAL_MAP_DIRECT): scripts/analysis/analyze_global_map.py scripts/utils.py $(CONFIG) $(REFINED) $(REFINED_CIT)
	$(PYTHON) $< --method direct --output $@

$(GLOBAL_MAP_COCIT): scripts/analysis/analyze_global_map.py scripts/utils.py $(CONFIG) $(REFINED) $(REFINED_CIT)
	$(PYTHON) $< --method cocitation --output $@

deliverables/_shared/figures/fig_global_map_direct.png: scripts/figures/plot_fig_global_map.py \
		scripts/figures/_community_registry.py scripts/plot_style.py config/community_registry.yml $(GLOBAL_MAP_DIRECT)
	$(PYTHON) $< --input $(GLOBAL_MAP_DIRECT) --output $@

deliverables/_shared/figures/fig_global_map_cocitation.png: scripts/figures/plot_fig_global_map.py \
		scripts/figures/_community_registry.py scripts/plot_style.py config/community_registry.yml $(GLOBAL_MAP_COCIT)
	$(PYTHON) $< --input $(GLOBAL_MAP_COCIT) --output $@

# Co-citation communities (compute: community assignments + summary table)
COMMUNITIES := $(DERIVED)/communities.csv
$(COMMUNITIES): scripts/analysis/analyze_cocitation.py scripts/utils.py $(REFINED_CIT)
	$(PYTHON) $< --output $@

# Co-citation communities (plot: network figure)
deliverables/_shared/figures/fig_communities.png: scripts/figures/plot_cocitation.py scripts/utils.py $(COMMUNITIES) $(REFINED_CIT)
	$(PYTHON) $< --output $@ --input $(COMMUNITIES)

# KDE supplementary
deliverables/_shared/figures/fig_kde.png: scripts/figures/plot_figS_kde.py scripts/plot_style.py scripts/utils.py $(CONFIG) \
		$(DERIVED)/tab_pole_papers.csv
	$(PYTHON) $< --output $@

# Lexical TF-IDF table (diagnostic, not in manuscript)
$(DERIVED)/tab_lexical_tfidf.csv: scripts/analysis/compute_lexical.py scripts/utils.py $(REFINED) \
		$(DERIVED)/tab_breakpoint_robustness.csv
	$(PYTHON) $< --output $@

# Multilingual epistemic structure (exploratory JSON report)
deliverables/_shared/tables/multilingual_report.json: scripts/analysis/analyze_multilingual.py scripts/utils.py \
		scripts/analysis/build_het_core.py $(REFINED) $(REFINED_EMB) $(REFINED_CIT) $(SEMANTIC_CLUSTERS)
	$(PYTHON) $< --output $@

# K-sensitivity table
$(DERIVED)/tab_k_sensitivity.csv: scripts/analysis/compute_breakpoints.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $@ --k-sensitivity

# K-sensitivity figure
deliverables/_shared/figures/fig_k_sensitivity.png: scripts/figures/plot_fig_k_sensitivity.py $(CONFIG) \
		$(DERIVED)/tab_k_sensitivity.csv
	$(PYTHON) $< --output $@

# Lexical TF-IDF figures (one per detected break year; output filenames are
# dynamic, so we use a sentinel file to track freshness).
.lexical_tfidf.stamp: scripts/figures/plot_fig_lexical_tfidf.py scripts/plot_style.py $(CONFIG) \
		$(DERIVED)/tab_lexical_tfidf.csv
	$(PYTHON) $< --output $@ --input $(DERIVED)/tab_lexical_tfidf.csv

# DVC pipeline DAG (data paper)
deliverables/_shared/figures/fig_dag.png: scripts/figures/plot_fig_dag.py scripts/plot_style.py $(CONFIG) dvc.yaml
	$(PYTHON) $< --output $@

# -- NCC Analysis (Nature Climate Change) --

# Censor-gap k=2 breakpoint tables (intermediate for NCC figure a)
$(DERIVED)/tab_breakpoints_censor2.csv: scripts/analysis/compute_breakpoints.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $@ --censor-gap 2

$(DERIVED)/tab_breakpoint_robustness_censor2.csv: scripts/analysis/compute_breakpoints.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $@ --robustness --censor-gap 2

# NCC Figure (a): Divergence with 2009 peak (baseline vs censor-gap k=2)
deliverables/_shared/figures/fig_ncc_divergence.png: \
		scripts/figures/plot_ncc_divergence.py scripts/utils.py $(CONFIG) \
		$(DERIVED)/tab_breakpoints.csv \
		$(DERIVED)/tab_breakpoints_censor2.csv \
		$(DERIVED)/tab_breakpoint_robustness_censor2.csv
	$(PYTHON) $< --output $@ --input $(DERIVED)/tab_breakpoints.csv $(DERIVED)/tab_breakpoints_censor2.csv $(DERIVED)/tab_breakpoint_robustness_censor2.csv

# NCC Figure (b): Core vs full corpus comparison panel
deliverables/_shared/figures/fig_ncc_core_comparison.png: \
		scripts/figures/plot_ncc_core_comparison.py scripts/utils.py $(CONFIG) \
		$(DERIVED)/tab_breakpoints.csv $(DERIVED)/tab_breakpoint_robustness.csv \
		$(DERIVED)/tab_alluvial.csv \
		$(DERIVED)/tab_breakpoints_core.csv $(DERIVED)/tab_breakpoint_robustness_core.csv \
		$(DERIVED)/tab_alluvial_core.csv
	$(PYTHON) $< --output $@

# NCC Figure (c): Bimodality KDE with period decomposition
deliverables/_shared/figures/fig_ncc_bimodality.png: \
		scripts/figures/plot_ncc_bimodality.py scripts/utils.py $(CONFIG) \
		$(DERIVED)/tab_pole_papers.csv
	$(PYTHON) $< --output $@

# NCC Figure (d): Alluvial diagram (NCC format)
deliverables/_shared/figures/fig_ncc_alluvial.png: \
		scripts/figures/plot_ncc_alluvial.py scripts/utils.py $(CONFIG) \
		$(DERIVED)/tab_alluvial.csv $(DERIVED)/cluster_labels.json
	$(PYTHON) $< --output $@ --input $(DERIVED)/tab_alluvial.csv

figures-manuscript: corpus-handoff $(MANUSCRIPT_FIGS)
figures-datapaper:  corpus-handoff $(DATAPAPER_FIGS)
figures-companion:  corpus-handoff $(MULTILAYER_FIGS)
figures-techrep:    corpus-handoff $(TECHREP_FIGS)
figures-ncc:        corpus-handoff $(NCC_FIGS)
figures: corpus-handoff $(ALL_FIGS) corpus-tables

# ── Namespaced aliases (Phase 2) ────────────────────────
# Organized by concern for discoverability: make analysis-<tab>
analysis-figures: figures
analysis-tables: corpus-tables $(MOSTCITED)
analysis-stats: stats

# ═══════════════════════════════════════════════════════════
# PHASE 3 — Render (Quarto → PDF/DOCX)
# ═══════════════════════════════════════════════════════════

# Each deliverable owns a Phase-3 render .mk beside its source under
# deliverables/<x>/ (ticket 0237). `manuscript` and `papers` invoke them via
# `$(MAKE) -f` — a separate make process that parses only the render .mk (+
# paths.mk), never these Phase-2 rules. So `papers` is Phase-3 only: no
# check-corpus, no uv run, rendering from artifacts a prior `make analysis` left
# on disk. Each render .mk depends only on committed/handoff artifacts, so a
# deliverable builds clean-room with no corpus data. Quarto's single-file render
# writes the PDF NEXT TO its source (it ignores a project output-dir), so the
# Make target IS the output file and Make verifies it (tickets 0131, 0226, 0237).

manuscript:
	$(MAKE) -f deliverables/manuscript/manuscript.mk deliverables/manuscript/manuscript.pdf deliverables/manuscript/manuscript.docx

papers: corpus-report technical-report data-paper multilayer-detection multilayer-techrep zoo

corpus-report:
	$(MAKE) -f deliverables/corpus-report/corpus-report.mk deliverables/corpus-report/corpus-report.pdf

technical-report:
	$(MAKE) -f deliverables/technical-report/technical-report.mk deliverables/technical-report/technical-report.pdf

data-paper:
	$(MAKE) -f deliverables/data-paper/data-paper.mk deliverables/data-paper/data-paper.pdf

multilayer-detection:
	$(MAKE) -f deliverables/multilayer/multilayer.mk deliverables/multilayer/multilayer-detection.pdf

multilayer-techrep:
	$(MAKE) -f deliverables/multilayer/multilayer.mk deliverables/multilayer/multilayer-detection-techrep.pdf

zoo:
	$(MAKE) -f deliverables/zoo/zoo.mk deliverables/zoo/breakpoint-detect-method-zoo.pdf

# ── Namespaced aliases (Phase 3) ────────────────────────
manuscript-render: manuscript
manuscript-figures: figures-manuscript

datapaper-render: data-paper
datapaper-figures: figures-datapaper

# ── Phase 4a — analysis archive (packages Phase 2 outputs) ─
# Data + scripts: reviewers verify figures/tables are reproducible.
#   tar xzf archive.tar.gz && cd ... && uv sync && make
SHELL            := /bin/bash
ANALYSIS_OUTPUTS := deliverables/_shared/figures/fig_bars_v1.png \
                    deliverables/_shared/figures/fig_composition.png \
                    deliverables/_shared/tables/tab_venues.md \
                    $(DERIVED)/tab_alluvial.csv \
                    $(DERIVED)/tab_core_shares.csv \
                    $(DERIVED)/tab_bimodality.csv \
                    $(DERIVED)/tab_axis_detection.csv \
                    $(DERIVED)/tab_pole_papers.csv \
                    $(DERIVED)/cluster_labels.json

archive-analysis: check-manuscript-data $(ANALYSIS_OUTPUTS)
	bash build/build_analysis_archive.sh

# ── Phase 4b — manuscript archive (packages Phase 3 outputs) ─
# Pre-built figures + content: reviewers verify PDF renders.
# No Python needed — only Quarto + XeLaTeX.
#   tar xzf archive.tar.gz && cd ... && make

archive-manuscript: $(MANUSCRIPT_FIGS) $(MANUSCRIPT_INCLUDES) deliverables/manuscript/manuscript-vars.yml manuscript
	bash build/build_manuscript_archive.sh

# ── Phase 4c — data paper archive (full pipeline) ─────────
# Complete reproducibility package: all corpus-building scripts, DVC pipeline,
# pool data, caches.  Reviewers can verify with:
#   tar xzf archive.tar.gz && cd ... && uv sync && dvc repro
archive-datapaper: check-corpus corpus-tables figures-datapaper
	bash build/build_datapaper_archive.sh

# Repair shared-env console-script shebangs (ticket 0158). uv only rewrites them
# on an actual sync, so scripts that a removed worktree left behind keep its
# dangling interpreter (e.g. `dvc`, which has no `python -m` entry point). This
# rewrites every bin/ python shebang to the canonical resolved interpreter.
# Idempotent; a no-op where .venv is absent or already canonical.
venv-canonicalize:
	@v=$(realpath .venv); \
	if [ -n "$$v" ] && [ -x "$$v/bin/python3" ]; then \
	  for f in "$$v"/bin/*; do \
	    [ -f "$$f" ] || continue; \
	    head -1 "$$f" | grep -Eq '^#!.*/python[0-9.]*$$' || continue; \
	    head -1 "$$f" | grep -qxF "#!$$v/bin/python3" && continue; \
	    sed -i "1s|^#!.*|#!$$v/bin/python3|" "$$f"; \
	  done; \
	fi

# ── All checks (tests) ───────────────────────────────────
# The libs/openalex-corpus path package ships its own 25-test suite that root
# `pytest tests/` never collects (norecursedirs=["libs"]). Run it explicitly so
# host CI gates it. Pure-logic / mocked-HTTP — belongs in the fast tier too.
check-package: | venv-canonicalize
	$(PYTHON) -m pytest libs/openalex-corpus/tests -v --tb=short

check: check-package | venv-canonicalize
	$(PYTHON) -m pytest tests/ -v --tb=short -n 4

# Fast inner loop: pure-Python logic only. Deselects slow (network / real data /
# heavy numerical dep / heavy compute), integration (subprocess / sleep), and
# adherence (lint — ruff/mypy/hygiene, run via `make lint`). Ticket 0214.
check-fast: check-package | venv-canonicalize
	$(PYTHON) -m pytest tests/ -v --tb=short -m "not slow and not integration and not adherence" -n 4

# Lint / rule-enforcement tier (ruff, mypy, hygiene, contracts). Run alongside
# tests, not inside the inner loop — a warm mypy cache makes it ~1s. Ticket 0214.
lint: | venv-canonicalize
	$(PYTHON) -m pytest tests/ --tb=short -m adherence -n 4

# Record per-test durations for the fast-path ratchet (ticket 0216) into the
# gitignored .test_durations.json. Serial (-n0) and opt-in so timings reflect
# true per-test cost, not xdist contention. Run this to refresh the data the
# ratchet (test_fast_path_budget.py, adherence tier) checks on the next run.
# --continue-on-collection-errors: a base (non-corpus) env may lack an optional
# dep (e.g. bibtexparser), which hard-stops collection of one module; the
# recorder is best-effort and should still time every collectable fast-path test.
test-durations: | venv-canonicalize
	RECORD_TEST_DURATIONS=1 $(PYTHON) -m pytest tests/ --tb=short \
		-m "not slow and not integration and not adherence" \
		-p no:xdist -q --continue-on-collection-errors

# PDF content audit: does each docs/articles/*.pdf match its bib title?
# Author-run, human-verified — NOT wired into check/check-fast: scanned PDFs have
# no extractable text, so low scores are HUMAN-eyeball flags, never a hard gate.
# Reads PDFs from the main checkout (they are gitignored, absent from worktrees).
audit-pdf-content:
	$(PYTHON) scripts/qa/qa_pdf_content.py --output data/derived/pdf_content_audit.csv

# Smoke pipeline: run Phase 2 on a 100-row fixture (no DVC pull needed, <30s).
# Exercises: compute_breakpoints, compute_clusters, plot_fig1_bars.
smoke:
	$(PYTHON) -m pytest tests/test_smoke_pipeline.py -v --tb=short

# Determinism check: run figure scripts twice on smoke data, diff outputs.
# Catches unseeded randomness, leaking timestamps, floating-point non-determinism.
determinism-check:
	$(PYTHON) -m pytest tests/test_determinism.py -v --tb=short

# Regression hashes: compare Phase 2 output hashes against golden baseline.
# Runs as pytest (one test per script, module-scoped fixture = scripts run once).
#   make regression          — check against golden baseline
#   make regression-update   — regenerate golden baseline (after intentional change)
regression:
	$(PYTHON) -m pytest tests/test_regression.py -v --tb=short -m integration -k "test_regression_"

regression-update:
	$(PYTHON) scripts/analysis/compute_regression_hashes.py --update-golden

# ── Benchmarking ─────────────────────────────────────────
# Record wall time + peak RSS per Phase 2 target.
# Output: benchmarks/timings.jsonl (one JSON line per target).
BENCH := scripts/time_target.sh
BENCH_OUT := benchmarks/timings.jsonl

benchmark: check-corpus
	@mkdir -p benchmarks
	$(BENCH) compute_breakpoints $(BENCH_OUT) $(PYTHON) scripts/analysis/compute_breakpoints.py --output $(DERIVED)/tab_breakpoints.csv
	$(BENCH) compute_clusters $(BENCH_OUT) $(PYTHON) scripts/analysis/compute_clusters.py --output $(DERIVED)/tab_alluvial.csv
	$(BENCH) analyze_bimodality $(BENCH_OUT) $(PYTHON) scripts/analysis/analyze_bimodality.py --output $(DERIVED)/tab_bimodality.csv
	$(BENCH) plot_fig1_bars $(BENCH_OUT) $(PYTHON) scripts/figures/plot_fig1_bars.py
	@echo "Benchmark results: $(BENCH_OUT)"

# ── Setup (run once after cloning) ───────────────────────
setup:
	git config core.hooksPath .githooks
	@echo "Hooks activated (.githooks/pre-commit, .githooks/post-checkout)"

# ── Housekeeping ─────────────────────────────────────────
clean:
	rm -rf deliverables/*/*.pdf deliverables/*/*.docx deliverables/*/*_files deliverables/*/.quarto

rebuild: clean all
