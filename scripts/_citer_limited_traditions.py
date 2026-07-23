"""Citer-limited pre-2007 traditions: shared builder (ticket 0286).

Same co-citation method as `_pre2007_traditions` (top pre-2007 references,
MIN_COCIT threshold, Louvain with the config seed) but the CITING side is
restricted to corpus documents published <= a citer cutoff year. This tests
what the sparse early citation record can establish on its own, without the
benefit of retrospective co-citation by later scholarship — the hardest case
for the corpus's citation layer, and the basis of the R1-14 limitations
demonstration (`compute_network_limitations.py`) and the electronic-supplement
figure (`plot_fig_traditions_pre2008_citers.py`).

Lives in a neutral (non-plot, non-compute) module so both layers import it
without a compute -> plot backward arrow (architecture rule 4).
"""

import re

import pandas as pd
from _pre2007_traditions import (
    TOP_N,
    _build_cocitation_network,
    _load_data,
)
from pipeline_loaders import (
    load_analysis_config,
    load_refined_works,
    pre2007_cutoff_year,
)
from utils import get_logger, normalize_doi

log = get_logger("_citer_limited_traditions")

# Candidate anchor authors of the burden-sharing / equity debate, fixed a
# priori from the intellectual-history record (UNFCCC-period equity
# literature; ticket 0286). Diacritic variants of the same surname count as
# one candidate: 16 distinct candidates.
BURDEN_CANDIDATES = [
    "ringius", "rose", "tol", "banuri", "shukla", "baer", "athanasiou",
    "meyer", "grubb", "elzen", ("hohne", "höhne"), "ott",
    ("oberthur", "oberthür"), "bodansky", "yamin", "depledge",
]
# Institutionalist anchors of the retrospective third tradition — included in
# the bootstrap emergence test (a community anchored by these would also count
# as a governance/equity pole) but NOT candidates of the equity debate itself.
INSTITUTIONALIST_ANCHORS = ["north", "dimaggio", "finnemore"]


def _flatten(candidates):
    out = []
    for c in candidates:
        out.extend(c if isinstance(c, tuple) else (c,))
    return out


BURDEN_RE = re.compile(
    r"\b(" + "|".join(_flatten(BURDEN_CANDIDATES) + INSTITUTIONALIST_ANCHORS)
    + r")\b"
)


def citer_limited_cutoff() -> int:
    """Citer cutoff year from config (network_limitations.citer_cutoff)."""
    return int(load_analysis_config()["network_limitations"]["citer_cutoff"])


def load_citer_limited(citer_cutoff, works_path=None, cit_path=None):
    """Citations restricted to citing documents published <= citer_cutoff.

    Returns (cit, doi_meta, cutoff_year) where cutoff_year is the reference-
    side pre-2007 cutoff shared with the canonical figure.
    """
    cutoff_year = pre2007_cutoff_year(load_analysis_config())
    cit, doi_meta = _load_data(works_path, cit_path)
    if works_path is not None:
        works = pd.read_csv(works_path)
    else:
        works = load_refined_works()
    works["doi_norm"] = works["doi"].apply(normalize_doi)
    works["year_num"] = pd.to_numeric(works["year"], errors="coerce")
    doi_year = works.set_index("doi_norm")["year_num"].to_dict()
    n_before = len(cit)
    cit = cit[cit["source_doi"].map(doi_year) <= citer_cutoff].copy()
    cit["ref_year_num"] = pd.to_numeric(cit["ref_year"], errors="coerce")
    log.info("Citer filter <= %d: %d -> %d citation pairs (%d citing docs)",
             citer_cutoff, n_before, len(cit), cit["source_doi"].nunique())
    return cit, doi_meta, cutoff_year


def build_top_graph(cit, doi_meta, cutoff_year):
    """Top-N pre-cutoff co-citation graph from a citation table.

    Returns (G, ref_counts); (None, None) when no pre-cutoff reference exists.
    """
    pre_dois = (
        set(cit.loc[cit["ref_year_num"] <= cutoff_year, "ref_doi"])
        - {"", "nan", "none"}
    )
    rc_all = cit.groupby("ref_doi").size()
    rc = rc_all.loc[rc_all.index.isin(pre_dois)].sort_values(ascending=False)
    if len(rc) == 0:
        return None, None
    top_refs = rc.head(min(TOP_N, len(rc))).index.tolist()
    G = _build_cocitation_network(cit, doi_meta, rc, top_refs)
    return G, rc


def burden_hits(G, partition):
    """Per community: count of distinct burden-anchor nodes, and sizes."""
    comm_counts, comm_sizes = {}, {}
    for n, c in partition.items():
        comm_sizes[c] = comm_sizes.get(c, 0) + 1
        if BURDEN_RE.search(G.nodes[n].get("author", "")):
            comm_counts[c] = comm_counts.get(c, 0) + 1
    return comm_counts, comm_sizes


def cluster_present(G, partition, anchors, min_anchors=2, min_size=4):
    """True when >= min_anchors anchor nodes share a community of min_size."""
    sizes, counts = {}, {}
    for n, c in partition.items():
        sizes[c] = sizes.get(c, 0) + 1
        a = G.nodes[n].get("author", "")
        if any(x in a for x in anchors):
            counts[c] = counts.get(c, 0) + 1
    return any(counts.get(c, 0) >= min_anchors and sizes[c] >= min_size
               for c in sizes)


def candidates_in_network(G):
    """How many of the 18 burden candidates have >= 1 node in the graph."""
    authors = [str(G.nodes[n].get("author", "") or "") for n in G.nodes()]
    present = 0
    for cand in BURDEN_CANDIDATES:
        variants = cand if isinstance(cand, tuple) else (cand,)
        pat = re.compile(r"\b(" + "|".join(variants) + r")\b")
        if any(pat.search(a) for a in authors):
            present += 1
    return present
