"""Seriousness tier and registry flags per venue and per REL work (ticket 1841).

Inputs (all read-only):

- ``data/rel_pool/pool.csv`` and the live intake deliveries it was built
  from (``data/rel_intake``): member records give TOC ISSNs (lane 1650),
  RePEc series handles (lane 1810) and record-id prefixes (lanes 1653, 1790);
- ``data/rel_venues/openalex_work_venues.csv``, the OpenAlex venue cache
  (``enrich_rel_venues_openalex.py``);
- ``config/rel_toc_manifest.csv`` (TOC journals: ISSNs, publisher);
- ``config/rel_venue_tiers.yaml`` (B list, repositories, publisher flag);
- ``config/rel_venue_registries.yaml`` and the registry pull it names
  (``use``) under ``--archive-root``; each file is checked against the
  pull's ``MANIFEST.sha256`` before it is parsed.

Outputs (``--output-dir``, default ``data/rel_pool``), deterministic: sorted
rows, no timestamps, byte-identical on rerun with the same inputs.

- ``rel_venues.csv``  one row per venue: key, OpenAlex source id, ISSN-L,
  ISSNs, name, publisher, source type, tier, tier rule, B entry, the tier
  under each NGO setting, registry flags (``registry:entry_id[match]``), flag
  details (Kanalregisteret: every yearly level), number of works excluded and
  by which registries, publisher flag, works;
- ``rel_work_venues.csv``  one row per pool work: work key, lanes, venue key,
  how the venue was resolved, tier, tier rule, the tier under each NGO
  setting, flags (per work: Kanalregisteret by the work's year, hijacked by
  every URL of the work), flagged, excluded, excluded by, publisher flag (loader:
  ``_rel_venues.load_work_venues``; the REL view is ticket 1843's);
- ``rel_venue_counts.json`` / ``.md``  venues and works per tier, per registry
  flag, excluded, moved by the NGO switch and per publisher flag, by lane,
  and the works with no venue.

Switches (author decisions 2026-10-01): ``exclusion.exclude`` in
``rel_venue_registries.yaml`` and ``ngo_research_in_b`` in
``rel_venue_tiers.yaml``. Every flag and both tiers are always written, so
any other setting is recomputable from the tables.

Resolution and tier rules: ``_rel_venues`` module docstring.

Usage:
    python scripts/corpus_rel_venues.py --archive-root DIR [--output-dir data/rel_pool]
"""

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict

import _rel_venue_registries as rvr
import _rel_venues as rv
import yaml
from _rel_pool_keys import norm_openalex
from _venue_naming import canonical_venue, venue_type
from utils import get_logger

log = get_logger("corpus_rel_venues")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "config")

VENUE_COLUMNS = ["venue_key", "openalex_source_id", "issn_l", "issns", "name", "publisher",
                 "source_type", "tier", "tier_rule", "b_id", "tier_ngo_in_b", "tier_ngo_not_b",
                 "flags", "flag_details", "n_works_excluded", "excluded_by", "publisher_flag",
                 "n_works", "tiers_version"]
WORK_COLUMNS = ["work_key", "year", "lanes", "venue_key", "venue_resolution", "tier", "tier_rule",
                "b_id", "tier_ngo_in_b", "tier_ngo_not_b", "tier_without_nonresearch", "flags", "flagged",
                "excluded",
                "excluded_by", "publisher_flag"]
NGO_CATEGORY = "ngo_research"
REPEC_LANE = "t1810-repec-local"
TOC_LANE = "t1650-sommaires"


def _read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _write_csv(path, columns, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})


# ── Inputs ───────────────────────────────────────────────


def pool_deliveries(pool):
    """Delivery ids (``lane/delivery``) the pool's member records name, sorted.

    The pool lists only live deliveries, so their supersession is already
    resolved: this needs no second reading of the intake manifests.
    """
    return sorted({m.split(":", 1)[0] for w in pool
                   for m in (w.get("member_record_ids") or "").split(";")
                   if ":" in m and "/" in m.split(":", 1)[0]})


