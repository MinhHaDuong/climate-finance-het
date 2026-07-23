#!/usr/bin/env python3
"""Spot-check co-citation edges of the citer-limited network against Crossref.

A co-citation edge (A, B) asserts that at least one citing document in the
corpus cites both A and B. For a random sample of edges of the citer-limited
top-N pre-2007 subgraph (config `network_limitations`), this script picks one
corpus document recorded as co-citing the pair, re-fetches that document's
reference list from Crossref, and checks that both endpoint DOIs appear in
it. Reports the concordance proportion with a 95% Wilson CI — the edge-level
quality evidence cited in the R1-14 response
(deliverables/data-paper/revision-rdj26561/r1-14-network-response.md).

Follows the Test-A idiom of qa_citations.py (link accuracy vs Crossref),
lifted from citation rows to network edges.

Usage:
    uv run python scripts/qa/qa_cocitation_edges.py \
        --output deliverables/_shared/tables/qa_cocitation_edges_report.json
"""

import argparse
import json

import numpy as np
from _citer_limited_traditions import (
    build_top_graph,
    citer_limited_cutoff,
    load_citer_limited,
)
from pipeline_loaders import load_analysis_config
from qa_citations import fetch_crossref_refs, wilson_ci
from script_io_args import parse_io_args, validate_io
from utils import get_logger

log = get_logger("qa_cocitation_edges")


def cociting_sources(cit, a, b):
    """Corpus documents whose reference lists contain both a and b."""
    srcs_a = set(cit.loc[cit["ref_doi"] == a, "source_doi"])
    srcs_b = set(cit.loc[cit["ref_doi"] == b, "source_doi"])
    return sorted(srcs_a & srcs_b)


def check_edges(G, cit, sample_n, rng):
    """Verify a sample of edges; returns (results, summary)."""
    edges = sorted(G.edges())
    n = min(sample_n, len(edges))
    idx = rng.choice(len(edges), size=n, replace=False)
    results = []
    confirmed = errors = 0
    for k, i in enumerate(sorted(idx)):
        a, b = edges[i]
        witnesses = cociting_sources(cit, a, b)
        status, ok, witness = "no_witness", False, None
        for witness in witnesses:
            refs, status = fetch_crossref_refs(witness)
            if status != "ok":
                continue
            ok = a in refs and b in refs
            break
        if status == "ok":
            confirmed += int(ok)
        else:
            errors += 1
        results.append({"ref_a": a, "ref_b": b, "witness": witness,
                        "weight": G[a][b]["weight"], "status": status,
                        "confirmed": bool(ok)})
        log.info("  edge %d/%d: %s -- %s via %s: %s (confirmed=%s)",
                 k + 1, n, a, b, witness, status, ok)
    n_checked = n - errors
    p, lo, hi = wilson_ci(confirmed, n_checked)
    summary = {"n_sampled": n, "n_checked": n_checked,
               "n_confirmed": confirmed, "n_unresolvable": errors,
               "concordance": p, "ci95_low": lo, "ci95_high": hi}
    return results, summary


def main():
    io_args, extra = parse_io_args()
    validate_io(output=io_args.output, inputs=io_args.input)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-n", type=int, default=None,
                        help="Override config network_limitations.edge_sample_n")
    args = parser.parse_args(extra)

    cfg = load_analysis_config()["network_limitations"]
    sample_n = (args.sample_n if args.sample_n is not None
                else int(cfg["edge_sample_n"]))
    rng = np.random.default_rng(int(cfg["edge_sample_seed"]))
    citer_cutoff = citer_limited_cutoff()

    works_path = io_args.input[0] if io_args.input else None
    cit_path = (io_args.input[1]
                if io_args.input and len(io_args.input) >= 2 else None)
    cit, doi_meta, cutoff_year = load_citer_limited(
        citer_cutoff, works_path, cit_path)
    G, _ = build_top_graph(cit, doi_meta, cutoff_year)
    if G is None:
        log.info("Empty network — writing empty report.")
        with open(io_args.output, "w") as fh:
            json.dump({"summary": None, "edges": []}, fh, indent=1)
        return
    log.info("Network: %d nodes, %d edges; sampling %d edges",
             G.number_of_nodes(), G.number_of_edges(), sample_n)

    results, summary = check_edges(G, cit, sample_n, rng)
    report = {"citer_cutoff": citer_cutoff, "ref_cutoff_year": cutoff_year,
              "n_nodes": G.number_of_nodes(), "n_edges": G.number_of_edges(),
              "summary": summary, "edges": results}
    with open(io_args.output, "w") as fh:
        json.dump(report, fh, indent=1)
    log.info("Concordance: %d/%d = %.3f [%.3f, %.3f] (%d unresolvable)",
             summary["n_confirmed"], summary["n_checked"],
             summary["concordance"], summary["ci95_low"],
             summary["ci95_high"], summary["n_unresolvable"])


if __name__ == "__main__":
    main()
