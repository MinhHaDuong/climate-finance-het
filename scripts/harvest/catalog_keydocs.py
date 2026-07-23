#!/usr/bin/env python3
"""Curated key-documents importer — UNFCCC / OECD DAC layer (ticket 0288).

Reads a curated seed list (config/unfccc_sources.yaml or
config/oecd_dac_sources.yaml), optionally fetches each document's PDF,
extracts its text (pdfplumber, with an ocrmypdf OCR fallback for scanned
pre-2007 material), derives an abstract-equivalent flagged as reconstructed,
and writes a per-source works catalog consumed by catalog_merge.

This is a durable, rerunnable Phase-1 source (author constraint, 2026-07-22):
PDFs and extracted text are cached under data/pool/keydocs/<source>/, so
reruns are incremental, and pre-placed PDFs (manual bulk export from portals
that block robots, e.g. OECD One) are picked up by the same path.

Dedup by design: seed entries must not carry DOIs — DOI'd works (notably OECD
10.1787 publications) enter via the academic-source path; catalog_merge
collapses any residual title+year overlap with the grey seed list.

Produces: data/catalogs/<source>_works.csv (via --output)

Usage:
    python scripts/harvest/catalog_keydocs.py \
        --input config/unfccc_sources.yaml --source-name unfccc \
        --output data/catalogs/unfccc_works.csv [--fetch]
"""

import argparse
import os
import re
import shutil
import subprocess

import pandas as pd
import yaml
from script_io_args import parse_io_args, validate_io
from utils import (
    POOL_DIR,
    WORKS_COLUMNS,
    get_logger,
    polite_get,
    save_csv,
)

log = get_logger("catalog_keydocs")

VALID_SOURCES = ("unfccc", "oecd")

DOC_CLASSES = {
    "unfccc": {
        "decision", "biennial_assessment", "fund_report", "inc",
        "submission", "negotiation_record",
    },
    "oecd": {
        "statistical_directive", "development_cooperation_report",
        "dac_document",
    },
}

REQUIRED_FIELDS = ("symbol", "title", "year", "body", "doc_class")

