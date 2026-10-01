"""REL membership and exclusion reasons: a fuzzy set cut at alpha (ticket 1843, tracker 1830).

Pure functions over the REL view rows (``_rel_view.build_view``), the
``rel_dimensions`` rows (tickets 1840, 1842) and the per-work venue table
(``_rel_venues.load_work_venues``, ticket 1841). ``corpus_rel_view.py`` does
the I/O.

**Model** (author framing of 2026-10-01). REL is a fuzzy set, the
intersection of fuzzy facets. A work's membership ``mu`` is the minimum of its
facet values. Facets are evaluated in ``FACETS`` order, cheapest first:

1. ``seriousness`` (deterministic, free: the venue table). Values per tier
   from ``_rel_venues.tier_membership`` (decided: A 1, B 1, unknown 0.5, C 0);
   0 for a registry exclusion (switch (a), never on a title match) and, in the
   sensitivity rows, for a dropped publisher; tier ``unknown`` is 0 under switch
   (c) ``exclude``, never C;
2. ``icf`` (stage-1 model, then Opus): by the work's ICF status, values in
   ``config/rel_screen.yaml`` ``membership.icf`` (proposed: icf 1, unsure 0.5,
   aux and out 0); ``unscreened`` and ``pending_stage2`` are not graded yet.
   Planned (pending): ICF = min(international, climate, finance), three
   facets in place of this one; the list form of ``FACETS`` takes them as is;
3. ``discipline`` (Opus v2 or the 1842 catch-up): the contribution test,
   ``membership.discipline`` (proposed: yes 1, unsure 0.5, no 0; ``na`` and
   ``unknown`` as unsure). Not graded while no dimension row exists.

Evaluation stops at the first facet worth 0 (later facets need not be
graded), or at the first facet not graded yet. ``mu`` is the minimum over the
facets evaluated; ``mu_complete`` says whether it is final (a 0, or every
facet graded). The crisp REL set is the alpha-cut ``mu >= alpha``
(``_rel_venues.alpha``, decided 0.5).

**Reason**: ``<facet>_excluded`` for the first facet, in evaluation order, that
attains ``mu`` when ``mu < alpha``; else ``<facet>_pending`` for the first facet
not graded; else ``included``. ``mu_facet`` names the facet attaining ``mu``.

**Which dimension row wins** (several runs per work): the row with the model
and run of the work's deciding stage-2 ICF label (the forward version-2
answer, given beside the ICF label); otherwise the last ``catchup`` row in
table order (ticket 1842; the table is append-only). Stage-2 rows of a
superseded run and ``audit`` rows are not used, and counted.

**Families** (version_hint links, ``family_id`` of the view): a family is the
union of its versions, so its membership is the maximum over its members.
This is how the decided rule "a family counts once, the article preferred" is
realised: the representative (``rel_family_id``) is the member attaining that
maximum, the published article first, then the earliest year, then the
smallest ``work_key``; when no member is final, the member furthest along the
evaluation stands for the family (pending before excluded, a later facet
before an earlier one).
"""

import re
from collections import Counter, defaultdict

import _rel_venues as rvn
import _rel_view as rv

FACETS = ["seriousness", "icf", "discipline"]  # evaluation order, cheapest first
REASONS = [f"{f}_{k}" for f in FACETS for k in ("excluded", "pending")] + ["included"]
ICF_STATUS = {"icf": "icf", "unsure_unresolved": "unsure", "aux": "aux", "out": "out",
              "stage1_out": "out", "stage1_aux": "aux"}
ICF_PENDING = {"unscreened", "pending_stage2"}
DISCIPLINE_AS_UNSURE = {"na", "unknown"}
PUBLISHERS = ["mdpi", "frontiers", "hindawi"]
WIDE_REGISTRIES = ["doaj_withdrawn", "scopus_discontinued"]
VIEW_COLUMNS = ["contrib", "discipline_field", "contrib_type", "discipline_source",
                "discipline_run_id", "discipline_flag", "venue_key", "tier", "publisher_flag",
                "seriousness", "seriousness_flag", *[f"mu_{f}" for f in FACETS],
                "mu", "mu_facet", "mu_complete", "rel_reason", "rel_reason_detail",
                "rel_final", "rel_family_id"]
