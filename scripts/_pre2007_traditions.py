"""Pre-2007 co-citation traditions: shared analysis helper.

Builds the co-citation network of the most-cited pre-2007 references and
assigns its Louvain communities to three intellectual traditions by anchor
matching. This is the single source of truth for the pre-2007 tradition
seed-sets: the figure (`plot_fig_traditions.py`) renders it, and
`compute_null_separation.py` tests it against a degree-preserving null.

It lives in a neutral (non-plot, non-compute) module so both the plot and the
compute layer import it without a compute → plot backward arrow (architecture
rule 4; ticket 0250).
"""

import community as community_louvain
import networkx as nx
import numpy as np
import pandas as pd
from pipeline_loaders import (
    load_analysis_config,
    load_refined_works,
    pre2007_cutoff_year,
)
from scipy.sparse import lil_matrix
from utils import (
    get_logger,
    load_refined_citations,
    normalize_doi,
)

log = get_logger("_pre2007_traditions")

# --- Parameters ---
# CUTOFF_YEAR is not a hardcoded constant: it is derived from the config
# periodization (first break - 1) via pre2007_cutoff_year(), the single source
# of truth shared with compute_pre2007_coverage.py.
TOP_N = 250
MIN_COCIT = 3
RANDOM_STATE = 42

TRADITION_ANCHORS = {
    "pricing": ["weitzman", "barrett", "carraro", "montgomery", "pizer"],
    "cdm":     ["michaelowa", "sutter", "ellis", "haites", "pearson"],
    "unfccc":  ["north", "dimaggio", "finnemore"],
}


def _load_data(works_path, cit_path):
    """Load citations and works, build DOI metadata lookup."""
    log.info("Loading citations...")
    if cit_path is not None:
        cit = pd.read_csv(cit_path, low_memory=False)
    else:
        cit = load_refined_citations()
    cit["source_doi"] = cit["source_doi"].apply(normalize_doi)
    cit["ref_doi"] = cit["ref_doi"].apply(normalize_doi)
    cit = cit[(cit["source_doi"] != "") & (cit["ref_doi"] != "")]
    cit = cit[~cit["source_doi"].isin(["nan", "none"])]
    cit = cit[~cit["ref_doi"].isin(["nan", "none"])]
    log.info("  Citation pairs: %d", len(cit))

    if works_path is not None:
        works = pd.read_csv(works_path)
    else:
        works = load_refined_works()
    works["doi_norm"] = works["doi"].apply(normalize_doi)
    doi_meta = {}
    for _, row in works.iterrows():
        d = row["doi_norm"]
        if d and d not in ("nan", "none"):
            doi_meta[d] = {
                "title": str(row.get("title", "") or ""),
                "author": str(row.get("first_author", "") or ""),
                "year": row.get("year", ""),
            }
    for _, row in cit.iterrows():
        d = row["ref_doi"]
        if d and d not in ("nan", "none") and d not in doi_meta:
            doi_meta[d] = {
                "title": str(row.get("ref_title", "") or ""),
                "author": str(row.get("ref_first_author", "") or ""),
                "year": row.get("ref_year", "") or "",
            }
    return cit, doi_meta


