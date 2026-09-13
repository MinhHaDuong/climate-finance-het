# Static observatory handoffs: one invocation, one JSON output; no collection.
JETP_OBSERVATORY := deliverables/jetp-observatory
JETP_OBSERVATORY_VIEWS := overview comparison ZAF IDN VNM SEN
JETP_OBSERVATORY_JSON := $(addprefix $(JETP_OBSERVATORY)/data/,$(addsuffix .json,$(JETP_OBSERVATORY_VIEWS)))
JETP_OBSERVATORY_INPUTS := $(addprefix data/jetp/,$(addsuffix .csv,projects events implementation-events sources source-claims project-source-links project-coverage manifest)) \
    $(wildcard data/jetp/comparison/*.json) \
    $(wildcard data/jetp/editorial/countries/*.md) \
    data/jetp/documents.dvc config/jetp_observatory.yaml \
    scripts/jetp/_observatory_data.py scripts/jetp/build_observatory.py

.PHONY: jetp-observatory jetp-observatory-preview
jetp-observatory: $(JETP_OBSERVATORY_JSON)

$(JETP_OBSERVATORY)/data/%.json: $(JETP_OBSERVATORY_INPUTS)
	$(PYTHON) scripts/jetp/build_observatory.py --view $* --output $@

# Preview only. Publication is a separate reviewed action.
jetp-observatory-preview: jetp-observatory
	$(PYTHON) -m http.server 8765 --bind 127.0.0.1 --directory $(JETP_OBSERVATORY)
