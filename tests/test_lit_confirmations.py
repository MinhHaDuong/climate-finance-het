"""Tests for the literature-confirmation statistics pipeline (ticket 0310).

The data paper's literature review quotes four confirmations of published
results, each backed by one statistic in
deliverables/_shared/tables/tab_lit_confirmations.csv. These tests pin the
pure logic on synthetic data (finance-journal matching, pre/post proportion
test, Chow break on log-counts, adaptation/mitigation counting), the config
contract, the CLI/Makefile contracts by source inspection, and the
prose <-> artifact traceability (every lit_* Quarto variable quoted in the
prose exists in the committed CSV).
"""

import os

import pandas as pd
import yaml

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
BASE = os.path.join(SCRIPTS, "..")
CSV_PATH = os.path.join(
    BASE, "deliverables", "_shared", "tables", "tab_lit_confirmations.csv")


def _config():
    with open(os.path.join(BASE, "config", "analysis.yaml")) as fh:
        return yaml.safe_load(fh)["lit_confirmations"]


# ── Pure logic ──────────────────────────────────────────────────────────


def test_finance_journal_match_normalises_ampersand_and_case():
    from _lit_confirmations import is_finance_journal

    journals = ["journal of banking and finance", "finance research letters"]
    assert is_finance_journal("Journal of Banking & Finance", journals)
    assert is_finance_journal("FINANCE RESEARCH LETTERS ", journals)
    assert not is_finance_journal("Energy Economics", journals)
    assert not is_finance_journal(None, journals)


def test_proportion_break_contingency():
    """Chi-squared on the pre/post contingency; p small for a real shift."""
    from _lit_confirmations import proportion_break

    years = pd.Series([2010] * 100 + [2020] * 100)
    infin = pd.Series([True] * 1 + [False] * 99 + [True] * 30 + [False] * 70)
    res = proportion_break(years, infin, break_year=2015)
    assert res["n_pre"] == 100 and res["n_post"] == 100
    assert res["fin_pre"] == 1 and res["fin_post"] == 30
    assert res["p_value"] < 1e-6


def test_chow_break_on_log_counts_detects_slope_shift():
    from _lit_confirmations import chow_break

    years = list(range(2000, 2025))
    counts = [10 * 1.02 ** (y - 2000) for y in years[:15]] + [
        10 * 1.02**15 * 1.5 ** (y - 2015) for y in years[15:]
    ]
    res = chow_break(pd.Series(counts, index=years), break_year=2015)
    assert res["p_value"] < 1e-6
    assert res["growth_post_pct"] > res["growth_pre_pct"]


def test_chow_break_null_is_insignificant():
    from _lit_confirmations import chow_break

    years = list(range(2000, 2025))
    counts = [10 * 1.05 ** (y - 2000) for y in years]
    res = chow_break(pd.Series(counts, index=years), break_year=2015)
    assert res["p_value"] > 0.5


def test_adaptation_mitigation_counts_exclusive_mentions():
    from _lit_confirmations import adaptation_mitigation_counts

    texts = pd.Series([
        "adaptation to climate change",
        "Adaptation finance",
        "mitigation costs",
        "adaptation and mitigation together",  # both -> excluded
        "green bonds",                          # neither -> excluded
    ])
    n_adapt, n_mitig = adaptation_mitigation_counts(texts)
    assert (n_adapt, n_mitig) == (2, 1)


def test_pole_labelling_from_registry_mapping():
    from _lit_confirmations import pole_labels

    id_to_concept = {"7": "north-south", "1": "governance", "0": "climate-risk"}
    partition = {"a": 7, "b": 1, "c": 0, "d": 99}
    labels = pole_labels(
        partition, id_to_concept,
        public=["north-south", "governance", "health"],
        market=["climate-risk", "green-finance", "innovation"])
    assert labels == {"a": "public", "b": "public", "c": "market"}


# ── Config contract ─────────────────────────────────────────────────────


def test_config_declares_lit_confirmations_parameters():
    cfg = _config()
    for key in ("finance_journals", "break_year", "adaptation_terms",
                "mitigation_terms", "public_pole", "market_pole",
                "null_n_perm", "null_seed"):
        assert key in cfg, key
    assert len(cfg["finance_journals"]) >= 7
    # Pole concepts must exist in the community registry.
    with open(os.path.join(BASE, "config", "community_registry.yml")) as fh:
        registry = yaml.safe_load(fh)
    concepts = set(registry["concepts"])
    for c in cfg["public_pole"] + cfg["market_pole"]:
        assert c in concepts, c


# ── CLI / Makefile contracts (source inspection, no subprocess) ─────────


def test_compute_script_cli_contract():
    src = open(os.path.join(
        SCRIPTS, "analysis", "compute_lit_confirmations.py")).read()
    assert "parse_io_args" in src
    assert "LitConfirmationsSchema" in src
    assert "load_analysis_config" in src
    # Determinism: rewiring must go through the canonical null helper.
    assert "null_separation_test" in src


def test_makefile_wires_target():
    mk = open(os.path.join(SCRIPTS, "analysis", "lit-confirmations.mk")).read()
    assert "tab_lit_confirmations.csv" in mk
    top = open(os.path.join(BASE, "Makefile")).read()
    assert "lit-confirmations.mk" in top


def test_compute_vars_exports_lit_variables():
    src = open(os.path.join(SCRIPTS, "analysis", "compute_vars.py")).read()
    assert "tab_lit_confirmations.csv" in src
    assert "lit_confirmations_stats" in src


# ── Prose <-> artifact traceability ─────────────────────────────────────


def test_prose_lit_variables_trace_to_artifact():
    """Every lit_* Quarto variable used in the prose is derivable from the
    committed CSV: the compute_vars mapping only reads artifact metrics."""
    import re

    qmd = open(os.path.join(
        BASE, "deliverables", "data-paper", "data-paper.qmd")).read()
    used = set(re.findall(r"{{<\s*meta\s+(lit_\w+)\s*>}}", qmd))
    assert used, "the data paper quotes no lit_* variable"
    assert os.path.exists(CSV_PATH), "committed artifact missing"
    df = pd.read_csv(CSV_PATH)
    assert set(df.columns) == {"metric", "value"}
    metrics = set(df["metric"])
    for m in ("finshare_p_value", "growth_p_value",
              "poles_within_share_z", "poles_p_value",
              "adapt_p_value", "adapt_n", "mitig_n"):
        assert m in metrics, m
    # The DOC_VARS data-paper list must declare every used variable.
    import importlib.util

    spec = importlib.util.find_spec("analysis.compute_vars") if False else None
    src = open(os.path.join(SCRIPTS, "analysis", "compute_vars.py")).read()
    for var in used:
        assert f'"{var}"' in src, f"{var} not declared in compute_vars.py"


def test_no_hardcoded_p_values_in_prose_bullets():
    """The confirmation bullets carry no literal p = 0.x digits."""
    import re

    qmd = open(os.path.join(
        BASE, "deliverables", "data-paper", "data-paper.qmd")).read()
    # Find the confirmations block (bulleted list quoting lit_ variables).
    bullets = [ln for ln in qmd.splitlines()
               if ln.lstrip().startswith("-") and "lit_" in ln]
    assert len(bullets) == 4, "expected exactly four confirmation bullets"
    for ln in bullets:
        assert not re.search(r"[=<]\s*0?\.\d", ln), f"hardcoded number: {ln}"
