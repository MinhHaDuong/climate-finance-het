# WARNING: AI-generated, not human-reviewed
"""Pick up documents the author saved by hand in Firefox (ticket 0926).

Some publishers refuse the collector even with the author's cookies. The
author then opens the document in the browser and saves it; this command
scans the download directory, asks Firefox's ``places.sqlite`` where each
file was downloaded from, and matches that address to a registered source
whose latest attempt did not collect it. A matched file is fingerprinted,
stored content-addressed beside the harvested ones and recorded as a new
``collected`` manifest row with collection method ``browser-manual``.

Nothing is renamed or matched by hand, and nothing is ingested on a guess: a
file with no recorded origin, or whose origin names no uncollected source, is
reported and left where it is. The download directory itself is never
modified.
"""

import argparse
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from script_io_args import parse_io_args, validate_io
from utils import get_logger

from jetp import _firefox
from jetp.corpus_harvest_documents import (
    _append_manifest,
    _blank_manifest_row,
    _load_manifest,
    _store_object,
    _valid_content,
    load_registry,
)

log = get_logger("jetp.corpus_collect_downloads")

MATERIAL_STATUSES = frozenset({"collected", "not_modified"})
PARTIAL_SUFFIXES = (".part", ".crdownload", ".tmp")


def normalise_url(url: str) -> str:
    """Compare addresses without fragment, host case or a trailing slash."""
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def uncollected_sources(registry, manifest) -> dict[str, dict[str, str]]:
    """Index the active sources whose latest attempt kept no bytes, by address.

    A source answers to its registered URL and to the final URL of each of
    its recorded attempts, since a publisher often redirects.
    """
    latest = {row["source_id"]: row["status"] for row in manifest}
    wanted = {
        source["source_id"]: source for source in registry
        if source["active"] == "true"
        and latest.get(source["source_id"]) not in MATERIAL_STATUSES
    }
    index = {}
    for source in wanted.values():
        index.setdefault(normalise_url(source["url"]), source)
    for row in manifest:
        if row["source_id"] in wanted and row["final_url"]:
            index.setdefault(normalise_url(row["final_url"]), wanted[row["source_id"]])
    return index


def _candidate_files(downloads: Path) -> list[Path]:
    return sorted(
        path for path in downloads.iterdir()
        if path.is_file() and not path.name.startswith(".")
        and not path.name.endswith(PARTIAL_SUFFIXES)
    )


def _mtime_utc(path: Path) -> str:
    stamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    return stamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def collect_downloads(
    registry_path: str | Path,
    manifest_path: str | Path,
    storage_root: str | Path,
    downloads: Path,
    origins: dict[Path, str],
    *,
    dry_run: bool = False,
) -> tuple[list[dict[str, str]], list[tuple[Path, str]]]:
    """Match downloaded files to uncollected sources and record the matches.

    Parameters
    ----------
    registry_path
        Curated source-registry CSV.
    manifest_path
        Append-only collection manifest CSV.
    storage_root
        Root of the content-addressed binary pool.
    downloads
        Directory the browser saves files into.
    origins
        Downloaded file path to the address it was fetched from, as read from
        Firefox by ``_firefox.download_origins``.
    dry_run
        Report the matches without storing bytes or writing the manifest.

    Returns
    -------
    tuple[list[dict[str, str]], list[tuple[Path, str]]]
        The manifest rows appended, and each file left out with the reason.

    """
    registry = load_registry(registry_path)
    manifest = _load_manifest(Path(manifest_path))
    index = uncollected_sources(registry, manifest)
    resolved = {path.resolve(): url for path, url in origins.items()}
    rows, skipped = [], []
    for path in _candidate_files(downloads):
        origin = resolved.get(path.resolve())
        if origin is None:
            skipped.append((path, "no download origin recorded by Firefox"))
            continue
        source = index.get(normalise_url(origin))
        if source is None:
            skipped.append((path, "origin matches no uncollected source"))
            continue
        if any(row["source_id"] == source["source_id"] for row in rows):
            skipped.append((path, f"{source['source_id']} already matched by another file"))
            continue
        body = path.read_bytes()
        valid, error = _valid_content(body, source["expected_format"])
        if not valid:
            skipped.append((path, f"{source['source_id']}: {error}"))
            continue
        row = _blank_manifest_row(source, _mtime_utc(path), "browser-manual")
        row["final_url"] = origin
        row["content_type"] = mimetypes.guess_type(path.name)[0] or ""
        row["size_bytes"] = str(len(body))
        row["status"] = "collected"
        if dry_run:
            row["sha256"], row["storage_path"] = "", ""
        else:
            row["sha256"], row["storage_path"] = _store_object(
                body, source["expected_format"], Path(storage_root))
        rows.append(row)
    if not dry_run:
        _append_manifest(Path(manifest_path), rows)
    for row in rows:
        log.info("%s: collected from the downloads", row["source_id"])
    for path, reason in skipped:
        log.warning("not ingested: %s (%s)", path.name, reason)
    return rows, skipped


def main(argv=None) -> None:
    """Run the download pickup from the command line."""
    io_args, extra = parse_io_args(argv)
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", required=True)
    parser.add_argument("--downloads-dir", type=Path,
                        help="browser download directory; xdg-user-dir DOWNLOAD if omitted")
    parser.add_argument("--firefox-profile", type=Path,
                        help="Firefox profile directory; the default profile if omitted")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(extra)
    if not io_args.input or len(io_args.input) != 1:
        parser.error("exactly one --input source registry is required")
    validate_io(output=io_args.output, inputs=io_args.input)
    profile = args.firefox_profile or _firefox.default_profile()
    collect_downloads(
        io_args.input[0],
        io_args.output,
        args.storage_root,
        args.downloads_dir or _firefox.downloads_dir(),
        _firefox.download_origins(profile),
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
