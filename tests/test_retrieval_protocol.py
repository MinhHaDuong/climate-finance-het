"""The data paper's retrieval protocol is reconstructible from config (ticket 0329).

All four external reviewers of RDJ-26561 said the paper names its method
without specifying it: the eight target languages are never listed, the
filtering thresholds are never reported, and the query protocol can only be
recovered by reading the harvest code. These guards make the paper's claims
answerable to the configuration the harvest actually read.

Three guard families:

- **Config integrity** — every Tier-1 term carries a language tag, so the
  language list the paper prints cannot drift from the terms that ran.
- **Prose ↔ config** — the paper names exactly the languages config declares,
  and every threshold it quotes is a ``{{< meta >}}`` macro rather than a
  hand-typed literal.
- **Artifact ↔ config** — the deposited retrieval-protocol table counts the
  same terms and seed documents the config holds, so the deposit cannot drift
  from what ran.

Everything here reads YAML and text files only. No corpus data, no heavy
dependency: fast tier.
"""

import os
import re
import sys

import pytest
import yaml

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, os.path.join(REPO, "scripts", "analysis"))
sys.path.insert(0, os.path.join(REPO, "scripts", "figures"))

QMD = os.path.join(REPO, "deliverables", "data-paper", "data-paper.qmd")
QUERIES_YAML = os.path.join(REPO, "config", "openalex_queries.yaml")
FILTER_YAML = os.path.join(REPO, "config", "corpus_filter.yaml")
GREY_YAML = os.path.join(REPO, "config", "grey_sources.yaml")


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _qmd_text():
    with open(QMD, encoding="utf-8") as fh:
        return fh.read()


def _include_text(name):
    path = os.path.join(REPO, "deliverables", "_shared", "_includes", name)
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _section(text, heading_prefix):
    """Body of the ``### <heading_prefix> ...`` section, up to the next heading."""
    lines = text.splitlines()
    start = next(
        i for i, ln in enumerate(lines) if ln.startswith(f"### {heading_prefix}")
    )
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## ") or lines[i].startswith("### "):
            end = i
            break
    return "\n".join(lines[start:end])


def target_languages() -> list[str]:
    """Display names of the languages the Tier-1 core terms are written in."""
    tags = _load(QUERIES_YAML)["term_languages"]
    return sorted({lang for lang in tags.values() if lang})


# --------------------------------------------------------------------------- #
# Config integrity — the language tags cover Tier 1 exactly
# --------------------------------------------------------------------------- #
def test_term_languages_covers_tier1_exactly():
    """A bijection, so neither list can gain or lose a term unnoticed.

    ``term_languages`` is what the paper's language sentence is generated
    from; ``tiers.1.terms`` is what the harvester queries. If they diverge the
    paper describes a harvest that did not happen.
    """
    cfg = _load(QUERIES_YAML)
    tagged = set(cfg["term_languages"])
    queried = set(cfg["tiers"][1]["terms"])
    assert tagged == queried, (
        "term_languages and tiers.1.terms disagree — "
        f"untagged terms: {sorted(queried - tagged)}; "
        f"tagged but never queried: {sorted(tagged - queried)}"
    )


def test_eight_target_languages_declared():
    """The paper's headline claim is eight languages; config must hold eight."""
    assert len(target_languages()) == 8, (
        f"config declares {len(target_languages())} target languages "
        f"({target_languages()}), the paper claims eight"
    )


def test_language_neutral_terms_are_tagged_null():
    """Institution names (``green climate fund``) carry no language tag.

    Tagging them with a language would inflate the count the paper prints.
    """
    tags = _load(QUERIES_YAML)["term_languages"]
    untagged = [t for t, lang in tags.items() if lang is None]
    assert untagged, "at least the institution-name terms must be tagged null"


# --------------------------------------------------------------------------- #
# Prose ↔ config — the paper names the languages config declares
# --------------------------------------------------------------------------- #
def test_paper_names_every_target_language():
    sources = _section(_qmd_text(), "2.1")
    missing = [lang for lang in target_languages() if lang not in sources]
    assert not missing, (
        f"§2.1 does not name these target languages: {missing}. "
        "The language list must match config/openalex_queries.yaml."
    )


