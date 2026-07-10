# corpus-report.mk — Phase 3 render workpackage for the corpus report.
#
# Render-only: produces deliverables/corpus-report/corpus-report.pdf from the
# prose source, its includes, bibliography and vars — artifacts a prior
# `make analysis` (Phase 2) put on disk. No uv, no corpus data, no compute rules.
# Toolchain: Quarto + a LaTeX engine only.
#
#   make -f deliverables/corpus-report/corpus-report.mk deliverables/corpus-report/corpus-report.pdf
#
# Invoked by the root Makefile's `papers` target via `$(MAKE) -f` so this render
# process never parses the root Phase-2 rules (ticket 0237). Quarto's single-file
# render writes the PDF next to the source, so the Make target is that file.

-include paths.mk

deliverables/corpus-report/corpus-report.pdf: deliverables/corpus-report/corpus-report.qmd $(CORPUS_REPORT_INCLUDES) $(BIB) deliverables/_shared/technical-report-vars.yml
	quarto render $< --to pdf

.PHONY: corpus-report
corpus-report: deliverables/corpus-report/corpus-report.pdf
