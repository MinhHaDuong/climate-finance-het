# multilayer.mk — Phase 3 render workpackage for the multilayer-detection paper.
#
# Render-only: owns BOTH the main paper (multilayer-detection.pdf) and its
# technical supplement (multilayer-detection-techrep.pdf, ticket 0096), rendered
# from handoff artifacts on disk (includes, bibliography, vars) produced by a
# prior `make analysis` (Phase 2). No uv, no corpus data, no compute rules.
# Toolchain: Quarto + a LaTeX engine only.
#
#   make -f deliverables/multilayer/multilayer.mk deliverables/multilayer/multilayer-detection.pdf
#   make -f deliverables/multilayer/multilayer.mk deliverables/multilayer/multilayer-detection-techrep.pdf
#
# Invoked by the root Makefile's `papers` target via `$(MAKE) -f` so this render
# process never parses the root Phase-2 rules (ticket 0237). The Phase-2 remainder
# of the old multilayer-detection.mk (the four companion-figure compute rules)
# lives at scripts/analysis/multilayer-detection.mk (ticket 0239).

-include paths.mk

deliverables/multilayer/multilayer-detection.pdf: deliverables/multilayer/multilayer-detection.qmd $(MULTILAYER_INCLUDES) $(BIB) deliverables/multilayer/multilayer-detection-vars.yml
	quarto render $< --to pdf

deliverables/multilayer/multilayer-detection-techrep.pdf: deliverables/multilayer/multilayer-detection-techrep.qmd $(MULTILAYER_TECHREP_INCLUDES) $(BIB) deliverables/_shared/technical-report-vars.yml
	quarto render $< --to pdf

.PHONY: multilayer-detection multilayer-techrep
multilayer-detection: deliverables/multilayer/multilayer-detection.pdf
multilayer-techrep: deliverables/multilayer/multilayer-detection-techrep.pdf
