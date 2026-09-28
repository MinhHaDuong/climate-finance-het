"""Record browser-saved JETP files as v2 retrievals and snapshots."""

import argparse
import logging
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from jetp import _firefox
from jetp.corpus_harvest_ledger import (
    _format,
    _valid_content,
    load_inputs,
    next_id,
    publish_attempts,
    store_object,
)

ROOT = Path(__file__).resolve().parents[2]
LOG = logging.getLogger(__name__)
MATERIAL = {'collected', 'not_modified'}
PARTIAL_SUFFIXES = ('.part', '.crdownload', '.tmp')


def normalise_url(url):
    parts = urlsplit(url.strip())
    path = parts.path.rstrip('/') or '/'
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ''))


def uncollected_documents(documents, attempts):
    latest = {}
    local_records = set()
    for row in attempts:
        latest[row['document_id']] = row['status']
        if row['collection_method'] == 'local-record':
            local_records.add(row['document_id'])
    wanted = {row['document_id']: row for row in documents
              if row['active'] == 'true' and row['document_id'] not in local_records
              and latest.get(row['document_id']) not in MATERIAL}
    index = {normalise_url(row['url']): row for row in wanted.values()}
    for row in attempts:
        if row['document_id'] in wanted and row['final_url']:
            index.setdefault(normalise_url(row['final_url']), wanted[row['document_id']])
    return index


def collect_downloads(ledger_dir, storage_root, downloads, origins, *, dry_run=False):
    """Use Firefox origin records; never match a filename by guesswork."""
    documents, attempts, snapshots = load_inputs(ledger_dir)
    index = uncollected_documents(documents, attempts)
    origins = {path.resolve(): url for path, url in origins.items()}
    rows, new_snapshots, skipped = [], [], []
    for path in sorted(Path(downloads).iterdir()):
        if not path.is_file() or path.name.startswith('.') or path.name.endswith(PARTIAL_SUFFIXES):
            continue
        origin = origins.get(path.resolve())
        if origin is None:
            skipped.append((path, 'no download origin recorded by Firefox'))
            continue
        document = index.get(normalise_url(origin))
        if document is None:
            skipped.append((path, 'origin matches no uncollected document'))
            continue
        identity = document['document_id']
        if any(row['document_id'] == identity for row in rows):
            skipped.append((path, f'{identity} already matched by another file'))
            continue
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or ''
        fmt = _format(document['url'], content_type)
        if error := _valid_content(body, fmt):
            skipped.append((path, f'{identity}: {error}'))
            continue
        timestamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(
            microsecond=0).isoformat().replace('+00:00', 'Z')
        digest, relative = ('', '') if dry_run else store_object(body, fmt, storage_root)
        rows.append(dict(retrieval_id=next_id(identity, attempts + rows),
                         document_id=identity, retrieved_at=timestamp,
                         status='collected', http_status='', content_type=content_type,
                         etag='', last_modified='', final_url=origin, error='',
                         sha256=digest, collection_method='browser-manual'))
        if not dry_run:
            new_snapshots.append(dict(sha256=digest, storage_path=relative,
                                      size_bytes=str(len(body)), content_type=content_type))
    if not dry_run:
        publish_attempts(ledger_dir, attempts, snapshots, rows, new_snapshots)
    return rows, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', '--ledger-dir', dest='ledger_dir', type=Path,
                        default=ROOT / 'data/jetp',
                        help='ledger directory receiving retrievals and snapshots')
    parser.add_argument('--storage-root', type=Path, default=ROOT / 'data/jetp/documents')
    parser.add_argument('--downloads-dir', type=Path)
    parser.add_argument('--firefox-profile', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    profile = args.firefox_profile or _firefox.default_profile()
    rows, skipped = collect_downloads(
        args.ledger_dir, args.storage_root,
        args.downloads_dir or _firefox.downloads_dir(),
        _firefox.download_origins(profile), dry_run=args.dry_run)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    LOG.info('%d matched downloads; %d left out', len(rows), len(skipped))
    for path, reason in skipped:
        LOG.info('%s: %s', path.name, reason)


if __name__ == '__main__':
    main()
