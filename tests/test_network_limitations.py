"""Tests for the citer-limited network limitations pipeline (ticket 0286).

The R1-14 response letter quotes numbers from
deliverables/_shared/tables/tab_network_limitations.csv and
qa_cocitation_edges_report.json. These tests pin the pure logic (burden-anchor
counting, cluster-presence predicate, candidate census) on synthetic graphs,
and the CLI/Makefile contracts by source inspection (no subprocess in the
fast tier).
"""

import glob
import os
import re

import networkx as nx
import pandas as pd
import yaml

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")


def _graph(authors_by_comm):
    """Graph + partition: {comm_id: [author, ...]} -> (G, partition)."""
    G = nx.Graph()
    partition = {}
    i = 0
    for c, authors in authors_by_comm.items():
        for a in authors:
            G.add_node(f"n{i}", author=a)
            partition[f"n{i}"] = c
            i += 1
    return G, partition


def test_burden_candidates_are_sixteen_distinct():
    from _citer_limited_traditions import BURDEN_CANDIDATES

    assert len(BURDEN_CANDIDATES) == 16
    flat = [v for c in BURDEN_CANDIDATES
            for v in (c if isinstance(c, tuple) else (c,))]
    assert len(set(flat)) == len(flat)


def test_burden_hits_counts_anchors_per_community():
    from _citer_limited_traditions import burden_hits

    G, partition = _graph({0: ["tol", "grubb", "smith"],
                           1: ["nordhaus", "weitzman"]})
    counts, sizes = burden_hits(G, partition)
    assert counts == {0: 2}
    assert sizes == {0: 3, 1: 2}


def test_burden_hits_matches_diacritic_variant():
    from _citer_limited_traditions import burden_hits

    G, partition = _graph({0: ["höhne", "oberthür", "x", "y"]})
    counts, _ = burden_hits(G, partition)
    assert counts == {0: 2}


def test_cluster_present_thresholds():
    from _citer_limited_traditions import cluster_present

    G, partition = _graph({0: ["michaelowa", "sutter", "a", "b"],
                           1: ["haites", "c"]})
    anchors = ["michaelowa", "sutter", "haites"]
    assert cluster_present(G, partition, anchors,
                           min_anchors=2, min_size=4)
    # Size threshold not met when the community is too small
    assert not cluster_present(G, partition, anchors,
                               min_anchors=2, min_size=5)
    # Anchor threshold
    assert not cluster_present(G, partition, anchors,
                               min_anchors=3, min_size=2)


def test_candidates_in_network_counts_variants_once():
    from _citer_limited_traditions import candidates_in_network

    G = nx.Graph()
    G.add_node("a", author="hohne")
    G.add_node("b", author="höhne")
    G.add_node("c", author="tol")
    G.add_node("d", author="nordhaus")
    assert candidates_in_network(G) == 2


def test_candidates_in_network_word_boundary():
    """'stolz' must not match the candidate 'tol'."""
    from _citer_limited_traditions import candidates_in_network

    G = nx.Graph()
    G.add_node("a", author="stolz")
    assert candidates_in_network(G) == 0


def test_config_declares_network_limitations_parameters():
    cfg_path = os.path.join(SCRIPTS, "..", "config", "analysis.yaml")
    with open(cfg_path) as fh:
        cfg = yaml.safe_load(fh)
    nl = cfg["network_limitations"]
    for key in ("citer_cutoff", "n_perm", "n_boot", "seed",
                "edge_sample_n", "edge_sample_seed"):
        assert key in nl, key


def test_compute_script_cli_contract():
    src = open(os.path.join(
        SCRIPTS, "analysis", "compute_network_limitations.py")).read()
    assert "parse_io_args" in src
    assert "--n-boot" in src
    assert "--skip-bootstrap" in src
    assert "NetworkLimitationsSchema" in src
    # Bootstrap must resample citers as DISTINCT documents (the k^2 trap).
    assert "#{i}" in src.replace('f"{d}#{i}"', "#{i}")


