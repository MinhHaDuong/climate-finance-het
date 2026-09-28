"""Materialize DVC-only all-sector CRS source lines in a disposable ledger SQLite.

The base SQLite comes from ``build_ledger.py``. This explicit second step
adds no CSV ledger rows and never runs during a render or an earlier phase.
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import logging
import os
import sqlite3
from pathlib import Path

from jetp._ledger_headers import LEDGER_DIR

log = logging.getLogger(__name__)
BULK_DIR = LEDGER_DIR / 'crs-bulk'
REVIEW_MANIFEST = LEDGER_DIR / 'comparison/crs/bulk-manifest.json'
COUNTRIES = {'IDN', 'SEN', 'VNM', 'ZAF'}
DIMENSIONS = ('DONOR', 'RECIPIENT', 'SECTOR', 'MEASURE', 'CHANNEL',
              'MODALITY', 'FLOW_TYPE', 'PRICE_BASE', 'MD_DIM', 'MD_ID',
              'UNIT_MEASURE')


def _manifest(bulk_dir, review_manifest, require_full):
    original = (bulk_dir / 'manifest.json').read_bytes()
    if original != review_manifest.read_bytes():
        raise ValueError('DVC bulk manifest differs from the reviewed Git copy')
    manifest = json.loads(original)
    if not isinstance(manifest, dict):
        raise ValueError('CRS bulk manifest is not a file map')
    expected = {f'crs_{country}_{year}_micro.csv.gz'
                for country in COUNTRIES for year in range(2005, 2025)}
    if require_full and set(manifest) != expected:
        raise ValueError('CRS bulk manifest is not the 80 four-country/year files')
    return manifest


def _rows(path, item):
    compressed = path.read_bytes()
    raw = gzip.decompress(compressed)
    if (hashlib.sha256(raw).hexdigest() != item['response_sha256'] or
            len(raw) != item['response_bytes']):
        raise ValueError(f'{path}: response differs from reviewed manifest')
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''))
    fields = reader.fieldnames
    if not fields or len(fields) != item['field_count'] or len(fields) != 51:
        raise ValueError(f'{path}: expected 51 source fields')
    rows = list(reader)
    if (len(rows) != item['rows'] or
            sum(row['PRICE_BASE'] == 'Q' for row in rows) != item['price_q_rows']):
        raise ValueError(f'{path}: row counts differ from reviewed manifest')
    if any(row['RECIPIENT'] != item['country'] or
           row['TIME_PERIOD'] != str(item['year']) or
           row['MD_DIM'] != 'DD' or row['PRICE_BASE'] not in ('Q', 'V')
           for row in rows):
        raise ValueError(f'{path}: row outside requested country/year microdata')
    return compressed, rows


def _insert_file(conn, name, item, bulk_dir):
    country, year = item['country'], int(item['year'])
    if (country not in COUNTRIES or
            name != f'crs_{country}_{year}_micro.csv.gz'):
        raise ValueError(f'{name}: invalid country-year name')
    compressed, rows = _rows(bulk_dir / name, item)
    sha = hashlib.sha256(compressed).hexdigest()
    recorded_at = item['retrieved_at'][:10]
    document_id = f'oecd-crs-all-{country.lower()}-{year}-{recorded_at}'
    conn.execute(
        'INSERT INTO documents (document_id,country,document_type,language,title,url,active,notes) '
        'VALUES (?,?,?,?,?,?,?,?)',
        (document_id, country, 'data_portal', 'en',
         f'OECD CRS all-sector microdata, {country}, {year}', item['url'], 'true',
         'DVC-only bulk source; lines materialized in SQLite, not ledger CSV'))
    conn.execute(
        'INSERT INTO document_publishers (document_id,party_id,role,name_row_id) '
        'VALUES (?,?,?,?)', (document_id, 'oecd', 'author', 'oecd.name.1'))
    conn.execute(
        'INSERT INTO snapshots (sha256,storage_path,size_bytes,content_type) '
        'VALUES (?,?,?,?)',
        (sha, f'crs-bulk/{name}', len(compressed), 'application/gzip'))
    conn.execute(
        'INSERT INTO retrievals (retrieval_id,document_id,retrieved_at,status,'
        'http_status,content_type,etag,last_modified,final_url,sha256,collection_method) '
        'VALUES (?,?,?,?,?,?,?,?,?,?,?)',
        (f'{document_id}:1', document_id, item['retrieved_at'], 'collected', 200,
         'application/gzip', item.get('etag'), item.get('last_modified'),
         item['url'], sha, 'script'))
    pending = []
    locators = set()
    for ordinal, row in enumerate(rows, 1):
        locator = '.'.join(row[column] for column in DIMENSIONS)
        locator += f"/{row['TIME_PERIOD']}"
        if locator in locators:
            raise ValueError(f'{name}: duplicate SDMX locator {locator}')
        locators.add(locator)
        pending.append((
            f'{document_id}-row-{ordinal}', country, sha, locator, ordinal,
            row['PROJECT_TITLE'] or row['SHORT_DESCRIPTION'] or None,
            'named_item' if row['PROJECT_TITLE'] else 'unnamed_item',
            row['SECTOR'], recorded_at,
            'Unadjudicated all-sector CRS source row; no comparator observation'))
        if len(pending) == 1000:
            conn.executemany(
                'INSERT INTO lines (line_id,country,sha256,locator,ordinal,label,'
                'classification,own_sector,recorded_at,notes) VALUES (?,?,?,?,?,?,?,?,?,?)',
                pending)
            pending.clear()
    if pending:
        conn.executemany(
            'INSERT INTO lines (line_id,country,sha256,locator,ordinal,label,'
            'classification,own_sector,recorded_at,notes) VALUES (?,?,?,?,?,?,?,?,?,?)',
            pending)
    return len(rows)


def materialize(base, output, bulk_dir=BULK_DIR,
                review_manifest=REVIEW_MANIFEST, require_full=True):
    """Copy a validated base ledger and add all bulk lines atomically to SQLite."""
    base, output = Path(base), Path(output)
    bulk_dir, review_manifest = Path(bulk_dir), Path(review_manifest)
    if base.resolve() == output.resolve():
        raise ValueError('bulk output must differ from the base SQLite')
    if not base.is_file():
        raise FileNotFoundError(f'base ledger SQLite is absent: {base}')
    manifest = _manifest(bulk_dir, review_manifest, require_full)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_name(output.name + '.pending')
    staging.unlink(missing_ok=True)
    try:
        with sqlite3.connect(base) as source, sqlite3.connect(staging) as conn:
            source.backup(conn)
            conn.execute('PRAGMA foreign_keys=ON')
            if conn.execute("SELECT 1 FROM parties WHERE party_id='oecd'").fetchone() is None:
                raise ValueError('base ledger lacks the OECD publisher party')
            count = 0
            for name, item in sorted(manifest.items()):
                count += _insert_file(conn, name, item, bulk_dir)
            violations = conn.execute('PRAGMA foreign_key_check').fetchall()
            if violations:
                raise ValueError(f'bulk SQLite has {len(violations)} foreign-key violations')
            conn.commit()
        os.replace(staging, output)
        return count
    except BaseException:
        staging.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bulk-dir', type=Path, default=BULK_DIR)
    parser.add_argument('--review-manifest', type=Path, default=REVIEW_MANIFEST)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    log.info('%d DVC CRS rows materialized in %s',
             materialize(args.base, args.output, args.bulk_dir, args.review_manifest),
             args.output)


if __name__ == '__main__':
    main()