def load_members(intake_dir, pool):
    """``{member id: evidence}`` for every intake record of a delivery the pool names."""
    out = {}
    for did in pool_deliveries(pool):
        path = os.path.join(intake_dir, did)
        for r in _read_csv(os.path.join(path, "records.csv")):
            rid = r["record_id"]
            out[f"{did}:{rid}"] = {
                "lane": did.split("/")[0],
                "issns": rvr.issns_in(r.get("issn")),
                "journal_key": r.get("journal_key") or "",
                "repec": rv.repec_handle(r.get("series_handle")),
                "template": r.get("template_type") or "",
                "prefix": rid.split(":", 1)[0].lower() if ":" in rid else "",
                "url": r.get("url") or "",
            }
    return out


def load_registries(archive_root, reg_cfg):
    """Registry entries of the configured pull, after checking its manifest."""
    pull = str(reg_cfg["use"])
    day = os.path.join(archive_root, pull)
    manifest = {}
    with open(os.path.join(day, "MANIFEST.sha256"), encoding="utf-8") as fh:
        for line in fh:
            digest, name = line.rstrip("\n").split("  ", 1)
            manifest[name] = digest
    regs = reg_cfg["registries"]
    unknown = sorted(set(rv.exclusion_registries(reg_cfg)) - set(regs))
    if unknown:
        raise ValueError(f"exclusion.exclude names unknown registries {unknown}")
    expected = sorted({f for r in regs.values() for f in ([r["file"]] if "file" in r else r["files"])})
    missing = [f for f in expected if f not in manifest]
    if missing:
        raise RuntimeError(f"{day}/MANIFEST.sha256 does not cover {missing}")
    for name, digest in manifest.items():
        if rvr.sha256_file(os.path.join(day, name)) != digest:
            raise RuntimeError(f"{day}/{name}: sha256 differs from MANIFEST.sha256")
    entries = []
    entries += rvr.parse_kanalregisteret(os.path.join(day, regs["kanalregisteret"]["file"]),
                                         regs["kanalregisteret"]["entry_url"])[1]
    entries += rvr.parse_scopus_discontinued(os.path.join(day, regs["scopus_discontinued"]["file"]),
                                             regs["scopus_discontinued"]["entry_url"])[1]
    d = regs["doaj_withdrawn"]
    entries += rvr.parse_doaj_withdrawn([os.path.join(day, f) for f in d["files"]],
                                        d["reason_pattern"], d["entry_url"])[1]
    entries += rvr.parse_hijacked(os.path.join(day, regs["hijacked"]["file"]),
                                  regs["hijacked"].get("page", ""))[1]
    return rv.RegistryIndex(entries, pull)


# ── Per-work venue resolution ────────────────────────────


