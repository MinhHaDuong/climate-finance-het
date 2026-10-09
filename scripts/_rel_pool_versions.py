"""Step 5 of pool dedup version 2: versions of one work become one work (ticket 2048).

Author decision of 2026-10-09: a working paper (or preprint) and its published
article are ONE work, and the PUBLISHED article names it (``published_ids``).
Version 1 does not have this step; ``_rel_pool_dedup`` runs it last in version
2, on the components steps 1 to 4 left.

Kinds of rows:

- **working paper**: a DOI of a working-paper or preprint registrar (SSRN
  10.2139, Research Square 10.21203, NBER 10.3386, OSF 10.31219 and 10.31235,
  arXiv 10.48550), a repository DOI (Zenodo 10.5281, figshare 10.6084) whose
  type is not a dataset or software, or a type naming a working paper,
  preprint, report, discussion paper or posted content. The type is the row's
  ``doc_type``, else the one an enrichment table gives its DOI or OpenAlex id
  (``enriched_doc_type``, set by ``_rel_pool_enrich.mark_doc_types`` before
  clustering; ticket 2052). A RePEc series is a working paper through the
  ``doc_type`` its lane gives (the ReDIF template): the handle does not say;
- **published**: any other row with a DOI, an OpenAlex id or a type;
- neither: a row with no identifier and no type. It never makes a version join.

A component is *published* when it holds a published row, *working paper
only* when it holds working-paper rows and no published row.

5a. **Explicit links.** A row's ``version_hint`` names other versions of the
    same work (``;`` or space separated): a DOI, an OpenAlex id, or a
    ``record_id`` of the same lane (lane 1651 writes its ``version_link`` as
    ``1651-<ref>``, lane 1650 its alias DOIs). A hint that resolves to exactly
    one component joins it, whatever the titles, years or DOIs, two published
    DOIs of one article included (counted apart, ``hint_unions_two_published``).
5b. **Title and window.** A working-paper-only component joins a published
    component when a working-paper row of the one and a published row of the
    other share the title key of the version (not a generic title) and the
    article year minus the working-paper year, earliest against earliest, is
    in ``WINDOW`` (-1 to +5 years, author decision of 2026-10-09). A title of
    ``SHORT_TITLE_WORDS`` words or fewer also needs the first authors to agree
    (both known, a surname in common): 'Climate Change Governance', HAL 2022
    and CUP 2021, was a false merge. Clusters of accepted pairs holding two
    published components join nothing (chain veto).
5c. **Duplicate OpenAlex records** (author decision of 2026-10-09; switch
    ``openalex_duplicates``). An *OpenAlex-only* component carries OpenAlex
    ids and no DOI. Within a group of components sharing a title key of
    ``OA_MIN_WORDS`` words or more (not generic) and a year, the
    OpenAlex-only components join one another, and join the DOI-bearing
    component when there is exactly one; with two or more, they join none of
    them. Clusters of accepted pairs holding two DOI-bearing components join
    nothing, so a work never gains two DOIs or two published versions here.
    First authors are not read: mostly missing on these records.

Translations are out of scope. Every decision reads the components and is
applied at once, so the result does not depend on row order.
"""

import re
import unicodedata
from collections import defaultdict

from _rel_pool_keys import is_generic_title, norm_openalex
from utils import normalize_doi

# Article year minus working-paper year (author decision 2026-10-09).
WINDOW = (-1, 5)
WP_DOI_PREFIXES = ("10.2139/", "10.21203/", "10.3386/", "10.31219/", "10.31235/", "10.48550/")
# Zenodo, figshare: a working paper unless typed a dataset or software.
REPOSITORY_DOI_PREFIXES = ("10.5281/", "10.6084/")
NOT_A_PAPER = re.compile(r"data[\s_-]*set|software|computer[\s_-]*program", re.IGNORECASE)
WP_TYPE = re.compile(r"working[\s_-]*paper|preprint|report|posted[\s_-]*content"
                     r"|discussion[\s_-]*paper", re.IGNORECASE)
REPORT_ONLY = re.compile(r"report", re.IGNORECASE)
SHORT_TITLE_WORDS = 3
OA_MIN_WORDS = 4


def mark_type(row):
    """The type the marks read: the row's own, else the enrichment's."""
    return row.get("doc_type") or row.get("enriched_doc_type") or ""


def wp_marks(row):
    """Which marks make a row a working paper: ``doi``, ``repository``,
    ``report`` (a type naming a report and nothing else) or ``type``."""
    doi, t = row.get("doi") or "", mark_type(row)
    marks = set()
    if doi.startswith(WP_DOI_PREFIXES):
        marks.add("doi")
    if doi.startswith(REPOSITORY_DOI_PREFIXES) and not NOT_A_PAPER.search(t):
        marks.add("repository")
    m = WP_TYPE.findall(t)
    if m:
        marks.add("report" if all(REPORT_ONLY.fullmatch(x) for x in m) else "type")
    return marks


