# Data paper reproducibility archive

Companion to: Ha-Duong M. (2026) "A Curated Corpus of Climate Finance
Literature, 1990–2024: Six Sources, Multilingual Retrieval, and Grey
Literature", Research Data Journal for the Humanities and Social Sciences.

Dataset DOI: [10.5281/zenodo.19236130](https://doi.org/10.5281/zenodo.19236130)

## Archive structure

```
climate-finance-datapaper/
  code/                    # Full pipeline source (git archive of HEAD)
    Makefile.datapaper     # Entry point — three targets below
    content/               # Data paper source, figures, tables, vars
    scripts/               # Pipeline + analysis scripts
    config/                # Query taxonomy, source configuration
    dvc.yaml, dvc.lock     # Pipeline definitions
    checksums-data.md5     # Reference checksums for data/
  data/
    inputs/                # Raw data inputs: per-source catalogs, pre-merge
      *_works.csv                # openalex, istex, bibcnrs, scispace, grey, teaching
    products/              # Final data products of this paper
      climate_finance_corpus.csv # 42,922 works (abstracts stripped)
      codebook.md                # Data dictionary: per-column type, values, missingness
      embeddings.npz             # 38,479 multilingual vectors (1024-dim)
      citations.csv              # 968,871 citation pairs
```

`data/inputs/` holds the raw harvests as retrieved from each source, before
merge and deduplication — the provenance trail. `data/products/` holds the
curated outputs this paper describes; most users need only `products/`.

## Prerequisites

- [Quarto](https://quarto.org/docs/get-started/) + XeLaTeX (for `make papers`)
- GNU coreutils (for `make verify`; macOS: `brew install coreutils`)

## Usage

```bash
tar xzf climate-finance-datapaper.tar.gz
cd climate-finance-datapaper/code
make -f Makefile.datapaper verify   # check data checksums
make -f Makefile.datapaper papers   # render data-paper.pdf
```

## Targets

**`make verify`** — checks shipped data files against MD5 checksums.
No Python, no internet needed.

**`make papers`** — renders `data-paper.pdf` from frozen variables and
pre-built figures. No pipeline, no API calls, no corpus data needed.
Output: `output/content/data-paper.pdf`.

**`make corpus`** — runs the full DVC pipeline (`dvc repro`). Included as
process documentation; a full rebuild requires API access and takes 4–6
hours. See `dvc.yaml` and `scripts/` for the pipeline logic.

## Usage examples

The following scripts read from the corpus CSV and produce the data
paper's figure and tables. They illustrate how to work with the dataset:

| Script | Output | What it does |
|--------|--------|--------------|
| `scripts/plot_fig_bars.py` | `fig_bars.png` | Annual publication volume bar chart |
| `scripts/figures/export_corpus_table.py` | `tab_corpus_sources.md` | Per-source quality and completeness table |
| `scripts/figures/export_language_table.py` | `tab_languages.md` | Language distribution table |

## License

Code: MIT. Data: CC BY 4.0.
