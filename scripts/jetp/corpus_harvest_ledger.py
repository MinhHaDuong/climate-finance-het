"""Collect registered JETP documents into v2 retrievals and snapshots."""

import argparse
import hashlib
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from jetp import _firefox
from jetp._ledger_headers import load_schema, read_table, write_table

ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 250 * 1024 * 1024
GATE_TITLE = re.compile(rb'\blog ?in\b|\bsign ?in\b|just a moment|access denied|captcha', re.I)
HTML_TITLE = re.compile(rb'<title[^>]*>(.*?)</title>', re.I | re.S)
SUFFIXES = {'pdf': '.pdf', 'html': '.html', 'json': '.json',
            'csv': '.csv', 'xml': '.xml', 'other': '.bin'}


def _rows(ledger_dir, table, schema):
    values, errors = read_table(ledger_dir, table, schema)
    if errors:
        raise ValueError(f'{table}: {errors[0]}')
    return [{column: value or '' for column, value in zip(schema.header(table), row)}
            for row in values]


def load_inputs(ledger_dir):
    """Read current documents, attempts and snapshots with their schema headers."""
    schema = load_schema()
    return (_rows(ledger_dir, 'documents', schema),
            _rows(ledger_dir, 'retrievals', schema),
            _rows(ledger_dir, 'snapshots', schema))


def _ordinal(row):
    return int(row['retrieval_id'].rsplit(':', 1)[1])


def next_id(document_id, attempts):
    number = max((_ordinal(row) for row in attempts
                  if row['document_id'] == document_id), default=0) + 1
    return f'{document_id}:{number}'


def _format(url, content_type=''):
    suffix = Path(urlsplit(url).path).suffix.lower().lstrip('.')
    if suffix in SUFFIXES and suffix != 'other':
        return suffix
    content_type = content_type.lower()
    for mime, fmt in (('pdf', 'pdf'), ('html', 'html'), ('json', 'json'),
                      ('csv', 'csv'), ('xml', 'xml')):
        if mime in content_type:
            return fmt
    return 'other'


def _valid_content(body, fmt):
    if not body:
        return 'empty response body'
    if fmt == 'pdf' and not body.startswith(b'%PDF-'):
        return 'expected PDF magic bytes'
    if fmt == 'html':
        if not body.lstrip().lower().startswith((b'<!doctype html', b'<html')):
            return 'expected HTML document'
        title = HTML_TITLE.search(body[:65536])
        if title and GATE_TITLE.search(title.group(1)):
            return 'login or challenge page, not the document'
    return ''


def _body(response, limit):
    length = response.headers.get('Content-Length') or ''
    if length and int(length) > limit:
        raise ValueError(f'content length {length} exceeds limit {limit}')
    chunks, size = [], 0
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        size += len(chunk)
        if size > limit:
            raise ValueError(f'download exceeds limit {limit}')
        chunks.append(chunk)
    return b''.join(chunks)


def store_object(body, fmt, storage_root):
    digest = hashlib.sha256(body).hexdigest()
    relative = Path('objects') / digest[:2] / f'{digest}{SUFFIXES[fmt]}'
    destination = Path(storage_root) / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
            stream.write(body)
            temporary = Path(stream.name)
        os.replace(temporary, destination)
    return digest, relative.as_posix()


def _attempt(document, previous, retrieval_id, timestamp, session, storage_root,
             max_bytes, method):
    """Fetch one document and return its retrieval plus an optional snapshot."""
    row = dict(retrieval_id=retrieval_id, document_id=document['document_id'],
               retrieved_at=timestamp, status='', http_status='', content_type='',
               etag='', last_modified='', final_url=document['url'], error='',
               sha256='', collection_method=method)
    headers = {}
    if previous:
        if previous['etag']:
            headers['If-None-Match'] = previous['etag']
        if previous['last_modified']:
            headers['If-Modified-Since'] = previous['last_modified']
    response = None
    try:
        response = session.get(document['url'], headers=headers, stream=True,
                               timeout=(10, 60), allow_redirects=True)
        row.update(http_status=str(response.status_code), final_url=response.url,
                   content_type=response.headers.get('Content-Type', ''),
                   etag=response.headers.get('ETag', ''),
                   last_modified=response.headers.get('Last-Modified', ''))
        if response.status_code == 304:
            if not previous:
                row.update(status='invalid_response', error='304 without prior bytes')
            else:
                row.update(status='not_modified', sha256=previous['sha256'],
                           content_type=row['content_type'] or previous['content_type'],
                           etag=row['etag'] or previous['etag'],
                           last_modified=row['last_modified'] or previous['last_modified'])
            return row, None
        if not 200 <= response.status_code < 300:
            status = ('blocked' if response.status_code in (401, 403) else
                      'missing' if response.status_code in (404, 410) else
                      'retryable_http_error' if response.status_code == 429 or response.status_code >= 500
                      else 'http_error')
            row.update(status=status, error=f'HTTP {response.status_code}')
            return row, None
        body = _body(response, max_bytes)
        fmt = _format(response.url, row['content_type'])
        if fmt == 'other' and body.lstrip().lower().startswith((b'<!doctype html', b'<html')):
            fmt = 'html'
        elif fmt == 'other' and body.startswith(b'%PDF-'):
            fmt = 'pdf'
        if error := _valid_content(body, fmt):
            row.update(status='invalid_content', error=error)
            return row, None
        digest, relative = store_object(body, fmt, storage_root)
        row.update(status='collected', sha256=digest)
        snapshot = dict(sha256=digest, storage_path=relative,
                        size_bytes=str(len(body)), content_type=row['content_type'])
        return row, snapshot
    except requests.RequestException as exc:
        row.update(status='fetch_error', error=f'{type(exc).__name__}: {exc}')
        return row, None
    except (OSError, ValueError) as exc:
        row.update(status='invalid_content', error=str(exc))
        return row, None
    finally:
        if response is not None:
            response.close()


