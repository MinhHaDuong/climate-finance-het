# Codebook — climate_finance_corpus.csv

Formal data dictionary for the deposited corpus file. Columns are organised in four logical groups. Missingness (share of empty or null cells) is measured on the shipped data (42916 rows) by `scripts/figures/export_codebook.py`; `n/a` marks optional columns absent from this build. Generated from the deposit column contract (`scripts/_deposit_variables.py`).

## Record identity

| Variable | Type | Allowed values | Missing | Description |
|:------|:----|:------------|------:|:-------------------------|
| `source` | string | openalex, istex, bibcnrs, scispace, grey, teaching | 0.0% | Primary source catalog for the record's metadata (highest-priority contributing source) |
| `source_id` | string | free | 1.3% | Identifier in the primary source (e.g. OpenAlex work ID) |
| `doi` | string, nullable | free | 19.2% | Digital Object Identifier, when available |

## Bibliographic metadata

| Variable | Type | Allowed values | Missing | Description |
|:------|:----|:------------|------:|:-------------------------|
| `title` | string | free | 0.6% | Title of the work |
| `first_author` | string, nullable | free | 2.4% | First author name |
| `all_authors` | string, nullable | free | 2.4% | Full author list, separator-joined |
| `year` | integer | free | 1.1% | Publication year |
| `journal` | string, nullable | free | 16.4% | Publication venue (journal, publisher, or repository) |
| `language` | string, nullable | free | 4.1% | Language code (ISO 639-1), detected and normalised |
| `keywords` | string, nullable | free | 2.7% | Keywords, semicolon-separated |
| `categories` | string, nullable | free | 1.8% | Subject categories / concepts from the source catalog |
| `cited_by_count` | integer | free | 4.1% | Citation count (OpenAlex, as of the collection date) |
| `affiliations` | string, nullable | free | 42.3% | Author affiliations, when available |

## Provenance flags

| Variable | Type | Allowed values | Missing | Description |
|:------|:----|:------------|------:|:-------------------------|
| `from_openalex` | boolean | 0, 1 | 0.0% | Provenance flag: found in OpenAlex |
| `from_istex` | boolean | 0, 1 | 0.0% | Provenance flag: found in ISTEX |
| `from_bibcnrs` | boolean | 0, 1 | 0.0% | Provenance flag: found in bibCNRS |
| `from_scispace` | boolean | 0, 1 | 0.0% | Provenance flag: found via SciSpace |
| `from_grey` | boolean | 0, 1 | 0.0% | Provenance flag: grey-literature source |
| `from_teaching` | boolean | 0, 1 | 0.0% | Provenance flag: teaching canon (syllabi) |
| `from_unfccc` | boolean | 0, 1 | n/a | Provenance flag: curated UNFCCC key document |
| `from_oecd` | boolean | 0, 1 | n/a | Provenance flag: curated OECD key document |
| `abstract_provenance` | string, nullable | curated, reconstructed:lead, reconstructed:exec_summary, empty | n/a | Provenance of the abstract text for curated key documents: `curated`, `reconstructed:lead`, or `reconstructed:exec_summary`; empty elsewhere |
| `keywords_provenance` | string, nullable | extracted, generated:lexicon, empty | n/a | Provenance of the keywords for curated key documents: `extracted` or `generated:lexicon`; empty elsewhere |
| `source_count` | integer | 1–8 | 0.0% | Number of sources that contributed the record (sum of the provenance flags) |

## Curation metadata

| Variable | Type | Allowed values | Missing | Description |
|:------|:----|:------------|------:|:-------------------------|
| `abstract_status` | string | original, reconstructed, generated, too_long, missing | 0.0% | Status of the (undistributed) abstract: `original`, `reconstructed` (from OpenAlex inverted index or ISTEX fulltext), `generated` (LLM summary of an oversized abstract), `too_long`, or `missing` |
| `near_duplicate_group` | integer, nullable | free | 98.8% | Group identifier for near-identical content published under several DOIs; null for ungrouped works |
| `semantic_outlier_dist` | float, nullable | free | n/a | Distance to the corpus embedding centroid, computed for the semantic-outlier flag |
| `in_v1` | boolean | true, false | n/a | Version tracking: work present in the v1.0 submission corpus |
| `is_flagged` | boolean | true, false | 0.0% | Any quality flag raised; the refined subset is `df[~df['is_flagged'] | df['is_protected']]` |
| `flag_reason` | string | comma-joined subset of the six flag names, or empty | 68.7% | Comma-separated list of raised quality flags (missing_metadata, no_abstract_irrelevant, title_blacklist, citation_isolated_old, semantic_outlier, llm_irrelevant); empty when unflagged |
| `is_protected` | boolean | true, false | 0.0% | Protection from removal (key papers kept despite flags) |
| `protection_reason` | string, nullable | free | 77.1% | Why the work is protected (citation count, seed list, ...) |
