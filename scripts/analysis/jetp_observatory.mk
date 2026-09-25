# Static observatory handoffs: one invocation, one JSON output; no collection.
JETP_OBSERVATORY := deliverables/jetp-observatory
JETP_OBSERVATORY_VIEWS := overview comparison coverage documents ZAF IDN VNM SEN
JETP_OBSERVATORY_EDITION_HISTORY := $(JETP_OBSERVATORY)/data/editions.json
JETP_OBSERVATORY_JSON := $(addprefix $(JETP_OBSERVATORY)/data/,$(addsuffix .json,$(JETP_OBSERVATORY_VIEWS)))
JETP_OBSERVATORY_PROVENANCE := $(JETP_OBSERVATORY)/data/provenance.json
JETP_PARTY_NAMES_VIEW := $(JETP_OBSERVATORY)/data/party-names.json
JETP_M1A_DIR := $(JETP_OBSERVATORY)/data/m1a
JETP_M1A_FILES := $(addprefix $(JETP_M1A_DIR)/,ZAF.csv IDN.csv VNM.csv SEN.csv \
    ZAF.json IDN.json VNM.json SEN.json manifest.json)
# The export is a view of the ledger lines of its six extracts (ticket 0873).
# The pinned extracts they were ingested from once, by
# scripts/jetp/build_m1a_lines.py, are not read here: that ingestion is a
# record written once and reviewed as a diff, not a build step.
JETP_M1A_INPUTS := config/jetp-m1a-inventories.json scripts/jetp/build_m1a_inventories.py \
    scripts/jetp/_ledger_headers.py config/jetp-ledger.sql .githooks/pre-commit \
    $(wildcard data/jetp/lines.csv data/jetp/lines.d/*.csv data/jetp/line-fields/*.csv) \
    data/jetp/line-field-specs.csv data/jetp/routes.csv
JETP_OBSERVATORY_INPUTS := data/jetp/migration/0875-projects-legacy.csv $(addprefix data/jetp/,$(addsuffix .csv,coverage events implementation-events sources source-claims project-source-links project-coverage manifest event-timing documents retrievals snapshots)) \
    $(wildcard data/jetp/comparison/*.json) \
    $(wildcard data/jetp/editorial/countries/*.md) $(wildcard data/jetp/releases/*/release.json) \
    data/jetp/documents.dvc config/jetp_observatory.yaml \
    scripts/jetp/_observatory_data.py scripts/jetp/build_observatory.py scripts/jetp/_publication.py scripts/jetp/build_observatory_provenance.py \
    scripts/jetp/build_observations.py scripts/jetp/_m1a_document_links.py \
    scripts/jetp/_ledger_headers.py config/jetp-ledger.sql

JETP_OBSERVATIONS_DIR := $(JETP_OBSERVATORY)/data/observations
JETP_OBSERVATIONS_FILES := $(addprefix $(JETP_OBSERVATIONS_DIR)/,ZAF.json IDN.json VNM.json SEN.json)
JETP_V2_EVENT_FILES := data/jetp/observations.csv data/jetp/timings.csv data/jetp/rates.csv \
    data/jetp/migration/0876-pending.csv data/jetp/migration/0876-timing-reconciliation.csv