class Resolver:
    """Venue key of a pool work from its OpenAlex rows and member records."""

    def __init__(self, oa_cache, members, toc_manifest, b_prefixes=()):
        self.oa = oa_cache
        self.b_prefixes = set(b_prefixes)
        self.members = members
        self.toc = {r["journal_key"]: r for r in toc_manifest}
        self.sources = {}
        for oid in sorted(oa_cache):
            r = oa_cache[oid]
            if r.get("source_id") and r["source_id"] not in self.sources:
                self.sources[r["source_id"]] = r
        self.issn_to_source = {}
        names = defaultdict(set)
        for sid in sorted(self.sources):
            r = self.sources[sid]
            for i in self._source_issns(r):
                self.issn_to_source.setdefault(i, sid)
            names[rv.name_key(r["source_name"])].add(sid)
        self.name_to_source = {n: min(s) for n, s in names.items() if n and len(s) == 1}

    @staticmethod
    def _source_issns(r):
        return sorted({rvr.norm_issn(x) for x in [r.get("issn_l")] + (r.get("issns") or "").split(";")}
                      - {""})

    def resolve(self, work):
        """``(venue_key, resolution, evidence)`` for one pool row."""
        ids = [norm_openalex(work.get("openalex_id"))]
        ids += sorted({norm_openalex(x) for x in (work.get("all_openalex_ids") or "").split(";")}
                      - set(ids))
        oa = next((self.oa[i] for i in ids if i and i in self.oa and self.oa[i].get("source_id")), None)
        landing = (oa or {}).get("landing_url", "")
        mem = [self.members[m] for m in (work.get("member_record_ids") or "").split(";")
               if m in self.members]
        # Every URL the work is known by, for the hijacked check: the landing
        # page of each of its OpenAlex rows, with or without a source, and the
        # URL of each intake member record (the lanes outside OpenAlex).
        urls = sorted(({self.oa[i].get("landing_url") or "" for i in ids if i in self.oa}
                       | {m["url"] for m in mem} | {landing}) - {""})
        catalogue_sources = sorted({m.split(":", 1)[0].lower()
                                    for m in (work.get("member_record_ids") or "").split(";")
                                    if ":" in m and "/" not in m.split(":", 1)[0]})
        repec = next((m["repec"] for m in mem if m["repec"]), "") or rv.repec_from_url(landing)
        template = next((m["template"] for m in mem if m["repec"]), "")
        toc = next((m for m in mem if m["lane"] == TOC_LANE and m["issns"]), None)
        ev = {"landing_url": landing, "urls": urls, "repec": repec, "template": template,
              "prefixes": sorted({m["prefix"] for m in mem if m["prefix"]} | set(catalogue_sources)),
              "toc_issns": toc["issns"] if toc else (),
              "toc_publisher": self.toc.get(toc["journal_key"], {}).get("publisher", "") if toc else "",
              "journal": work.get("journal") or "", "doc_type": work.get("doc_type") or ""}

        if oa and not (oa.get("source_type") == "repository" and repec):
            return f"openalex:{oa['source_id']}", "openalex", ev
        if toc:
            sid = next((self.issn_to_source[i] for i in toc["issns"] if i in self.issn_to_source), "")
            if sid:
                return f"openalex:{sid}", "toc_issn_to_openalex", ev
            return f"issn:{toc['issns'][0]}", "toc_issn", ev
        if repec:
            if template == "redif-article":
                sid = self.name_to_source.get(rv.name_key(work.get("journal")), "")
                if sid:
                    return f"openalex:{sid}", "repec_journal_name_to_openalex", ev
            return repec, "repec", ev
        b_pref = [p for p in ev["prefixes"] if p in self.b_prefixes]
        if b_pref:
            return f"prefix:{b_pref[0]}", "record_prefix", ev
        name = rv.name_key(canonical_venue(work.get("journal"))) if work.get("journal") else ""
        if name and name != "missing":
            sid = self.name_to_source.get(name, "")
            if sid:
                return f"openalex:{sid}", "name_to_openalex", ev
            return f"name:{name}", "name", ev
        return "none", "none", ev


# ── Build ────────────────────────────────────────────────


def _majority(values):
    """Most common non-empty value; ties broken by the smallest. ``""`` if none."""
    c = Counter(v for v in values if v)
    if not c:
        return ""
    top = max(c.values())
    return min(v for v, n in c.items() if n == top)


def _year(value):
    """Publication year as an int, ``None`` when blank or not a year."""
    try:
        y = int(float(str(value).strip()))
    except ValueError:
        return None
    return y if 1000 <= y <= 2999 else None


def _tier(key, v, tiers, b_prefix):
    if key == "none":
        return "unknown", "no_venue", ""
    if key.startswith("prefix:") and v["record_prefixes"][0] in b_prefix:
        return "B", "b_institution", b_prefix[v["record_prefixes"][0]]
    return rv.assign_tier(v, tiers)


def _by_site(urls, tiers, base, nonresearch_on):
    """``(tier, b_id, nonresearch)`` of a work of tier ``base`` by its own URLs."""
    dom, url = rv.b_by_domain_url(urls, tiers)
    if not dom:
        return base, "", False
    if nonresearch_on and rv.is_nonresearch(url, tiers):
        return "C", "", True
    return "B", dom, False


