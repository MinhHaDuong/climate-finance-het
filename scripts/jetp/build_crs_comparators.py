"""Ingest the pinned four-country OECD CRS energy projection into the ledger.

The reviewed Q-only projections are local records of an archived DVC pull.
Each SDMX microdata row becomes a source line and a cited flow; Rio scores
remain categorical observations and are never multiplied into money here.
"""

import argparse
import csv
import hashlib
import io
import json
import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from jetp._ledger_headers import (
    LEDGER_DIR,
    _shard_texts,
    file_ceiling,
    load_schema,
    read_table,
    write_table,
)
from jetp.build_comparators import flow_type
from jetp.catalog_crs import BASE, ENERGY_SECTORS, build_key

SOURCE_DIR = LEDGER_DIR / 'comparison/crs'
MARKERS = {'BIODIVERSITY': 'biodiversity',
           'CLIMATE_MITIGATION': 'mitigation',
           'CLIMATE_ADAPTATION': 'adaptation',
           'DESERTIFICATION': 'desertification'}
COUNTRIES = {'IDN', 'SEN', 'VNM', 'ZAF'}
METHOD = 'oecd_crs_energy_microdata'
DECIDED_BY = 'scripts/jetp/build_crs_comparators.py'
ONTOLOGY_DECIDER = 'author, ticket 0885 (2026-09-28)'
DEFLATOR_SERIES = 'oecd-crs-Q-2024-USD-already-constant'
log = logging.getLogger(__name__)


def _cell(value):
    return '' if value is None else str(value)


class Tables:
    """Indexed append-or-verify writes; a rerun cannot change an older row."""

    def __init__(self, ledger_dir, schema, names):
        self.schema = schema
        self.rows = {}
        self.index = {}
        for name in names:
            records, errors = read_table(ledger_dir, name, schema)
            if errors:
                raise ValueError('; '.join(errors))
            header = schema.header(name)
            self.rows[name] = [dict(zip(header, row)) for row in records]
            self.index[name] = {tuple(_cell(row[column]) for column in schema.keys[name]): row
                                for row in self.rows[name]}

    def add(self, name, row):
        key = tuple(_cell(row[column]) for column in self.schema.keys[name])
        found = self.index[name].get(key)
        if found is None:
            self.rows[name].append(row)
            self.index[name][key] = row
        elif any(_cell(found.get(column)) != _cell(row.get(column))
                 for column in self.schema.header(name)):
            raise ValueError(f'{name}: conflicting row {key}')


def _manifest(source_dir, require_full):
    with (source_dir / 'manifest.csv').open(newline='', encoding='utf-8') as handle:
        manifest = list(csv.DictReader(handle))
    keys = {(row['country'], row['year']) for row in manifest}
    if len(keys) != len(manifest):
        raise ValueError('duplicate country-year CRS energy projection')
    if require_full and (len(manifest) != 80 or {row['country'] for row in manifest} != COUNTRIES):
        raise ValueError('expected 80 four-country/year CRS energy projections')
    if any(row['country'] not in COUNTRIES for row in manifest):
        raise ValueError('CRS projection country outside four-country contract')
    return manifest


def _source_rows(source_dir, item):
    path = source_dir / item['projection_file']
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != item['projection_sha256'] or len(raw) != int(item['projection_bytes']):
        raise ValueError(f'{path}: projection differs from reviewed manifest')
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8'), newline=''))
    fields = reader.fieldnames
    if not fields or len(fields) != 51:
        raise ValueError(f'{path}: expected 51 CRS source fields')
    rows = list(reader)
    if len(rows) != int(item['q_rows']):
        raise ValueError(f'{path}: row count differs from manifest')
    if any(row['RECIPIENT'] != item['country'] or row['TIME_PERIOD'] != item['year']
           or row['PRICE_BASE'] != 'Q' or row['BASE_PER'] != '2024'
           or row['MD_DIM'] != 'DD' or row['UNIT_MEASURE'] != 'USD'
           or row['FLOW_TYPE'] not in ('C', 'D') for row in rows):
        raise ValueError(f'{path}: row outside Q/2024/USD country-year slice')
    if len({row['MD_ID'] for row in rows}) != len(rows):
        raise ValueError(f'{path}: duplicate SDMX MD_ID')
    return raw, fields, rows