def test_paper_names_no_language_it_did_not_query():
    """Guards the other direction: no language in §2.1 that config lacks.

    The candidate set is every language name that appears as a tag anywhere
    plus the common near-misses a drafter might add by hand.
    """
    sources = _section(_qmd_text(), "2.1")
    declared = set(target_languages())
    candidates = {
        "English", "French", "German", "Spanish", "Portuguese", "Arabic",
        "Chinese", "Japanese", "Russian", "Italian", "Dutch", "Korean",
        "Hindi", "Indonesian", "Turkish",
    }
    named_in_list = {
        lang for lang in candidates - declared
        if re.search(rf"\b{lang}\b", sources)
    }
    assert not named_in_list, (
        f"§2.1 names languages the harvest never queried: {sorted(named_in_list)}"
    )


# --------------------------------------------------------------------------- #
# Prose ↔ config — thresholds are macros, not literals
# --------------------------------------------------------------------------- #
# Every threshold §2.2 quotes, with the config path it must come from.
THRESHOLD_VARS = {
    "filter_outlier_min_lang": ("semantic_outlier", "min_language_count"),
    "filter_reranker_threshold": ("llm_relevance", "reranker_threshold"),
    "neardup_prefix_chars": ("near_duplicate", "prefix_length"),
    "neardup_min_group_size": ("near_duplicate", "min_group_size"),
    "neardup_overlap_pct": ("near_duplicate", "abstract_overlap_threshold"),
    "protect_min_cited": ("protection", "min_cited_by"),
    "protect_min_sources": ("protection", "min_source_count"),
}

# Literals that must never reappear in §2.2 in place of their macro. Chosen to
# be unambiguous in that section — a bare "50" would also match the abstract
# length, so only distinctive spellings are pinned.
BANNED_LITERALS = [
    "mean + 2 standard deviations",
    "0.002",
    "200 characters",
    "2+ sources",
]


@pytest.mark.parametrize("var", sorted(THRESHOLD_VARS))
def test_threshold_cited_as_macro(var):
    pipeline = _section(_qmd_text(), "2.2")
    assert f"{{{{< meta {var} >}}}}" in pipeline, (
        f"§2.2 must cite {var} as a {{{{< meta >}}}} macro (project rule: "
        "no hand-typed pipeline numbers)"
    )


@pytest.mark.parametrize("literal", BANNED_LITERALS)
def test_threshold_not_hand_typed(literal):
    pipeline = _section(_qmd_text(), "2.2")
    assert literal not in pipeline, (
        f"§2.2 hand-types {literal!r}; cite the config-derived macro instead"
    )


def test_near_duplicate_thresholds_live_in_config():
    """The four near-duplicate constants moved out of the Python source.

    This is the one place the reviewers' "you must read the code" complaint
    was literally true: the thresholds were module-level constants.
    """
    block = _load(FILTER_YAML)["near_duplicate"]
    for key in ("prefix_length", "min_group_size", "min_abstract_length",
                "abstract_overlap_threshold"):
        assert key in block, f"config/corpus_filter.yaml near_duplicate lacks {key}"


def test_qa_near_duplicates_defaults_come_from_config():
    import qa_near_duplicates as qnd

    block = _load(FILTER_YAML)["near_duplicate"]
    assert qnd.DEFAULT_PREFIX_LENGTH == block["prefix_length"]
    assert qnd.DEFAULT_MIN_GROUP_SIZE == block["min_group_size"]
    assert qnd.DEFAULT_MIN_ABSTRACT_LENGTH == block["min_abstract_length"]
    assert qnd.DEFAULT_ABSTRACT_OVERLAP_THRESHOLD == block["abstract_overlap_threshold"]


def test_declared_vars_match_what_the_collector_emits():
    """RETRIEVAL_VARS is spliced into DOC_VARS, so it must be exact.

    A name declared but not emitted renders as an empty macro; a name emitted
    but not declared never reaches the paper at all.
    """
    from _vars_retrieval import RETRIEVAL_VARS, retrieval_protocol_stats

    v = {}
    retrieval_protocol_stats(v)
    assert set(RETRIEVAL_VARS) == set(v), (
        f"declared but not emitted: {sorted(set(RETRIEVAL_VARS) - set(v))}; "
        f"emitted but not declared: {sorted(set(v) - set(RETRIEVAL_VARS))}"
    )
    assert set(RETRIEVAL_VARS) == set(THRESHOLD_VARS), (
        "this test file's registry has drifted from the collector's"
    )


