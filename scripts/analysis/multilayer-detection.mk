# multilayer-detection.mk — Figures for the companion paper (ticket 0058)
#
# Four canonical PNGs consumed by deliverables/multilayer/multilayer-detection.qmd.
#
# Include from the main Makefile:  -include scripts/analysis/multilayer-detection.mk
#
# Targets:
#   companion-figures  — build all four PNGs
#
# Inputs (ticket 0042 rerun outputs; produced by divergence-summary):
#   $(COMP_TABLES)/tab_summary_{S2_energy,L1,G9_community,G2_spectral}.csv
#   $(COMP_TABLES)/tab_div_C2ST_{embedding,lexical}.csv
#
# Optional inputs (ticket 0056 interpretation layer; stub fallback if absent):
#   deliverables/_shared/tables/tab_discrim_terms*.csv
#   deliverables/_shared/tables/tab_community_shifts*.csv

COMP_TABLES := $(DERIVED)
COMP_FIGS   := deliverables/_shared/figures
COMP_CFG    := config/analysis.yaml
COMP_UTILS  := scripts/_companion_plot_utils.py
COMP_STYLE  := scripts/plot_style.py

# Required summary + C2ST inputs (Figures 1 and 2).
COMP_DEPS_CORE := \
    $(COMP_TABLES)/tab_summary_S2_energy.csv \
    $(COMP_TABLES)/tab_summary_L1.csv \
    $(COMP_TABLES)/tab_summary_G9_community.csv \
    $(COMP_TABLES)/tab_summary_G2_spectral.csv \
    $(COMP_TABLES)/tab_div_C2ST_embedding.csv \
    $(COMP_TABLES)/tab_div_C2ST_lexical.csv

# ── Figure 1: Z-score time series ────────────────────────────────────────

$(COMP_FIGS)/fig_companion_zseries.png: \
    scripts/figures/plot_companion_zseries.py $(COMP_UTILS) $(COMP_STYLE) \
    $(COMP_CFG) $(COMP_DEPS_CORE)
	$(PYTHON) scripts/figures/plot_companion_zseries.py --output $@

# ── Figure 2: Transition zone heatmap ────────────────────────────────────

$(COMP_FIGS)/fig_companion_heatmap.png: \
    scripts/figures/plot_companion_heatmap.py $(COMP_UTILS) $(COMP_STYLE) \
    $(COMP_CFG) $(COMP_DEPS_CORE)
	$(PYTHON) scripts/figures/plot_companion_heatmap.py --output $@

# ── Figure 3: Discriminative terms ───────────────────────────────────────
# No hard dependency on tab_discrim_terms*.csv: the script degrades to a
# TODO(t0064)-annotated stub when the interpretation layer is absent.

$(COMP_FIGS)/fig_companion_terms.png: \
    scripts/figures/plot_companion_terms.py $(COMP_UTILS) $(COMP_STYLE) $(COMP_CFG)
	$(PYTHON) scripts/figures/plot_companion_terms.py --output $@

# ── Figure 4: Community shifts ───────────────────────────────────────────
# Same stub-fallback rationale as Figure 3.

$(COMP_FIGS)/fig_companion_community.png: \
    scripts/figures/plot_companion_community.py $(COMP_UTILS) $(COMP_STYLE) $(COMP_CFG)
	$(PYTHON) scripts/figures/plot_companion_community.py --output $@

.PHONY: companion-figures
companion-figures: \
    $(COMP_FIGS)/fig_companion_zseries.png \
    $(COMP_FIGS)/fig_companion_heatmap.png \
    $(COMP_FIGS)/fig_companion_terms.png \
    $(COMP_FIGS)/fig_companion_community.png

# ── Sensitivity grid (ticket 0083) ──────────────────────────────────────
$(COMP_TABLES)/tab_sensitivity_grid.csv: \
    scripts/analysis/compute_sensitivity_grid.py $(COMP_CFG)
	$(PYTHON) scripts/analysis/compute_sensitivity_grid.py --output $@

$(COMP_FIGS)/fig_companion_sensitivity.png: \
    scripts/figures/plot_companion_sensitivity.py $(COMP_CFG) \
    $(COMP_TABLES)/tab_sensitivity_grid.csv
	$(PYTHON) scripts/figures/plot_companion_sensitivity.py \
	    --input $(COMP_TABLES)/tab_sensitivity_grid.csv --output $@

.PHONY: companion-sensitivity
companion-sensitivity: \
    $(COMP_TABLES)/tab_sensitivity_grid.csv \
    $(COMP_FIGS)/fig_companion_sensitivity.png

# ── Technical supplement (ticket 0096) ───────────────────────────────────
# The Phase-3 render rules for BOTH multilayer-detection.pdf and its technical
# supplement (multilayer-detection-techrep.pdf) now live in
# deliverables/multilayer/multilayer.mk, invoked via `$(MAKE) -f` by the root
# `papers` target. MULTILAYER_TECHREP_INCLUDES moved to paths.mk. This file is the
# Phase-2 remainder: it only PRODUCES the companion figures (ticket 0237).