def _document(tables, item, raw, fields, recorded_at):
    country, year = item['country'], item['year']
    document_id = f'oecd-crs-energy-{country.lower()}-{year}-q-{recorded_at}'
    sha = hashlib.sha256(raw).hexdigest()
    key = build_key(RECIPIENT=country, SECTOR='+'.join(ENERGY_SECTORS),
                    PRICE_BASE='Q', MD_DIM='DD')
    url = (f'{BASE}{key}?startPeriod={year}&endPeriod={year}'
           '&dimensionAtObservation=AllDimensions&format=csvfile')
    tables.add('documents', dict(document_id=document_id, country=country,
        document_type='data_portal', language='en',
        title=f'OECD CRS energy microdata, {country}, {year}, 2024 constant USD',
        url=url, active='true', notes='Q-only 51-field projection of pinned DVC OECD SDMX pull; '
        f"source archive SHA-256 {item['source_sha256']}"))
    tables.add('document_publishers', dict(document_id=document_id,
        party_id='oecd', role='author', name_row_id='oecd.name.1'))
    tables.add('snapshots', dict(sha256=sha,
        storage_path=f"../comparison/crs/{item['projection_file']}",
        size_bytes=len(raw), content_type='text/csv'))
    tables.add('retrievals', dict(retrieval_id=f'{document_id}:1',
        document_id=document_id, retrieved_at=recorded_at, status='collected',
        content_type='text/csv', sha256=sha, collection_method='local-record'))
    tables.add('line_field_specs', dict(document_id=document_id,
        columns=json.dumps(fields, ensure_ascii=False)))
    return document_id, sha


def _line(tables, row, document_id, sha, ordinal, recorded_at):
    line_id = f"{document_id}-md-{row['MD_ID']}"
    locator = '.'.join(row[column] for column in (
        'DONOR', 'RECIPIENT', 'SECTOR', 'MEASURE', 'CHANNEL', 'MODALITY',
        'FLOW_TYPE', 'PRICE_BASE', 'MD_DIM', 'MD_ID', 'UNIT_MEASURE'))
    locator += f"/{row['TIME_PERIOD']}"
    tables.add('lines', dict(line_id=line_id, country=row['RECIPIENT'],
        sha256=sha, locator=locator, ordinal=ordinal,
        label=row['PROJECT_TITLE'] or row['SHORT_DESCRIPTION'] or None,
        classification='named_item' if row['PROJECT_TITLE'] else 'unnamed_item',
        own_sector=row['SECTOR'], recorded_at=recorded_at,
        notes='External CRS comparator activity-flow record; not a JETP project'))
    tables.add('external_ids', dict(scheme='oecd-crs-crs-id',
        external_id=row['MD_ID'], kind='line', id=line_id, line_id=line_id,
        recorded_at=recorded_at))
    return line_id


def _activity(tables, row, line_id, first_activity, recorded_at):
    donor_project = row['DONOR_PROJECT_ID'].strip()
    if not donor_project:
        return
    key = f"{row['DONOR']}:{donor_project}"
    anchor, anchor_year = first_activity.setdefault(
        key, (line_id, row['TIME_PERIOD']))
    if anchor == line_id:
        tables.add('external_ids', dict(scheme='oecd-crs-donor-project-id',
            external_id=key, kind='line', id=line_id, line_id=line_id,
            recorded_at=recorded_at))
    elif row['TIME_PERIOD'] != anchor_year:
        tables.add('relations', dict(relation_id=f'same-as-{line_id}',
            from_kind='line', from_id=line_id, relation='same_as',
            to_kind='line', to_id=anchor, status='accepted',
            method='exact_oecd_donor_and_project_id', method_version='1',
            confidence=1, decided_at=recorded_at, decided_by=DECIDED_BY,
            line_id=line_id))


def _observations(tables, row, line_id, recorded_at):
    observation_id = f'crs-flow-{line_id}'
    value = Decimal(row['OBS_VALUE']) * (Decimal(10) ** int(row['UNIT_MULT']))
    value_text = str(int(value)) if value == value.to_integral_value() else str(value)
    tables.add('observations', dict(observation_id=observation_id,
        subject_kind='line', subject_id=line_id, axis='money', measure='flow',
        flow_type=flow_type(row['FLOW_TYPE']), basis='unknown', value=value_text,
        unit='USD', currency='USD', line_id=line_id, method=METHOD,
        method_version='1', recorded_at=recorded_at, status='accepted',
        notes='OECD Q value already in 2024 constant USD; UNIT_MULT applied, no FX or deflator rate applied'))
    for role in ('period_start', 'period_end'):
        tables.add('timings', dict(timing_id=f'{observation_id}-{role}',
            observation_id=observation_id, date_role=role,
            date=row['TIME_PERIOD'], date_precision='year',
            lower_bound=f"{row['TIME_PERIOD']}-01-01",
            upper_bound=f"{row['TIME_PERIOD']}-12-31",
            line_id=line_id, recorded_at=recorded_at))
    for column, marker in MARKERS.items():
        score = row[column] or 'not_screened'
        if score not in ('0', '1', '2', 'not_screened'):
            raise ValueError(f'{line_id}: invalid {column} score {score!r}')
        tables.add('observations', dict(
            observation_id=f'crs-marker-{marker}-{line_id}',
            subject_kind='line', subject_id=line_id, measure='marker',
            value=score if score != 'not_screened' else None,
            own_status=score, indicator_code=marker,
            line_id=line_id, method=METHOD, method_version='1',
            recorded_at=recorded_at, status='accepted'))


