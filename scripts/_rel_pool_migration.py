"""What pool dedup version 2 would change, written beside the pool (ticket 2047).

``corpus_rel_pool --dedup-version 2`` builds the pool of both versions on the
same rows (``_rel_pool_dedup``) and passes them here. Nothing is written in
the pool directory and no label table is read or written: version 1 stays the
pool until ticket 2048 switches it and migrates the labels.

Files written in the migration directory:

- ``work_key_migration.csv``, **append-only**: one row per pair
  ``old_work_key -> new_work_key`` of a version 1 work whose key changes, or
  that version 2 splits. ``change`` is ``rekey``, ``merge`` (several old
  works become one), ``split`` (one old work becomes several) or
  ``merge;split``; ``cause`` is ``title_key`` (the new title normalizer),
  ``repec_handle`` (the RePEc handle key), ``title_key|repec_handle`` (either
  alone does it) or ``combined`` (only the two together). ``inputs_md5``
  fingerprints the rows (their record ids). A rerun appends the rows not
  already present and never rewrites one.
- ``dedup_v2_works.csv``: the works behind every count, one row per
  (category, work).
- ``dedup_v2_report.json`` / ``.md``: counts by category, then by lane, by
  period (1990-2006, 2007-2014, 2015-2025, and outside) and by language, with
  the first act (1990-2006) shown separately. Every count is measured on this
  build; the only derived numbers are under ``derived``, with their arithmetic.

Categories: ``merged`` (a version 2 work gathering two or more version 1
works, by cause), ``split``, ``rekeyed`` (key changed, no merge or split),
``multi_doi`` and ``multi_openalex`` (version 2 works with two or more DOIs or
OpenAlex ids), ``title_only`` (version 2 works named by their title alone).
A work counts once per lane it draws from: lane counts add up to more than
the total.
"""

import csv
import hashlib
import json
import os
from collections import Counter, defaultdict

from _rel_pool_dedup import cluster_with
from _rel_title_key import title_key
from utils import normalize_title

MIGRATION_FILE = "work_key_migration.csv"
MIGRATION_COLUMNS = ["from_version", "to_version", "inputs_md5", "old_work_key",
                     "new_work_key", "change", "cause"]
WORK_COLUMNS = ["category", "cause", "work_key", "other_work_keys", "year", "period",
                "language", "sources", "n_dois", "n_openalex_ids", "title"]
PERIODS = [("1990-2006", 1990, 2006), ("2007-2014", 2007, 2014), ("2015-2025", 2015, 2025)]
FIRST_ACT = "1990-2006"
CATEGORIES = ["merged", "split", "rekeyed", "multi_doi", "multi_openalex", "title_only"]


def period(year):
    """The act of a year: ``1990-2006``, ``2007-2014``, ``2015-2025``, else outside."""
    try:
        y = int(year)
    except (TypeError, ValueError):
        return "no year"
    for name, lo, hi in PERIODS:
        if lo <= y <= hi:
            return name
    return "before 1990" if y < 1990 else "after 2025"


def _root_keys(roots, pool):
    """Root index -> work_key; ``build_pool`` emits one work per root, roots sorted."""
    return dict(zip(sorted(set(roots)), (p["work_key"] for p in pool)))


def _cause(joined_by_title, joined_by_repec):
    if joined_by_title and joined_by_repec:
        return "title_key|repec_handle"
    if joined_by_title:
        return "title_key"
    if joined_by_repec:
        return "repec_handle"
    return "combined"