def test_compute_vars_emits_thresholds_from_config():
    from _vars_retrieval import retrieval_protocol_stats

    cfg = _load(FILTER_YAML)
    v = {}
    retrieval_protocol_stats(v)
    for var, (block, key) in THRESHOLD_VARS.items():
        assert var in v, f"retrieval_protocol_stats did not emit {var}"
        raw = cfg[block][key]
        expected = f"{raw * 100:.0f}" if var.endswith("_pct") else str(raw)
        assert v[var] == expected, f"{var}: got {v[var]!r}, config says {expected!r}"


def test_stats_rule_depends_on_the_threshold_config():
    """Make must rebuild the vars file when a reported threshold changes.

    compute_vars reads config/corpus_filter.yaml, so leaving it out of the
    prerequisites lets an edited sigma sit in config while the paper keeps
    printing the old number — the exact drift this ticket exists to close.
    """
    with open(os.path.join(REPO, "Makefile"), encoding="utf-8") as fh:
        makefile = fh.read()
    rule = makefile.split("$(COMPUTED_STATS) &:", 1)[1].split("\n\n", 1)[0]
    assert "config/corpus_filter.yaml" in rule, (
        "the $(COMPUTED_STATS) rule must list config/corpus_filter.yaml as a "
        "prerequisite; compute_vars.py reads its thresholds into the paper"
    )


def test_committed_vars_artifact_matches_config():
    """The number the paper prints, not the number the collector would print.

    Every other guard here computes its expected side from the same live
    config the production code reads, so all of them stay green when the
    committed artifact is stale — edit a threshold, skip `make stats`, and
    the paper keeps printing the old value with nothing to say so. This repo
    has no CI, so that is the standing drift vector, and it is the exact
    failure this ticket exists to remove. Possible only for the config-derived
    variables: the corpus-derived ones need Phase-1 data to recompute.
    """
    from _vars_retrieval import retrieval_protocol_stats
    from compute_vars import DOC_OUTPUT_DIR

    expected = {}
    retrieval_protocol_stats(expected)

    path = os.path.join(DOC_OUTPUT_DIR["data-paper"], "data-paper-vars.yml")
    with open(path, encoding="utf-8") as fh:
        committed = yaml.safe_load(fh) or {}

    stale = {
        k: (committed.get(k), v)
        for k, v in expected.items()
        if str(committed.get(k)) != v
    }
    assert not stale, (
        "data-paper-vars.yml is stale against config/corpus_filter.yaml "
        f"(committed, expected): {stale}. Run `make stats` and commit."
    )


def test_threshold_vars_registered_for_the_data_paper():
    from compute_vars import DOC_VARS

    declared = set(DOC_VARS["data-paper"])
    missing = set(THRESHOLD_VARS) - declared
    assert not missing, f"DOC_VARS['data-paper'] is missing {sorted(missing)}"


# --------------------------------------------------------------------------- #
# Artifact ↔ config — the deposited table counts what the config holds
# --------------------------------------------------------------------------- #
def test_protocol_rows_count_the_config_terms():
    from export_retrieval_protocol import build_protocol_rows

    cfg = _load(QUERIES_YAML)
    rows = {r["Source"]: r for r in build_protocol_rows()}
    assert "OpenAlex" in rows, "the protocol table must have an OpenAlex row"

    expected_total = sum(len(t["terms"]) for t in cfg["tiers"].values())
    assert str(expected_total) in rows["OpenAlex"]["Query terms"], (
        f"OpenAlex row must report {expected_total} terms: "
        f"{rows['OpenAlex']['Query terms']!r}"
    )
    for tier, tier_cfg in cfg["tiers"].items():
        assert f"T{tier} {len(tier_cfg['terms'])}" in rows["OpenAlex"]["Query terms"], (
            f"tier {tier} term count missing from the OpenAlex row"
        )