def _source_fields(ledger_dir, document_id, fields, rows, line_ids):
    path = ledger_dir / 'line-fields' / f'{document_id}.csv'
    output = io.StringIO()
    writer = csv.DictWriter(output, ['line_id', *fields], lineterminator='\n')
    writer.writeheader()
    for line_id, row in zip(line_ids, rows):
        writer.writerow({'line_id': line_id, **row})
    data = output.getvalue().encode('utf-8')
    if len(data) > file_ceiling():
        raise ValueError(f'{path}: source field table exceeds file ceiling')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _append_line_shards(ledger_dir, schema, new_lines, recorded_at):
    header = schema.header('lines')
    by_country = defaultdict(list)
    for row in new_lines:
        by_country[row['country']].append(row)
    for country, rows in sorted(by_country.items()):
        directory = ledger_dir / 'lines.d'
        existing = sorted(directory.glob(f'{country}-{recorded_at[:4]}*.csv'))
        parts = [int(path.stem.rsplit('-', 1)[-1]) if
                 len(path.stem.rsplit('-', 1)[-1]) == 2 and
                 path.stem.rsplit('-', 1)[-1].isdigit() else 1 for path in existing]
        next_part = max(parts, default=0) + 1
        for offset, text in enumerate(_shard_texts(header, rows, file_ceiling())):
            part = next_part + offset
            suffix = '' if part == 1 else f'-{part:02d}'
            target = directory / f'{country}-{recorded_at[:4]}{suffix}.csv'
            if target.exists():
                raise ValueError(f'line shard exists: {target}')
            target.write_text(text, encoding='utf-8')


def _coefficients(tables, source_dir, ledger_dir, recorded_at):
    """Enter only coefficients the OECD survey explicitly reports for EU."""
    path = source_dir / 'rio-coefficients-2020.csv'
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8'), newline=''))
    fields = reader.fieldnames
    rows = list(reader)
    if len(rows) != 3 or {row['marker'] for row in rows} != {
            'adaptation', 'mitigation', 'biodiversity'}:
        raise ValueError(f'{path}: expected three EU survey marker rows')
    document_id = 'oecd-rio-coefficients-survey-2020-projection'
    tables.add('documents', dict(document_id=document_id, document_type='secondary_news',
        language='en', title='OECD 2020 survey of Rio marker coefficients',
        url='https://one.oecd.org/document/DCD/DAC/STAT(2020)41/en/pdf',
        published_date='2020', active='true',
        notes='Projection of Table 1, EU row, printed page 4; coefficients concern 2017-18 reporting'))
    tables.add('document_publishers', dict(document_id=document_id,
        party_id='oecd', role='author', name_row_id='oecd.name.1'))
    tables.add('snapshots', dict(sha256=sha,
        storage_path='../comparison/crs/rio-coefficients-2020.csv',
        size_bytes=len(raw), content_type='text/csv'))
    tables.add('retrievals', dict(retrieval_id=f'{document_id}:1',
        document_id=document_id, retrieved_at=recorded_at, status='collected',
        content_type='text/csv', sha256=sha, collection_method='local-record'))
    tables.add('line_field_specs', dict(document_id=document_id,
        columns=json.dumps(fields, ensure_ascii=False)))
    line_ids = []
    for ordinal, row in enumerate(rows, 1):
        if (row['provider'], row['period_start'], row['period_end'],
                row['measurement_basis']) != ('EU', '2017', '2018', 'commitment'):
            raise ValueError(f'{path}: survey scope differs from recorded EU row')
        line_id = f"{document_id}-eu-{row['marker']}"
        line_ids.append(line_id)
        tables.add('lines', dict(line_id=line_id, country='GLB', sha256=sha,
            locator=f"table1/eu/{row['marker']}", ordinal=ordinal,
            label=f"EU {row['marker']} Rio coefficient, 2017-18",
            classification='heading', recorded_at=recorded_at,
            notes='Global source line: EU reporting method; GLB is no recipient country'))
        for year in (2017, 2018):
            for score, column in (('1', 'significant_pct'), ('2', 'principal_pct')):
                value = Decimal(row[column]) / 100
                tables.add('marker_coefficients', dict(
                    coefficient_row_id=f"oecd-survey-eu-{row['marker']}-{score}-{year}",
                    donor_party_id='european-union', marker=row['marker'],
                    score=score, year=year, coefficient=str(value),
                    line_id=line_id, recorded_at=recorded_at,
                    decided_by=ONTOLOGY_DECIDER, status='accepted'))
    _source_fields(ledger_dir, document_id, fields, rows, line_ids)