def publish_attempts(ledger_dir, attempts, snapshots, new_attempts, new_snapshots):
    """Publish snapshots first so every committed retrieval hash can resolve."""
    schema = load_schema()
    known = {row['sha256']: row for row in snapshots}
    for row in new_snapshots:
        if previous := known.get(row['sha256']):
            if previous['size_bytes'] != row['size_bytes']:
                raise ValueError(f'conflicting snapshot {row["sha256"]}')
        else:
            known[row['sha256']] = row
    if new_snapshots:
        write_table(ledger_dir, 'snapshots', list(known.values()), schema=schema)
    if new_attempts:
        write_table(ledger_dir, 'retrievals', attempts + new_attempts, schema=schema)


def harvest_documents(ledger_dir, storage_root, *, document_ids=None, statuses=None,
                      timestamp=None, session=None, session_factory=None,
                      method='script', delay=0, sleep=time.sleep, max_bytes=MAX_BYTES):
    """Append attempts for selected active documents without changing older rows."""
    documents, attempts, snapshots = load_inputs(ledger_dir)
    registered = {row['document_id'] for row in documents}
    if unknown := (document_ids or set()) - registered:
        raise ValueError(f'unknown document IDs: {sorted(unknown)}')
    latest = {}
    material = {}
    for row in sorted(attempts, key=_ordinal):
        latest[row['document_id']] = row
        if row['sha256']:
            material[row['document_id']] = row
    local_records = {row['document_id'] for row in attempts
                     if row['collection_method'] == 'local-record'}
    if blocked := (document_ids or set()) & local_records:
        raise ValueError(f'local-record documents are not HTTP harvest targets: {sorted(blocked)}')
    selected = [row for row in documents if row['active'] == 'true'
                and row['document_id'] not in local_records
                and (document_ids is None or row['document_id'] in document_ids)
                and (statuses is None or latest.get(row['document_id'], {}).get('status') in statuses)]
    http = session or (session_factory([row['url'] for row in selected])
                       if session_factory else make_session())
    timestamp = timestamp or datetime.now(timezone.utc).replace(
        microsecond=0).isoformat().replace('+00:00', 'Z')
    new_attempts, new_snapshots = [], []
    for index, document in enumerate(selected):
        if index and delay:
            sleep(delay)
        identity = document['document_id']
        row, snapshot = _attempt(document, material.get(identity),
                                 next_id(identity, attempts + new_attempts),
                                 timestamp, http, storage_root, max_bytes, method)
        new_attempts.append(row)
        if snapshot:
            new_snapshots.append(snapshot)
            material[identity] = row
    publish_attempts(ledger_dir, attempts, snapshots, new_attempts, new_snapshots)
    return new_attempts


def make_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
                    allowed_methods=('GET',), respect_retry_after_header=True)
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers['User-Agent'] = 'climate-finance-het JETP research corpus; contact: repository owner'
    return session


def browser_session(profile, urls):
    session = make_session()
    hosts = {urlsplit(url).hostname or '' for url in urls} - {''}
    session.cookies.update(_firefox.load_cookies(profile, hosts))
    session.headers['User-Agent'] = _firefox.user_agent(profile)
    session.headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    session.headers['Accept-Language'] = 'en-US,en;q=0.5'
    return session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger-dir', type=Path, default=ROOT / 'data/jetp')
    parser.add_argument('--storage-root', type=Path, default=ROOT / 'data/jetp/documents')
    parser.add_argument('--document-id', action='append')
    parser.add_argument('--only-status', action='append')
    parser.add_argument('--browser-session', action='store_true')
    parser.add_argument('--firefox-profile', type=Path)
    parser.add_argument('--delay', type=float)
    parser.add_argument('--max-bytes', type=int, default=MAX_BYTES)
    args = parser.parse_args()
    factory = None
    if args.browser_session:
        profile = args.firefox_profile or _firefox.default_profile()
        factory = lambda urls: browser_session(profile, urls)
    harvest_documents(args.ledger_dir, args.storage_root,
                      document_ids=set(args.document_id) if args.document_id else None,
                      statuses=set(args.only_status) if args.only_status else None,
                      session_factory=factory,
                      method='browser-session' if args.browser_session else 'script',
                      delay=args.delay if args.delay is not None else (2.5 if args.browser_session else 0),
                      max_bytes=args.max_bytes)


if __name__ == '__main__':
    main()
