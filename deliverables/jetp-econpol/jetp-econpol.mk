# Render-only LaTeX workpackage for the live JETP political-economy paper.
# Invoked by the root `make papers`; no uv, data, Quarto, or analysis rules.

-include paths.mk

.DELETE_ON_ERROR:

LATEXMK ?= latexmk
# ``-cd`` makes sibling macro files and ../_shared bibliography paths resolve
# from this document's directory, while the target still names the root path.
LATEXMK_FLAGS ?= -cd -pdf -halt-on-error -interaction=nonstopmode
PYTHON ?= python3

deliverables/jetp-econpol/jetp-econpol.pdf: deliverables/jetp-econpol/jetp-econpol.tex deliverables/jetp-econpol/jetp-econpol-vars.tex $(BIB) deliverables/_shared/bibliography/OEconomia_EN_2.bst scripts/check_latex_log.py
	$(LATEXMK) $(LATEXMK_FLAGS) $<
	$(PYTHON) scripts/check_latex_log.py deliverables/jetp-econpol/jetp-econpol.log

.PHONY: jetp-econpol
jetp-econpol: deliverables/jetp-econpol/jetp-econpol.pdf
