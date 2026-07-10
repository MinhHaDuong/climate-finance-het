# technical-report.mk — Phase 3 render workpackage for the technical report.
#
# Render-only: produces deliverables/technical-report/technical-report.pdf from
# handoff artifacts on disk (includes, bibliography, vars, figures, the lexical
# TF-IDF stamp) — all produced by a prior `make analysis` (Phase 2). No uv, no
# corpus data, no compute rules. Toolchain: Quarto + a LaTeX engine only.
#
#   make -f deliverables/technical-report/technical-report.mk deliverables/technical-report/technical-report.pdf
#
# Invoked by the root Makefile's `papers` target via `$(MAKE) -f` so this render
# process never parses the root Phase-2 rules (ticket 0237). The figure lists and
# .lexical_tfidf.stamp are plain artifact-file prerequisites here, satisfied by a
# prior analysis build — not targets this file knows how to rebuild.

-include paths.mk

deliverables/technical-report/technical-report.pdf: deliverables/technical-report/technical-report.qmd $(TECHREP_INCLUDES) $(BIB) deliverables/_shared/technical-report-vars.yml $(TECHREP_FIGS) $(MULTILAYER_FIGS) .lexical_tfidf.stamp
	quarto render $< --to pdf

.PHONY: technical-report
technical-report: deliverables/technical-report/technical-report.pdf
