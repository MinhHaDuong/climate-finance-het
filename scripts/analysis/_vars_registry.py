"""Which variables each document declares, and which file they are written to.

Split out of `compute_vars.py` when registering corpus-report pushed that
module past the god-module cap (ticket 0357). The split follows the seam that
was already there: this module is the *registry* — a document-keyed contract
that changes whenever prose gains or loses a `{{< meta >}}` macro — while
`compute_vars` holds the *collectors* that read pipeline outputs. The two churn
for unrelated reasons.

`compute_vars` re-exports both names, so `from compute_vars import DOC_VARS`
keeps working for the guards that read the registry.
"""

import os

from _vars_ablation import ABLATION_VARS
from _vars_retrieval import FLAG_RULE_VARS, RETRIEVAL_VARS
from utils import BASE_DIR

# The metadata file each document loads, matching the `metadata-files:` line in
# its front matter. Most documents get a sibling -vars.yml in their own
# deliverable folder (ticket 0226); four share technical-report-vars.yml, which
# is why it lives in _shared/.
#
# Sharing is declared here rather than left implicit in the render (ticket
# 0357). A document absent from this registry still renders — Quarto resolves
# whatever the shared file happens to carry and writes `?meta:key` for the rest,
# exit 0 — so an unregistered document does not fail, it quietly under-declares.
# corpus-report did exactly that for 12 keys. Every shared file is written with
# the union of its documents' keys.
SHARED_VARS_FILE = os.path.join(BASE_DIR, "deliverables", "_shared", "technical-report-vars.yml")

DOC_VARS_FILE = {
    "technical-report": SHARED_VARS_FILE,
    "corpus-report": SHARED_VARS_FILE,
    "multilayer-detection-techrep": SHARED_VARS_FILE,
    "breakpoint-detect-method-zoo": SHARED_VARS_FILE,
    "data-paper": os.path.join(
        BASE_DIR, "deliverables", "data-paper", "data-paper-vars.yml"
    ),
    "multilayer-detection": os.path.join(
        BASE_DIR, "deliverables", "multilayer", "multilayer-detection-vars.yml"
    ),
}

