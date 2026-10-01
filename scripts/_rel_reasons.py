"""REL exclusions by reason: ICF, discipline, seriousness (ticket 1843, tracker 1830).

Pure functions over the REL view rows (``_rel_view.build_view``), the
``rel_dimensions`` rows (ticket 1840/1842) and the per-work venue table
(``_rel_venues.load_work_venues``, ticket 1841). ``corpus_rel_view.py`` does
the I/O.

**One reason per work, first that applies, in this fixed order:**

1. ICF: ``icf_excluded`` (the ICF status leaves REL: ``stage1_out``, ``aux``,
   ``out``, ``unsure_unresolved`` when the rule drops it) or ``icf_pending``
   (``unscreened``, ``pending_stage2``);
2. discipline: ``discipline_excluded`` (contribution test ``contrib`` = ``no``)
   or ``discipline_pending`` (no dimension row yet: the catch-up of ticket 1842
   has not reached the work). ``unsure``, and ``na``/``unknown`` answers given
   to an ICF-included work, stay in, flagged (``discipline_flag``), recall
   first like the ICF ``unsure``;
3. seriousness: ``seriousness_excluded``, by a registry exclusion (switch (a),
   ISSN or domain matches only, never a title match), then by tier C (tier
   under switch (b); tiers kept: A and B). Tier ``unknown`` (no resolvable
   venue) follows switch (c), ``no_venue``: kept and flagged (``seriousness_flag``) by
   default, ``tier_unknown`` exclusion otherwise, never tier C;
4. ``included``.

A later dimension is still recorded on the row (``contrib``, ``seriousness``)
but never counted once an earlier reason applies.

**Which dimension row wins** (several runs per work): the row with the key of
the work's deciding stage-2 ICF label (same model and run: the forward
version-2 answer, given with the ICF label it sits beside); otherwise the
last ``catchup`` row in table order (ticket 1842; the table is append-only,
so the order is the order of the runs). Stage-2 rows of a superseded run and
``audit`` rows are not used, and counted (``dimension_rows_unused``).

**Families** (version_hint links, ``family_id`` of the view): a family counts
once and takes the most favourable reason of its members, in the order
``FAMILY_RANK`` (included, then the two pending reasons, then exclusions by the
latest stage reached); among members with that reason, a published article
first, then the earliest year, then the smallest ``work_key``. So every
dimension, seriousness included, is judged on any member: a family is in REL
when one member passes all three, and its representative (``rel_family_id``)
is then an included member, the article first.
"""

import re
from collections import Counter, defaultdict

import _rel_venues as rvn
import _rel_view as rv

REASONS = ["icf_excluded", "icf_pending", "discipline_excluded", "discipline_pending",
           "seriousness_excluded", "included"]
FAMILY_RANK = {"included": 0, "discipline_pending": 1, "icf_pending": 2,
               "seriousness_excluded": 3, "discipline_excluded": 4, "icf_excluded": 5}
ICF_PENDING = {"unscreened", "pending_stage2"}
PUBLISHERS = ["mdpi", "frontiers", "hindawi"]
WIDE_REGISTRIES = ["doaj_withdrawn", "scopus_discontinued"]
VIEW_COLUMNS = ["contrib", "discipline_field", "contrib_type", "discipline_source",
                "discipline_run_id", "discipline_flag", "venue_key", "tier", "publisher_flag",
                "seriousness", "seriousness_flag", "rel_reason", "rel_reason_detail", "rel_final",
                "rel_family_id"]
DISCIPLINE_NOTE = (
    "discipline_excluded leans toward over-excluding applied finance: on the 1840 gold "
    "set, Opus v2 excluded 4 of 59 gold includes, 3 of them applied finance with a "
    "policy question (W3122424672, W4399863925, W7212372846), against 3 extra includes "
    "(ticket 1843 note, PR 1652). Read this count as an upper bound on the discipline "
    "exclusions of applied finance.")

_FLAG = re.compile(r"^([^:]+):(.*)\[(\w+)\]$")


def parse_flags(text: str) -> list[dict]:
    """``registry:entry_id[match]`` cells (``_rel_venues.flags_text``) as dicts."""
    out = []
    for part in filter(None, (text or "").split(";")):
        m = _FLAG.match(part)
        if not m:
            raise ValueError(f"unreadable venue flag {part!r}")
        out.append({"registry": m.group(1), "entry_id": m.group(2), "match": m.group(3)})
    return out


def seriousness_rule(registries_cfg: dict, tiers_cfg: dict) -> dict:
    """Switches (a), (b) and (c) as configured (all pending author decisions)."""
    return {"exclude": rvn.exclusion_registries(registries_cfg),
            "ngo_research_in_b": rvn.ngo_switch(tiers_cfg),
            "no_venue": rvn.unknown_switch(tiers_cfg),
            "tiers": ["A", "B"], "drop_publishers": []}


