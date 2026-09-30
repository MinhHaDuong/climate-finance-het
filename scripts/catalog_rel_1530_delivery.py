"""Convert the 1530 "Sud et langues" search runs into a REL intake delivery.

Ticket 1731. The 1530 pass (``catalog_rel_sud_search.py``) wrote one
``registry.csv`` and one ``results.jsonl.gz`` per run directory; the final
search is runs ``f`` and ``g`` (88 frozen queries). This script turns them into
a delivery that meets the intake contract (``docs/rel-intake-contract.md``) so
the pool merge reads 1530 like every other lane. It replaces the ad-hoc
builders of the 2026-09-29 archive (``adhoc-scripts/t1530-build-final.py``).

Everything retrieved is delivered, including the works already in the corpus:
the pool merge needs the overlap to report the lane's yield. One row per
OpenAlex work in ``records.csv`` (``record_id`` = the OpenAlex id, first
retrieving query in run order); every further retrieval of the same work is
listed in ``excluded.csv`` as ``duplicate_in_lane``. A work whose OpenAlex
record has no title is ``not_retrievable``. The lane's documented limits come
from ``config/rel_pool.yaml`` (``t1530_delivery.incomplete``) together with any
query the registries mark incomplete.

Usage:
    python scripts/catalog_rel_1530_delivery.py \\
        --run-dir <archive>/padme-rel_sud_runs/20260929f \\
        --run-dir <archive>/padme-rel_sud_runs/20260929g \\
        --output-dir data/rel_intake/t1530-sud-openalex/2026-09-29
"""

import argparse
import csv
import gzip
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone

import qa_rel_intake as ric
import yaml
from utils import get_logger, normalize_doi

log = get_logger("catalog_rel_1530_delivery")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "config", "rel_pool.yaml")

# Columns carried beyond the contract: the 1530 search's own provenance.
EXTRA_RECORD_COLUMNS = ["search_run", "query_ids_all", "kinds", "cited_by_count",
                        "in_refined_v2", "icf_term"]
REGISTRY_COLUMNS = ric.REGISTRY_REQUIRED + [
    "filter", "n_expected", "stop_reason", "kind", "stratum", "language",
    "theme", "search_run"]


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit():
    try:
        return subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _run_name(run_dir):
    return os.path.basename(os.path.normpath(run_dir))