DISCIPLINE_NOTE = (
    "discipline_excluded leans toward over-excluding applied finance: on the 1840 gold "
    "set, Opus v2 excluded 4 of 59 gold includes, 3 of them applied finance with a "
    "policy question (W3122424672, W4399863925, W7212372846), against 3 extra includes "
    "(ticket 1843 note, PR 1652). Read this count as an upper bound on the discipline "
    "exclusions of applied finance.")
SERIOUSNESS_NOTE = (
    "seriousness_excluded is overstated: some journal articles reachable only through "
    "aggregators (DOAJ, Dialnet, ORBi) fall to tier C as repository copies, about 5 of "
    "20 in the ticket 1841 sample.")

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


# ── Membership functions ─────────────────────────────────


def seriousness_rule(registries_cfg: dict, tiers_cfg: dict) -> dict:
    """The seriousness facet as configured: switches (a), (b), (c), tier values, alpha."""
    return {"exclude": rvn.exclusion_registries(registries_cfg),
            "ngo_research_in_b": rvn.ngo_switch(tiers_cfg),
            "no_venue": rvn.unknown_switch(tiers_cfg),
            "tier_mu": dict(sorted(rvn.tier_membership(tiers_cfg).items())),
            "alpha": rvn.alpha(tiers_cfg),
            "tiers": ["A", "B"], "drop_publishers": []}


def membership_rule(cfg: dict, screen_rule: dict, alpha: float) -> dict:
    """ICF and discipline values of ``config/rel_screen.yaml`` ``membership``, checked.

    Every value lies in [0, 1]; the alpha-cut must reproduce the crisp ICF exit
    rule: unsure is in REL iff ``stage2_unsure_in_rel``.
    """
    m = cfg.get("membership") or {}
    out = {"status": m.get("status", ""),
           "icf": {str(k): float(v) for k, v in (m.get("icf") or {}).items()},
           "discipline": {str(k): float(v) for k, v in (m.get("discipline") or {}).items()}}
    for facet, keys in (("icf", {"icf", "unsure", "aux", "out"}),
                        ("discipline", {"yes", "unsure", "no"})):
        if set(out[facet]) != keys or not all(0 <= v <= 1 for v in out[facet].values()):
            raise ValueError(f"membership.{facet} must give {sorted(keys)} values in [0, 1]")
    if (out["icf"]["unsure"] >= alpha) != screen_rule["stage2_unsure_in_rel"]:
        raise ValueError("membership.icf.unsure and alpha contradict stage2_unsure_in_rel")
    return out


def seriousness_of(venue: dict, srule: dict) -> tuple[float, str]:
    """``(value, detail)`` of the seriousness facet for one work.

    ``detail``: ``registry:<r>``, ``tier_c``, ``tier_unknown`` (switch (c)
    ``exclude``), ``tier_<t>`` for a tier left out by ``tiers``,
    ``publisher:<p>``, or ``""``.
    """
    excl = sorted({f["registry"] for f in parse_flags(venue["flags"]) if f["match"] != "title"}
                  & set(srule["exclude"]))
    if excl:
        return 0.0, "registry:" + excl[0]
    tier = venue["tier_ngo_in_b"] if srule["ngo_research_in_b"] else venue["tier_ngo_not_b"]
    if tier == "unknown" and srule["no_venue"] == "exclude":
        return 0.0, "tier_unknown"
    if tier != "unknown" and tier not in srule["tiers"]:
        return 0.0, f"tier_{tier.lower()}"
    if venue.get("publisher_flag") in srule["drop_publishers"]:
        return 0.0, "publisher:" + venue["publisher_flag"]
    value = float(srule["tier_mu"][tier])
    return value, "tier_c" if tier == "C" and not value else ""


