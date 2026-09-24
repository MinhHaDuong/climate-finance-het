"""Give every collected JETP document a public Web Archive copy (ticket 0925).

The observatory links each document to the publisher's page it was collected
from. Publishers move and delete pages; the SHA-256 we recorded still proves
which bytes were read, but a reader who follows a dead link can no longer
reach them. This script asks the Internet Archive to hold a copy of each
collected page while it still exists, and records the answer in its own
table, ``data/jetp/web-archive-captures.csv`` — never in the collection
registry: one file is one table, and the site joins the two at read time on
the document's address.

For each collected document (a retrieval that kept bytes, from the ledger's
``retrievals.csv`` and the legacy ``manifest.csv`` a new harvest still writes)
and each address it was collected from:

1. an address on ``data.commoncrawl.org`` is a Common Crawl WARC, not a
   publisher's page: recorded ``not_applicable``, never captured;
2. the Wayback availability API is asked for the snapshot closest to the
   collection date; a 200 snapshot within ``--reuse-window-days`` (a year)
   of it is recorded ``reused``, and nothing new is requested;
3. otherwise Save Page Now is asked for a capture, and the job is followed
   to its end: ``captured`` with the snapshot's address and timestamp, or
   ``failed`` with the reason.

Save Page Now is asked with the project's Internet Archive account when
``~/.config/keys/archive.env`` holds ``IA_S3_ACCESS_KEY`` and
``IA_S3_SECRET_KEY``: each value is read just before the request that needs
it (``pipeline_keystore``), sent only as that request's ``Authorization:
LOW`` header, never logged, never written to the table. Authenticated, up to
three jobs run at once (the account's concurrency); without the file the run
is anonymous and serial, as it was first written — and anonymous capture was
refused with HTTP 401 from 2026-09-24.

The run is resumable and polite. A row already ``captured``, ``reused`` or
``not_applicable`` is skipped; a ``failed`` one is tried again. Requests are
paced (``--pace``), a rate limit (HTTP 429) backs off exponentially, and a
failure is recorded and the run moves on: one document never blocks the
rest. After ``--breaker`` consecutive connection failures to Save Page Now
the run stops requesting captures — it still reuses existing snapshots — and
records the remaining documents as failed with the reason
``wayback_unreachable``, so a rerun picks them up. The table is
rewritten atomically after every document, in key order, so an interrupted
run loses at most the document in flight.
"""

import argparse
import csv
import os
import re
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from pipeline_keystore import read_credential
from utils import get_logger

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / 'data/jetp'
FIELDS = ('source_id', 'url', 'outcome', 'capture_url', 'captured_at', 'attempted_at', 'error')
OUTCOMES = ('captured', 'reused', 'failed', 'not_applicable')
DONE = {'captured', 'reused', 'not_applicable'}
NOT_PUBLISHER_HOSTS = ('data.commoncrawl.org',)

AVAILABILITY = 'https://archive.org/wayback/available'
SAVE = 'https://web.archive.org/save'
STATUS = 'https://web.archive.org/save/status/'
REPLAY = 'https://web.archive.org/web/'
USER_AGENT = 'climate-finance-het JETP research corpus (Web Archive capture); contact: repository owner'
log = get_logger('jetp.corpus_web_archive_capture')
TIMESTAMP = re.compile(r'/web/(\d{14})')
JOB = re.compile(r'spn2-[0-9a-f]{20,}')
KEY_PROVIDER = 'archive'
KEY_NAMES = ('IA_S3_ACCESS_KEY', 'IA_S3_SECRET_KEY')
AUTHENTICATED_WORKERS = 3


def authorization(keys_dir=None):
    """The Save Page Now authorization header, or {} to stay anonymous.

    Read at each call, never cached, never logged: the values live in this
    one dictionary for the one request that sends it.
    """
    access, secret = (read_credential(KEY_PROVIDER, name, keys_dir=keys_dir) for name in KEY_NAMES)
    return {'Authorization': f'LOW {access}:{secret}'} if access and secret else {}


class Unreachable(Exception):
    """The Wayback host did not answer at all (connection or timeout)."""


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def iso(timestamp):
    """A 14-digit Wayback timestamp as an ISO instant."""
    return datetime.strptime(timestamp, '%Y%m%d%H%M%S').strftime('%Y-%m-%dT%H:%M:%SZ')


