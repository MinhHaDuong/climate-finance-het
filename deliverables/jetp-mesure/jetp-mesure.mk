# Render-only LaTeX workpackage for the live JETP measurement paper.
# Invoked by the root `make papers`; no uv, data, Quarto, or analysis rules.

-include paths.mk

.DELETE_ON_ERROR:

LATEXMK ?= latexmk
# ``-cd`` makes sibling macro files and ../_shared bibliography paths resolve
# from this document's directory, while the target still names the root path.
LATEXMK_FLAGS ?= -cd -pdf -halt-on-error -interaction=nonstopmode
PYTHON ?= python3

deliverables/jetp-mesure/jetp-mesure.pdf: deliverables/jetp-mesure/jetp-mesure.tex deliverables/jetp-mesure/jetp-mesure-vars.tex docs/jetp-study/0823-central-figure.svg docs/jetp-study/0823-figure-manifest.json docs/jetp-study/0730-descriptives.json docs/jetp-study/0730-run-manifest.json $(BIB) deliverables/_shared/bibliography/OEconomia_EN_2.bst scripts/qa_latex_log.py
	$(LATEXMK) $(LATEXMK_FLAGS) $<
	$(PYTHON) scripts/qa_latex_log.py deliverables/jetp-mesure/jetp-mesure.log

.PHONY: jetp-mesure
jetp-mesure: deliverables/jetp-mesure/jetp-mesure.pdf
