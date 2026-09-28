"""Ingest frozen World Bank API editions as comparator lines, never JETP projects.

One JSON projection is one dataset edition/document and one snapshot.  A P-number
locates a record in that edition.  Later editions retain their own lines and
receive a reviewed ``same_as`` relation to the first line for that P-number.
The closed energy pool is a perimeter of lines, using the observatory's frozen
selection rule.  No network request or source-field expansion occurs here.
"""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

import yaml

from jetp._ledger_headers import LEDGER_DIR, load_schema, read_table, write_table
from jetp._observatory_data import historical_record

ROOT = Path(__file__).resolve().parents[2]
RECORDED_AT = '2026-09-28'
DECIDED_BY = 'scripts/jetp/build_comparators.py'
COUNTRIES = {'ID': 'IDN', 'SN': 'SEN', 'VN': 'VNM', 'ZA': 'ZAF'}
POOL_ID = 'world-bank-pre-jetp-closed-energy'
STATUS = {'Active': 'implementation', 'Closed': 'closed',
          'Dropped': 'cancelled', 'Pipeline': 'pipeline'}


def _rows(directory, table, schema):
    records, errors = read_table(directory, table, schema)
    if errors:
        raise ValueError('; '.join(errors))
    return [dict(zip(schema.header(table), row)) for row in records]


def _add(rows, row, key):
    found = next((old for old in rows if tuple(old.get(k) for k in key) ==
                  tuple(row.get(k) for k in key)), None)
    if found is None:
        rows.append(row)
    elif any(str(found.get(k) or '') != str(v or '') for k, v in row.items()):
        raise ValueError(f'conflicting {key}: {tuple(row.get(k) for k in key)}')