def ingest(source_dir=SOURCE_DIR, ledger_dir=LEDGER_DIR, *, recorded_at,
           require_full=True):
    """Ingest the energy projection, preserving existing lines and decisions."""
    date.fromisoformat(recorded_at)
    source_dir, ledger_dir = Path(source_dir), Path(ledger_dir)
    schema = load_schema()
    names = ('parties', 'party_names', 'documents', 'document_publishers',
             'snapshots', 'retrievals', 'line_field_specs', 'lines', 'external_ids',
             'relations', 'observations', 'timings', 'deflators',
             'sector_crosswalk', 'marker_coefficients')
    tables = Tables(ledger_dir, schema, names)
    old_line_ids = set(tables.index['lines'])
    tables.add('parties', dict(party_id='oecd', authority_category='secondary_source',
        notes='OECD publishes Creditor Reporting System microdata supplied by reporters'))
    lines_by_id = {row['line_id']: row for row in tables.rows['lines']}
    first_activity = {
        row['external_id']: (row['id'], lines_by_id[row['id']]['locator'].rsplit('/', 1)[-1])
        for row in tables.rows['external_ids']
        if row['scheme'] == 'oecd-crs-donor-project-id'
    }
    first_doc = None
    count = 0
    first_year_line = {}
    sectors = set()
    for item in _manifest(source_dir, require_full):
        raw, fields, rows = _source_rows(source_dir, item)
        document_id, sha = _document(tables, item, raw, fields, recorded_at)
        first_doc = first_doc or document_id
        line_ids = []
        for ordinal, row in enumerate(rows, 1):
            line_id = _line(tables, row, document_id, sha, ordinal, recorded_at)
            line_ids.append(line_id)
            _activity(tables, row, line_id, first_activity, recorded_at)
            _observations(tables, row, line_id, recorded_at)
            first_year_line.setdefault(int(row['TIME_PERIOD']), line_id)
            sectors.add(row['SECTOR'])
            count += 1
        _source_fields(ledger_dir, document_id, fields, rows, line_ids)
    tables.add('party_names', dict(name_row_id='oecd.name.1', party_id='oecd',
        name='Organisation for Economic Co-operation and Development',
        form_type='preferred', document_id=first_doc, recorded_at=recorded_at,
        decided_by=ONTOLOGY_DECIDER, status='accepted'))
    for sector in sorted(sectors):
        tables.add('sector_crosswalk', dict(
            crosswalk_row_id=f'oecd-crs.sector.{sector}.1', publisher_id='oecd',
            own_sector=sector, purpose_code=sector, recorded_at=recorded_at,
            decided_by=ONTOLOGY_DECIDER, status='accepted',
            notes='Identity mapping of OECD CRS purpose code'))
    for year, line_id in sorted(first_year_line.items()):
        tables.add('deflators', dict(series=DEFLATOR_SERIES, year=year, value=1,
            line_id=line_id, recorded_at=recorded_at))
    if require_full or (source_dir / 'rio-coefficients-2020.csv').exists():
        _coefficients(tables, source_dir, ledger_dir, recorded_at)
    country_by_line = {row['line_id']: row['country'] for row in tables.rows['lines']}
    country_by_doc = {row['document_id']: row.get('country')
                      for row in tables.rows['documents']}

    def country_for_relation(row):
        if row['line_id']:
            return country_by_line[row['line_id']]
        if row['from_kind'] == 'document':
            return country_by_doc[row['from_id']] or 'GLB'
        # Existing aliases of parties such as AFD have no country. GLB is a
        # storage bucket only; relations still make no country assertion.
        if row['from_kind'] == 'party':
            return 'GLB'
        raise ValueError(f"relation {row['relation_id']} needs a shard bucket")

    new_lines = [row for row in tables.rows['lines']
                 if (row['line_id'],) not in old_line_ids]
    _append_line_shards(ledger_dir, schema, new_lines, recorded_at)
    for name in names:
        if name == 'lines':
            continue
        kwargs = {'country_by_line_id': country_by_line}
        if name == 'relations':
            kwargs = {'country_for_row': country_for_relation}
        write_table(ledger_dir, name, tables.rows[name], schema=schema, **kwargs)
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--source-dir', type=Path, default=SOURCE_DIR)
    parser.add_argument('--output-dir', '--ledger-dir', dest='ledger_dir',
                        type=Path, default=LEDGER_DIR)
    parser.add_argument('--recorded-at', required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    log.info('%d CRS rows', ingest(args.source_dir, args.ledger_dir,
                                   recorded_at=args.recorded_at))


if __name__ == '__main__':
    main()
