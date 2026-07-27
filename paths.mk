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
#
# Each set is the doc's FULL include closure: the {{< include >}} directives in
# the .qmd plus everything they pull in transitively. Nested includes resolve
# against the ROOT document's directory, not the including file's — so a nested
# `../_shared/_includes/zoo/x.md` is reached from `deliverables/<doc>/`.
#
# These lists are the render rules' prerequisites, so a stale entry is not just a
# wrong answer to "what does this doc need?" — it makes the rule miss a real
# dependency and rebuild on a file the doc stopped including. Ticket 0359 found
# every list but MANUSCRIPT/MULTILAYER_TECHREP/ZOO drifted: the technical report
# declared eleven includes it had dropped and none of the 23 it composes.
# tests/test_deliverable_artifacts.py recomputes every closure from the .qmd
# files and fails on mismatch in both directions. Ticket 0290 landed a second
# guard of its own in parallel; the two were merged into that one file rather
# than left as two answers to one question.
MANUSCRIPT_INCLUDES := deliverables/_shared/tables/tab_venues.md

GIDE_INCLUDES := deliverables/_shared/tables/tab_venues_fr.md

CORPUS_REPORT_INCLUDES := deliverables/_shared/_includes/corpus-construction.md \
		deliverables/_shared/_includes/corpus-enrichment.md \
		deliverables/_shared/_includes/corpus-filtering.md \
		deliverables/_shared/tables/tab_corpus_sources.md \
		deliverables/_shared/_includes/metadata-quality.md \
		deliverables/_shared/_includes/embedding-quality.md \
		deliverables/_shared/_includes/citation-quality.md \
		deliverables/_shared/tables/tab_citation_coverage.md \
		deliverables/_shared/tables/tab_languages.md \
		deliverables/_shared/_includes/core-vs-full-definition.md \
		deliverables/_shared/_includes/reproducibility.md \
		deliverables/_shared/_includes/annex-crossencoder.md \
		deliverables/_shared/_includes/teaching-convergence.md

# Method-zoo include tree: one composer + 18 per-method entries. Shared by the
# technical report and the standalone zoo document, which compose it identically.
ZOO_TREE := deliverables/_shared/_includes/techrep-zoo.md \
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

# The technical report is the method-zoo document (rewritten under 0096/0226):
# four framing includes plus the composer and its 18 per-method entries. The
# corpus/analysis chapters it used to carry are gone (ticket 0290).
TECHREP_INCLUDES := deliverables/_shared/_includes/techrep/overview.md \
		deliverables/_shared/_includes/techrep/zscore.md \
		deliverables/_shared/_includes/techrep/null-model.md \
		deliverables/_shared/_includes/techrep/summary-of-findings.md \
		$(ZOO_TREE)

DATAPAPER_INCLUDES := deliverables/_shared/tables/tab_corpus_sources.md \
		deliverables/_shared/tables/tab_corpus_flow.md \
		deliverables/_shared/tables/tab_languages.md \
		deliverables/_shared/tables/tab_variables.md

# The multilayer paper composes no shared include — it carries its method and
# results sections inline (guarded by
# tests/test_multilayer_detection_sections.py::test_no_old_method_includes) plus
# its five companion figures (MULTILAYER_FIGS, which the render rule takes in
# this variable's place). Until 0359 it declared six top-level includes it had
# stopped composing, all of them in the orphan set ticket 0290 audits.
MULTILAYER_INCLUDES :=

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

# breakpoint-detect-method-zoo.qmd: three framing includes + the shared zoo tree.
ZOO_INCLUDES := deliverables/_shared/_includes/techrep/overview.md \
		deliverables/_shared/_includes/techrep/zscore.md \
		deliverables/_shared/_includes/techrep/null-model.md \
		$(ZOO_TREE)

# ── Per-document figure sets ─────────────────────────────
# Artifact-file lists. A render rule lists these as plain file prerequisites; the
# Phase-2 rules that PRODUCE them live in the concern .mk (root), not here.
#
# A figure belongs in the variable of the deliverable that EMBEDS it — that is
# the question a reader comes here to answer (ticket 0359). Two markers keep the
# answer honest, both enforced by tests/test_deliverable_artifacts.py:
#   `# not-embedded: <file>.png — <reason>`  built on purpose, embedded nowhere
#   ORPHANED_FIGS                            built, no consumer left at all
# The tests check both directions and reject a stale marker, so a prose cut that
# orphans a figure fails the suite instead of leaving `make` doing dead work.
MANUSCRIPT_FIGS := deliverables/_shared/figures/fig_bars_v1.png deliverables/_shared/figures/fig_composition.png deliverables/_shared/figures/fig_breaks.png

