"""Direct-citation graph construction shared by the global-map consumers.

Extracted from analyze_global_map.py (0250/0254 neutral-module pattern) so
compute_lit_confirmations.py and compute_sem6_assignments.py can reuse the
data loading and graph construction without importing a Tier-3 entry point.
"""

import networkx as nx
from pipeline_loaders import load_refined_works
from utils import get_logger, load_refined_citations, normalize_doi

log = get_logger("_global_map_graph")

BAD_DOIS = {"", "nan", "none"}


def load_data():
    """Load cleaned citation pairs, corpus works, and a DOI metadata lookup."""
    cit = load_refined_citations()
    cit["source_doi"] = cit["source_doi"].apply(normalize_doi)
    cit["ref_doi"] = cit["ref_doi"].apply(normalize_doi)
    cit = cit[~cit["source_doi"].isin(BAD_DOIS) & ~cit["ref_doi"].isin(BAD_DOIS)]
    works = load_refined_works()
    works["doi_norm"] = works["doi"].apply(normalize_doi)
    works = works[~works["doi_norm"].isin(BAD_DOIS)]
    meta = works.set_index("doi_norm")[["first_author", "year"]].to_dict("index")
    # Reference-side fallback for references outside the corpus (cocitation)
    if "ref_first_author" in cit.columns:
        sub = cit.drop_duplicates("ref_doi")
        for d, au, yr in zip(sub["ref_doi"], sub.get("ref_first_author", ""),
                             sub.get("ref_year", "")):
            if d not in meta:
                meta[d] = {"first_author": au, "year": yr}
    return cit, works, meta


def direct_graph(cit, works):
    """Undirected graph of direct citations between corpus documents."""
    corpus = set(works["doi_norm"])
    sub = cit[cit["source_doi"].isin(corpus) & cit["ref_doi"].isin(corpus)]
    sub = sub[sub["source_doi"] != sub["ref_doi"]]
    G = nx.Graph()
    G.add_edges_from(
        sub[["source_doi", "ref_doi"]].drop_duplicates().itertuples(
            index=False, name=None))
    G.remove_nodes_from(list(nx.isolates(G)))
    rank = sub.groupby("ref_doi").size().to_dict()
    return G, rank