def compare(rows, v1, v2):
    """Per-work changes from version 1 to version 2 and the migration pairs."""
    (roots1, pool1, _), (roots2, pool2, _) = v1, v2
    k1, k2 = _root_keys(roots1, pool1), _root_keys(roots2, pool2)
    old_rows, new_rows = defaultdict(list), defaultdict(list)
    to_new, to_old = defaultdict(set), defaultdict(set)
    for i in range(len(rows)):
        o, n = k1[roots1[i]], k2[roots2[i]]
        old_rows[o].append(i)
        new_rows[n].append(i)
        to_new[o].add(n)
        to_old[n].add(o)
    # The cascade with one change at a time tells which change does it.
    by_title = cluster_with(rows, None, title_key, repec=False)
    by_repec = cluster_with(rows, None, normalize_title, repec=True)

    def one(idx, roots):
        return len({roots[i] for i in idx}) == 1

    merged = {n: _cause(one(idx, by_title), one(idx, by_repec))
              for n, idx in new_rows.items() if len(to_old[n]) > 1}
    split = {o: _cause(not one(idx, by_title), not one(idx, by_repec))
             for o, idx in old_rows.items() if len(to_new[o]) > 1}
    pairs = []
    for o in sorted(to_new):
        for n in sorted(to_new[o]):
            change = ";".join(c for c, hit in (("merge", n in merged), ("split", o in split)) if hit)
            if o == n and not change:
                continue
            if change == "merge":
                cause = merged[n]
            elif change:
                cause = split[o] if change == "split" else f"{merged[n]};{split[o]}"
            else:
                cause = "repec_handle" if n.startswith("repec:") else "title_key"
            pairs.append({"old_work_key": o, "new_work_key": n,
                          "change": change or "rekey", "cause": cause})
    return {"merged": merged, "split": split, "pairs": pairs, "to_old": to_old, "to_new": to_new}


def _append_migration(path, pairs, inputs_md5):
    """Append the pairs not yet in the table; refuse a table of another shape."""
    seen = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames != MIGRATION_COLUMNS:
                raise ValueError(f"{path}: columns {reader.fieldnames}, expected {MIGRATION_COLUMNS}")
            seen = {tuple(r[c] for c in MIGRATION_COLUMNS) for r in reader}
    new = [{"from_version": "1", "to_version": "2", "inputs_md5": inputs_md5, **p}
           for p in pairs]
    new = [r for r in new if tuple(r[c] for c in MIGRATION_COLUMNS) not in seen]
    header = not os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=MIGRATION_COLUMNS, lineterminator="\n")
        if header:
            w.writeheader()
        w.writerows(new)
    return len(new)


def _work_rows(diff, pool1, pool2):
    """(category, cause, work, other keys) for every counted work."""
    p1 = {p["work_key"]: p for p in pool1}
    out = []
    changed = set(diff["split"])
    for p in pool2:
        k = p["work_key"]
        if k in diff["merged"]:
            out.append(("merged", diff["merged"][k], p, sorted(diff["to_old"][k])))
            changed |= diff["to_old"][k]
        if len(p["all_dois"].split(";")) > 1:
            out.append(("multi_doi", "", p, []))
        if len(p["all_openalex_ids"].split(";")) > 1:
            out.append(("multi_openalex", "", p, []))
        if k.startswith("title:"):
            out.append(("title_only", "", p, []))
    for o, cause in diff["split"].items():
        out.append(("split", cause, p1[o], sorted(diff["to_new"][o])))
    for pr in diff["pairs"]:
        if pr["change"] == "rekey" and pr["old_work_key"] not in changed:
            out.append(("rekeyed", pr["cause"], p1[pr["old_work_key"]], [pr["new_work_key"]]))
    return out


def _counts(work_rows):
    """Measured counts by category: total, cause, lane, period, language, first act."""
    c = {cat: {"total": 0, "by_cause": Counter(), "by_lane": Counter(), "by_period": Counter(),
               "by_language": Counter()} for cat in CATEGORIES}
    first = {cat: {"total": 0, "by_lane": Counter(), "by_language": Counter()} for cat in CATEGORIES}
    for cat, cause, p, _ in work_rows:
        per, lang, lanes = period(p["year"]), p["language"] or "unknown", p["sources"].split(";")
        c[cat]["total"] += 1
        if cause:
            c[cat]["by_cause"][cause] += 1
        c[cat]["by_period"][per] += 1
        c[cat]["by_language"][lang] += 1
        for lane in lanes:
            c[cat]["by_lane"][lane] += 1
        if per == FIRST_ACT:
            first[cat]["total"] += 1
            first[cat]["by_language"][lang] += 1
            for lane in lanes:
                first[cat]["by_lane"][lane] += 1

    def plain(d):
        return {k: dict(sorted(v.items())) if isinstance(v, Counter) else v for k, v in d.items()}
    return ({cat: plain(v) for cat, v in c.items()}, {cat: plain(v) for cat, v in first.items()})


