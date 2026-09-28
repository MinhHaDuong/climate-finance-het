"""Collect four-country, all-sector OECD CRS microdata into a DVC-only directory.

This is an explicit collection command, never a dependency of a render or
ledger build.  Each successful country-year response and its metadata are
retained so a resumed run does not silently mix response vintages.
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import logging
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from jetp.catalog_crs import BASE, COUNTRIES, UA, build_key

log = logging.getLogger(__name__)


def _fetch(url, attempts=5):
    request = urllib.request.Request(url, headers={'User-Agent': UA})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=900) as response:
                return response.read(), dict(response.headers)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise ValueError(f'CRS country-year URL returned 404: {url}') from exc
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
            log.warning('HTTP %d, retry %d/%d: %s', exc.code, attempt + 1, attempts, url)
        except (TimeoutError, urllib.error.URLError):
            if attempt == attempts - 1:
                raise
            log.warning('Network retry %d/%d: %s', attempt + 1, attempts, url)
        time.sleep(min(60, 5 * (attempt + 1)))
    raise AssertionError('unreachable')


def _metadata(raw, country, year, url, headers):
    if not raw:
        raise ValueError(f'{country} {year}: empty CRS response')
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''))
    fields = reader.fieldnames
    if not fields or len(fields) != 51:
        raise ValueError(f'{country} {year}: expected 51 CRS fields, got {fields}')
    rows = list(reader)
    if any(row['RECIPIENT'] != country or row['TIME_PERIOD'] != str(year)
           or row['MD_DIM'] != 'DD' for row in rows):
        raise ValueError(f'{country} {year}: response differs from requested slice')
    return {
        'country': country, 'year': year, 'url': url,
        'retrieved_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'response_sha256': hashlib.sha256(raw).hexdigest(),
        'response_bytes': len(raw), 'rows': len(rows),
        'price_q_rows': sum(row['PRICE_BASE'] == 'Q' for row in rows),
        'field_count': len(fields), 'etag': headers.get('ETag'),
        'last_modified': headers.get('Last-Modified'),
    }


def collect(output, countries=COUNTRIES, start=2005, end=2024, pause=10):
    """Return metadata for complete responses; stop on any partial failure."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / 'manifest.json'
    prior = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest = dict(prior)
    for country in countries:
        for year in range(start, end + 1):
            name = f'crs_{country}_{year}_micro.csv.gz'
            path = output / name
            if name in manifest and path.exists():
                raw = gzip.decompress(path.read_bytes())
                if hashlib.sha256(raw).hexdigest() != manifest[name]['response_sha256']:
                    raise ValueError(f'{path}: manifest hash mismatch')
                log.info('Already collected %s: %d rows', name, manifest[name]['rows'])
                continue
            key = build_key(RECIPIENT=country, MD_DIM='DD')
            url = (f'{BASE}{key}?startPeriod={year}&endPeriod={year}'
                   '&dimensionAtObservation=AllDimensions&format=csvfile')
            raw, headers = _fetch(url)
            metadata = _metadata(raw, country, year, url, headers)
            compressed = gzip.compress(raw, compresslevel=9, mtime=0)
            temp = path.with_suffix('.tmp')
            temp.write_bytes(compressed)
            temp.replace(path)
            manifest[name] = metadata
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
            log.info('Collected %s: %d rows, %d bytes', name, metadata['rows'], len(raw))
            time.sleep(pause)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--countries', nargs='+', default=COUNTRIES)
    parser.add_argument('--start', type=int, default=2005)
    parser.add_argument('--end', type=int, default=2024)
    parser.add_argument('--pause', type=float, default=10)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    collect(args.output, args.countries, args.start, args.end, args.pause)


if __name__ == '__main__':
    main()
