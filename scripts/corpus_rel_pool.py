"""Build the REL pool: pinned catalogue + every lane delivery (tickets 1731, 1655).

Reads the pinned merged catalogue (``config/rel_pool.yaml`` → ``catalogue``;
refused unless its md5 and row count match) and every delivery under
``data/rel_intake/<lane>/<delivery>/`` that no other delivery supersedes. Each
delivery is checked against the intake contract (``qa_rel_intake``); one
failing delivery aborts the merge with its violations.

Keys (``_rel_pool_keys``): normalized DOI, OpenAlex id, Handle (the only URL
that is a key), title + year; ``no_dedup_key`` rows of ``excluded.csv`` enter
as title-only works. Deduplication (``_rel_pool_dedup``) is one union-find
over all rows, catalogue and lanes alike; its module docstring gives the
cascade. DOIs are compared as normalized strings, never resolved: a malformed
DOI is kept and counted (``doi_malformed``).

Outputs (required explicit ``--output-dir``):

- ``pool.csv``: one row per work. ``work_key`` is ``openalex:W…`` when a member
  carries an OpenAlex id, else ``doi:<doi>``, else ``url:<handle key>``, else
  ``title:<title>|<year>``; title keys that two works share (generic
  title-only rows kept apart) get ``#<first member record id>``. Metadata come
  from the first non-empty member: catalogue rows first, then lanes in
  ``lane_order``; the abstract alone is chosen by quality (``_rel_pool_abstract``;
  ``abstract_source`` is the lane that supplied it, ``abstract_flag`` is ``ok``,
  ``truncated_suspect``, ``highlights``, ``stub`` or ``no_abstract``). Provenance: ``in_catalogue``, ``sources`` (``catalogue``
  then lane ids), ``n_sources``, ``member_record_ids``.
- Enrichment tables (``enrichment`` in the config; ticket 2052,
  ``_rel_pool_enrich``) fill a blank abstract or resource type per work without
  changing a key or a provenance column; with any table configured the pool
  gains ``doc_type_source``, with none it is byte-identical to before.
- ``merge_report.json`` / ``merge_report.md``: the per-delivery report
  (``_rel_pool_report``).

Dedup version (``dedup_version`` in the config, ``--dedup-version`` on the
command line; ticket 2047). Version 1, the default, builds the pool above.
Version 2 (new title key, RePEc handle key, a working paper and its article
as one work; ``_rel_pool_dedup``; its work keys add ``repec:<handle>`` after
``url:`` and before ``title:``) builds no pool and writes nothing in
``--output-dir``: it computes both versions on the
same rows and writes, in ``--migration-dir`` (required, outside the output
directory), the report of what version 2 would change and the append-only
migration table ``old work_key -> new work_key`` (``_rel_pool_migration``).
No label table is read or written. Ticket 2048 switches the pool.

Usage:
    python scripts/corpus_rel_pool.py [--config config/rel_pool.yaml] \\
        [--catalogue PATH] [--intake-dir DIR] --output-dir data/rel_pool \\
        [--dedup-version 2 --migration-dir DIR]
"""

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict

import qa_rel_intake as ric
import yaml
from _rel_pool_abstract import select_abstract
from _rel_pool_dedup import check_version, cluster, title_normalizer
from _rel_pool_enrich import EXTRA_COLUMNS, Enrichment, load_tables
from _rel_pool_keys import norm_openalex, norm_year, repec_key, url_ids
from _rel_pool_migration import write_migration
from _rel_pool_report import CATALOGUE, RelPoolError, make_report, report_markdown
from utils import get_logger, normalize_doi, normalize_title

log = get_logger("corpus_rel_pool")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "config", "rel_pool.yaml")

# Exclusion reason whose rows are kept in the pool as title-only works.
NO_DEDUP_KEY = "no_dedup_key"

# Pool metadata columns, filled from the first non-empty member.
META_COLUMNS = ["native_titleless_provenance", "is_paratext", "doi", "openalex_id", "title", "first_author", "all_authors",
                "year", "journal", "abstract", "language", "doc_type",
                "affiliation_countries", "affiliations", "cited_by_count"]
POOL_COLUMNS = (["work_key"] + META_COLUMNS
                + ["version_hint", "all_dois", "all_openalex_ids", "in_catalogue",
                   "catalogue_sources", "sources", "n_sources", "member_record_ids",
                   "abstract_source", "abstract_flag"])


# ── Inputs ───────────────────────────────────────────────


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _ids(r, openalex_field):
    """DOI, OpenAlex id and Handle of a raw row; a resolver URL fills a blank id."""
    u_doi, u_oa, handle = url_ids(r.get("url"))
    return {"doi": normalize_doi(r.get("doi")) or normalize_doi(u_doi),
            "openalex_id": norm_openalex(openalex_field) or u_oa, "handle": handle}