def test_plot_script_reads_registry_with_fallback():
    src = open(os.path.join(
        SCRIPTS, "figures", "plot_fig_traditions_pre2008_citers.py")).read()
    assert "community_registry.yml" in src
    assert "plot_fig_traditions" in src  # fallback labels/colors
    assert "save_figure" in src
    assert "fig.savefig" not in src


def test_qa_script_reuses_crossref_idiom():
    src = open(os.path.join(SCRIPTS, "qa", "qa_cocitation_edges.py")).read()
    assert "from _crossref_qa import fetch_crossref_refs, wilson_ci" in src
    assert "--sample-n" in src


def test_makefile_wires_targets():
    mk = open(os.path.join(
        SCRIPTS, "analysis", "network-limitations.mk")).read()
    for t in ("tab_network_limitations.csv",
              "fig_traditions_pre2008_citers.png",
              "qa_cocitation_edges_report.json"):
        assert t in mk, t
    top = open(os.path.join(SCRIPTS, "..", "Makefile")).read()
    assert "network-limitations.mk" in top


def test_response_letter_numbers_trace_to_artifact():
    """Every statistic in the R1-14 paragraph exists in the stats CSV."""
    base = os.path.join(SCRIPTS, "..")
    csv_path = os.path.join(
        base, "deliverables", "_shared", "tables",
        "tab_network_limitations.csv")
    md_path = os.path.join(
        base, "deliverables", "data-paper", "revision-rdj26561",
        "r1-14-network-response.md")
    assert os.path.exists(md_path)
    assert os.path.exists(csv_path)

    df = pd.read_csv(csv_path).set_index("metric")["value"]
    md = open(md_path).read()
    # The headline claims are backed by artifact rows.
    assert df["econ_cross_cluster_edges_observed"] == 0
    for metric in ("econ_cross_share_null_mean", "econ_within_share_z",
                   "burden_candidates_in_network", "boot_burden_rate",
                   "boot_cdm_rate", "boot_pricing_rate"):
        assert metric in df.index, metric
    # The letter quotes the null cross-share percentage and z-score verbatim.
    pct = round(100 * df["econ_cross_share_null_mean"])
    assert f"{pct:.0f}%" in md
    assert f"z = {df['econ_within_share_z']:.1f}" in md


