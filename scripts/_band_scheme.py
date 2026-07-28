"""Lineage-band scheme for the citation genealogy: how many bands, and which
colour and label belongs to each.

Neutral module (the 0250/0254/0286 pattern, as `_tradition_style.py`) so the
model (`analysis/analyze_genealogy.py`) and both renderers
(`figures/plot_genealogy.py`, `figures/plot_genealogy_html.py`) share one
definition without a script-to-script import. It lives at the `scripts/` root
because that is the only directory every subpackage sees: `PYTHONPATH` carries
the flat root, never `scripts/analysis/` or `scripts/figures/`, so
`from analyze_genealogy import ...` would raise `ModuleNotFoundError` under the
Makefile's own invocation.

The three constants were hand-copied into all three modules, each copy carrying
a comment saying it must match the others. Re-theming the static PNG without
touching the HTML renderer produced two figures disagreeing on which colour
meant which lineage — at exit 0, with no exception and no missing target
(ticket 0571). `tests/test_band_scheme_single_source.py` now fails if a module
re-introduces a local copy.

`CDM_CLUSTER` deliberately stays in `analyze_genealogy.py`: it names a KMeans
cluster id used to *assign* lineages, not part of the presentation scheme the
renderers read.
"""

#: Number of lineage bands the genealogy is drawn in.
N_COMMUNITIES = 3

#: Band id → display label. Ordered as the bands are stacked.
BAND_NAMES = {0: "CDM / Kyoto heritage", 1: "Accountability pole", 2: "Efficiency pole"}

#: Band id → hex colour, shared by the static PNG and the interactive HTML.
BAND_COLORS_RGB = {0: "#F4A261", 1: "#457B9D", 2: "#E63946"}
