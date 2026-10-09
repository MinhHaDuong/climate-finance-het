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
  ``merge;split``; ``cause`` names the version 2 changes that, each applied
  alone on top of version 1, already make the change: ``title_key`` (the new
  title normalizer), ``repec_handle`` (the RePEc handle key, step 2c),
  ``component_guard`` (steps 3 and 4 judge whole components), ``versions``
  (step 5: lane links, a working paper and its article, duplicate OpenAlex
  records when ``openalex_duplicates`` is on), several joined
  by ``|`` when each alone does it, or ``combined`` when only changes together
  do it. ``inputs_md5``
  fingerprints the rows (their record ids). A rerun appends the rows not
  already present and never rewrites one.
- ``dedup_v2_works.csv``: the works behind every count, one row per
  (category, work).
- ``dedup_v2_version_pairs.csv``: one row per union of step 5 (ticket 2048),
  a lane link, a working paper and its article, or two OpenAlex records, both
  records side by side (``_rel_pool_versions.pair_records``); the precision
  panel samples it.
- ``dedup_v2_report.json`` / ``.md``: counts by category, then by lane, by
  period (1990-2006, 2007-2014, 2015-2025, and outside) and by language, with
  the first act (1990-2006) shown separately. Every count is measured on this
  build; the only derived numbers are under ``derived``, with their arithmetic.

