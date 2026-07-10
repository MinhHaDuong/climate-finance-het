# zoo.mk (render) — Phase 3 render workpackage for the method-zoo report.
#
# Render-only: produces deliverables/zoo/breakpoint-detect-method-zoo.pdf from
# handoff artifacts on disk (the zoo includes, bibliography, vars, the 17
# schematics and 18 result panels) produced by a prior `make analysis` (Phase 2).
# No uv, no corpus data, no compute rules. Toolchain: Quarto + a LaTeX engine only.
#
#   make -f deliverables/zoo/zoo.mk deliverables/zoo/breakpoint-detect-method-zoo.pdf
#
# Invoked by the root Makefile's `papers` target via `$(MAKE) -f` so this render
# process never parses the root Phase-2 rules (ticket 0237). The Phase-2 remainder
# (schematic/result-panel/cross-year compute rules) stays at root as zoo.mk.
#
# The figure prerequisites reference $(ZOO_SCHEMATICS) $(ZOO_RESULT_FIGS)
# explicitly, not the ambiguous $(ZOO_FIGS) — at the root the latter shadowed a
# file-list alias with the concern zoo.mk's directory-path definition.

-include paths.mk

deliverables/zoo/breakpoint-detect-method-zoo.pdf: deliverables/zoo/breakpoint-detect-method-zoo.qmd $(ZOO_INCLUDES) $(BIB) deliverables/_shared/technical-report-vars.yml $(ZOO_SCHEMATICS) $(ZOO_RESULT_FIGS)
	quarto render $< --to pdf

.PHONY: zoo
zoo: deliverables/zoo/breakpoint-detect-method-zoo.pdf
