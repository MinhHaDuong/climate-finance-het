| Group | Variable | Type | Description |
|:----|:------|:----|:-------------------------------|
| Record identity | `source` | string | Primary source catalog for the record's metadata (highest-priority contributing source) |
|  | `source_id` | string | Identifier in the primary source (e.g. OpenAlex work ID) |
|  | `doi` | string, nullable | Digital Object Identifier, when available |
| Bibliographic metadata | `title` | string | Title of the work |
|  | `first_author` | string, nullable | First author name |
|  | `all_authors` | string, nullable | Full author list, separator-joined |
|  | `year` | integer | Publication year |
|  | `journal` | string, nullable | Publication venue (journal, publisher, or repository) |
|  | `language` | string, nullable | Language code (ISO 639-1), detected and normalised |
|  | `keywords` | string, nullable | Keywords, semicolon-separated |
|  | `categories` | string, nullable | Subject categories / concepts from the source catalog |
|  | `cited_by_count` | integer | Citation count (OpenAlex, as of the collection date) |
|  | `affiliations` | string, nullable | Author affiliations, when available |
| Provenance flags | `from_openalex` | boolean | Provenance flag: found in OpenAlex |
|  | `from_istex` | boolean | Provenance flag: found in ISTEX |
|  | `from_bibcnrs` | boolean | Provenance flag: found in bibCNRS |
|  | `from_scispace` | boolean | Provenance flag: found via SciSpace |
|  | `from_grey` | boolean | Provenance flag: grey-literature source |
|  | `from_teaching` | boolean | Provenance flag: teaching canon (syllabi) |
|  | `from_unfccc` | boolean | Provenance flag: curated UNFCCC key document (absent from corpus builds predating this pipeline stage) |
|  | `from_oecd` | boolean | Provenance flag: curated OECD key document (absent from corpus builds predating this pipeline stage) |
|  | `abstract_provenance` | string, nullable | Provenance of the abstract text for curated key documents: `curated`, `reconstructed:lead`, or `reconstructed:exec_summary`; empty elsewhere (absent from corpus builds predating this pipeline stage) |
|  | `keywords_provenance` | string, nullable | Provenance of the keywords for curated key documents: `extracted` or `generated:lexicon`; empty elsewhere (absent from corpus builds predating this pipeline stage) |
|  | `source_count` | integer | Number of sources that contributed the record (sum of the provenance flags) |
| Curation metadata | `abstract_status` | string | Status of the (undistributed) abstract: `original`, `reconstructed` (from OpenAlex inverted index or ISTEX fulltext), `generated` (LLM summary of an oversized abstract), `too_long`, or `missing` |
|  | `near_duplicate_group` | integer, nullable | Group identifier for near-identical content published under several DOIs; null for ungrouped works |
|  | `semantic_outlier_dist` | float, nullable | Distance to the corpus embedding centroid, computed for the semantic-outlier flag (absent from corpus builds predating this pipeline stage) |
|  | `in_v1` | boolean | Version tracking: work present in the v1.0 submission corpus (absent from corpus builds predating this pipeline stage) |
|  | `is_flagged` | boolean | Any quality flag raised; the refined subset is `df[~df['is_flagged'] | df['is_protected']]` |
|  | `flag_reason` | string | Comma-separated list of raised quality flags (missing_metadata, no_abstract_irrelevant, title_blacklist, citation_isolated_old, semantic_outlier, llm_irrelevant); empty when unflagged |
|  | `is_protected` | boolean | Protection from removal (key papers kept despite flags) |
|  | `protection_reason` | string, nullable | Why the work is protected (citation count, seed list, ...) (absent from corpus builds predating this pipeline stage) |

: Variables of `climate_finance_corpus.csv`, by logical group. Generated from the deposit column contract (`scripts/_deposit_variables.py`); per-source provenance, allowed values, and missingness are in the deposited codebook. {#tbl-variables}
