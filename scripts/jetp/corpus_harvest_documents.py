# WARNING: AI-generated, not human-reviewed
"""Harvest versioned JETP documents with an append-only provenance manifest.

The source registry is curated in git. Binary objects are content-addressed
under the storage root and are intended to be tracked by DVC. The manifest is
append-only: a refresh records a new material version or a ``not_modified``
check, without rewriting prior observations.
"""

import argparse
import csv
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from script_io_args import parse_io_args, validate_io
from urllib3.util.retry import Retry
from utils import get_logger

from jetp.schemas import (
    AUTHORITY_CATEGORIES,
    COUNTRIES,
    SOURCE_TYPES,
)

log = get_logger("jetp.corpus_harvest_documents")

REGISTRY_FIELDS = (
    "source_id",
    "country",
    "authority_category",
    "publisher",
    "source_type",
    "title",
    "published_date",
    "url",
    "project_id",
    "expected_format",
    "priority",
    "active",
    "notes",
)

MANIFEST_FIELDS = (
    "source_id",
    "country",
    "retrieved_at",
    "status",
    "http_status",
    "content_type",
    "etag",
    "last_modified",
    "sha256",
    "size_bytes",
    "storage_path",
    "final_url",
    "error",
)

EXPECTED_FORMATS = frozenset({"pdf", "html", "csv", "json", "xml", "other"})
ACTIVE_VALUES = {"true": True, "false": False}
DEFAULT_MAX_BYTES = 250 * 1024 * 1024


def _is_iso_date(value: str) -> bool:
    if not value:
        return True
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _require(row: dict[str, str], field: str, line: int) -> str:
    value = row.get(field, "").strip()
    if not value:
        raise ValueError(f"line {line}: missing {field}")
    return value


def _validate_registry_row(row: dict[str, str], line: int) -> dict[str, str]:
    source_id = _require(row, "source_id", line)
    country = _require(row, "country", line)
    if country not in COUNTRIES:
        raise ValueError(f"line {line}: invalid country {country!r}")
    authority = _require(row, "authority_category", line)
    if authority not in AUTHORITY_CATEGORIES:
        raise ValueError(f"line {line}: invalid authority_category {authority!r}")
    source_type = _require(row, "source_type", line)
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"line {line}: invalid source_type {source_type!r}")
    expected_format = _require(row, "expected_format", line)
    if expected_format not in EXPECTED_FORMATS:
        raise ValueError(f"line {line}: invalid expected_format {expected_format!r}")
    url = _require(row, "url", line)
    if urlparse(url).scheme not in {"http", "https"}:
        raise ValueError(f"line {line}: URL must use http or https")
    priority = _require(row, "priority", line)
    if priority not in {"1", "2", "3"}:
        raise ValueError(f"line {line}: priority must be 1, 2 or 3")
    active = _require(row, "active", line).lower()
    if active not in ACTIVE_VALUES:
        raise ValueError(f"line {line}: active must be true or false")
    published_date = row.get("published_date", "").strip()
    if not _is_iso_date(published_date):
        raise ValueError(f"line {line}: published_date must be YYYY-MM-DD or blank")
    _require(row, "publisher", line)
    _require(row, "title", line)
    clean = {field: row.get(field, "").strip() for field in REGISTRY_FIELDS}
    clean["active"] = active
    clean["source_id"] = source_id
    return clean


def load_registry(path: str | Path) -> list[dict[str, str]]:
    """Load and validate the curated source registry.

    Parameters
    ----------
    path
        CSV file containing one row per source URL.

    Returns
    -------
    list[dict[str, str]]
        Active and inactive validated registry rows.

    Raises
    ------
    ValueError
        If headers, controlled values, dates, URLs or identifiers are invalid.

    """
    with Path(path).open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(REGISTRY_FIELDS):
            raise ValueError(
                "source registry headers must be exactly: " + ",".join(REGISTRY_FIELDS)
            )
        rows = [_validate_registry_row(row, line) for line, row in enumerate(reader, 2)]
    identifiers = [row["source_id"] for row in rows]
    duplicates = sorted(
        {value for value in identifiers if identifiers.count(value) > 1}
    )
    if duplicates:
        raise ValueError(f"duplicate source_id values: {duplicates}")
    return rows


