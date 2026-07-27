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

# The paper composes no shared include (MULTILAYER_INCLUDES is empty since 0359);
# its five companion figures are what it actually needs on disk.
deliverables/multilayer/multilayer-detection.pdf: deliverables/multilayer/multilayer-detection.qmd $(MULTILAYER_FIGS) $(BIB) deliverables/multilayer/multilayer-detection-vars.yml
	quarto render $< --to pdf

# The supplement embeds the zoo figures of the six methods it discusses. It takes
# the whole zoo set as prerequisite rather than a seventh variable naming eleven
# files: `make zoo-figures` produces the set as a unit, so a subset would buy no
# incrementality (0359).
deliverables/multilayer/multilayer-detection-techrep.pdf: deliverables/multilayer/multilayer-detection-techrep.qmd $(MULTILAYER_TECHREP_INCLUDES) $(BIB) deliverables/_shared/technical-report-vars.yml $(ZOO_SCHEMATICS) $(ZOO_RESULT_FIGS)
	quarto render $< --to pdf

.PHONY: multilayer-detection multilayer-techrep
multilayer-detection: deliverables/multilayer/multilayer-detection.pdf
multilayer-techrep: deliverables/multilayer/multilayer-detection-techrep.pdf
