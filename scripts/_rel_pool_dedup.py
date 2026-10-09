"""The REL pool deduplication cascade: one union-find over all rows (1731, 1655, 2047).

Two versions, chosen by ``dedup_version`` (``config/rel_pool.yaml``,
``corpus_rel_pool --dedup-version``). **Version 1 is the default** and the
only one that builds the pool; version 2 is computed beside it for a report
and a migration table (ticket 2047) until ticket 2048 switches the pool.

The cascade:

1. same normalized DOI;
2. same OpenAlex id (transitive: a record whose DOI matches one work and whose
   OpenAlex id matches another joins the two);
2b. same Handle key (``_rel_pool_keys.handle_key``), joining only components
   whose DOIs and OpenAlex ids do not disagree, even through a chain;
2c. version 2 only: same RePEc handle (``_rel_pool_keys.repec_key``, exact
   equality of the lowercased handle), with the chain protection of 2b;
3. same normalized title and same year, decided on the components steps 1-2c
   left: the rows join when their identifier-bearing rows form at most one
   component, or components that cannot disagree (one with DOIs only, one
   with OpenAlex ids only). When two components both carry DOIs (or both
   OpenAlex ids) the title is **ambiguous**: nothing joins them, and rows with
   neither join only one another. A URL never vetoes a join (one work often
   has several), and a title never joins across years;
4. rows a lane listed as ``no_dedup_key`` (title only) join the one component
   whose rows carry the same normalized title, any year. Several such
   components: ambiguous, the row stays out. A generic title
   (``is_generic_title``) never joins: the row stays its own work.

The normalized title of steps 3 and 4 is ``utils.normalize_title`` in version
1 (lower-case, every character but letters, digits, ``_`` and spaces deleted)
and ``_rel_title_key.title_key`` in version 2 (entities unescaped, tags
stripped, NFKC, Latin accents folded, apostrophes deleted, hyphens and other
punctuation to space; see that module).

Working papers and articles. In both versions a working paper and its article
that carry their own DOIs stay two works, unless a shared OpenAlex record joins
them (step 2). The author decided on 2026-10-09 that a working paper and its
published article are ONE work; that rule is ticket 2048 and is not coded here.

Every step decides on the components the previous steps left and applies its
unions at once, so the result does not depend on row order.
"""

from collections import defaultdict

from _rel_pool_keys import is_generic_title
from _rel_title_key import title_key
from utils import normalize_title

DEDUP_VERSIONS = (1, 2)


def title_normalizer(version):
    """The title normalizer of a dedup version."""
    check_version(version)
    return normalize_title if version == 1 else title_key


def check_version(version):
    if version not in DEDUP_VERSIONS:
        raise ValueError(f"dedup_version {version!r} is not one of {DEDUP_VERSIONS}")


def keys_of(row, norm=normalize_title):
    """(doi, openalex_id, title|year) keys of a normalized row; blanks omitted."""
    title = norm(row["title"])
    return (row["doi"], row["openalex_id"],
            f"{title}|{row['year']}" if title and row["year"] else "")


def compatible(a, b):
    """Two rows whose DOIs and OpenAlex ids do not disagree (a URL never does)."""
    return not ((a["doi"] and b["doi"] and a["doi"] != b["doi"])
                or (a["openalex_id"] and b["openalex_id"]
                    and a["openalex_id"] != b["openalex_id"]))


class UnionFind:
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