# Every table, not only the three served: build_observations.py goes through
# read_inputs, which loads and cross-validates all nine. No DVC pointer, and
# that is a property of the build rather than an omission: the registry is
# collapsed on the recorded digest, so the four views are identical whether or
# not the document snapshot is checked out.
JETP_OBSERVATIONS_INPUTS := $(filter data/jetp/%.csv,$(JETP_OBSERVATORY_INPUTS)) \
    data/jetp/migration/0875-dispositions.csv data/jetp/migration/0970-event-adjudications.csv \
    data/jetp/migration/1160-citation-decisions.csv $(wildcard data/jetp/lines.d/*.csv) \
    scripts/jetp/build_observations.py scripts/jetp/build_observatory.py \
    scripts/jetp/_observatory_data.py scripts/jetp/_m1a_document_links.py

# The ontology tables, one served file per table (ticket 0882), empty tables
# included: the Glossary is generated from them. A separate script from the
# country views, so those views and their recorded input hashes stay put when
# a term is revised.
JETP_ONTOLOGY_VIEWS_DIR := $(JETP_OBSERVATORY)/data/ontology
JETP_ONTOLOGY_VIEWS := $(addprefix $(JETP_ONTOLOGY_VIEWS_DIR)/,terms.json status-crosswalk.json \
    sector-crosswalk.json perimeters.json marker-coefficients.json)
JETP_ONTOLOGY_VIEWS_INPUTS := $(wildcard data/jetp/ontology/*.csv data/jetp/ontology/*/*.csv) \
    config/jetp-ledger.sql .githooks/pre-commit scripts/jetp/build_ontology_views.py \
    scripts/jetp/_ontology.py scripts/jetp/_ledger_headers.py

# Web Archive copies and publisher link checks (ticket 0925): two tables of
# their own beside the collection registry, never columns of it, each served
# as its own view by its own script, so a capture or a monthly check rebuilds
# these two files and no other view's recorded input hashes. The page joins
# them to documents.json on the document's address.
JETP_WEB_ARCHIVE := data/jetp/web-archive-captures.csv
JETP_LINK_CHECKS := data/jetp/publisher-link-checks.csv
JETP_LINK_VIEWS := $(JETP_OBSERVATORY)/data/web-archive.json $(JETP_OBSERVATORY)/data/publisher-links.json

.PHONY: jetp-web-archive jetp-link-check jetp-link-views
jetp-link-views: $(JETP_LINK_VIEWS)

$(JETP_OBSERVATORY)/data/web-archive.json: $(wildcard $(JETP_WEB_ARCHIVE)) scripts/jetp/build_link_views.py
	$(PYTHON) scripts/jetp/build_link_views.py --view web-archive --output $@

$(JETP_OBSERVATORY)/data/publisher-links.json: $(wildcard $(JETP_LINK_CHECKS)) scripts/jetp/build_link_views.py
	$(PYTHON) scripts/jetp/build_link_views.py --view publisher-links --output $@

# Network steps, never prerequisites of a build. The capture is resumable and
# polite (skips what is captured, retries what failed; see its docstring); run
# it after every harvest. The link check is monthly, on padme; its schedule is
# the author's to install (deliverables/jetp-observatory/README.md).
jetp-web-archive:
	$(PYTHON) scripts/jetp/corpus_web_archive_capture.py --output $(JETP_WEB_ARCHIVE)

jetp-link-check:
	$(PYTHON) scripts/jetp/corpus_check_publisher_links.py --output $(JETP_LINK_CHECKS)

.PHONY: jetp-m1a jetp-observations jetp-ontology-views jetp-observatory jetp-observatory-documents \
    jetp-observatory-refresh jetp-observatory-preview jetp-observatory-bundle jetp-observatory-publish
jetp-m1a: $(JETP_M1A_FILES)

$(JETP_M1A_FILES) &: $(JETP_M1A_INPUTS)
	$(PYTHON) scripts/jetp/build_m1a_inventories.py --output-dir $(JETP_M1A_DIR)

# Independent of jetp-observatory, as jetp-m1a already is: the four views are a
# second reading of the same ledger, not an input of the country JSON.
jetp-observations: $(JETP_OBSERVATIONS_FILES) $(JETP_V2_EVENT_FILES)

$(JETP_OBSERVATIONS_FILES) $(JETP_V2_EVENT_FILES) &: $(JETP_OBSERVATIONS_INPUTS)
	$(PYTHON) scripts/jetp/build_observations.py --write-normalized --output-dir $(JETP_OBSERVATIONS_DIR)

jetp-ontology-views: $(JETP_ONTOLOGY_VIEWS)

