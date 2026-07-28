#!/usr/bin/env bash
# Build the data paper reproducibility archive for Zenodo.
#
# Produces climate-finance-datapaper.tar.gz containing:
#   code/           — full pipeline source (git archive) + generated figures/tables,
#                     all at their repo paths so deliverables/ works as it does here
#   data/inputs/    — raw data inputs (per-source catalogs, pre-merge)
#   data/products/  — final data products of the paper (corpus CSV without
#                     abstracts, embeddings, citations, and the
#                     machine-readable descriptor datapackage.json)
# Raw-vs-product split per RDJ-26561 remark ED-04 (ticket 0280).
# The build validates the deposited CSV against its own datapackage.json and
# aborts on any violation (ticket 0354).
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

# Phase-2 render inputs that `git archive` cannot ship because they are
# gitignored regenerables. Mirrored into the code tree at their repo paths by
# `cp --parents`, so this array is both the manifest and the layout. Guarded by
# tests/test_archive_script_paths — each path must resolve to a real file, so a
# renamed figure cannot silently strand the archive. Build them first with
# `make corpus-tables figures-datapaper`.
#
# Figures only: the tables the paper includes are discovered below from its own
# {{< include >}} directives, which cannot go stale the way a hand-kept list can.
DATAPAPER_FILES=(
    deliverables/_shared/figures/fig_bars.png
)

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

# Machine-readable descriptor of the CSV just written, emitted beside it and
# then enforced against it (ticket 0354). The gate is deliberately here rather
# than only in `make deposit-validate`: the archive must not be packageable
# while the deposited bytes contradict the schema it publishes. `set -e` aborts
# the build on a non-zero validate.
echo "  Emitting the deposit descriptor (datapackage.json)..."
PYTHONPATH="scripts:libs/openalex-corpus/src${PYTHONPATH:+:$PYTHONPATH}" \
    uv run --env-file .env python scripts/figures/export_datapackage.py \
        --input "$TMP/data/products/climate_finance_corpus.csv" \
        --output "$TMP/data/products/datapackage.json"

echo "  Validating the deposited CSV against its own datapackage.json..."
uv run --env-file .env frictionless validate "$TMP/data/products/datapackage.json"

echo "  Copying final products (embeddings, citations)..."
cp -L "$DATA_DIR/embeddings.npz" "$TMP/data/products/"
cp -L "$DATA_DIR/citations.csv" "$TMP/data/products/"
# Retrieval-protocol appendix (ticket 0329): the paper points referees here for
# the query fields, per-tier term counts, and the grey-literature enumeration.
cp "$PROJ_ROOT/deliverables/_shared/tables/tab_retrieval_protocol.csv" "$TMP/data/products/"
cp "$PROJ_ROOT/deliverables/_shared/tables/tab_retrieval_protocol.md" "$TMP/data/products/"
# Reranker human-validation evidence (ticket 0372): §2.3 quotes AUC = 0.818
# and names these four files; the per-quintile rate table is what the AUC
# recomputes from, the sample sheets are the surviving grading record.
cp "$PROJ_ROOT/deliverables/_shared/tables/tab_reranker_validation.csv" "$TMP/data/products/"
# Removal ablation (ticket 0337): what the filter removes, per stratum.
cp "$PROJ_ROOT/deliverables/_shared/tables/tab_filter_ablation.csv" "$TMP/data/products/"
cp "$PROJ_ROOT/docs/reranker_hitl_stratified.csv" "$TMP/data/products/"
cp -L "$DATA_DIR/reranker_hitl_review.csv" "$TMP/data/products/"
cp -L "$DATA_DIR/reranker_calibration.csv" "$TMP/data/products/"

echo "  Copying raw inputs (per-source catalogs)..."
# One catalog per corpus source (utils.SOURCE_NAMES). Pinned by
# test_datapaper_archive_layout.py so the deposit never ships fewer catalogs
# than the paper claims sources (ticket 0327).
for src in openalex istex bibcnrs scispace grey teaching unfccc oecd; do
    cp -L "$DATA_DIR/${src}_works.csv" "$TMP/data/inputs/" 2>/dev/null || true
done

# ── Generated render inputs (hard fail) ──────────────────
# `git archive` ships every *tracked* file at its repo path, so the data paper
# already arrives as its own Quarto project under deliverables/data-paper/ with
# its own _quarto.yml. What it cannot ship are the Phase-2 artifacts that are
# gitignored because they are regenerable; those are mirrored in here at the
# same repo paths, so the ../_shared/... references in data-paper.qmd resolve.
#
# No repo-wide _quarto.yml is written: the 0226 reorg retired it, and a config
# re-rooting the paper under content/ is what broke this script (ticket 0292).
echo "  Copying generated figures and tables..."
mkdir -p "$TMP/code/deliverables/_shared/figures" "$TMP/code/deliverables/_shared/tables"
# Loop variable deliberately not `src`: test_datapaper_archive_layout.py finds
# the per-source catalog loop by taking the first line matching "for src in",
# so a second one here would shadow the guard depending on line order.
for f in "${DATAPAPER_FILES[@]}"; do
    cp --parents "$f" "$TMP/code/"
done

# Stage exactly the tables the paper includes, discovered from its own
# {{< include >}} directives. The hand-kept list had already gone stale
# (tab_variables.md was missing) and would have gone stale again with
# tab_corpus_flow.md (ticket 0327). They land at the repo-mirrored path the
# include directives themselves name, so discovery and destination agree.
grep -o '{{< include [^ ]*tables/[^ ]*\.md' deliverables/data-paper/data-paper.qmd \
  | sed 's|.*tables/||' | sort -u | while read -r tbl; do
    cp "deliverables/_shared/tables/$tbl" "$TMP/code/deliverables/_shared/tables/"
done

# Reviewer entry point. The repo's own Makefile rides along in the git archive
# and is the Phase-2 build; this one is the three-target reviewer interface,
# invoked as `make -f Makefile.datapaper`.
cp build/templates/Makefile.datapaper "$TMP/code/Makefile.datapaper"

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
