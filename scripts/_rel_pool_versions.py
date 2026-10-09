"""Step 5 of pool dedup version 2: a working paper and its article are one work (ticket 2048).

Author decision of 2026-10-09: a working paper (or preprint) and its published
article are ONE work. Version 1 does not have this step; ``_rel_pool_dedup``
runs it last in version 2, on the components steps 1 to 4 left.

Kinds of rows:

- **working paper**: a DOI of a working-paper or preprint registrar (SSRN
  10.2139, Research Square 10.21203, NBER 10.3386, Zenodo 10.5281, OSF
  10.31219 and 10.31235, arXiv 10.48550), or a ``doc_type`` naming a working
  paper, preprint, report, discussion paper or posted content. A RePEc
  series is a working paper through the ``doc_type`` its lane gives (the
  ReDIF template, ``working-paper`` in the RePEc mirror lane): the handle
  string itself does not say which template it is;
- **published**: any other row with a DOI, an OpenAlex id or a ``doc_type``;
- neither: a row with no identifier and no type (title-only rows, id-less
  catalogue rows). It never makes a version join.

A component is *published* when it holds a published row, *working paper
only* when it holds working-paper rows and no published row.

5a. **Explicit links.** A row's ``version_hint`` names other versions of the
    same work (``;`` or space separated): a DOI, an OpenAlex id, or a
    ``record_id`` of the same lane (lane 1651 writes its ``version_link`` as
    ``1651-<ref>``, lane 1650 its alias DOIs). A hint that resolves to exactly
    one component joins it, whatever the titles, years or DOIs: the lane
    asserted the link (the Gavard-Schoch pair, ZEW 2021 and the 2026 article,
    differ in title and are five years apart).
5b. **Title and window.** A working-paper-only component joins a published
    component when a working-paper row of the one and a published row of the
    other share the title key of the version (not a generic title) and the
    article year minus the working-paper year, earliest against earliest, is
    in ``WINDOW`` (-1 to +5 years, author decision of 2026-10-09). The
    accepted pairs are then taken as clusters: a cluster holding two
    published components (a working paper that fits two different articles)
    joins nothing, so no work gains the DOIs of two published versions.
    Two working papers join only through a published component.

Translations are out of scope (titles differ: She, Wu & Pan 2020 in Chinese
and Wu, Pan & She 2021 in English stay two works unless a lane links them).

Every decision reads the components and is applied at once, so the result
does not depend on row order.
"""

import re
from collections import defaultdict

from _rel_pool_keys import is_generic_title, norm_openalex
from utils import normalize_doi

# Article year minus working-paper year (author decision 2026-10-09).
WINDOW = (-1, 5)
WP_DOI_PREFIXES = ("10.2139/", "10.21203/", "10.3386/", "10.5281/", "10.31219/",
                   "10.31235/", "10.48550/")
WP_TYPE = re.compile(r"working[\s_-]*paper|preprint|report|posted[\s_-]*content"
                     r"|discussion[\s_-]*paper", re.IGNORECASE)


def is_working_paper(row):
    """A row of a working-paper or preprint registrar, or typed as one."""
    return ((row.get("doi") or "").startswith(WP_DOI_PREFIXES)
            or bool(WP_TYPE.search(row.get("doc_type") or "")))


def is_published(row):
    """Any row with an identifier or a type that is not a working paper."""
    return not is_working_paper(row) and bool(
        row.get("doi") or row.get("openalex_id") or (row.get("doc_type") or "").strip())


def _hints(row):
    """(kind, value) pointers of a row's ``version_hint``."""
    for tok in re.split(r"[;\s]+", row.get("version_hint") or ""):
        tok = tok.strip()
        if not tok:
            continue
        doi = normalize_doi(tok[4:] if tok.lower().startswith("doi:") else tok)
        if doi.startswith("10."):
            yield "doi", doi
        elif norm_openalex(tok):
            yield "openalex", norm_openalex(tok)
        else:
            yield "record", (row.get("origin", ""), tok)


def _bare_record_id(row):
    """A lane row's own ``record_id`` (``<lane>/<delivery>:<id>`` minus the prefix)."""
    rid = row.get("record_id", "")
    return rid.split(":", 1)[1] if ":" in rid else rid


