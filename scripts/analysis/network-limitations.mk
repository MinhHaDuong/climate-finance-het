# network-limitations.mk — Citer-limited network limitations (ticket 0286)
#
# Include from the main Makefile:  -include scripts/analysis/network-limitations.mk
#
# R1-14 limitations demonstration for the data paper's response letter:
# what the sparse early citation record (citing documents <= config
# network_limitations.citer_cutoff) can establish on its own. Every number
# quoted in deliverables/data-paper/revision-rdj26561/r1-14-network-response.md
# traces to one of these artifacts.
#
# Targets:
#   network-limitations       Stats CSV (null test + bootstrap; ~minutes)
#   fig-traditions-pre2008    Electronic-supplement figure (committed artifact)
#   qa-cocitation-edges       Crossref edge spot-check JSON (network access)
#
# Inputs (Phase 1 contract): $(REFINED), $(REFINED_CIT) — from main Makefile.

NETLIM_STATS := deliverables/_shared/tables/tab_network_limitations.csv
NETLIM_FIG   := deliverables/_shared/figures/fig_traditions_pre2008_citers.png
NETLIM_QA    := deliverables/_shared/tables/qa_cocitation_edges_report.json

$(NETLIM_STATS): scripts/analysis/compute_network_limitations.py \
		scripts/_citer_limited_traditions.py scripts/_pre2007_traditions.py \
		scripts/_null_separation.py scripts/schemas.py scripts/utils.py \
		scripts/pipeline_loaders.py $(CONFIG) $(REFINED) $(REFINED_CIT)
	$(PYTHON) $< --output $@

$(NETLIM_FIG): scripts/figures/plot_fig_traditions_pre2008_citers.py \
		scripts/_citer_limited_traditions.py scripts/_pre2007_traditions.py \
		scripts/plot_style.py scripts/utils.py scripts/pipeline_loaders.py \
		$(CONFIG) $(REFINED) $(REFINED_CIT)
	$(PYTHON) $< --output $@

# Network access (Crossref); run deliberately, artifact is committed.
$(NETLIM_QA): scripts/qa/qa_cocitation_edges.py \
		scripts/_citer_limited_traditions.py scripts/qa/qa_citations.py \
		scripts/utils.py scripts/pipeline_loaders.py $(CONFIG) \
		$(REFINED) $(REFINED_CIT)
	$(PYTHON) $< --output $@

.PHONY: network-limitations fig-traditions-pre2008 qa-cocitation-edges
network-limitations: $(NETLIM_STATS)
fig-traditions-pre2008: $(NETLIM_FIG)
qa-cocitation-edges: $(NETLIM_QA)
