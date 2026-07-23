# paths.mk — shared artifact-location interface between build phases (ticket 0237).
#
# Variable definitions ONLY (zero recipes). This file is the thin contract that
# lets the analysis-side build (Phase 2, concern .mk at root) and the writing-side
# build (Phase 3, per-deliverable render .mk under deliverables/<x>/) agree on
# where artifacts live without either triggering the other. -include'd FIRST by
# the root Makefile and by every per-deliverable render .mk.

# ── Phase-2 derived-data root ─────────────────────────────
DERIVED := data/derived/tables

# ── Shared bibliography ───────────────────────────────────
BIB := deliverables/_shared/bibliography/main.bib
CSL := deliverables/_shared/bibliography/oeconomia.csl

# ── Per-document include sets ─────────────────────────────
# Each render rule depends on its own doc's includes. Since 0226 every deliverable
# is a folder-scoped Quarto project, so a render needs only its own includes — not
# the union of all docs (the retired PROJECT_INCLUDES model).
MANUSCRIPT_INCLUDES := deliverables/_shared/tables/tab_venues.md

# corpus-report.qmd {{< include >}} directives (authored by grepping the .qmd).
CORPUS_REPORT_INCLUDES := deliverables/_shared/_includes/corpus-construction.md \
		deliverables/_shared/_includes/corpus-enrichment.md \
		deliverables/_shared/_includes/corpus-filtering.md \
		deliverables/_shared/tables/tab_corpus_sources.md \
		deliverables/_shared/_includes/metadata-quality.md \
		deliverables/_shared/_includes/embedding-quality.md \
		deliverables/_shared/_includes/citation-quality.md \
		deliverables/_shared/tables/tab_languages.md \
		deliverables/_shared/_includes/core-vs-full-definition.md \
		deliverables/_shared/_includes/reproducibility.md \
		deliverables/_shared/_includes/annex-crossencoder.md \
		deliverables/_shared/_includes/teaching-convergence.md

TECHREP_INCLUDES := deliverables/_shared/_includes/corpus-construction.md \
		deliverables/_shared/_includes/corpus-enrichment.md \
		deliverables/_shared/_includes/corpus-filtering.md \
		deliverables/_shared/_includes/core-vs-full.md \
		deliverables/_shared/_includes/structural-breaks.md \
		deliverables/_shared/_includes/alluvial-diagram.md \
		deliverables/_shared/_includes/bimodality-analysis.md \
		deliverables/_shared/_includes/pca-scatter.md \
		deliverables/_shared/_includes/citation-genealogy.md \
		deliverables/_shared/_includes/citation-quality.md \
		deliverables/_shared/_includes/reproducibility.md \
		deliverables/_shared/tables/tab_citation_coverage.md

DATAPAPER_INCLUDES := deliverables/_shared/_includes/corpus-construction.md \
		deliverables/_shared/_includes/corpus-filtering.md \
		deliverables/_shared/_includes/embedding-generation.md \
		deliverables/_shared/_includes/reproducibility.md \
		deliverables/_shared/tables/tab_corpus_sources.md \
		deliverables/_shared/tables/tab_languages.md \
		deliverables/_shared/tables/tab_variables.md

MULTILAYER_INCLUDES := deliverables/_shared/_includes/embedding-generation.md \
		deliverables/_shared/_includes/structural-breaks.md \
		deliverables/_shared/_includes/alluvial-diagram.md \
		deliverables/_shared/_includes/bimodality-analysis.md \
		deliverables/_shared/_includes/pca-scatter.md \
		deliverables/_shared/_includes/core-vs-full.md

# Technical supplement to the multilayer paper (ticket 0096).
MULTILAYER_TECHREP_INCLUDES := \
	deliverables/_shared/_includes/techrep/overview.md \
	deliverables/_shared/_includes/techrep/zscore.md \
	deliverables/_shared/_includes/techrep/null-model.md \
	deliverables/_shared/_includes/zoo/S2_energy.md \
	deliverables/_shared/_includes/zoo/L1_js.md \
	deliverables/_shared/_includes/zoo/G9_community.md \
	deliverables/_shared/_includes/zoo/G2_spectral.md \
	deliverables/_shared/_includes/zoo/C2ST_embedding.md \
	deliverables/_shared/_includes/zoo/C2ST_lexical.md

# Method-zoo include tree: one composer + 18 per-method entries.
# Used by breakpoint-detect-method-zoo.qmd.
ZOO_INCLUDES := deliverables/_shared/_includes/techrep/overview.md \
		deliverables/_shared/_includes/techrep/zscore.md \
		deliverables/_shared/_includes/techrep/null-model.md \
		deliverables/_shared/_includes/techrep-zoo.md \
		deliverables/_shared/_includes/zoo/S1_mmd.md \
		deliverables/_shared/_includes/zoo/S2_energy.md \
		deliverables/_shared/_includes/zoo/S3_sliced_wasserstein.md \
		deliverables/_shared/_includes/zoo/S4_frechet.md \
		deliverables/_shared/_includes/zoo/C2ST_embedding.md \
		deliverables/_shared/_includes/zoo/L1_js.md \
		deliverables/_shared/_includes/zoo/L2_ntr.md \
		deliverables/_shared/_includes/zoo/L3_term_burst.md \
		deliverables/_shared/_includes/zoo/C2ST_lexical.md \
		deliverables/_shared/_includes/zoo/G1_pagerank.md \
		deliverables/_shared/_includes/zoo/G2_spectral.md \
		deliverables/_shared/_includes/zoo/G3_coupling_age.md \
		deliverables/_shared/_includes/zoo/G4_cross_tradition.md \
		deliverables/_shared/_includes/zoo/G5_pref_attachment.md \
		deliverables/_shared/_includes/zoo/G6_entropy.md \
		deliverables/_shared/_includes/zoo/G7_disruption.md \
		deliverables/_shared/_includes/zoo/G8_betweenness.md \
		deliverables/_shared/_includes/zoo/G9_community.md

