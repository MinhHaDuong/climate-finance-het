"""Filtering thresholds read from config rather than typed into prose (ticket 0329).

All four RDJ-26561 external reviewers asked for the numbers the six-flag
filter actually used. They are configuration values, not corpus measurements,
so this collector reads `config/corpus_filter.yaml` and needs no Phase-1 data
— which is why it lives here rather than among compute_vars' corpus readers.

Reading them at build time rather than typing them into the prose is what
keeps the documents and the pipeline from drifting apart. Two documents draw
on this collector and they quote different subsets, so the variable names are
grouped in two lists: `DOC_VARS` may not register a variable its document's
prose never uses, and `test_doc_vars_no_extras` enforces that.
"""

from filter_flags import _load_config

# The §2.2 thresholds the data paper quotes. compute_vars splices this into
# DOC_VARS, so the emitter and the registration cannot drift apart.
RETRIEVAL_VARS = [
    "filter_outlier_sigma",
    "filter_reranker_threshold",
    "neardup_min_group_size",
    "neardup_overlap_pct",
    "neardup_prefix_chars",
    "protect_min_cited",
    "protect_min_sources",
]

# Per-flag rule parameters that only the corpus report narrates, flag by flag
# (ticket 0357). Kept apart from RETRIEVAL_VARS rather than merged into it
# because the data paper does not report them, and a variable listed for a
# document that never uses it fails the registry guard.
#
# The concept-group *names* are a variable and not prose for a reason: the
# report had them as "climate, finance, development, environment", which are
# the query-time groups of `config/openalex_queries.yaml`, not the four that
# Flag 6 scores against. The two sets diverged when ecology stopped counting as
# a concept group and nothing moved the prose.
FLAG_RULE_VARS = [
    "filter_citation_max_year",
    "filter_concept_group_n",
    "filter_concept_groups",
    "filter_min_concept_groups",
]


def _pct0(value: float) -> str:
    """Percentage on a 0--100 scale, no decimals."""
    return f"{value:.0f}"


def retrieval_protocol_stats(v: dict) -> None:
    """Add every filtering threshold a deliverable quotes from config."""
    cfg = _load_config()
    v["filter_outlier_sigma"] = str(cfg["semantic_outlier"]["sigma"])
    v["filter_reranker_threshold"] = str(cfg["llm_relevance"]["reranker_threshold"])

    nd = cfg["near_duplicate"]
    v["neardup_prefix_chars"] = str(nd["prefix_length"])
    v["neardup_min_group_size"] = str(nd["min_group_size"])
    v["neardup_overlap_pct"] = _pct0(100 * nd["abstract_overlap_threshold"])

    protection = cfg["protection"]
    v["protect_min_cited"] = str(protection["min_cited_by"])
    v["protect_min_sources"] = str(protection["min_source_count"])

    groups = list(cfg["concept_groups"])
    v["filter_concept_groups"] = ", ".join(groups)
    v["filter_concept_group_n"] = str(len(groups))
    v["filter_min_concept_groups"] = str(cfg["min_concept_groups"])
    v["filter_citation_max_year"] = str(cfg["citation_isolation"]["max_year"])
