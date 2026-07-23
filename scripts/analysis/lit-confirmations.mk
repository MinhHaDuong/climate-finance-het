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
		scripts/analysis/analyze_global_map.py scripts/schemas.py \
		scripts/utils.py scripts/pipeline_loaders.py $(CONFIG) \
		config/community_registry.yml $(REFINED) $(REFINED_CIT)
	$(PYTHON) $< --output $@

$(SEM6_ASSIGN): scripts/analysis/compute_sem6_assignments.py \
		scripts/analysis/analyze_global_map.py scripts/schemas.py \
		scripts/utils.py scripts/pipeline_loaders.py $(CONFIG) \
		$(REFINED) $(REFINED_EMB) $(REFINED_CIT)
	$(PYTHON) $< --output $@

$(SEM6_ROBUST): scripts/analysis/compute_semantic_robustness.py \
		scripts/schemas.py scripts/utils.py scripts/pipeline_loaders.py \
		$(CONFIG) $(SEM6_ASSIGN) $(REFINED) $(REFINED_EMB)
	$(PYTHON) $< --input $(SEM6_ASSIGN) --output $@

.PHONY: lit-confirmations
lit-confirmations: $(LITCONF_STATS) $(SEM6_ASSIGN) $(SEM6_ROBUST)
