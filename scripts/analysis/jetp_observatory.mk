# Static observatory handoffs: one invocation, one JSON output; no collection.
JETP_OBSERVATORY := deliverables/jetp-observatory
JETP_OBSERVATORY_VIEWS := overview comparison ZAF IDN VNM SEN
JETP_OBSERVATORY_EDITION_HISTORY := $(JETP_OBSERVATORY)/data/editions.json
JETP_OBSERVATORY_JSON := $(addprefix $(JETP_OBSERVATORY)/data/,$(addsuffix .json,$(JETP_OBSERVATORY_VIEWS)))
JETP_OBSERVATORY_PROVENANCE := $(JETP_OBSERVATORY)/data/provenance.json
JETP_M1A_DIR := $(JETP_OBSERVATORY)/data/m1a
JETP_M1A_FILES := $(addprefix $(JETP_M1A_DIR)/,ZAF.csv IDN.csv VNM.csv SEN.csv manifest.json)
JETP_M1A_INPUTS := config/jetp-m1a-inventories.json scripts/jetp/build_m1a_inventories.py \
    docs/jetp-study/0818-zaf-q1-2026-rows.csv data/jetp/plan-projects.csv \
    data/jetp/releases/vnm-migration-0764.json
JETP_OBSERVATORY_INPUTS := $(addprefix data/jetp/,$(addsuffix .csv,projects events implementation-events sources source-claims project-source-links project-coverage manifest event-timing)) \
    $(wildcard data/jetp/comparison/*.json) \
    $(wildcard data/jetp/editorial/countries/*.md) $(wildcard data/jetp/releases/*/release.json) \
    data/jetp/documents.dvc config/jetp_observatory.yaml \
    scripts/jetp/_observatory_data.py scripts/jetp/build_observatory.py scripts/jetp/_publication.py scripts/jetp/build_observatory_provenance.py

.PHONY: jetp-m1a jetp-observatory jetp-observatory-preview
jetp-m1a: $(JETP_M1A_FILES)

$(JETP_M1A_FILES) &: $(JETP_M1A_INPUTS)
	$(PYTHON) scripts/jetp/build_m1a_inventories.py --output-dir $(JETP_M1A_DIR)

jetp-observatory: $(JETP_OBSERVATORY_JSON) $(JETP_OBSERVATORY_EDITION_HISTORY) $(JETP_OBSERVATORY_PROVENANCE)

$(JETP_OBSERVATORY)/data/%.json: $(JETP_OBSERVATORY_INPUTS)
	$(PYTHON) scripts/jetp/build_observatory.py --view $* --output $@

$(JETP_OBSERVATORY_PROVENANCE): $(JETP_OBSERVATORY_JSON) $(JETP_OBSERVATORY_INPUTS)
	$(PYTHON) scripts/jetp/build_observatory_provenance.py --output $@

# Preview only. Publication is a separate reviewed action.
jetp-observatory-preview: jetp-observatory
	$(PYTHON) -m http.server 8765 --bind 127.0.0.1 --directory $(JETP_OBSERVATORY)
