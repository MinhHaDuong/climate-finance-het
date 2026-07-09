#!/usr/bin/env python3
"""Audit that each local PDF's *content* matches its bib entry's title.

`tests/test_cited_works_available.py` gates cite => *presence* of a `file=` PDF,
not that the PDF is the right work. A mis-downloaded file saved under the wrong
key (e.g. lepenies2016.pdf once held *Taste as Experience* instead of *The Power
of a Single Number*) passes that gate silently. This script closes the gap: for
every bib entry with a `file=` field it extracts a title signal from the PDF
(pdfinfo metadata Title + first-page text) and fuzzily compares it to the bib
`title`, printing a mismatch table ranked worst-first for HUMAN verification.

Scanned PDFs carry no reliable metadata and often no extractable text, so a low
score is a *flag for human check*, never grounds for auto-replacement. Mismatches
under a *cited* key are the real hazard (a wrong-file citation in the manuscript)
and are marked specially.

Lightweight by design: shells out to poppler's `pdfinfo` / `pdftotext` CLIs; no
heavy PDF dependency. Matching logic is pure and unit-tested in
`tests/test_audit_pdf_content.py`. Author-run via `make audit-pdf-content` — not
a CI gate, because scanned PDFs make the flag list inherently human-verified.
"""

import argparse
import csv
import logging
import os
import re
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Default to the MAIN checkout: gitignored PDFs do not travel into worktrees.
DEFAULT_ARTICLES_DIR = (
    "/home/haduong/CNRS/projets/actifs/climate-finance-het/docs/articles"
)
DEFAULT_BIB = "content/bibliography/main.bib"
DEFAULT_QMD_GLOBS = ["content/*.qmd", "content/**/*.qmd"]

# Reuse the citation-key / entry-head patterns from test_cited_works_available.
CITE = re.compile(r"(?<!\w)@([\w][\w:.\-+/]*)")
ENTRY_HEAD = re.compile(r"(?m)^@[a-zA-Z]+\{([^,]+),")

# Short function words carry no discriminating signal for title containment.
_STOPWORDS = frozenset(
    "the a an of and or for to in on at by with from as is are be into"
    " über the und der die das von im le la les de des du et".split()
)


