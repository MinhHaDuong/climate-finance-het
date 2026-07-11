# separation.mk — Pre-2007 tradition-separation fortify-or-demote (ticket 0182)
#
# Include from the main Makefile:  -include scripts/analysis/separation.mk
#
# Tests whether the observed separation of the three pre-2007 intellectual
# traditions in the co-citation graph exceeds what the degree sequence alone
# produces (density-conditioned configuration-model null).
#
# Targets:
#   pre2007-coverage     Coverage diagnostic (sparsity regime) CSV
#   pre2007-separation   Degree-preserving separation null CSV
#   separation           Both
#
# Inputs (Phase 1 contract): $(REFINED), $(REFINED_CIT) — from main Makefile.

SEP_TABLES   := deliverables/_shared/tables
SEP_COVERAGE := $(SEP_TABLES)/tab_pre2007_coverage.csv
SEP_NULL     := $(SEP_TABLES)/tab_null_separation_pre2007.csv

$(SEP_COVERAGE): scripts/analysis/compute_pre2007_coverage.py scripts/utils.py \
		scripts/pipeline_loaders.py scripts/schemas.py $(CONFIG) \
		$(REFINED) $(REFINED_CIT)
	$(PYTHON) $< --output $@

$(SEP_NULL): scripts/analysis/compute_null_separation.py scripts/_null_separation.py \
		scripts/plot_fig_traditions.py scripts/utils.py scripts/schemas.py \
		scripts/pipeline_loaders.py $(CONFIG) $(REFINED) $(REFINED_CIT)
	$(PYTHON) $< --output $@

.PHONY: pre2007-coverage pre2007-separation separation
pre2007-coverage: $(SEP_COVERAGE)
pre2007-separation: $(SEP_NULL)
separation: $(SEP_COVERAGE) $(SEP_NULL)
