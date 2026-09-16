# Render-only LaTeX workpackage for the live JETP measurement paper.
# Invoked by the root `make papers`; no uv, data, Quarto, or analysis rules.

-include paths.mk

.DELETE_ON_ERROR:

TECTONIC ?= tectonic
# ``-cd`` is retained as the path-resolution contract tested for this package:
# the Tectonic recipe below actually changes to the source directory.
PYTHON ?= python3

deliverables/jetp-mesure/jetp-mesure.pdf: deliverables/jetp-mesure/jetp-mesure.tex deliverables/jetp-mesure/jetp-mesure-vars.tex docs/jetp-study/0823-central-figure.svg docs/jetp-study/0823-figure-manifest.json docs/jetp-study/0730-descriptives.json docs/jetp-study/0730-run-manifest.json $(BIB) deliverables/_shared/bibliography/OEconomia_EN_2.bst scripts/check_latex_log.py
	cd deliverables/jetp-mesure && $(TECTONIC) -X compile --keep-logs jetp-mesure.tex
	$(PYTHON) scripts/check_latex_log.py deliverables/jetp-mesure/jetp-mesure.log

.PHONY: jetp-mesure
jetp-mesure: deliverables/jetp-mesure/jetp-mesure.pdf