def icf_of(row: dict, mrule: dict) -> tuple[float | None, str]:
    if row["status"] in ICF_PENDING:
        return None, row["status"]
    return mrule["icf"][ICF_STATUS[row["status"]]], row["status"]


def discipline_value(contrib: str, mrule: dict) -> float | None:
    if not contrib:
        return None
    return mrule["discipline"]["unsure" if contrib in DISCIPLINE_AS_UNSURE else contrib]


def evaluate(values: list[tuple[str, float | None, str]], alpha: float) -> dict:
    """Membership, attaining facet and reason from ``(facet, value, detail)`` in order."""
    graded, pending = [], ""
    for name, value, detail in values:
        if value is None:
            pending = name
            break
        graded.append((name, value, detail))
        if value == 0:
            break
    mu = min(v for _, v, _ in graded) if graded else None
    first = next(((n, d) for n, v, d in graded if v == mu), ("", ""))
    if mu is not None and mu < alpha:
        reason, detail = f"{first[0]}_excluded", first[1]
    elif pending:
        reason, detail = f"{pending}_pending", ""
    else:
        reason, detail = "included", ""
    return {"mu": mu, "mu_facet": first[0], "mu_complete": not pending or reason.endswith(
        "_excluded"), "rel_reason": reason, "rel_reason_detail": detail,
        "graded": {n for n, _, _ in graded}}


# ── Discipline rows ──────────────────────────────────────


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
    cands = forward or catchup
    win = cands[-1] if cands else None
    return win, len(dims) - (win is not None), len({d["contrib"] for d in cands}) > 1


# ── The view ─────────────────────────────────────────────


def _facet_values(row: dict, venue: dict, srule: dict, mrule: dict) -> list:
    s_val, s_detail = seriousness_of(venue, srule)
    i_val, i_detail = icf_of(row, mrule)
    return [("seriousness", s_val, s_detail), ("icf", i_val, i_detail),
            ("discipline", discipline_value(row["contrib"], mrule), row["discipline_field"])]


def assign(rows: list[dict], pool: list[dict], dims: list[dict], venues: dict,
           srule: dict, mrule: dict) -> dict:
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
        })
        values = _facet_values(row, venue, srule, mrule)
        ev = evaluate(values, srule["alpha"])
        row["seriousness"] = values[0][2]
        row["seriousness_flag"] = "no_venue" if row["tier"] == "unknown" and values[0][1] else ""
        for name, value, _ in values:
            row[f"mu_{name}"] = _fmt(value) if name in ev["graded"] else ""
        row.update({k: ev[k] for k in ("mu_facet", "rel_reason", "rel_reason_detail")})
        row["mu"] = _fmt(ev["mu"])
        row["mu_complete"] = "true" if ev["mu_complete"] else "false"
        row["rel_final"] = "true" if ev["rel_reason"] == "included" else "false"
    assign_families(rows)
    return {"dimension_rows": len(dims),
            "dimension_rows_matched": sum(len(v) for v in by_work.values()),
            "dimension_rows_unused": unused,
            "works_with_disagreeing_dimension_rows": conflicts}


def _fmt(value: float | None) -> str:
    return "" if value is None else f"{value:g}"


def _rank(r: dict) -> tuple:
    """Sort key of a family member: final members by mu, then furthest along."""
    reason = r["rel_reason"]
    cls = 0 if reason == "included" else 1 if reason.endswith("_pending") else 2
    facet = FACETS.index(reason.rsplit("_", 1)[0]) if cls else 0
    return (cls, -facet, -float(r["mu"] or 0), not rv._is_article(r["pool_doc_type"]),
            r["year"] or "9999", r["work_key"])


def assign_families(rows: list[dict]) -> None:
    """``rel_family_id``: the representative of each family (module docstring)."""
    groups = defaultdict(list)
    for row in rows:
        groups[row["family_id"]].append(row)
    for members in groups.values():
        rep = min(members, key=_rank)
        for r in members:
            r["rel_family_id"] = rep["work_key"]


