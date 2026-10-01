"""Fetch and archive the REL venue registries, one dated pull (ticket 1841).

For each registry of ``config/rel_venue_registries.yaml`` (Kanalregisteret
table 851, Scopus source title list, DOAJ change logs, Retraction Watch
Hijacked Journal Checker): download the raw file into
``<output-dir>/<YYYY-MM-DD>/``, make it read-only, write the directory's
``MANIFEST.sha256``, parse it with its filter (``_rel_venue_registries``) and
record the pull in ``config/rel_venue_registry_pulls.csv`` (URL, date, sha256,
bytes, data rows, flagged entries, filter).

Re-runnable: a file already archived for that date is never overwritten; it is
re-hashed and re-parsed, so a second run on the same day only refreshes the
record. A new day is a new directory. Point ``use:`` in the config at the pull
the build should read.

Usage:
    python scripts/catalog_rel_venue_registries.py --output-dir DIR
        [--date YYYY-MM-DD] [--registry NAME ...]
"""

import argparse
import csv
import os
import re
import stat
import sys
from datetime import date

import _rel_venue_registries as rvr
import requests
import yaml
from utils import get_logger

log = get_logger("catalog_rel_venue_registries")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "config", "rel_venue_registries.yaml")
DEFAULT_PULLS = os.path.join(ROOT, "config", "rel_venue_registry_pulls.csv")
PULL_COLUMNS = ["registry", "pull_date", "file", "url", "sha256", "bytes", "rows",
                "flagged", "filter"]
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) climate-finance-het REL venue registries"}


# One session for the few registry downloads: connection reuse and one
# place for the headers; every call sets its own timeout.
SESSION = requests.Session()
SESSION.headers.update(UA)


def scopus_xlsx_url(page_url):
    """The current source-title-list xlsx linked from Elsevier's content policy page."""
    html = SESSION.get(page_url, timeout=120).text
    links = sorted(set(re.findall(r'(?:https:)?//downloads\.ctfassets\.net/[^"\\\s]+\.xlsx', html)))
    if len(links) != 1:
        raise RuntimeError(f"expected one xlsx link on {page_url}, found {links}")
    return "https:" + links[0] if links[0].startswith("//") else links[0]


def download(url, dest):
    """Fetch ``url`` into ``dest`` unless it is already archived; make it read-only."""
    if os.path.exists(dest):
        log.info("kept %s (already archived)", dest)
        return
    tmp = dest + ".part"
    with SESSION.get(url, timeout=600, stream=True) as r:
        r.raise_for_status()
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
    os.replace(tmp, dest)
    os.chmod(dest, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    log.info("archived %s (%d bytes)", dest, os.path.getsize(dest))


def write_manifest(day_dir):
    names = sorted(n for n in os.listdir(day_dir)
                   if n != "MANIFEST.sha256" and not n.endswith(".part"))
    path = os.path.join(day_dir, "MANIFEST.sha256")
    if os.path.exists(path):
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    with open(path, "w", encoding="utf-8") as fh:
        for n in names:
            fh.write(f"{rvr.sha256_file(os.path.join(day_dir, n))}  {n}\n")
    os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def parse(name, spec, day_dir):
    """``(rows, entries)`` of one archived registry."""
    eu = spec.get("entry_url", "{id}")
    if name == "kanalregisteret":
        return rvr.parse_kanalregisteret(os.path.join(day_dir, spec["file"]), eu)
    if name == "scopus_discontinued":
        return rvr.parse_scopus_discontinued(os.path.join(day_dir, spec["file"]), eu)
    if name == "doaj_withdrawn":
        return rvr.parse_doaj_withdrawn([os.path.join(day_dir, f) for f in spec["files"]],
                                        spec["reason_pattern"], eu)
    if name == "hijacked":
        return rvr.parse_hijacked(os.path.join(day_dir, spec["file"]), spec.get("page", ""))
    raise KeyError(name)


def fetch(name, spec, day_dir):
    """Download one registry; ``[(file, url)]`` of what it archived."""
    if name == "scopus_discontinued":
        pairs = [(spec["file"], scopus_xlsx_url(spec["page"]))]
    elif "files" in spec:
        pairs = list(zip(spec["files"], spec["urls"]))
    else:
        pairs = [(spec["file"], spec["url"])]
    for fname, url in pairs:
        download(url, os.path.join(day_dir, fname))
    return pairs


def load_pulls(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_pulls(path, rows):
    rows = sorted(rows, key=lambda r: (r["pull_date"], r["registry"], r["file"]))
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=PULL_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    # Multi-output: the dated pull directory under --output-dir (the archive root)
    # and the pulls record (--pulls).
    ap.add_argument("--output-dir", required=True, help="registry archive root")
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--pulls", default=DEFAULT_PULLS)
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--registry", action="append", help="default: all")
    args = ap.parse_args(argv)

    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    names = args.registry or sorted(cfg["registries"])
    day_dir = os.path.join(args.output_dir, args.date)
    os.makedirs(day_dir, exist_ok=True)

    pulls = [p for p in load_pulls(args.pulls)
             if not (p["pull_date"] == args.date and p["registry"] in names)]
    for name in names:
        spec = cfg["registries"][name]
        pairs = fetch(name, spec, day_dir)
        rows, entries = parse(name, spec, day_dir)
        log.info("%s: %d rows, %d flagged", name, rows, len(entries))
        for i, (fname, url) in enumerate(pairs):
            path = os.path.join(day_dir, fname)
            pulls.append({"registry": name, "pull_date": args.date, "file": fname, "url": url,
                          "sha256": rvr.sha256_file(path), "bytes": os.path.getsize(path),
                          # rows and flagged describe the registry, on its first file's line
                          "rows": rows if i == 0 else "", "flagged": len(entries) if i == 0 else "",
                          "filter": spec["filter"] if i == 0 else ""})
    write_manifest(day_dir)
    write_pulls(args.pulls, pulls)
    log.info("pull %s recorded in %s", args.date, args.pulls)
    return 0


if __name__ == "__main__":
    sys.exit(main())