Categories: ``merged`` (a version 2 work gathering two or more version 1
works, by cause), ``versions_merged`` (a version 2 work in which step 5 joined
two or more components of version 2 without step 5; ticket 2048), ``split``, ``rekeyed`` (key changed, no merge or split),
``multi_doi`` and ``multi_openalex`` (version 2 works with two or more DOIs or
OpenAlex ids), ``title_only`` (version 2 works named by their title alone).
A work counts once per lane it draws from: lane counts add up to more than
the total.
"""

import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict

from _rel_pool_dedup import UnionFind, cluster_with
from _rel_pool_versions import (
    PAIR_COLUMNS,
    is_working_paper,
    pair_records,
    published_ids,
    recall_on_known,
)
from _rel_title_key import title_key, title_words
from utils import normalize_title

MIGRATION_FILE = "work_key_migration.csv"
PAIRS_FILE = "dedup_v2_version_pairs.csv"
MIGRATION_COLUMNS = ["from_version", "to_version", "inputs_md5", "old_work_key",
                     "new_work_key", "change", "cause"]
WORK_COLUMNS = ["category", "cause", "work_key", "other_work_keys", "year", "period",
                "language", "sources", "n_dois", "n_openalex_ids", "title"]
PERIODS = [("1990-2006", 1990, 2006), ("2007-2014", 2007, 2014), ("2015-2025", 2015, 2025)]
FIRST_ACT = "1990-2006"
CATEGORIES = ["merged", "versions_merged", "split", "rekeyed", "multi_doi", "multi_openalex",
              "title_only"]


def dois_of(all_dois):
    """The DOIs of an ``all_dois`` cell. The cell joins DOIs with ``;``, and a
    SICI DOI holds one itself (``10.1002/(sici)…co;2-d``): split only before
    a ``10.`` prefix. Splitting on every ``;`` counted 365 multi-DOI works on
    the pool of 2026-10-09, of which 340 carry one SICI DOI (ticket 2048)."""
    return [d for d in re.split(r";(?=10\.)", all_dois or "") if d]


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


def _root_keys(rows, roots, pool):
    """Root index -> work_key. ``build_pool`` emits one work per root in sorted
    root order, and a root is a member row: checked, so a mismatch fails loudly
    instead of mislabelling the migration table."""
    pairs = list(zip(sorted(set(roots)), pool))
    # Substring, not split(";"): a record id may itself contain ";".
    bad = [(rows[root]["record_id"], p["work_key"]) for root, p in pairs
           if rows[root]["record_id"] not in p["member_record_ids"]]
    if len(pairs) != len(pool) or bad:
        raise ValueError(f"pool works are not in sorted root order: {bad[:3]}")
    return {root: p["work_key"] for root, p in pairs}


# Each version 2 change alone on top of version 1:
# (name, normalizer, step 2c, guard, step 5).
CHANGES = [("title_key", title_key, False, False, False),
           ("repec_handle", normalize_title, True, False, False),
           ("component_guard", normalize_title, False, True, False),
           ("versions", normalize_title, False, False, True)]


def _cause(hits):
    """The changes that alone do it, ``|``-joined; ``combined`` if none alone does."""
    return "|".join(name for (name, *_), hit in zip(CHANGES, hits) if hit) or "combined"


def compare(rows, v1, v2, oa_dups=False):
    """Per-work changes from version 1 to version 2 and the migration pairs."""
    (roots1, pool1, _), (roots2, pool2, _) = v1, v2
    k1, k2 = _root_keys(rows, roots1, pool1), _root_keys(rows, roots2, pool2)
    old_rows, new_rows = defaultdict(list), defaultdict(list)
    to_new, to_old = defaultdict(set), defaultdict(set)
    for i in range(len(rows)):
        o, n = k1[roots1[i]], k2[roots2[i]]
        old_rows[o].append(i)
        new_rows[n].append(i)
        to_new[o].add(n)
        to_old[n].add(o)
    # The cascade with one change at a time tells which change does it.
    alone = [cluster_with(rows, None, norm, repec=repec, guard=guard, versions=versions,
                          oa_dups=versions and oa_dups)
             for _, norm, repec, guard, versions in CHANGES]

    def one(idx, roots):
        return len({roots[i] for i in idx}) == 1

    merged = {n: _cause([one(idx, r) for r in alone])
              for n, idx in new_rows.items() if len(to_old[n]) > 1}
    split = {o: _cause([not one(idx, r) for r in alone])
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
            elif n.startswith("repec:"):
                cause = "repec_handle"
            else:  # a rekey without a merge: the article names a work it already was
                cause = "title_key" if n.startswith("title:") else "published_name"
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


def _work_rows(diff, pool1, pool2, by_versions=None):
    """(category, cause, work, other keys) for every counted work.

    ``by_versions``: work_key -> the version 2 works without step 5 it gathers."""
    p1 = {p["work_key"]: p for p in pool1}
    by_versions = by_versions or {}
    out = []
    changed = set(diff["split"])
    for p in pool2:
        k = p["work_key"]
        if k in diff["merged"]:
            out.append(("merged", diff["merged"][k], p, sorted(diff["to_old"][k])))
            changed |= diff["to_old"][k]
        if k in by_versions:
            out.append(("versions_merged", "", p, by_versions[k]))
        if len(dois_of(p["all_dois"])) > 1:
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
    v = report.get("versions")
    if v:
        nb = v["named_by_published"]
        lines += ["", "## Step 5: versions of one work (ticket 2048, measured)", "",
                  f"- works made by step 5: {v['works_made_by_step_5']:,} "
                  f"(from {v['parts_joined_by_step_5']:,} components)",
                  "- works by rule: " + ", ".join(f"{k} {n:,}" for k, n in v["works_by_rule"].items()),
                  "- unions by rule: " + ", ".join(f"{k} {n:,}" for k, n in v["unions_by_rule"].items()),
                  f"- named by the published article: {nb['works']:,} works, "
                  f"{nb['wp_key_rekeyed']:,} where a working paper's version 1 key now points to "
                  f"the article's; version 1 keys not mapped: {nb['unmapped_v1_keys']:,}",
                  "- step counts: " + ", ".join(f"{k} {n:,}" for k, n in
                                                report["stats"]["v2"].get("versions", {}).items())]
        for name, rec in v["recall"].items():
            lines.append(f"- recall on the {rec['works']:,} {name} works of version 2 without "
                         f"step 5: {rec['rejoined']:,} rejoined; missed by reason "
                         + ", ".join(f"{k} {n:,}" for k, n in rec["missed_by_reason"].items()))
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


def _versions(rows, roots1, roots2, pool1, pool2, diff, pairs=None, oa_dups=False):
    """Step 5 (ticket 2048): the version 2 works it makes, by rule, the works
    the published article names, and its recall.

    Recall is measured on the works of version 2 without step 5 that already
    hold two or more DOIs (or OpenAlex ids), joined by a shared record: cut
    into one part per identifier, would step 5 alone rejoin them?

    Works named by the published article: every version 1 key of their rows
    must map to the version 2 key (``unmapped_v1_keys`` counts failures), and
    ``wp_key_rekeyed`` counts those where the key a working paper's version 1
    work had now points to the article's."""
    roots_nv = cluster_with(rows, None, title_key, repec=True, guard=True, versions=False)
    k2 = dict(zip(sorted(set(roots2)), (p["work_key"] for p in pool2)))
    parts = defaultdict(set)
    members = defaultdict(list)
    for i, (r2, rnv) in enumerate(zip(roots2, roots_nv)):
        parts[k2[r2]].add(rnv)
        members[rnv].append(i)
    by_work = {k: sorted(diff["to_old"].get(k, ())) for k, ps in parts.items() if len(ps) > 1}

    def multi(field):
        return [m for m in members.values()
                if len({rows[i][field] for i in m if rows[i][field]}) > 1]

    recall = {name: recall_on_known(rows, multi(field), field, title_key, title_words, UnionFind,
                                    oa_dups=oa_dups)
              for name, field in (("multi_doi", "doi"), ("multi_openalex", "openalex_id"))}
    rules = defaultdict(set)
    for p in pairs or ():
        rules[k2[roots2[p["a_row"]]]].add(p["kind"])
    k1 = dict(zip(sorted(set(roots1)), (p["work_key"] for p in pool1)))
    named, unmapped, wp_rekeyed = 0, 0, 0
    for k, idx in ((k2[r], i) for r, i in _members(roots2).items()):
        if not published_ids([rows[i] for i in idx]):
            continue
        named += 1
        olds = {k1[roots1[i]] for i in idx}
        unmapped += len(olds - diff["to_old"].get(k, set()) - {k})
        wp_rekeyed += any(k1[roots1[i]] != k for i in idx if is_working_paper(rows[i]))
    return {"by_work": by_work, "works_made_by_step_5": len(by_work),
            "parts_joined_by_step_5": sum(len(parts[k]) for k in by_work),
            "works_by_rule": dict(sorted(Counter("+".join(sorted(v)) for v in rules.values())
                                         .items())),
            "unions_by_rule": dict(sorted(Counter(p["kind"] for p in pairs or ()).items())),
            "named_by_published": {"works": named, "wp_key_rekeyed": wp_rekeyed,
                                   "unmapped_v1_keys": unmapped},
            "recall": recall}


