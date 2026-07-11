"""Audit main.bib DOIs against Crossref: resolution + title/author match.

For every DOI-bearing entry in ``content/bibliography/main.bib`` this fetches
``api.crossref.org/works/<doi>`` and compares the entry's title and first-author
surname against the Crossref record. It catches the LLM-fabricated sub-class
(valid DOI, wrong paper) that DOI resolution alone misses — the class that
produced the ``delvenne2017`` / ``li2021`` / ``manne_richels1992`` errors.

Non-Crossref registrars (arXiv, figshare, Zenodo, Dryad, DataCite books) return
404 from the Crossref works endpoint by design; their prefixes are skipped so a
legitimate arXiv DOI is not reported as a dead identifier.

Verdicts per entry:
  OK                  resolves, title and first-author both match
  WRONG_PAPER         resolves (HTTP 200) but title similarity < threshold
  AUTHOR_MISMATCH     title matches but first-author surname differs (advisory)
  NOT_IN_CROSSREF     404 and prefix not a known non-Crossref registrar
  SKIP_REGISTRAR      non-Crossref prefix (arXiv/figshare/Zenodo/…), not checked
  NETWORK_ERROR       Crossref unreachable / timed out
  NO_DOI              entry carries no DOI

Run as a CLI to regenerate the report; import ``run_audit`` from the standing
test (``tests/test_bib_doi_title.py``).
"""

import argparse
import csv
import os
import re
import sys
import time
import unicodedata
from difflib import SequenceMatcher

import bibtexparser
import requests
from script_io_args import parse_io_args, validate_io
from utils import get_logger

log = get_logger("qa_bib_doi")

# Non-Crossref DOI registrars — Crossref's /works endpoint 404s on these by
# design, so a 404 here is not evidence of a wrong identifier.
NON_CROSSREF_PREFIXES = (
    "10.48550",  # arXiv
    "10.6084",   # figshare
    "10.5281",   # Zenodo
    "10.5061",   # Dryad
    "10.17605",  # OSF
)

TITLE_THRESHOLD = 0.60  # SequenceMatcher ratio below which titles are "different"
CROSSREF_WORKS = "https://api.crossref.org/works/"
MAILTO = "minh.haduong@gmail.com"  # Crossref polite pool

# Default bib path, relative to this file (scripts/ -> repo root -> deliverables/…).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BIB = os.path.join(_REPO_ROOT, "deliverables", "_shared", "bibliography", "main.bib")


def _delatex(text):
    r"""Collapse LaTeX accent macros so 'Barab{\'a}si' -> 'Barabasi'."""
    # {\'a}, \'{a}, \'a  ->  a   (accent command + its letter)
    text = re.sub(r"\\[`'^\"~=.]\{?(\w)\}?", r"\1", text)
    return text.replace("{", "").replace("}", "").replace("\\", "")


