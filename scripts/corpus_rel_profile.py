"""Count the REL pool against the minimum metadata profile (ticket 2043, child of 0700).

Read-only: reads a pool table (``pool.csv`` of ``corpus_rel_pool.py``) and,
when given, the OpenAlex backfill (ticket 2041, ``catalog_rel_oa_backfill.py``),
joined by OpenAlex id for the authors and the host organization the pool
merge does not carry yet. Writes ``rel_profile_counts.json`` to ``--output-dir``.
Never writes into ``data/rel_pool``; the pool is not modified and no work is
dropped: this reports what the filter *would* remove.

Reports, in this order:

1. ``fields_available``: for each mandatory property, how many works carry the
   input column that measures it, by lane. A count on a property whose column
   is blank for a lane is a count of the harvest, not of the works.
2. ``before_filter``: works by lane (a work counts in each lane it came from;
   lanes overlap), period (1990-2006, 2007-2014, 2015-2025, other), language
   (blank is its own value, ``unknown``) and document type, with the first act
   and the non-English share stated apart. Printed before any scenario is applied.
3. ``scenarios``: ``six_fields`` (the author decision), ``venue_optional``,
   ``creator_ignored`` (the author column is blank for the OpenAlex lanes) and
   ``creator_ignored_venue_optional``, plus ``venue_missing_any`` (the works that
   lack a venue identity, whatever else they lack) and ``venue_sole_missing`` (the
   works whose only gap is the venue: excluded by ``profile_missing_venue`` alone). Each gives the works it would exclude
   by first failing property (waterfall in ``FIELDS`` order) and by lane,
   period, language and document type, so each count can be compared with
   ``before_filter``.
4. ``venue``: how each work's venue identity resolves (first hit of the configured
   order), what the venue rescues from the old publisher-string rule, the DOI prefixes left
   unresolved (the residue a longer prefix table would reduce), and the DOI-less
   works. ``identifier``: the kinds accepted and the platforms of the
   works lacking one.
5. ``spend_avoided_derived``: excluded works times a per-work model cost quoted
   from the tickets (stage 1: USD 1.10 for 23,110 works, ticket 1733 log;
   stage 2: about USD 5.9 for 34,766 duplicate judgments, same log). Derived,
   not measured.

Usage:
    python scripts/corpus_rel_profile.py --pool POOL.csv [--backfill backfill.jsonl.gz]
        --output-dir DIR
"""

import argparse
import csv
import gzip
import json
import os
import re
import sys
from collections import Counter

import _rel_profile as rp
from utils import get_logger

log = get_logger("corpus_rel_profile")

PERIODS = [("1990-2006", 1990, 2006), ("2007-2014", 2007, 2014), ("2015-2025", 2015, 2025)]
SCENARIOS = {
    "six_fields": [],
    "venue_optional": ["venue"],
    "creator_ignored": ["creator"],
    "creator_ignored_venue_optional": ["creator", "venue"],
    "venue_missing_any": ["identifier", "creator", "title", "publicationYear", "resourceType"],
    "venue_sole_missing": None,  # excluded iff the venue is the only missing property
}
# Per-work model cost, USD, derived from ticket 1733's log (stage 1: 1.10 / 23,110;
# stage 2: 5.9 / 34,766).
COST_STAGE1 = 1.10 / 23110
COST_STAGE2 = 5.9 / 34766
LANG_ALIASES = {"eng": "en", "spa": "es", "fra": "fr", "por": "pt", "deu": "de", "zho": "zh"}


def ratio(num: int, den: int) -> float | None:
    """``num / den`` rounded, or ``None`` (never 0) when the denominator is 0: the share is
    undefined there, e.g. no language known, an empty pool, no first-act work."""
    return round(num / den, 4) if den else None


def period_of(year: str) -> str:
    y = int(year) if re.fullmatch(r"\d{4}", year or "") else 0
    return next((name for name, lo, hi in PERIODS if lo <= y <= hi), "other_years")