$(JETP_ONTOLOGY_VIEWS) &: $(JETP_ONTOLOGY_VIEWS_INPUTS)
	$(PYTHON) scripts/jetp/build_ontology_views.py --output-dir $(JETP_ONTOLOGY_VIEWS_DIR)

jetp-observatory: $(JETP_ONTOLOGY_VIEWS) $(JETP_LINK_VIEWS) $(JETP_PARTY_NAMES_VIEW) $(JETP_OBSERVATORY_JSON) $(JETP_OBSERVATORY_EDITION_HISTORY) $(JETP_OBSERVATORY_PROVENANCE)

$(JETP_PARTY_NAMES_VIEW): data/jetp/parties.csv data/jetp/party-names.csv scripts/jetp/build_party_names_view.py
	$(PYTHON) scripts/jetp/build_party_names_view.py --output $@

# The documents view is the collection registry alone (ticket 0858): it reads
# no other view, so it has no prerequisite beyond the inputs above. The join
# between a document and what was extracted from it is made by the page, at
# read time, on the M1a and observations views served beside it.
$(JETP_OBSERVATORY)/data/%.json: $(JETP_OBSERVATORY_INPUTS)
	$(PYTHON) scripts/jetp/build_observatory.py --view $* --output $@

$(JETP_OBSERVATORY_PROVENANCE): $(JETP_OBSERVATORY_JSON) $(JETP_OBSERVATORY_INPUTS)
	$(PYTHON) scripts/jetp/build_observatory_provenance.py --output $@

# Local reading convenience only: never a prerequisite of the JSON build or of
# the public bundle, so neither depends on whether a snapshot happens to exist.
# The staged copy is initialized once, not tracked: after a `dvc checkout` moves
# data/jetp/documents to another revision, `make jetp-observatory-refresh`
# restages it. A reflink copy would otherwise keep serving the old bytes.
# Objects are named by their hash, so differing file lists mean a stale copy:
# say so rather than exit silently (two VNM sources 404'd on 2026-09-24).
# Where reflinks are unsupported, documents/ is a real directory whose objects/
# links to the checkout, so the index below never lands in data/jetp.
# Every run rewrites documents/index.json, the list of copies the pages may
# link (ticket 0915): the pages draw an archived link only for a copy it lists.
jetp-observatory-documents:
	@set -eu; \
	docs=$(JETP_OBSERVATORY)/documents; \
	if [ -L "$$docs" ]; then \
	    echo 'Staged JETP documents are a symlink; run make jetp-observatory-refresh to index them.' >&2; \
	    exit 0; \
	fi; \
	if [ -e "$$docs" ]; then \
	    if [ -d data/jetp/documents ] && \
	        ! cmp -s <(cd data/jetp/documents && find -L . -type f | sort) \
	                 <(cd "$$docs" && find -L . -type f ! -path ./index.json | sort); then \
	        echo 'Staged JETP documents differ from data/jetp/documents; run make jetp-observatory-refresh.' >&2; \
	    fi; \
	else \
	    if [ ! -d data/jetp/documents ]; then \
	        echo 'JETP snapshots absent; run make jetp-data to read documents locally.' >&2; \
	        exit 0; \
	    fi; \
	    stage=$$(mktemp -d $(JETP_OBSERVATORY)/.documents-init.XXXXXX) || exit 0; \
	    trap 'rm -rf -- "$$stage"' 0; \
	    if ! cp -RL --reflink=always -- data/jetp/documents "$$stage/documents" 2>/dev/null; then \
	        rm -rf -- "$$stage/documents"; \
	        mkdir -- "$$stage/documents"; \
	        ln -s ../../../data/jetp/documents/objects "$$stage/documents/objects"; \
	    fi; \
	    mv -Tn -- "$$stage/documents" "$$docs"; \
	fi; \
	$(PYTHON) scripts/jetp/build_documents_index.py --documents "$$docs"