def _markdown(report):
    lines = ["# REL pool dedup version 2: what would change (ticket 2047)", "",
             "Nothing in the pool or any label table was written. Counts are measured on",
             "this build; derived numbers carry their arithmetic. A work counts once per",
             "lane it draws from.", "", "## Totals (measured)", ""]
    lines += [f"- {k}: {v:,}" for k, v in report["totals"].items()]
    lines += ["", "## Derived", ""] + [f"- {k}: {v}" for k, v in report["derived"].items()]
    for title, block in (("All periods", report["counts"]), ("First act, 1990-2006", report["first_act"])):
        lines += ["", f"## {title}", ""]
        for cat in CATEGORIES:
            b = block[cat]
            lines += [f"### {cat}: {b['total']:,}", ""]
            for axis in ("by_cause", "by_period", "by_lane", "by_language"):
                if b.get(axis):
                    lines.append(f"- {axis[3:]}: " + ", ".join(f"{k} {v:,}" for k, v in b[axis].items()))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_migration(rows, v1, v2, out_dir):
    """Write the report, the works list and the migration table; return the report."""
    roots1, pool1, stats1 = v1
    roots2, pool2, stats2 = v2
    diff = compare(rows, v1, v2)
    inputs_md5 = hashlib.md5("\n".join(sorted(r["record_id"] for r in rows)).encode()).hexdigest()
    os.makedirs(out_dir, exist_ok=True)
    appended = _append_migration(os.path.join(out_dir, MIGRATION_FILE), diff["pairs"], inputs_md5)
    work_rows = _work_rows(diff, pool1, pool2)
    with open(os.path.join(out_dir, "dedup_v2_works.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=WORK_COLUMNS, lineterminator="\n")
        w.writeheader()
        for cat, cause, p, others in work_rows:
            w.writerow({"category": cat, "cause": cause, "work_key": p["work_key"],
                        "other_work_keys": ";".join(others), "year": p["year"],
                        "period": period(p["year"]), "language": p["language"],
                        "sources": p["sources"],
                        "n_dois": len([d for d in p["all_dois"].split(";") if d]),
                        "n_openalex_ids": len([d for d in p["all_openalex_ids"].split(";") if d]),
                        "title": p["title"]})
    counts, first = _counts(work_rows)
    totals = {"rows": len(rows), "works_v1": len(pool1), "works_v2": len(pool2),
              "migration_pairs": len(diff["pairs"]), "migration_rows_appended": appended,
              **{cat: counts[cat]["total"] for cat in CATEGORIES},
              "merged_v1_works": sum(len(diff["to_old"][k]) for k in diff["merged"]),
              "multi_doi_v1": sum(len(p["all_dois"].split(";")) > 1 for p in pool1),
              "multi_openalex_v1": sum(len(p["all_openalex_ids"].split(";")) > 1 for p in pool1),
              "title_only_v1": sum(p["work_key"].startswith("title:") for p in pool1)}
    report = {
        "dedup_version": 2, "inputs_md5": inputs_md5, "totals": totals,
        "derived": {"works_removed": f"works_v1 - works_v2 = {len(pool1)} - {len(pool2)} "
                                     f"= {len(pool1) - len(pool2)}"},
        "stats": {"v1": stats1, "v2": stats2},
        "counts": counts, "first_act": first,
    }
    with open(os.path.join(out_dir, "dedup_v2_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(os.path.join(out_dir, "dedup_v2_report.md"), "w", encoding="utf-8") as fh:
        fh.write(_markdown(report))
    return report