def read_runs(run_dirs):
    """Registry rows and result rows of each run, in the order given."""
    registry, results = [], []
    for run_dir in run_dirs:
        run = _run_name(run_dir)
        with open(os.path.join(run_dir, "registry.csv"), encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                registry.append({**r, "search_run": run})
        with gzip.open(os.path.join(run_dir, "results.jsonl.gz"), "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    results.append({**json.loads(line), "search_run": run})
    return registry, results


def build_registry(registry_rows):
    """Contract registry rows; ``query`` is the exact OpenAlex filter string."""
    ids = Counter(r["query_id"] for r in registry_rows)
    dups = sorted(q for q, n in ids.items() if n > 1)
    if dups:
        raise ValueError(f"query_id reused across runs: {dups[:5]}")
    out = []
    for r in registry_rows:
        completed = str(r.get("completed", "")).strip().lower()
        out.append({
            "query_id": r["query_id"],
            "platform": r.get("platform") or "openalex",
            "query": r["filter"],
            "run_at": r["run_at"],
            "n_received": r["n_received"],
            "completed": "true" if completed == "true" else "false",
            "filter": r["filter"],
            "n_expected": r.get("n_expected", ""),
            "stop_reason": r.get("stop_reason", ""),
            "kind": r.get("kind", ""),
            "stratum": r.get("stratum", ""),
            "language": r.get("language", ""),
            "theme": r.get("theme", ""),
            "search_run": r["search_run"],
        })
    return out


def _blank(v):
    return "" if v is None else str(v)


def _record(w, run_at, retrievals):
    """One contract row for OpenAlex work ``w`` (its first titled retrieval)."""
    wid = w["openalex_id"]
    return {
        "record_id": wid,
        "query_id": w["query_id"],
        "platform": "openalex",
        "retrieved_at": run_at[w["query_id"]],
        "title": w.get("title") or "",
        "platform_record_id": wid,
        "doi": normalize_doi(w.get("doi")),
        "openalex_id": wid,
        "title_original": "",
        "first_author": "",
        "all_authors": "",
        "year": _blank(w.get("year")),
        "publication_date": _blank(w.get("date")),
        "journal": _blank(w.get("journal")),
        "issn": "",
        "doc_type": _blank(w.get("type")),
        "language": _blank(w.get("language")),
        "abstract": _blank(w.get("abstract")),
        "abstract_provenance": "",
        "url": f"https://openalex.org/{wid}",
        "affiliation_countries": "; ".join(w.get("countries") or []),
        "version_hint": "",
        "lane_status": "in_refined_v2" if any(x["in_corpus"] for x in retrievals) else "candidate",
        "lane_note": "",
        "search_run": w["search_run"],
        "query_ids_all": ";".join(dict.fromkeys(x["query_id"] for x in retrievals)),
        "kinds": ";".join(sorted({x["kind"] for x in retrievals})),
        "cited_by_count": _blank(w.get("cited_by_count")),
        "in_refined_v2": "true" if any(x["in_corpus"] for x in retrievals) else "false",
        "icf_term": "true" if any(x.get("icf_term") for x in retrievals) else "false",
    }


def build_records(results, registry):
    """Split result rows into delivered records and excluded rows.

    A work retrieved several times is delivered once, from its first
    retrieval that carries a title; the other retrievals are
    ``duplicate_in_lane``. A work never retrieved with a title is
    ``not_retrievable`` (the contract requires a title).
    """
    run_at = {r["query_id"]: r["run_at"] for r in registry}
    kind = {r["query_id"]: r["kind"] for r in registry}
    by_work = {}
    for w in results:
        by_work.setdefault(w["openalex_id"], []).append({**w, "kind": kind[w["query_id"]]})
    records, excluded = [], []
    for wid, rows in by_work.items():
        titled = [w for w in rows if (w.get("title") or "").strip()]
        if not titled:
            excluded.append({"record_id": wid, "query_id": rows[0]["query_id"],
                             "reason": "not_retrievable", "title": "",
                             "note": "OpenAlex record has no title"})
            excluded += [{"record_id": wid, "query_id": w["query_id"],
                          "reason": "duplicate_in_lane", "title": "",
                          "note": f"also retrieved by {rows[0]['query_id']}"}
                         for w in rows[1:]]
            continue
        keep = titled[0]
        records.append(_record(keep, run_at, rows))
        for w in rows:
            if w is keep:
                continue
            excluded.append({"record_id": wid, "query_id": w["query_id"],
                             "reason": "duplicate_in_lane", "title": w.get("title") or "",
                             "note": f"also retrieved by {keep['query_id']}"})
    return records, excluded


def build_manifest(cfg, records, excluded, registry, inputs, delivery, delivered_at):
    incomplete = [{"unit": r["query_id"], "reason": r["stop_reason"]}
                  for r in registry if r["completed"] == "false"]
    incomplete += [dict(x) for x in cfg.get("incomplete", [])]
    return {
        "lane": cfg["lane"],
        "ticket": str(cfg["ticket"]),
        "delivery": delivery,
        "delivered_at": delivered_at,
        "producer": {"script": "scripts/catalog_rel_1530_delivery.py",
                     "commit": _git_commit(), "machine": socket.gethostname()},
        "counts": {"records": len(records),
                   "excluded": dict(sorted(Counter(r["reason"] for r in excluded).items()))},
        "coverage": "incomplete" if incomplete else "complete",
        "incomplete": incomplete,
        "needs_human": [],
        "supersedes": None,
        "notes": cfg.get("notes", ""),
        "inputs": inputs,
    }


def _write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


def write_delivery(out_dir, records, excluded, registry, manifest):
    os.makedirs(out_dir, exist_ok=True)
    _write_csv(os.path.join(out_dir, "records.csv"),
               ric.RECORD_COLUMNS + EXTRA_RECORD_COLUMNS, records)
    _write_csv(os.path.join(out_dir, "registry.csv"), REGISTRY_COLUMNS, registry)
    _write_csv(os.path.join(out_dir, "excluded.csv"), ric.EXCLUDED_COLUMNS, excluded)
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def publish_delivery(out_dir, records, excluded, registry, manifest):
    """Write and check the delivery beside its target, then rename it into place.

    The staging tree ``<lane_dir>/.staging-*/<lane>/<delivery>`` keeps the lane
    and delivery names the checker compares with the manifest, and sits on the
    target's filesystem so the final rename is atomic. A delivery that fails
    the contract leaves nothing behind (not even a lane directory this run
    created). Returns the contract violations.
    """
    out_dir = os.path.abspath(out_dir)
    lane_dir = os.path.dirname(out_dir)
    created_lane = not os.path.isdir(lane_dir)
    os.makedirs(lane_dir, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=".staging-", dir=lane_dir)
    try:
        stage = os.path.join(staging, os.path.basename(lane_dir), os.path.basename(out_dir))
        write_delivery(stage, records, excluded, registry, manifest)
        errors = ric.check_delivery(stage)
        if not errors:
            os.rename(stage, out_dir)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        if created_lane and not os.listdir(lane_dir):
            os.rmdir(lane_dir)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", action="append", required=True,
                        help="a 1530 run directory (registry.csv + results.jsonl.gz); repeat, in run order")
    # Multi-output: a delivery is four files in one directory.
    parser.add_argument("--output-dir", required=True,
                        help="data/rel_intake/<lane>/<delivery>")
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--delivered-at", default=None,
                        help="ISO datetime recorded in the manifest (default: now, UTC)")
    args = parser.parse_args(argv)

    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)["t1530_delivery"]
    if os.path.exists(args.output_dir):
        log.error("%s already exists; deliveries are immutable", args.output_dir)
        return 1

    reg_rows, results = read_runs(args.run_dir)
    registry = build_registry(reg_rows)
    records, excluded = build_records(results, registry)
    inputs = [{"path": os.path.join(_run_name(d), f), "sha256": _sha256(os.path.join(d, f))}
              for d in args.run_dir for f in ("registry.csv", "results.jsonl.gz")]
    delivered_at = args.delivered_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    delivery = os.path.basename(os.path.normpath(args.output_dir))
    manifest = build_manifest(cfg, records, excluded, registry, inputs, delivery, delivered_at)
    errors = publish_delivery(args.output_dir, records, excluded, registry, manifest)
    for e in errors:
        log.error("%s", e)
    log.info("%d result rows -> %d records, excluded %s, %d registry rows",
             len(results), len(records), manifest["counts"]["excluded"], len(registry))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