# The only recursive removal is the staged copy this file created.
jetp-observatory-refresh:
	rm -rf -- $(JETP_OBSERVATORY)/documents
	$(MAKE) jetp-observatory-documents

# Preview only. Publication is a separate reviewed action.
jetp-observatory-preview: jetp-observatory jetp-observatory-documents
	$(PYTHON) -m http.server 8765 --bind 127.0.0.1 --directory $(JETP_OBSERVATORY)

# The public bundle (ticket 0915) is the tracked site tree at one commit and
# nothing else: no build flag, no rewritten file. documents/ is git-ignored, so
# the tree cannot hold it; the target still refuses one, in the tree or in the
# extracted bundle. It reads refs only — no network, no DVC — and writes into a
# git-ignored directory. The default ref is the local origin/main, the tree
# jetp-observatory-publish pushes: fetch first to preview what will go out.
JETP_PAGES_REF ?= origin/main
JETP_PAGES_BUNDLE ?= data/derived/jetp/observatory-pages
jetp-observatory-bundle:
	@set -eu; \
	tree=$$(git rev-parse --verify '$(JETP_PAGES_REF):$(JETP_OBSERVATORY)'); \
	top=$$(git ls-tree --name-only "$$tree"); \
	if grep -qx documents <<<"$$top"; then \
	    echo 'documents/ is tracked in the site tree; refusing to bundle.' >&2; exit 1; \
	fi; \
	git check-ignore -q '$(JETP_PAGES_BUNDLE)/index.html' || { \
	    echo '$(JETP_PAGES_BUNDLE) is not git-ignored; refusing to write there.' >&2; exit 1; }; \
	rm -rf -- '$(JETP_PAGES_BUNDLE)'; \
	mkdir -p -- '$(JETP_PAGES_BUNDLE)'; \
	git archive --format=tar "$$tree" | tar -x -C '$(JETP_PAGES_BUNDLE)'; \
	if [ -e '$(JETP_PAGES_BUNDLE)/documents' ]; then \
	    echo 'The bundle holds documents/; refusing it.' >&2; rm -rf -- '$(JETP_PAGES_BUNDLE)'; exit 1; \
	fi; \
	echo "Bundled $(JETP_PAGES_REF) (site tree $$tree) into $(JETP_PAGES_BUNDLE)"

# Pushes the same tree to gh-pages; never enables GitHub Pages, which is the
# author's step (deliverables/jetp-observatory/README.md). No CI (ticket 0321).
jetp-observatory-publish:
	bash scripts/jetp/publish_observatory_pages.sh --push '$(JETP_PAGES_REF)'

# Ledger DDL tooling (ticket 0871): config/jetp-ledger.sql is the one schema of
# the ledger's common tables; the CSVs load into a derived SQLite whose keys,
# checks and violation_* views are the validator. JETP_LEDGER_DIR points the
# two targets at another ledger, such as a test fixture.
JETP_LEDGER_DIR ?= data/jetp
JETP_LEDGER_DB := data/derived/jetp/ledger.sqlite
JETP_LEDGER_INPUTS := config/jetp-ledger.sql .githooks/pre-commit \
    scripts/jetp/build_ledger.py scripts/jetp/_ledger_headers.py scripts/utils.py \
    $(wildcard $(JETP_LEDGER_DIR)/*.csv $(JETP_LEDGER_DIR)/*/*.csv)

.PHONY: jetp-ledger-db jetp-ledger-check
jetp-ledger-db: $(JETP_LEDGER_DB)

$(JETP_LEDGER_DB): $(JETP_LEDGER_INPUTS)
	$(PYTHON) scripts/jetp/build_ledger.py --ledger-dir $(JETP_LEDGER_DIR) --output $@

jetp-ledger-check:
	$(PYTHON) scripts/jetp/build_ledger.py --ledger-dir $(JETP_LEDGER_DIR) --check