def load_catalogue(path, expected_md5, expected_rows):
    """Catalogue rows, normalized; refuse any file but the pinned one."""
    md5 = _md5(path)
    if md5 != expected_md5:
        raise RelPoolError(f"catalogue {path} has md5 {md5}, config pins {expected_md5}")
    raw = _read_csv(path)
    if expected_rows is not None and len(raw) != expected_rows:
        raise RelPoolError(f"catalogue {path} has {len(raw)} rows, config pins {expected_rows}")
    rows = []
    for i, r in enumerate(raw):
        rows.append({
            "origin": CATALOGUE, "delivery": CATALOGUE,
            "record_id": f"{r.get('source', '')}:{r.get('source_id') or i}",
            **_ids(r, r.get("source_id")),
            "title": r.get("title") or "",
            "first_author": r.get("first_author") or "",
            "all_authors": r.get("all_authors") or "",
            "year": norm_year(r.get("year")),
            "journal": r.get("journal") or "",
            "abstract": r.get("abstract") or "",
            "language": r.get("language") or "",
            "doc_type": "",
            "affiliation_countries": "",
            "affiliations": r.get("affiliations") or "",
            "cited_by_count": r.get("cited_by_count") or "",
            "version_hint": "",
            "catalogue_source": r.get("source") or "",
        })
    dup = [k for k, n in Counter(r["record_id"] for r in rows).items() if n > 1]
    if dup:
        raise RelPoolError(f"catalogue record ids (source:source_id) not unique: {dup[:5]}")
    return rows, md5


def _supersedes(manifest, lane):
    """Delivery ids (``lane/delivery``) a manifest declares it supersedes."""
    sup = manifest.get("supersedes")
    if not sup:
        return set()
    items = sup if isinstance(sup, list) else [sup]
    return {s if "/" in str(s) else f"{lane}/{s}" for s in map(str, items)}


def find_deliveries(intake_dir):
    """Live deliveries as ``(delivery_id, path, manifest)``, superseded ones dropped."""
    found = []
    if not os.path.isdir(intake_dir):
        return [], []
    for lane in sorted(os.listdir(intake_dir)):
        lane_dir = os.path.join(intake_dir, lane)
        if not os.path.isdir(lane_dir):
            continue
        for delivery in sorted(os.listdir(lane_dir)):
            path = os.path.join(lane_dir, delivery)
            if not os.path.isdir(path):
                continue
            manifest = {}
            mpath = os.path.join(path, "manifest.json")
            if os.path.isfile(mpath):
                # A missing manifest is left to the contract check; an unreadable
                # one would silently drop the delivery's supersedes, so it aborts.
                try:
                    with open(mpath, encoding="utf-8") as fh:
                        manifest = json.load(fh)
                except json.JSONDecodeError as exc:
                    raise RelPoolError(f"{mpath}: not valid JSON ({exc})") from exc
                if not isinstance(manifest, dict):
                    raise RelPoolError(f"{mpath}: top level must be an object")
            found.append((f"{lane}/{delivery}", path, manifest))
    edges = {did: _supersedes(manifest, did.split("/")[0]) for did, _, manifest in found}
    _check_supersedes(edges)
    superseded = set().union(*edges.values()) if edges else set()
    live = [d for d in found if d[0] not in superseded]
    return live, sorted(superseded)


def _check_supersedes(edges):
    """A supersedes target must exist and the relation must have no cycle."""
    missing = sorted(f"{did} -> {t}" for did, targets in edges.items()
                     for t in targets if t not in edges)
    if missing:
        raise RelPoolError("supersedes names no existing delivery: " + "; ".join(missing))
    state = {}

    def visit(did, path):
        state[did] = "open"
        for t in sorted(edges[did]):
            if state.get(t) == "open":
                raise RelPoolError("supersedes cycle: " + " -> ".join(path + [t]))
            if t not in state:
                visit(t, path + [t])
        state[did] = "done"

    for did in sorted(edges):
        if did not in state:
            visit(did, [did])


def check_deliveries(deliveries):
    """Abort on the first delivery that violates the contract, listing its faults."""
    for did, path, _ in deliveries:
        errors = ric.check_delivery(path)
        if errors:
            raise RelPoolError(f"delivery {did} violates the intake contract:\n  "
                               + "\n  ".join(errors))


