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

Which rows are free. In version 1, steps 3 and 4 look at each row's own
identifiers: a row with no DOI and no OpenAlex id counts as free even when step
2b already joined it to a component that carries one, so steps 2b then 3 can
still gather two DOIs or two OpenAlex ids in one work. This is live: version 1
joins OpenAlex W2065222064 with W3121726814, and W2217893324 with W3140695789.
Version 2 judges whole components in steps 3 and 4 (a component is free only
when none of its rows carries a DOI or an OpenAlex id; no two components that
both carry DOIs, or both OpenAlex ids, join, even through a chain), so in
version 2 no step after step 2 gathers two DOIs or two OpenAlex ids.

The normalized title of steps 3 and 4 is ``utils.normalize_title`` in version
1 (lower-case, every character but letters, digits, ``_`` and spaces deleted)
and ``_rel_title_key.title_key`` in version 2 (entities unescaped, tags
stripped, apostrophes deleted, NFKC, Latin accents folded, then letters, marks,
digits and currency signs only, no spaces; see that module). The generic-title
test of step 4 reads ``title_words``, the same title with its spaces.

5. version 2 only: a working paper and its published article are ONE work
   (author decision of 2026-10-09, ticket 2048; ``_rel_pool_versions``):
   5a. a lane's ``version_hint`` that resolves to one component joins it;
   5b. a working-paper-only component joins a published component with the
   same title key when the article year minus the working-paper year is
   between -1 and +5; a cluster that would hold two published components
   joins nothing.

Working papers and articles. In version 1 a working paper and its article that
carry their own DOIs stay two works, unless a shared OpenAlex record joins
them (step 2). Version 2 joins them by step 5; version 1 is still the default,
so the pool keeps them apart until ticket 2048 switches the version.

Every step decides on the components the previous steps left and applies its
unions at once, so the result does not depend on row order.
"""

from collections import defaultdict

from _rel_pool_keys import is_generic_title
from _rel_pool_versions import version_unions
from _rel_title_key import title_key, title_words
from utils import normalize_title

DEDUP_VERSIONS = (1, 2)
# The words form of a spaceless title key, for the generic-title test of step 4.
WORDS = {title_key: title_words}


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


def _component_ids(rows, uf):
    """Root -> (DOIs, OpenAlex ids) of every row of the component."""
    ids = defaultdict(lambda: (set(), set()))
    for i, r in enumerate(rows):
        dois, oas = ids[uf.find(i)]
        if r["doi"]:
            dois.add(r["doi"])
        if r["openalex_id"]:
            oas.add(r["openalex_id"])
    return ids


def _one_doi_one_openalex(ids, comps):
    """Steps 2b and 2c: together the components carry at most one DOI and one OpenAlex id."""
    return (len(set().union(*(ids[c][0] for c in comps))) <= 1
            and len(set().union(*(ids[c][1] for c in comps))) <= 1)


def _no_two_kinds(ids, comps):
    """Version 2, steps 3 and 4: no two components both carry DOIs, nor both OpenAlex ids."""
    return (sum(bool(ids[c][0]) for c in comps) <= 1
            and sum(bool(ids[c][1]) for c in comps) <= 1)


def _guarded_edges(rows, uf, groups, rule):
    """Unions within groups that never gather what ``rule`` forbids; (edges, refused groups).

    A group whose components pass ``rule`` joins whole; otherwise only its
    identifier-less components join one another. The accepted edges are then
    taken as clusters: a cluster that fails ``rule`` through a chain keeps only
    its identifier-less edges.
    """
    ids = _component_ids(rows, uf)

    def idless(c):
        return not (ids[c][0] or ids[c][1])

    edges, refused = [], 0
    for group in groups:
        comps = sorted({uf.find(i) for i in group})
        if not rule(ids, comps):
            refused += 1
            comps = [c for c in comps if idless(c)]
        edges += [(comps[0], c) for c in comps[1:]]
    clusters = UnionFind(len(rows))
    for a, b in edges:
        clusters.union(a, b)
    members = defaultdict(set)
    for a, b in edges:
        members[clusters.find(a)].update((a, b))
    ok = {root for root, comps in members.items() if rule(ids, comps)}
    return [(a, b) for a, b in edges
            if clusters.find(a) in ok or (idless(a) and idless(b))], refused


def _handle_unions(rows, uf, groups):
    """Steps 2b and 2c: Handle (or RePEc handle) unions that join no two DOIs
    and no two OpenAlex ids, even through a chain (``_guarded_edges``)."""
    return _guarded_edges(rows, uf, groups, _one_doi_one_openalex)[0]


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


def _title_only_unions(rows, uf, norm=normalize_title, guard=False):
    """Step 4; returns (ambiguous rows, generic-title rows kept apart).

    With ``guard`` (version 2) the joins go through ``_guarded_edges``: a
    title-only row whose component already carries a DOI or an OpenAlex id
    (through its RePEc handle) never brings a second one into the target."""
    words = WORDS.get(norm, norm)
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
    pending, groups, ambiguous, generic = [], [], 0, 0
    for t, idx in title_only.items():
        if is_generic_title(words(rows[idx[0]]["title"]) if words is not norm else t):
            generic += len(idx)
            continue
        comps = by_title.get(t, set())
        if len(comps) == 1:
            target = next(iter(comps))
            pending += [(target, i) for i in idx]
            groups.append([target] + idx)
        else:
            ambiguous += len(idx) if comps else 0
            pending += [(idx[0], i) for i in idx[1:]]
            groups.append(idx)
    if guard:
        pending = _guarded_edges(rows, uf, groups, _no_two_kinds)[0]
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


def cluster(rows, stats=None, version=1, pairs=None):
    """Component root index per row under dedup ``version`` (default 1).

    ``stats`` (a dict) receives the step counts: ``ambiguous_title_groups``,
    ``ambiguous_title_only``, ``generic_title_only``, and in version 2
    ``versions`` (step 5); ``pairs`` (a list) the unions of step 5."""
    v2 = version >= 2
    return cluster_with(rows, stats, title_normalizer(version), repec=v2, guard=v2, versions=v2,
                        pairs=pairs)


def cluster_with(rows, stats, norm, repec, guard=False, versions=False, pairs=None):
    """The cascade with a given title normalizer, with or without step 2c,
    the component guard of steps 3 and 4 and step 5 (``versions``; ``pairs``
    receives its unions, see ``version_unions``).

    ``cluster`` names the two versions; the version 2 report also runs each
    change alone on top of version 1 to tell which one causes a merge or a split."""
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
    if guard:
        pending, ambiguous = _guarded_edges(
            rows, uf, [g for g in by_title.values() if len(g) > 1], _no_two_kinds)
    else:
        for group in by_title.values():
            if len(group) > 1:
                pairs, amb = _title_unions(rows, uf, group)
                pending += pairs
                ambiguous += amb
    for i, j in pending:
        uf.union(i, j)
    ambiguous_title_only, generic = _title_only_unions(rows, uf, norm, guard)
    vstats = version_unions(rows, uf, norm, WORDS.get(norm, norm), pairs=pairs) if versions else None
    if stats is not None:
        stats.update(ambiguous_title_groups=ambiguous, ambiguous_title_only=ambiguous_title_only,
                     generic_title_only=generic)
        if vstats is not None:
            stats["versions"] = vstats
    return [uf.find(i) for i in range(len(rows))]