def _hint_unions(rows, idx, uf):
    """Step 5a: ((hinting row, target row) pairs, hints resolved, unresolved)."""
    index = defaultdict(set)
    for i in idx:
        r = rows[i]
        if r.get("doi"):
            index["doi", r["doi"]].add(i)
        if r.get("openalex_id"):
            index["openalex", r["openalex_id"]].add(i)
        if r.get("record_id"):
            index["record", (r.get("origin", ""), _bare_record_id(r))].add(i)
    unions, resolved, unresolved = [], 0, 0
    for i in idx:
        for hint in _hints(rows[i]):
            hits = index.get(hint, ())
            if len({uf.find(j) for j in hits}) != 1:
                unresolved += 1
                continue
            resolved += 1
            unions.append((i, min(hits)))
    return unions, resolved, unresolved


def _kinds_by_key(rows, idx, uf, norm, words):
    """Working-paper and published components, and per title key the
    (year, row) of each component's working-paper and published rows."""
    published, wp = set(), set()
    by_key = defaultdict(lambda: defaultdict(lambda: {"wp": [], "pub": []}))
    for i in idx:
        r = rows[i]
        kind = "wp" if is_working_paper(r) else "pub" if is_published(r) else ""
        if not kind:
            continue
        c = uf.find(i)
        (wp if kind == "wp" else published).add(c)
        key = norm(r["title"] or "")
        if key and r.get("year") and not is_generic_title(words(r["title"])):
            by_key[key][c][kind].append((int(r["year"]), i))
    return wp - published, published, by_key


def _window_edges(wp_only, published, by_key, stats):
    """Step 5b pairs (working-paper-only, published component) -> pair info."""
    edges = {}
    for key in sorted(by_key):
        comps = by_key[key]
        pubs = [c for c in comps if c in published and comps[c]["pub"]]
        for w in (c for c in comps if c in wp_only and comps[c]["wp"]):
            wy, wi = min(comps[w]["wp"])
            for p in pubs:
                py, pi = min(comps[p]["pub"])
                if not WINDOW[0] <= py - wy <= WINDOW[1]:
                    stats["pairs_out_of_window"] += 1
                    continue
                edges.setdefault((w, p), {"kind": "window", "a_row": wi, "b_row": pi,
                                          "gap": py - wy, "key": key})
    return edges


def _refused(edges):
    """Cluster of each pair, and the clusters that hold two published components."""
    parent = {}

    def find(c):
        parent.setdefault(c, c)
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c

    for w, p in edges:
        parent[find(w)] = find(p)
    pubs = defaultdict(set)
    for _, p in edges:
        pubs[find(p)].add(p)
    return find, {root for root, ps in pubs.items() if len(ps) > 1}


def version_unions(rows, uf, norm, words, idx=None, pairs=None):
    """Step 5 on ``rows`` (those in ``idx``, default all) and union-find ``uf``.

    Applies the unions to ``uf`` and returns the step counts. ``pairs``, a
    list, receives one dict per union: ``kind`` ``link`` (5a; ``a_row`` the
    hinting row, ``b_row`` the row it names, ``key`` the hint) or ``window``
    (5b; ``a_row`` the working-paper row, ``b_row`` the published row, ``gap``
    the article year minus the working-paper year, ``key`` the title key).
    """
    idx = range(len(rows)) if idx is None else list(idx)
    hint_edges, resolved, unresolved = _hint_unions(rows, idx, uf)
    stats = {"hints_resolved": resolved, "hints_unresolved": unresolved, "hint_unions": 0,
             "pairs_in_window": 0, "pairs_out_of_window": 0, "pairs_refused": 0,
             "clusters_refused": 0, "pairs_accepted": 0}
    for a, b in hint_edges:
        if uf.find(a) == uf.find(b):
            continue
        stats["hint_unions"] += 1
        uf.union(a, b)
        if pairs is not None:
            pairs.append({"kind": "link", "a_row": a, "b_row": b, "gap": "", "key": ""})
    edges = _window_edges(*_kinds_by_key(rows, idx, uf, norm, words), stats)
    find, refused = _refused(edges)
    stats.update(pairs_in_window=len(edges), clusters_refused=len(refused))
    for (w, p), info in edges.items():
        if find(w) in refused:
            stats["pairs_refused"] += 1
            continue
        stats["pairs_accepted"] += 1
        uf.union(w, p)
        if pairs is not None:
            pairs.append(info)
    return stats