def seriousness_of(venue: dict, srule: dict) -> str:
    """``""`` (passes), ``registry:<r>``, ``tier_c``, ``tier_unknown`` or ``publisher:<p>``.

    Tier ``unknown`` (no resolvable venue, ticket 1841) passes under switch (c)
    ``no_venue`` = ``keep_flagged`` and is flagged on the row (``seriousness_flag``); under
    ``exclude`` it is a seriousness exclusion of its own, never tier C.
    """
    excl = sorted({f["registry"] for f in parse_flags(venue["flags"]) if f["match"] != "title"}
                  & set(srule["exclude"]))
    if excl:
        return "registry:" + excl[0]
    tier = venue["tier_ngo_in_b"] if srule["ngo_research_in_b"] else venue["tier_ngo_not_b"]
    if tier == "unknown":
        if srule["no_venue"] == "exclude":
            return "tier_unknown"
    elif tier not in srule["tiers"]:
        return "tier_c"
    if venue.get("publisher_flag") in srule["drop_publishers"]:
        return "publisher:" + venue["publisher_flag"]
    return ""


def _match_dimensions(pool: list[dict], dims: list[dict]) -> dict:
    """``{pool index: [dimension rows, table order]}`` via ``_rel_view.match_labels``."""
    keyed = []
    for d in dims:
        wk = d["work_key"]
        keyed.append(dict(d, openalex_id=wk[len("openalex:"):] if wk.startswith("openalex:")
                          else "", doi=wk[len("doi:"):] if wk.startswith("doi:") else ""))
    matched, _, _ = rv.match_labels(pool, keyed)
    return matched


def discipline_of(row: dict, dims: list[dict]) -> tuple[dict | None, int, bool]:
    """The winning dimension row of one work (module docstring), the unused rows,
    and whether the candidate rows of the winning kind disagree on ``contrib``
    (two keys of one work answered in one run, or two catch-up runs): the last
    one still wins, and the disagreement is counted, never hidden."""
    if not dims:
        return None, 0, False
    forward = [d for d in dims if d["stage"] == "2" and row["stage2_run_id"]
               and (d["model"], d["run_id"]) == (row["stage2_model"], row["stage2_run_id"])]
    catchup = [d for d in dims if d["stage"] == "catchup"]
    pool = forward or catchup
    win = pool[-1] if pool else None
    return win, len(dims) - (win is not None), len({d["contrib"] for d in pool}) > 1


def _reason(row: dict) -> tuple[str, str]:
    if row["rel_included"] != "true":
        return ("icf_pending" if row["status"] in ICF_PENDING else "icf_excluded"), row["status"]
    if not row["discipline_source"]:
        return "discipline_pending", ""
    if row["contrib"] == "no":
        return "discipline_excluded", row["discipline_field"]
    if row["seriousness"]:
        return "seriousness_excluded", row["seriousness"]
    return "included", ""


def assign(rows: list[dict], pool: list[dict], dims: list[dict], venues: dict,
           srule: dict) -> dict:
    """Add ``VIEW_COLUMNS`` to the view rows (pool order, as ``build_view`` returns
    them); return a summary. A pool work missing from ``venues`` is refused: the
    venue table is stale (``make rel-venues``).
    """
    missing = [r["work_key"] for r in rows if r["work_key"] not in venues]
    if missing:
        raise ValueError(f"{len(missing)} pool works have no row in the venue table "
                         f"(first: {missing[0]}): rebuild it with `make rel-venues`")
    by_work = _match_dimensions(pool, dims)
    unused = conflicts = 0
    for i, row in enumerate(rows):
        win, n_unused, disagree = discipline_of(row, by_work.get(i, []))
        unused += n_unused
        conflicts += disagree
        contrib = win["contrib"] if win else ""
        venue = venues[row["work_key"]]
        row.update({
            "pool_doc_type": pool[i]["doc_type"],
            "contrib": contrib, "discipline_field": win["field"] if win else "",
            "contrib_type": win["contrib_type"] if win else "",
            "discipline_source": ("stage2" if win["stage"] == "2" else win["stage"]) if win else "",
            "discipline_run_id": win["run_id"] if win else "",
            "discipline_flag": contrib if contrib in ("unsure", "na", "unknown") else "",
            "venue_key": venue.get("venue_key", ""),
            "tier": venue["tier_ngo_in_b"] if srule["ngo_research_in_b"] else venue["tier_ngo_not_b"],
            "publisher_flag": venue.get("publisher_flag", ""),
            "seriousness": seriousness_of(venue, srule),
        })
        # Flag only an unknown-venue work that switch (c) keeps.
        row["seriousness_flag"] = ("no_venue" if row["tier"] == "unknown"
                                   and not row["seriousness"] else "")
        row["rel_reason"], row["rel_reason_detail"] = _reason(row)
        row["rel_final"] = "true" if row["rel_reason"] == "included" else "false"
    assign_families(rows)
    return {"dimension_rows": len(dims),
            "dimension_rows_matched": sum(len(v) for v in by_work.values()),
            "dimension_rows_unused": unused,
            "works_with_disagreeing_dimension_rows": conflicts}