# --------------------------------------------------------------------------- #
# Pure matching logic (unit-tested without touching real PDFs).
# --------------------------------------------------------------------------- #
def normalize(text: str) -> str:
    """Lowercase, strip diacritics-insensitively nothing, collapse to words."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def significant_tokens(text: str) -> set[str]:
    """Content tokens (>= 4 chars, not stopwords) for containment scoring."""
    return {
        t for t in normalize(text).split()
        if len(t) >= 4 and t not in _STOPWORDS
    }


def seq_ratio(a: str, b: str) -> float:
    """SequenceMatcher ratio over normalized strings (0..1)."""
    a, b = normalize(a), normalize(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def containment(title: str, text: str) -> float:
    """Fraction of the title's significant tokens present in `text`.

    Robust to the PDF's first page holding the title amid other front-matter:
    what matters is whether the title's content words appear, not their order.
    """
    title_tokens = significant_tokens(title)
    if not title_tokens:
        return 0.0
    text_tokens = significant_tokens(text)
    return len(title_tokens & text_tokens) / len(title_tokens)


def match_score(bib_title: str, meta_title: str, page_text: str) -> float:
    """Best title-match evidence in [0, 1]: max of metadata ratio and
    first-page-text containment. High => PDF content agrees with bib title.
    """
    return max(
        seq_ratio(bib_title, meta_title),
        containment(bib_title, page_text),
    )


# --------------------------------------------------------------------------- #
# Bib + citation parsing.
# --------------------------------------------------------------------------- #
def parse_bib(bib_path: Path) -> dict[str, dict[str, str]]:
    """Return {key: {"title": ..., "file": ...}} for entries with a file= field."""
    text = bib_path.read_text(encoding="utf-8")
    entries: dict[str, dict[str, str]] = {}
    for chunk in re.split(r"(?m)^(?=@[a-zA-Z]+\{)", text):
        m = ENTRY_HEAD.match(chunk)
        if not m:
            continue
        key = m.group(1).strip()
        fm = re.search(r"(?mi)^\s*file\s*=\s*\{([^}]*)\}", chunk)
        if not fm:
            continue
        tm = re.search(r"(?mi)^\s*title\s*=\s*[{\"](.+?)[}\"]\s*,?\s*$", chunk)
        title = tm.group(1) if tm else ""
        # Strip nested braces used for capitalization protection.
        title = title.replace("{", "").replace("}", "").strip()
        entries[key] = {"title": title, "file": fm.group(1).strip()}
    return entries


def cited_keys(root: Path, globs: list[str]) -> set[str]:
    keys: set[str] = set()
    for pat in globs:
        for f in root.glob(pat):
            for m in CITE.findall(f.read_text(encoding="utf-8", errors="ignore")):
                keys.add(m.rstrip(".,;:"))
    return keys


# --------------------------------------------------------------------------- #
# PDF title-signal extraction (poppler CLIs).
# --------------------------------------------------------------------------- #
def pdf_meta_title(pdf_path: Path) -> str:
    try:
        out = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True, text=True, timeout=30,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return ""
    for line in out.splitlines():
        if line.startswith("Title:"):
            title = line.split(":", 1)[1].strip()
            # Discard the common junk metadata that is not the work's title.
            if title.lower().startswith("microsoft word"):
                return ""
            return title
    return ""


def pdf_first_page_text(pdf_path: Path, chars: int = 2000) -> str:
    try:
        out = subprocess.run(
            ["pdftotext", "-f", "1", "-l", "1", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=60,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return ""
    return out[:chars]


def resolve_pdf(articles_dir: Path, file_field: str) -> Path:
    """A file= field is `docs/articles/<name>.pdf`; map it onto articles_dir."""
    return articles_dir / Path(file_field).name


# --------------------------------------------------------------------------- #
# Audit driver.
# --------------------------------------------------------------------------- #
def audit(articles_dir: Path, bib_path: Path, root: Path, globs: list[str]):
    entries = parse_bib(bib_path)
    cited = cited_keys(root, globs)
    rows = []
    for key, info in sorted(entries.items()):
        pdf = resolve_pdf(articles_dir, info["file"])
        if not pdf.exists():
            rows.append({
                "key": key, "cited": key in cited, "score": -1.0,
                "bib_title": info["title"], "pdf_signal": "<PDF MISSING>",
            })
            continue
        meta = pdf_meta_title(pdf)
        page = pdf_first_page_text(pdf)
        score = match_score(info["title"], meta, page)
        signal = meta or " ".join(page.split())[:80]
        rows.append({
            "key": key, "cited": key in cited, "score": round(score, 3),
            "bib_title": info["title"], "pdf_signal": signal or "<NO TEXT>",
        })
    rows.sort(key=lambda r: (r["score"], not r["cited"]))
    return rows


def write_report(rows, output: str):
    with open(output, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh, fieldnames=["key", "cited", "score", "bib_title", "pdf_signal"]
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)


def print_table(rows, threshold: float):
    flagged = [r for r in rows if 0 <= r["score"] < threshold]
    missing = [r for r in rows if r["score"] < 0]
    cited_hazards = [r for r in flagged if r["cited"]]
    logger.info("Audited %d PDF-bearing bib entries.", len(rows))
    logger.info(
        "Flagged %d below score %.2f (%d cited hazards, %d missing PDFs).\n",
        len(flagged), threshold, len(cited_hazards), len(missing),
    )
    logger.info("%-6s %-28s %-40s %s", "SCORE", "KEY", "BIB TITLE", "PDF SIGNAL")
    logger.info("%s", "-" * 110)
    for r in flagged:
        mark = "!!CITED" if r["cited"] else ""
        logger.info(
            "%-6s %-28s %-40s %s %s",
            f"{r['score']:.3f}", r["key"][:28], r["bib_title"][:40],
            r["pdf_signal"][:40], mark,
        )
    if cited_hazards:
        logger.info("\n=== CITED-KEY MISMATCHES (human re-acquisition needed) ===")
        for r in cited_hazards:
            logger.info("  %s (score %.3f): bib=%r vs pdf=%r",
                        r["key"], r["score"], r["bib_title"], r["pdf_signal"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True,
        help="CSV report path (required; full audit including passing entries)",
    )
    parser.add_argument(
        "--articles-dir", default=DEFAULT_ARTICLES_DIR,
        help="Directory holding the PDFs (default: main-checkout docs/articles)",
    )
    parser.add_argument(
        "--bib", default=DEFAULT_BIB,
        help="BibTeX file with file= fields (default: content/bibliography/main.bib)",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.30,
        help="Flag entries scoring below this (default: 0.30)",
    )
    args = parser.parse_args(argv)

    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.isdir(out_dir):
        raise FileNotFoundError(f"Output directory does not exist: {out_dir}")

    root = Path(__file__).resolve().parent.parent
    bib_path = Path(args.bib)
    if not bib_path.is_absolute():
        bib_path = root / bib_path
    articles_dir = Path(args.articles_dir)

    rows = audit(articles_dir, bib_path, root, DEFAULT_QMD_GLOBS)
    write_report(rows, args.output)
    print_table(rows, args.threshold)
    logger.info("\nFull report written to %s", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