# Abstract-equivalent derivation
ABSTRACT_MAX_WORDS = 300
SUMMARY_HEADINGS = re.compile(
    r"^\s*(executive\s+summary|summary\s+and\s+recommendations|summary)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
# Below this many characters of extractable text the PDF is treated as
# scanned and routed to OCR.
MIN_TEXT_CHARS = 200

# UN/OECD cover-page masthead lines to drop before deriving a lead abstract:
# organisation banners, distribution notices, document symbols, dates,
# language notices, session headers, page markers.
BOILERPLATE_LINE = re.compile(
    r"^\s*("
    r"(?i:"
    r"united(\s*\|)?\s+nations.*"
    r"|general assembly"
    r"|distr\.?\s*(:)?\s*(general|limited)?"
    r"|general|limited"
    r"|original\s*:.*"
    r"|(fccc|dcd|a/ac)\S*.*"
    r"|\d{1,2}\s+\w+\s+\d{4}"
    r"|page\s+\d+"
    r")"
    # The ALL-CAPS banner branch stays OUTSIDE the (?i:) scope: made
    # case-insensitive it matches any prose line without digits or
    # periods, eating decision titles and preambles (PR #1085 review).
    r"|[A-Z][A-Z /,'()-]+"
    r")\s*$"
)

OCR_TIMEOUT_S = 1800

# Keywords rule (author decision, 2026-07-22): never faked from titles.
# An explicit keywords block on the first page is used verbatim; otherwise
# lexicon terms found in the text are joined; otherwise keywords stay empty.
# Disclosure travels in keywords_provenance ("extracted" / "generated:lexicon"),
# mirroring abstract_provenance.
FIRST_PAGE_CHARS = 3500

KEYWORDS_BLOCK = re.compile(
    r"^\s*(?:keywords?|mots[- ]cl[e\u00e9]s)\s*[:\uff1a]\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)

# Deterministic generation vocabulary, matched case-insensitively against the
# extracted text. Curated with the seed lists; promote to config/ if ticket
# 0304 grows it beyond a screenful.
KEYWORD_LEXICON = [
    "climate finance",
    "climate change",
    "adaptation",
    "mitigation",
    "loss and damage",
    "financial mechanism",
    "Green Climate Fund",
    "Global Environment Facility",
    "Adaptation Fund",
    "long-term finance",
    "biennial assessment",
    "official development assistance",
    "Rio markers",
    "blended finance",
    "capacity-building",
    "technology transfer",
]


def load_seed(path: str, source_name: str) -> list[dict]:
    """Load and validate a curated seed list. Fails loud on invalid entries."""
    assert source_name in VALID_SOURCES, f"unknown source: {source_name}"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    entries = data["documents"] if isinstance(data, dict) else data
    if not entries:
        raise ValueError(f"Empty seed list: {path}")

    valid_classes = DOC_CLASSES[source_name]
    seen = set()
    stems: dict[str, str] = {}
    for e in entries:
        for field in REQUIRED_FIELDS:
            if not e.get(field):
                raise ValueError(
                    f"Seed entry missing required field '{field}': {e}")
        if "doi" in e:
            raise ValueError(
                f"Seed entry {e['symbol']} carries a doi — DOI'd works enter "
                "via the academic-source path (OpenAlex), never through the "
                "key-documents layer (dedup by design, ticket 0288)")
        if e["doc_class"] not in valid_classes:
            raise ValueError(
                f"Unknown doc_class '{e['doc_class']}' for source "
                f"{source_name} in {e['symbol']} (valid: {sorted(valid_classes)})")
        if e["symbol"] in seen:
            raise ValueError(f"Duplicate symbol in seed: {e['symbol']}")
        seen.add(e["symbol"])
        stem = safe_filename(e["symbol"])
        if stem in stems:
            raise ValueError(
                f"Seed symbols {stems[stem]!r} and {e['symbol']!r} collapse to "
                f"the same pool filename stem {stem!r} — their cached PDFs "
                "would silently collide; disambiguate the symbols")
        stems[stem] = e["symbol"]
    log.info("Loaded %d validated seed entries from %s", len(entries), path)
    return entries


def safe_filename(symbol: str) -> str:
    """Turn a document symbol into a filesystem-safe stem."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", symbol).strip("_")


def fetch_pdf(url: str, dest: str) -> str:
    """Fetch a PDF to dest unless already cached. Returns a status string."""
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return "cached"
    if not url:
        return "no_url"
    try:
        # 3s delay: unfccc.int rate-arms its Incapsula wall against faster
        # crawls (observed 2026-07-23 — /resource/docs began serving challenge
        # pages mid-harvest at 1s delay with a concurrent classifier).
        # Wayback id_ snapshot URLs must be fetched verbatim: the pipeline's
        # mailto-param injection changes the snapshot URL key and turns an
        # existing capture into a 404 (observed 2026-07-23).
        if url.startswith("https://web.archive.org/"):
            import time as _time

            import requests as _requests
            headers = {"User-Agent": "ClimateFinancePipeline/1.0 "
                                     "(mailto:minh.haduong@gmail.com)"}
            resp = None
            for attempt in range(4):
                _time.sleep(3.0 + attempt * 60.0)  # wayback throttles hard
                resp = _requests.get(url, timeout=180, headers=headers)
                if resp.status_code not in (429, 503):
                    break
            resp.raise_for_status()
        else:
            resp = polite_get(url, delay=3.0)
    except Exception as e:
        log.warning("  fetch failed for %s: %s", url, e)
        return "failed"
    content = resp.content
    if not content.startswith(b"%PDF"):
        log.warning("  not a PDF (portal challenge page?): %s", url)
        return "not_pdf"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(content)
    return "fetched"


def extract_text(pdf_path: str) -> str:
    """Extract the text layer of a PDF with pdfplumber."""
    import pdfplumber  # deferred: heavy import, not needed metadata-only

    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()


def ocr_text(pdf_path: str, txt_path: str) -> str | None:
    """OCR a scanned PDF via ocrmypdf's sidecar output.

    Returns the OCR'ed text, or None if ocrmypdf is unavailable or fails
    (the caller records status 'needs_ocr' so the padme run can complete it).
    """
    if shutil.which("ocrmypdf") is None:
        log.warning("  ocrmypdf not on PATH — cannot OCR %s", pdf_path)
        return None
    out_pdf = txt_path + ".ocr.pdf"
    cmd = ["ocrmypdf", "--force-ocr", "--sidecar", txt_path, pdf_path, out_pdf]
    try:
        subprocess.run(cmd, check=True, capture_output=True,
                       timeout=OCR_TIMEOUT_S)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        log.warning("  OCR failed for %s: %s", pdf_path, e)
        return None
    finally:
        if os.path.exists(out_pdf):
            os.remove(out_pdf)
    with open(txt_path, encoding="utf-8") as f:
        return f.read()


def get_document_text(pdf_path: str, txt_cache_path: str) -> tuple[str, str]:
    """Return (text, status) for a fetched PDF, using the .txt cache.

    Status: cached | text_layer | ocr | needs_ocr
    """
    if os.path.exists(txt_cache_path) and os.path.getsize(txt_cache_path) > 0:
        with open(txt_cache_path, encoding="utf-8") as f:
            return f.read(), "cached"

    text = extract_text(pdf_path)
    if len(text) >= MIN_TEXT_CHARS:
        _write_text_cache(txt_cache_path, text)
        return text, "text_layer"

    ocred = ocr_text(pdf_path, txt_cache_path)
    if ocred and len(ocred.strip()) >= MIN_TEXT_CHARS:
        return ocred, "ocr"
    # ocrmypdf writes its sidecar to the cache path unconditionally; an
    # under-threshold stub left behind would be served as "cached" on the
    # next run instead of retrying the OCR.
    if os.path.exists(txt_cache_path):
        os.remove(txt_cache_path)
    return "", "needs_ocr"


def _write_text_cache(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def derive_abstract(text: str) -> tuple[str, str]:
    """Derive an abstract-equivalent from extracted document text.

    Prefers an executive-summary-type section; falls back to the lead of the
    document. Returns (abstract, method) where method is
    'reconstructed:exec_summary', 'reconstructed:lead', or '' when no text.
    """
    text = (text or "").strip()
    if not text:
        return "", ""

    m = SUMMARY_HEADINGS.search(text)
    if m:
        section = text[m.end():].strip()
        words = section.split()
        return " ".join(words[:ABSTRACT_MAX_WORDS]), "reconstructed:exec_summary"

    words = _strip_masthead(text).split()
    return " ".join(words[:ABSTRACT_MAX_WORDS]), "reconstructed:lead"


def _strip_masthead(text: str) -> str:
    """Drop cover-page boilerplate lines from the head of a document.

    Stops filtering at the first line of running prose so only the masthead
    is affected; falls back to the raw text if everything matched.
    """
    lines = text.splitlines()
    start = 0
    for i, line in enumerate(lines):
        if not line.strip():
            start = i + 1
            continue
        if BOILERPLATE_LINE.match(line.strip()):
            start = i + 1
            continue
        break
    remainder = "\n".join(lines[start:]).strip()
    return remainder or text


def derive_keywords(text: str) -> tuple[str, str]:
    """Derive (keywords, provenance) from extracted document text.

    First-page explicit keywords block wins ("extracted"); else lexicon terms
    present in the text ("generated:lexicon"); else empty — no text, no
    keywords (author rule, 2026-07-22).
    """
    if not text:
        return "", ""
    m = KEYWORDS_BLOCK.search(text[:FIRST_PAGE_CHARS])
    if m:
        return m.group(1).strip(), "extracted"
    low = text.lower()
    found = [term for term in KEYWORD_LEXICON if term.lower() in low]
    if found:
        return "; ".join(found), "generated:lexicon"
    return "", ""


def build_record(entry: dict, source_name: str, abstract: str | None,
                 abstract_provenance: str | None,
                 keywords: str | None = None,
                 keywords_provenance: str | None = None) -> dict:
    """Map a seed entry (+ derived abstract/keywords) onto the works-catalog
    schema."""
    if entry.get("abstract"):
        abstract = entry["abstract"]
        abstract_provenance = "curated"
    return {
        "source": source_name,
        "source_id": entry["symbol"],
        "doi": "",
        "title": entry["title"],
        "first_author": entry["body"],
        "all_authors": entry["body"],
        "year": str(entry["year"]),
        "journal": entry["body"],
        "abstract": abstract or "",
        "language": entry.get("language", "en"),
        "keywords": keywords or "",
        "categories": f"key documents; {entry['doc_class']}",
        "cited_by_count": "",
        "affiliations": entry["body"],
        "abstract_provenance": abstract_provenance or "",
        "keywords_provenance": keywords_provenance or "",
    }


def harvest_entry(entry: dict, source_name: str, pool_dir: str,
                  fetch: bool) -> dict:
    """Process one seed entry: optional fetch + extract + derive, then map.

    Contract: entries must come from load_seed() — schema fields are indexed
    directly, so a dict that skipped validation dies on a bare KeyError.
    """
    abstract, provenance = None, None
    keywords, kw_provenance = None, None
    if fetch and not entry.get("abstract"):
        stem = safe_filename(entry["symbol"])
        pdf_path = os.path.join(pool_dir, stem + ".pdf")
        txt_path = os.path.join(pool_dir, stem + ".txt")
        status = fetch_pdf(entry.get("url", ""), pdf_path)
        if status in ("cached", "fetched"):
            text, text_status = get_document_text(pdf_path, txt_path)
            abstract, provenance = derive_abstract(text)
            keywords, kw_provenance = derive_keywords(text)
            log.info("  %s: fetch=%s text=%s abstract=%s",
                     entry["symbol"], status, text_status,
                     provenance or "none")
        else:
            log.info("  %s: fetch=%s (no text)", entry["symbol"], status)
    return build_record(entry, source_name, abstract, provenance,
                        keywords, kw_provenance)


def main(argv=None):
    io_args, extra = parse_io_args(argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-name", required=True, choices=VALID_SOURCES,
                        help="Layer sub-list this seed belongs to")
    parser.add_argument("--fetch", action="store_true",
                        help="Fetch PDFs and derive abstract-equivalents "
                             "(network; run on padme)")
    parser.add_argument("--pool-dir", default=None,
                        help="PDF/text cache directory "
                             "(default: data/pool/keydocs/<source>)")
    args = parser.parse_args(extra)

    if not io_args.input or len(io_args.input) != 1:
        raise SystemExit("--input must name exactly one seed YAML file")
    validate_io(output=io_args.output, inputs=io_args.input)

    seed_path = io_args.input[0]
    pool_dir = args.pool_dir or os.path.join(POOL_DIR, "keydocs",
                                             args.source_name)

    entries = load_seed(seed_path, args.source_name)
    records = [harvest_entry(e, args.source_name, pool_dir, args.fetch)
               for e in entries]

    df = pd.DataFrame(records, columns=WORKS_COLUMNS + ["abstract_provenance"])
    save_csv(df, io_args.output)
    n_abs = (df["abstract"] != "").sum()
    log.info("Summary: %d %s key documents (%d with abstract-equivalent)",
             len(df), args.source_name, n_abs)


if __name__ == "__main__":
    main()
