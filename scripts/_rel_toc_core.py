"""Pure functions of the REL table-of-contents sweep (ticket 1650).

Normalisation, item typing, Crossref/OpenAlex record flattening, the merge of
the two TOC sources, pool matching and the per-issue register. No network, no
files: ``catalog_rel_toc.py`` does the I/O.
"""

import collections
import html
import re
import unicodedata

from utils import normalize_doi, reconstruct_abstract

FROM_DATE = "1990-01-01"
UNTIL_DATE = "2026-09-28"  # config/rel_review.yaml search date


def crossref_filter(journal):
    """Crossref /works filter: every ISSN of the title (ORed), REL window.

    /journals/{issn}/works follows one ISSN: ESPR deposits 2023+ under its eISSN
    only, and a pISSN sweep misses 13,125 works (measured 2026-09-30).
    """
    issns = [i for i in (journal.get("pissn"), journal.get("eissn")) if i]
    issns = list(dict.fromkeys(issns))
    return ",".join([f"issn:{i}" for i in issns]
                    + [f"from-pub-date:{FROM_DATE}", f"until-pub-date:{UNTIL_DATE}"])

# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------

_TAG = re.compile(r"<[^>]+>")


def normalize_title(title):
    """Casefold, strip markup and accents, keep letters and digits."""
    if not isinstance(title, str) or not title:
        return ""
    t = html.unescape(_TAG.sub("", title))
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c)).casefold()
    t = re.sub(r"[\u2019\u2018'`]", "", t)  # "Editor's" -> "editors", not "editor s"
    t = re.sub(r"[^\w\s]|_", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def surname_key(name):
    """Last token of a surname, from 'Given Family', 'Family, Given' or 'Family'."""
    if not isinstance(name, str) or not name.strip():
        return ""
    if "," in name:
        name = name.split(",", 1)[0]
    tokens = normalize_title(name).split()
    return tokens[-1] if tokens else ""


# Patterns run on the normalised title (lowercase, punctuation as spaces) and
# describe the whole shape of a notice, never a bare prefix: "Index insurance
# and basis risk" and "Covered interest parity" are articles (gaze, PR 1615).
# When a title is ambiguous the item stays an article and is delivered.
_CLASSES = [
    ("front-back-matter",
     r"^(front|back) matter( .*)?$|^issue information( .*)?$"
     r"|^editorial (advisory )?board( .*)?$|^(inside )?(front |back )?cover( page| 2)?( .*board)?$"
     r"|^title page$|^(recent )?referees$|^list of (reviewers|referees)( .*)?$"
     r"|^acknowledge?ments? (to|of) (the )?(reviewers|referees)( .*)?$"
     r"|^(volume )?contents( page)?$|^volume information$"
     r"|^masthead$|^(table of )?contents( of volume \S+| list)?$"
     r"|^cover [0-9]( .*)?$|^(author |subject )?index( to volume \S+)?$"
     r"|^subscription (information|page)$|^instructions (to|for) (authors|contributors)$"
     r"|^announcements?$|^announcements? call for .*$"),
    ("book-review", r"^books? (reviews?|received)( .*)?$|^book notes?( .*)?$"),
    ("erratum",
     r"^(erratum|errata|corrigendum|corrigenda)( .*)?$|^corrections?$|^correction to .*$"
     r"|^.* (erratum|corrigendum)$|^publisher correction( .*)?$"
     r"|^retraction( notice)?$|^retraction notice to .*$|^notice of retraction( .*)?$"
     r"|^expression of concern( .*)?$"),
    ("editorial", r"^editorial( .*)?$|^editors? (note|introduction)( .*)?$"
                  r"|^introduction to the (special )?issue( .*)?$|^foreword( .*)?$|^preface( .*)?$"),
    ("society-report", r"^report of the .*$|^minutes of .*$|^annual report( .*)?$|^program of .*$"
                       r"|^papers and proceedings( .*)?$|^list of members( .*)?$"
                       r"|^in memoriam( .*)?$|^obituary( .*)?$"),
]


def classify_item(title):
    """Type a TOC item from its title; the type is recorded, never used to drop."""
    t = normalize_title(title)
    if not t:
        return "untitled"
    for label, pat in _CLASSES:
        if re.search(pat, t):
            return label
    return "article"


def _date_year(item, *keys):
    for k in keys:
        parts = (item.get(k) or {}).get("date-parts") or [[None]]
        if parts and parts[0] and parts[0][0]:
            return int(parts[0][0]), "-".join(str(p) for p in parts[0])
    return None, ""


def crossref_record(item, journal_key, issn):
    """Flatten one Crossref work into a TOC record."""
    authors = item.get("author") or []
    names = []
    for a in authors:
        fam, giv = a.get("family") or a.get("name") or "", a.get("given") or ""
        names.append(f"{fam}, {giv}".strip(", ") if giv else fam)
    volume = (item.get("volume") or "").strip()
    online_first = not volume
    if online_first:
        year, date = _date_year(item, "published-online", "issued")
    else:
        year, date = _date_year(item, "published-print", "issued", "published-online")
    title = " ".join(item.get("title") or [])
    return {
        "journal_key": journal_key, "issn": issn,
        "journal": " ".join(item.get("container-title") or []),
        "doi": normalize_doi(item.get("DOI") or ""),
        "title": title, "item_class": classify_item(title),
        "crossref_type": item.get("type") or "",
        "authors": "; ".join(names),
        "first_author": names[0] if names else "",
        "first_author_surname": surname_key(names[0]) if names else "",
        "year": year, "pub_date": date,
        "volume": volume, "issue": "" if online_first else (item.get("issue") or "").strip(),
        "online_first": online_first,
        "abstract": re.sub(r"\s+", " ", _TAG.sub(" ", item.get("abstract") or "")).strip()[:3000],
        "openalex_id": "",
    }


def openalex_record(work, journal_key):
    biblio = work.get("biblio") or {}
    names = [(a.get("author") or {}).get("display_name") or ""
             for a in work.get("authorships") or []]
    title = work.get("display_name") or ""
    return {
        "journal_key": journal_key,
        "openalex_id": (work.get("id") or "").rsplit("/", 1)[-1],
        "doi": normalize_doi(work.get("doi") or ""),
        "title": title, "item_class": classify_item(title),
        "openalex_type": work.get("type") or "",
        "authors": "; ".join(names),
        "first_author": names[0] if names else "",
        "first_author_surname": surname_key(names[0]) if names else "",
        "year": work.get("publication_year"), "pub_date": work.get("publication_date") or "",
        "volume": biblio.get("volume") or "", "issue": biblio.get("issue") or "",
        "abstract": (reconstruct_abstract(work.get("abstract_inverted_index")) or "")[:3000],
    }


def issue_key(rec):
    """(journal, year, volume, issue); online-first items group by year."""
    if rec["online_first"]:
        return (rec["journal_key"], rec["year"], "", "online-first")
    return (rec["journal_key"], rec["year"], rec["volume"], rec["issue"])


def _year(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


class PoolIndex:
    """Match keys of the pool: DOI, OpenAlex id, title+surname, title (no author)."""

    def __init__(self, rows):
        self.dois, self.ids = set(), set()
        self.title_author = collections.defaultdict(set)
        self.title_noauthor = collections.defaultdict(set)
        for r in rows:
            if r.get("doi"):
                self.dois.add(normalize_doi(r["doi"]))
            if r.get("openalex_id"):
                self.ids.add(r["openalex_id"])
            t, y = normalize_title(r.get("title")), _year(r.get("year"))
            if not t:
                continue
            s = surname_key(r.get("first_author"))
            if s:
                self.title_author[(t, s)].add(y)
            else:
                self.title_noauthor[t].add(y)
        self.size = len(rows)

    @staticmethod
    def _near(years, y):
        return y is not None and any(v is not None and abs(v - y) <= 1 for v in years)

    def match(self, rec):
        """How the record is found in the pool: a method name, or '' if absent."""
        if rec.get("doi") and normalize_doi(rec["doi"]) in self.dois:
            return "doi"
        if rec.get("openalex_id") and rec["openalex_id"] in self.ids:
            return "openalex_id"
        t, y = normalize_title(rec.get("title")), _year(rec.get("year"))
        # "Front Matter", "Foreword", "Comment": a title match would be noise.
        if len(t.split()) < 3 or classify_item(t) != "article":
            return ""
        s = rec.get("first_author_surname") or ""
        if s and self._near(self.title_author.get((t, s), ()), y):
            return "title_author_year"
        if self._near(self.title_noauthor.get(t, ()), y):
            return "title_year_noauthor"
        return ""


def merge_toc(cr_recs, oa_recs):
    """Crossref TOC plus what only OpenAlex holds, one record per work.

    An OpenAlex work joins its Crossref record by DOI, else by title + first-author
    surname + year within one (a DOI alias, e.g. a back file redeposited by a new
    publisher). The rest is kept as ``openalex-only``: never dropped, never merged
    by title alone. Such a record adopts the year of its Crossref issue if any.
    """
    out = [{**r, "toc_source": "crossref", "in_openalex": False, "alias_dois": "",
            "openalex_type": "", "year_source": "crossref",
            "abstract_provenance": ""} for r in cr_recs]
    by_doi = {r["doi"]: r for r in out if r["doi"]}
    by_title = collections.defaultdict(list)
    issue_year = {}
    offsets = collections.Counter()
    for r in out:
        by_title[(normalize_title(r["title"]), r["first_author_surname"])].append(r)
        if not r["online_first"]:
            issue_year.setdefault((r["volume"], r["issue"]), r["year"])
            if r["volume"].isdigit() and r["year"]:
                offsets[r["year"] - int(r["volume"])] += 1
    # One volume a year (AER: volume 89 is 1999) lets a volume date an item that
    # OpenAlex misdates; several volumes a year (Elsevier) does not.
    offset = None
    if offsets:
        best, n = offsets.most_common(1)[0]
        if n >= 0.9 * sum(offsets.values()):
            offset = best
    extra = []
    for o in oa_recs:
        hit = by_doi.get(o["doi"]) if o["doi"] else None
        if hit is None and o["item_class"] == "article" and o["first_author_surname"]:
            hits = [r for r in by_title.get((normalize_title(o["title"]),
                                             o["first_author_surname"]), [])
                    if r["year"] and o["year"] and abs(r["year"] - o["year"]) <= 1]
            if hits:
                hit = hits[0]
                if o["doi"]:
                    hit["alias_dois"] = " ".join(filter(None, [hit["alias_dois"], o["doi"]]))
        if hit is not None:
            hit["openalex_id"] = hit["openalex_id"] or o["openalex_id"]
            hit["in_openalex"] = True
            hit["openalex_type"] = o["openalex_type"]
            if not hit["title"] and o["title"]:
                hit["title"], hit["item_class"] = o["title"], classify_item(o["title"])
            if not hit["abstract"] and o["abstract"]:
                hit["abstract"], hit["abstract_provenance"] = o["abstract"], "openalex"
            continue
        online_first = not o["volume"]
        year, source = o["year"], "openalex"
        if not online_first and (o["volume"], o["issue"]) in issue_year:
            year, source = issue_year[(o["volume"], o["issue"])], "crossref-issue"
        elif (not online_first and offset is not None and o["volume"].isdigit()
              and 1900 <= int(o["volume"]) + offset <= 2030):
            # a volume field holding a page or article number must not redate
            year, source = int(o["volume"]) + offset, "volume-offset"
        extra.append({**o, "issn": "", "journal": "", "crossref_type": "",
                      "online_first": online_first, "year": year, "year_source": source,
                      "toc_source": "openalex-only", "in_openalex": True, "alias_dois": "",
                      "abstract_provenance": ""})
    return out + extra


def in_window(rec):
    """Year inside the REL window (items redated before 1990 fall out, counted)."""
    return rec["year"] is None or int(FROM_DATE[:4]) <= rec["year"] <= int(UNTIL_DATE[:4])


def unit_id(rec):
    """Registry id of the TOC unit holding a record (one issue, or online-first by year)."""
    journal, year, volume, issue = issue_key(rec)
    y = year if year is not None else "na"
    if issue == "online-first":
        return f"TOC-{journal}-{y}-online-first"
    return f"TOC-{journal}-{y}-v{volume or 'na'}-i{issue or 'na'}"


# The contract (docs/rel-intake-contract.md) leaves out only what is not an item:
# covers, boards, contents pages, issue records and erratum notices. Book reviews,
# editorials and society reports are delivered.
_FRONT_MATTER = {"front-back-matter", "erratum", "untitled"}


def exclusion_reason(rec):
    """Contract reason for leaving a record out, else '' (the record is delivered).

    An untitled record is an issue record (front matter) when Crossref types it
    ``journal-issue``; otherwise it is an item whose title neither Crossref nor
    OpenAlex holds (``not_retrievable``), often a short untitled book review.
    """
    cls = rec.get("item_class")
    if cls == "untitled" and rec.get("crossref_type") != "journal-issue":
        return "not_retrievable"
    return "front_matter" if cls in _FRONT_MATTER else ""


def lane_status(rec):
    """Information only, never a filter: in the pool already, or a candidate."""
    return "already_in_pool" if rec.get("in_pool") else "candidate"


def record_id(rec):
    if rec.get("doi"):
        return f"doi:{rec['doi']}"
    return f"openalex:{rec['openalex_id']}"


def build_register(records):
    """One row per TOC unit: expected, scanned, in pool, candidates, unresolved.

    Scope (author, 2026-09-30): the TOC is what Crossref and OpenAlex hold, not
    verified against publisher pages, so every retrieved item counts as scanned.
    ``unresolved`` counts OpenAlex-only items without a DOI, which no second
    source confirms.
    """
    groups = collections.OrderedDict()
    for rec in sorted(records, key=lambda r: (r["journal_key"], r["year"] or 0,
                                              str(r["volume"]), str(r["issue"]))):
        groups.setdefault(unit_id(rec), []).append(rec)
    rows = []
    for qid, recs in groups.items():
        journal, year, volume, issue = issue_key(recs[0])
        n_pool = sum(1 for r in recs if r["in_pool"])
        reasons = collections.Counter(exclusion_reason(r) for r in recs)
        rows.append({
            "query_id": qid, "journal_key": journal, "year": year if year is not None else "",
            "volume": volume, "issue": issue,
            "expected": len(recs), "scanned": len(recs),
            "crossref_n": sum(1 for r in recs if r.get("toc_source", "crossref") == "crossref"),
            "openalex_only_n": sum(1 for r in recs if r.get("toc_source") == "openalex-only"),
            "front_matter": reasons["front_matter"],
            "not_retrievable": reasons["not_retrievable"],
            "in_pool": n_pool,
            "candidates": sum(1 for r in recs if not r["in_pool"] and not exclusion_reason(r)),
            "unresolved": sum(1 for r in recs if r.get("toc_source") == "openalex-only"
                              and not r.get("doi")),
        })
    return rows
