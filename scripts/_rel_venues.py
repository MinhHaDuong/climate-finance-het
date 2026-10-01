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

**Flags**: a registry entry flags a venue whose ISSNs include one of the
entry's ISSNs (``match=issn``), or, for a venue with no ISSN at all, whose
folded name equals the entry's title when that title has two words or more and
is unique in its registry (``match=title``). A hijacked-checker entry flags a
work whose landing-page host is the clone's domain (``match=domain``).

**Switches** (both pending author decisions, ticket 1841): a flag from a
registry listed in ``exclusion.exclude`` (``rel_venue_registries.yaml``)
sets ``excluded``; the others only flag. ``ngo_research_in_b``
(``rel_venue_tiers.yaml``) selects which of the two computed tiers,
``tier_ngo_in_b`` or ``tier_ngo_not_b``, is the ``tier``.
"""

import csv
import re
import unicodedata
from collections import Counter

from _rel_venue_registries import host_of, norm_issn

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
    rep = cfg.get("repositories") or {}
    return {
        "version": cfg["version"], "b": b,
        "repo_types": set(rep.get("types") or []), "repo_names": _rx(rep.get("names")),
        "repo_repec": [str(x).lower() for x in rep.get("repec") or []],
        "journal_types": set(cfg.get("journal_types") or ["journal"]),
        "journal_doc_types": {fold(x) for x in cfg.get("journal_doc_types") or []},
        "publishers": [{"id": p["id"], "names": _rx(p.get("names")),
                        "repec": [str(x).lower() for x in p.get("repec") or []]}
                       for p in cfg.get("publisher_flags") or []],
    }


def without_categories(tiers, categories):
    """A copy of compiled ``tiers`` whose B list drops the given categories."""
    return dict(tiers, b=[e for e in tiers["b"] if e["category"] not in set(categories)])


def ngo_switch(cfg):
    """Value of the pending switch ``ngo_research_in_b`` (default ``True``)."""
    return bool((cfg.get("ngo_research_in_b") or {}).get("value", True))


def exclusion_registries(cfg):
    """Registries whose hit excludes a venue (switch ``exclusion.exclude``)."""
    return sorted((cfg.get("exclusion") or {}).get("exclude") or [])


def exclusion_of(flags, exclude):
    """Registries among ``flags`` that exclude, sorted and joined by ``;``."""
    return ";".join(sorted({f["registry"] for f in flags} & set(exclude)))


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
    if (v.get("source_type") in tiers["repo_types"] or _any(tiers["repo_names"], names)
            or _repec_hit(tiers["repo_repec"], repec)):
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
                "pull_date": self.pull_date, "entry_url": e["entry_url"], "reason": e["reason"]}

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

    def work_flags(self, landing_url):
        """Hijacked-checker flags of one work, by landing-page host."""
        host = host_of(landing_url)
        return [self._flag(e, "domain") for e in sorted(self.by_domain.get(host, []),
                                                         key=lambda e: e["entry_id"])]


def flags_text(flags):
    """Flags as one cell: ``registry:entry_id[match]`` joined by ``;``."""
    return ";".join(f"{f['registry']}:{f['entry_id']}[{f['match']}]" for f in flags)


# ── Loader for the REL view (ticket 1843) ────────────────


def load_work_venues(path):
    """``{work_key: row}`` of ``rel_work_venues.csv``.

    ``flagged`` and ``excluded`` become bools; ``tier_included`` is tier A or B
    and ``included`` is ``tier_included and not excluded``, both under the
    switches the table was built with. Any other setting is recomputed from
    ``flags`` (registry names) and ``tier_ngo_in_b`` / ``tier_ngo_not_b``.
    """
    out = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            r["flagged"] = r["flagged"] == "true"
            r["excluded"] = r["excluded"] == "true"
            r["tier_included"] = r["tier"] in ("A", "B")
            r["included"] = r["tier_included"] and not r["excluded"]
            out[r["work_key"]] = r
    return out
