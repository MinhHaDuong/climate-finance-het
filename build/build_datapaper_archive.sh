#!/usr/bin/env bash
# Build the data paper reproducibility archive for Zenodo.
#
# Produces climate-finance-datapaper.tar.gz containing:
#   code/           — full pipeline source (git archive) + pre-built figures/tables
#   data/inputs/    — raw data inputs (per-source catalogs, pre-merge)
#   data/products/  — final data products of the paper (corpus CSV without
#                     abstracts, embeddings, citations, codebook)
# Raw-vs-product split per RDJ-26561 remark ED-04 (ticket 0280).
#
# Prerequisites: make check-corpus corpus-tables figures-datapaper
# Usage: bash build/build_datapaper_archive.sh

set -euo pipefail

# PATH guard: ensure uv is findable in non-interactive shells (ssh, cron, systemd).
command -v uv 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"

PROJ_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARCHIVE=climate-finance-datapaper
TMP="/tmp/$ARCHIVE"
# Honour the same data-root override as the Python pipeline (worktrees, smoke).
DATA_DIR="${CLIMATE_FINANCE_DATA:-$PROJ_ROOT/data}/catalogs"

echo "=== Building data paper archive ==="

rm -rf "$TMP"
mkdir -p "$TMP/code" "$TMP/data/inputs" "$TMP/data/products"

# ── Code: pipeline source via git archive ────────────────
echo "  Extracting code from git..."
git -C "$PROJ_ROOT" archive HEAD | tar -x -C "$TMP/code"
rm -rf "$TMP/code/.dvc" "$TMP/code/attic" "$TMP/code/.claude"

# ── Data: deposit files ──────────────────────────────────
echo "  Preparing deposit CSV (dropping abstracts)..."
cd "$PROJ_ROOT"
# Direct script run (no make) — put the source roots on PYTHONPATH so utils /
# openalex_corpus resolve (imported as source, not installed; ticket 0253). cwd
# is $PROJ_ROOT, so the relative roots resolve.
PYTHONPATH="scripts:libs/openalex-corpus/src${PYTHONPATH:+:$PYTHONPATH}" \
    uv run --env-file .env python scripts/figures/export_deposit.py --output "$TMP/data/products/climate_finance_corpus.csv"

echo "  Copying final products (embeddings, citations, codebook)..."
cp -L "$DATA_DIR/embeddings.npz" "$TMP/data/products/"
cp -L "$DATA_DIR/citations.csv" "$TMP/data/products/"
cp "$PROJ_ROOT/deliverables/_shared/tables/codebook.md" "$TMP/data/products/"

echo "  Copying raw inputs (per-source catalogs)..."
for src in openalex istex bibcnrs scispace grey teaching; do
    cp -L "$DATA_DIR/${src}_works.csv" "$TMP/data/inputs/" 2>/dev/null || true
done

# ── Quarto project config: data paper only ───────────────
# The repo _quarto.yml lists all papers; Quarto scans them all even when
# rendering one file. Replace with a minimal config for the data paper.
cat > "$TMP/code/_quarto.yml" << 'YAML'
project:
  type: default
  output-dir: output
  render:
    - content/data-paper.qmd

bibliography: content/bibliography/main.bib

format:
  pdf:
    pdf-engine: xelatex
    cite-method: citeproc
YAML

# ── Figures, tables, vars for rendering (hard fail) ──────
echo "  Copying figures and tables..."
mkdir -p "$TMP/code/content/figures" "$TMP/code/content/tables"
cp deliverables/_shared/figures/fig_bars.png "$TMP/code/content/figures/"
cp deliverables/_shared/tables/tab_corpus_sources.md deliverables/_shared/tables/tab_languages.md \
   "$TMP/code/content/tables/"
cp deliverables/data-paper/data-paper-vars.yml "$TMP/code/content/"

# ── Checksums for make verify ────────────────────────────
echo "  Computing data checksums..."
cd "$TMP/data" && find inputs products -type f | sort | xargs md5sum > "$TMP/code/checksums-data.md5"

# ── Tarball ──────────────────────────────────────────────
echo "=== Creating tarball ==="
tar czf "$PROJ_ROOT/$ARCHIVE.tar.gz" -C /tmp \
    --exclude='__pycache__' --exclude='.venv' \
    "$ARCHIVE"

echo "=== Data paper archive ==="
du -h "$PROJ_ROOT/$ARCHIVE.tar.gz"
echo "Files: $(tar tzf "$PROJ_ROOT/$ARCHIVE.tar.gz" | wc -l)"
rm -rf "$TMP"
echo "Done: $ARCHIVE.tar.gz"