def test_protocol_rows_count_the_curated_seed_lists():
    from export_retrieval_protocol import build_protocol_rows

    rows = {r["Source"]: r for r in build_protocol_rows()}
    n_grey = len(_load(GREY_YAML))
    assert str(n_grey) in rows["Grey literature"]["Query terms"], (
        f"grey row must report {n_grey} curated reports"
    )
    for name, path in (
        ("UNFCCC key documents", "unfccc_sources.yaml"),
        ("OECD DAC key documents", "oecd_dac_sources.yaml"),
    ):
        n = len(_load(os.path.join(REPO, "config", path))["documents"])
        assert str(n) in rows[name]["Query terms"], (
            f"{name} row must report {n} seed documents"
        )


def test_seed_layer_languages_come_from_the_seed_entries():
    """The key-document rows read their languages, they do not assert them.

    Both seed lists carry a per-document ``language`` field, so this column
    has a config source and must use it — a hand-typed "English" would keep
    printing English after the first French COP decision was seeded.
    """
    from export_retrieval_protocol import build_protocol_rows

    rows = {r["Source"]: r for r in build_protocol_rows()}
    for name, path in (
        ("UNFCCC key documents", "unfccc_sources.yaml"),
        ("OECD DAC key documents", "oecd_dac_sources.yaml"),
    ):
        entries = _load(os.path.join(REPO, "config", path))["documents"]
        codes = {e["language"] for e in entries if e.get("language")}
        assert codes, f"{path} declares no language field to read"
        assert len(rows[name]["Languages"].split(", ")) == len(codes), (
            f"{name} reports {rows[name]['Languages']!r} against "
            f"{len(codes)} distinct seed language(s)"
        )


def test_unconfigured_sources_say_so_rather_than_inventing_a_query():
    """Honesty guard on the three hand-exported sources.

    Their rows describe a harvest with no machine-readable record. Printing a
    plausible query for them would be worse than printing nothing, because a
    referee would take it for the query that ran.
    """
    from export_retrieval_protocol import build_protocol_rows

    rows = {r["Source"]: r for r in build_protocol_rows()}
    for name in ("bibCNRS", "SciSpace", "Teaching canon"):
        assert rows[name]["Query terms"] == "not machine-readable", (
            f"{name} claims a query term count it cannot source from config"
        )


def test_caption_declares_which_cells_are_config_derived():
    from export_retrieval_protocol import CAPTION

    assert "machine-readable" in CAPTION and "configuration" in CAPTION, (
        "the caption must tell a referee which cells are rendered from config "
        "and which merely describe the harvest"
    )


def test_caption_does_not_credit_config_for_hand_typed_languages():
    """The Languages column is config-derived for three rows, not five.

    OpenAlex reads its term-language tags and the two key-document layers read
    their seed entries; the ISTEX and grey-literature cells are literals in the
    export script. A caption crediting all five configured sources to the
    deposited configuration sells a referee a provenance two rows lack — the
    same drift this artifact exists to prevent.
    """
    import export_retrieval_protocol as mod

    with open(mod.__file__, encoding="utf-8") as fh:
        source = fh.read()
    rows = {r["Source"]: r for r in mod.build_protocol_rows()}
    hand_typed = ("ISTEX", "Grey literature")
    for name in hand_typed:
        assert f'"Languages": "{rows[name]["Languages"]}"' in source, (
            f"{name} languages are no longer a hand-typed literal — the "
            "caption's disclosure must be revisited"
        )

    caption = mod.CAPTION.lower()
    marker = "language coverage is config-derived only for"
    assert marker in caption, (
        "the caption must scope the Languages column's config provenance to "
        "the rows that have it"
    )
    disclosure = caption[caption.index(marker) :]
    for token in ("istex", "grey", "asserted"):
        assert token in disclosure, (
            f"the caption must disclose that {token!r} languages are asserted, "
            "not read from config"
        )


def test_protocol_openalex_row_reports_the_query_field():
    """The reviewers asked which fields the query searched."""
    from export_retrieval_protocol import build_protocol_rows

    rows = {r["Source"]: r for r in build_protocol_rows()}
    assert "default.search" in rows["OpenAlex"]["Query fields"]


def test_grey_enumeration_lists_every_curated_report():
    """Action 6: the 17 grey-literature reports are enumerated in the deposit."""
    from export_retrieval_protocol import build_grey_rows

    grey = _load(GREY_YAML)
    rows = build_grey_rows()
    assert len(rows) == len(grey)
    assert {r["Title"] for r in rows} == {e["title"] for e in grey}


