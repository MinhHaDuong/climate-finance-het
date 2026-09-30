"""REL "Sud et langues" search over sources outside OpenAlex (ticket 1653).

Runs the adapters of ``scripts/rel_sud_sources/`` (SciELO, Redalyc, AJOL...)
and writes, in a fresh output directory:

- ``registry.csv``: one row per query: exact query string, route, endpoint,
  date, count announced, count received, count matched, completion flag and
  stop reason. A query cut short is ``completed`` False, never silently full.
- ``raw/<source>.jsonl.gz``: every record received, normalized (the export).
- ``candidates.csv``: the records handed to the intake exporter
  (``catalog_rel_1653_delivery.py``, pool ticket 1655), each row
  carrying its provenance (source, query id, query string, route, endpoint,
  date, export file). Search routes keep every record the server returned;
  harvest and listing routes keep the records whose title or abstract matched
  the lexicon (``HARVEST_ROUTES``).

An output directory that already holds a registry or a non-empty ``raw/`` is
refused. An adapter that raises still gets its registry row (incomplete,
stop reason ``exception: <type>``) before the run stops.

Usage:
    python scripts/catalog_rel_sud_sources.py --output-dir DIR [--source NAME ...]
        [--list] [--dry-run] [--cap N]
"""

import argparse
import csv
import gzip
import json
import os
import sys
from datetime import datetime, timezone

from rel_sud_sources._common import (
    RECORD_FIELDS,
    discover,
    keep,
    load_lexicon,
)
from utils import get_logger

log = get_logger("rel_sud_sources")

REGISTRY_FIELDS = [
    "query_id", "source", "route", "endpoint", "query_string", "run_at",
    "n_expected", "n_received", "n_matched", "completed", "stop_reason",
]
PROVENANCE_FIELDS = [
    "source", "query_id", "query_string", "route", "endpoint", "run_at",
    "export_file",
]
CANDIDATE_FIELDS = PROVENANCE_FIELDS + RECORD_FIELDS

def run_source(mod, cfg, out_dir, reg, cand, cap, delay):
    src = mod.SOURCE
    export = os.path.join("raw", f"{src['name']}.jsonl.gz")
    with gzip.open(os.path.join(out_dir, export), "at", encoding="utf-8") as raw:
        for spec in mod.plan(cfg):
            run_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            row = {"query_id": spec["query_id"], "source": src["name"],
                   "route": src["route"], "endpoint": spec.get("endpoint", src["endpoint"]),
                   "query_string": spec["query_string"], "run_at": run_at,
                   "n_expected": "", "n_received": 0, "n_matched": 0,
                   "completed": False, "stop_reason": "no response"}
            prov = {k: row[k] for k in PROVENANCE_FIELDS if k in row}
            prov["export_file"] = export
            try:
                for kind, val in mod.fetch(spec, delay):
                    if kind == "meta":
                        row["n_expected"] = val
                    elif kind == "work":
                        raw.write(json.dumps({"query_id": spec["query_id"], **val},
                                             ensure_ascii=False) + "\n")
                        row["n_received"] += 1
                        if keep(src["route"], val):
                            row["n_matched"] += 1
                            cand.writerow({**prov,
                                           **{k: val.get(k, "") for k in RECORD_FIELDS}})
                        if cap and row["n_received"] >= cap:
                            row["stop_reason"] = "record cap"
                            break
                    else:
                        row["stop_reason"] = val
                        row["completed"] = val == ""
            except BaseException as exc:  # the row is written, then the run stops
                row["completed"] = False
                row["stop_reason"] = f"exception: {type(exc).__name__}"
                raise
            finally:
                reg.writerow(row)
            log.info("%s expected=%s received=%s kept=%s %s", spec["query_id"],
                     row["n_expected"], row["n_received"], row["n_matched"],
                     row["stop_reason"] or "complete")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default="config/rel_sud_search.yaml",
                    help="1530 lexicon, reused for every source")
    # Multi-output script (registry, raw exports, candidates): --output-dir.
    ap.add_argument("--output-dir")
    ap.add_argument("--source", action="append", help="adapter name (repeatable)")
    ap.add_argument("--cap", type=int, default=0, help="max records per query (0 = none)")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    adapters = discover()
    if args.list:
        for name, mod in sorted(adapters.items()):
            log.info("%s %s %s", name, mod.SOURCE["route"], mod.SOURCE["endpoint"])
        return 0
    chosen = args.source or sorted(adapters)
    unknown = [s for s in chosen if s not in adapters]
    if unknown:
        log.error("unknown source(s): %s", ", ".join(unknown))
        return 2
    cfg = {"lexicon": load_lexicon(args.config)}
    if args.dry_run:
        for name in chosen:
            for spec in adapters[name].plan(cfg):
                log.info("%s %s", spec["query_id"], spec["query_string"][:160])
        return 0
    if not args.output_dir:
        ap.error("--output-dir is required")
    reg_path = os.path.join(args.output_dir, "registry.csv")
    raw_dir = os.path.join(args.output_dir, "raw")
    if os.path.exists(reg_path) or (os.path.isdir(raw_dir) and os.listdir(raw_dir)):
        log.error("%s already holds a registry or raw exports; use a new --output-dir",
                  args.output_dir)
        return 2
    os.makedirs(os.path.join(args.output_dir, "raw"), exist_ok=True)
    with open(reg_path, "w", encoding="utf-8", newline="") as reg_fh, \
            open(os.path.join(args.output_dir, "candidates.csv"), "w",
                 encoding="utf-8", newline="") as cand_fh:
        reg = csv.DictWriter(reg_fh, REGISTRY_FIELDS)
        cand = csv.DictWriter(cand_fh, CANDIDATE_FIELDS)
        reg.writeheader()
        cand.writeheader()
        for name in chosen:
            run_source(adapters[name], cfg, args.output_dir, reg, cand,
                       args.cap, args.delay)
            reg_fh.flush()
            cand_fh.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
