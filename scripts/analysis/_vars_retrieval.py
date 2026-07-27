"""Retrieval-protocol variables for the data paper (ticket 0329).

All four RDJ-26561 external reviewers asked for the numbers the six-flag
filter actually used. They are configuration values, not corpus measurements,
so this collector reads `config/corpus_filter.yaml` and needs no Phase-1 data
— which is why it lives here rather than among compute_vars' corpus readers.

Reading them at build time rather than typing them into the prose is what
keeps the paper and the pipeline from drifting apart.
"""

from filter_flags import _load_config

# The variables retrieval_protocol_stats emits. compute_vars splices this into
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


def _pct0(value: float) -> str:
    """Percentage on a 0--100 scale, no decimals."""
    return f"{value:.0f}"


def retrieval_protocol_stats(v: dict) -> None:
    """Add the filtering thresholds the data paper's §2.2 quotes."""
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
