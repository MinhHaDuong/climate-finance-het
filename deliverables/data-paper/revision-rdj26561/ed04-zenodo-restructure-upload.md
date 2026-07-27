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
   `data/products/`; `codebook.md`, `datapackage.json` and `croissant.json`
   in `data/products/`). The build validates the deposited CSV against its own
   `datapackage.json` and aborts rather than package a file that contradicts
   the schema it publishes (ticket 0354), so a successful build is also a
   passed data check.
2. Zenodo → record 19236130 → **New version**. Remove the old tarball, upload
   the new one.
3. Replace the record description with the text below; keep title, authors,
   license (data CC BY 4.0, code MIT), and keywords unchanged.
4. Fill the record metadata below (ORCID, funding). It persists across
   versions, so this is a one-time pass.
5. Set the version field (suggested: `v1.1.1` — same data, restructured
   packaging + codebook) and publish.
6. Check that the paper's cited DOI still resolves; the paper cites
   10.5281/zenodo.19236130 — if the journal prefers, switch the citation to
   the concept DOI or the new version DOI at proof stage.

## Record metadata (author, one pass)

Typed into the Zenodo form by hand: the upload is a web click-path, so no
repo-side metadata file is read. These three items are the whole list.

- **ORCID** on the author entry: `0000-0001-9988-2100`. Already carried by the
  paper front matter (`deliverables/data-paper/data-paper.qmd:5`); the Zenodo
  record is the only other place it belongs.
- **Funding**: CNRS. Zenodo's funder picker resolves either identifier —
  ROR `https://ror.org/02feahw73`, Crossref Funder ID
  `10.13039/501100004794` (verified against both registries 2026-07-27; the ROR
  record carries the same fundref ID). Recurring institutional support with no
  grant number: leave the award field empty rather than inventing one.
- **Related identifier** — `IsSupplementTo` the journal article, added **at
  proof stage**: RDJ4HSS has not assigned the article DOI yet, so the field
  cannot be filled on this version. This is the relation that makes the
  paper↔data link machine-traversable, which is what a data journal indexes on.

Do **not** hand-add the version relation. Zenodo sets `IsVersionOf` /
`HasVersion` between the concept DOI and each version DOI itself when you use
the **New version** button; adding it manually duplicates the chain.

## Record description (new version)

Reproducibility archive for "A Curated Corpus of Climate Finance Literature,
1990–2024: Six Sources, Multilingual Retrieval, and Grey Literature" (Research
Data Journal for the Humanities and Social Sciences).

The archive is structured in three parts:

- `code/` — full pipeline source: harvesting, merge, deduplication, flagging
  scripts, configuration, and DVC pipeline definitions, with a Makefile
  offering `verify` (checksums), `papers` (render the data paper), and
  `corpus` (full rebuild) targets.
- `data/inputs/` — raw data inputs: the six per-source catalogs
  (`openalex_works.csv`, `istex_works.csv`, `bibcnrs_works.csv`,
  `scispace_works.csv`, `grey_works.csv`, `teaching_works.csv`) as harvested,
  before merge and deduplication — the provenance trail.
- `data/products/` — final data products of the paper:
  `climate_finance_corpus.csv` (42,916 deduplicated works, abstracts stripped
  for redistribution reasons), `codebook.md` (data dictionary: per-column
  type, allowed values, and measured missingness), `embeddings.npz` (38,473
  multilingual 1024-dim vectors, BAAI/bge-m3), and `citations.csv`
  (citation pairs, normalised DOIs).

Changes in this version: package restructured to separate raw inputs from
final products (editorial remark ED-04); added `codebook.md`, the formal data
dictionary for `climate_finance_corpus.csv` (reviewer remark R1-19). Data
files are unchanged from the previous version.

Code: MIT. Data: CC BY 4.0.

## Response-letter bullet (feeds 0283)

> **ED-04 (Zenodo package structure).** We restructured the Zenodo package to
> separate raw data inputs from final data products. The new version of the
> deposit (same concept DOI) contains `data/inputs/` with the six per-source
> catalogs as harvested, and `data/products/` with the paper's outputs
> (`climate_finance_corpus.csv`, `codebook.md`, `embeddings.npz`,
> `citations.csv`); `code/` holds the pipeline source. The archive README and
> the paper's Data section (§3) describe the same layout, and the packaging is
> produced by a build script, so the structure is reproducible rather than
> hand-arranged.
