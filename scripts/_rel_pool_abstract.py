"""Abstract selector of the REL pool (ticket 2045).

Every other pool column comes from the first non-empty member. The abstract
does not: its members differ in quality, and rank (catalogue first, then
``lane_order``) says nothing about it. ``select_abstract`` classes each
member's abstract and takes the best class present:

1. ``usable``: not boilerplate, not a stub, not truncated;
2. ``truncated``: a prefix (ellipsis ignored) of a longer, non-boilerplate
   member's abstract;
3. ``highlights``: a table candidate that is a 'Highlights' bullet list ("Highlights:" or "Highlights•");
4. ``stub``: not boilerplate, under ``STUB_MAX`` characters once trimmed;
5. ``boilerplate``: ``openalex_corpus.is_boilerplate_abstract``;
6. ``blank``: whitespace only.

Within a class the longest wins; ties go to the earlier-ranked member. A work
whose abstracts all sit in a lower class still gets one (never worse than the
first-non-empty rule), flagged. ``abstract_flag``:

- ``ok``: a usable abstract that does not look cut;
- ``truncated_suspect``: a truncated one, or a usable one with no longer copy
  that is exactly ``OLD_CUT`` characters (the old ``slim()`` cut) or ends in
  an ellipsis;
- ``stub``: only a stub or boilerplate abstract exists;
- ``highlights``: only a 'Highlights' bullet list ("Highlights:" or "Highlights•") from an enrichment table
  (ticket 2052; ``_rel_pool_enrich``) exists besides stubs: ranked below a
  usable or truncated abstract, above a stub; never applied to a lane member;
- ``no_abstract``: blank after trimming, the rule of ``_rel_reasons`` (author
  decision 2026-10-07: counted in the bibliometric analysis only).
"""

import re

from openalex_corpus import is_boilerplate_abstract

STUB_MAX = 100   # characters after trimming
OLD_CUT = 1500   # the old slim() cut; equal length is evidence, not proof
_ELLIPSIS = re.compile(r"\s*(?:\.\.\.|…)$")
_WS = re.compile(r"\s+")

OK, TRUNCATED, STUB, NONE = "ok", "truncated_suspect", "stub", "no_abstract"
HIGHLIGHTS = "highlights"
CLASSES = ("usable", "truncated", "highlights", "stub", "boilerplate", "blank")
_HIGHLIGHTS = re.compile(r"(?:research\s+)?highlights\s*(?:[:•·►▪▶■●○*-])", re.IGNORECASE)


def _norm(text):
    return _WS.sub(" ", text).strip()


def looks_cut(text):
    """Length of the old cut, or a trailing ellipsis."""
    t = _norm(text)
    return len(t) == OLD_CUT or bool(_ELLIPSIS.search(t))


def classify(texts, title="", tables=None):
    """Class (see ``CLASSES``) of each abstract in ``texts``, judged against its siblings.

    ``tables`` (optional, one bool per text) marks enrichment-table candidates;
    only those can be classed ``highlights``."""
    norm = [_norm(t) for t in texts]
    boiler = [bool(n) and is_boilerplate_abstract(t, title=title) for t, n in zip(texts, norm, strict=True)]
    out = []
    for k, n in enumerate(norm):
        if not n:
            out.append("blank")
        elif boiler[k]:
            out.append("boilerplate")
        elif len(n) < STUB_MAX:
            out.append("stub")
        else:
            core = _ELLIPSIS.sub("", n)
            longer = any(len(norm[j]) > len(n) and not boiler[j] and norm[j].startswith(core)
                         for j in range(len(norm)) if j != k)
            if longer:
                out.append("truncated")
            elif tables and tables[k] and _HIGHLIGHTS.match(n):
                out.append("highlights")
            else:
                out.append("usable")
    return out


def select_abstract(members, title=""):
    """``(abstract, source, flag)`` for one work from its ranked members.

    ``members`` are the work's rows, best-ranked first; one with no
    ``abstract`` value does not take part. ``source`` is its ``origin``.
    """
    idx = [k for k, m in enumerate(members) if m.get("abstract")]
    if not idx:
        return "", "", NONE
    texts = [members[k]["abstract"] for k in idx]
    tables = [bool(members[k].get("_table")) for k in idx]
    classes = classify(texts, title, tables)
    best = next(c for c in CLASSES if c in classes)
    k = min((j for j, c in enumerate(classes) if c == best),
            key=lambda j: (-len(_norm(texts[j])), j))
    text, source = texts[k], members[idx[k]]["origin"]
    if best == "blank":
        return text, source, NONE
    if best == "highlights":
        return text, source, HIGHLIGHTS
    if best in ("stub", "boilerplate"):
        return text, source, STUB
    if best == "truncated" or looks_cut(text):
        return text, source, TRUNCATED
    return text, source, OK
