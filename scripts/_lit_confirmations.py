"""Pure logic for the literature-result confirmations (ticket 0310).

Four published results confirmed on the corpus, one statistic each:

1. finance-journal share, pre/post break year — chi-squared proportion test;
2. annual-count growth break — Chow test on log-counts (OLS, F statistic);
3. public/market pole citation separation — degree-preserving rewiring null
   (delegated to _null_separation.null_separation_test by the caller);
4. adaptation vs mitigation attention — exact binomial test.

Everything here is deterministic; the only stochastic step (the rewiring
null) lives in _null_separation, seeded and canonicalised by construction.
"""

import pandas as pd
from scipy import stats


def _norm_journal(name):
    """Lowercased, '&'->'and', whitespace-collapsed journal name."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    return " ".join(str(name).lower().replace("&", "and").split())


def is_finance_journal(name, finance_journals):
    """True when the normalised journal name is in the explicit list."""
    return _norm_journal(name) in set(finance_journals)


def proportion_break(years, in_finance, break_year):
    """Chi-squared test on the pre/post contingency of finance-journal works.

    Parameters: aligned Series of publication years and booleans (work is in
    a listed finance journal). Returns counts, shares (%), chi2 and p.
    """
    pre = years < break_year
    fin_pre = int((in_finance & pre).sum())
    fin_post = int((in_finance & ~pre).sum())
    n_pre = int(pre.sum())
    n_post = int((~pre).sum())
    table = [[fin_pre, n_pre - fin_pre], [fin_post, n_post - fin_post]]
    chi2, p, _, _ = stats.chi2_contingency(table)
    return {
        "n_pre": n_pre,
        "n_post": n_post,
        "fin_pre": fin_pre,
        "fin_post": fin_post,
        "share_pre_pct": 100.0 * fin_pre / n_pre if n_pre else float("nan"),
        "share_post_pct": 100.0 * fin_post / n_post if n_post else float("nan"),
        "chi2": float(chi2),
        "p_value": float(p),
    }


def chow_break(counts, break_year):
    """Chow test for a structural break in log annual counts at break_year.

    ``counts`` is a Series indexed by year. Restricted model: one log-linear
    trend. Unrestricted: separate intercept and slope on each side. The F
    statistic compares residual sums of squares (2 restrictions).
    """
    import numpy as np

    counts = counts[counts > 0].sort_index()
    y = np.log(counts.to_numpy(dtype=float))
    x = counts.index.to_numpy(dtype=float)
    post = (x >= break_year).astype(float)

    def rss(X):
        beta, res, _, _ = np.linalg.lstsq(X, y, rcond=None)
        pred = X @ beta
        return float(((y - pred) ** 2).sum()), beta

    ones = np.ones_like(x)
    rss_r, _ = rss(np.column_stack([ones, x]))
    X_u = np.column_stack([ones, x, post, post * (x - break_year)])
    rss_u, beta_u = rss(X_u)
    k_restr = 2
    df_denom = len(y) - X_u.shape[1]
    f_stat = ((rss_r - rss_u) / k_restr) / (rss_u / df_denom)
    p = float(stats.f.sf(f_stat, k_restr, df_denom))
    slope_pre = beta_u[1]
    slope_post = beta_u[1] + beta_u[3]
    return {
        "f_stat": float(f_stat),
        "p_value": p,
        "growth_pre_pct": 100.0 * (float(np.exp(slope_pre)) - 1.0),
        "growth_post_pct": 100.0 * (float(np.exp(slope_post)) - 1.0),
    }


def adaptation_mitigation_counts(texts, adaptation_terms=("adaptation",),
                                 mitigation_terms=("mitigation",)):
    """Counts of works mentioning exactly one of the two term families."""
    low = texts.fillna("").str.lower()
    has_a = low.apply(lambda t: any(term in t for term in adaptation_terms))
    has_m = low.apply(lambda t: any(term in t for term in mitigation_terms))
    return int((has_a & ~has_m).sum()), int((has_m & ~has_a).sum())


def adaptation_binomial(n_adapt, n_mitig):
    """Exact binomial test: adaptation share vs 0.5 among exclusive mentions."""
    res = stats.binomtest(n_adapt, n_adapt + n_mitig, p=0.5)
    return {
        "adapt_n": n_adapt,
        "mitig_n": n_mitig,
        "adapt_share_pct": 100.0 * n_adapt / (n_adapt + n_mitig),
        "p_value": float(res.pvalue),
    }


def pole_labels(partition, id_to_concept, public, market):
    """Map Louvain node partition to 'public'/'market' pole labels.

    ``partition``: node -> community id (int). ``id_to_concept``: community id
    (str) -> registry concept key. Nodes in unmapped or out-of-pole
    communities are dropped.
    """
    public, market = set(public), set(market)
    labels = {}
    for node, cid in partition.items():
        concept = id_to_concept.get(str(cid))
        if concept in public:
            labels[node] = "public"
        elif concept in market:
            labels[node] = "market"
    return labels