def _members(roots):
    out = defaultdict(list)
    for i, r in enumerate(roots):
        out[r].append(i)
    return out


def write_migration(rows, v1, v2, out_dir, pairs=None, oa_dups=False):
    """Write the report, the works list, the migration table and, given the
    step-5 ``pairs``, ``dedup_v2_version_pairs.csv``; return the report."""
    roots1, pool1, stats1 = v1
    roots2, pool2, stats2 = v2
    diff = compare(rows, v1, v2, oa_dups)
    versions = _versions(rows, roots1, roots2, pool1, pool2, diff, pairs, oa_dups)
    inputs_md5 = hashlib.md5("\n".join(sorted(r["record_id"] for r in rows)).encode()).hexdigest()
    os.makedirs(out_dir, exist_ok=True)
    appended = _append_migration(os.path.join(out_dir, MIGRATION_FILE), diff["pairs"], inputs_md5)
    work_rows = _work_rows(diff, pool1, pool2, versions.pop("by_work"))
    if pairs is not None:
        with open(os.path.join(out_dir, PAIRS_FILE), "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=PAIR_COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerows(pair_records(rows, pairs))
    with open(os.path.join(out_dir, "dedup_v2_works.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=WORK_COLUMNS, lineterminator="\n")
        w.writeheader()
        for cat, cause, p, others in work_rows:
            w.writerow({"category": cat, "cause": cause, "work_key": p["work_key"],
                        "other_work_keys": ";".join(others), "year": p["year"],
                        "period": period(p["year"]), "language": p["language"],
                        "sources": p["sources"],
                        "n_dois": len(dois_of(p["all_dois"])),
                        "n_openalex_ids": len([d for d in p["all_openalex_ids"].split(";") if d]),
                        "title": p["title"]})
    counts, first = _counts(work_rows)
    totals = {"rows": len(rows), "works_v1": len(pool1), "works_v2": len(pool2),
              "migration_pairs": len(diff["pairs"]), "migration_rows_appended": appended,
              **{cat: counts[cat]["total"] for cat in CATEGORIES},
              "merged_v1_works": sum(len(diff["to_old"][k]) for k in diff["merged"]),
              "multi_doi_v1": sum(len(dois_of(p["all_dois"])) > 1 for p in pool1),
              "multi_openalex_v1": sum(len(p["all_openalex_ids"].split(";")) > 1 for p in pool1),
              "title_only_v1": sum(p["work_key"].startswith("title:") for p in pool1)}
    report = {
        "dedup_version": 2, "inputs_md5": inputs_md5, "openalex_duplicates": oa_dups,
        "totals": totals,
        "derived": {"works_removed": f"works_v1 - works_v2 = {len(pool1)} - {len(pool2)} "
                                     f"= {len(pool1) - len(pool2)}"},
        "stats": {"v1": stats1, "v2": stats2},
        "counts": counts, "first_act": first, "versions": versions,
    }
    with open(os.path.join(out_dir, "dedup_v2_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(os.path.join(out_dir, "dedup_v2_report.md"), "w", encoding="utf-8") as fh:
        fh.write(_markdown(report))
    return report
