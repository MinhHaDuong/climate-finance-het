# data-paper.mk — Phase 3 render workpackage for the RDJ4HSS data paper.
#
# Render-only: produces deliverables/data-paper/data-paper.pdf from handoff
# artifacts on disk (includes, bibliography, vars) — produced by a prior
# `make analysis` (Phase 2). No uv, no corpus data, no compute rules.
# Toolchain: Quarto + a LaTeX engine only.
#
#   make -f deliverables/data-paper/data-paper.mk deliverables/data-paper/data-paper.pdf
#
# Invoked by the root Makefile's `papers` target via `$(MAKE) -f` so this render
# process never parses the root Phase-2 rules (ticket 0237).

-include paths.mk

# DATAPAPER_FIGS added by 0359 — the paper embeds two of its four figures and
# nothing made the PDF depend on either.
deliverables/data-paper/data-paper.pdf: deliverables/data-paper/data-paper.qmd $(DATAPAPER_INCLUDES) $(BIB) deliverables/data-paper/data-paper-vars.yml $(DATAPAPER_FIGS)
	quarto render $< --to pdf

.PHONY: data-paper
data-paper: deliverables/data-paper/data-paper.pdf
