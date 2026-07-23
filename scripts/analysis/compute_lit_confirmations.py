"""Literature-result confirmations for the data paper (ticket 0310).

Confirms four published results on the corpus, one statistic each, quoted
in the data paper's literature review through lit_* Quarto variables
(compute_vars.py reads this script's output):

1. Diaz-Rainey et al. 2017 — climate finance nearly absent from leading
   finance journals: chi-squared test on the pre/post break-year contingency
   of works published in an explicit finance-journal list.
2. Kouwenberg & Zheng 2023 — exponential post-2015 growth: Chow test for a
   structural break in log annual counts at the break year.
3. Kouwenberg & Zheng 2023 — the financial-economic cluster is disconnected
   from the rest: within-pole citation-edge share (public vs market poles of
   the global map's Louvain communities) vs a degree-preserving rewiring
   null (_null_separation, deterministic by construction).
4. UNEP Adaptation Gap Report 2023 — adaptation under-attended vs
   mitigation: exact binomial test on works mentioning exactly one of the
   two terms in title+abstract.

Output: one long-format CSV (metric, value), LitConfirmationsSchema.

Usage:
    uv run python scripts/analysis/compute_lit_confirmations.py \
        --output deliverables/_shared/tables/tab_lit_confirmations.csv
"""

import os

import community as community_louvain
import pandas as pd
import yaml
from _lit_confirmations import (
    adaptation_binomial,
    adaptation_mitigation_counts,
    chow_break,
    is_finance_journal,
    pole_labels,
    proportion_break,
)
from _null_separation import (
    null_separation_test,
    within_tradition_share,
)
from analyze_global_map import direct_graph, load_data
from pipeline_loaders import load_analysis_config, load_refined_works
from schemas import LitConfirmationsSchema
from script_io_args import parse_io_args, validate_io
from utils import BASE_DIR, get_logger

log = get_logger("compute_lit_confirmations")


def finance_share_rows(works, cfg):
    """Result 1: finance-journal share, pre/post break year."""
    in_fin = works["journal"].apply(
        lambda j: is_finance_journal(j, cfg["finance_journals"]))
    res = proportion_break(works["year"], in_fin, int(cfg["break_year"]))
    log.info("Finance journals: %d/%d pre, %d/%d post (%.2f%% -> %.2f%%), "
             "chi2=%.1f p=%.2e", res["fin_pre"], res["n_pre"],
             res["fin_post"], res["n_post"], res["share_pre_pct"],
             res["share_post_pct"], res["chi2"], res["p_value"])
    return [
        ("finshare_n_pre", res["n_pre"]),
        ("finshare_n_post", res["n_post"]),
        ("finshare_fin_pre", res["fin_pre"]),
        ("finshare_fin_post", res["fin_post"]),
        ("finshare_pre_pct", res["share_pre_pct"]),
        ("finshare_post_pct", res["share_post_pct"]),
        ("finshare_chi2", res["chi2"]),
        ("finshare_p_value", res["p_value"]),
    ]


def growth_break_rows(works, cfg, periodization):
    """Result 2: Chow break in log annual counts at the break year.

    Counts are restricted to the periodization window (1990--2024): stray
    out-of-window years carry a handful of works and would otherwise
    dominate the fitted slopes.
    """
    counts = works["year"].dropna().astype(int).value_counts().sort_index()
    lo, hi = int(periodization["year_min"]), int(periodization["year_max"])
    counts = counts[(counts.index >= lo) & (counts.index <= hi)]
    res = chow_break(counts, int(cfg["break_year"]))
    log.info("Growth break: F=%.1f p=%.2e, %.1f%%/yr pre -> %.1f%%/yr post",
             res["f_stat"], res["p_value"],
             res["growth_pre_pct"], res["growth_post_pct"])
    return [
        ("growth_f_stat", res["f_stat"]),
        ("growth_p_value", res["p_value"]),
        ("growth_pre_pct", res["growth_pre_pct"]),
        ("growth_post_pct", res["growth_post_pct"]),
    ]