# ── Per-document figure sets ─────────────────────────────
# Artifact-file lists. A render rule lists these as plain file prerequisites; the
# Phase-2 rules that PRODUCE them live in the concern .mk (root), not here.
MANUSCRIPT_FIGS := deliverables/_shared/figures/fig_bars_v1.png deliverables/_shared/figures/fig_composition.png deliverables/_shared/figures/fig_breaks.png

DATAPAPER_FIGS  := deliverables/_shared/figures/fig_bars.png deliverables/_shared/figures/fig_dag.png \
                   deliverables/_shared/figures/fig_global_map_direct.png \
                   deliverables/_shared/figures/fig_global_map_cocitation.png

MULTILAYER_FIGS  := deliverables/_shared/figures/fig_breakpoints.png deliverables/_shared/figures/fig_alluvial.png \
                   deliverables/_shared/figures/fig_breaks.png \
                   deliverables/_shared/figures/fig_bimodality.png \
                   deliverables/_shared/figures/fig_seed_axis_core.png deliverables/_shared/figures/fig_pca_scatter.png \
                   deliverables/_shared/figures/fig_genealogy.png \
                   deliverables/_shared/figures/fig_companion_zseries.png \
                   deliverables/_shared/figures/fig_companion_heatmap.png \
                   deliverables/_shared/figures/fig_companion_terms.png \
                   deliverables/_shared/figures/fig_companion_community.png

TECHREP_FIGS    := deliverables/_shared/figures/fig_alluvial_core.png \
                   deliverables/_shared/figures/fig_bimodality_core.png \
                   deliverables/_shared/figures/fig_bimodality_lexical_core.png \
                   deliverables/_shared/figures/fig_bimodality_keywords_core.png \
                   deliverables/_shared/figures/fig_bimodality_lexical.png \
                   deliverables/_shared/figures/fig_bimodality_keywords.png \
                   deliverables/_shared/figures/fig_kde.png \
                   deliverables/_shared/figures/fig_traditions.png \
                   deliverables/_shared/figures/fig_communities.png \
                   deliverables/_shared/figures/fig_semantic.png \
                   deliverables/_shared/figures/fig_semantic_lang.png \
                   deliverables/_shared/figures/fig_semantic_period.png

# Method-zoo figures (17 schematics + 18 zoo result panels).
# schematic_C2ST.png serves both C2ST_embedding and C2ST_lexical, hence 17 schematics for 18 methods.
ZOO_SCHEMATICS := deliverables/_shared/figures/schematic_S1_mmd.png \
                  deliverables/_shared/figures/schematic_S2_energy.png \
                  deliverables/_shared/figures/schematic_S3_sliced_wasserstein.png \
                  deliverables/_shared/figures/schematic_S4_frechet.png \
                  deliverables/_shared/figures/schematic_C2ST.png \
                  deliverables/_shared/figures/schematic_L1_js.png \
                  deliverables/_shared/figures/schematic_L2_ntr.png \
                  deliverables/_shared/figures/schematic_L3_burst.png \
                  deliverables/_shared/figures/schematic_G1_pagerank.png \
                  deliverables/_shared/figures/schematic_G2_spectral.png \
                  deliverables/_shared/figures/schematic_G3_coupling_age.png \
                  deliverables/_shared/figures/schematic_G4_cross_tradition.png \
                  deliverables/_shared/figures/schematic_G5_pref_attachment.png \
                  deliverables/_shared/figures/schematic_G6_entropy.png \
                  deliverables/_shared/figures/schematic_G7_disruption.png \
                  deliverables/_shared/figures/schematic_G8_betweenness.png \
                  deliverables/_shared/figures/schematic_G9_community.png

ZOO_RESULT_FIGS := deliverables/_shared/figures/fig_zoo_S1_MMD.png \
                   deliverables/_shared/figures/fig_zoo_S2_energy.png \
                   deliverables/_shared/figures/fig_zoo_S3_sliced_wasserstein.png \
                   deliverables/_shared/figures/fig_zoo_S4_frechet.png \
                   deliverables/_shared/figures/fig_zoo_C2ST_embedding.png \
                   deliverables/_shared/figures/fig_zoo_C2ST_lexical.png \
                   deliverables/_shared/figures/fig_zoo_L1.png \
                   deliverables/_shared/figures/fig_zoo_L2.png \
                   deliverables/_shared/figures/fig_zoo_L3.png \
                   deliverables/_shared/figures/fig_zoo_G1_pagerank.png \
                   deliverables/_shared/figures/fig_zoo_G2_spectral.png \
                   deliverables/_shared/figures/fig_zoo_G3_coupling_age.png \
                   deliverables/_shared/figures/fig_zoo_G4_cross_tradition.png \
                   deliverables/_shared/figures/fig_zoo_G5_pref_attachment.png \
                   deliverables/_shared/figures/fig_zoo_G6_entropy.png \
                   deliverables/_shared/figures/fig_zoo_G7_disruption.png \
                   deliverables/_shared/figures/fig_zoo_G8_betweenness.png \
                   deliverables/_shared/figures/fig_zoo_G9_community.png