def _strip_accents(text):
    """Fold accents so 'Büchner' compares equal to 'Buchner'."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def normalize_title(title):
    """Lowercase, drop LaTeX/punctuation, collapse whitespace."""
    if not title:
        return ""
    t = _strip_accents(_delatex(title).lower())
    t = re.sub(r"[^a-z0-9 ]", " ", t)      # punctuation
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _fold_surname(surname):
    """Normalize a surname for comparison: LaTeX macros + accents + case folded."""
    return _strip_accents(_delatex(surname).lower()).strip()


def first_author_surname(author_field):
    """Best-effort last name of the first author from a bibtex author string.

    Handles 'Last, First and …' and 'First Last and …' orderings. Returns ''
    for a braced corporate author ('{Nature Climate Change}') so the caller
    skips the author check on entries with no personal first author.
    """
    if not author_field or author_field.lstrip().startswith("{"):
        return ""
    first = author_field.split(" and ")[0].strip()
    if "," in first:                       # 'Buchner, Barbara'
        surname = first.split(",")[0]
    else:                                  # 'Barbara Buchner'
        surname = first.split()[-1] if first.split() else ""
    return _fold_surname(surname)


def author_mismatch(bib_surname, cr_surname):
    """True when both surnames are present and differ after accent/LaTeX fold.

    Surname-token equality, not the old substring containment: "li" and "lin"
    are different authors and must be flagged, where ``bib not in cr`` let a
    short surname slip inside a longer one unreported (ticket 0196).

    Compared on the shorter trailing token run so a dropped particle is not a
    mismatch: ``first_author_surname`` yields only the last token of a
    "First Last" bib name ("Jan van der Berg" -> "berg") while Crossref keeps
    the particle ("van der Berg" -> "van der berg"); the tails ["berg"] match.
    A genuine short-surname swap still differs on its trailing token
    (["li"] != ["lin"]). Folding is idempotent, so callers may pass folded or
    raw surnames. Advisory only — AUTHOR_MISMATCH never gates CI.
    """
    bib = _fold_surname(bib_surname).split()
    cr = _fold_surname(cr_surname).split()
    if not bib or not cr:
        return False
    n = min(len(bib), len(cr))
    return bib[-n:] != cr[-n:]


PREFIX_MATCH_MIN_WORDS = 4  # a prefix only proves identity if it is substantial


def title_ratio(bib_title, crossref_title):
    """Similarity of two titles, subtitle-truncation tolerant.

    When one normalized title is a prefix of the other *and* the shorter one is
    at least ``PREFIX_MATCH_MIN_WORDS`` words, Crossref has merely dropped a
    subtitle — treat as a full match. The word floor matters: a short generic
    bib title ("Climate Policy") can be a prefix of an unrelated longer Crossref
    title ("Climate Policy in the EU"), so accepting *any* prefix would let a
    wrong DOI on a short title pass the hard WRONG_PAPER gate. Below the floor,
    and for non-prefix pairs, fall back to a SequenceMatcher ratio.
    """
    a = normalize_title(bib_title)
    b = normalize_title(crossref_title)
    if not a or not b:
        return 0.0
    if a.startswith(b) or b.startswith(a):
        shorter = a if len(a) <= len(b) else b
        if len(shorter.split()) >= PREFIX_MATCH_MIN_WORDS:
            return 1.0
    return SequenceMatcher(None, a, b).ratio()


def is_non_crossref(doi):
    return any(doi.startswith(p) for p in NON_CROSSREF_PREFIXES)


def crossref_lookup(doi, session, timeout=15):
    """Return (status, title, first_author_surname).

    status in {'ok', 'not_found', 'error'}. On 'ok', title and surname come from
    the Crossref record (surname may be '' when Crossref lists no authors).
    """
    url = CROSSREF_WORKS + requests.utils.quote(doi, safe="")
    try:
        resp = session.get(url, params={"mailto": MAILTO}, timeout=timeout)
    except requests.RequestException:
        return "error", "", ""
    if resp.status_code == 404:
        return "not_found", "", ""
    if resp.status_code != 200:
        return "error", "", ""
    try:
        msg = resp.json()["message"]
    except (ValueError, KeyError):
        return "error", "", ""
    titles = msg.get("title") or [""]
    cr_title = titles[0] if titles else ""
    authors = msg.get("author") or []
    cr_surname = ""
    if authors:
        fam = authors[0].get("family", "")
        cr_surname = _strip_accents(fam.lower()).strip()
    return "ok", cr_title, cr_surname


def _verdict(entry, session, delay):
    """Classify one bib entry. Returns a dict row."""
    key = entry.get("ID", "")
    doi = (entry.get("doi") or "").strip()
    bib_title = entry.get("title", "")
    bib_surname = first_author_surname(entry.get("author", ""))
    row = {
        "key": key,
        "doi": doi,
        "verdict": "",
        "title_ratio": "",
        "bib_title": bib_title,
        "crossref_title": "",
        "bib_author": bib_surname,
        "crossref_author": "",
    }
    if not doi:
        row["verdict"] = "NO_DOI"
        return row
    if is_non_crossref(doi):
        row["verdict"] = "SKIP_REGISTRAR"
        return row
    time.sleep(delay)
    status, cr_title, cr_surname = crossref_lookup(doi, session)
    row["crossref_title"] = cr_title
    row["crossref_author"] = cr_surname
    if status == "error":
        row["verdict"] = "NETWORK_ERROR"
        return row
    if status == "not_found":
        row["verdict"] = "NOT_IN_CROSSREF"
        return row
    ratio = title_ratio(bib_title, cr_title)
    row["title_ratio"] = f"{ratio:.2f}"
    if ratio < TITLE_THRESHOLD:
        row["verdict"] = "WRONG_PAPER"
    elif author_mismatch(bib_surname, cr_surname):
        row["verdict"] = "AUTHOR_MISMATCH"
    else:
        row["verdict"] = "OK"
    return row


def run_audit(bib_path=DEFAULT_BIB, delay=0.2, limit=None):
    """Audit every entry in ``bib_path``. Returns a list of verdict rows.

    ``delay`` throttles Crossref calls; ``limit`` caps entries checked (testing).
    """
    with open(bib_path, encoding="utf-8") as fh:
        db = bibtexparser.load(fh)
    session = requests.Session()
    session.headers["User-Agent"] = f"climate-finance-het bib-audit (mailto:{MAILTO})"
    rows = []
    entries = db.entries if limit is None else db.entries[:limit]
    for entry in entries:
        rows.append(_verdict(entry, session, delay))
    return rows


# Hard defects: a valid DOI pointing at the wrong paper, or a DOI Crossref
# cannot resolve. These are mechanically decidable and gate the standing test.
HARD_VERDICTS = {"WRONG_PAPER", "NOT_IN_CROSSREF"}
# Advisory: first-author surname differs. Noisy (compound surnames, corporate
# authors, name-order) — reported for human review, never auto-failing. The
# ticket notes this sub-class "cannot be fully automated".
ADVISORY_VERDICTS = {"AUTHOR_MISMATCH"}


def suspects(rows):
    """Rows with a hard, mechanically-decidable defect (wrong paper / dead DOI)."""
    return [r for r in rows if r["verdict"] in HARD_VERDICTS]


def advisories(rows):
    """Rows with a soft author-name mismatch — review, don't gate on these."""
    return [r for r in rows if r["verdict"] in ADVISORY_VERDICTS]


def main(argv=None):
    io_args, extra = parse_io_args(argv)
    validate_io(output=io_args.output)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=float, default=0.2,
                        help="Seconds between Crossref calls (politeness)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Cap entries checked (debugging)")
    args = parser.parse_args(extra)

    bib_path = io_args.input[0] if io_args.input else DEFAULT_BIB
    rows = run_audit(bib_path, delay=args.delay, limit=args.limit)

    with open(io_args.output, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    log.info("=== bib DOI audit ===")
    for verdict, n in sorted(counts.items()):
        log.info("  %-16s %d", verdict, n)
    bad = suspects(rows)
    if bad:
        log.info("\n=== hard defects (wrong paper / dead DOI) ===")
        for r in bad:
            log.info("  [%s] %s  ratio=%s", r["verdict"], r["key"], r["title_ratio"])
            log.info("      bib:      %s", r["bib_title"][:70])
            log.info("      crossref: %s", r["crossref_title"][:70])
    soft = advisories(rows)
    if soft:
        log.info("\n=== advisories (author-name mismatch — review manually) ===")
        for r in soft:
            log.info("  [%s] %s  bib=%s crossref=%s", r["verdict"], r["key"],
                     r["bib_author"], r["crossref_author"])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
