"""Claim-calibration guards for the data paper (ticket 0334).

Two claims outran their evidence: the prior-mapping comparison said the
corpus "subsumes" other studies' corpora when the probe replicates their
*queries* against OpenAlex, and the Abstract claimed broad coverage from an
institutional layer that is under 2% of the corpus. Per the CI test-polarity
rule these guards are negative bans and mechanical consistency checks only —
no positive wording is pinned, so a legitimate rewrite stays legal as long
as the claim and its evidence move together.

Guards:

- The stem "subsum" never appears (the probe is query-level, so no verb of
  record-level containment is defensible).
- The institutional-layer share in the Abstract is a ``{{< meta >}}``
  shortcode, never a hand-typed literal (the Abstract carries no literal
  percentage at all).
- The label Table 1 gives the World Bank / curated-seed source appears in
  the Abstract, so the two cannot drift apart under a rename.
"""

import os
import re
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "analysis"))

import compute_vars

QMD = os.path.join(
    os.path.dirname(__file__), "..", "deliverables", "data-paper", "data-paper.qmd"
)


def _paper() -> str:
    with open(QMD, encoding="utf-8") as f:
        return f.read()


# --------------------------------------------------------------------------- #
# Pure helpers (fang-tested below on known-bad fixtures)
# --------------------------------------------------------------------------- #
def find_containment_verbs(text: str) -> list[str]:
    """Occurrences of the "subsum" stem, any inflection, any case."""
    return re.findall(r"\bsubsum\w*", text, re.IGNORECASE)


def extract_abstract(text: str) -> str:
    """The YAML ``abstract:`` block scalar from the front matter."""
    m = re.search(r"^abstract: \|\n((?:[ \t]+\S.*\n|\n)+?)(?=^\S)", text, re.MULTILINE)
    assert m, "no abstract block found in front matter"
    return m.group(1)


def find_literal_percentages(text: str) -> list[str]:
    """Hand-typed percentages (``12%``, ``1.5%``) — shortcode output excluded."""
    return re.findall(r"\b\d+(?:\.\d+)?%", text)


def sources_table_labels(text: str) -> list[str]:
    """First-column labels of the #tbl-sources pipe table."""
    m = re.search(
        r"\n(\| *Source *\|.*?)\n\n: [^\n]*\{#tbl-sources\}", text, re.DOTALL
    )
    assert m, "no #tbl-sources pipe table found"
    labels = []
    for line in m.group(1).splitlines()[2:]:  # skip header + delimiter rows
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0]:
            labels.append(cells[0])
    return labels


# --------------------------------------------------------------------------- #
# Live guards
# --------------------------------------------------------------------------- #
@pytest.mark.adherence
def test_no_record_level_containment_verb():
    hits = find_containment_verbs(_paper())
    assert hits == [], (
        f"'subsume' claims record-level containment the query-level probe "
        f"cannot support: {hits}"
    )


@pytest.mark.adherence
def test_abstract_layer_share_is_a_shortcode_not_a_literal():
    abstract = extract_abstract(_paper())
    assert "{{< meta inst_layer_pct >}}" in abstract, (
        "the Abstract's institutional-layer claim must quantify itself via "
        "the inst_layer_pct shortcode"
    )
    literals = find_literal_percentages(abstract)
    assert literals == [], f"hand-typed percentage(s) in the Abstract: {literals}"


@pytest.mark.adherence
def test_sources_table_label_matches_abstract():
    text = _paper()
    abstract = extract_abstract(text).lower()
    labels = sources_table_labels(text)
    wb_labels = [
        label
        for label, line in zip(labels, _tbl_sources_rows(text))
        if "world bank" in line.lower()
    ]
    assert wb_labels, "no #tbl-sources row mentions the World Bank harvest"
    for label in wb_labels:
        assert label.lower() in abstract, (
            f"Table 1 labels the layer {label!r} but the Abstract does not "
            f"use that name — the two must move together"
        )


def _tbl_sources_rows(text: str) -> list[str]:
    m = re.search(
        r"\n(\| *Source *\|.*?)\n\n: [^\n]*\{#tbl-sources\}", text, re.DOTALL
    )
    assert m
    return [line for line in m.group(1).splitlines()[2:] if line.strip()]


# --------------------------------------------------------------------------- #
# Vars plumbing
# --------------------------------------------------------------------------- #
def test_inst_layer_share_registered_for_data_paper():
    assert "inst_layer_pct" in compute_vars.DOC_VARS["data-paper"]


def test_corpus_stats_emits_inst_layer_share(monkeypatch, tmp_path):
    df = pd.DataFrame(
        {
            "from_openalex": [True, True, True, False, False, False, True, True],
            "from_grey": [False, False, False, True, False, False, False, False],
            "from_unfccc": [False, False, False, False, True, False, False, False],
            # overlaps from_unfccc row 4: the union must not double-count
            "from_oecd": [False, False, False, False, True, True, False, False],
        }
    )
    monkeypatch.setattr(compute_vars, "load_refined_works", lambda: df)
    monkeypatch.setattr(compute_vars, "CATALOGS_DIR", str(tmp_path))
    v = {}
    compute_vars.corpus_stats(v)
    assert v["inst_layer_pct"] == "37.5"  # 3 of 8, union not sum

    # A missing layer column must not silently shrink the share: the collector
    # emits nothing, and the absent key fails loud as an unresolved shortcode.
    monkeypatch.setattr(
        compute_vars, "load_refined_works", lambda: df.drop(columns=["from_oecd"])
    )
    v = {}
    compute_vars.corpus_stats(v)
    assert "inst_layer_pct" not in v


# --------------------------------------------------------------------------- #
# Fangs — each guard proven against a known-bad fixture
# --------------------------------------------------------------------------- #
BAD_DOC = """---
abstract: |
  A corpus that subsumes prior mappings, with grey literature
  making up 1.5% of the works.
---

| Source | Automation | Coverage |
|--------|------------|----------|
| Grey literature | Hybrid | curated seed + World Bank repository |

: Sources. {#tbl-sources}
"""


@pytest.mark.adherence
def test_fang_containment_verb_detected():
    assert find_containment_verbs("It subsumes and Subsumed corpora") == [
        "subsumes",
        "Subsumed",
    ]


@pytest.mark.adherence
def test_fang_literal_percentage_detected():
    assert find_literal_percentages(extract_abstract(BAD_DOC)) == ["1.5%"]


@pytest.mark.adherence
def test_fang_label_mismatch_detected():
    abstract = extract_abstract(BAD_DOC).lower()
    labels = sources_table_labels(BAD_DOC)
    assert labels == ["Grey literature"]
    # the fixture's abstract does say "grey literature", so mismatch detection
    # is exercised on a renamed-label variant instead
    renamed = BAD_DOC.replace("| Grey literature |", "| Institutional reports |")
    assert "institutional reports" not in abstract
    assert sources_table_labels(renamed) == ["Institutional reports"]
