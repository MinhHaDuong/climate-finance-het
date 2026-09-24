"""Check that each publisher address the observatory links still answers (ticket 0925).

Every document on the site links to the page it was collected from. This
check asks each of those addresses, politely, whether it is still there, and
records the answer in its own table, ``data/jetp/publisher-link-checks.csv``:
one row per address, updated in place, so git history holds the month-by-
month record and the file stays one table of the current state. The site
joins it on the document's address at read time; the collection registry and
the address it records are never touched.

An address is asked with HEAD, then with GET (body never read) when HEAD is
refused or unanswered. The outcome is one of

- ``alive``: a 2xx answer once redirects are followed (a 3xx only where the
  redirect could not be followed further);
- ``dead``: HTTP 404 or 410, or the page's own host name no longer resolves — the
  publisher says the page is gone, or the publisher is gone;
- ``unreachable``: anything else (403 to robots, 5xx, timeout, TLS error).
  A page a server refuses to show a script is not a dead page, and a bad
  night is not a death: neither is displayed as one.

``dead_since`` is the check date at which an address was first found dead
in its current unbroken run of dead checks; an ``unreachable`` check neither
starts nor ends the run, and an ``alive`` one ends it. The check is meant
to run monthly on padme (``make jetp-link-check``;
``deliverables/jetp-observatory/README.md`` § Web Archive copies and link
checks).
"""

import argparse
import csv
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from utils import get_logger

log = get_logger('jetp.corpus_check_publisher_links')

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / 'data/jetp'
FIELDS = ('url', 'checked_at', 'method', 'http_status', 'outcome', 'dead_since', 'error')
OUTCOMES = ('alive', 'dead', 'unreachable')
DEAD_STATUS = {404, 410}
USER_AGENT = 'climate-finance-het JETP research corpus (link check); contact: repository owner'
UNRESOLVED = ('NameResolutionError', 'Name or service not known', 'nodename nor servname',
              'getaddrinfo failed', 'No address associated with hostname')


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _read(path):
    if not Path(path).is_file():
        return []
    with open(path, encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def publisher_urls(ledger_dir=LEDGER):
    """Every address a document was collected from, as the site links it."""
    urls = {row['final_url'] for row in _read(Path(ledger_dir) / 'retrievals.csv')}
    urls |= {row['final_url'] for row in _read(Path(ledger_dir) / 'manifest.csv')}
    return sorted(u for u in urls if u and u.lower().startswith(('http://', 'https://')))


def read_checks(path):
    rows = _read(path)
    for row in rows:
        if row['outcome'] not in OUTCOMES:
            raise ValueError(f"{row['url']}: unknown outcome {row['outcome']!r}")
    return {row['url']: row for row in rows}


def write_checks(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        for url in sorted(rows):
            writer.writerow({f: rows[url].get(f, '') for f in FIELDS})
    os.replace(tmp, path)


def classify(status):
    if status is not None and status < 400:
        return 'alive'
    return 'dead' if status in DEAD_STATUS else 'unreachable'


def probe(http, url, timeout=30):
    """(method, status, outcome, error) for one address: HEAD, then GET."""
    method, status, error = 'HEAD', None, ''
    try:
        response = http.head(url, timeout=timeout, allow_redirects=True)
        status = response.status_code
    except requests.RequestException as exc:
        error = f'{type(exc).__name__}: {exc}'
    if status is None or status >= 400:
        method = 'GET'
        try:
            with http.get(url, timeout=timeout, allow_redirects=True, stream=True) as response:
                status, error = response.status_code, ''
        except requests.RequestException as exc:
            status, error = None, f'{type(exc).__name__}: {exc}'
    # Only the publisher's own host counts: a server that redirects a script to
    # an unresolvable name (www.unitedtractors.com sends it to no.access,
    # 2026-09-24) is refusing the robot, not gone.
    host = urlsplit(url).hostname or ''
    if status is None and any(marker in error for marker in UNRESOLVED) \
            and f"host='{host}'" in error:
        return method, None, 'dead', 'host name does not resolve: ' + error[:200]
    return method, status, classify(status), error[:240]


def check_one(http, url, previous, checked_at):
    method, status, outcome, error = probe(http, url)
    dead_since = ''
    if outcome == 'dead':
        dead_since = previous.get('dead_since') or checked_at[:10]
    elif outcome == 'unreachable':
        dead_since = previous.get('dead_since', '')
    return dict(url=url, checked_at=checked_at, method=method,
                http_status='' if status is None else str(status),
                outcome=outcome, dead_since=dead_since, error=error)


def run(urls, output, http=None, pace=1.5, sleep=time.sleep, checked_at=None):
    """Check every address; the table is rewritten after each one."""
    http = http or requests.Session()
    http.headers.setdefault('User-Agent', USER_AGENT)
    rows = read_checks(output)
    for n, url in enumerate(urls, 1):
        rows[url] = check_one(http, url, rows.get(url, {}), checked_at or now())
        write_checks(rows, output)
        log.info('[%d/%d] %s %s %s', n, len(urls), rows[url]['outcome'],
                 rows[url]['http_status'], url)
        if n < len(urls):
            sleep(pace)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--ledger-dir', type=Path, default=LEDGER,
                        help='where retrievals.csv and manifest.csv are read')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pace', type=float, default=1.5, help='seconds between requests')
    args = parser.parse_args(argv)
    rows = run(publisher_urls(args.ledger_dir), args.output, pace=args.pace)
    for outcome in OUTCOMES:
        log.info('%5d  %s', sum(r['outcome'] == outcome for r in rows.values()), outcome)
    return 0


if __name__ == '__main__':
    sys.exit(main())
