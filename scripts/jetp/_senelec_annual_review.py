"""Fail-closed checks for the bounded Senelec annual-report review."""

from __future__ import annotations

import hashlib
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

EDITION_FIELDS = (
    "inventory_id", "source_id", "edition", "raw_disposition",
    "extraction_disposition", "document_sha256", "candidate_count", "notes",
)
CANDIDATE_FIELDS = (
    "candidate_id", "source_id", "edition", "document_sha256", "locator",
    "candidate_type", "candidate_summary", "candidate_disposition",
    "verifiable_excerpt", "canonical_project_id", "reason",
)
RAW_DISPOSITIONS = {"raw_retained", "index_retained_file_not_retained"}
EXTRACTION_DISPOSITIONS = {"reviewed", "not_extracted"}


def _require(rows: Iterable[dict[str, str]], fields: tuple[str, ...], label: str) -> list[dict[str, str]]:
    material = list(rows)
    for row in material:
        optional = {"canonical_project_id", "document_sha256"}
        missing = [field for field in fields if field not in optional and not row.get(field, "").strip()]
        if missing:
            raise ValueError(f"missing {label} field: {', '.join(missing)}")
    return material


def validate_editions(rows: Iterable[dict[str, str]]) -> None:
    """Require exactly the six index editions and preserve non-retention."""
    material = _require(rows, EDITION_FIELDS, "edition")
    expected = {str(year) for year in range(2019, 2025)}
    if {row["edition"] for row in material} != expected or len(material) != len(expected):
        raise ValueError("review must account for each 2019--2024 annual edition exactly once")
    for row in material:
        year = int(row["edition"])
        if row["raw_disposition"] not in RAW_DISPOSITIONS:
            raise ValueError("invalid annual-report raw disposition")
        if row["extraction_disposition"] not in EXTRACTION_DISPOSITIONS:
            raise ValueError("invalid annual-report extraction disposition")
        if year < 2023 and (row["raw_disposition"], row["extraction_disposition"]) != (
            "index_retained_file_not_retained", "not_extracted"
        ):
            raise ValueError("2019--22 files were not retained and cannot be extracted")
        if year < 2023 and row["document_sha256"]:
            raise ValueError("unretained annual-report files cannot claim a raw-byte hash")
        if year >= 2023 and (row["raw_disposition"], row["extraction_disposition"]) != (
            "raw_retained", "reviewed"
        ):
            raise ValueError("retained annual reports must be reviewed")
        if year >= 2023 and not row["document_sha256"]:
            raise ValueError("retained annual-report files require a raw-byte hash")
        if int(row["candidate_count"]) < 0:
            raise ValueError("candidate count cannot be negative")


def validate_candidates(candidates: Iterable[dict[str, str]], editions: Iterable[dict[str, str]]) -> None:
    """Candidates remain leads until source evidence establishes exact identity."""
    material = _require(candidates, CANDIDATE_FIELDS, "candidate")
    edition_rows = list(editions)
    counts = {row["edition"]: int(row["candidate_count"]) for row in edition_rows}
    if any(row["candidate_disposition"] != "unresolved_no_identity" for row in material):
        raise ValueError("annual-report leads require exact identity before admission")
    if any(row["canonical_project_id"] for row in material):
        raise ValueError("annual-report candidates cannot be merged by similarity")
    observed = {edition: 0 for edition in counts}
    for row in material:
        if not row["document_sha256"]:
            raise ValueError("a reviewed candidate requires a raw-byte hash")
        if row["edition"] not in observed:
            raise ValueError("candidate refers to an unreviewed edition")
        observed[row["edition"]] += 1
    if observed != counts:
        raise ValueError("candidate count does not match edition review")


def extract_pdf_page(document: Path, page: int) -> str:
    """Extract one numbered PDF page locally, preserving the cited pagination."""
    result = subprocess.run(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(document), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _page_number(locator: str) -> int:
    match = re.fullmatch(r"PDF p\.(\d+)", locator)
    if not match:
        raise ValueError("candidate locator must be a single PDF page")
    return int(match.group(1))


def validate_candidate_evidence(
    candidates: Iterable[dict[str, str]],
    editions: Iterable[dict[str, str]],
    storage_root: Path,
    *,
    extract_page=extract_pdf_page,
) -> None:
    """Replay every candidate against its hashed local PDF page and excerpt."""
    edition_by_source = {
        (row["source_id"], row["edition"]): row
        for row in editions
        if row["raw_disposition"] == "raw_retained"
    }
    for candidate in candidates:
        key = (candidate["source_id"], candidate["edition"])
        edition = edition_by_source.get(key)
        if edition is None:
            raise ValueError("candidate source edition is not retained")
        expected_hash = edition["document_sha256"]
        if candidate["document_sha256"] != expected_hash:
            raise ValueError("candidate hash does not match its retained edition")
        document = storage_root / "objects" / expected_hash[:2] / f"{expected_hash}.pdf"
        if not document.is_file():
            raise ValueError("retained candidate PDF is unavailable")
        if hashlib.sha256(document.read_bytes()).hexdigest() != expected_hash:
            raise ValueError("retained candidate PDF hash does not match its edition")
        page = _page_number(candidate["locator"])
        try:
            text = extract_page(document, page)
        except (KeyError, subprocess.CalledProcessError) as exc:
            raise ValueError("candidate page cannot be extracted") from exc
        if candidate["verifiable_excerpt"] not in text:
            raise ValueError("candidate excerpt is not on its cited PDF page")