def _load_manifest(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(MANIFEST_FIELDS):
            raise ValueError("existing manifest has an incompatible schema")
        return list(reader)


def _latest_material_row(
    rows: list[dict[str, str]], source_id: str
) -> dict[str, str] | None:
    for row in reversed(rows):
        if row["source_id"] == source_id and row["sha256"]:
            return row
    return None


def _conditional_headers(previous: dict[str, str] | None) -> dict[str, str]:
    headers = {}
    if previous and previous["etag"]:
        headers["If-None-Match"] = previous["etag"]
    if previous and previous["last_modified"]:
        headers["If-Modified-Since"] = previous["last_modified"]
    return headers


def _extension(expected_format: str) -> str:
    return {
        "pdf": ".pdf",
        "html": ".html",
        "csv": ".csv",
        "json": ".json",
        "xml": ".xml",
        "other": ".bin",
    }[expected_format]


def _valid_content(body: bytes, expected_format: str) -> tuple[bool, str]:
    stripped = body.lstrip()
    if expected_format == "pdf" and not body.startswith(b"%PDF-"):
        return False, "expected PDF magic bytes"
    if expected_format == "html" and not stripped.lower().startswith(
        (b"<!doctype html", b"<html")
    ):
        return False, "expected HTML document"
    if not body:
        return False, "empty response body"
    return True, ""


def _read_body(response, max_bytes: int) -> bytes:
    length = response.headers.get("Content-Length", "")
    if length and int(length) > max_bytes:
        raise ValueError(f"content length {length} exceeds limit {max_bytes}")
    chunks = []
    size = 0
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        if not chunk:
            continue
        size += len(chunk)
        if size > max_bytes:
            raise ValueError(f"download exceeds limit {max_bytes}")
        chunks.append(chunk)
    return b"".join(chunks)


def _store_object(
    body: bytes, expected_format: str, storage_root: Path
) -> tuple[str, str]:
    digest = hashlib.sha256(body).hexdigest()
    relative = Path("objects") / digest[:2] / f"{digest}{_extension(expected_format)}"
    destination = storage_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        with tempfile.NamedTemporaryFile(
            dir=destination.parent, delete=False
        ) as stream:
            stream.write(body)
            temporary = Path(stream.name)
        os.replace(temporary, destination)
    return digest, relative.as_posix()


def _blank_manifest_row(source: dict[str, str], retrieved_at: str) -> dict[str, str]:
    return {
        "source_id": source["source_id"],
        "country": source["country"],
        "retrieved_at": retrieved_at,
        "status": "",
        "http_status": "",
        "content_type": "",
        "etag": "",
        "last_modified": "",
        "sha256": "",
        "size_bytes": "",
        "storage_path": "",
        "final_url": source["url"],
        "error": "",
    }


def _append_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def _status_for_http(status_code: int) -> str:
    if status_code in {401, 403}:
        return "blocked"
    if status_code in {404, 410}:
        return "missing"
    if status_code == 429 or status_code >= 500:
        return "retryable_http_error"
    return "http_error"


def _harvest_one(
    source: dict[str, str],
    previous: dict[str, str] | None,
    storage_root: Path,
    retrieved_at: str,
    session,
    max_bytes: int,
) -> dict[str, str]:
    row = _blank_manifest_row(source, retrieved_at)
    response = None
    try:
        response = session.get(
            source["url"],
            headers=_conditional_headers(previous),
            stream=True,
            timeout=(10, 60),
            allow_redirects=True,
        )
        row["http_status"] = str(response.status_code)
        row["final_url"] = response.url
        row["content_type"] = response.headers.get("Content-Type", "")
        row["etag"] = response.headers.get("ETag", "")
        row["last_modified"] = response.headers.get("Last-Modified", "")
        if response.status_code == 304:
            if not previous:
                row["status"] = "invalid_response"
                row["error"] = "304 response without a prior material version"
                return row
            row.update(
                {
                    "status": "not_modified",
                    "content_type": previous["content_type"],
                    "etag": row["etag"] or previous["etag"],
                    "last_modified": row["last_modified"] or previous["last_modified"],
                    "sha256": previous["sha256"],
                    "size_bytes": previous["size_bytes"],
                    "storage_path": previous["storage_path"],
                }
            )
            return row
        if not 200 <= response.status_code < 300:
            row["status"] = _status_for_http(response.status_code)
            row["error"] = f"HTTP {response.status_code}"
            return row
        body = _read_body(response, max_bytes)
        valid, error = _valid_content(body, source["expected_format"])
        if not valid:
            row["status"] = "invalid_content"
            row["error"] = error
            return row
        digest, storage_path = _store_object(
            body, source["expected_format"], storage_root
        )
        row["status"] = "collected"
        row["sha256"] = digest
        row["size_bytes"] = str(len(body))
        row["storage_path"] = storage_path
        return row
    except requests.RequestException as exc:
        row["status"] = "fetch_error"
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row
    except (OSError, ValueError) as exc:
        row["status"] = "invalid_content"
        row["error"] = str(exc)
        return row
    finally:
        if response is not None:
            response.close()


def harvest_registry(
    registry_path: str | Path,
    manifest_path: str | Path,
    storage_root: str | Path,
    *,
    source_ids: set[str] | None = None,
    retrieved_at: str | None = None,
    session=None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> list[dict[str, str]]:
    """Refresh every active source and append the observations to a manifest.

    Parameters
    ----------
    registry_path
        Curated source-registry CSV.
    manifest_path
        Append-only collection manifest CSV.
    storage_root
        Root of the content-addressed binary pool.
    source_ids
        Optional registered source identifiers to refresh. All active sources
        are refreshed when omitted.
    retrieved_at
        ISO timestamp supplied by deterministic tests; defaults to current UTC.
    session
        Requests-compatible session, injectable for tests.
    max_bytes
        Maximum accepted response size per document.

    Returns
    -------
    list[dict[str, str]]
        Manifest rows appended by this refresh.

    """
    registry = load_registry(registry_path)
    registered = {source["source_id"] for source in registry}
    unknown = sorted((source_ids or set()) - registered)
    if unknown:
        raise ValueError(f"unknown source_id values: {unknown}")
    manifest = Path(manifest_path)
    prior_rows = _load_manifest(manifest)
    storage = Path(storage_root)
    timestamp = retrieved_at or datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")
    http = session or make_session()
    new_rows = []
    for source in registry:
        if source["active"] != "true":
            continue
        if source_ids is not None and source["source_id"] not in source_ids:
            continue
        previous = _latest_material_row(prior_rows + new_rows, source["source_id"])
        row = _harvest_one(source, previous, storage, timestamp, http, max_bytes)
        new_rows.append(row)
        log.info("%s: %s", source["source_id"], row["status"])
    _append_manifest(manifest, new_rows)
    return new_rows


def make_session() -> requests.Session:
    """Return a polite HTTP session with bounded retries."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers["User-Agent"] = (
        "climate-finance-het JETP research corpus; contact: repository owner"
    )
    return session


def main(argv=None) -> None:
    """Run the document harvester from the command line."""
    io_args, extra = parse_io_args(argv)
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", required=True)
    parser.add_argument("--source-id", action="append")
    parser.add_argument("--retrieved-at")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    args = parser.parse_args(extra)
    if not io_args.input or len(io_args.input) != 1:
        parser.error("exactly one --input source registry is required")
    validate_io(output=io_args.output, inputs=io_args.input)
    harvest_registry(
        io_args.input[0],
        io_args.output,
        args.storage_root,
        source_ids=set(args.source_id) if args.source_id else None,
        retrieved_at=args.retrieved_at,
        max_bytes=args.max_bytes,
    )


if __name__ == "__main__":
    main()