# ── Counts ───────────────────────────────────────────────


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
    included = by["included"]
    return {
        "facet_order": FACETS,
        "works": {k: len(by[k]) for k in REASONS},
        "families": {k: sum(r["rel_reason"] == k for r in fam_rows) for k in REASONS},
        "seriousness_excluded_by_detail_works": _split(by["seriousness_excluded"],
                                                       "rel_reason_detail"),
        "icf_excluded_by_status_works": _split(by["icf_excluded"], "rel_reason_detail"),
        "icf_pending_by_status_works": _split(by["icf_pending"], "status"),
        "icf_pending_by_tier_works": _split(by["icf_pending"], "tier"),
        "discipline_excluded_by_field_works": _split(by["discipline_excluded"],
                                                     "discipline_field"),
        "discipline_excluded_by_source_works": _split(by["discipline_excluded"],
                                                      "discipline_source"),
        "discipline_pending_by_tier_works": _split(by["discipline_pending"], "tier"),
        "discipline_pending_by_mu_works": _split(by["discipline_pending"], "mu"),
        "included_by_mu_works": _split(included, "mu"),
        "included_mu_weighted_works": sum(float(r["mu"]) for r in included),
        "included_by_tier_works": _split(included, "tier"),
        "included_by_publisher_flag_works": dict(sorted(Counter(
            r["publisher_flag"] for r in included if r["publisher_flag"]).items())),
        "included_discipline_flagged_works": _split(
            [r for r in included if r["discipline_flag"]], "discipline_flag"),
        "included_icf_unsure_flagged_works": sum(r["rel_flag"] == "unsure" for r in included),
        "included_no_venue_flagged_works": sum(r["seriousness_flag"] == "no_venue"
                                               for r in included),
    }


def stage2_skip(rows: list[dict]) -> dict:
    """ICF-pending works by tier: those whose seriousness is 0 need no ICF screening."""
    out = {}
    for status in sorted(ICF_PENDING):
        rs = [r for r in rows if r["status"] == status]
        out[status] = {"by_tier": _split(rs, "tier"),
                       "skippable_seriousness_0": sum(
                           r["rel_reason"] == "seriousness_excluded" for r in rs),
                       "to_screen": sum(r["rel_reason"] == "icf_pending" for r in rs)}
    return out


# ── Sensitivity ──────────────────────────────────────────


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


def sensitivity(rows: list[dict], venues: dict, base: dict, mrule: dict) -> list[dict]:
    """REL under each seriousness setting, ICF and discipline values fixed.

    Every work is re-evaluated (seriousness comes first, so a setting moves
    works between every reason). Works and families (a family is in when any
    member is); ``included_mu_weighted``: the sum of ``mu`` over the included
    works. ``discipline_pending_*``: works whose only missing facet is
    discipline, the provisional upper bound while 1842 has not run. Under
    switch (c) ``keep_flagged``, ``tier_a_only`` still keeps the works of tier
    ``unknown``; the ``no_venue_flipped`` row shows them excluded.
    """
    out = []
    for name, srule in _scenarios(base):
        inc, pend = [], []
        for r in rows:
            ev = evaluate(_facet_values(r, venues[r["work_key"]], srule, mrule), srule["alpha"])
            if ev["rel_reason"] == "included":
                inc.append((r, ev["mu"]))
            elif ev["rel_reason"] == "discipline_pending":
                pend.append(r)
        out.append({
            "scenario": name,
            "exclude_registries": ";".join(srule["exclude"]),
            "tiers": "+".join(srule["tiers"]),
            "ngo_research_in_b": str(srule["ngo_research_in_b"]).lower(),
            "drop_publishers": ";".join(srule["drop_publishers"]),
            "no_venue": srule["no_venue"],
            "included_works": len(inc),
            "included_families": len({r["family_id"] for r, _ in inc}),
            "included_mu_weighted": _fmt(sum(mu for _, mu in inc)),
            "discipline_pending_works": len(pend),
            "discipline_pending_families": len({r["family_id"] for r in pend}),
        })
    return out