def _work_tier(ven, urls, tiers, tiers_no_ngo, ngo_in_b, nonresearch_on):
    """``(tier, rule, b_id, tier_ngo_in_b, tier_ngo_not_b, tier_without_nonresearch)`` of a work.

    A work with no venue, or a C venue (repository, unlisted source), that a B
    institution published on its own site is B by its URL (rule ``b_domain``);
    a non-research page of such a site (blog post, speech, homepage, media
    compilation: the ``nonresearch`` list, switch d) goes to C (rule
    ``nonresearch``) when the switch is ``to_c``.
    """
    tier, rule, b_id = ven["tier"], ven["tier_rule"], ven["b_id"]
    if tier not in ("unknown", "C"):
        return tier, rule, b_id, ven["tier_ngo_in_b"], ven["tier_ngo_not_b"], tier
    t_in, dom_in, nr_in = _by_site(urls, tiers, ven["tier_ngo_in_b"], nonresearch_on)
    t_not, dom_not, nr_not = _by_site(urls, tiers_no_ngo, ven["tier_ngo_not_b"], nonresearch_on)
    t_sel, dom, nr = (t_in, dom_in, nr_in) if ngo_in_b else (t_not, dom_not, nr_not)
    raw = _by_site(urls, tiers if ngo_in_b else tiers_no_ngo, tier, False)[0]
    if nr:
        return "C", "nonresearch", "", t_in, t_not, raw
    if dom:
        return "B", "b_domain", dom, t_in, t_not, raw
    return tier, rule, b_id, t_in, t_not, raw


def build(pool, resolver, tiers, registries, tiers_cfg, exclude=()):
    """``(venue rows, work rows)``, both sorted.

    ``exclude``: registries whose flag sets ``excluded`` (switch a). The NGO
    switch (b) is read from ``tiers_cfg``; both tiers are always computed.
    """
    ngo_in_b = rv.ngo_switch(tiers_cfg)
    nonresearch_on = rv.nonresearch_switch(tiers_cfg) == "to_c"
    tiers_no_ngo = rv.without_categories(tiers, [NGO_CATEGORY])
    works, by_venue = [], defaultdict(list)
    for w in pool:
        key, how, ev = resolver.resolve(w)
        works.append((w, key, how, ev))
        by_venue[key].append(ev)
    b_prefix = {p: e["id"] for e in tiers["b"] for p in e["record_prefix"]}
    b_prefix_no_ngo = {p: e["id"] for e in tiers_no_ngo["b"] for p in e["record_prefix"]}

    venues = {}
    for key in sorted(by_venue):
        evs = by_venue[key]
        v = {"key": key, "name": "", "hosts": [], "source_id": "", "source_type": "", "issns": [],
             "issn_l": "", "repec": "", "repec_template": "", "record_prefixes": [],
             "toc_journal": False, "declared_journal": False, "publisher": ""}
        toc_issns = sorted({i for e in evs for i in e["toc_issns"]})
        toc_pub = _majority(e["toc_publisher"] for e in evs)
        if key.startswith("openalex:"):
            s = resolver.sources[key.split(":", 1)[1]]
            v.update(name=s["source_name"], source_id=s["source_id"], source_type=s["source_type"],
                     issn_l=rvr.norm_issn(s.get("issn_l")), publisher=s["host_org_name"],
                     hosts=[s["host_org_name"]] + (s.get("host_lineage_names") or "").split(";") + [toc_pub],
                     issns=sorted(set(Resolver._source_issns(s)) | set(toc_issns)),
                     toc_journal=bool(toc_issns))
        elif key.startswith("issn:"):
            v.update(name=_majority(e["journal"] for e in evs), issns=toc_issns, issn_l=toc_issns[0],
                     publisher=toc_pub, hosts=[toc_pub], toc_journal=True)
        elif key.startswith("repec:"):
            v.update(name=_majority(e["journal"] for e in evs), repec=key,
                     repec_template=_majority(e["template"] for e in evs))
        elif key.startswith("prefix:"):
            v.update(name=_majority(e["journal"] for e in evs), record_prefixes=[key.split(":", 1)[1]])
        elif key.startswith("name:"):
            name = _majority(e["journal"] for e in evs)
            n_journal = sum(rv.fold(e["doc_type"]) in tiers["journal_doc_types"] for e in evs)
            v.update(name=name, declared_journal=(venue_type(canonical_venue(name)) == "journal"
                                                  and 2 * n_journal >= len(evs)))
        with_ngo = _tier(key, v, tiers, b_prefix)
        without_ngo = _tier(key, v, tiers_no_ngo, b_prefix_no_ngo)
        tier, rule, b_id = with_ngo if ngo_in_b else without_ngo
        flags = registries.venue_flags(v["issns"], v["name"]) if key != "none" else []
        venues[key] = {
            "venue_key": key, "openalex_source_id": v["source_id"], "issn_l": v["issn_l"],
            "issns": ";".join(v["issns"]), "name": v["name"], "publisher": v["publisher"],
            "source_type": v["source_type"] or ("repec_" + v["repec_template"] if v["repec"] else ""),
            "tier": tier, "tier_rule": rule, "b_id": b_id, "_flags": flags,
            "tier_ngo_in_b": with_ngo[0], "tier_ngo_not_b": without_ngo[0],
            "publisher_flag": rv.publisher_flag(v, tiers), "n_works": len(evs),
            "tiers_version": tiers_cfg["version"],
        }

    work_rows = []
    for w, key, how, ev in works:
        ven = venues[key]
        year = _year(w.get("year"))
        flags = rv.work_venue_flags(ven["_flags"], year) + registries.work_flags(ev["urls"])
        tier, rule, b_id, t_in, t_not, t_raw = _work_tier(ven, ev["urls"], tiers, tiers_no_ngo,
                                                          ngo_in_b, nonresearch_on)
        work_rows.append({
            "work_key": w["work_key"], "year": "" if year is None else str(year),
            "lanes": w.get("sources") or "", "venue_key": key,
            "venue_resolution": how, "tier": tier, "tier_rule": rule,
            "b_id": b_id, "tier_ngo_in_b": t_in,
            "tier_ngo_not_b": t_not, "tier_without_nonresearch": t_raw, "flags": rv.flags_text(flags),
            "flagged": "true" if flags else "false", "excluded_by": rv.exclusion_of(flags, exclude),
            "publisher_flag": ven["publisher_flag"],
            "_flags": flags,
        })
    # Hijacked hits stay on their works: a clone's landing page does not make
    # the legitimate venue it imitates disreputable.
    for r in work_rows:
        r["excluded"] = "true" if r["excluded_by"] else "false"
    # A venue's exclusion is per work (Kanalregisteret levels are per year,
    # hijacked hits per URL): the venue row counts its excluded works and
    # names the registries behind them.
    excl = defaultdict(lambda: [0, set()])
    for r in work_rows:
        if r["excluded_by"]:
            excl[r["venue_key"]][0] += 1
            excl[r["venue_key"]][1].update(r["excluded_by"].split(";"))
    for key, ven in venues.items():
        ven["_flags"].sort(key=lambda f: (f["registry"], f["entry_id"], f["match"]))
        ven["flags"] = rv.flags_text(ven["_flags"])
        ven["n_works_excluded"] = excl[key][0] if key in excl else 0
        ven["excluded_by"] = ";".join(sorted(excl[key][1])) if key in excl else ""
        ven["flag_details"] = " ; ".join(
            f"{f['registry']} {f['entry_id']} ({f['match']}, pull {f['pull_date']}): {f['reason']} {f['entry_url']}".strip()
            for f in ven["_flags"])
    work_rows.sort(key=lambda r: r["work_key"])
    return [venues[k] for k in sorted(venues)], work_rows


