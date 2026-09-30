"""Work keys of the REL causal-map lane (tickets 1652, 1755).

Title keys (the pool's normaliser), the DOI veto of the title+year join, the
doi.org check of the EDS DOIs that would split a title group, and the carry
of judge labels to records whose key changed. Used by
``corpus_rel_causal_yield.py``, which re-exports these names.
"""

import bisect
import csv
import os
import re
import unicodedata
from collections import defaultdict

from utils import normalize_doi, normalize_title

_DOI = re.compile(r"^10\.\d{4,9}/\S+$")


def valid_doi(doi):
    """The normalised DOI, or "" for a truncated one (EDS returns bare
    prefixes such as `10.35219`, which would join unrelated works)."""
    d = normalize_doi(doi or "")
    return d if _DOI.match(d) else ""


def norm_title(title):
    """The pool's title normaliser (``_rel_pool_dedup``), so that the lane and
    the pool group the same titles: `China’s` and `China's` are one title."""
    return normalize_title(title or "")


def title_key(title, year):
    t = norm_title(title)
    return f"{t}|{year}" if len(t) >= 20 and year else ""


def _agrees(hint, doi):
    """An EDS DOI agrees with a DOI when it is empty, equal, or a strict prefix
    (EDS truncates); any other pair names two different works."""
    return not hint or doi.startswith(hint)


def _prefix_of_another(hint, lane_sorted):
    """True when ``hint`` is a strict prefix of a DOI or EDS DOI anywhere in
    the lane (``lane_sorted``, sorted): a truncated DOI, whatever its title."""
    i = bisect.bisect_right(lane_sorted, hint)
    return i < len(lane_sorted) and lane_sorted[i].startswith(hint)


def _title_groups(records, by_oa, resolves=None):
    """Per title+year key: the DOIs records carry, the first OpenAlex work
    without DOI, and the anchors: those DOIs plus the EDS DOIs that can name
    a work of their own.

    An EDS DOI is no anchor when it is a strict prefix of any DOI or EDS DOI
    of the lane (truncated). In a group with several anchors, an EDS DOI that
    no record carries as its DOI must also resolve at doi.org (``resolves``,
    a ``doi -> bool`` callable; ``None`` resolves nothing): a DOI cut at a
    field boundary (`...2004.`, `..._v1`) is no prefix of anything the lane
    holds, and only the resolver catches it."""
    dois_by_title, hints_by_title, oa_by_title = defaultdict(set), defaultdict(set), {}
    for r in records:
        k = title_key(r.get("title"), r.get("year"))
        if not k:
            continue
        if r.get("doi"):
            dois_by_title[k].add(r["doi"])
            continue
        if r.get("doi_eds"):
            hints_by_title[k].add(r["doi_eds"])
        if r.get("openalex_id"):
            oa_by_title.setdefault(k, by_oa.get(r["openalex_id"], "oa:" + r["openalex_id"]))
    known = set().union(*dois_by_title.values()) if dois_by_title else set()
    lane_sorted = sorted(known | {h for r in records if (h := r.get("doi_eds"))})
    candidates = {k: dois_by_title[k] | {h for h in hints_by_title[k]
                                         if not _prefix_of_another(h, lane_sorted)}
                  for k in set(dois_by_title) | set(hints_by_title)}
    to_check = sorted({h for k, c in candidates.items() if len(c) > 1
                       for h in c - dois_by_title[k] if h not in known})
    ok = {h for h in to_check if resolves is not None and resolves(h)}
    anchors = {k: {a for a in c if a in dois_by_title[k] or a in known or a in ok or len(c) == 1}
               for k, c in candidates.items()}
    return dois_by_title, oa_by_title, anchors


def _split_group_key(r, hint, group, own, k):
    """Key of a record without DOI in a title+year group holding works whose
    DOIs disagree: the one anchor its EDS DOI agrees with; else its OpenAlex
    id; else the title+year key, which the group's other unplaceable EDS
    records share. (The pool joins such rows with one another only when the
    pool's title group holds two DOI components; with one, it joins them to
    it.) A record that anchors a work with its own EDS DOI gets it as
    ``doi``."""
    agreeing = sorted(a for a in group if _agrees(hint, a))
    if len(agreeing) != 1:
        return "oa:" + r["openalex_id"] if r.get("openalex_id") else "ty:" + k
    if agreeing[0] in own:
        return "doi:" + agreeing[0]
    if hint == agreeing[0]:
        r["doi"], r["doi_promoted"] = hint, True
    return "edsdoi:" + agreeing[0]