def replay_url(timestamp, url):
    return f'{REPLAY}{timestamp}/{url}'


def _read(path):
    if not Path(path).is_file():
        return []
    with open(path, encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def collected_documents(ledger_dir=LEDGER):
    """Every (source id, address, collection instant) that kept bytes, oldest first.

    The ledger's retrievals are what the Documents page serves; the legacy
    manifest is read too because the harvester still writes a new collection
    there first. A document collected several times from one address is one
    row, dated by its first collection.
    """
    found = {}
    for row in _read(Path(ledger_dir) / 'retrievals.csv'):
        if row.get('sha256') and row.get('final_url'):
            key = (row['document_id'], row['final_url'])
            found[key] = min(found.get(key, row['retrieved_at']), row['retrieved_at'])
    for row in _read(Path(ledger_dir) / 'manifest.csv'):
        if row.get('sha256') and row.get('final_url'):
            key = (row['source_id'], row['final_url'])
            found[key] = min(found.get(key, row['retrieved_at']), row['retrieved_at'])
    return [dict(source_id=s, url=u, collected_at=t) for (s, u), t in sorted(found.items())]


def read_captures(path):
    rows = _read(path)
    for row in rows:
        if row['outcome'] not in OUTCOMES:
            raise ValueError(f"{row['source_id']}: unknown outcome {row['outcome']!r}")
    return {(r['source_id'], r['url']): r for r in rows}


def write_captures(rows, path):
    """Rewrite the whole table in key order, atomically."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        for key in sorted(rows):
            writer.writerow({f: rows[key].get(f, '') for f in FIELDS})
    os.replace(tmp, path)


class Wayback:
    """The two Internet Archive services, paced, with backoff on rate limits."""

    def __init__(self, session=None, pace=15.0, lookup_pace=1.5, timeout=60,
                 poll_interval=10.0, poll_limit=240.0, backoff=(120, 300, 900),
                 submit_backoff=(20, 60, 180),
                 sleep=time.sleep, keys_dir=None):
        self.http = session or requests.Session()
        self.http.headers.setdefault('User-Agent', USER_AGENT)
        self.pace, self.lookup_pace, self.timeout = pace, lookup_pace, timeout
        self.poll_interval, self.poll_limit, self.backoff = poll_interval, poll_limit, backoff
        # An authenticated submission refused with 429 is mostly a collision
        # with the account's three concurrent jobs, freed within seconds of a
        # capture ending: it waits less than the services' general backoff.
        self.submit_backoff = submit_backoff
        self.sleep = sleep
        self.keys_dir = keys_dir
        # Submissions are paced across workers; polls run side by side.
        self._submit = threading.Lock()
        # Lookups too: the availability API rate-limits the machine, not a
        # worker (three workers pacing themselves drew 429s and 20-minute
        # backoffs on 2026-09-24).
        self._lookup = threading.Lock()

    @property
    def authenticated(self):
        return bool(authorization(self.keys_dir))

    def _request(self, method, url, backoff=None, **kwargs):
        """One request; a rate limit is waited out, a dead host raised."""
        for delay in (*(self.backoff if backoff is None else backoff), None):
            try:
                response = self.http.request(method, url, timeout=self.timeout, **kwargs)
            except (requests.ConnectionError, requests.Timeout) as exc:
                raise Unreachable(type(exc).__name__) from exc
            if response.status_code != 429 or delay is None:
                return response
            wait = response.headers.get('Retry-After', '')
            pause = max(delay, int(wait)) if wait.isdigit() else delay
            # Said, so a run waiting out a rate limit is not read as a hang.
            log.info('rate limited: %s %s; waiting %d s', method,
                     urlsplit(url).hostname + urlsplit(url).path.split('/save/status/')[0], pause)
            self.sleep(pause)
        return response

    def closest(self, url, collected_at):
        """The 200 snapshot closest to the collection date, or None.

        The availability API answers the same query with a snapshot one
        moment and with none the next (seen 2026-09-24, while the replay
        host was unreachable), and more often with none for a 14-digit
        timestamp. So it is asked for the collection day, then with no
        date; an empty answer after both is "none found", not "none exists".
        """
        for stamp in (re.sub(r'\D', '', collected_at)[:8], None):
            params = {'url': url, **({'timestamp': stamp} if stamp else {})}
            with self._lookup:
                response = self._request('GET', AVAILABILITY, params=params)
                self.sleep(self.lookup_pace)
            if response.status_code != 200:
                continue
            snapshot = (response.json().get('archived_snapshots') or {}).get('closest') or {}
            if snapshot.get('available') and str(snapshot.get('status')) == '200' \
                    and snapshot.get('timestamp'):
                return snapshot['timestamp']
        return None

    def save(self, url):
        """Ask Save Page Now for a capture; (timestamp, None) or (None, reason)."""
        with self._submit:
            response = self._request('POST', SAVE, backoff=self.submit_backoff,
                                     data={'url': url}, allow_redirects=False,
                                     headers={'Accept': 'application/json',
                                              **authorization(self.keys_dir)})
            self.sleep(self.pace)
        # An immediate answer: the snapshot's address in a header.
        for header in ('Content-Location', 'Location'):
            match = TIMESTAMP.search(response.headers.get(header, ''))
            if match:
                return match.group(1), None
        if response.status_code == 429:
            return None, 'rate_limited'
        if response.status_code >= 400:
            return None, f'save_http_{response.status_code}'
        job = None
        try:
            payload = response.json()
            job = payload.get('job_id')
            if not job and payload.get('message'):
                return None, 'save_refused: ' + str(payload['message'])[:160]
        except ValueError:
            match = JOB.search(response.text or '')
            job = match.group(0) if match else None
        if not job:
            return None, 'save_no_job'
        return self._follow(job)

    def _follow(self, job):
        waited = 0.0
        while waited <= self.poll_limit:
            self.sleep(self.poll_interval)
            waited += self.poll_interval
            response = self._request('GET', STATUS + job, headers={
                'Accept': 'application/json', **authorization(self.keys_dir)})
            if response.status_code != 200:
                continue
            status = response.json()
            if status.get('status') == 'success' and status.get('timestamp'):
                return status['timestamp'], None
            if status.get('status') == 'error':
                return None, 'save_error: ' + str(status.get('status_ext') or status.get('message') or 'unknown')[:160]
        return None, 'save_pending_timeout'


def within(timestamp, collected_at, days):
    captured = datetime.strptime(timestamp, '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
    collected = datetime.fromisoformat(collected_at.replace('Z', '+00:00'))
    if collected.tzinfo is None:
        collected = collected.replace(tzinfo=timezone.utc)
    return abs((captured - collected).days) <= days


def capture_one(document, wayback, reuse_window_days, save=True,
                skip_reason='wayback_unreachable', lookup_first=True):
    """The table row for one document, whatever happens to its capture.

    ``save=False`` is the tripped breaker: an existing snapshot is still
    looked up, but no new capture is requested of a host that stopped
    answering.
    """
    row = dict(source_id=document['source_id'], url=document['url'],
               capture_url='', captured_at='', attempted_at=now(), error='')
    if (urlsplit(document['url']).hostname or '') in NOT_PUBLISHER_HOSTS:
        return dict(row, outcome='not_applicable',
                    error='Common Crawl WARC record, not a publisher page')
    lookup, timestamp = '', None
    try:
        if lookup_first:
            timestamp = wayback.closest(document['url'], document['collected_at'])
    except Unreachable as exc:
        timestamp, lookup = None, f'; availability lookup unreachable ({exc})'
    if timestamp and within(timestamp, document['collected_at'], reuse_window_days):
        return dict(row, outcome='reused', capture_url=replay_url(timestamp, document['url']),
                    captured_at=iso(timestamp))
    if not save:
        return dict(row, outcome='failed', error=skip_reason + lookup)
    try:
        timestamp, reason = wayback.save(document['url'])
    except Unreachable as exc:
        timestamp, reason = None, f'wayback_unreachable ({exc})'
    if timestamp:
        return dict(row, outcome='captured', capture_url=replay_url(timestamp, document['url']),
                    captured_at=iso(timestamp))
    return dict(row, outcome='failed', error=reason + lookup)


def run(documents, output, wayback, reuse_window_days=365, breaker=5, limit=None,
        request_captures=True, workers=1):
    """Capture every document not yet done; the table is written after each one.

    ``workers`` documents are in flight at once (three when authenticated);
    their submissions are still paced one by one inside ``Wayback.save``.
    """
    rows = read_captures(output)
    pending = [d for d in documents
               if rows.get((d['source_id'], d['url']), {}).get('outcome') not in DONE]
    if limit is not None:
        pending = pending[:limit]
    log.info('%d collected documents, %d to capture, %d at a time',
             len(documents), len(pending), workers)
    state = {'unreachable': 0, 'done': 0}
    lock = threading.Lock()

    def one(document):
        key = (document['source_id'], document['url'])
        with lock:
            save = state['unreachable'] < breaker
            earlier = rows.get(key, {}).get('error', '')
        try:
            if request_captures:
                # A row Save Page Now itself refused was looked up in that
                # same attempt and nothing was found: ask for the capture.
                row = capture_one(document, wayback, reuse_window_days, save=save,
                                  lookup_first=not earlier.startswith('save_'))
            else:
                # Lookup only: a refusal already recorded (save_http_401 when
                # Save Page Now wants an account) is kept as the reason.
                row = capture_one(document, wayback, reuse_window_days, save=False,
                                  skip_reason=earlier if earlier.startswith('save_')
                                  else 'save_not_requested')
        except (requests.RequestException, ValueError) as exc:
            row = dict(source_id=key[0], url=key[1], outcome='failed', capture_url='',
                       captured_at='', attempted_at=now(),
                       error=f'{type(exc).__name__}: {exc}'[:160])
        with lock:
            # Only a capture request tells whether Save Page Now answers: a
            # reused snapshot or a Common Crawl row asked it nothing, and a row
            # the tripped breaker skipped says only 'wayback_unreachable'. Any
            # other answer -- a capture, a refusal, a rate limit, an unreadable
            # reply -- proves the host is up.
            if row['error'].startswith('wayback_unreachable ('):
                state['unreachable'] += 1
            elif row['outcome'] == 'captured' or (
                    row['outcome'] == 'failed'
                    and not row['error'].startswith('wayback_unreachable')):
                state['unreachable'] = 0
            rows[key] = row
            write_captures(rows, output)
            state['done'] += 1
            log.info('[%d/%d] %s: %s %s', state['done'], len(pending), key[0],
                     row['outcome'], row['error'])

    if workers <= 1:
        for document in pending:
            one(document)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(one, pending))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--ledger-dir', type=Path, default=LEDGER)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-id', action='append')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--pace', type=float,
                        help='seconds between Save Page Now submissions '
                             '(default 5 authenticated, 15 anonymous)')
    parser.add_argument('--reuse-window-days', type=int, default=365)
    parser.add_argument('--breaker', type=int, default=5)
    parser.add_argument('--no-save', action='store_true',
                        help='only look up existing snapshots; request no new capture '
                             '(anonymous Save Page Now answered HTTP 401 on 2026-09-24)')
    args = parser.parse_args(argv)
    documents = collected_documents(args.ledger_dir)
    if args.source_id:
        documents = [d for d in documents if d['source_id'] in set(args.source_id)]
    wayback = Wayback()
    authenticated = wayback.authenticated
    wayback.pace = args.pace if args.pace is not None else (5.0 if authenticated else 15.0)
    log.info('Save Page Now: %s', 'authenticated' if authenticated else 'anonymous')
    rows = run(documents, args.output, wayback,
               reuse_window_days=args.reuse_window_days, breaker=args.breaker, limit=args.limit,
               request_captures=not args.no_save,
               workers=AUTHENTICATED_WORKERS if authenticated else 1)
    counts = {}
    for row in rows.values():
        label = row['outcome'] if row['outcome'] != 'failed' else 'failed: ' + row['error'].split(' (')[0].split(':')[0]
        counts[label] = counts.get(label, 0) + 1
    for label, count in sorted(counts.items()):
        log.info('%5d  %s', count, label)
    return 0


if __name__ == '__main__':
    sys.exit(main())
