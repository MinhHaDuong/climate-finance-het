"""Venue identity, seriousness tier and registry flags for REL works (ticket 1841).

Pure functions over in-memory records; ``corpus_rel_venues.py`` does the I/O.
``load_work_venues`` is the loader ticket 1843 joins into the REL view.

**Venue key** (stable across pool rebuilds, never a pool row number):

- ``openalex:S…``  an OpenAlex source;
- ``repec:<archive>:<series>``  a RePEc series, used when OpenAlex has no
  source or only a generic repository for the work;
- ``issn:NNNN-NNNN``  an ISSN no OpenAlex source of the pool carries;
- ``prefix:<prefix>``  a document of a tier-B institution known only by its
  intake record-id prefix (``ipea``, ``ceew``...) or catalogue source
  (``unfccc``, ``oecd``), a ``record_prefix`` of the B list;
- ``name:<folded name>``  the free-text journal name, when nothing else;
- ``none``  no venue at all.

**Tier rule** (first that applies; ``tier_rule`` names it):

1. ``b_series``  a B entry's ``repec`` code or ``series`` pattern → B;
2. ``repository``  a repository/preprint server → C;
3. ``journal``  OpenAlex journal source, RePEc journal series, TOC journal or
   a journal name declared by a journal doc type → A;
4. ``b_institution``  a B entry's ``names``, ``record_prefix``, ISSN or
   OpenAlex id → B;
5. ``other`` → C.

A work with no venue is tier ``unknown`` (rule ``no_venue``), never C. Per
work, an ``unknown`` or C work whose own URL is on a B institution's site
(``b_domains``) is B, rule ``b_domain`` (``corpus_rel_venues.build``).

**Flags**: a registry entry flags a venue whose ISSNs include one of the
entry's ISSNs (``match=issn``), or, for a venue with no ISSN at all, whose
folded name equals the entry's title when that title has two words or more and
is unique in its registry (``match=title``). A hijacked-checker entry flags a
work whose landing-page host is the clone's domain (``match=domain``).

**Switches** (author decisions 2026-10-01, ticket 1841): a flag from a
registry listed in ``exclusion.exclude`` (``rel_venue_registries.yaml``)
sets ``excluded`` when it matched by ISSN or domain; the others, and title
matches, only flag. ``ngo_research_in_b``
(``rel_venue_tiers.yaml``) selects which of the two computed tiers,
``tier_ngo_in_b`` or ``tier_ngo_not_b``, is the ``tier``.
"""

import csv
import re
import unicodedata
from collections import Counter

from _rel_venue_registries import host_of, level_at, norm_issn

# ── Names ────────────────────────────────────────────────