def language_of(code: str) -> str:
    c = (code or "").strip().lower().split("-")[0]
    return LANG_ALIASES.get(c, c) or "unknown"


def under_data(path: str) -> bool:
    """True when ``path`` is ``<root>/data`` or inside it, after resolving symlinks and ``..``."""
    data = os.path.realpath(os.path.join(rp.ROOT, "data"))
    out = os.path.realpath(path)
    return out == data or out.startswith(data + os.sep)


def read_backfill(path: str | None) -> dict:
    """``{openalex_id: (first_author, all_authors, host_org_name)}`` from the backfill."""
    out = {}
    if not path or not os.path.exists(path):
        return out
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                out[r["openalex_id"]] = (r.get("first_author") or "",
                                         " ; ".join(r.get("all_authors") or []),
                                         r.get("host_org_name") or "")
    return out


def _dims(row: dict, lanes: list[str]) -> list[tuple]:
    return ([("lane", lane) for lane in lanes] + [("period", period_of(row["year"])),
            ("language", language_of(row["language"])),
            ("doc_type", (row["doc_type"] or "").strip().lower() or "blank")])


def _tally_venue(row: dict, profile: dict, counters: list[Counter]) -> None:
    """Venue tallies of one work: old publisher-string resolution, venue first hit, what the
    venue rescues from the old rule, platform-named journals, the DOI residue."""
    how, venue_how, rescued, repec_available, journal_platform, residue, no_doi = counters
    name, via = rp.publisher_of(row, profile)
    how[via] += 1
    vname, vvia = rp.venue_of(row, profile)
    venue_how[vvia] += 1
    if (row.get("journal") or "").strip() and rp.is_platform_name(row["journal"], profile):
        journal_platform["journal_is_platform_name"] += 1
    if not name:
        if vname:
            rescued[vvia] += 1
        if rp._repec_body(row, profile):
            repec_available["old_unresolved_with_repec_archive"] += 1
    if not vname:
        doi = (row["doi"] or "").strip()
        if doi:
            residue[doi.split("/", 1)[0]] += 1
        else:
            no_doi["no_doi"] += 1