# not-embedded: fig_global_map_cocitation.png — co-citation companion to the
#   direct map, built for comparison and deliberately embedded in no document;
#   pinned by tests/test_global_map.py::test_datapaper_prose_uses_generated_vars
DATAPAPER_FIGS  := deliverables/_shared/figures/fig_bars.png \
                   deliverables/_shared/figures/fig_global_map_direct.png \
                   deliverables/_shared/figures/fig_global_map_cocitation.png

# fig_bars is shared with the data paper; fig_dag and the three semantic-space
# panels were filed under DATAPAPER_FIGS / TECHREP_FIGS until 0359 — the corpus
# report is their only consumer.
CORPUS_REPORT_FIGS := deliverables/_shared/figures/fig_bars.png \
                   deliverables/_shared/figures/fig_dag.png \
                   deliverables/_shared/figures/fig_semantic.png \
                   deliverables/_shared/figures/fig_semantic_lang.png \
                   deliverables/_shared/figures/fig_semantic_period.png

MULTILAYER_FIGS  := deliverables/_shared/figures/fig_companion_zseries.png \
                   deliverables/_shared/figures/fig_companion_heatmap.png \
                   deliverables/_shared/figures/fig_companion_terms.png \
                   deliverables/_shared/figures/fig_companion_community.png \
                   deliverables/_shared/figures/fig_companion_sensitivity.png

# The two conference decks embed pipeline figures like any other deliverable;
# they are rendered by hand (no .mk rule), so before 0359 nothing declared them
# and fig_composition_wide.png — built by its own Makefile rule for the Gide
# deck's 2x3 landscape slot — belonged to no set at all.
SLIDES_FIGS     := deliverables/_shared/figures/fig_bars.png \
                   deliverables/_shared/figures/fig_bars_v1.png \
                   deliverables/_shared/figures/fig_breaks.png \
                   deliverables/_shared/figures/fig_composition.png \
                   deliverables/_shared/figures/fig_composition_wide.png

# Built, embedded by no deliverable. Each one's sole consumer was a top-level
# _shared/_includes/ file that no .qmd includes any more — the orphaned-include
# set ticket 0290 is auditing — except fig_traditions/fig_communities, which no
# file references at all. They stay in ALL_FIGS so `make figures` builds exactly
# what it built before; their disposition (delete figure + rule + backing table,
# or re-embed) rides with 0290's verdict on the includes.
ORPHANED_FIGS   := deliverables/_shared/figures/fig_alluvial_core.png \
                   deliverables/_shared/figures/fig_bimodality_core.png \
                   deliverables/_shared/figures/fig_bimodality_lexical_core.png \
                   deliverables/_shared/figures/fig_bimodality_keywords_core.png \
                   deliverables/_shared/figures/fig_bimodality_lexical.png \
                   deliverables/_shared/figures/fig_bimodality_keywords.png \
                   deliverables/_shared/figures/fig_kde.png \
                   deliverables/_shared/figures/fig_traditions.png \
                   deliverables/_shared/figures/fig_communities.png \
                   deliverables/_shared/figures/fig_breakpoints.png \
                   deliverables/_shared/figures/fig_alluvial.png \
                   deliverables/_shared/figures/fig_bimodality.png \
                   deliverables/_shared/figures/fig_seed_axis_core.png \
                   deliverables/_shared/figures/fig_pca_scatter.png \
                   deliverables/_shared/figures/fig_genealogy.png

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

# The technical report embeds the zoo set and nothing else: it composes
# _includes/techrep-zoo.md, which pulls in one _includes/zoo/ entry per method,
# each carrying its schematic and its result panel. Defined here, after the two
# lists it expands (`:=` is immediate). Until 0359 this variable named twelve
# figures the report has not embedded since the techrep rewrite; they are now in
# CORPUS_REPORT_FIGS and ORPHANED_FIGS.
TECHREP_FIGS    := $(ZOO_SCHEMATICS) $(ZOO_RESULT_FIGS)
