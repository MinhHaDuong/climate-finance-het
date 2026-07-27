#!/usr/bin/env bash
# Build the manuscript reproducibility archive (Phase 4).
#
# Produces climate-finance-manuscript.tar.gz containing:
#   deliverables/  — manuscript source and the shared assets it references,
#                    mirrored at their repo paths so the ../_shared/ relative
#                    references in manuscript.qmd resolve unchanged
#   expected-manuscript.pdf — pre-built reference PDF
#
# The archive mirrors the repo layout (ticket 0226): each deliverable is its own
# Quarto project carrying its own _quarto.yml, and shared assets live one level
# up in deliverables/_shared/. Flattening this into the old content/ tree breaks
# every ../_shared/... reference in the manuscript, which is what ticket 0292
# fixed. Mirror with `cp --parents`; never re-root.
#
# Prerequisites: manuscript PDF built (make manuscript)
# No Python needed — only Quarto + XeLaTeX.
# Usage: bash build/build_manuscript_archive.sh

set -euo pipefail

PROJ_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARCHIVE=climate-finance-manuscript
TMP="/tmp/$ARCHIVE"

# Every input the archive ships, at its repo-relative path. `cp --parents`
# mirrors each one into the archive, so this array is simultaneously the
# manifest and the layout. Guarded by tests/test_archive_script_paths — each
# path must resolve to a real file, so a moved asset cannot silently strand
# the archive. Keep the array free of parentheses.
MANUSCRIPT_FILES=(
    deliverables/manuscript/manuscript.qmd
    deliverables/manuscript/manuscript-vars.yml
    deliverables/manuscript/_quarto.yml
    deliverables/manuscript/author-footnote.tex
    deliverables/_shared/figures/fig_bars_v1.png
    deliverables/_shared/figures/fig_breaks.png
    deliverables/_shared/figures/fig_composition.png
    deliverables/_shared/tables/tab_venues.md
    deliverables/_shared/bibliography/main.bib
    deliverables/_shared/bibliography/oeconomia.csl
)

echo "=== Building manuscript archive ==="

cd "$PROJ_ROOT"

rm -rf "$TMP"
mkdir -p "$TMP"

for src in "${MANUSCRIPT_FILES[@]}"; do
    cp --parents "$src" "$TMP/"
done

# Pre-built output PDF, kept at the archive root — away from the Quarto project
# directory, so `quarto render` never treats it as its own stale output.
cp deliverables/manuscript/manuscript.pdf "$TMP/expected-manuscript.pdf"

# Build infrastructure (no Python needed)
cp build/templates/Makefile.manuscript  "$TMP/Makefile"
cp build/templates/README-manuscript.md "$TMP/README.md"

# Record toolchain versions used to build the shipped PDF
printf 'Quarto %s\n%s\n' "$(quarto --version)" "$(xdvipdfmx --version 2>&1 | head -1)" > "$TMP/TOOLCHAIN.txt"

# Input checksums — reviewers verify with: make && make verify
# Listed at the same mirrored paths the Makefile builds from.
cd "$TMP" && md5sum "${MANUSCRIPT_FILES[@]}" > checksums.md5

# Tarball
echo "=== Creating tarball ==="
tar czf "$PROJ_ROOT/$ARCHIVE.tar.gz" -C /tmp "$ARCHIVE"
echo "=== Manuscript archive ==="
du -h "$PROJ_ROOT/$ARCHIVE.tar.gz"
echo "Files: $(tar tzf "$PROJ_ROOT/$ARCHIVE.tar.gz" | wc -l)"
rm -rf "$TMP"
echo "Done: $ARCHIVE.tar.gz"