def fold(text):
    """Lower-case, accent-free, punctuation as spaces, single-spaced."""
    t = unicodedata.normalize("NFKD", str(text or ""))
    t = "".join(c for c in t if not unicodedata.combining(c)).casefold()
    t = re.sub(r"[’‘'`]", "", t)
    t = re.sub(r"[^\w&/+-]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def name_key(text):
    """Folded name for equality matching: no leading article, no punctuation."""
    t = re.sub(r"[^\w]+", " ", fold(text)).strip()
    return re.sub(r"^(the|la|le|les|el|los|las|o|a|die|der) ", "", t)


_REPEC_URL = re.compile(r"(?:ideas|econpapers)\.repec\.org/(?:[a-z]/)?(?:RePEc:)?"
                        r"([a-z0-9]{3})[:/]([a-z0-9]{6})", re.I)


def repec_from_url(url):
    """``repec:<archive>:<series>`` from an IDEAS or EconPapers URL, else ``""``."""
    m = _REPEC_URL.search(str(url or ""))
    return f"repec:{m.group(1).lower()}:{m.group(2).lower()}" if m else ""


def repec_handle(handle):
    """``repec:<archive>:<series>`` from a RePEc series handle (``RePEc:nbr:nberwo``)."""
    parts = str(handle or "").strip().lower().split(":")
    if len(parts) >= 3 and parts[0] == "repec":
        return f"repec:{parts[1]}:{parts[2]}"
    return ""


# ── Configuration ────────────────────────────────────────


def _rx(patterns):
    return [re.compile(p, re.I) for p in patterns or []]


def compile_tiers(cfg):
    """The tier configuration with its regexes compiled."""
    b = []
    for e in cfg["b_list"]:
        b.append({
            "id": e["id"], "category": e.get("category", ""),
            "repec": [str(x).lower() for x in e.get("repec") or []],
            "series": _rx(e.get("series")), "names": _rx(e.get("names")),
            "record_prefix": [str(x).lower() for x in e.get("record_prefix") or []],
            "openalex": set(e.get("openalex") or []),
            "issn": {norm_issn(x) for x in e.get("issn") or []} - {""},
        })
    domains = cfg.get("b_domains") or {}
    unknown_ids = sorted(set(domains) - {e["id"] for e in b})
    if unknown_ids:
        raise ValueError(f"b_domains names ids not in b_list: {unknown_ids}")
    for e in b:
        e["domains"] = sorted(str(d).lower() for d in domains.get(e["id"]) or [])
    rep = cfg.get("repositories") or {}
    return {
        "version": cfg["version"], "b": b,
        "repo_types": set(rep.get("types") or []), "repo_names": _rx(rep.get("names")),
        "repo_repec": [str(x).lower() for x in rep.get("repec") or []],
        "journal_types": set(cfg.get("journal_types") or ["journal"]),
        "journal_doc_types": {fold(x) for x in cfg.get("journal_doc_types") or []},
        "nonresearch": _rx((cfg.get("nonresearch") or {}).get("url_patterns")),
        "publishers": [{"id": p["id"], "names": _rx(p.get("names")),
                        "repec": [str(x).lower() for x in p.get("repec") or []]}
                       for p in cfg.get("publisher_flags") or []],
    }


def without_categories(tiers, categories):
    """A copy of compiled ``tiers`` whose B list drops the given categories."""
    return dict(tiers, b=[e for e in tiers["b"] if e["category"] not in set(categories)])


def ngo_switch(cfg):
    """Value of the switch ``ngo_research_in_b`` (default ``True``)."""
    return bool((cfg.get("ngo_research_in_b") or {}).get("value", True))


NO_VENUE_VALUES = ("keep_flagged", "exclude")
NONRESEARCH_VALUES = ("to_c", "off")
KANAL_X_VALUES = ("flag_only", "exclude")


def nonresearch_switch(cfg):
    """Value of the switch ``nonresearch`` (``to_c`` or ``off``)."""
    value = (cfg.get("nonresearch") or {}).get("value", "to_c")
    if value not in NONRESEARCH_VALUES:
        raise ValueError(f"nonresearch.value must be one of {NONRESEARCH_VALUES}, not {value!r}")
    return value


def kanal_x_switch(reg_cfg):
    """Value of the switch ``kanal_x`` (``flag_only`` or ``exclude``)."""
    value = (reg_cfg.get("kanal_x") or {}).get("value", "flag_only")
    if value not in KANAL_X_VALUES:
        raise ValueError(f"kanal_x.value must be one of {KANAL_X_VALUES}, not {value!r}")
    return value


def tier_membership(cfg):
    """``{tier: membership}`` in the set of serious venues (``tier_membership``).

    ``no_venue.membership``, when given, must agree with the ``unknown`` value.
    """
    values = {str(k): float(v) for k, v in ((cfg.get("tier_membership") or {}).get("values") or {}).items()}
    if set(values) != {"A", "B", "C", "unknown"}:
        raise ValueError(f"tier_membership.values must give A, B, C and unknown, not {sorted(values)}")
    nv = (cfg.get("no_venue") or {}).get("membership")
    if nv is not None and float(nv) != values["unknown"]:
        raise ValueError(f"no_venue.membership {nv} differs from tier_membership.unknown {values['unknown']}")
    return values


def alpha(cfg):
    """The alpha-cut: a work is in the crisp REL set when its membership >= alpha."""
    return float((cfg.get("alpha") or {})["value"])


def unknown_switch(cfg):
    """Value of the switch ``no_venue`` (``keep_flagged`` or ``exclude``)."""
    value = (cfg.get("no_venue") or {}).get("value", "keep_flagged")
    if value not in NO_VENUE_VALUES:
        raise ValueError(f"no_venue.value must be one of {NO_VENUE_VALUES}, not {value!r}")
    return value


def exclusion_registries(cfg):
    """Registries whose hit excludes a work: ``exclusion.exclude`` (switch a),
    plus ``kanalregisteret`` when ``kanal_x`` (switch a') is ``exclude``."""
    listed = set((cfg.get("exclusion") or {}).get("exclude") or [])
    if "kanalregisteret" in listed:
        raise ValueError("set Kanalregisteret exclusion with the kanal_x switch, not exclusion.exclude")
    if kanal_x_switch(cfg) == "exclude":
        listed.add("kanalregisteret")
    return sorted(listed)


def exclusion_of(flags, exclude):
    """Registries among ``flags`` that exclude, sorted and joined by ``;``.

    A title match never excludes: two journals can share a title (Wiley's and
    another "Sustainable Development"), so it stays a flag to read by hand.
    """
    return ";".join(sorted({f["registry"] for f in flags if f["match"] != "title"} & set(exclude)))


def _repec_hit(codes, repec_key):
    """True when ``repec:<a>:<s>`` matches an archive code or ``a:s`` pair."""
    if not repec_key:
        return False
    a_s = repec_key[len("repec:"):]
    archive = a_s.split(":", 1)[0]
    return any(c == archive or c == a_s for c in codes)


def _any(rxs, texts):
    return any(rx.search(t) for rx in rxs for t in texts if t)


# ── Tier ─────────────────────────────────────────────────


def assign_tier(v, tiers):
    """``(tier, tier_rule, b_id)`` of a venue record.

    ``v`` keys: ``key``, ``name``, ``hosts`` (host organization, lineage,
    publisher names), ``source_id``, ``source_type``, ``issns``, ``repec``
    (``repec:a:s`` or ""), ``repec_template``, ``record_prefixes``,
    ``toc_journal`` (bool), ``declared_journal`` (bool).
    """
    names = [fold(v.get("name"))]
    hosts = [fold(h) for h in v.get("hosts") or []]
    repec = v.get("repec") or ""
    for e in tiers["b"]:
        if _repec_hit(e["repec"], repec) or _any(e["series"], names):
            return "B", "b_series", e["id"]
    journal_typed = v.get("source_type") in tiers["journal_types"] or bool(v.get("toc_journal"))
    # A repository name pattern never overrides a journal type: "REPeC" and
    # "Compra Journal of Economics" are journals whose names hold "repec", "mpra".
    if (v.get("source_type") in tiers["repo_types"] or _repec_hit(tiers["repo_repec"], repec)
            or (not journal_typed and _any(tiers["repo_names"], names))):
        # A repository can still be a B institution's own (World Bank OKR),
        # by its own name: its host is not evidence (RePEc's host is a Fed).
        for e in tiers["b"]:
            if _any(e["names"], names):
                return "B", "b_institution", e["id"]
        return "C", "repository", ""
    if (v.get("source_type") in tiers["journal_types"] or v.get("toc_journal")
            or v.get("repec_template") == "redif-article" or v.get("declared_journal")):
        return "A", "journal", ""
    prefixes = set(v.get("record_prefixes") or [])
    issns = set(v.get("issns") or [])
    for e in tiers["b"]:
        if (_any(e["names"], names + hosts) or prefixes & set(e["record_prefix"])
                or (v.get("source_id") and v["source_id"] in e["openalex"]) or issns & e["issn"]):
            return "B", "b_institution", e["id"]
    return "C", "other", ""


def b_by_domain(urls, tiers):
    """Id of the B entry whose domain hosts one of ``urls``, else ``""``.

    A host matches a domain it equals or sits under (``files.wri.org`` is
    ``wri.org``); a domain written ``=host`` matches that host only
    (``=fao.org`` keeps out ``agris.fao.org``, FAO's index of third-party
    records). Entries are tried in list order, so the first wins.
    """
    return b_by_domain_url(urls, tiers)[0]


def _host_match(host, domain):
    if domain.startswith("="):
        return host == domain[1:]
    return host == domain or host.endswith("." + domain)


def b_by_domain_url(urls, tiers):
    """``(b_id, url)``: the B entry whose domain hosts one of ``urls`` and that URL."""
    for e in tiers["b"]:
        for d in e.get("domains") or []:
            for u in sorted(urls):
                if _host_match(host_of(u), d):
                    return e["id"], u
    return "", ""


def is_nonresearch(url, tiers):
    """True when ``url`` matches a pattern of the non-research list (switch d)."""
    return any(rx.search(url) for rx in tiers["nonresearch"])


def publisher_flag(v, tiers):
    """Id of the flagged publisher (MDPI, Frontiers, Hindawi) of a venue, else ``""``."""
    hosts = [fold(h) for h in v.get("hosts") or []]
    for p in tiers["publishers"]:
        if _any(p["names"], hosts) or _repec_hit(p["repec"], v.get("repec") or ""):
            return p["id"]
    return ""


# ── Registry flags ───────────────────────────────────────


class RegistryIndex:
    """ISSN, title and domain indexes over registry entries of one pull."""

    def __init__(self, entries, pull_date):
        self.pull_date = pull_date
        self.by_issn, self.by_title, self.by_domain = {}, {}, {}
        title_count = Counter()
        for e in entries:
            if e["registry"] == "hijacked":
                self.by_domain.setdefault(e["domain"], []).append(e)
                continue
            for i in e["issns"]:
                self.by_issn.setdefault(i, []).append(e)
            t = name_key(e["title"])
            if len(t.split()) >= 2:
                title_count[(e["registry"], t)] += 1
                self.by_title.setdefault(t, []).append(e)
        # A title that names two entries of one registry is ambiguous: drop it.
        self.by_title = {t: [e for e in es if title_count[(e["registry"], t)] == 1]
                         for t, es in self.by_title.items()}

    def _flag(self, e, match):
        return {"registry": e["registry"], "entry_id": e["entry_id"], "match": match,
                "pull_date": self.pull_date, "entry_url": e["entry_url"], "reason": e["reason"],
                "levels": e.get("levels") or {}, "last_year": e.get("last_year")}

    def venue_flags(self, issns, name):
        """Flags of a venue, one per (registry, entry), sorted."""
        out = {}
        for i in sorted(issns):
            for e in self.by_issn.get(i, []):
                out.setdefault((e["registry"], e["entry_id"]), self._flag(e, "issn"))
        if not issns:
            for e in self.by_title.get(name_key(name), []):
                out.setdefault((e["registry"], e["entry_id"]), self._flag(e, "title"))
        return [out[k] for k in sorted(out)]

    def work_flags(self, urls):
        """Hijacked-checker flags of one work: any of its URLs on a clone host."""
        if isinstance(urls, str):
            urls = [urls]
        out = {}
        for host in sorted({host_of(u) for u in urls} - {""}):
            for e in self.by_domain.get(host, []):
                out.setdefault(e["entry_id"], self._flag(e, "domain"))
        return [out[k] for k in sorted(out)]


def work_venue_flags(venue_flags, year):
    """The venue's flags that apply to a work of ``year``.

    A Kanalregisteret flag applies only when the journal's level for the
    work's year is X (``_rel_venue_registries.level_at``); the other
    registries carry no year and apply to every work of the venue.
    """
    return [f for f in venue_flags
            if f["registry"] != "kanalregisteret" or level_at(f["levels"], year, f["last_year"]) == "X"]


def flags_text(flags):
    """Flags as one cell: ``registry:entry_id[match]`` joined by ``;``."""
    return ";".join(f"{f['registry']}:{f['entry_id']}[{f['match']}]" for f in flags)


# ── Loader for the REL view (ticket 1843) ────────────────


def load_work_venues(path, no_venue="keep_flagged"):
    """``{work_key: row}`` of ``rel_work_venues.csv``.

    ``flagged`` and ``excluded`` become bools; ``unknown`` is tier ``unknown``
    (no resolvable venue). ``tier_included`` is tier A or B, or ``unknown``
    when ``no_venue`` (switch c, ``unknown_switch``) is ``keep_flagged``;
    ``included`` is ``tier_included and not excluded``. Switches a and b are
    those the table was built with. Any other setting is recomputed from
    ``flags`` (``registry:entry_id[match]``; skip ``[title]`` matches, which never
    exclude) and ``tier_ngo_in_b`` / ``tier_ngo_not_b``.
    """
    out = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            r["flagged"] = r["flagged"] == "true"
            r["excluded"] = r["excluded"] == "true"
            r["unknown"] = r["tier"] == "unknown"
            r["tier_included"] = r["tier"] in ("A", "B") or (r["unknown"] and no_venue == "keep_flagged")
            r["included"] = r["tier_included"] and not r["excluded"]
            out[r["work_key"]] = r
    return out
