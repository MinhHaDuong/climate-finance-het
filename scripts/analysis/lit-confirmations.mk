# lit-confirmations.mk — Literature-result confirmations (ticket 0310)
#
# Include from the main Makefile:  -include scripts/analysis/lit-confirmations.mk
#
# Four published results confirmed on the corpus with one statistic each
# (ED-02/R1-18): finance-journal share break, post-2015 growth break,
# public/market pole separation null, adaptation-vs-mitigation binomial.
# Every lit_* variable quoted in deliverables/data-paper/data-paper.qmd
# traces to a row of the committed artifact.
#
# Inputs (Phase 1 contract): $(REFINED), $(REFINED_CIT) — from main Makefile.

LITCONF_STATS  := deliverables/_shared/tables/tab_lit_confirmations.csv
SEM6_ASSIGN    := deliverables/_shared/tables/tab_sem6_assignments.csv
SEM6_ROBUST    := deliverables/_shared/tables/tab_semantic_robustness.csv

$(LITCONF_STATS): scripts/analysis/compute_lit_confirmations.py \
		scripts/_lit_confirmations.py scripts/_null_separation.py \
		scripts/_global_map_graph.py scripts/schemas.py \
		scripts/utils.py scripts/pipeline_loaders.py $(CONFIG) \
		config/community_registry.yml $(REFINED) $(REFINED_CIT)
	$(PYTHON) $< --output $@

$(SEM6_ASSIGN): scripts/analysis/compute_sem6_assignments.py \
		scripts/_global_map_graph.py scripts/schemas.py \
		scripts/utils.py scripts/pipeline_loaders.py $(CONFIG) \
		$(REFINED) $(REFINED_EMB) $(REFINED_CIT)
	$(PYTHON) $< --output $@

$(SEM6_ROBUST): scripts/analysis/compute_semantic_robustness.py \
		scripts/schemas.py scripts/utils.py scripts/pipeline_loaders.py \
		$(CONFIG) $(SEM6_ASSIGN) $(REFINED) $(REFINED_EMB)
	$(PYTHON) $< --input $(SEM6_ASSIGN) --output $@

# Semantic-composition figure for the data paper (author decision 2026-07-23):
# manuscript appendix Figure 2 recomputed on the current corpus. Follow-up to
# PR #1109 (author arbitration): the clustering input EXCLUDES works with
# boilerplate/stub/missing abstracts (is_boilerplate_abstract) — a data-quality
# artifact is not a theme of the field — via the _clean alluvial variant.
# The alluvial table is copied into the shared tables dir as the committed
# backing record.
SEM_COMPO_TAB := deliverables/_shared/tables/tab_sem_composition.csv
SEM_COMPO_FIG := deliverables/_shared/figures/fig_sem_composition.png

$(DERIVED)/tab_alluvial_clean.csv $(DERIVED)/cluster_labels_clean.json \
$(DERIVED)/tab_core_shares_clean.csv &: \
		scripts/analysis/compute_clusters.py scripts/utils.py $(CONFIG) $(REFINED)
	$(PYTHON) $< --output $(DERIVED)/tab_alluvial_clean.csv --exclude-boilerplate

$(SEM_COMPO_TAB): $(DERIVED)/tab_alluvial_clean.csv
	cp $< $@

$(SEM_COMPO_FIG): scripts/figures/plot_fig2_composition.py \
		scripts/plot_style.py scripts/utils.py $(CONFIG) \
		$(DERIVED)/tab_alluvial_clean.csv $(DERIVED)/cluster_labels_clean.json \
		config/datapaper_cluster_short_labels.json
	$(PYTHON) $< --output $@ --input $(DERIVED)/tab_alluvial_clean.csv \
		--labels $(DERIVED)/cluster_labels_clean.json \
		--short-labels config/datapaper_cluster_short_labels.json

.PHONY: lit-confirmations
lit-confirmations: $(LITCONF_STATS) $(SEM6_ASSIGN) $(SEM6_ROBUST) \
	$(SEM_COMPO_TAB) $(SEM_COMPO_FIG)
