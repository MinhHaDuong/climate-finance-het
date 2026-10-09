"""Enrichment tables of the REL pool (ticket 2052).

A table fills a value per work (an abstract, a resource type) without being a
lane: it adds nothing to ``sources``, ``n_sources``, ``member_record_ids`` or
``work_key``. Each table is a config entry (``enrichment`` in
``config/rel_pool.yaml``): ``source`` (the label that provenance carries),
``path``, ``sha256`` (the build refuses any other file), ``doi_column`` and/or
``openalex_column``, ``fills`` (pool column -> table column; ``abstract`` and
``doc_type`` only), ``rule`` (``fill_blank``) and ``redistribution``.

Join. A table row matches a work when its normalized DOI or OpenAlex id
equals one of the DOIs or ids of any member of the work. A row whose keys
reach two different works is ambiguous: reported, it joins none. Rows that
reach no work are counted.

Filling. ``doc_type`` is filled only where the pool value is blank, with
``doc_type_source`` naming the table. An abstract enters the ticket-2045
selector (``_rel_pool_abstract``) as one more candidate whose ``origin`` is the
table label, so quality, truncation and stub flags apply to it. It never
replaces a usable abstract the members already give (flag ``ok``); it replaces
a weaker one or a blank only when it ranks in a strictly better class. A
candidate that is a 'Highlights:' bullet list is classed ``highlights``,
below a real abstract and above a stub, and the pool flags it so.

Several values for one work: a ``doc_type`` the tables disagree on resolves to
the alphabetically first (label, value) pair and is counted
(``doc_type_conflict``). The report describes the version-1 build, the pool
written; its counters ``unmatched``, ``ambiguous`` and ``no_key`` start at 0.

The result does not depend on the order of the tables: candidates are sorted
before they are chosen from, and counters are keyed by label.
"""

import csv
import hashlib
import os
from collections import Counter, defaultdict

from _rel_pool_abstract import OK, select_abstract
from _rel_pool_keys import norm_openalex
from _rel_pool_report import RelPoolError
from utils import normalize_doi

