# ED-04 — Zenodo package restructure: upload kit (ticket 0280)

One version bump groups the package restructure (ED-04, ticket 0280) and the
codebook (R1-19, ticket 0287). Uploading is the author's act; everything below
is prepared.

## Invariant

Concept DOI stays stable. Use Zenodo's **New version** button on the existing
record (version DOI 10.5281/zenodo.19236130) — never create a new record. The
new version receives its own version DOI; the concept DOI keeps resolving to
the latest version.

## Steps (author)

1. Rebuild the archive at the merged commit:
   `make check-corpus corpus-tables figures-datapaper && bash build/build_datapaper_archive.sh`
   → `climate-finance-datapaper.tar.gz` (layout: `code/`, `data/inputs/`,
   `data/products/`; codebook.md in `data/products/`).
2. Zenodo → record 19236130 → **New version**. Remove the old tarball, upload
   the new one.
3. Replace the record description with the text below. Retitle the record
   "Six Sources" → "**Eight Sources**" (ticket 0327): the v2 corpus adds the
   curated UNFCCC and OECD DAC layers, and the paper's related-dataset entry
   and suggested citation now carry the eight-source title. Authors, license
   (data CC BY 4.0, code MIT), and keywords stay unchanged.
4. Set the version field (suggested: `v2.0` — new corpus harvest, eight
   sources, restructured packaging + codebook) and publish.
5. Check that the paper's cited DOI still resolves; the paper cites
   10.5281/zenodo.19236130 — if the journal prefers, switch the citation to
   the concept DOI or the new version DOI at proof stage.

## Record description (new version)

Reproducibility archive for "A Curated Corpus of Climate Finance Literature,
1990–2024: Eight Sources, Multilingual Retrieval, and Grey Literature"
(Research Data Journal for the Humanities and Social Sciences).

The archive is structured in three parts:

- `code/` — full pipeline source: harvesting, merge, deduplication, flagging
  scripts, configuration, and DVC pipeline definitions, with a Makefile
  offering `verify` (checksums), `papers` (render the data paper), and
  `corpus` (full rebuild) targets.
- `data/inputs/` — raw data inputs: the eight per-source catalogs
  (`openalex_works.csv`, `istex_works.csv`, `bibcnrs_works.csv`,
  `scispace_works.csv`, `grey_works.csv`, `teaching_works.csv`,
  `unfccc_works.csv`, `oecd_works.csv`) as harvested, before merge and
  deduplication — the provenance trail.
- `data/products/` — final data products of the paper:
  `climate_finance_corpus.csv` (43,179 deduplicated works, abstracts stripped
  for redistribution reasons), `codebook.md` (data dictionary: per-column
  type, allowed values, and measured missingness), `embeddings.npz` (38,736
  multilingual 1024-dim vectors, BAAI/bge-m3), and `citations.csv`
  (citation pairs, normalised DOIs).

Changes in this version: package restructured to separate raw inputs from
final products (editorial remark ED-04); added `codebook.md`, the formal data
dictionary for `climate_finance_corpus.csv` (reviewer remark R1-19); the
corpus is rebuilt on the v2 harvest, which adds the curated UNFCCC and OECD
DAC key-document layers, so `data/inputs/` carries eight per-source catalogs
and the data files change with it.

Code: MIT. Data: CC BY 4.0.

## Response-letter bullet (feeds 0283)

> **ED-04 (Zenodo package structure).** We restructured the Zenodo package to
> separate raw data inputs from final data products. The new version of the
> deposit (same concept DOI) contains `data/inputs/` with the eight per-source
> catalogs as harvested, and `data/products/` with the paper's outputs
> (`climate_finance_corpus.csv`, `codebook.md`, `embeddings.npz`,
> `citations.csv`); `code/` holds the pipeline source. The archive README and
> the paper's Data section (§3) describe the same layout, and the packaging is
> produced by a build script, so the structure is reproducible rather than
> hand-arranged.
