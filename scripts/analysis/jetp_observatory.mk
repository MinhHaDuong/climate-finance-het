# Static observatory handoffs: one invocation, one JSON output; no collection.
JETP_OBSERVATORY := deliverables/jetp-observatory
JETP_OBSERVATORY_VIEWS := overview comparison documents ZAF IDN VNM SEN
JETP_OBSERVATORY_EDITION_HISTORY := $(JETP_OBSERVATORY)/data/editions.json
JETP_OBSERVATORY_JSON := $(addprefix $(JETP_OBSERVATORY)/data/,$(addsuffix .json,$(JETP_OBSERVATORY_VIEWS)))
JETP_OBSERVATORY_PROVENANCE := $(JETP_OBSERVATORY)/data/provenance.json
JETP_M1A_DIR := $(JETP_OBSERVATORY)/data/m1a
JETP_M1A_FILES := $(addprefix $(JETP_M1A_DIR)/,ZAF.csv IDN.csv VNM.csv SEN.csv \
    ZAF.json IDN.json VNM.json SEN.json manifest.json)
# The four country views alone: what extraction_index() reads (ticket 0839).
JETP_M1A_VIEWS := $(addprefix $(JETP_M1A_DIR)/,ZAF.json IDN.json VNM.json SEN.json)
JETP_M1A_INPUTS := config/jetp-m1a-inventories.json scripts/jetp/build_m1a_inventories.py \
    docs/jetp-study/0818-zaf-q1-2026-rows.csv docs/jetp-study/0818-zaf-q1-2026-fields.csv \
    data/jetp/plan-projects.csv \
    data/jetp/releases/vnm-migration-0764.json
JETP_OBSERVATORY_INPUTS := $(addprefix data/jetp/,$(addsuffix .csv,projects events implementation-events sources source-claims project-source-links project-coverage manifest event-timing)) \
    $(wildcard data/jetp/comparison/*.json) \
    $(wildcard data/jetp/editorial/countries/*.md) $(wildcard data/jetp/releases/*/release.json) \
    data/jetp/documents.dvc config/jetp_observatory.yaml \
    scripts/jetp/_observatory_data.py scripts/jetp/build_observatory.py scripts/jetp/_publication.py scripts/jetp/build_observatory_provenance.py \
    scripts/jetp/build_observations.py scripts/jetp/_m1a_document_links.py

JETP_OBSERVATIONS_DIR := $(JETP_OBSERVATORY)/data/observations
JETP_OBSERVATIONS_FILES := $(addprefix $(JETP_OBSERVATIONS_DIR)/,ZAF.json IDN.json VNM.json SEN.json)
# Every table, not only the three served: build_observations.py goes through
# read_inputs, which loads and cross-validates all nine. No DVC pointer, and
# that is a property of the build rather than an omission: the registry is
# collapsed on the recorded digest, so the four views are identical whether or
# not the document snapshot is checked out.
JETP_OBSERVATIONS_INPUTS := $(filter data/jetp/%.csv,$(JETP_OBSERVATORY_INPUTS)) \
    scripts/jetp/build_observations.py scripts/jetp/build_observatory.py \
    scripts/jetp/_observatory_data.py scripts/jetp/_m1a_document_links.py

.PHONY: jetp-m1a jetp-observations jetp-observatory jetp-observatory-documents \
    jetp-observatory-refresh jetp-observatory-preview
jetp-m1a: $(JETP_M1A_FILES)

$(JETP_M1A_FILES) &: $(JETP_M1A_INPUTS)
	$(PYTHON) scripts/jetp/build_m1a_inventories.py --output-dir $(JETP_M1A_DIR)

# Independent of jetp-observatory, as jetp-m1a already is: the four views are a
# second reading of the same ledger, not an input of the country JSON.
jetp-observations: $(JETP_OBSERVATIONS_FILES)

$(JETP_OBSERVATIONS_FILES) &: $(JETP_OBSERVATIONS_INPUTS)
	$(PYTHON) scripts/jetp/build_observations.py --output-dir $(JETP_OBSERVATIONS_DIR)

jetp-observatory: $(JETP_OBSERVATORY_JSON) $(JETP_OBSERVATORY_EDITION_HISTORY) $(JETP_OBSERVATORY_PROVENANCE)

$(JETP_OBSERVATORY)/data/%.json: $(JETP_OBSERVATORY_INPUTS)
	$(PYTHON) scripts/jetp/build_observatory.py --view $* --output $@

# The documents view indexes what the four M1a views cite (ticket 0839), so
# they are read, never rebuilt, by its recipe: listed here as prerequisites so
# extraction_index() always finds them written. The recipe stays the pattern
# rule's above. reviewed-evidence.json, also read, is a committed artifact of
# the release pipeline and not a target of this file: naming it here would
# hand it to the pattern rule, which has no such view.
$(JETP_OBSERVATORY)/data/documents.json: $(JETP_M1A_VIEWS)

$(JETP_OBSERVATORY_PROVENANCE): $(JETP_OBSERVATORY_JSON) $(JETP_OBSERVATORY_INPUTS)
	$(PYTHON) scripts/jetp/build_observatory_provenance.py --output $@

# Local reading convenience only: never a prerequisite of the JSON build or of
# the public bundle, so neither depends on whether a snapshot happens to exist.
# The staged copy is initialized once, not tracked: after a `dvc checkout` moves
# data/jetp/documents to another revision, `make jetp-observatory-refresh`
# restages it. A reflink copy would otherwise keep serving the old bytes.
jetp-observatory-documents:
	@set -eu; \
	if [ -e $(JETP_OBSERVATORY)/documents ] || [ -L $(JETP_OBSERVATORY)/documents ]; then exit 0; fi; \
	if [ ! -d data/jetp/documents ]; then \
	    echo 'JETP snapshots absent; run make jetp-data to read documents locally.' >&2; \
	    exit 0; \
	fi; \
	stage=$$(mktemp -d $(JETP_OBSERVATORY)/.documents-init.XXXXXX) || exit 0; \
	trap 'rm -rf -- "$$stage"' 0; \
	if cp -RL --reflink=always -- data/jetp/documents "$$stage/documents" 2>/dev/null; then \
	    mv -Tn -- "$$stage/documents" $(JETP_OBSERVATORY)/documents; \
	else \
	    ln -s ../../data/jetp/documents $(JETP_OBSERVATORY)/documents; \
	fi

# The only recursive removal is the staged copy this file created.
jetp-observatory-refresh:
	rm -rf -- $(JETP_OBSERVATORY)/documents
	$(MAKE) jetp-observatory-documents

# Preview only. Publication is a separate reviewed action.
jetp-observatory-preview: jetp-observatory jetp-observatory-documents
	$(PYTHON) -m http.server 8765 --bind 127.0.0.1 --directory $(JETP_OBSERVATORY)