def _build_cocitation_network(cit, doi_meta, ref_counts, top_refs):
    """Build co-citation graph from top references."""
    actual_top_n = len(top_refs)
    top_set = set(top_refs)
    ref_to_idx = {r: i for i, r in enumerate(top_refs)}

    log.info("Building co-citation matrix...")
    source_groups = cit.groupby("source_doi")["ref_doi"].apply(list)

    cocit = lil_matrix((actual_top_n, actual_top_n), dtype=np.float32)
    for ref_list in source_groups.values:
        in_top = [r for r in ref_list if r in top_set]
        if len(in_top) < 2:
            continue
        for i in range(len(in_top)):
            for j in range(i + 1, len(in_top)):
                a = ref_to_idx[in_top[i]]
                b = ref_to_idx[in_top[j]]
                cocit[a, b] += 1
                cocit[b, a] += 1

    cocit_dense = cocit.toarray()
    log.info("  Non-zero co-citation pairs: %d",
             np.count_nonzero(cocit_dense) // 2)

    G = nx.Graph()
    for doi in top_refs:
        meta = doi_meta.get(doi, {})
        author = (str(meta.get("author", "") or "")
                  .split(",")[0].split(";")[0].strip())
        year = str(meta.get("year", "") or "")
        title = str(meta.get("title", "") or "")
        if "." in year:
            year = year.split(".")[0]
        label = _make_node_label(author, year, title, doi)
        G.add_node(doi, label=label,
                   citations=int(ref_counts.get(doi, 0)),
                   author=author.lower())

    for i in range(actual_top_n):
        for j in range(i + 1, actual_top_n):
            w = cocit_dense[i, j]
            if w >= MIN_COCIT:
                G.add_edge(top_refs[i], top_refs[j], weight=float(w))

    isolates = list(nx.isolates(G))
    G.remove_nodes_from(isolates)
    log.info("Network: %d nodes, %d edges",
             G.number_of_nodes(), G.number_of_edges())
    log.info("  Removed %d isolates", len(isolates))
    return G


def _make_node_label(author, year, title, doi):
    """Create a readable label for a network node."""
    if (author and author.lower() not in ("nan", "none", "")
            and year and year not in ("nan", "none", "")):
        return f"{author} {year}"
    if title and title.lower() not in ("nan", "none", ""):
        words = [w for w in title.split() if len(w) > 2][:3]
        suffix = f" {year}" if year and year not in ("nan", "none") else ""
        return " ".join(words) + suffix
    return doi.split("/")[-1][:16]


def _assign_traditions(G, partition):
    """Map Louvain communities to named traditions via anchor matching."""
    comm_to_nodes = {}
    for doi, c in partition.items():
        comm_to_nodes.setdefault(c, []).append(doi)

    scores = {}
    for c, nodes in comm_to_nodes.items():
        for trad, anchors in TRADITION_ANCHORS.items():
            count = sum(
                1 for doi in nodes
                if any(a in G.nodes[doi].get("author", "")
                       for a in anchors)
            )
            scores[(c, trad)] = count

    comm_to_tradition = {}
    trad_to_comm = {}
    assigned_comms = set()
    assigned_trads = set()

    for (c, trad), score in sorted(scores.items(), key=lambda x: -x[1]):
        if score == 0:
            break
        if c in assigned_comms or trad in assigned_trads:
            continue
        comm_to_tradition[c] = trad
        trad_to_comm[trad] = c
        assigned_comms.add(c)
        assigned_trads.add(trad)

    for c in comm_to_nodes:
        if c not in comm_to_tradition:
            comm_to_tradition[c] = "other"

    return comm_to_tradition, trad_to_comm, comm_to_nodes


def build_pre2007_traditions(works_path, cit_path=None):
    """Build the pre-2007 co-citation graph and its tradition assignment.

    This is the single source of truth for the pre-2007 tradition seed-sets:
    the figure renders it, and compute_null_separation.py tests it against a
    degree-preserving null. Returns None when there is no pre-2007 network.

    Returns
    -------
    dict | None
        graph, partition (node->community), comm_to_tradition,
        trad_to_comm, comm_to_nodes, ref_counts, n_comm, modularity,
        actual_top_n.

    """
    cutoff_year = pre2007_cutoff_year(load_analysis_config())

    cit, doi_meta = _load_data(works_path, cit_path)

    # Filter to pre-2007 references
    cit["ref_year_num"] = pd.to_numeric(cit["ref_year"], errors="coerce")
    pre_dois = (
        set(cit.loc[cit["ref_year_num"] <= cutoff_year, "ref_doi"])
        - {"", "nan", "none"}
    )

    ref_counts_all = cit.groupby("ref_doi").size()
    ref_counts = ref_counts_all.loc[
        ref_counts_all.index.isin(pre_dois)
    ].sort_values(ascending=False)
    log.info("  Pre-%d refs: %d (cited >= 1)",
             cutoff_year, len(ref_counts))

    actual_top_n = min(TOP_N, len(ref_counts))
    if actual_top_n == 0:
        log.info("No pre-%d references found.", cutoff_year)
        return None

    top_refs = ref_counts.head(actual_top_n).index.tolist()
    log.info("  Using top %d; citation range: %d .. %d",
             actual_top_n,
             ref_counts.iloc[0],
             ref_counts.iloc[actual_top_n - 1])

    G = _build_cocitation_network(cit, doi_meta, ref_counts, top_refs)
    if G.number_of_nodes() == 0:
        log.info("Empty network.")
        return None

    partition = community_louvain.best_partition(
        G, weight="weight", random_state=RANDOM_STATE)
    n_comm = len(set(partition.values()))
    modularity = community_louvain.modularity(
        partition, G, weight="weight")
    log.info("  Louvain: %d communities, modularity=%.4f",
             n_comm, modularity)

    comm_to_tradition, trad_to_comm, comm_to_nodes = _assign_traditions(
        G, partition)

    return {
        "graph": G,
        "partition": partition,
        "comm_to_tradition": comm_to_tradition,
        "trad_to_comm": trad_to_comm,
        "comm_to_nodes": comm_to_nodes,
        "ref_counts": ref_counts,
        "n_comm": n_comm,
        "modularity": modularity,
        "actual_top_n": actual_top_n,
        "cutoff_year": cutoff_year,
    }
