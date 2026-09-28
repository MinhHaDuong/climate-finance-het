"""Freeze the constant-price CRS energy slice from the pinned DVC archive.

The archived OECD response remains under DVC.  These reviewed CSV projections
retain its 51 source fields and only PRICE_BASE=Q microdata.  No API is called.
"""

import argparse
import csv
import gzip
import hashlib
import io
import logging
from pathlib import Path

from jetp._ledger_headers import LEDGER_DIR, file_ceiling
from jetp.catalog_crs import COUNTRIES

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / 'data/jetp/crs'
OUTPUT_DIR = LEDGER_DIR / 'comparison/crs'
YEARS = range(2005, 2025)
MANIFEST_FIELDS = ('country', 'year', 'source_file', 'source_sha256',
                   'source_rows', 'q_rows', 'v_rows', 'projection_file',
                   'projection_sha256', 'projection_bytes')
log = logging.getLogger(__name__)


def project(source_dir=SOURCE_DIR, output_dir=OUTPUT_DIR):
    """Write deterministic Q-only projections and their source hash manifest."""
    source_dir, output_dir = Path(source_dir), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for country in COUNTRIES:
        for year in YEARS:
            name = f'crs_{country}_{year}_micro.csv.gz'
            source = source_dir / name
            source_bytes = source.read_bytes()
            raw = gzip.decompress(source_bytes).decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(raw, newline=''))
            fields = reader.fieldnames
            if not fields or len(fields) != 51:
                raise ValueError(f'{source}: expected 51 source fields')
            rows = list(reader)
            if any(row['RECIPIENT'] != country or row['TIME_PERIOD'] != str(year)
                   or row['MD_DIM'] != 'DD' or row['PRICE_BASE'] not in ('Q', 'V')
                   for row in rows):
                raise ValueError(f'{source}: source rows differ from country/year/micro slice')
            q_rows = [row for row in rows if row['PRICE_BASE'] == 'Q']
            v_rows = [row for row in rows if row['PRICE_BASE'] == 'V']
            if len(q_rows) != len(v_rows):
                raise ValueError(f'{source}: Q and V row counts differ')
            output = io.StringIO()
            writer = csv.DictWriter(output, fields, lineterminator='\n')
            writer.writeheader()
            writer.writerows(q_rows)
            data = output.getvalue().encode('utf-8')
            if len(data) > file_ceiling():
                raise ValueError(f'{source}: Q projection exceeds file ceiling')
            target = output_dir / f'crs_{country}_{year}_Q.csv'
            target.write_bytes(data)
            manifest.append(dict(country=country, year=year, source_file=name,
                source_sha256=hashlib.sha256(source_bytes).hexdigest(),
                source_rows=len(rows), q_rows=len(q_rows), v_rows=len(v_rows),
                projection_file=target.name,
                projection_sha256=hashlib.sha256(data).hexdigest(),
                projection_bytes=len(data)))
    output = io.StringIO()
    writer = csv.DictWriter(output, MANIFEST_FIELDS, lineterminator='\n')
    writer.writeheader()
    writer.writerows(manifest)
    (output_dir / 'manifest.csv').write_text(output.getvalue(), encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--source-dir', type=Path, default=SOURCE_DIR)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    manifest = project(args.source_dir, args.output_dir)
    log.info('%d CRS Q rows in %d files',
             sum(int(row['q_rows']) for row in manifest), len(manifest))


if __name__ == '__main__':
    main()