def assign_work_keys(records, resolves=None):
    """Work key per record: its DOI; else the DOI another record gives its
    OpenAlex id; else, within its title+year group, the one DOI it agrees
    with; else its OpenAlex id; else the key of an identified record with the
    same title+year; else a title+year key. The title join also covers an
    OpenAlex record without DOI and an EDS record carrying one, which an
    id-first rule would keep apart.

    A title+year group whose records carry two DOIs that disagree (the
    OpenAlex DOIs, and the EDS DOIs that ``_title_groups`` accepts as anchors:
    no prefix of a lane DOI, and resolving at doi.org) holds several works
    (ticket 1755): a record joins only the one DOI it agrees with, and a
    record that agrees with several, or none, keeps its own key. An EDS DOI
    that anchors such a split becomes the record's ``doi``: without it the
    pool's title+year join would fuse the works again."""
    by_oa = {r["openalex_id"]: "doi:" + r["doi"] for r in records
             if r.get("doi") and r.get("openalex_id")}
    known_dois = {r["doi"] for r in records if r.get("doi")}
    dois_by_title, oa_by_title, anchors = _title_groups(records, by_oa, resolves)
    for r in records:
        k = title_key(r.get("title"), r.get("year"))
        hint = r.get("doi_eds") or ""
        group = anchors.get(k, set())
        if r.get("doi"):
            r["work_key"] = "doi:" + r["doi"]
        elif r.get("openalex_id") and r["openalex_id"] in by_oa:
            r["work_key"] = by_oa[r["openalex_id"]]
        elif hint in known_dois:
            # an EDS DOI that equals a DOI another record carries is not truncated
            r["work_key"] = "doi:" + hint
        elif len(group) > 1:
            r["work_key"] = _split_group_key(r, hint, group, dois_by_title[k], k)
        else:
            one_doi = "doi:" + next(iter(dois_by_title[k])) if dois_by_title.get(k) else ""
            if r.get("openalex_id"):
                r["work_key"] = one_doi or "oa:" + r["openalex_id"]
            else:
                r["work_key"] = (one_doi or oa_by_title.get(k)
                                 or ("ty:" + k if k else "")
                                 or ("edsdoi:" + hint if hint else "")
                                 or "an:" + r.get("eds_an", ""))
    return records


def _legacy_title_key(title, year):
    """The title key before ticket 1755 (ASCII-folded, punctuation read as a
    space), under which the judge labels of 2026-09-30 were given."""
    t = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    return f"{t}|{year}" if len(t) >= 20 and year else ""


def carry_labels(records, labels, raw):
    """Give a (work, question) pair the judge never saw the label the judge
    gave the same record under a key the earlier rule could have given it
    (legacy title key, OpenAlex id, DOI, accession number), when those labels
    agree. Never for a work split from a DOI twin (``edsdoi:`` keys, promoted
    DOIs): the old label judged the twin. Returns the pairs labelled."""
    found = defaultdict(set)
    for r in records:
        key = (r["work_key"], r["question"])
        if key in labels or r["work_key"].startswith("edsdoi:") or r.get("doi_promoted"):
            continue
        tk = _legacy_title_key(r.get("title"), r.get("year"))
        olds = [k for k in ("ty:" + tk if tk else "",
                            "oa:" + r["openalex_id"] if r.get("openalex_id") else "",
                            "doi:" + r["doi"] if r.get("doi") else "",
                            "an:" + r["eds_an"] if r.get("eds_an") else "") if k]
        found[key] |= {raw[pid] for k in olds if (pid := pair_id(k, r["question"])) in raw}
    carried = {key: next(iter(labs)) for key, labs in found.items() if len(labs) == 1}
    labels.update(carried)
    return len(carried)


def pair_id(work_key, question):
    return f"{question}::{work_key}"


HANDLE_API = "https://doi.org/api/handles/"
DOI_CHECK_FIELDS = ["doi", "resolves", "checked_at"]


def handle_lookup(doi):
    """True when doi.org's handle API knows ``doi`` (free, no key); raises on
    anything but a definite answer, so a network failure never demotes a DOI."""
    import time
    from urllib.parse import quote

    import requests
    resp = requests.get(HANDLE_API + quote(doi, safe="/"), timeout=30)
    time.sleep(0.2)
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    return resp.json().get("responseCode") == 1


class DoiChecks:
    """doi.org answers, cached in a CSV so each EDS DOI is looked up once and
    the evidence is archived with the analysis (``--doi-checks``)."""

    def __init__(self, path, lookup=handle_lookup):
        self.path, self.lookup, self.done = path, lookup, {}
        if os.path.exists(path):
            with open(path, encoding="utf-8", newline="") as fh:
                self.done = {r["doi"]: r["resolves"] == "true" for r in csv.DictReader(fh)}

    def __call__(self, doi):
        if doi not in self.done:
            from datetime import datetime, timezone
            self.done[doi] = self.lookup(doi)
            new = not os.path.exists(self.path)
            with open(self.path, "a", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, DOI_CHECK_FIELDS)
                if new:
                    w.writeheader()
                w.writerow({"doi": doi, "resolves": str(self.done[doi]).lower(),
                            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        return self.done[doi]
