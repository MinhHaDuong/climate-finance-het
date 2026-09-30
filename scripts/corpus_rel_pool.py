"""Build the REL pool: pinned catalogue + every lane delivery (ticket 1731).

Reads the pinned merged catalogue (``config/rel_pool.yaml`` → ``catalogue``;
refused unless its md5 and row count match) and every delivery under
``data/rel_intake/<lane>/<delivery>/`` that no other delivery supersedes. Each
delivery is checked against the intake contract (``qa_rel_intake``); one
failing delivery aborts the merge with its violations.

Deduplication is one union-find over all rows, catalogue and lanes alike:

1. same normalized DOI;
2. same OpenAlex id (the union is transitive: a record whose DOI matches one
   work and whose OpenAlex id matches another joins the two);
2b. same normalized ``url`` (``norm_url``: scheme and host lowercased,
   trailing slash dropped, ``hdl.handle.net/X`` and ``<host>/handle/X`` both
   ``hdl:X``, query and fragment dropped; under the unregistered DSpace
   default prefix ``123456789`` a repository Handle keeps its host,
   ``hdl:<host>/123456789/…``). A resolver URL is not a URL key: ``doi.org/…``
   fills an empty DOI and ``openalex.org/W…`` an empty OpenAlex id instead.
   A URL never overrides an identifier disagreement: it joins only rows whose
   components (after steps 1-2) carry no two DOIs and no two OpenAlex ids, a
   shared landing page such as a journal issue URL cannot fuse two DOIs;
3. same normalized title and same year, decided on the components steps 1-2b
   left: the rows sharing a title + year join when their identifier-bearing
   rows form at most one component, or components that cannot disagree (no
   identifier kind, DOI, OpenAlex id or URL, on both sides). When two
   components both carry DOIs (or both OpenAlex ids, or both URLs), the title
   is **ambiguous**: nothing joins them, and rows with no identifier join only
   one another. A working paper and
   its article with their own DOIs therefore stay two works, an id-less
   "Editorial" cannot fuse distinct DOIs, and a title never joins across
   years. Each row's ``version_hint`` is carried so the counting-unit decision
   (open, ticket 1655) can be applied later;
4. rows a lane listed in ``excluded.csv`` as ``no_dedup_key`` (a title known
   but no DOI, OpenAlex id or year in the source) stay in the pool as
   title-only works: each joins the one component whose rows carry the same
   normalized title (any year), and stays separate when several components
   do (counted as ambiguous) or none does. Unjoined, its ``work_key`` is
   ``title:<normalized title>|`` (empty year).

DOIs are compared as normalized strings, never resolved: a DOI field that is
not a well-formed ``10.xxxx/...`` DOI is kept and counted (``doi_malformed``).

Outputs (``--output-dir``, default ``data/rel_pool``):

- ``pool.csv``: one row per work. ``work_key`` is ``openalex:W…`` when a member
  carries an OpenAlex id, else ``doi:<doi>``, else ``url:<normalized url>``,
  else ``title:<title>|<year>``.
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
DOI = ric.DOI
CATALOGUE = "catalogue"
# Exclusion reason whose rows are kept in the pool as title-only works.
NO_DEDUP_KEY = "no_dedup_key"

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


_URL = re.compile(r"^(https?)://([^/?#\s]+)(\S*)$", re.IGNORECASE)
_HANDLE_PATH = re.compile(r"^/handle/(.+)$")
DOI_RESOLVERS = {"doi.org", "dx.doi.org", "www.doi.org"}
OPENALEX_HOSTS = {"openalex.org", "api.openalex.org"}


# DSpace's default local prefix: unregistered, reused by many repositories, so
# ``<host>/handle/123456789/X`` names X only on that host.
DSPACE_DEFAULT_PREFIX = "123456789"


def norm_url(v):
    """Normalized URL key, ``hdl:<handle>`` for a Handle, ``""`` if not http(s).

    A Handle URL drops its query string and fragment (``?show=full`` is a view
    of the same item). Under the DSpace default prefix a repository Handle
    keeps its host: ``hdl:<host>/123456789/X``.
    """
    m = _URL.match(str(v or "").strip())
    if not m:
        return ""
    scheme, host, path = m.group(1).lower(), m.group(2).lower(), m.group(3).rstrip("/")
    handle_path = re.split(r"[?#]", path, maxsplit=1)[0].rstrip("/")
    if host == "hdl.handle.net" and handle_path.strip("/"):
        return "hdl:" + handle_path.lstrip("/")
    hm = _HANDLE_PATH.match(handle_path)
    if hm:
        handle = hm.group(1)
        if handle.split("/", 1)[0] == DSPACE_DEFAULT_PREFIX:
            return f"hdl:{host}/{handle}"
        return "hdl:" + handle
    return f"{scheme}://{host}{path}"


def ids_from_url(raw, doi, openalex_id):
    """``(doi, openalex_id, url_key)`` once a resolver URL has filled its identifier."""
    m = _URL.match(str(raw or "").strip())
    host = m.group(2).lower() if m else ""
    if host in DOI_RESOLVERS:
        return doi or normalize_doi(raw), openalex_id, ""
    if host in OPENALEX_HOSTS:
        return doi, openalex_id or norm_openalex(raw), ""
    return doi, openalex_id, norm_url(raw)


def keys_of(row):
    """(doi, openalex_id, title|year) keys of a normalized row; blanks omitted."""
    title = normalize_title(row["title"])
    return (row["doi"], row["openalex_id"],
            f"{title}|{row['year']}" if title and row["year"] else "")


def _compatible(a, b):
    """Two rows that no identifier sets apart."""
    return not ((a["doi"] and b["doi"] and a["doi"] != b["doi"])
                or (a["openalex_id"] and b["openalex_id"]
                    and a["openalex_id"] != b["openalex_id"])
                or (a.get("url") and b.get("url") and a["url"] != b["url"]))


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


def _url_unions(rows, uf, url_groups):
    """Step 2b: URL unions that join no two DOIs and no two OpenAlex ids.

    Judged on the components steps 1-2 left, so row order does not matter. A
    URL group whose components carry at most one DOI and one OpenAlex id joins
    whole; otherwise only its identifier-less rows join one another. The
    accepted edges are then taken as clusters: a cluster that would still
    gather two DOIs (or two OpenAlex ids) through a chain of URLs keeps only
    its identifier-less edges.
    """
    ids = defaultdict(lambda: (set(), set()))
    for i, r in enumerate(rows):
        dois, oas = ids[uf.find(i)]
        if r["doi"]:
            dois.add(r["doi"])
        if r["openalex_id"]:
            oas.add(r["openalex_id"])

    def consistent(comps):
        return (len(set().union(*(ids[c][0] for c in comps))) <= 1
                and len(set().union(*(ids[c][1] for c in comps))) <= 1)

    def idless(c):
        return not (ids[c][0] or ids[c][1])

    edges = []
    for group in url_groups:
        comps = sorted({uf.find(i) for i in group})
        if not consistent(comps):
            comps = [c for c in comps if idless(c)]
        edges += [(comps[0], c) for c in comps[1:]]
    clusters = _UnionFind(len(rows))
    for a, b in edges:
        clusters.union(a, b)
    members = defaultdict(set)
    for a, b in edges:
        members[clusters.find(a)].update((a, b))
    ok = {root for root, comps in members.items() if consistent(comps)}
    return [(a, b) for a, b in edges
            if clusters.find(a) in ok or (idless(a) and idless(b))]


def _title_unions(rows, uf, group):
    """Unions one title + year group allows, judged on the identifier components.

    Returns the index pairs to join and whether the group was ambiguous.
    Distinct components never share a DOI, an OpenAlex id or a URL key (they
    would have joined), so two components disagree exactly when both carry
    an identifier of the same kind.
    """
    def ident(i):
        return (bool(rows[i]["doi"]), bool(rows[i]["openalex_id"]), bool(rows[i].get("url")))

    free = [i for i in group if not any(ident(i))]
    comps = defaultdict(lambda: [False, False, False])
    for i in group:
        if any(ident(i)):
            flags = comps[uf.find(i)]
            for k, has in enumerate(ident(i)):
                flags[k] |= has
    kinds = list(comps.values())
    ambiguous = any(any(x and y for x, y in zip(a, b))
                    for n, a in enumerate(kinds) for b in kinds[n + 1:])
    members = free if ambiguous else group
    return [(members[0], j) for j in members[1:]], ambiguous


def cluster(rows, stats=None):
    """Union-find over ``rows``: component root index per row.

    Steps 1-2 (DOI, OpenAlex id) join unconditionally; step 2b (URL key)
    joins only components no identifier sets apart. Step 3 decides every
    title + year group on the components steps 1-2 left, then applies all
    its unions at once, so the result does not depend on row order.
    ``stats`` (a dict), when given, receives ``ambiguous_title_groups``.
    """
    uf = _UnionFind(len(rows))
    by_doi, by_oa, by_url, by_title = (defaultdict(list), defaultdict(list),
                                       defaultdict(list), defaultdict(list))
    for i, r in enumerate(rows):
        doi, oa, ty = keys_of(r)
        if doi:
            by_doi[doi].append(i)
        if oa:
            by_oa[oa].append(i)
        if r.get("url"):
            by_url[r["url"]].append(i)
        if ty:
            by_title[ty].append(i)
    for group in list(by_doi.values()) + list(by_oa.values()):
        for j in group[1:]:
            uf.union(group[0], j)
    for i, j in _url_unions(rows, uf, by_url.values()):
        uf.union(i, j)
    pending, ambiguous = [], 0
    for group in by_title.values():
        if len(group) > 1:
            pairs, amb = _title_unions(rows, uf, group)
            pending += pairs
            ambiguous += amb
    for i, j in pending:
        uf.union(i, j)
    ambiguous_title_only = _title_only_unions(rows, uf)
    if stats is not None:
        stats["ambiguous_title_groups"] = ambiguous
        stats["ambiguous_title_only"] = ambiguous_title_only
    return [uf.find(i) for i in range(len(rows))]


def _title_only_unions(rows, uf):
    """Step 4: join each ``no_dedup_key`` row to the one component with its title.

    Candidates are the components (after steps 1-3) of the other rows whose
    normalized title is the same, whatever their year. One candidate: join.
    Several: ambiguous, the row stays out (rows of the same title join one
    another). Returns the number of ambiguous title-only rows.
    """
    by_title = defaultdict(set)
    title_only = defaultdict(list)
    for i, r in enumerate(rows):
        t = normalize_title(r["title"])
        if not t:
            continue
        if r.get("title_only"):
            title_only[t].append(i)
        else:
            by_title[t].add(uf.find(i))
    pending, ambiguous = [], 0
    for t, idx in title_only.items():
        comps = by_title.get(t, set())
        if len(comps) == 1:
            target = next(iter(comps))
            pending += [(target, i) for i in idx]
        else:
            ambiguous += len(idx) if comps else 0
            pending += [(idx[0], i) for i in idx[1:]]
    for i, j in pending:
        uf.union(i, j)
    return ambiguous


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
            **dict(zip(("doi", "openalex_id", "url"), ids_from_url(
                r.get("url"), normalize_doi(r.get("doi")), norm_openalex(r.get("source_id"))))),
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
    rows = []
    for r in _read_csv(os.path.join(path, "records.csv")):
        rows.append({
            "origin": did.split("/")[0], "delivery": did,
            "record_id": f"{did}:{r['record_id']}",
            **dict(zip(("doi", "openalex_id", "url"), ids_from_url(
                r.get("url"), normalize_doi(r.get("doi")), norm_openalex(r.get("openalex_id"))))),
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
                "doi": "", "openalex_id": "", "url": "", "year": "", "title": r["title"],
                **{c: "" for c in ("first_author", "all_authors", "journal", "abstract",
                                   "language", "doc_type", "affiliation_countries",
                                   "version_hint", "affiliations", "cited_by_count",
                                   "catalogue_source")},
                "title_only": True,
            })
    excluded = Counter(r.get("reason") for r in excl_rows)
    return rows, dict(sorted(excluded.items()))


# ── Pool ─────────────────────────────────────────────────


def _work_key(merged, url=""):
    if merged["openalex_id"]:
        return f"openalex:{merged['openalex_id']}"
    if merged["doi"]:
        return f"doi:{merged['doi']}"
    if url:
        return f"url:{url}"
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
        merged["work_key"] = _work_key(merged, next((m["url"] for m in mem if m.get("url")), ""))
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
    if row.get("url") and row["url"] in cat_index["url"]:
        return "by_url"
    if ty and any(_compatible(row, c) for c in cat_index["title"].get(ty, [])):
        return "by_title_year"
    return None


def _catalogue_index(rows):
    """Catalogue keys, for naming the method of a direct catalogue match."""
    index = {"doi": set(), "openalex_id": set(), "url": set(), "title": defaultdict(list)}
    for r in rows:
        if r["origin"] != CATALOGUE:
            continue
        doi, oa, ty = keys_of(r)
        if doi:
            index["doi"].add(doi)
        if oa:
            index["openalex_id"].add(oa)
        if r.get("url"):
            index["url"].add(r["url"])
        if ty:
            index["title"][ty].append(r)
    return index


def delivery_counts(did, idx, rows, roots, comp, cat_index):
    """Contract merge-report counts of one delivery.

    A delivery's works are the pool works its rows land in, so the counts
    always add up with the pool; ``dup_within_delivery`` counts rows that land
    in the same work as another row of the delivery. Each work is placed with
    a catalogue row (named by the first direct match method of the delivery's
    rows, cascade order; ``via_other_lane`` when only another lane's record
    bridges them), with another delivery only, or alone (``new_to_pool``).
    """
    drows = [rows[i] for i in idx if not rows[i].get("title_only")]
    title_only = [i for i in idx if rows[i].get("title_only")]
    works = defaultdict(list)
    for i in idx:
        works[roots[i]].append(i)
    in_cat = Counter({"by_doi": 0, "by_openalex_id": 0, "by_url": 0, "by_title_year": 0,
                      "via_other_lane": 0})
    other_lane_only = new = 0
    for root, members in works.items():
        full = comp[root]
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
        "doi_malformed": sum(bool(r["doi"]) and not DOI.match(r["doi"]) for r in drows),
        "with_openalex_id": sum(bool(r["openalex_id"]) for r in drows),
        "with_url": sum(bool(r.get("url")) for r in drows),
        "title_year_only": sum(not r["doi"] and not r["openalex_id"] and not r.get("url")
                               for r in drows),
        "title_only_from_excluded": len(title_only),
        "title_only_joined": sum(len(comp[roots[i]]) > 1 and any(
            not rows[j].get("title_only") for j in comp[roots[i]]) for i in title_only),
        "dup_within_delivery": len(idx) - len(works),
        "works": len(works),
        "in_catalogue": {"total": sum(in_cat.values()), **dict(in_cat)},
        "in_other_lane_only": other_lane_only,
        "new_to_pool": new,
    }


def make_report(rows, roots, deliveries, excluded, catalogue_meta, superseded, stats=None):
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
        "ambiguous_title_groups": (stats or {}).get("ambiguous_title_groups"),
        "ambiguous_title_only": (stats or {}).get("ambiguous_title_only"),
        "catalogue_doi_malformed": sum(r["origin"] == CATALOGUE and bool(r["doi"])
                                       and not DOI.match(r["doi"]) for r in rows),
    }
    checks = {
        "pool = catalogue works + lane-only works":
            recon["pool_works"] == recon["catalogue_works"] + recon["lane_only_works"],
        "sum of new_to_pool = lane-only works from a single delivery":
            sum(p["new_to_pool"] for p in per.values()) == recon["lane_only_works_single_delivery"],
        "works per n_sources sum to the pool": sum(n_sources.values()) == recon["pool_works"],
    }
    for did, p in per.items():
        checks[f"{did}: records + title_only_from_excluded - dup_within_delivery = works"] = (
            p["records"] + p["title_only_from_excluded"] - p["dup_within_delivery"] == p["works"])
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
        "notes": ("Per-delivery counts are per source, before cross-source deduplication: a "
                  "work two lanes found counts in both. "
                  "in_catalogue.via_other_lane: the delivery's work joins a catalogue work only "
                  "through another lane's record. already_screened and still_to_screen wait for "
                  "the icf_screen table (ticket 1732)."),
    }


def report_markdown(report):
    head = ["delivery", "records", "excluded", "title_only_from_excluded", "with_doi", "doi_malformed", "with_openalex_id",
            "title_year_only", "dup_within_delivery", "in_catalogue (doi/oa/url/title/via lane)",
            "in_other_lane_only", "new_to_pool"]
    lines = ["# REL pool merge report", "",
             f"Catalogue: `{report['catalogue']['path']}`, md5 `{report['catalogue']['md5']}`, "
             f"{report['catalogue']['rows']} rows.", "",
             "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for did, p in report["deliveries"].items():
        c = p["in_catalogue"]
        exc = ", ".join(f"{k} {v}" for k, v in p["excluded"].items()) or "0"
        lines.append("| " + " | ".join(map(str, [
            did, p["records"], exc, p["title_only_from_excluded"], p["with_doi"], p["doi_malformed"], p["with_openalex_id"], p["title_year_only"],
            p["dup_within_delivery"],
            f"{c['total']} ({c['by_doi']}/{c['by_openalex_id']}/{c['by_url']}/{c['by_title_year']}/"
            f"{c['via_other_lane']})",
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
    stats = {}
    roots = cluster(rows, stats)
    pool = build_pool(rows, roots, lane_rank)
    meta = {"path": os.path.relpath(catalogue_path, ROOT) if os.path.isabs(catalogue_path)
            else catalogue_path, "md5": md5, "rows": len(cat_rows), "run": cat_cfg.get("run")}
    report = make_report(rows, roots, deliveries, excluded, meta, superseded, stats)

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
