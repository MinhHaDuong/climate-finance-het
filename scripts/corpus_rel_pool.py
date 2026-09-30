"""Build the REL pool: pinned catalogue + every lane delivery (ticket 1731).

Reads the pinned merged catalogue (``config/rel_pool.yaml`` → ``catalogue``;
refused unless its md5 and row count match) and every delivery under
``data/rel_intake/<lane>/<delivery>/`` that no other delivery supersedes. Each
delivery is checked against the intake contract (``qa_rel_intake``); one
failing delivery aborts the merge with its violations.

Deduplication is one union-find over all rows, catalogue and lanes alike:

1. same normalized DOI;
2. same OpenAlex id;
3. same normalized title and same year, **unless** the two rows carry
   different DOIs or different OpenAlex ids. A working paper and its article
   with their own DOIs therefore stay two works, and a title never joins
   across years; each row's ``version_hint`` is carried so the counting-unit
   decision (open, ticket 1655) can be applied later.

The union is transitive: a record whose DOI matches one work and whose OpenAlex
id matches another joins the two.

Outputs (``--output-dir``, default ``data/rel_pool``):

- ``pool.csv``: one row per work. ``work_key`` is ``openalex:W…`` when a member
  carries an OpenAlex id, else ``doi:<doi>``, else ``title:<title>|<year>``.
  Metadata come from the first non-empty member: catalogue rows first, then
  lanes in ``lane_order``. Provenance: ``in_catalogue``, ``sources``
  (``catalogue`` then lane ids), ``n_sources``, ``member_record_ids``.
- ``merge_report.json``: per delivery, before cross-source deduplication, the
  fields of the contract's merge-report table; then pool totals, works per
  number of sources and a reconciliation that must add up (the script fails
  otherwise).
- ``merge_report.md``: the same per-delivery table, readable.

Usage:
    python scripts/corpus_rel_pool.py [--config config/rel_pool.yaml] \\
        [--catalogue PATH] [--intake-dir DIR] [--output-dir data/rel_pool]
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict

import qa_rel_intake as ric
import yaml
from utils import get_logger, normalize_doi, normalize_title

log = get_logger("corpus_rel_pool")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "config", "rel_pool.yaml")

OPENALEX_ID = re.compile(r"^W\d+$")
CATALOGUE = "catalogue"

# Pool metadata columns, filled from the first non-empty member.
META_COLUMNS = ["doi", "openalex_id", "title", "first_author", "all_authors",
                "year", "journal", "abstract", "language", "doc_type",
                "affiliation_countries", "affiliations", "cited_by_count"]
POOL_COLUMNS = (["work_key"] + META_COLUMNS
                + ["version_hint", "all_dois", "all_openalex_ids", "in_catalogue",
                   "catalogue_sources", "sources", "n_sources", "member_record_ids"])


class RelPoolError(Exception):
    """A refused input: wrong catalogue, failing delivery, broken reconciliation."""


# ── Identifiers ──────────────────────────────────────────


def norm_year(v):
    """``2026.0`` / ``2026`` → ``2026``; anything else → ``""``."""
    s = str(v or "").strip()
    try:
        y = int(float(s))
    except ValueError:
        return ""
    return str(y) if 1000 <= y <= 2999 else ""


def norm_openalex(v):
    s = str(v or "").strip()
    s = s.rsplit("/", 1)[-1]
    return s.upper() if OPENALEX_ID.match(s.upper()) else ""


def keys_of(row):
    """(doi, openalex_id, title|year) keys of a normalized row; blanks omitted."""
    title = normalize_title(row["title"])
    return (row["doi"], row["openalex_id"],
            f"{title}|{row['year']}" if title and row["year"] else "")


def _compatible(a, b):
    """Two rows may join by title + year only when no identifier disagrees."""
    return not ((a["doi"] and b["doi"] and a["doi"] != b["doi"])
                or (a["openalex_id"] and b["openalex_id"]
                    and a["openalex_id"] != b["openalex_id"]))


class _UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, i, j):
        ri, rj = self.find(i), self.find(j)
        if ri != rj:
            self.parent[max(ri, rj)] = min(ri, rj)


def cluster(rows):
    """Union-find over ``rows``: component root index per row.

    DOI and OpenAlex id join unconditionally; title + year joins a pair of
    rows only when their identifiers are compatible (pairwise, so the result
    does not depend on row order and a subset's joins are a subset of the
    whole's joins).
    """
    uf = _UnionFind(len(rows))
    by_doi, by_oa, by_title = defaultdict(list), defaultdict(list), defaultdict(list)
    for i, r in enumerate(rows):
        doi, oa, ty = keys_of(r)
        if doi:
            by_doi[doi].append(i)
        if oa:
            by_oa[oa].append(i)
        if ty:
            by_title[ty].append(i)
    for group in list(by_doi.values()) + list(by_oa.values()):
        for j in group[1:]:
            uf.union(group[0], j)
    for group in by_title.values():
        for a in range(len(group)):
            for b in range(a + 1, len(group)):
                i, j = group[a], group[b]
                if _compatible(rows[i], rows[j]):
                    uf.union(i, j)
    return [uf.find(i) for i in range(len(rows))]


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
            "doi": normalize_doi(r.get("doi")),
            "openalex_id": norm_openalex(r.get("source_id")),
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
                try:
                    with open(mpath, encoding="utf-8") as fh:
                        manifest = json.load(fh)
                except json.JSONDecodeError:
                    manifest = {}
            found.append((f"{lane}/{delivery}", path, manifest if isinstance(manifest, dict) else {}))
    superseded = set()
    for did, _, manifest in found:
        superseded |= _supersedes(manifest, did.split("/")[0])
    live = [d for d in found if d[0] not in superseded]
    return live, sorted(superseded & {d[0] for d in found})


def check_deliveries(deliveries):
    """Abort on the first delivery that violates the contract, listing its faults."""
    for did, path, _ in deliveries:
        errors = ric.check_delivery(path)
        if errors:
            raise RelPoolError(f"delivery {did} violates the intake contract:\n  "
                               + "\n  ".join(errors))


def load_delivery(did, path):
    rows = []
    for r in _read_csv(os.path.join(path, "records.csv")):
        rows.append({
            "origin": did.split("/")[0], "delivery": did,
            "record_id": f"{did}:{r['record_id']}",
            "doi": normalize_doi(r.get("doi")),
            "openalex_id": norm_openalex(r.get("openalex_id")),
            **{c: r.get(c) or "" for c in ("title", "first_author", "all_authors",
                                            "journal", "abstract", "language", "doc_type",
                                            "affiliation_countries", "version_hint")},
            "year": norm_year(r.get("year")),
            "affiliations": "",
            "cited_by_count": r.get("cited_by_count") or "",
            "catalogue_source": "",
        })
    excluded = Counter(r.get("reason") for r in _read_csv(os.path.join(path, "excluded.csv")))
    return rows, dict(sorted(excluded.items()))


# ── Pool ─────────────────────────────────────────────────


def _work_key(merged):
    if merged["openalex_id"]:
        return f"openalex:{merged['openalex_id']}"
    if merged["doi"]:
        return f"doi:{merged['doi']}"
    return f"title:{normalize_title(merged['title'])}|{merged['year']}"


def build_pool(rows, roots, lane_rank):
    """One pool row per component; members ordered catalogue first, then lanes."""
    members = defaultdict(list)
    for i, root in enumerate(roots):
        members[root].append(i)

    def rank(i):
        r = rows[i]
        return (0 if r["origin"] == CATALOGUE else 1 + lane_rank[r["origin"]], r["delivery"], i)

    pool = []
    for root in sorted(members):
        idx = sorted(members[root], key=rank)
        mem = [rows[i] for i in idx]
        merged = {c: next((m[c] for m in mem if m[c]), "") for c in META_COLUMNS}
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
        merged["work_key"] = _work_key(merged)
        pool.append(merged)
    keys = Counter(p["work_key"] for p in pool)
    dup = [k for k, n in keys.items() if n > 1]
    if dup:
        raise RelPoolError(f"work_key not unique: {dup[:5]}")
    return pool


# ── Report ───────────────────────────────────────────────


def _direct_catalogue_method(row, cat_index):
    """How a lane row matches the catalogue directly, cascade order, or None."""
    doi, oa, ty = keys_of(row)
    if doi and doi in cat_index["doi"]:
        return "by_doi"
    if oa and oa in cat_index["openalex_id"]:
        return "by_openalex_id"
    if ty and any(_compatible(row, c) for c in cat_index["title"].get(ty, [])):
        return "by_title_year"
    return None


def _catalogue_index(rows):
    """Catalogue keys, for naming the method of a direct catalogue match."""
    index = {"doi": set(), "openalex_id": set(), "title": defaultdict(list)}
    for r in rows:
        if r["origin"] != CATALOGUE:
            continue
        doi, oa, ty = keys_of(r)
        if doi:
            index["doi"].add(doi)
        if oa:
            index["openalex_id"].add(oa)
        if ty:
            index["title"][ty].append(r)
    return index


def delivery_counts(did, idx, rows, roots, comp, cat_index):
    """Contract merge-report counts of one delivery, before cross-source dedup.

    The delivery is first deduplicated on its own (same cascade); each of its
    works is then placed by the pool component it landed in: with a catalogue
    row (named by the direct match method, cascade order), with another
    delivery only, or alone.
    """
    drows = [rows[i] for i in idx]
    works = defaultdict(list)
    for k, lroot in enumerate(cluster(drows)):
        works[lroot].append(idx[k])
    in_cat = Counter({"by_doi": 0, "by_openalex_id": 0, "by_title_year": 0, "via_other_lane": 0})
    other_lane_only = new = 0
    for members in works.values():
        full = comp[roots[members[0]]]
        if any(rows[j]["origin"] == CATALOGUE for j in full):
            method = next((m for m in (_direct_catalogue_method(rows[i], cat_index)
                                       for i in members) if m), "via_other_lane")
            in_cat[method] += 1
        elif any(rows[j]["delivery"] != did for j in full):
            other_lane_only += 1
        else:
            new += 1
    return {
        "records": len(drows),
        "with_doi": sum(bool(r["doi"]) for r in drows),
        "with_openalex_id": sum(bool(r["openalex_id"]) for r in drows),
        "title_year_only": sum(not r["doi"] and not r["openalex_id"] for r in drows),
        "dup_within_delivery": len(drows) - len(works),
        "works": len(works),
        "in_catalogue": {"total": sum(in_cat.values()), **dict(in_cat)},
        "in_other_lane_only": other_lane_only,
        "new_to_pool": new,
    }


def make_report(rows, roots, deliveries, excluded, catalogue_meta, superseded):
    """Assemble merge_report.json; raise if the reconciliation does not add up."""
    comp = defaultdict(list)
    for i, root in enumerate(roots):
        comp[root].append(i)
    cat_index = _catalogue_index(rows)
    by_delivery = defaultdict(list)
    for i, r in enumerate(rows):
        if r["origin"] != CATALOGUE:
            by_delivery[r["delivery"]].append(i)

    per = {}
    for did, _, manifest in deliveries:
        counts = delivery_counts(did, by_delivery.get(did, []), rows, roots, comp, cat_index)
        per[did] = {"lane": did.split("/")[0], "coverage": manifest.get("coverage"),
                    "records": counts.pop("records"), "excluded": excluded[did],
                    **counts, "already_screened": None}

    n_cat_rows = sum(r["origin"] == CATALOGUE for r in rows)
    comps_with_cat = [c for c in comp.values() if any(rows[j]["origin"] == CATALOGUE for j in c)]
    lane_only = [c for c in comp.values() if not any(rows[j]["origin"] == CATALOGUE for j in c)]
    multi_delivery_lane_only = sum(len({rows[j]["delivery"] for j in c}) > 1 for c in lane_only)
    n_sources = Counter(len({rows[j]["origin"] for j in c}) for c in comp.values())
    conflicting = sum(len({rows[j]["doi"] for j in c if rows[j]["doi"]}) > 1 for c in comp.values())

    recon = {
        "pool_works": len(comp),
        "catalogue_rows": n_cat_rows,
        "catalogue_works": len(comps_with_cat),
        "catalogue_rows_joined": n_cat_rows - len(comps_with_cat),
        "lane_only_works": len(lane_only),
        "lane_only_works_single_delivery": len(lane_only) - multi_delivery_lane_only,
        "lane_only_works_several_deliveries": multi_delivery_lane_only,
        "works_with_several_dois": conflicting,
    }
    checks = {
        "pool = catalogue works + lane-only works":
            recon["pool_works"] == recon["catalogue_works"] + recon["lane_only_works"],
        "sum of new_to_pool = lane-only works from a single delivery":
            sum(p["new_to_pool"] for p in per.values()) == recon["lane_only_works_single_delivery"],
        "works per n_sources sum to the pool": sum(n_sources.values()) == recon["pool_works"],
    }
    for did, p in per.items():
        checks[f"{did}: records - dup_within_delivery = works"] = (
            p["records"] - p["dup_within_delivery"] == p["works"])
        checks[f"{did}: works = in_catalogue + in_other_lane_only + new_to_pool"] = (
            p["works"] == p["in_catalogue"]["total"] + p["in_other_lane_only"] + p["new_to_pool"])
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise RelPoolError("merge report does not reconcile: " + "; ".join(failed))
    recon["checks"] = {k: "ok" for k in checks}

    return {
        "catalogue": catalogue_meta,
        "deliveries": per,
        "superseded_deliveries": superseded,
        "pool": {
            "works": len(comp),
            "in_catalogue": len(comps_with_cat),
            "lane_only": len(lane_only),
            "works_per_n_sources": {str(k): n_sources[k] for k in sorted(n_sources)},
            "still_to_screen": None,
        },
        "reconciliation": recon,
        "notes": ("Per-delivery counts are before cross-source deduplication. "
                  "in_catalogue.via_other_lane: the delivery's work joins a catalogue work only "
                  "through another lane's record. already_screened and still_to_screen wait for "
                  "the icf_screen table (ticket 1732)."),
    }


def report_markdown(report):
    head = ["delivery", "records", "excluded", "with_doi", "with_openalex_id",
            "title_year_only", "dup_within_delivery", "in_catalogue (doi/oa/title/via lane)",
            "in_other_lane_only", "new_to_pool"]
    lines = ["# REL pool merge report", "",
             f"Catalogue: `{report['catalogue']['path']}`, md5 `{report['catalogue']['md5']}`, "
             f"{report['catalogue']['rows']} rows.", "",
             "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for did, p in report["deliveries"].items():
        c = p["in_catalogue"]
        exc = ", ".join(f"{k} {v}" for k, v in p["excluded"].items()) or "0"
        lines.append("| " + " | ".join(map(str, [
            did, p["records"], exc, p["with_doi"], p["with_openalex_id"], p["title_year_only"],
            p["dup_within_delivery"],
            f"{c['total']} ({c['by_doi']}/{c['by_openalex_id']}/{c['by_title_year']}/{c['via_other_lane']})",
            p["in_other_lane_only"], p["new_to_pool"]])) + " |")
    pool = report["pool"]
    lines += ["", f"Pool: {pool['works']} works ({pool['in_catalogue']} with a catalogue row, "
              f"{pool['lane_only']} from lanes only).",
              "Works per number of sources: "
              + ", ".join(f"{k}: {v}" for k, v in pool["works_per_n_sources"].items()) + ".", ""]
    return "\n".join(lines)


def _write_pool(path, pool):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=POOL_COLUMNS, lineterminator="\n")
        w.writeheader()
        for p in pool:
            w.writerow(p)


def run(cfg, catalogue_path, intake_dir, out_dir):
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
    roots = cluster(rows)
    pool = build_pool(rows, roots, lane_rank)
    meta = {"path": os.path.relpath(catalogue_path, ROOT) if os.path.isabs(catalogue_path)
            else catalogue_path, "md5": md5, "rows": len(cat_rows), "run": cat_cfg.get("run")}
    report = make_report(rows, roots, deliveries, excluded, meta, superseded)

    os.makedirs(out_dir, exist_ok=True)
    _write_pool(os.path.join(out_dir, "pool.csv"), pool)
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
    parser.add_argument("--output-dir", default=os.path.join("data", "rel_pool"))
    args = parser.parse_args(argv)
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    try:
        report = run(cfg, args.catalogue or cfg["catalogue"]["path"],
                     args.intake_dir or cfg["intake_dir"], args.output_dir)
    except RelPoolError as exc:
        log.error("%s", exc)
        return 1
    p = report["pool"]
    log.info("pool: %d works (%d with a catalogue row, %d lane-only); per n_sources %s",
             p["works"], p["in_catalogue"], p["lane_only"], p["works_per_n_sources"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