def load_delivery(did, path):
    from _rel_titleless_intake import validate_admission
    with open(os.path.join(path, "manifest.json"), encoding="utf-8") as fh:
        admission = validate_admission(path, json.load(fh), _read_csv(os.path.join(path, "records.csv")))
    rows = []
    for r in _read_csv(os.path.join(path, "records.csv")):
        rows.append({
            "origin": did.split("/")[0], "delivery": did,
            "native_titleless_provenance": admission.get(r["record_id"], ""), "is_paratext": r.get("is_paratext") or "",
            "record_id": f"{did}:{r['record_id']}",
            **_ids(r, r.get("openalex_id")),
            # Dedup version 2 only (step 2c): the verified handle, else a
            # record_id that is a handle (the RePEc mirror lane).
            "repec": repec_key(r.get("repec_handle")) or repec_key(r["record_id"]),
            **{c: r.get(c) or "" for c in ("title", "first_author", "all_authors",
                                            "journal", "abstract", "language", "doc_type",
                                            "affiliation_countries", "version_hint")},
            "year": norm_year(r.get("year")),
            "affiliations": "",
            "cited_by_count": r.get("cited_by_count") or "",
            "catalogue_source": "",
        })
    excl_rows = _read_csv(os.path.join(path, "excluded.csv"))
    for r in excl_rows:
        if r.get("reason") == NO_DEDUP_KEY and (r.get("title") or "").strip():
            rows.append({
                "origin": did.split("/")[0], "delivery": did,
                "record_id": f"{did}:excluded:{r['record_id']}",
                "doi": "", "openalex_id": "", "handle": "", "year": "", "title": r["title"],
                "repec": repec_key(r["record_id"]),
                **{c: "" for c in ("first_author", "all_authors", "journal", "abstract",
                                   "language", "doc_type", "affiliation_countries",
                                   "version_hint", "affiliations", "cited_by_count",
                                   "catalogue_source")},
                "title_only": True,
            })
    excluded = Counter(r.get("reason") for r in excl_rows)
    return rows, dict(sorted(excluded.items()))


# ── Pool ─────────────────────────────────────────────────


def _work_key(merged, handle="", repec="", norm=normalize_title):
    if merged["openalex_id"]:
        return f"openalex:{merged['openalex_id']}"
    if merged["doi"]:
        return f"doi:{merged['doi']}"
    if handle:
        return f"url:{handle}"
    if repec:
        return repec
    return f"title:{norm(merged['title'])}|{merged['year']}"


def build_pool(rows, roots, lane_rank, version=1, enrich=None):
    """One pool row per component; members ordered catalogue first, then lanes.

    Version 2 names a work with its RePEc handle after the Handle and before
    the title, and its title key with ``_rel_title_key``; version 1 has
    neither (the pool's work keys).

    ``enrich`` (an ``Enrichment``, ticket 2052) fills abstract and doc_type
    from its tables after the members; it changes no key or provenance column."""
    norm = title_normalizer(version)
    members = defaultdict(list)
    for i, root in enumerate(roots):
        members[root].append(i)

    def rank(i):
        r = rows[i]
        return (0 if r["origin"] == CATALOGUE else 1 + lane_rank[r["origin"]], r["delivery"], i)

    if enrich:
        enrich.match(rows, members)
    pool = []
    for root in sorted(members):
        idx = sorted(members[root], key=rank)
        mem = [rows[i] for i in idx]
        merged = {c: next((m.get(c, "") for m in mem if m.get(c)), "") for c in META_COLUMNS}
        merged["abstract"], merged["abstract_source"], merged["abstract_flag"] = \
            select_abstract(mem, merged["title"])
        if enrich:
            enrich.fill(merged, mem, root)
        origins = list(dict.fromkeys(m["origin"] for m in mem))
        merged.update({
            "version_hint": ";".join(dict.fromkeys(m["version_hint"] for m in mem if m["version_hint"])),
            "all_dois": ";".join(sorted({m["doi"] for m in mem if m["doi"]})),
            "all_openalex_ids": ";".join(sorted({m["openalex_id"] for m in mem if m["openalex_id"]})),
            "in_catalogue": "true" if CATALOGUE in origins else "false",
            "catalogue_sources": ";".join(sorted({m["catalogue_source"] for m in mem
                                                  if m["catalogue_source"]})),
            "sources": ";".join(origins),
            "n_sources": len(origins),
            "member_record_ids": ";".join(m["record_id"] for m in mem),
        })
        repec = next((m["repec"] for m in mem if m.get("repec")), "") if version >= 2 else ""
        merged["work_key"] = _work_key(merged, next((m["handle"] for m in mem
                                                     if m.get("handle")), ""), repec, norm)
        pool.append(merged)
    keys = Counter(p["work_key"] for p in pool)
    for p in pool:
        # Works with no identifier and one title (generic title-only rows kept
        # apart, id-less catalogue rows) are told apart by their first member.
        if keys[p["work_key"]] > 1 and p["work_key"].startswith("title:"):
            p["work_key"] += "#" + p["member_record_ids"].split(";", 1)[0]
    dup = [k for k, n in Counter(p["work_key"] for p in pool).items() if n > 1]
    if dup:
        raise RelPoolError(f"work_key not unique: {dup[:5]}")
    return pool


def _write_pool(path, pool, columns=POOL_COLUMNS):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        for p in pool:
            w.writerow(p)