def poles_rows(cfg, louvain_seed):
    """Result 3: public/market pole separation vs degree-preserving null."""
    with open(os.path.join(BASE_DIR, "config", "community_registry.yml")) as fh:
        registry = yaml.safe_load(fh)
    id_to_concept = registry["figures"]["fig_global_map_direct"]

    cit, works, _meta = load_data()
    G, _rank = direct_graph(cit, works)
    partition = community_louvain.best_partition(
        G, weight="weight", random_state=louvain_seed)
    labels = pole_labels(partition, id_to_concept,
                         cfg["public_pole"], cfg["market_pole"])
    H = G.subgraph(labels).copy()
    cross = sum(1 for u, v in H.edges() if labels[u] != labels[v])
    res = null_separation_test(
        H, labels, within_tradition_share,
        n_perm=int(cfg["null_n_perm"]), seed=int(cfg["null_seed"]))
    log.info("Poles: %d nodes, %d edges, %d cross; within obs=%.4f "
             "null=%.4f±%.4f z=%.1f p=%.4f (%d truncated)",
             H.number_of_nodes(), H.number_of_edges(), cross,
             res["observed"], res["null_mean"], res["null_std"],
             res["z_score"], res["p_value"], res["n_truncated"])
    return [
        ("poles_n_nodes", H.number_of_nodes()),
        ("poles_n_edges", H.number_of_edges()),
        ("poles_cross_edges", cross),
        ("poles_cross_share_pct", 100.0 * cross / H.number_of_edges()),
        ("poles_cross_share_null_pct", 100.0 * (1.0 - res["null_mean"])),
        ("poles_within_share_observed", res["observed"]),
        ("poles_within_share_null_mean", res["null_mean"]),
        ("poles_within_share_null_std", res["null_std"]),
        ("poles_within_share_z", res["z_score"]),
        ("poles_p_value", res["p_value"]),
        ("poles_n_perm", res["n_perm"]),
        ("poles_n_truncated", res["n_truncated"]),
    ]


def adaptation_rows(works, cfg):
    """Result 4: adaptation vs mitigation attention, exact binomial."""
    texts = (works["title"].fillna("") + " " +
             works["abstract"].fillna("")).astype(str)
    n_adapt, n_mitig = adaptation_mitigation_counts(
        texts, tuple(cfg["adaptation_terms"]), tuple(cfg["mitigation_terms"]))
    res = adaptation_binomial(n_adapt, n_mitig)
    log.info("Adaptation %d vs mitigation %d (%.1f%%), binomial p=%.2e",
             n_adapt, n_mitig, res["adapt_share_pct"], res["p_value"])
    return [
        ("adapt_n", res["adapt_n"]),
        ("mitig_n", res["mitig_n"]),
        ("adapt_share_pct", res["adapt_share_pct"]),
        ("adapt_p_value", res["p_value"]),
    ]


def main():
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)
    cfg_all = load_analysis_config()
    cfg = cfg_all["lit_confirmations"]
    louvain_seed = int(cfg_all["pre2007_traditions"]["louvain_seed"])

    works = load_refined_works()
    rows = []
    rows += finance_share_rows(works, cfg)
    rows += growth_break_rows(works, cfg, cfg_all["periodization"])
    rows += poles_rows(cfg, louvain_seed)
    rows += adaptation_rows(works, cfg)

    df = pd.DataFrame(rows, columns=["metric", "value"])
    df["value"] = df["value"].astype(float)
    LitConfirmationsSchema.validate(df)
    os.makedirs(os.path.dirname(io_args.output) or ".", exist_ok=True)
    df.to_csv(io_args.output, index=False)
    log.info("Wrote %d metrics to %s", len(df), io_args.output)


if __name__ == "__main__":
    main()
