"""Central community/tradition name + color registry for network figures.

Loads config/community_registry.yml (one concept = one exact label = one
color across all figures) and exposes small helpers shared by the corpus
network figures (ticket 0307).
"""

import os

import yaml

_REG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..",
    "config", "community_registry.yml")

with open(_REG_PATH) as _f:
    _REG = yaml.safe_load(_f)

CONCEPTS = _REG["concepts"]
LABEL_OVERRIDES = _REG.get("label_overrides", {})


def concept(key):
    """Return (label, color) for a concept key."""
    c = CONCEPTS[key]
    return c["label"], c["color"]


def tradition_concepts():
    """Map tradition key ('pricing', 'cdm', 'unfccc') -> (label, color)."""
    return {t: concept(k) for t, k in _REG["traditions"].items()}


def figure_communities(figure_name):
    """Map Louvain community id (int) -> (label, color) for a figure."""
    fig = _REG["figures"].get(figure_name, {})
    return {int(cid): concept(k) for cid, k in fig.items()}


def override_label(text):
    """Apply the registry's broken-metadata label overrides.

    Applied by the render pass AFTER author-year formatting; unknown labels
    pass through unchanged.
    """
    return LABEL_OVERRIDES.get(text, text)


def short_label(text):
    """'Axel Michaelowa 2003' -> 'A. Michaelowa 2003' (first names to initials)."""
    toks = text.split()
    if len(toks) < 3 or not toks[-1][:4].isdigit():
        return text
    head = [t if (len(t) <= 2 and t.endswith(".")) else t[0] + "."
            for t in toks[:-2]]
    return " ".join(head + toks[-2:])


def surname_label(text):
    """'William D. Nordhaus 2015' -> 'Nordhaus 2015' (surname + year only)."""
    toks = text.split()
    if len(toks) >= 2 and toks[-1][:4].isdigit():
        return " ".join(toks[-2:])
    return text
