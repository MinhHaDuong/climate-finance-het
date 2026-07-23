"""Tradition labels and colors for the pre-2007 network figures.

Neutral module (0250/0254 pattern) so both the canonical figure
(`plot_fig_traditions.py`) and the citer-limited variant
(`plot_fig_traditions_pre2008_citers.py`) share one style definition
without a script-to-script import (Tier-2 surface rule, ticket 0286).
The shared community registry (`config/community_registry.yml`, ticket
0307) overrides these labels/colors when present.
"""

TRADITION_LABELS = {
    "pricing": "Environmental economics\n(pricing & quantities)",
    "cdm":     "Development economics\n(CDM & carbon markets)",
    "unfccc":  "Burden-sharing\n(UNFCCC & institutions)",
    "other":   None,
}

TRADITION_COLORS = {
    "pricing": "#1a6496",
    "cdm":     "#e07b39",
    "unfccc":  "#4a9e6b",
    "other":   "#DDDDDD",
}

TRADITION_EDGE_COLORS = {
    "pricing": "#1a6496",
    "cdm":     "#e07b39",
    "unfccc":  "#4a9e6b",
    "other":   "#CCCCCC",
}