def _separators(line: str) -> int:
    """Cell separators in a pipe-table row — escaped pipes are content."""
    return line.replace("\\|", "").count("|")


def _pipe_tables(md: str) -> list[list[str]]:
    """Consecutive runs of pipe rows — one run per markdown table."""
    tables, current = [], []
    for line in md.splitlines():
        if line.startswith("|"):
            current.append(line)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def test_markdown_rows_are_not_ragged():
    """Render oracle: every row carries its own table's column count.

    A title containing a pipe would silently split a row and shift every
    later cell. The emitter owns escaping (ticket 0325), so each table is
    checked against its own header rather than a file-wide width.
    """
    from export_retrieval_protocol import render_markdown

    tables = _pipe_tables(render_markdown())
    assert len(tables) == 2, f"expected the protocol and grey tables, got {len(tables)}"
    for table in tables:
        header, *rest = table
        width = _separators(header)
        ragged = [ln for ln in rest if _separators(ln) != width]
        assert not ragged, (
            f"rows disagree with their header's {width} separators: {ragged[:2]}"
        )


def test_export_writes_both_group_members_from_either_path(tmp_path):
    """Make passes whichever grouped-target member went stale as ``$@``.

    Writing only the file named by ``--output`` would leave the CSV absent
    (or holding markdown) while Make counted the whole group as built.
    """
    from export_retrieval_protocol import main

    for requested in ("tab.csv", "tab.md"):
        out = tmp_path / requested
        main(str(out))
        assert (tmp_path / "tab.csv").read_text(encoding="utf-8").startswith("Source,")
        assert (tmp_path / "tab.md").read_text(encoding="utf-8").startswith("## Retrieval")
        (tmp_path / "tab.csv").unlink()
        (tmp_path / "tab.md").unlink()


def test_markdown_escapes_a_pipe_in_a_cell():
    """The fang: a pipe inside a cell must stop acting as a separator.

    Counting raw pipes would read the escaped form as ragged and the
    unescaped form as fine — precisely backwards — so the guard above counts
    separators, and this pins that distinction.
    """
    from export_retrieval_protocol import _cell

    cell = _cell("Climate | Finance")
    assert _separators(cell) == 0, f"pipe left acting as a separator in {cell!r}"
    assert "|" in cell, "the pipe itself must survive into the published cell"


def test_paper_points_at_the_deposited_protocol():
    """§2.1 tells the reader where the reconstructable protocol lives."""
    sources = _section(_qmd_text(), "2.1")
    assert "tab_retrieval_protocol" in sources, (
        "§2.1 must name the deposited retrieval-protocol table"
    )
    for cfg_name in ("openalex_queries.yaml", "corpus_filter.yaml", "grey_sources.yaml"):
        assert cfg_name in sources, f"§2.1 must name the deposited {cfg_name}"


def test_quoted_tier1_terms_exist_in_the_config():
    """No document may quote a Tier-1 term the harvest never issued.

    The corpus report listed a Japanese term (気候ファイナンス) the config does
    not contain, next to the eight-language claim it is meant to evidence —
    a term substitution rather than a count drift, and invisible to a guard
    that only counts languages. One direction only: these lists summarise,
    so a config term may go unquoted, but a quoted term must be real.
    """
    tier1 = set(_load(QUERIES_YAML)["tiers"][1]["terms"])
    include = os.path.join(
        REPO, "deliverables", "_shared", "_includes", "corpus-construction.md"
    )
    with open(include, encoding="utf-8") as fh:
        line = next(ln for ln in fh if ln.startswith("**Tier 1"))

    quoted = set(re.findall(r'`"([^"]+)"`', line))
    assert quoted, "the Tier-1 paragraph quotes no terms — has it been reworded?"
    invented = quoted - tier1
    assert not invented, (
        f"terms quoted in corpus-construction.md that config never queried: "
        f"{sorted(invented)}"
    )


