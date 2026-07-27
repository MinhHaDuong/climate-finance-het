"""Shared vocabulary for TF-IDF cluster and community labelling (ticket 0321).

Two consumers label groups of works by their distinctive TF-IDF terms and must
agree on what counts as distinctive: `compute_clusters` (semantic k-means
clusters, whose top terms label the alluvial panels) and `analyze_global_map`
(Louvain citation communities, whose top terms label the fig_global_map_direct
nodes). A term suppressed in one and kept in the other would make the two
disagree about the same corpus. The clusters' most visible consumer used to be
the fig_sem_composition subtitles, deleted with that figure in 0359; the shared
vocabulary still matters because both labellers describe one corpus.

This module exists because `analyze_global_map` was importing these names from
`compute_clusters`, which is a Tier-3 entry point. The `scripts/` reorg (epic
0240) rests on Tier-3 files being import-leaves — nothing may import them by
flat name, or moving them between phase directories breaks the importer. A
neutral `_`-private module at the flat library surface is the 0250/0254
resolution for that dual-role hazard; the alternative, reclassifying
`compute_clusters` as Tier-2, would have been the escape hatch rather than the
fix, since it is an entry point that merely happened to own two helpers.

No I/O, no config, no corpus access — vocabulary only.
"""

import re

# Terms too common in a climate-finance corpus to distinguish anything within
# it. "climate" and "finance" describe every work in the corpus, so they carry
# no information about which group a work belongs to.
LABEL_STOPWORDS = {
    "climate", "climate change", "change", "finance", "financial", "carbon",
    "emission", "emissions", "mitigation", "adaptation",
    "paper", "study", "analysis", "results", "approach", "article", "research",
    "literature", "review", "data", "work", "based", "findings", "using",
    "new", "use", "used", "model", "evidence", "impact", "effects", "effect",
    "role", "case", "sector", "risk", "market", "markets", "investment",
    "countries", "country", "policy", "policies", "global", "world",
    "international", "national", "economic", "economics", "development",
    "blockchain", "esg", "theory", "usd",
    "pdf", "http", "https", "www", "vol", "pp",
}

# Expansions collapsed to their acronym before vectorising, so a work writing
# "clean development mechanism" and one writing "CDM" contribute to the same
# term rather than splitting its weight across two.
ACRONYM_EXPANSIONS = {
    r"\benvironmental[,]?\s+social\s+(?:and\s+)?governance\b": "ESG",
    r"\bclean\s+development\s+mechanism\b": "CDM",
    r"\bemissions?\s+trading\s+(?:system|scheme)\b": "ETS",
    r"\bunited\s+nations\s+framework\s+convention\s+on\s+climate\s+change\b": "UNFCCC",
    r"\bconference\s+of\s+(?:the\s+)?parties\b": "COP",
    r"\bgreen\s+climate\s+fund\b": "GCF",
    r"\bsustainable\s+development\s+goals?\b": "SDGs",
    r"\bnationally\s+determined\s+contributions?\b": "NDCs",
}


def collapse_acronyms(text):
    """Replace known expansions with their acronyms to avoid double-counting."""
    for pattern, acronym in ACRONYM_EXPANSIONS.items():
        text = re.sub(pattern, acronym, text, flags=re.IGNORECASE)
    return text