def test_no_response_file_quotes_a_stale_z():
    """No response document quotes a z-score the stats CSV does not produce.

    The presence check above passes as soon as ONE file carries the current
    value, so it cannot see a second file still carrying the old one. That is
    not hypothetical: ticket 0625 regenerated the table (z 9.086 -> 8.738),
    fixed `r1-14-network-response.md`, and left the same R1-14 sentence in
    `response-letter.md` reading z = 9.1 — contradicting the artifact it
    cites, in the document that actually goes to the journal.

    Absence, not presence, is the property worth pinning. Files are discovered
    rather than listed, so a new response document is covered on arrival.

    Three scoping decisions, each paid for by a review round:

    *Which z.* Requiring every z in the bundle to equal this one fails on
    correct prose — the bundle may quote a z from another analysis, and one
    already exists: `lit_poles_z`, the Kouwenberg--Zheng poles separation,
    also a degree-preserving rewiring null and rendered as such in
    `data-paper.qmd`. So the accepted set is every z the pipeline generates,
    not this one value. That is the property worth asserting: a
    degree-preserving z in the response traces to some artifact. A superseded
    9.1 matches nothing and is caught; a legitimate 76 matches and passes.

    *Which spelling.* `z = 8.7`, `z=8.7`, `Z = 8.7`, `z ≈ 8.7` and `a z of
    8.7` are one claim to a reader, and a guard reading one of them is a
    rewrite away from blind. Comparison is numeric at the precision the prose
    chose, not string equality: `z = 8.74` is more precise and correct, and
    a `.1f` string compare would bounce it.

    *Which window.* Matching per line makes an ordinary paragraph rewrap
    blind the guard — the real occurrences sit at 63--73 characters in files
    wrapped near 77, so one added word moves a z onto its own line. The
    search runs over whitespace-collapsed text within a window of the phrase
    instead, which no reflow changes.

    `external-review/` is skipped explicitly rather than by relying on the
    glob being non-recursive — it holds inbound referee text, whose numbers
    are theirs to be wrong about, and an implicit exclusion would evaporate
    the day someone widens the glob.
    """
    base = os.path.join(SCRIPTS, "..")
    bundle = os.path.join(
        base, "deliverables", "data-paper", "revision-rdj26561")
    df = pd.read_csv(os.path.join(
        base, "deliverables", "_shared", "tables",
        "tab_network_limitations.csv")).set_index("metric")["value"]
    generated = [float(df["econ_within_share_z"])]
    with open(os.path.join(
            base, "deliverables", "data-paper", "data-paper-vars.yml")) as fh:
        poles_z = yaml.safe_load(fh).get("lit_poles_z")
    if poles_z is not None:
        generated.append(float(poles_z))

    responses = [p for p in sorted(glob.glob(
        os.path.join(bundle, "**", "*.md"), recursive=True))
        if "external-review" not in os.path.relpath(p, bundle).split(os.sep)]
    assert responses, "revision bundle has no response documents"
    claim_re = re.compile(
        r"degree-preserving.{0,120}?\bz\s*(?:=|≈|of)\s*(\d+(?:\.\d+)?)",
        re.IGNORECASE)
    stale = []
    for path in responses:
        with open(path) as fh:
            text = " ".join(fh.read().split())
        for quoted in claim_re.findall(text):
            decimals = len(quoted.partition(".")[2])
            if not any(float(quoted) == round(g, decimals)
                       for g in generated):
                stale.append(
                    f"{os.path.relpath(path, bundle)} quotes z = {quoted} "
                    f"for a degree-preserving null; the pipeline generates "
                    f"{[round(g, decimals) for g in generated]}")
    assert not stale, "; ".join(stale)


def test_response_provenance_names_the_pinned_corpus():
    """The response's corpus-state line names the corpus `dvc.lock` pins.

    The response asserts, three lines apart, both a corpus state and that
    repeated `make network-limitations` runs are byte-identical. Once the
    numbers are regenerated those two claims constrain each other: if the
    named corpus were really the one in hand, the regeneration would have
    reproduced the old table. Ticket 0625 moved the numbers and initially
    left the line naming a 2026-07-23 checkout the values no longer came
    from — a false provenance claim manufactured by the fix itself.

    Pinning the md5 rather than the date is what makes the claim checkable:
    a date is prose, a hash is the corpus.

    The hash is required *in the bullet that claims it*, not anywhere in the
    file. The document deliberately names two corpus states — the statistics
    table's and the spot-check's earlier one — so a file-wide search would
    be satisfied by the hash sitting in either, and could not see the exact
    defect it exists to catch recur one bullet over.
    """
    base = os.path.join(SCRIPTS, "..")
    lock = yaml.safe_load(open(os.path.join(base, "dvc.lock")))
    pinned = {o["md5"] for stage in lock["stages"].values()
              for o in stage.get("outs", [])
              if o["path"].endswith("refined_citations.csv")}
    assert pinned, "dvc.lock pins no refined_citations.csv"
    md = open(os.path.join(
        base, "deliverables", "data-paper", "revision-rdj26561",
        "r1-14-network-response.md")).read()
    bullet = re.search(
        r"^-\s+Corpus state, statistics table:(.*?)(?=^-\s|\Z)",
        md, re.MULTILINE | re.DOTALL)
    assert bullet, (
        "no 'Corpus state, statistics table:' bullet — the response must "
        "say which corpus the regenerated table came from")
    claimed = " ".join(bullet.group(1).split())
    assert any(h in claimed for h in pinned), (
        f"the statistics-table corpus bullet names no currently pinned "
        f"refined_citations; it says {claimed!r}, dvc.lock pins "
        f"{sorted(pinned)}")