FILLABLE = ("abstract", "doc_type")
RULES = ("fill_blank",)
EXTRA_COLUMNS = ["doc_type_source"]
_ENTRY_KEYS = {"source", "path", "sha256", "doi_column", "openalex_column",
               "fills", "rule", "redistribution"}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_tables(entries, root, reserved=()):
    """Validated, hash-checked tables from the config list ``entries``."""
    tables, seen = [], set()
    for e in entries or []:
        label = str(e.get("source") or "")
        missing = sorted({"source", "path", "sha256", "fills", "rule"} - set(e))
        if missing or not label:
            raise RelPoolError(f"enrichment entry {label or e}: missing {missing or ['source']}")
        unknown = sorted(set(e) - _ENTRY_KEYS)
        if unknown:
            raise RelPoolError(f"enrichment {label}: unknown keys {unknown}")
        if label == "catalogue" or label in reserved:
            raise RelPoolError(f"enrichment source {label} is the name of the catalogue or a lane")
        if label in seen:
            raise RelPoolError(f"enrichment source {label} listed twice")
        seen.add(label)
        if e["rule"] not in RULES:
            raise RelPoolError(f"enrichment {label}: rule {e['rule']!r} not in {RULES}")
        fills = e["fills"] or {}
        if not fills or set(fills) - set(FILLABLE):
            raise RelPoolError(f"enrichment {label}: fills must name {FILLABLE}, got {sorted(fills)}")
        if not (e.get("doi_column") or e.get("openalex_column")):
            raise RelPoolError(f"enrichment {label}: needs doi_column or openalex_column")
        path = os.path.join(root, e["path"])
        if not os.path.isfile(path):
            raise RelPoolError(f"enrichment {label}: {path} not found")
        got = _sha256(path)
        if got != e["sha256"]:
            raise RelPoolError(f"enrichment {label}: {path} has sha256 {got}, config pins {e['sha256']}")
        with open(path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            cols = set(reader.fieldnames or [])
            need = {c for c in (e.get("doi_column"), e.get("openalex_column"), *fills.values()) if c}
            if need - cols:
                raise RelPoolError(f"enrichment {label}: columns {sorted(need - cols)} absent from {path}")
            rows = list(reader)
        tables.append({"label": label, "doi": e.get("doi_column"),
                       "oa": e.get("openalex_column"), "fills": dict(fills),
                       "rows": rows, "sha256": got})
    return tables


def mark_doc_types(rows, tables):
    """Dedup version 2, before clustering (ticket 2048): give a row whose
    ``doc_type`` is blank the type the tables give its own DOI, else its
    OpenAlex id, as ``enriched_doc_type``. Only the working-paper mark of step
    5 reads it (``_rel_pool_versions.mark_type``); the pool's ``doc_type``
    stays filled per work by ``Enrichment.fill``. Several values for one key:
    the first (label, value) pair. Returns the number of rows marked."""
    by_key = defaultdict(set)
    for t in tables:
        src = t["fills"].get("doc_type")
        if not src:
            continue
        for r in t["rows"]:
            v = (r.get(src) or "").strip()
            if v:
                for k in Enrichment._row_keys(t, r):
                    by_key[k].add((t["label"], v))
    n = 0
    for r in rows:
        if r.get("doc_type"):
            continue
        for k in (("d", r.get("doi")), ("o", r.get("openalex_id"))):
            if k[1] and by_key.get(k):
                r["enriched_doc_type"] = min(by_key[k])[1]
                n += 1
                break
    return n


class Enrichment:
    """The tables of one build and what they delivered (``stats``)."""

    def __init__(self, tables):
        self.tables = tables
        self.cands = {}
        self.stats = {}

    @staticmethod
    def _row_keys(t, r):
        ks = []
        if t["doi"] and normalize_doi(r.get(t["doi"])):
            ks.append(("d", normalize_doi(r[t["doi"]])))
        if t["oa"] and norm_openalex(r.get(t["oa"])):
            ks.append(("o", norm_openalex(r[t["oa"]])))
        return ks

    def match(self, rows, members):
        """Join every table row to its work; ``members``: root -> row indexes."""
        keyed = [(t, r, self._row_keys(t, r)) for t in self.tables for r in t["rows"]]
        wanted = {k for _, _, ks in keyed for k in ks}
        works = defaultdict(set)
        for root, idx in members.items():
            for i in idx:
                for k in (("d", rows[i]["doi"]), ("o", rows[i]["openalex_id"])):
                    if k in wanted:
                        works[k].add(root)
        self.cands = defaultdict(lambda: {c: set() for c in FILLABLE})
        self.stats = {t["label"]: Counter(rows=len(t["rows"]), unmatched=0, ambiguous=0, no_key=0, matched=0) for t in self.tables}
        amb_keys = {t["label"]: set() for t in self.tables}
        for t, r, ks in keyed:
            st = self.stats[t["label"]]
            hit = set().union(*(works.get(k, set()) for k in ks))
            amb_keys[t["label"]].update(k for k in ks if len(works.get(k, ())) > 1)
            if not ks:
                st["no_key"] += 1
            elif not hit:
                st["unmatched"] += 1
            elif len(hit) > 1:
                st["ambiguous"] += 1
            else:
                st["matched"] += 1
                self._deliver(t, r, next(iter(hit)), st)
        for label, ks in amb_keys.items():
            self.stats[label]["ambiguous_keys"] = len(ks)

    def _deliver(self, t, r, root, st):
        for col, src in t["fills"].items():
            v = (r.get(src) or "").strip()
            if v:
                st["delivers_" + col] += 1
                self.cands[root][col].add((t["label"], v if col == "doc_type" else r[src]))

    def fill(self, merged, mem, root):
        """Apply the candidates of ``root`` to the pool row ``merged``."""
        merged["doc_type_source"] = ""
        c = self.cands.get(root)
        if not c:
            return
        if c["doc_type"] and not merged["doc_type"]:
            values = sorted(c["doc_type"], key=lambda sv: (sv[0], sv[1]))
            merged["doc_type_source"], merged["doc_type"] = values[0]
            self.stats[values[0][0]]["filled_doc_type"] += 1
            if len({v for _, v in c["doc_type"]}) > 1:
                self.stats[values[0][0]]["doc_type_conflict"] += 1
        if c["abstract"] and merged["abstract_flag"] != OK:
            extra = [{"origin": s, "abstract": a, "_table": True}
                     for s, a in sorted(c["abstract"])]
            text, source, flag = select_abstract(mem + extra, merged["title"])
            if source in {s for s, _ in c["abstract"]} and text in {a for _, a in c["abstract"]}:
                merged["abstract"], merged["abstract_source"], merged["abstract_flag"] = text, source, flag
                self.stats[source]["filled_abstract"] += 1

    def report(self):
        return {label: dict(sorted(st.items())) for label, st in sorted(self.stats.items())}