def recall_on_known(rows, members, id_field, norm, words, union_find):
    """Whether step 5 alone rebuilds works that hold several DOIs (or OpenAlex ids).

    ``members``: lists of row indices, one per known multi-version work. The
    rows of each work are cut into one part per value of ``id_field`` (rows
    without it dropped) and step 5 runs on those parts alone. Returns
    ``{"works", "rejoined", "missed_by_reason"}``; a miss is explained by the
    first of: ``no_working_paper`` (every part published), ``title_differs``,
    ``out_of_window``, ``two_published`` (the cluster veto), ``other``.
    """
    out = {"works": 0, "rejoined": 0, "missed_by_reason": defaultdict(int), "missed": []}
    for mem in members:
        sub = [rows[i] for i in mem if rows[i].get(id_field)]
        uf = union_find(len(sub))
        first = {}
        for k, r in enumerate(sub):
            uf.union(first.setdefault(r[id_field], k), k)
        out["works"] += 1
        stats = version_unions(sub, uf, norm, words)
        if len({uf.find(k) for k in range(len(sub))}) == 1:
            out["rejoined"] += 1
            continue
        wp_keys = {norm(r["title"] or "") for r in sub if is_working_paper(r)}
        pub_keys = {norm(r["title"] or "") for r in sub if is_published(r)}
        if not wp_keys:
            why = "no_working_paper"
        elif stats["clusters_refused"]:
            why = "two_published"
        elif stats["pairs_out_of_window"]:
            why = "out_of_window"
        elif not wp_keys & pub_keys:
            why = "title_differs"
        else:
            why = "other"
        out["missed_by_reason"][why] += 1
        out["missed"].append({"reason": why, "record_ids": [r["record_id"] for r in sub]})
    out["missed_by_reason"] = dict(sorted(out["missed_by_reason"].items()))
    out["recall"] = out["rejoined"] / out["works"] if out["works"] else None
    return out


PAIR_SIDE_FIELDS = ("record_id", "title", "year", "first_author", "journal", "doi",
                    "openalex_id", "doc_type", "abstract")
PAIR_COLUMNS = (["pair_id", "kind", "gap", "key"]
                + [f"{side}_{f}" for side in ("a", "b") for f in PAIR_SIDE_FIELDS])
ABSTRACT_CHARS = 400


def pair_records(rows, pairs):
    """One flat record per step-5 union, for the report and the precision panel.

    Each side is its row, blanks filled from the rows that share its DOI or
    OpenAlex id (the same record seen by several sources); the abstract is cut
    to ``ABSTRACT_CHARS``. Pair ids, ``L`` for a link and ``P`` for a window
    pair, number each kind in the order of its sorted record ids."""
    by_id = defaultdict(list)
    for i, r in enumerate(rows):
        if r.get("doi"):
            by_id["doi", r["doi"]].append(i)
        if r.get("openalex_id"):
            by_id["oa", r["openalex_id"]].append(i)

    def side(i):
        r = rows[i]
        same = sorted(set(by_id.get(("doi", r.get("doi")), ()))
                      | set(by_id.get(("oa", r.get("openalex_id")), ())))
        out = {f: r.get(f) or next((rows[j].get(f) for j in same if rows[j].get(f)), "")
               for f in PAIR_SIDE_FIELDS}
        out.update(record_id=r["record_id"], year=r.get("year", ""), doi=r.get("doi", ""),
                   openalex_id=r.get("openalex_id", ""), abstract=out["abstract"][:ABSTRACT_CHARS])
        return out

    keyed = sorted(pairs, key=lambda p: (p["kind"], rows[p["a_row"]]["record_id"],
                                         rows[p["b_row"]]["record_id"]))
    out, n = [], defaultdict(int)
    for p in keyed:
        a, b = side(p["a_row"]), side(p["b_row"])
        pid = f"{'L' if p['kind'] == 'link' else 'P'}{n[p['kind']]:05d}"
        n[p["kind"]] += 1
        out.append({"pair_id": pid, "kind": p["kind"], "gap": p["gap"], "key": p["key"],
                    **{f"a_{f}": a[f] for f in PAIR_SIDE_FIELDS},
                    **{f"b_{f}": b[f] for f in PAIR_SIDE_FIELDS}})
    return out
