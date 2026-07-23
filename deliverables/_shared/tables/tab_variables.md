| Variable | Type | Description | Source |
|:------|:----|:-------------------------|:---------|
| `source` | string | Primary source catalog for the record's metadata (highest-priority contributing source) | source catalogs, merged by catalog_merge.py |
| `source_id` | string | Identifier in the primary source (e.g. OpenAlex work ID) | source catalogs, merged by catalog_merge.py |
| `doi` | string, nullable | Digital Object Identifier, when available | source catalogs, merged by catalog_merge.py |
| `title` | string | Title of the work | source catalogs, merged by catalog_merge.py |
| `first_author` | string, nullable | First author name | source catalogs, merged by catalog_merge.py |
| `all_authors` | string, nullable | Full author list, separator-joined | source catalogs, merged by catalog_merge.py |
| `year` | integer | Publication year | source catalogs, merged by catalog_merge.py |
| `journal` | string, nullable | Publication venue (journal, publisher, or repository) | source catalogs, merged by catalog_merge.py |
| `language` | string, nullable | Language code (ISO 639-1), detected and normalised | enrichment (enrich_* scripts) |
| `keywords` | string, nullable | Keywords, semicolon-separated | source catalogs, merged by catalog_merge.py |
| `categories` | string, nullable | Subject categories / concepts from the source catalog | source catalogs, merged by catalog_merge.py |
| `cited_by_count` | integer | Citation count (OpenAlex, as of the collection date) | source catalogs, merged by catalog_merge.py |
| `affiliations` | string, nullable | Author affiliations, when available | source catalogs, merged by catalog_merge.py |
| `from_openalex` | boolean | Provenance flag: found in OpenAlex | source catalogs, merged by catalog_merge.py |
| `from_istex` | boolean | Provenance flag: found in ISTEX | source catalogs, merged by catalog_merge.py |
| `from_bibcnrs` | boolean | Provenance flag: found in bibCNRS | source catalogs, merged by catalog_merge.py |
| `from_scispace` | boolean | Provenance flag: found via SciSpace | source catalogs, merged by catalog_merge.py |
| `from_grey` | boolean | Provenance flag: grey-literature source | source catalogs, merged by catalog_merge.py |
| `from_teaching` | boolean | Provenance flag: teaching canon (syllabi) | source catalogs, merged by catalog_merge.py |
| `from_unfccc` | boolean | Provenance flag: curated UNFCCC key document (absent from corpus builds predating this pipeline stage) | curated key-documents layer (catalog_keydocs.py, corpus v2) |
| `from_oecd` | boolean | Provenance flag: curated OECD key document (absent from corpus builds predating this pipeline stage) | curated key-documents layer (catalog_keydocs.py, corpus v2) |
| `abstract_provenance` | string, nullable | Provenance of the abstract text for curated key documents: `curated`, `reconstructed:lead`, or `reconstructed:exec_summary`; empty elsewhere (absent from corpus builds predating this pipeline stage) | curated key-documents layer (catalog_keydocs.py, corpus v2) |
| `keywords_provenance` | string, nullable | Provenance of the keywords for curated key documents: `extracted` or `generated:lexicon`; empty elsewhere (absent from corpus builds predating this pipeline stage) | curated key-documents layer (catalog_keydocs.py, corpus v2) |
| `source_count` | integer | Number of sources that contributed the record (sum of the provenance flags) | source catalogs, merged by catalog_merge.py |
| `abstract_status` | string | Status of the (undistributed) abstract: `original`, `reconstructed` (from OpenAlex inverted index or ISTEX fulltext), `generated` (LLM summary of an oversized abstract), `too_long`, or `missing` | enrichment (enrich_* scripts) |
| `near_duplicate_group` | integer, nullable | Group identifier for near-identical content published under several DOIs; null for ungrouped works | quality filtering (corpus_filter.py) |
| `semantic_outlier_dist` | float, nullable | Distance to the corpus embedding centroid, computed for the semantic-outlier flag (absent from corpus builds predating this pipeline stage) | quality filtering (corpus_filter.py) |
| `in_v1` | boolean | Version tracking: work present in the v1.0 submission corpus (absent from corpus builds predating this pipeline stage) | quality filtering (corpus_filter.py) |
| `is_flagged` | boolean | Any quality flag raised; the refined subset is `df[~df['is_flagged'] | df['is_protected']]` | quality filtering (corpus_filter.py) |
| `flag_reason` | string | Comma-separated list of raised quality flags (missing_metadata, no_abstract_irrelevant, title_blacklist, citation_isolated_old, semantic_outlier, llm_irrelevant); empty when unflagged | quality filtering (corpus_filter.py) |
| `is_protected` | boolean | Protection from removal (key papers kept despite flags) | quality filtering (corpus_filter.py) |
| `protection_reason` | string, nullable | Why the work is protected (citation count, seed list, ...) (absent from corpus builds predating this pipeline stage) | quality filtering (corpus_filter.py) |

: Variables of `climate_finance_corpus.csv`. The table is generated from the deposit column contract (`scripts/deposit_variables.py`), which the export script enforces at write time. {#tbl-variables}