# ── Counts ───────────────────────────────────────────────


def make_counts(venue_rows, work_rows, registries_pull, tiers_version, switches=None):
    def lanes(r):
        return [x for x in r["lanes"].split(";") if x] or ["(none)"]

    by_lane = defaultdict(lambda: {"works": 0, "tier": Counter(), "registry": Counter(),
                                   "flagged": 0, "excluded": 0, "ngo_switch_moves": 0, "nonresearch_moves": 0,
                                   "publisher_flag": Counter(), "no_venue": 0})
    for r in work_rows:
        regs = sorted({f["registry"] for f in r["_flags"]})
        for lane in ["(all)"] + lanes(r):
            b = by_lane[lane]
            b["works"] += 1
            b["tier"][r["tier"]] += 1
            b["flagged"] += r["flagged"] == "true"
            b["excluded"] += r["excluded"] == "true"
            b["ngo_switch_moves"] += r["tier_ngo_in_b"] != r["tier_ngo_not_b"]
            b["nonresearch_moves"] += r["tier"] != r["tier_without_nonresearch"]
            for g in regs:
                b["registry"][g] += 1
            if r["publisher_flag"]:
                b["publisher_flag"][r["publisher_flag"]] += 1
            b["no_venue"] += r["venue_key"] == "none"
    venues = {
        "total": len(venue_rows),
        "tier": dict(sorted(Counter(v["tier"] for v in venue_rows).items())),
        "tier_rule": dict(sorted(Counter(v["tier_rule"] for v in venue_rows).items())),
        "registry": dict(sorted(Counter(g for v in venue_rows
                                        for g in {f["registry"] for f in v["_flags"]}).items())),
        "flagged": sum(bool(v["_flags"]) for v in venue_rows),
        "with_excluded_works": sum(v["n_works_excluded"] > 0 for v in venue_rows),
        "ngo_switch_moves": sum(v["tier_ngo_in_b"] != v["tier_ngo_not_b"] for v in venue_rows),
        "publisher_flag": dict(sorted(Counter(v["publisher_flag"] for v in venue_rows
                                              if v["publisher_flag"]).items())),
    }
    b_works = Counter(r["b_id"] for r in work_rows if r["tier"] == "B" and r["b_id"])
    venues["b_id_works"] = dict(sorted(b_works.items()))
    works = {lane: {"works": b["works"], "tier": dict(sorted(b["tier"].items())),
                    "registry": dict(sorted(b["registry"].items())), "flagged": b["flagged"],
                    "excluded": b["excluded"], "ngo_switch_moves": b["ngo_switch_moves"],
                    "nonresearch_moves": b["nonresearch_moves"],
                    "publisher_flag": dict(sorted(b["publisher_flag"].items())),
                    "no_venue": b["no_venue"]}
             for lane, b in sorted(by_lane.items())}
    resolution = dict(sorted(Counter(r["venue_resolution"] for r in work_rows).items()))
    return {"tiers_version": tiers_version, "registries_pull": registries_pull,
            "switches": switches or {}, "venues": venues, "works_by_lane": works, "venue_resolution": resolution,
            "work_tier_rule": dict(sorted(Counter(r["tier_rule"] for r in work_rows).items()))}