def assign_families(rows: list[dict]) -> None:
    """``rel_family_id``: the representative of each family under ``FAMILY_RANK``."""
    groups = defaultdict(list)
    for row in rows:
        groups[row["family_id"]].append(row)
    for members in groups.values():
        rep = min(members, key=lambda r: (FAMILY_RANK[r["rel_reason"]],
                                          not rv._is_article(r["pool_doc_type"]),
                                          r["year"] or "9999", r["work_key"]))
        for r in members:
            r["rel_family_id"] = rep["work_key"]


def _split(rows, key):
    return dict(sorted(Counter(r[key] for r in rows).items()))


def reason_counts(rows: list[dict]) -> dict:
    """Counts by reason, in works and in families (one per ``rel_family_id``).

    Every other count is in works (``*_works``): ``rel_final`` is per work, so
    a working paper and its article, both included, are two works and one
    family.
    """
    reps = {r["rel_family_id"] for r in rows}
    fam_rows = [r for r in rows if r["work_key"] in reps]
    by = defaultdict(list)
    for r in rows:
        by[r["rel_reason"]].append(r)
    pending = by["discipline_pending"]
    included = by["included"]
    return {
        "works": {k: len(by[k]) for k in REASONS},
        "families": {k: sum(r["rel_reason"] == k for r in fam_rows) for k in REASONS},
        "icf_excluded_by_status": _split(by["icf_excluded"], "rel_reason_detail"),
        "icf_pending_by_status": _split(by["icf_pending"], "rel_reason_detail"),
        "discipline_excluded_by_field": _split(by["discipline_excluded"], "discipline_field"),
        "discipline_excluded_by_source": _split(by["discipline_excluded"], "discipline_source"),
        "discipline_pending_by_seriousness": dict(sorted(Counter(
            (r["seriousness"].split(":")[0] or "pass") for r in pending).items())),
        "discipline_pending_no_venue_flagged_works": sum(
            r["seriousness_flag"] == "no_venue" for r in pending),
        "seriousness_excluded_by_detail": _split(by["seriousness_excluded"],
                                                 "rel_reason_detail"),
        "included_by_tier_works": _split(included, "tier"),
        "included_by_publisher_flag_works": dict(sorted(Counter(
            r["publisher_flag"] for r in included if r["publisher_flag"]).items())),
        "included_discipline_flagged_works": _split(
            [r for r in included if r["discipline_flag"]], "discipline_flag"),
        "included_icf_unsure_flagged_works": sum(r["rel_flag"] == "unsure" for r in included),
        "included_no_venue_flagged_works": sum(r["seriousness_flag"] == "no_venue"
                                              for r in included),
    }


def _scenarios(base: dict) -> list[tuple[str, dict]]:
    out = [("default", base),
           ("publishers_dropped", dict(base, drop_publishers=PUBLISHERS))]
    out += [(f"drop_{p}", dict(base, drop_publishers=[p])) for p in PUBLISHERS]
    kanal = set(base["exclude"]) ^ {"kanalregisteret"}
    out += [("tier_a_only", dict(base, tiers=["A"])),
            ("kanalregisteret_flipped", dict(base, exclude=sorted(kanal))),
            ("registries_plus_scopus_doaj",
             dict(base, exclude=sorted(set(base["exclude"]) | set(WIDE_REGISTRIES)))),
            ("ngo_research_flipped", dict(base, ngo_research_in_b=not base["ngo_research_in_b"])),
            ("no_venue_flipped", dict(base, no_venue="keep_flagged"
                                      if base["no_venue"] == "exclude" else "exclude"))]
    return out


def sensitivity(rows: list[dict], venues: dict, base: dict) -> list[dict]:
    """REL included set under each seriousness setting (ICF and discipline fixed).

    Works and families (family groups of the view: a family is in when any
    member is). Under switch (c) ``keep_flagged``, ``tier_a_only`` still keeps
    the works of tier ``unknown`` (their tier is not known to be B or C); the
    ``no_venue_flipped`` row shows them excluded. ``discipline_pending_*``: works still awaiting the discipline
    test whose venue passes the setting, the provisional upper bound.
    """
    out = []
    for name, srule in _scenarios(base):
        inc, pend = [], []
        for r in rows:
            if r["rel_reason"] in ("included", "seriousness_excluded"):
                if not seriousness_of(venues[r["work_key"]], srule):
                    inc.append(r)
            elif r["rel_reason"] == "discipline_pending":
                if not seriousness_of(venues[r["work_key"]], srule):
                    pend.append(r)
        out.append({
            "scenario": name,
            "exclude_registries": ";".join(srule["exclude"]),
            "tiers": "+".join(srule["tiers"]),
            "ngo_research_in_b": str(srule["ngo_research_in_b"]).lower(),
            "drop_publishers": ";".join(srule["drop_publishers"]),
            "no_venue": srule["no_venue"],
            "included_works": len(inc),
            "included_families": len({r["family_id"] for r in inc}),
            "discipline_pending_works": len(pend),
            "discipline_pending_families": len({r["family_id"] for r in pend}),
        })
    return out
