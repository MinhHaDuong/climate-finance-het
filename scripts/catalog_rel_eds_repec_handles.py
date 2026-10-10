"""Decode the RePEc handles hidden in EDS accession numbers and check them
against the local RePEc mirror (ticket 2040).

An ``edsrep.`` accession number spells a RePEc handle without its colons
(``scripts/_rel_eds_ids.py``): archive and series are exact, the item is
compared on lower-case letters and digits. Each decoded number is looked up
among the ``Handle:`` lines of the mirror files of its series directory and
labelled ``matched`` (exactly one mirror handle), ``ambiguous``, ``unmatched``
(series present, item absent), ``no_series`` or ``undecodable``. No row is
dropped. ``EDSZBW`` numbers are K10plus PPNs: they are counted by check digit
and not looked up anywhere.

Controls run before any count: a known record (``edsrep.p.nbr.nberwo.35497``,
RePEc:nbr:nberwo:35497) must come out ``matched`` with that handle, and an
invented item of the same series must come out ``unmatched``; otherwise the
script stops without writing a count.

Usage:
    python scripts/catalog_rel_eds_repec_handles.py --results EDS_DIR/results.jsonl.gz \
        --mirror /data/mirrors/RePEc --output-dir OUT_DIR
Writes ``eds_repec_handles.csv`` (one row per distinct accession number) and
``eds_repec_handles.json`` (controls and counts).
"""

import argparse
import csv
import gzip
import json
import os
import re
import sys
from collections import Counter, defaultdict

import _redif
import _rel_eds_ids as ids
from utils import get_logger

log = get_logger("rel_eds_repec_handles")

CONTROL_AN = "edsrep.p.nbr.nberwo.35497"
CONTROL_HANDLE = "RePEc:nbr:nberwo:35497"
NEGATIVE_AN = "edsrep.p.nbr.nberwo.99999999"
REDIF_SUFFIXES = {".rdf", ".redif", ".txt", ""}
_HANDLE_LINE = re.compile(r"^\s*handle\s*:(.*)$", re.IGNORECASE | re.MULTILINE)
FIELDS = ["eds_an", "kind", "archive", "series", "item", "candidate", "status", "handle"]


def read_ans(paths):
    """Distinct accession numbers (in file order) of EDS results, and the
    provider of each retrieval row: ``[(an, provider, doi)]``."""
    rows, seen = [], set()
    for path in paths:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                m = re.match(r"EDS-([A-Za-z]+)-", r.get("search_id", ""))
                rows.append((r["eds_an"], m.group(1) if m else "", r.get("doi") or ""))
                seen.add(r["eds_an"])
    return rows


def mirror_files(mirror, archive, series):
    base = os.path.join(mirror, archive, series)
    for root, _, files in os.walk(base):
        for name in sorted(files):
            if name.endswith("~") or os.path.splitext(name)[1].lower() not in REDIF_SUFFIXES:
                continue
            yield os.path.join(root, name)


def build_index(mirror, wanted):
    """``({(archive, series, item_key): {handle}}, {(archive, series) present})``
    over the mirror files of the wanted series directories."""
    index, present = defaultdict(set), set()
    for archive, series in sorted(wanted):
        for path in mirror_files(mirror, archive, series):
            with open(path, "rb") as fh:
                raw = fh.read()
            if not _redif.looks_like_redif(raw[:65536]):
                continue
            text, _ = _redif.decode(raw)
            for m in _HANDLE_LINE.finditer(text):
                h = _redif.norm_handle(m.group(1).strip())
                key = ids.mirror_key(h) if h else None
                if key and key[:2] == (archive, series):
                    index[key].add(h)
                    present.add(key[:2])
    return index, present


def resolve_all(ans, index, present):
    out = []
    for an in ans:
        d = ids.decode_edsrep(an)
        status, handle = ids.resolve(d, index, series=present)
        out.append({"eds_an": an, **({k: d[k] for k in ("kind", "archive", "series", "item", "candidate")}
                                     if d else {}), "status": status, "handle": handle})
    return out


def controls(index, present):
    pos = resolve_all([CONTROL_AN], index, present)[0]
    neg = resolve_all([NEGATIVE_AN], index, present)[0]
    ok = (pos["status"] == ids.STATUS_MATCHED and pos["handle"].lower() == CONTROL_HANDLE.lower()
          and neg["status"] == ids.STATUS_UNMATCHED)
    return ok, {"positive": pos, "negative": neg}


def run(args):
    rows = read_ans(args.results)
    rep = [a for a in dict.fromkeys(r[0] for r in rows) if a.startswith("edsrep.")]
    wanted = {(d["archive"], d["series"]) for d in map(ids.decode_edsrep, rep + [CONTROL_AN]) if d}
    index, present = build_index(args.mirror, wanted)
    ok, ctl = controls(index, present)
    if not ok:
        log.error("control failed, no count written: %s", json.dumps(ctl))
        return 1
    resolved = resolve_all(rep, index, present)
    os.makedirs(args.output_dir, exist_ok=True)
    with open(os.path.join(args.output_dir, "eds_repec_handles.csv"), "w", encoding="utf-8",
              newline="") as fh:
        w = csv.DictWriter(fh, FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(resolved)
    by_an = {r["eds_an"]: r["status"] for r in resolved}
    zbw = [a for a in dict.fromkeys(r[0] for r in rows) if a.startswith("EDSZBW")]
    summary = {
        "controls": ctl,
        "mirror_series_scanned": len(wanted), "mirror_series_with_handles": len(present),
        "mirror_handles_indexed": sum(len(v) for v in index.values()),
        "distinct_edsrep_an": len(rep), "status_distinct": dict(Counter(by_an.values())),
        "by_kind": {k: dict(Counter(r["status"] for r in resolved if r.get("kind") == k))
                    for k in sorted({r.get("kind") for r in resolved if r.get("kind")})},
        # retrieval rows (record level) without an EDS DOI, by provider and handle status
        "rows_without_doi": {p: dict(Counter(by_an.get(a, "not_edsrep") for a, pp, doi in rows
                                             if pp == p and not doi))
                             for p in sorted({r[1] for r in rows})},
        "distinct_zbw_an": len(zbw), "zbw_ppn_check_digit_valid": sum(map(ids.ppn_valid, zbw)),
    }
    with open(os.path.join(args.output_dir, "eds_repec_handles.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, ensure_ascii=False)
    log.info("%s", json.dumps(summary, indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", required=True, nargs="+", help="results.jsonl.gz of EDS runs")
    ap.add_argument("--mirror", default="/data/mirrors/RePEc")
    # Multi-output script (table and summary): --output-dir.
    ap.add_argument("--output-dir", required=True)
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