# Which variables each document uses (direct + {{< include >}}'d files).
# Each document gets a sibling -vars.yml containing only its variables.
DOC_VARS = {
    # "manuscript" is pinned to v1.0 values — not auto-generated.
    # Edit content/manuscript-vars.yml manually if needed.
    "technical-report": [
        "corpus_total",
        "emb_dimensions",
    ],
    # Three documents that also load technical-report-vars.yml. The first two
    # happened to resolve because they quote the same two variables the
    # technical report does; corpus-report did not, and rendered 12 `?meta:`
    # placeholders until ticket 0357 registered it.
    "multilayer-detection-techrep": [
        "corpus_total",
        "emb_dimensions",
    ],
    "breakpoint-detect-method-zoo": [
        "corpus_total",
        "emb_dimensions",
    ],
    "corpus-report": [
        # direct + includes: corpus-construction, corpus-enrichment,
        #   corpus-filtering, metadata/embedding/citation-quality,
        #   core-vs-full-definition, reproducibility, annex-crossencoder,
        #   teaching-convergence
        "cite_coverage_pct",
        "cite_crossref_rows",
        "cite_doi_ref_pct",
        "cite_doi_ref_rows",
        "cite_fetched_dois",
        "cite_never_fetched",
        "cite_total_dois",
        "cite_total_rows",
        "corpus_core",
        "corpus_core_threshold",
        "corpus_sources",
        "corpus_total",
        "corpus_with_embeddings",
        # Flag 6 and Phase B thresholds, read from config (ticket 0357).
        *FLAG_RULE_VARS,
        "filter_outlier_sigma",
        "filter_reranker_threshold",
        "protect_min_cited",
        "protect_min_sources",
    ],
    "data-paper": [
        # direct + includes: corpus-construction, corpus-filtering,
        #   embedding-generation
        "cite_coverage_core_pct",
        "cite_cov_cryst_pct",
        "cite_cov_post2015_pct",
        "cite_cov_pre2007_pct",
        # The four DOI-carriage vars (cite_doi_{pre2007,post2015}_pct and
        # cite_cov_{pre2007,post2015}_of_doi_pct) left with 0332's cut of the
        # gradient-mechanism sentences; the three period coverages above stay.
        # compute_citation_coverage.py still emits all seven — re-add here if
        # the mechanism argument returns.
        "cite_refined_coverage_pct",
        "cite_refined_rows",
        "cite_total_rows",
        "complete_captured_n",
        "complete_captured_pct",
        "complete_ci_lower_pct",
        "complete_ci_upper_pct",
        "complete_total_n",
        "corpus_core",
        "corpus_core_threshold",
        "corpus_multi_source",
        "corpus_multi_source_pct",
        "corpus_no_doi_pct",
        "corpus_raw",
        "corpus_sources",
        "corpus_total",
        "corpus_with_embeddings",
        "emb_dimensions",
        "filter_citation_isolated",
        "filter_flagged",
        "filter_llm_irrelevant",
        "filter_missing_metadata",
        "filter_no_abstract",
        "filter_protected",
        "filter_title_blacklist",
        *ABLATION_VARS,  # §2.3 language ablation (ticket 0337)
        *RETRIEVAL_VARS,  # §2.2 thresholds, read from config (ticket 0329)
        "dedup_doi_removed",
        "dedup_fn_pairs",
        "dedup_fn_pairs_pct",
        "dedup_fn_upper_docs",
        "dedup_fn_upper_pct",
        "dedup_fp_doi_collision_groups",
        "dedup_fp_empty_year_docs",
        "dedup_fp_empty_year_groups",
        "dedup_titleyear_removed",
        "gm_communities",
        "gm_connected_pct",
        "gm_coverage_pct",
        "gm_modularity",
        "gm_n_connected",
        "inst_layer_pct",
        "lang_detected_n",
        "lang_detected_pct",
        "lang_english_pct",
        "lang_non_english_n",
        # Two earlier cuts orphaned lit_* vars, both still emitted upstream:
        # the adaptation-share and chi-square/p details went with PR #1120,
        # leaving only the two finance-journal shares in the
        # literature-confirmation bullet (§1); lit_sem6_ari and lit_sem6_n went
        # with 0332's §4 cut, since the semantic-cluster paragraph they served
        # needed an under-review companion paper to interpret.
        "lit_finshare_post_pct",
        "lit_finshare_pre_pct",
        "lit_growth_f",
        "lit_growth_p",
        "lit_growth_post_pct",
        "lit_poles_cross_null_pct",
        "lit_poles_cross_pct",
        "lit_poles_p",
        "lit_poles_z",
        "openalex_pct",
        "refs_doi_docs",
        "refs_max",
        "refs_mean",
        "refs_median",
        "refs_p95",
        "refs_zero_n",
        "refs_zero_share_pct",
        "verify_ci_lower_pct",
        "verify_ci_upper_pct",
        "verify_confirmed_pct",
        "verify_sample_n",
        "verify_unconfirmed_n",
    ],
    "multilayer-detection": [
        "bim_corr",
        "bim_dbic_2007_2014",
        "bim_dbic_embedding",
        "bim_dbic_post2015",
        "bim_dbic_pre2007",
        "bim_dbic_tfidf",
        "bim_dip_p_2007_2014",
        "bim_dip_p_embedding",
        "bim_dip_p_post2015",
        "bim_dip_p_pre2007",
        "bim_gmm_modes",
        "bim_gmm_separation",
        "bim_n_2007_2014",
        "bim_n_accountability",
        "bim_n_efficiency",
        "bim_n_post2015",
        "bim_n_pre2007",
        "corpus_core",
        "corpus_core_threshold",
        "corpus_sources",
        "corpus_total",
        "emb_dimensions",
        "lang_english_pct",
        "pca_emb_pc1_var_pct",
        "pca_emb_pc2_cosine",
        "pca_emb_pc2_dbic",
        "pca_emb_pc2_var_pct",
        "g9_peak_year_w3",
        "l1_peak_year_w3",
        "s2_peak_year_w3",
        "zone_1_end",
        "zone_1_start",
    ],
}