def is_working_paper(row):
    """A row of a working-paper or preprint registrar, or typed as one."""
    return bool(wp_marks(row))


def is_published(row):
    """Any row with an identifier or a type that is not a working paper."""
    return not is_working_paper(row) and bool(
        row.get("doi") or row.get("openalex_id") or mark_type(row).strip())


def published_ids(mem):
    """(OpenAlex id, DOI) naming a work that holds a working paper and a
    published row with an identifier (author decision 2026-10-09): the
    article is the first published row with a DOI, else the first published
    row; its DOI, and the OpenAlex id of a published row with that DOI (or
    of the article, without a DOI). ``None`` otherwise.

    The DOI comes first: OpenAlex types an SSRN record without a DOI as an
    article, and the Gavard-Schoch work, which holds one, was named by it."""
    pubs = [m for m in mem if is_published(m) and (m.get("doi") or m.get("openalex_id"))]
    if not pubs or not any(is_working_paper(m) for m in mem):
        return None
    art = next((m for m in pubs if m.get("doi")), pubs[0])
    doi = art.get("doi") or ""
    oa = next((m["openalex_id"] for m in pubs if m.get("openalex_id")
               and (m.get("doi") or "") == doi), "")
    return oa, doi


def _fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).casefold()


def surnames(first_author):
    """Name tokens of a first author, initials dropped (``Gavard, C.`` -> {gavard})."""
    s = _fold(first_author)
    if "," in s:
        s = s.split(",", 1)[0]
    return {t for t in re.findall(r"[^\W\d_]+", s) if len(t) > 2}


def same_first_author(a, b):
    """Both first authors known and sharing a surname."""
    sa, sb = surnames(a), surnames(b)
    return bool(sa and sb and sa & sb)


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


def _n_words(rows, i, words):
    return len(words(rows[i]["title"] or "").split())


def _window_edges(rows, wp_only, published, by_key, words, stats):
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
                if _n_words(rows, wi, words) <= SHORT_TITLE_WORDS and not any(
                        same_first_author(rows[a].get("first_author"), rows[b].get("first_author"))
                        for _, a in comps[w]["wp"] for _, b in comps[p]["pub"]):
                    stats["pairs_short_title_refused"] += 1
                    continue
                edges.setdefault((w, p), {"kind": "window", "a_row": wi, "b_row": pi,
                                          "gap": py - wy, "key": key})
    return edges


def _refused(edges, too_many):
    """Cluster of each pair, and the clusters ``too_many`` refuses (given the
    set of components of the cluster)."""
    parent = {}

    def find(c):
        parent.setdefault(c, c)
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c

    for a, b in edges:
        parent[find(a)] = find(b)
    comps = defaultdict(set)
    for a, b in edges:
        comps[find(a)].update((a, b))
    return find, {root for root, cs in comps.items() if too_many(cs)}


def _component_flags(rows, idx, uf):
    """Root -> (has a DOI, has an OpenAlex id, has a published row)."""
    flags = defaultdict(lambda: [False, False, False])
    for i in idx:
        r, f = rows[i], flags[uf.find(i)]
        f[0] |= bool(r.get("doi"))
        f[1] |= bool(r.get("openalex_id"))
        f[2] |= is_published(r)
    return flags


def _openalex_edges(rows, idx, uf, norm, words, stats):
    """Step 5c pairs (OpenAlex-only component, other component) -> pair info."""
    flags = _component_flags(rows, idx, uf)
    groups = defaultdict(dict)        # (key, year) -> component -> first row
    for i in idx:
        r = rows[i]
        key = norm(r["title"] or "")
        if not (key and r.get("year")) or _n_words(rows, i, words) < OA_MIN_WORDS \
                or is_generic_title(words(r["title"])):
            continue
        groups[key, r["year"]].setdefault(uf.find(i), i)
    edges = {}
    for (key, _), comps in sorted(groups.items()):
        oa_only = sorted(c for c in comps if flags[c][1] and not flags[c][0])
        with_doi = sorted(c for c in comps if flags[c][0])
        if not oa_only:
            continue
        for c in oa_only[1:]:
            edges.setdefault((c, oa_only[0]), {"kind": "openalex", "a_row": comps[c],
                                               "b_row": comps[oa_only[0]], "gap": 0, "key": key})
        if len(with_doi) == 1:
            d = with_doi[0]
            for c in oa_only:
                edges.setdefault((c, d), {"kind": "openalex_doi", "a_row": comps[c],
                                          "b_row": comps[d], "gap": 0, "key": key})
        elif len(with_doi) > 1:
            stats["oa_groups_two_doi"] += 1
    return edges, flags


def _accept(edges, refused_root, uf, pairs, stats, name):
    for (a, b), info in edges.items():
        if refused_root(a):
            stats[f"{name}_refused"] += 1
            continue
        stats[f"{name}_accepted"] += 1
        uf.union(a, b)
        if pairs is not None:
            pairs.append(info)


