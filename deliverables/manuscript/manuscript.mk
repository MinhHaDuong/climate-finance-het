# manuscript.mk — Phase 3 writing workpackage for the Œconomia article.
#
# Standalone clean-room build: produces output/content/manuscript.{pdf,docx}
# from committed handoff artifacts ALONE — no uv, no Python, no corpus data.
# Toolchain: Quarto + a LaTeX engine (XeLaTeX via TeX Live) + Pandoc only.
#
#   make -f deliverables/manuscript/manuscript.mk output/content/manuscript.pdf
#
# Also -include'd by the top-level Makefile so `make manuscript` resolves the
# same rules. Prerequisites are the prose source plus the git-tracked writing
# deliverables (3 figures + tab_venues.md, see .gitignore negations) and the
# committed bibliography/vars — every one present in a fresh checkout. The
# Phase-2 figure-from-data rules that PRODUCE these deliverables stay in the
# main Makefile; this file only CONSUMES them. (Tickets 0131, 0226.)
#
# Since 0226 the manuscript is its own Quarto project
# (deliverables/manuscript/_quarto.yml, output-dir ../../output/content). Quarto
# project discovery is scoped to that folder, which holds only the two
# manuscript-workpackage docs, so the old exclusion-mask profile files
# (_quarto-manuscript*.yml) are gone.

# Reproducible PDF metadata timestamps when built standalone (the top-level
# Makefile exports the same; ?=-style guard keeps it a no-op when included).
export SOURCE_DATE_EPOCH ?= 0

# Writing-facing manuscript deliverables — git-tracked, byte-stable.
MANUSCRIPT_SRC      := deliverables/manuscript/manuscript.qmd
MANUSCRIPT_BIB      := deliverables/_shared/bibliography/main.bib
MANUSCRIPT_CSL      := deliverables/_shared/bibliography/oeconomia.csl
MANUSCRIPT_VARS     := deliverables/manuscript/manuscript-vars.yml
MANUSCRIPT_DELIVERABLES := deliverables/_shared/figures/fig_bars_v1.png \
                           deliverables/_shared/figures/fig_composition.png \
                           deliverables/_shared/figures/fig_breaks.png \
                           deliverables/_shared/tables/tab_venues.md

MANUSCRIPT_INPUTS := $(MANUSCRIPT_SRC) $(MANUSCRIPT_BIB) $(MANUSCRIPT_CSL) \
                     $(MANUSCRIPT_VARS) $(MANUSCRIPT_DELIVERABLES)

output/content/manuscript.pdf: $(MANUSCRIPT_INPUTS)
	quarto render $(MANUSCRIPT_SRC) --to pdf

output/content/manuscript.docx: $(MANUSCRIPT_INPUTS)
	quarto render $(MANUSCRIPT_SRC) --to docx

# ── Charles Gide conference variant ─────────────────────────────────────────
# Short French paper (manuscript-Gide.qmd) presented at the 21e colloque Charles
# Gide. Same writing workpackage: shares the manuscript's git-tracked figures +
# tab_venues.md and manuscript-vars.yml. No data, no uv — Quarto + LaTeX only.
#
# deliverables/manuscript/manuscript-Gide.qmd is git-tracked. The figures and
# tables it consumes are tracked handoff artifacts too; regenerating them from
# data is the analysis workpackage's job, so render this paper with those
# artifacts already present (a full data-less clean-room rebuild is ticket 0131).
GIDE_SRC        := deliverables/manuscript/manuscript-Gide.qmd
# French-caption variant of the shared venues table: identical English table body
# (headers, journal names, counts) with a French caption. Derived from the
# git-tracked tab_venues.md, so it stays in sync when that table is regenerated.
# Writing-side only: a plain-text transform, no uv and no data.
GIDE_VENUES_FR  := deliverables/_shared/tables/tab_venues_fr.md

$(GIDE_VENUES_FR): deliverables/_shared/tables/tab_venues.md deliverables/_shared/tables/tab_venues_fr_caption.md
	{ grep -v '^: ' $< ; cat deliverables/_shared/tables/tab_venues_fr_caption.md ; } > $@

GIDE_INPUTS := $(GIDE_SRC) $(MANUSCRIPT_BIB) $(MANUSCRIPT_CSL) \
               $(MANUSCRIPT_VARS) \
               $(MANUSCRIPT_DELIVERABLES) $(GIDE_VENUES_FR)

output/content/manuscript-Gide.pdf: $(GIDE_INPUTS)
	quarto render $(GIDE_SRC) --to pdf

.PHONY: gide
gide: output/content/manuscript-Gide.pdf
