"""Parse the local RePEc ReDIF mirror into one table (ticket 1810, action 1).

Walks the mirror (``/data/mirrors/RePEc/`` on padme, module ``RePEc-ReDIF`` of
``rsync://rsync.repec.org/``), reads every file whose first 64 KB open a ReDIF
template (content sniffing: the mirror holds ReDIF under ``.rdf``, ``.redif``,
``.RDF``, ``.txt``, no extension, …, next to PDFs and HTML), and writes one row
per ReDIF-Paper, -Article, -Book or -Chapter template.

The RePEc handle is the row key. A handle met in several files (editor backup
copies such as ``*.rdf~``, a series mirrored twice) keeps the row from the
first file in path order, backups last; the others are counted as
``duplicate_handle`` and listed in ``<output stem>.duplicates.csv``. A work
template without a handle cannot be keyed and is counted, not kept.

Outputs (``--output`` is the Parquet table; the others sit next to it):

- ``<stem>.parquet``      the table (columns: ``_redif.to_row`` + ``source_file``, ``encoding``)
- ``<stem>.counts.json``  files seen / sniffed ReDIF / read errors, templates by type,
                          rows kept, duplicates, handle-less, cp1252 files, mirror path
                          and the provenance passed with ``--provenance``
- ``<stem>.duplicates.csv``

Usage (padme; the bulk table stays under ``~/data/projets/…/rel_repec/``):
    uv run python scripts/catalog_rel_repec_redif.py --mirror /data/mirrors/RePEc \\
        --output ~/data/projets/climate-finance-het/rel_repec/<date>/redif.parquet \\
        --provenance provenance.json --jobs 16
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone

import _redif

SKIP_EXT = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".gz", ".png", ".jpg",
            ".jpeg", ".gif", ".xml", ".ps", ".tar", ".tgz", ".z", ".bz2", ".7z")
SNIFF_BYTES = 65536
MAX_BYTES = 512 * 1024 * 1024


def _skip(name: str) -> bool:
    n = name.lower()
    return "@synoeastream" in n or n.endswith(SKIP_EXT)


def _files(root: str) -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for f in sorted(filenames):
            if not _skip(f):
                out.append(os.path.join(dirpath, f))
    return out


def parse_file(path: str, root: str) -> tuple[list[dict], list[tuple[str, str]], Counter]:
    """Rows, (series handle, name) pairs and counters of one file."""
    c: Counter = Counter()
    rows: list[dict] = []
    series: list[tuple[str, str]] = []
    try:
        if os.path.getsize(path) > MAX_BYTES:
            c["files_too_large"] += 1
            return rows, series, c
        with open(path, "rb") as fh:
            head = fh.read(SNIFF_BYTES)
            if not _redif.looks_like_redif(head):
                c["files_not_redif"] += 1
                return rows, series, c
            raw = head + fh.read()
    except OSError:
        c["files_read_error"] += 1
        return rows, series, c
    c["files_redif"] += 1
    text, enc = _redif.decode(raw)
    if enc != "utf-8":
        c["files_cp1252"] += 1
    rel = os.path.relpath(path, root)
    for tpl in _redif.iter_templates(text):
        t = _redif.template_type(tpl) or "(none)"
        c["templates:" + t] += 1
        if t in _redif.SERIES_TYPES:
            series.append(_redif.series_of(tpl))
        if t not in _redif.WORK_TYPES:
            continue
        row = _redif.to_row(tpl)
        if not row["handle"]:
            c["works_without_handle"] += 1
            continue
        row["source_file"] = rel
        row["encoding"] = enc
        rows.append(row)
    return rows, series, c


def parse_dir(args: tuple[str, str]) -> tuple[list[dict], list[tuple[str, str]], Counter]:
    top, root = args
    rows: list[dict] = []
    series: list[tuple[str, str]] = []
    c: Counter = Counter()
    for p in _files(top):
        c["files_seen"] += 1
        r, s, cc = parse_file(p, root)
        rows += r
        series += s
        c.update(cc)
    return rows, series, c


def _backup_last(path: str) -> tuple[int, str]:
    return (1 if path.endswith("~") else 0, path)


def build(root: str, jobs: int) -> tuple[list[dict], list[dict], Counter]:
    """(rows kept, duplicate rows, counters) for the mirror under ``root``."""
    tops = sorted(os.path.join(root, d) for d in os.listdir(root))
    dirs = [t for t in tops if os.path.isdir(t)]
    c: Counter = Counter()
    for f in (t for t in tops if os.path.isfile(t)):
        c["files_seen"] += 1
    all_rows: list[dict] = []
    series: dict[str, str] = {}
    work = [(d, root) for d in dirs]
    if jobs > 1:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            results = list(ex.map(parse_dir, work, chunksize=4))
    else:
        results = [parse_dir(w) for w in work]
    for rows, ser, cc in results:
        all_rows += rows
        c.update(cc)
        for h, n in ser:
            if h and n and h not in series:
                series[h] = n
    all_rows.sort(key=lambda r: _backup_last(r["source_file"]))
    kept: dict[str, dict] = {}
    dups: list[dict] = []
    for r in all_rows:
        key = r["handle"].lower()
        if key in kept:
            dups.append({"handle": r["handle"], "source_file": r["source_file"],
                         "kept_from": kept[key]["source_file"]})
            continue
        if not r["journal"]:
            r["journal"] = series.get(r["series_handle"], "")
        kept[key] = r
    c["series_named"] = len(series)
    c["duplicate_handle"] = len(dups)
    rows = sorted(kept.values(), key=lambda r: r["handle"].lower())
    for r in rows:
        c["rows:" + r["template_type"]] += 1
    c["rows"] = len(rows)
    return rows, dups, c


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mirror", required=True)
    ap.add_argument("--output", required=True, help="Parquet table path")
    ap.add_argument("--provenance", help="JSON file merged into counts.json (refresh date, rsync itemized counts)")
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args(argv)
    import pandas as pd

    t0 = datetime.now(timezone.utc)
    rows, dups, c = build(a.mirror, a.jobs)
    stem = os.path.splitext(a.output)[0]
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    cols = list(_redif.to_row({}).keys()) + ["source_file", "encoding"]
    pd.DataFrame(rows, columns=cols).to_parquet(a.output, index=False)
    with open(stem + ".duplicates.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["handle", "source_file", "kept_from"])
        w.writeheader()
        w.writerows(dups)
    counts = {"mirror": os.path.abspath(a.mirror), "parsed_at": t0.isoformat(timespec="seconds"),
              "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "counts": dict(sorted(c.items()))}
    if a.provenance:
        with open(a.provenance, encoding="utf-8") as fh:
            counts["provenance"] = json.load(fh)
    with open(stem + ".counts.json", "w", encoding="utf-8") as fh:
        json.dump(counts, fh, indent=1)
    print(json.dumps(counts["counts"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