def _check_migration_dir(migration_dir, out_dir):
    """The migration directory exists apart from the pool: never in or above it."""
    if not migration_dir:
        raise RelPoolError("dedup_version 2 writes a report and a migration table: "
                           "--migration-dir is required")
    mig, out = os.path.realpath(migration_dir), os.path.realpath(out_dir)
    for pool_dir in (out, os.path.join(ROOT, "data", "rel_pool")):
        if os.path.commonpath([mig, pool_dir]) in (mig, pool_dir):
            raise RelPoolError(f"--migration-dir {migration_dir} overlaps the pool directory "
                               f"{pool_dir}; version 2 writes nothing there")


def load_rows(cfg, catalogue_path, intake_dir):
    """Every input row, checked: the pinned catalogue then the live deliveries.

    Returns (rows, catalogue rows, catalogue md5, deliveries, superseded,
    excluded counts per delivery, lane rank)."""
    cat_cfg = cfg["catalogue"]
    cat_rows, md5 = load_catalogue(catalogue_path, cat_cfg["md5"], cat_cfg.get("rows"))
    deliveries, superseded = find_deliveries(intake_dir)
    check_deliveries(deliveries)

    order = list(cfg.get("lane_order") or [])
    lanes = sorted({did.split("/")[0] for did, _, _ in deliveries})
    extra = [lane for lane in lanes if lane not in order]
    if extra:
        log.warning("lanes not in lane_order, ranked after it by name: %s", extra)
    lane_rank = {lane: k for k, lane in enumerate(order + extra)}

    rows = list(cat_rows)
    excluded = {}
    for did, path, _ in deliveries:
        drows, excluded[did] = load_delivery(did, path)
        rows += drows
    return rows, cat_rows, md5, deliveries, superseded, excluded, lane_rank


def run(cfg, catalogue_path, intake_dir, out_dir, dedup_version=None, migration_dir=None):
    version = dedup_version if dedup_version is not None else cfg.get("dedup_version", 1)
    try:
        check_version(version)
    except ValueError as exc:
        raise RelPoolError(str(exc)) from exc
    if version == 2:
        _check_migration_dir(migration_dir, out_dir)
    cat_cfg = cfg["catalogue"]
    rows, cat_rows, md5, deliveries, superseded, excluded, lane_rank = load_rows(
        cfg, catalogue_path, intake_dir)
    stats = {}
    roots = cluster(rows, stats)
    tables = load_tables(cfg.get("enrichment"), ROOT)
    enrich = Enrichment(tables) if tables else None
    pool = build_pool(rows, roots, lane_rank, enrich=enrich)
    if version == 2:
        stats2, pairs = {}, []
        roots2 = cluster(rows, stats2, version=2, pairs=pairs)
        pool2 = build_pool(rows, roots2, lane_rank, version=2)
        return write_migration(rows, (roots, pool, stats), (roots2, pool2, stats2), migration_dir,
                               pairs)
    meta = {"path": os.path.relpath(catalogue_path, ROOT) if os.path.isabs(catalogue_path)
            else catalogue_path, "md5": md5, "rows": len(cat_rows), "run": cat_cfg.get("run")}
    report = make_report(rows, roots, deliveries, excluded, meta, superseded, stats)

    if enrich:
        report["enrichment"] = enrich.report()
    os.makedirs(out_dir, exist_ok=True)
    _write_pool(os.path.join(out_dir, "pool.csv"), pool,
                POOL_COLUMNS + EXTRA_COLUMNS if enrich else POOL_COLUMNS)
    with open(os.path.join(out_dir, "merge_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(os.path.join(out_dir, "merge_report.md"), "w", encoding="utf-8") as fh:
        fh.write(report_markdown(report))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--catalogue", default=None, help="default: config catalogue.path")
    parser.add_argument("--intake-dir", default=None, help="default: config intake_dir")
    # Multi-output: pool.csv, merge_report.json and merge_report.md in one directory.
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dedup-version", type=int, default=None,
                        help="default: config dedup_version, else 1")
    parser.add_argument("--migration-dir", default=None,
                        help="version 2: report and migration table directory, outside the pool")
    args = parser.parse_args(argv)
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    try:
        report = run(cfg, args.catalogue or cfg["catalogue"]["path"],
                     args.intake_dir or cfg["intake_dir"], args.output_dir,
                     args.dedup_version, args.migration_dir)
    except RelPoolError as exc:
        log.error("%s", exc)
        return 1
    if report.get("dedup_version") == 2:
        log.info("dedup v2 (nothing written to the pool): %s", report["totals"])
        return 0
    p = report["pool"]
    log.info("pool: %d works (%d with a catalogue row, %d lane-only); per n_sources %s",
             p["works"], p["in_catalogue"], p["lane_only"], p["works_per_n_sources"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