STAT_KEYS = ("hint_unions", "hint_unions_two_published", "pairs_in_window", "pairs_out_of_window",
             "pairs_short_title_refused", "clusters_refused", "pairs_refused", "pairs_accepted",
             "pairs_accepted_on_report_alone")
OA_STAT_KEYS = ("oa_pairs", "oa_groups_two_doi", "oa_clusters_refused", "oa_pairs_refused",
                "oa_pairs_accepted")


def version_unions(rows, uf, norm, words, idx=None, pairs=None, oa_dups=False):
    """Step 5 on ``rows`` (those in ``idx``, default all) and union-find ``uf``.

    Applies the unions to ``uf`` and returns the step counts. ``pairs``, a
    list, receives one dict per union: ``kind`` ``link`` (5a; ``a_row`` the
    hinting row, ``b_row`` the row it names, ``key`` the hint), ``window``
    (5b; ``a_row`` the working-paper row, ``b_row`` the published row, ``gap``
    the article year minus the working-paper year, ``key`` the title key),
    ``openalex`` or ``openalex_doi`` (5c, with ``oa_dups``; ``a_row`` a row of
    the OpenAlex-only component, ``b_row`` of the OpenAlex-only or the
    DOI-bearing component it joins).
    """
    idx = range(len(rows)) if idx is None else list(idx)
    hint_edges, resolved, unresolved = _hint_unions(rows, idx, uf)
    stats = defaultdict(int, hints_resolved=resolved, hints_unresolved=unresolved,
                        **{k: 0 for k in STAT_KEYS + (OA_STAT_KEYS if oa_dups else ())})
    published = {c for c, f in _component_flags(rows, idx, uf).items() if f[2]}
    for a, b in hint_edges:
        ra, rb = uf.find(a), uf.find(b)
        if ra == rb:
            continue
        stats["hint_unions"] += 1
        stats["hint_unions_two_published"] += ra in published and rb in published
        if ra in published or rb in published:
            published.add(min(ra, rb))
        uf.union(a, b)
        if pairs is not None:
            pairs.append({"kind": "link", "a_row": a, "b_row": b, "gap": "", "key": ""})
    wp_only, published, by_key = _kinds_by_key(rows, idx, uf, norm, words)
    edges = _window_edges(rows, wp_only, published, by_key, words, stats)
    find, refused = _refused(edges, lambda cs: len(cs & published) > 1)
    stats.update(pairs_in_window=len(edges), clusters_refused=len(refused))
    report_only = {uf.find(i) for i in idx if wp_marks(rows[i]) == {"report"}} - {
        uf.find(i) for i in idx if wp_marks(rows[i]) - {"report"}}
    stats["pairs_accepted_on_report_alone"] = sum(
        w in report_only for w, _ in edges if find(w) not in refused)
    _accept(edges, lambda a: find(a) in refused, uf, pairs, stats, "pairs")
    if oa_dups:
        oedges, flags = _openalex_edges(rows, idx, uf, norm, words, stats)
        ofind, orefused = _refused(oedges, lambda cs: sum(flags[c][0] for c in cs) > 1)
        stats.update(oa_pairs=len(oedges), oa_clusters_refused=len(orefused))
        _accept(oedges, lambda a: ofind(a) in orefused, uf, pairs, stats, "oa_pairs")
    return dict(sorted(stats.items()))


def recall_on_known(rows, members, id_field, norm, words, union_find, oa_dups=False):
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
        stats = version_unions(sub, uf, norm, words, oa_dups=oa_dups)
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
PAIR_PREFIX = {"link": "L", "window": "P", "openalex": "O", "openalex_doi": "D"}


def pair_records(rows, pairs):
    """One flat record per step-5 union, for the report and the precision panel.

    Each side is its row, blanks filled from the rows that share its DOI or
    OpenAlex id (the same record seen by several sources); ``doc_type`` is the
    type the marks read; the abstract is cut to ``ABSTRACT_CHARS``. Pair ids
    (``PAIR_PREFIX`` then a number) number each kind in the order of its
    sorted record ids."""
    by_id = defaultdict(list)
    for i, r in enumerate(rows):
        if r.get("doi"):
            by_id["doi", r["doi"]].append(i)
        if r.get("openalex_id"):
            by_id["oa", r["openalex_id"]].append(i)

    def side(i):
        r = {**rows[i], "doc_type": mark_type(rows[i])}
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
        pid = f"{PAIR_PREFIX[p['kind']]}{n[p['kind']]:05d}"
        n[p["kind"]] += 1
        out.append({"pair_id": pid, "kind": p["kind"], "gap": p["gap"], "key": p["key"],
                    **{f"a_{f}": a[f] for f in PAIR_SIDE_FIELDS},
                    **{f"b_{f}": b[f] for f in PAIR_SIDE_FIELDS}})
    return out