def test_paper_reports_the_config_concept_group_rule():
    """§2.1's Tier 3/4 co-occurrence rule must match what the harvest applied.

    The language list is guarded above; these three numbers describe the same
    harvest and were the other half of the reviewers' "reconstruct the query"
    complaint, so they get the same treatment.
    """
    cfg = _load(QUERIES_YAML)
    sources = _section(_qmd_text(), "2.1")
    spelled = {2: "two", 3: "three", 4: "four"}

    n_groups = len(cfg["concept_groups"])
    assert spelled[n_groups] in sources or str(n_groups) in sources, (
        f"§2.1 must say the taxonomy has {n_groups} concept groups"
    )
    for tier in (3, 4):
        need = cfg["tiers"][tier]["min_concept_groups"]
        assert spelled[need] in sources or str(need) in sources, (
            f"§2.1 must report Tier {tier}'s {need}-group co-occurrence rule"
        )
    for group in cfg["concept_groups"]:
        assert group in sources, f"§2.1 must name the {group!r} concept group"


def test_paper_states_the_key_document_selection_rule():
    """Ticket 0288's author-validated rule reaches the prose (reviewers: 'key
    according to whom?'). Pinned on the load-bearing nouns, not a phrasing."""
    sources = _section(_qmd_text(), "2.1")
    for token in ("COP", "OECD DAC", "curated"):
        assert token in sources, f"§2.1 key-document rule missing {token!r}"


def test_paper_states_the_outlier_centroid_scope():
    """The reviewers' actual question was global or stratified — answer it from
    config, so the prose cannot outlive the setting it describes."""
    scope = _load(FILTER_YAML)["semantic_outlier"].get("centroid", "global")
    pipeline = _section(_qmd_text(), "2.2")
    if scope == "per_language":
        assert "own language" in pipeline, (
            "config computes the outlier centroid within language; §2.2 must "
            "say so"
        )
        assert "computed globally" not in pipeline, (
            "§2.2 still claims a global centroid the pipeline stopped using"
        )
    else:
        assert "global" in pipeline.lower(), (
            "§2.2 must say the semantic-outlier mean and SD are computed "
            "globally"
        )


def test_paper_does_not_advertise_a_six_flag_filter():
    """Negative guard: the defect is lexically stable, the fix is not.

    "six-flag filter" is how the paper described the pipeline while one of the
    six removed nothing. Pinning the *absence* of that phrase survives any
    rewrite of the replacement prose, which a positive phrase pin would not
    (project rule: prose guards are negative or mechanical).

    Only the hyphenated attributive form is banned: "six flags annotate every
    work" is the true statement, and the count of flags is not the defect —
    calling all six of them a filter is.
    """
    if _load(FILTER_YAML)["semantic_outlier"].get("mode") != "diagnostic":
        pytest.skip("Flag 5 is configured as a filter")
    for label, text in (
        ("data-paper.qmd", _qmd_text()),
        ("corpus-filtering.md", _include_text("corpus-filtering.md")),
    ):
        assert "six-flag" not in text.lower(), (
            f"{label} still advertises a six-flag filter while Flag 5 "
            "removes nothing"
        )


def test_no_generated_caption_advertises_a_six_flag_filter():
    """The caption emitters are prose too, and their output is gitignored.

    `tab_corpus_sources.md` is included into both the data paper and the corpus
    report, so a stale flag count there reaches the rendered PDF while never
    appearing in a diff — the one site in this sweep that no prose review of
    the tracked files could have caught.
    """
    if _load(FILTER_YAML)["semantic_outlier"].get("mode") != "diagnostic":
        pytest.skip("Flag 5 is configured as a filter")
    figures = os.path.join(REPO, "scripts", "figures")
    for name in sorted(os.listdir(figures)):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(figures, name), encoding="utf-8") as fh:
            src = fh.read()
        assert "six-flag" not in src.lower(), (
            f"scripts/figures/{name} emits a six-flag claim into a generated "
            "caption while Flag 5 removes nothing"
        )


def test_paper_names_the_outlier_flag_as_a_diagnostic():
    """One token, not a phrasing: "diagnostic" is this pipeline's term of art.

    A reader counting flags in §2.2 against removals in @tbl-flow has to be
    able to tell that one of the six annotates without deleting (ticket 0361).
    """
    if _load(FILTER_YAML)["semantic_outlier"].get("mode") != "diagnostic":
        pytest.skip("Flag 5 is configured as a filter")
    pipeline = _section(_qmd_text(), "2.2")
    assert "diagnostic" in pipeline.lower(), (
        "§2.2 must name the semantic-distance flag as a diagnostic"
    )