def counts_markdown(c):
    tiers = ["A", "B", "C", "unknown"]
    regs = sorted({g for b in c["works_by_lane"].values() for g in b["registry"]})
    pubs = sorted({g for b in c["works_by_lane"].values() for g in b["publisher_flag"]})
    lines = [f"# REL venue tiers and flags (tiers v{c['tiers_version']}, registries pull {c['registries_pull']})",
             "", f"Switches (author decisions 2026-10-01): excluding registries "
             f"{', '.join(c['switches'].get('exclude', [])) or 'none'}; NGO research series in B: "
             f"{c['switches'].get('ngo_research_in_b')}; tier unknown: {c['switches'].get('no_venue')}; "
             f"Kanalregisteret X: {c['switches'].get('kanal_x')}; non-research list: "
             f"{c['switches'].get('nonresearch')}. `ngo moves` counts what the other NGO setting would "
             "move between tiers, `nonresearch moves` what the list moves to C. `no venue (key none)` counts "
             "works with no venue key; some of them are B by their own site (b_domain), the rest are tier "
             "`unknown`.",
             "", "## Venues", "",
             f"{c['venues']['total']} venues; per tier "
             + ", ".join(f"{t} {c['venues']['tier'].get(t, 0)}" for t in tiers)
             + f"; with excluded works {c['venues']['with_excluded_works']}; ngo moves {c['venues']['ngo_switch_moves']}"
             + f"; flagged by a registry {c['venues']['flagged']} ("
             + ", ".join(f"{g} {n}" for g, n in c["venues"]["registry"].items()) + "); publisher flag "
             + ", ".join(f"{g} {n}" for g, n in c["venues"]["publisher_flag"].items()) + ".",
             "", "## Works by lane", "",
             "| lane | works | " + " | ".join(tiers) + " | ngo moves | nonresearch moves | flagged | excluded | "
             + " | ".join(regs) + " | " + " | ".join(pubs) + " | no venue (key none) |",
             "|" + "---|" * (7 + len(tiers) + len(regs) + len(pubs))]
    for lane, b in c["works_by_lane"].items():
        lines.append(f"| {lane} | {b['works']} | " + " | ".join(str(b["tier"].get(t, 0)) for t in tiers)
                     + f" | {b['ngo_switch_moves']} | {b['nonresearch_moves']} | {b['flagged']} | {b['excluded']} | "
                     + " | ".join(str(b["registry"].get(g, 0)) for g in regs)
                     + " | " + " | ".join(str(b["publisher_flag"].get(g, 0)) for g in pubs)
                     + f" | {b['no_venue']} |")
    lines += ["", "## Venue resolution (works)", ""]
    lines += [f"- {k}: {n}" for k, n in c["venue_resolution"].items()]
    lines += ["", "## Tier rule (works)", ""]
    lines += [f"- {k}: {n}" for k, n in c["work_tier_rule"].items()]
    lines += ["", "## Tier B works by B entry", ""]
    lines += [f"- {k}: {n}" for k, n in sorted(c["venues"]["b_id_works"].items(), key=lambda x: (-x[1], x[0]))]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--pool", default=os.path.join(ROOT, "data", "rel_pool", "pool.csv"))
    ap.add_argument("--intake-dir", default=os.path.join(ROOT, "data", "rel_intake"))
    ap.add_argument("--oa-cache", default=os.path.join(ROOT, "data", "rel_venues",
                                                       "openalex_work_venues.csv"))
    ap.add_argument("--toc-manifest", default=os.path.join(CFG, "rel_toc_manifest.csv"))
    ap.add_argument("--tiers", default=os.path.join(CFG, "rel_venue_tiers.yaml"))
    ap.add_argument("--registries", default=os.path.join(CFG, "rel_venue_registries.yaml"))
    ap.add_argument("--archive-root", required=True)
    ap.add_argument("--output-dir", default=os.path.join(ROOT, "data", "rel_pool"))
    args = ap.parse_args(argv)

    with open(args.tiers, encoding="utf-8") as fh:
        tiers_cfg = yaml.safe_load(fh)
    with open(args.registries, encoding="utf-8") as fh:
        reg_cfg = yaml.safe_load(fh)
    tiers = rv.compile_tiers(tiers_cfg)
    registries = load_registries(args.archive_root, reg_cfg)
    oa = {r["openalex_id"]: r for r in _read_csv(args.oa_cache)} if os.path.exists(args.oa_cache) else {}
    if not oa:
        log.warning("no OpenAlex venue cache at %s: run make rel-venue-enrich", args.oa_cache)
    pool = _read_csv(args.pool)
    missing = sum(1 for w in pool if norm_openalex(w.get("openalex_id")) and
                  norm_openalex(w.get("openalex_id")) not in oa)
    if missing:
        log.warning("%d pool works have an OpenAlex id the cache lacks: run make rel-venue-enrich", missing)
    resolver = Resolver(oa, load_members(args.intake_dir, pool), _read_csv(args.toc_manifest),
                        [p for e in tiers["b"] for p in e["record_prefix"]])
    exclude = rv.exclusion_registries(reg_cfg)
    venue_rows, work_rows = build(pool, resolver, tiers, registries, tiers_cfg, exclude)
    counts = make_counts(venue_rows, work_rows, registries.pull_date, tiers_cfg["version"],
                         {"exclude": exclude, "ngo_research_in_b": rv.ngo_switch(tiers_cfg),
                          "no_venue": rv.unknown_switch(tiers_cfg),
                          "nonresearch": rv.nonresearch_switch(tiers_cfg),
                          "kanal_x": rv.kanal_x_switch(reg_cfg)})

    os.makedirs(args.output_dir, exist_ok=True)
    _write_csv(os.path.join(args.output_dir, "rel_venues.csv"), VENUE_COLUMNS, venue_rows)
    _write_csv(os.path.join(args.output_dir, "rel_work_venues.csv"), WORK_COLUMNS, work_rows)
    with open(os.path.join(args.output_dir, "rel_venue_counts.json"), "w", encoding="utf-8") as fh:
        json.dump(counts, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(args.output_dir, "rel_venue_counts.md"), "w", encoding="utf-8") as fh:
        fh.write(counts_markdown(counts))
    log.info("%d venues, %d works; per tier %s", len(venue_rows), len(work_rows),
             counts["works_by_lane"]["(all)"]["tier"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
