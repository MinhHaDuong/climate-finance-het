"""Language-ablation vars for the data paper (ticket 0337).

Sibling of ``_vars_retrieval``: a focused stats provider imported by
``compute_vars``. The removal shares are read back from the deposited
ablation table, so the prose quotes the artifact a reuser downloads, by
construction. The flag-6 attribution needs per-work flags and language
together, which only the pre-removal catalog carries.
"""

import os
import warnings

import pandas as pd
from utils import BASE_DIR, CATALOGS_DIR

# Keys this module contributes to the data paper (mirrors RETRIEVAL_VARS).
ABLATION_VARS = [
    "ablation_en_removed_pct",
    "ablation_nonen_removed_pct",
    "ablation_f6_nonen_share_pct",
]


def filter_ablation_stats(v):
    table_path = os.path.join(
        BASE_DIR, "deliverables", "_shared", "tables", "tab_filter_ablation.csv"
    )
    if not os.path.isfile(table_path):
        warnings.warn(f"Missing: {table_path}")
        return
    table = pd.read_csv(table_path)
    lang_rows = table[table["axis"] == "language"].set_index("stratum")
    v["ablation_en_removed_pct"] = f"{lang_rows.at['English', 'removed_pct']:.1f}"
    v["ablation_nonen_removed_pct"] = f"{lang_rows.at['non-English', 'removed_pct']:.1f}"

    ext_path = os.path.join(CATALOGS_DIR, "extended_works.csv")
    if not os.path.isfile(ext_path):
        warnings.warn(f"Missing: {ext_path}")
        return
    ext = pd.read_csv(
        ext_path, usecols=["language", "action", "llm_irrelevant"],
    )
    removed = ext[ext["action"].eq("would_remove")]
    non_en = removed[~removed["language"].fillna("unknown").isin(["en", "unknown"])]
    share = non_en["llm_irrelevant"].fillna(False).mean()
    v["ablation_f6_nonen_share_pct"] = f"{100 * share:.1f}"
