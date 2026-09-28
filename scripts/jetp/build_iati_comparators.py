"""Ingest frozen four-country IATI energy activities as comparator lines."""

import argparse
import csv
import gzip
import hashlib
import io
import json
import logging
from collections import defaultdict
from datetime import date
from pathlib import Path

from jetp._ledger_headers import (
    LEDGER_DIR,
    chunk_dir,
    file_ceiling,
    load_schema,
    write_table,
)
from jetp.build_comparators import _add, _fields, _rows

COUNTRIES = {'ID': 'IDN', 'SN': 'SEN', 'VN': 'VNM', 'ZA': 'ZAF'}
PUBLISHER = 'international-aid-transparency-initiative'
STATUS = {'1': 'pipeline', '2': 'implementation', '3': 'finalisation',
          '4': 'closed', '5': 'cancelled', '6': 'suspended'}
FLOWS = {'2': 'commitment',
         '3': 'disbursement', '4': 'expenditure',
         '12': 'pledge', 'C': 'commitment', 'D': 'disbursement',
         '7': 'disbursement'}
DECIDED_BY = 'author, ticket 0886 (2026-09-28)'
FIELD_COLUMNS = ('id', 'title', 'status', 'reporting_org', 'sectors',
                 'other_identifiers', 'source_transaction_count',
                 'unallocated_country_count', 'unallocated_sector_count')