def _handle_unions(rows, uf, groups):
    """Steps 2b and 2c: Handle (or RePEc handle) unions that join no two DOIs and no two OpenAlex ids.

    A group whose components carry at most one DOI and one OpenAlex id joins
    whole; otherwise only its identifier-less components join one another.
    The accepted edges are then taken as clusters: a cluster that would still
    gather two DOIs (or two OpenAlex ids) through a chain keeps only its
    identifier-less edges.
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
    for group in groups:
        comps = sorted({uf.find(i) for i in group})
        if not consistent(comps):
            comps = [c for c in comps if idless(c)]
        edges += [(comps[0], c) for c in comps[1:]]
    clusters = UnionFind(len(rows))
    for a, b in edges:
        clusters.union(a, b)
    members = defaultdict(set)
    for a, b in edges:
        members[clusters.find(a)].update((a, b))
    ok = {root for root, comps in members.items() if consistent(comps)}
    return [(a, b) for a, b in edges
            if clusters.find(a) in ok or (idless(a) and idless(b))]


def _title_unions(rows, uf, group):
    """Step 3 for one title + year group: the pairs to join, and whether ambiguous."""
    def ident(i):
        return (bool(rows[i]["doi"]), bool(rows[i]["openalex_id"]))

    free = [i for i in group if not any(ident(i))]
    comps = defaultdict(lambda: [False, False])
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


def _title_only_unions(rows, uf, norm=normalize_title):
    """Step 4; returns (ambiguous rows, generic-title rows kept apart)."""
    by_title = defaultdict(set)
    title_only = defaultdict(list)
    for i, r in enumerate(rows):
        t = norm(r["title"])
        if not t:
            continue
        if r.get("title_only"):
            title_only[t].append(i)
        else:
            by_title[t].add(uf.find(i))
    pending, ambiguous, generic = [], 0, 0
    for t, idx in title_only.items():
        if is_generic_title(t):
            generic += len(idx)
            continue
        comps = by_title.get(t, set())
        if len(comps) == 1:
            target = next(iter(comps))
            pending += [(target, i) for i in idx]
        else:
            ambiguous += len(idx) if comps else 0
            pending += [(idx[0], i) for i in idx[1:]]
    for i, j in pending:
        uf.union(i, j)
    return ambiguous, generic


def _index(rows, norm, repec):
    """Row indices by DOI, OpenAlex id, Handle, RePEc handle (if used) and title|year."""
    by_doi, by_oa, by_handle, by_repec, by_title = (defaultdict(list) for _ in range(5))
    for i, r in enumerate(rows):
        doi, oa, ty = keys_of(r, norm)
        if doi:
            by_doi[doi].append(i)
        if oa:
            by_oa[oa].append(i)
        if r.get("handle"):
            by_handle[r["handle"]].append(i)
        if repec and r.get("repec"):
            by_repec[r["repec"]].append(i)
        if ty:
            by_title[ty].append(i)
    return by_doi, by_oa, by_handle, by_repec, by_title


def cluster(rows, stats=None, version=1):
    """Component root index per row under dedup ``version`` (default 1).

    ``stats`` (a dict) receives the step counts: ``ambiguous_title_groups``,
    ``ambiguous_title_only``, ``generic_title_only``."""
    return cluster_with(rows, stats, title_normalizer(version), repec=version >= 2)


def cluster_with(rows, stats, norm, repec):
    """The cascade with a given title normalizer, with or without step 2c.

    ``cluster`` names the two versions; the version 2 report also runs the
    mixed variants to tell which change causes a merge."""
    uf = UnionFind(len(rows))
    by_doi, by_oa, by_handle, by_repec, by_title = _index(rows, norm, repec)
    for group in list(by_doi.values()) + list(by_oa.values()):
        for j in group[1:]:
            uf.union(group[0], j)
    for i, j in _handle_unions(rows, uf, by_handle.values()):
        uf.union(i, j)
    if repec:
        for i, j in _handle_unions(rows, uf, by_repec.values()):
            uf.union(i, j)
    pending, ambiguous = [], 0
    for group in by_title.values():
        if len(group) > 1:
            pairs, amb = _title_unions(rows, uf, group)
            pending += pairs
            ambiguous += amb
    for i, j in pending:
        uf.union(i, j)
    ambiguous_title_only, generic = _title_only_unions(rows, uf, norm)
    if stats is not None:
        stats.update(ambiguous_title_groups=ambiguous, ambiguous_title_only=ambiguous_title_only,
                     generic_title_only=generic)
    return [uf.find(i) for i in range(len(rows))]