def _fields(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, ['line_id', *columns], lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def _edition(path):
    path = Path(path)
    raw = path.read_bytes()
    data = json.loads(raw)
    iso2 = data['country_code']
    columns = data['projection_fields']
    if iso2 not in COUNTRIES or 'id' not in columns:
        raise ValueError(f'{path}: unknown country or missing P-number')
    if len(data['records']) != data['source_total']:
        raise ValueError(f'{path}: incomplete source total')
    if len({row['id'] for row in data['records']}) != len(data['records']):
        raise ValueError(f'{path}: duplicate P-number in edition')
    if any(set(row) != set(columns) for row in data['records']):
        raise ValueError(f'{path}: record fields differ from projection_fields')
    return data['retrieved_on'], iso2, path, raw, data


def _write_new_lines(ledger_dir, schema, editions, rows, existing_line_ids):
    """Leave earlier shards intact; append each newly ingested edition once."""
    for date, iso2, _, _, _ in sorted(editions):
        doc = f'world-bank-projects-{iso2.lower()}-{date}'
        subset = [row for row in rows if row['line_id'].startswith(doc + '-')]
        if not subset or all(row['line_id'] in existing_line_ids for row in subset):
            continue
        existing = sorted((ledger_dir / 'lines.d').glob(
            f'{COUNTRIES[iso2]}-{RECORDED_AT[:4]}*.csv'))
        parts = [int(p.stem.rsplit('-', 1)[-1])
                 if p.stem.rsplit('-', 1)[-1].isdigit()
                 and len(p.stem.rsplit('-', 1)[-1]) == 2 else 1 for p in existing]
        part = max(parts, default=1) + 1
        target = ledger_dir / 'lines.d' / f'{COUNTRIES[iso2]}-{RECORDED_AT[:4]}-{part:02d}.csv'
        if target.exists():
            raise ValueError(f'line shard exists: {target}')
        _fields(target, schema.header('lines')[1:], subset)


def ingest(paths, ledger_dir=LEDGER_DIR, signed_dates=None):
    """Add one or more editions. Return the number of lines and pool members."""
    ledger_dir = Path(ledger_dir)
    schema = load_schema()
    tables = {name: _rows(ledger_dir, name, schema) for name in (
        'documents', 'document_publishers', 'snapshots', 'retrievals', 'lines',
        'line_field_specs', 'external_ids', 'relations', 'status_crosswalk')}
    existing_line_ids = {row['line_id'] for row in tables['lines']}
    perimeters = _rows(ledger_dir, 'perimeters', schema)
    if signed_dates is None:
        config = yaml.safe_load((ROOT / 'config/jetp_observatory.yaml').read_text())
        signed_dates = {code: item['signed_on'] for code, item in config['countries'].items()}
    _add(perimeters, dict(perimeter_row_id=f'{POOL_ID}.1', perimeter_id=POOL_ID,
                          name='World Bank closed energy operations before JETP',
                          scope='Descriptive historical reference pool',
                          definition='World Bank status Closed, approval before the country JETP announcement, and a sector label containing energy, power or electric; membership is a line of the frozen API edition.',
                          recorded_at=RECORDED_AT, decided_by=DECIDED_BY,
                          status='accepted'), ('perimeter_row_id',))
    for own, shared in STATUS.items():
        _add(tables['status_crosswalk'], dict(
            crosswalk_row_id=f'world-bank.delivery.{own.lower()}.1',
            publisher_id='world-bank', own_status=own, axis='delivery',
            shared_status=shared, recorded_at=RECORDED_AT, decided_by=DECIDED_BY,
            status='accepted', notes='World Bank administrative project status; not physical completion'),
            ('crosswalk_row_id',))
    editions = [_edition(path) for path in paths]
    first_line = {row['external_id']: row['id'] for row in tables['external_ids']
                  if row['scheme'] == 'world-bank-p-number' and row['kind'] == 'line'}
    member_count = 0
    for date, iso2, path, raw, data in sorted(editions):
        country = COUNTRIES[iso2]
        columns = data['projection_fields']
        document_id = f'world-bank-projects-{iso2.lower()}-{date}'
        prefix = f'world-bank-projects-{iso2.lower()}-'
        earlier = [old['document_id'] for old in tables['documents']
                   if old['document_id'].startswith(prefix)
                   and old['document_id'][len(prefix):] < date]
        sha = hashlib.sha256(raw).hexdigest()
        url = f'https://search.worldbank.org/api/v2/projects?format=json&countrycode_exact={iso2}'
        _add(tables['documents'], dict(document_id=document_id, country=country,
            document_type='data_portal', language='en',
            title=f'World Bank Projects & Operations, {country}, API edition {date}',
            url=url, edition_of=max(earlier, default=None), active='true',
            notes='Frozen nine-field API projection assembled from paginated responses; page URLs and response hashes are in the JSON snapshot'), ('document_id',))
        _add(tables['document_publishers'], dict(document_id=document_id,
            party_id='world-bank', role='author', name_row_id='world-bank.name.1'),
            ('document_id', 'party_id'))
        _add(tables['snapshots'], dict(sha256=sha,
            storage_path=os.path.relpath(path.resolve(), (ledger_dir / 'documents').resolve()),
            size_bytes=len(raw), content_type='application/json'), ('sha256',))
        _add(tables['retrievals'], dict(retrieval_id=f'{document_id}:1',
            document_id=document_id, retrieved_at=date,
            status='collected', content_type='application/json',
            sha256=sha, collection_method='local-record'), ('retrieval_id',))
        _add(tables['line_field_specs'], dict(document_id=document_id,
            columns=json.dumps(columns, ensure_ascii=False)), ('document_id',))
        field_rows = []
        for ordinal, row in enumerate(data['records'], 1):
            p_number = row['id']
            line_id = f'{document_id}-{p_number}'
            _add(tables['lines'], dict(line_id=line_id, country=country, sha256=sha,
                locator=f'projects/{p_number}', ordinal=ordinal,
                label=row.get('project_name'), classification='named_item',
                own_status=row.get('status'), own_status_axis='delivery',
                own_sector=json.dumps(row.get('sector_namecode'), ensure_ascii=False),
                recorded_at=RECORDED_AT,
                notes='External comparator record; not a partnership project'), ('line_id',))
            field_rows.append({'line_id': line_id, **{
                key: json.dumps(row[key], ensure_ascii=False, separators=(',', ':'))
                if isinstance(row[key], (dict, list)) else (row[key] or '') for key in columns}})
            if p_number in first_line:
                if first_line[p_number] != line_id:
                    _add(tables['relations'], dict(
                        relation_id=f'same-as-{line_id}', from_kind='line', from_id=line_id,
                        relation='same_as', to_kind='line', to_id=first_line[p_number],
                        status='accepted', method='exact_world_bank_p_number', method_version='1',
                        confidence=1, decided_at=RECORDED_AT, decided_by=DECIDED_BY,
                        line_id=line_id), ('relation_id',))
            else:
                first_line[p_number] = line_id
                _add(tables['external_ids'], dict(scheme='world-bank-p-number',
                    external_id=p_number, kind='line', id=line_id, line_id=line_id,
                    recorded_at=RECORDED_AT), ('scheme', 'external_id'))
            if historical_record(row, country, signed_dates[country]):
                member_count += 1
                _add(tables['relations'], dict(relation_id=f'member-of-{POOL_ID}-{line_id}',
                    from_kind='line', from_id=line_id, relation='member_of',
                    to_kind='perimeter', to_id=POOL_ID, status='accepted',
                    method='closed_pre_jetp_energy_v1', method_version='1',
                    confidence=1, decided_at=RECORDED_AT, decided_by=DECIDED_BY,
                    line_id=line_id), ('relation_id',))
        _fields(ledger_dir / 'line-fields' / f'{document_id}.csv', columns, field_rows)
    for name, rows in tables.items():
        if name == 'lines':
            _write_new_lines(ledger_dir, schema, editions, rows, existing_line_ids)
        else:
            write_table(ledger_dir, name, rows, schema=schema)
    write_table(ledger_dir, 'perimeters', perimeters, schema=schema)
    return sum(len(data['records']) for *_, data in editions), member_count


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--snapshot', type=Path, nargs='+', required=True)
    parser.add_argument('--output', '--ledger-dir', dest='ledger_dir', type=Path,
                        default=LEDGER_DIR, help='Output ledger directory')
    args = parser.parse_args()
    print(ingest(args.snapshot, args.ledger_dir))


if __name__ == '__main__':
    main()