def count(pool_path: str, backfill: dict, profile: dict) -> dict:
    csv.field_size_limit(1 << 30)
    total = Counter()
    by_dim = Counter()
    blank_input = Counter()          # (column, lane) -> works with the column blank
    lane_works = Counter()
    miss_any = Counter()             # (field, dim) -> works missing it
    excl = {s: Counter() for s in SCENARIOS}
    waterfall = {s: Counter() for s in SCENARIOS}
    how = Counter()
    venue_how = Counter()
    rescued = Counter()
    repec_available = Counter()
    journal_platform = Counter()
    residue = Counter()
    no_doi = Counter()
    ident = Counter()
    ident_lost = Counter()
    joined = 0
    with open(pool_path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            oa = (row.get("openalex_id") or "").strip() or (
                (row.get("all_openalex_ids") or "").split(";")[0].strip())
            if oa in backfill:
                joined += 1
                fa, aa, host = backfill[oa]
                row["first_author"] = row.get("first_author") or fa
                row["all_authors"] = row.get("all_authors") or aa
                row["host_org_name"] = row.get("host_org_name") or host
            lanes = [x for x in (row["sources"] or "").split(";") if x] or ["none"]
            dims = _dims(row, lanes)
            total["works"] += 1
            for d in dims:
                by_dim[d] += 1
            for lane in lanes:
                lane_works[lane] += 1
                for col, blank in (("authors", not (row["first_author"] or row["all_authors"])),
                                   ("host_org_name", not row.get("host_org_name")),
                                   ("year", not row["year"]), ("doc_type", not row["doc_type"]),
                                   ("language", not row["language"])):
                    blank_input[(col, lane)] += blank
            miss = rp.missing_fields(row, profile)
            for f in miss:
                for d in dims:
                    miss_any[(f, d)] += 1
            kind = rp.identifier_of(row, profile)
            ident[kind or "none"] += 1
            if not kind:
                ident_lost[tuple(sorted(
                    {(m.split(":", 1)[1] if "/" in m.split(":", 1)[0] else m).split(":")[0]
                     for m in (row["member_record_ids"] or "none").split(";")}))] += 1
            _tally_venue(row, profile, [how, venue_how, rescued, repec_available,
                                        journal_platform, residue, no_doi])
            for scen, ignored in SCENARIOS.items():
                if ignored is None:
                    gone = ["venue"] if miss == ["venue"] and "venue" in profile["required"] else []
                else:
                    gone = [f for f in miss if f in profile["required"] and f not in ignored]
                if gone:
                    waterfall[scen][rp.CODE_PREFIX + gone[0]] += 1
                    excl[scen]["works"] += 1
                    for d in dims:
                        excl[scen][d] += 1
    return {"total": total, "by_dim": by_dim, "blank_input": blank_input, "lane_works": lane_works,
            "miss_any": miss_any, "excl": excl, "waterfall": waterfall, "how": how,
            "residue": residue, "no_doi": no_doi, "venue_how": venue_how, "rescued": rescued,
            "repec_available": repec_available, "journal_platform": journal_platform, "ident": ident, "ident_lost": ident_lost,
            "joined": joined}


def _table(c: Counter, by_dim: Counter, dim: str) -> dict:
    out = {}
    for (d, v), n in sorted(by_dim.items(), key=lambda kv: (-kv[1], str(kv[0]))):
        if d == dim:
            out[v] = {"works": n, "excluded": c.get((d, v), 0),
                      "excluded_share": round(c.get((d, v), 0) / n, 4)}
    return out


def report(m: dict, profile: dict, pool_path: str, backfill_path: str | None, n_backfill: int) -> dict:
    n = m["total"]["works"]
    by = m["by_dim"]

    def share(dim, val):
        return ratio(by[(dim, val)], n)

    known = sum(v for (d, k), v in by.items() if d == "language" and k != "unknown")
    non_en = sum(v for (d, k), v in by.items() if d == "language" and k not in ("unknown", "en"))
    first_act_n = by[("period", "1990-2006")]
    out = {
        "label": "measured on the pool table; derived blocks say so",
        "inputs": {"pool": pool_path, "pool_works": n, "backfill": backfill_path,
                   "backfill_records": n_backfill, "pool_works_joined_to_backfill": m["joined"],
                   "profile_version": profile["version"], "required": profile["required"]},
        "fields_available": {
            "note": ("blank_by_lane[column][lane]: works of the lane whose input column is blank "
                     "(a lane overlaps others). authors is the creator input, host_org_name the "
                     "publisher's first resolution step; doc_type is resourceType, year is "
                     "publicationYear, language is not a profile field."),
            "lane_works": dict(m["lane_works"].most_common()),
            "blank_by_lane": {col: {lane: m["blank_input"][(col, lane)] for lane in m["lane_works"]}
                              for col in ("authors", "host_org_name", "year", "doc_type", "language")}},
        "before_filter": {
            "works": n,
            "by_lane": {k: v for (d, k), v in by.most_common() if d == "lane"},
            "by_period": {k: v for (d, k), v in by.most_common() if d == "period"},
            "by_language": {k: v for (d, k), v in by.most_common() if d == "language"},
            "by_doc_type": {k: v for (d, k), v in by.most_common(60) if d == "doc_type"},
            "first_act_1990_2006": {"works": first_act_n, "share_of_pool": share("period", "1990-2006")},
            "non_english": {"works": non_en, "share_of_known_language": ratio(non_en, known),
                            "share_of_pool": ratio(non_en, n),
                            "language_known_works": known, "language_unknown_works": by[("language", "unknown")],
                            "note": ("language is blank for most OpenAlex-lane works, so the share of known language "
                                     "describes the labelled part only; a share is null when its "
                                     "denominator is 0 (undefined, not zero)")},
        },
        "missing_by_field_works": {f: {d_v: c for (ff, (d, d_v)), c in m["miss_any"].items()
                                       if ff == f and d == "period"} | {"all": sum(
                                           c for (ff, (d, _v)), c in m["miss_any"].items()
                                           if ff == f and d == "period")}
                                   for f in rp.FIELDS},
        "scenarios": {},
        "venue": {"resolved_by_first_hit": dict(m["venue_how"].most_common()),
                  "rescued_from_old_publisher_string_exclusion_by_step": dict(m["rescued"].most_common()),
                  "rescued_total": sum(m["rescued"].values()),
                  "old_publisher_string_unresolved": m["how"]["unresolved"],
                  "old_unresolved_with_a_repec_archive_whatever_the_journal": m["repec_available"][
                      "old_unresolved_with_repec_archive"],
                  "journal_field_is_a_platform_name_ignored": m["journal_platform"][
                      "journal_is_platform_name"],
                  "repec_archive_rows": len(profile["repec_archives"]),
                  "note": ("rescued: works the old rule (host organization, then DOI prefix) left "
                           "unresolved that a venue step now resolves; host_org and doi_prefix "
                           "rescue none by construction. unresolved_* below describe the venue.")},
        "publisher_string": {"resolved_by": dict(m["how"]),
                      "unresolved_with_doi_top_prefixes": dict(m["residue"].most_common(40)),
                      "unresolved_with_doi": sum(m["residue"].values()),
                      "unresolved_without_doi": m["no_doi"]["no_doi"],
                      "prefix_table_rows": len(profile["prefixes"])},
        "identifier": {"by_kind": dict(m["ident"].most_common()),
                       "lacking_one_by_record_id_platform_top": {
                           "+".join(k): v for k, v in m["ident_lost"].most_common(25)}},
    }
    for scen, ignored in SCENARIOS.items():
        e = m["excl"][scen]
        ex = e["works"]
        out["scenarios"][scen] = {
            "required": ([f for f in profile["required"] if f not in ignored] if ignored is not None else ["venue (sole missing property)"]),
            "excluded_works": ex, "excluded_share": ratio(ex, n),
            "kept_works": n - ex,
            "first_failing_property": dict(m["waterfall"][scen].most_common()),
            "by_lane": _table(e, by, "lane"), "by_period": _table(e, by, "period"),
            "by_language": _table(e, by, "language"),
            "by_doc_type": dict(list(_table(e, by, "doc_type").items())[:25]),
            "first_act_kept": by[("period", "1990-2006")] - e[("period", "1990-2006")],
            "first_act_excluded_share": ratio(e[("period", "1990-2006")], first_act_n),
            "non_english_kept": sum(by[("language", k)] - e[("language", k)] for (d, k) in list(by)
                                    if d == "language" and k not in ("unknown", "en")),
            "spend_avoided_derived_usd": {
                "stage1": round(ex * COST_STAGE1, 2), "stage2": round(ex * COST_STAGE2, 2),
                "basis": ("excluded works x USD 1.10/23,110 (stage 1) and USD 5.9/34,766 (stage 2 "
                          "Sol), rates quoted in the ticket 1733 log; an upper bound if some "
                          "excluded works were already screened or would exit at stage 1"),
            },
        }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--backfill", default=None)
    ap.add_argument("--profile-config", default=rp.DEFAULT_CONFIG)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args(argv)
    if under_data(args.output_dir):
        log.error("refusing to write into data/ (DVC-tracked): %s", args.output_dir)
        return 1
    profile = rp.load_profile(args.profile_config)
    backfill = read_backfill(args.backfill)
    res = report(count(args.pool, backfill, profile), profile, args.pool, args.backfill, len(backfill))
    os.makedirs(args.output_dir, exist_ok=True)
    path = os.path.join(args.output_dir, "rel_profile_counts.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    for s, v in res["scenarios"].items():
        log.info("%s: excluded %d of %d", s, v["excluded_works"], res["inputs"]["pool_works"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