def _render(header, rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, header, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _append_lines(ledger_dir, schema, lines, existing, recorded_at):
    """Append only new line shards; leave existing World Bank shards intact."""
    directory = chunk_dir(ledger_dir, 'lines')
    header = schema.header('lines')
    ceiling = file_ceiling()
    for country in COUNTRIES.values():
        members = [row for row in lines if row['country'] == country and
                   row['line_id'] not in existing]
        if not members:
            continue
        names = sorted(directory.glob(f'{country}-{recorded_at[:4]}*.csv'))
        parts = [int(path.stem.rsplit('-', 1)[-1])
                 if len(path.stem.rsplit('-', 1)[-1]) == 2 and
                 path.stem.rsplit('-', 1)[-1].isdigit() else 1 for path in names]
        part = max(parts, default=0) + 1
        batch = []
        for row in members:
            if batch and len(_render(header, [*batch, row]).encode()) > ceiling:
                suffix = f'-{part:02d}' if part > 1 else ''
                _fields(directory / f'{country}-{recorded_at[:4]}{suffix}.csv',
                        header[1:], batch)
                part += 1
                batch = []
            batch.append(row)
        if batch:
            suffix = f'-{part:02d}' if part > 1 else ''
            _fields(directory / f'{country}-{recorded_at[:4]}{suffix}.csv',
                    header[1:], batch)


def _add_identifiers(activity, line_id, tables, first_line, recorded_at):
    identifier = activity['id']
    if identifier in first_line:
        if first_line[identifier] != line_id:
            _add(tables['relations'], dict(
                relation_id=f'same-as-{line_id}', from_kind='line', from_id=line_id,
                relation='same_as', to_kind='line', to_id=first_line[identifier],
                status='accepted', method='exact_iati_identifier', method_version='1',
                confidence=1, decided_at=recorded_at,
                decided_by='scripts/jetp/build_iati_comparators.py', line_id=line_id),
                ('relation_id',))
    else:
        first_line[identifier] = line_id
        _add(tables['external_ids'], dict(scheme='iati-activity-id',
            external_id=identifier, kind='line', id=line_id,
            line_id=line_id, recorded_at=recorded_at), ('scheme', 'external_id'))
    for other in activity['other_identifiers']:
        ref = other.get('ref') or ''
        owner = other.get('owner') or ''
        if 'GEM' in ref.upper() or 'GEM' in owner.upper():
            _add(tables['external_ids'], dict(scheme='gem-id',
                external_id=ref, kind='line', id=line_id,
                line_id=line_id, recorded_at=recorded_at), ('scheme', 'external_id'))


def _add_transactions(activity, line_id, tables, observed, timed, recorded_at, counts):
    for index, transaction in enumerate(activity['transactions'], 1):
        code = transaction['code']
        if code not in FLOWS:
            counts['unmapped_transactions'] += 1
            continue
        observation_id = f'observation-{line_id}-tx-{index}'
        observation = dict(
            observation_id=observation_id, subject_kind='line',
            subject_id=line_id, axis='money', measure='flow',
            flow_type=FLOWS[code], basis='unknown', value=transaction['value'],
            unit=transaction['currency'], currency=transaction['currency'],
            own_status=code, line_id=line_id, method='iati_transaction',
            method_version='1', recorded_at=recorded_at, status='accepted',
            notes=f'IATI TransactionType:{code}; source transaction {index}')
        if observation_id not in observed:
            tables['observations'].append(observation)
            observed[observation_id] = observation
        elif any(str(observed[observation_id].get(key) or '') != str(value or '')
                 for key, value in observation.items()):
            raise ValueError(f'conflicting observation {observation_id}')
        counts['flows'] += 1
        if transaction['date']:
            timing = dict(
                timing_id=f'timing-{observation_id}', observation_id=observation_id,
                date_role='event', date=transaction['date'], date_precision='day',
                line_id=line_id, recorded_at=recorded_at)
            if timing['timing_id'] not in timed:
                tables['timings'].append(timing)
                timed[timing['timing_id']] = timing


def ingest(paths, ledger_dir=LEDGER_DIR, *, recorded_at):
    date.fromisoformat(recorded_at)
    ledger_dir = Path(ledger_dir)
    schema = load_schema()
    tables = {name: _rows(ledger_dir, name, schema) for name in (
        'documents', 'document_publishers', 'snapshots', 'retrievals',
        'lines', 'line_field_specs', 'external_ids', 'relations',
        'status_crosswalk', 'observations', 'timings')}
    existing = {row['line_id'] for row in tables['lines']}
    first_line = {row['external_id']: row['id'] for row in tables['external_ids']
                  if row['scheme'] == 'iati-activity-id' and row['kind'] == 'line'}
    existing_observations = {row['observation_id']: row for row in tables['observations']}
    existing_timings = {row['timing_id']: row for row in tables['timings']}
    for own, shared in STATUS.items():
        _add(tables['status_crosswalk'], dict(
            crosswalk_row_id=f'iati.delivery.{own}.1', publisher_id=PUBLISHER,
            own_status=own, axis='delivery', shared_status=shared,
            recorded_at=recorded_at, decided_by=DECIDED_BY, status='accepted',
            notes=f'IATI ActivityStatus:{own}'), ('crosswalk_row_id',))
    counts = defaultdict(int)
    for path in sorted(paths, key=lambda item: Path(item).name):
        path = Path(path)
        if path.resolve().parent != (ledger_dir / 'iati').resolve():
            raise ValueError(f'{path}: snapshot must live in {ledger_dir}/iati')
        raw = path.read_bytes()
        snapshot = json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)
        iso2 = snapshot['country_code']
        if iso2 not in COUNTRIES or len(snapshot['records']) != snapshot['count']:
            raise ValueError(f'{path}: invalid country or activity count')
        source_total = snapshot['source_total']
        if (snapshot['count'] > source_total or
                sum(item['returned'] for item in snapshot['queries']) != source_total or
                any(item['total'] != source_total for item in snapshot['queries'])):
            raise ValueError(f'{path}: incomplete API pagination')
        if len({row['id'] for row in snapshot['records']}) != snapshot['count']:
            raise ValueError(f'{path}: duplicate IATI identifiers')
        country = COUNTRIES[iso2]
        retrieved = snapshot['retrieved_at'][:10]
        if retrieved > recorded_at:
            raise ValueError(f'{path}: retrieval postdates ledger date')
        document_id = f'iati-energy-{iso2.lower()}-{retrieved}'
        sha = hashlib.sha256(raw).hexdigest()
        _add(tables['documents'], dict(document_id=document_id, country=country,
            document_type='data_portal', language='en',
            title=f'IATI Datastore Classic energy activity slice, {country}, {retrieved}',
            url=snapshot['source'], active='true',
            notes='Frozen country-energy API projection; query URLs and response hashes are in the snapshot; reporting organisation retained per activity'),
            ('document_id',))
        _add(tables['document_publishers'], dict(document_id=document_id,
            party_id=PUBLISHER, role='author',
            name_row_id=f'{PUBLISHER}.name.1'), ('document_id', 'party_id'))
        _add(tables['snapshots'], dict(sha256=sha,
            storage_path=f'../iati/{path.name}', size_bytes=len(raw),
            content_type='application/gzip' if path.suffix == '.gz' else 'application/json'),
            ('sha256',))
        _add(tables['retrievals'], dict(retrieval_id=f'{document_id}:1',
            document_id=document_id, retrieved_at=retrieved, status='collected',
            content_type='application/gzip' if path.suffix == '.gz' else 'application/json',
            sha256=sha, collection_method='script'), ('retrieval_id',))
        _add(tables['line_field_specs'], dict(document_id=document_id,
            columns=json.dumps(FIELD_COLUMNS)), ('document_id',))
        field_rows = []
        for ordinal, activity in enumerate(snapshot['records'], 1):
            identifier = activity['id']
            activity['status'] = str(activity['status']).strip()
            if not identifier or activity['status'] not in STATUS:
                raise ValueError(f'{path}: missing identifier or unknown IATI status')
            line_id = f'{document_id}-{hashlib.sha256(identifier.encode()).hexdigest()[:20]}'
            _add(tables['lines'], dict(line_id=line_id, country=country,
                sha256=sha, locator=identifier, ordinal=ordinal,
                label=activity['title'] or identifier,
                classification='named_item', own_status=activity['status'],
                own_status_axis='delivery',
                own_sector=json.dumps(activity['sectors'], ensure_ascii=False),
                recorded_at=recorded_at,
                notes='External IATI comparator activity; not a partnership project'),
                ('line_id',))
            field_rows.append({'line_id': line_id, **{
                key: json.dumps(activity[key], ensure_ascii=False, separators=(',', ':'))
                if isinstance(activity[key], (list, dict)) else activity[key]
                for key in FIELD_COLUMNS}})
            _add_identifiers(activity, line_id, tables, first_line, recorded_at)
            _add_transactions(activity, line_id, tables, existing_observations,
                              existing_timings, recorded_at, counts)
            counts['lines'] += 1
        _fields(ledger_dir / 'line-fields' / f'{document_id}.csv',
                FIELD_COLUMNS, field_rows)
    _append_lines(ledger_dir, schema, tables['lines'], existing, recorded_at)
    country_by_line = {row['line_id']: row['country'] for row in tables['lines']}
    country_by_doc = {row['document_id']: row.get('country')
                      for row in tables['documents']}

    def country_for_relation(row):
        if row['line_id']:
            return country_by_line[row['line_id']]
        if row['from_kind'] == 'document':
            return country_by_doc[row['from_id']] or 'GLB'
        if row['from_kind'] == 'party':
            return 'GLB'
        raise ValueError(f"relation {row['relation_id']} needs a shard bucket")

    for name, rows in tables.items():
        if name == 'lines':
            continue
        kwargs = ({'country_for_row': country_for_relation} if name == 'relations'
                  else {'country_by_line_id': country_by_line})
        write_table(ledger_dir, name, rows, schema=schema, **kwargs)
    return dict(counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, nargs='+', required=True)
    parser.add_argument('--recorded-at', required=True)
    parser.add_argument('--output', '--ledger-dir', dest='ledger_dir',
                        type=Path, default=LEDGER_DIR)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logging.info('IATI comparator ingestion: %s',
                 ingest(args.snapshot, args.ledger_dir, recorded_at=args.recorded_at))


if __name__ == '__main__':
    main()
