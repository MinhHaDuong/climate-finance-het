#!/usr/bin/env bash
# Build the analysis reproducibility archive (Phase 2).
# Entry point: `make archive-analysis`, which builds the outputs first.
#
# Produces climate-finance-analysis.tar.gz containing:
#   data/     — Phase 1 contract data (refined_works, embeddings)
#   scripts/  — analysis scripts that produce figures + tables
#   config/   — analysis parameters and frozen v1 data
#
# Prerequisites: make check-manuscript-data + all ANALYSIS_OUTPUTS built
# Usage: bash build/build_analysis_archive.sh

set -euo pipefail

PROJ_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="$PROJ_ROOT/data/catalogs"
ARCHIVE=climate-finance-analysis
TMP="/tmp/$ARCHIVE"

# Analysis outputs — must match Makefile ANALYSIS_OUTPUTS
ANALYSIS_OUTPUTS=(
    deliverables/_shared/figures/fig_bars_v1.png
    deliverables/_shared/figures/fig_composition.png
    deliverables/_shared/tables/tab_venues.md
    data/derived/tables/tab_alluvial.csv
    data/derived/tables/tab_core_shares.csv
    data/derived/tables/tab_bimodality.csv
    data/derived/tables/tab_axis_detection.csv
    data/derived/tables/tab_pole_papers.csv
    data/derived/tables/cluster_labels.json
)

echo "=== Building analysis archive ==="

rm -rf "$TMP"
# Output directories the archived Makefile writes into. They must pre-exist:
# validate_io() in scripts/script_io_args.py requires the output's parent
# directory, and the recipes mirror the repo paths that expected_outputs.md5
# records — not a re-rooted content/ tree (ticket 0292).
mkdir -p "$TMP/data/catalogs" \
         "$TMP/data/derived/tables" \
         "$TMP/scripts" \
         "$TMP/config" \
         "$TMP/deliverables/_shared/figures" \
         "$TMP/deliverables/_shared/tables"

cd "$PROJ_ROOT"

# Phase 1 contract data (dereference DVC symlinks)
cp -L "$DATA_DIR/refined_works.csv"     "$TMP/data/catalogs/"
cp -L "$DATA_DIR/refined_embeddings.npz" "$TMP/data/catalogs/"

# Scripts needed to build figures + tables.
# Full repo-relative paths, mirrored into the archive with `cp --parents` so the
# archived tree matches the repo: tier-2 libs stay flat at scripts/ while the
# reorg'd entry points keep their scripts/{figures,analysis}/ subdir (epic 0240).
# The archived Makefile.analysis-manuscript invokes them at these mirrored paths,
# and PYTHONPATH=scripts (ticket 0253) still resolves their flat `from utils …`
# imports. Guarded by tests/test_archive_script_paths — every path here must
# resolve to a real file, so the next mover cannot silently strand the cp.
SCRIPTS=(
    scripts/utils.py
    # Shared --input/--output parser. Every entry point below calls
    # parse_io_args at the top of main, so without it the archived scripts fail
    # at import; the archive shipped without it until ticket 0292.
    scripts/script_io_args.py
    scripts/pipeline_loaders.py
    scripts/pipeline_io.py
    scripts/pipeline_progress.py
    scripts/pipeline_text.py
    scripts/plot_style.py
    scripts/figures/plot_fig1_bars.py
    scripts/figures/plot_fig2_composition.py
    scripts/analysis/compute_clusters.py
    scripts/analysis/build_het_core.py
    scripts/figures/export_core_venues_markdown.py
    scripts/analysis/summarize_core_venues.py
    scripts/figures/export_tab_venues.py
    # Shared helpers the two venue emitters import. _venue_naming.py was
    # missing until ticket 0339, so the archived export_core_venues_markdown.py
    # could not import it (the Makefile prerequisite the escaper added is what
    # surfaced it).
    scripts/_venue_naming.py
    scripts/_markdown_table.py
    scripts/figures/export_citation_coverage.py
    scripts/analysis/analyze_bimodality.py
    scripts/figures/plot_bimodality.py
    scripts/figures/plot_bimodality_lexical.py
    scripts/figures/plot_bimodality_keywords.py
)
for src in "${SCRIPTS[@]}"; do
    cp --parents "$src" "$TMP/"
done

# openalex-corpus convention package — imported as source via PYTHONPATH
# (ticket 0253), not installed as a wheel (removed from uv.lock). The bundled
# scripts (utils.py, pipeline_text.py, …) import openalex_corpus, so the archive
# must carry the package source, matching the Makefile/Dockerfile source root
# libs/openalex-corpus/src.
mkdir -p "$TMP/libs"
cp -r libs/openalex-corpus "$TMP/libs/"
rm -rf "$TMP/libs/openalex-corpus/__pycache__" \
       "$TMP/libs/openalex-corpus/src/openalex_corpus/__pycache__" \
       "$TMP/libs/openalex-corpus/tests"

# Config + build infrastructure
cp config/analysis.yaml            "$TMP/config/"
cp config/v1_tab_alluvial.csv      "$TMP/config/"
cp config/v1_cluster_labels.json   "$TMP/config/"
cp config/v1_cluster_centroids.npy "$TMP/config/"
cp build/templates/Makefile.analysis-manuscript "$TMP/Makefile"
cp pyproject.toml uv.lock          "$TMP/"
echo 'CLIMATE_FINANCE_DATA=data' > "$TMP/.env"

# README + container file for reviewers
cp build/templates/README-analysis.md  "$TMP/README.md"
cp build/templates/Dockerfile.analysis "$TMP/Dockerfile"

# Expected output checksums — reviewers verify with: make && make verify
cd "$PROJ_ROOT"
md5sum "${ANALYSIS_OUTPUTS[@]}" > "$TMP/expected_outputs.md5"

# Tarball
echo "=== Creating tarball ==="
tar czf "$PROJ_ROOT/$ARCHIVE.tar.gz" -C /tmp "$ARCHIVE"
echo "=== Analysis archive ==="
du -h "$PROJ_ROOT/$ARCHIVE.tar.gz"
echo "Files: $(tar tzf "$PROJ_ROOT/$ARCHIVE.tar.gz" | wc -l)"
rm -rf "$TMP"
echo "Done: $ARCHIVE.tar.gz"
