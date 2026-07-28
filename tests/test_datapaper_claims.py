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
- That same label is the one the two generated source tables print for the
  layer (ticket 0565). Table 1 is authored in the paper, Table 2 and the
  deposited retrieval protocol come from ``export_corpus_table.py`` and
  ``export_retrieval_protocol.py``, which the corpus report also consumes —
  so a rename in the paper silently left the generated tables a page later
  calling the same layer something else. The guard reads Table 1's label and
  requires the generators and their committed artifacts to print it, rather
  than pinning any particular wording.
"""

import os
import re
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "analysis"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "figures"))

import compute_vars

REPO = os.path.join(os.path.dirname(__file__), "..")
QMD = os.path.join(REPO, "deliverables", "data-paper", "data-paper.qmd")
TABLES = os.path.join(REPO, "deliverables", "_shared", "tables")


def _paper() -> str:
    with open(QMD, encoding="utf-8") as f:
        return f.read()


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
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


def world_bank_row_label(rows: list[dict], label_key: str = "Source") -> str:
    """The label of the one row that describes the World Bank harvest.

    "World Bank" is the layer's fingerprint across every table: Table 1 names
    it in Coverage, the composition table in Query, the protocol table in
    Retrieval. Keying on it rather than on a column position or a source id
    means the guard follows the layer through a rename instead of pinning the
    name it happens to carry today.
    """
    hits = {
        str(r[label_key]).strip()
        for r in rows
        if "world bank" in " ".join(str(v) for v in r.values()).lower()
    }
    assert len(hits) == 1, (
        f"expected exactly one row mentioning the World Bank harvest, got {hits}"
    )
    return hits.pop()


def pipe_table_rows(text: str, columns: list[str]) -> list[dict]:
    """Body rows of the pipe table whose header row is exactly ``columns``.

    Matching the whole header, not just its first cell, is what lets this run
    over ``tab_retrieval_protocol.md`` — which carries the protocol table and
    the seed enumeration back to back — and pick the one asked for. Rows come
    back as dicts so ``world_bank_row_label`` can search every cell.
    """
    rows, in_table = [], False
    for line in text.splitlines():
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells == columns:
            in_table = True
            continue
        if not in_table or set(line) <= set("|:- "):
            continue
        rows.append(dict(zip(columns, cells)))
    assert rows, f"no pipe table with header {columns} found"
    return rows


def tbl_sources_rows(text: str) -> list[dict]:
    """Table 1 (``{#tbl-sources}``) as dicts, keyed by its own header cells."""
    m = re.search(
        r"\n\| *(Source *\|.*?)\n\n: [^\n]*\{#tbl-sources\}", text, re.DOTALL
    )
    assert m, "no #tbl-sources pipe table found"
    header, _delim, *body = m.group(1).splitlines()
    columns = [c.strip() for c in ("| " + header).strip().strip("|").split("|")]
    rows = []
    for line in body:
        if not line.strip():
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(dict(zip(columns, cells)))
    return rows


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


@pytest.mark.adherence
def test_generated_source_tables_use_table_1s_label():
    """Ticket 0565: Table 1, Table 2, and the protocol table name one layer once.

    Table 1 is authored prose, the other two are generated and shared with the
    corpus report, so a rename in the paper does not reach them. Both the
    generator and its committed artifact are checked: the generator alone
    would pass while the deposited CSV still carried the old label, and the
    artifact alone would pass until the next ``make``.
    """
    import export_corpus_table
    import export_retrieval_protocol

    expected = world_bank_row_label(tbl_sources_rows(_paper()))

    assert export_corpus_table.SOURCE_META["grey"]["label"] == expected, (
        f"Table 1 calls the layer {expected!r} but export_corpus_table labels "
        f"it {export_corpus_table.SOURCE_META['grey']['label']!r}"
    )
    protocol_label = world_bank_row_label(
        export_retrieval_protocol.build_protocol_rows()
    )
    assert protocol_label == expected, (
        f"Table 1 calls the layer {expected!r} but the retrieval protocol "
        f"labels it {protocol_label!r}"
    )

    for name in ("tab_corpus_sources.csv", "tab_retrieval_protocol.csv"):
        rows = pd.read_csv(os.path.join(TABLES, name)).to_dict("records")
        artifact_label = world_bank_row_label(rows)
        assert artifact_label == expected, (
            f"{name} labels the layer {artifact_label!r}, not Table 1's "
            f"{expected!r} — run `make corpus-tables` and commit"
        )

    md_rows = pipe_table_rows(
        _read(os.path.join(TABLES, "tab_corpus_sources.md")),
        ["Source", "Raw", "Refined", "Unique", "%non-EN", "%DOI", "%Abstract", "%Refs"],
    )
    assert expected in [r["Source"] for r in md_rows], (
        f"the included Table 2 markdown has no {expected!r} row — the CSV and "
        "its .md companion disagree"
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


GENERATED_MD = """| Source | Raw | Refined |
|:-------|----:|--------:|
| OpenAlex | 40,000 | 30,000 |
| Institutional reports | 281 | 210 |

: Corpus sources. {#tbl-quality}

| Title | Author | Year |
|:---|:---|:---|
| A World Bank report | Bank | 2013 |

: The seed list.
"""


@pytest.mark.adherence
def test_fang_world_bank_row_label_follows_a_rename():
    """The helper reads the label off the layer, not off a pinned name."""
    rows = [
        {"Source": "OpenAlex", "Coverage": "academic index"},
        {"Source": "Grey literature", "Coverage": "seed + World Bank repository"},
    ]
    assert world_bank_row_label(rows) == "Grey literature"
    renamed = [dict(r) for r in rows]
    renamed[1]["Source"] = "Institutional reports"
    assert world_bank_row_label(renamed) == "Institutional reports"


@pytest.mark.adherence
def test_fang_world_bank_row_label_rejects_an_ambiguous_table():
    """Two matching rows would let the guard pick a label at random."""
    rows = [
        {"Source": "A", "Coverage": "World Bank repository"},
        {"Source": "B", "Coverage": "World Bank API"},
    ]
    with pytest.raises(AssertionError, match="exactly one row"):
        world_bank_row_label(rows)


@pytest.mark.adherence
def test_fang_pipe_table_rows_picks_its_own_table():
    """The seed enumeration sits right below the protocol table; skip it."""
    rows = pipe_table_rows(GENERATED_MD, ["Source", "Raw", "Refined"])
    assert [r["Source"] for r in rows] == ["OpenAlex", "Institutional reports"]
    with pytest.raises(AssertionError, match="no pipe table with header"):
        pipe_table_rows(GENERATED_MD, ["Source", "Retrieval"])


@pytest.mark.adherence
def test_fang_generated_table_label_drift_detected():
    """Revert Table 2's label alone and the agreement check must fail."""
    paper_label = world_bank_row_label(tbl_sources_rows(BAD_DOC.replace(
        "| Grey literature |", "| Institutional reports |"
    )))
    assert paper_label == "Institutional reports"
    drifted = pipe_table_rows(
        GENERATED_MD.replace("| Institutional reports |", "| Grey literature |"),
        ["Source", "Raw", "Refined"],
    )
    assert paper_label not in [r["Source"] for r in drifted]


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
