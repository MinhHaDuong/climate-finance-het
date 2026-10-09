"""Merge several OpenAlex backfill directories into one input directory (ticket 2049).

The generators of the REL deliveries take a single ``--backfill`` directory;
the 2026-10-09 backfill came as two archives (the lane ids and the rest of the
pool). This reads each ``backfill.jsonl.gz`` read-only, refuses a truncated one
and an id present in two archives with different content, and writes
``backfill.jsonl.gz`` (deterministic gzip, mtime 0, first archive's order first)
plus ``MERGED.sha256`` and ``SOURCES.sha256`` (the sha256 of every source file).

Usage:
    python scripts/catalog_rel_oa_backfill_merge.py \\
        --source-dir ~/data/projets/climate-finance-het/rel_openalex_backfill/2026-10-09-lanes \\
        --source-dir ~/data/projets/climate-finance-het/rel_openalex_backfill/2026-10-09-pool \\
        --output-dir ~/data/projets/climate-finance-het/rel_openalex_backfill/2026-10-09-merged
"""

import argparse
import gzip
import hashlib
import json
import os
import sys

from catalog_rel_sud_search import BACKFILL_FILE, read_backfill_records


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def merge(source_dirs, output_dir):
    """Write the merged directory; returns ``(n_ids, sha256 of the merged file)``."""
    out_file = os.path.join(output_dir, BACKFILL_FILE)
    if os.path.exists(out_file):
        raise SystemExit(f"{out_file} exists; an archive is never overwritten")
    seen, lines, sources = {}, [], []
    for d in source_dirs:
        path = os.path.join(d, BACKFILL_FILE)
        recs, truncated = read_backfill_records(path)
        if truncated:
            raise SystemExit(f"{path} is truncated")
        sources.append(f"{_sha256(path)}  {os.path.basename(os.path.normpath(d))}/{BACKFILL_FILE}\n")
        for r in recs:
            key = r["openalex_id"]
            if key in seen:
                if seen[key] != r:
                    raise SystemExit(f"{key} differs between the source archives")
                continue
            seen[key] = r
            lines.append(json.dumps(r, ensure_ascii=False) + "\n")
    os.makedirs(output_dir, exist_ok=True)
    with open(out_file, "wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            gz.write("".join(lines).encode("utf-8"))
    digest = _sha256(out_file)
    with open(os.path.join(output_dir, "MERGED.sha256"), "w", encoding="utf-8") as fh:
        fh.write(f"{digest}  {BACKFILL_FILE}\n")
    with open(os.path.join(output_dir, "SOURCES.sha256"), "w", encoding="utf-8") as fh:
        fh.writelines(sources)
    return len(lines), digest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source-dir", action="append", required=True,
                    help="a catalog_rel_oa_backfill.py output directory; repeat, in order")
    # Multi-output: backfill.jsonl.gz and two checksum files in one directory.
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args(argv)
    n, digest = merge(args.source_dir, args.output_dir)
    print(f"{n} ids {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
