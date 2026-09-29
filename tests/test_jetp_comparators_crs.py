"""CRS microdata stays external line evidence, with typed money and Rio scores."""

import csv
import gzip
import hashlib
import io
import json
import shutil
import sqlite3
import urllib.error
from pathlib import Path

import pytest
from jetp._ledger_headers import (
    DDL_PATH,
    LEDGER_DIR,
    load_schema,
    read_table,
    write_table,
)
from jetp.build_crs_bulk_sqlite import materialize
from jetp.build_crs_comparators import _activity, ingest
from jetp.build_ledger import build
from jetp.catalog_crs_bulk import _fetch

pytestmark = pytest.mark.wp_jetp
ROOT = Path(__file__).resolve().parents[1]


def rows(directory, table):
    schema = load_schema()
    values, errors = read_table(directory, table, schema)
    assert errors == []
    return [dict(zip(schema.header(table), row)) for row in values]


def test_same_year_flow_siblings_are_not_cross_year_relations():
    class Recorder:
        def __init__(self):
            self.added = []

        def add(self, table, row):
            self.added.append((table, row))

    tables = Recorder()
    anchors = {}
    for year, line in ((2020, 'commitment'), (2020, 'disbursement'),
                       (2021, 'commitment')):
        _activity(tables, {'DONOR': 'FRA', 'DONOR_PROJECT_ID': 'P1',
                           'TIME_PERIOD': str(year)}, f'{line}-{year}',
                  anchors, '2026-09-28')
    relations = [row for table, row in tables.added if table == 'relations']
    assert len(relations) == 1
    assert relations[0]['from_id'] == 'commitment-2021'
    assert relations[0]['to_id'] == 'commitment-2020'


def test_bulk_collector_refuses_404_instead_of_archiving_an_empty_year(monkeypatch):
    def missing(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 404, 'Not Found', {}, None)

    monkeypatch.setattr('jetp.catalog_crs_bulk.urllib.request.urlopen', missing)
    with pytest.raises(ValueError, match='returned 404'):
        _fetch('https://example.test/crs')


def test_dvc_bulk_rows_materialize_only_in_disposable_sqlite(tmp_path):
    base = tmp_path / 'base.sqlite'
    output = tmp_path / 'bulk.sqlite'
    with sqlite3.connect(base) as conn:
        conn.executescript(DDL_PATH.read_text())
        conn.execute("INSERT INTO documents (document_id,title) VALUES ('oecd-source','OECD')")
        conn.execute("INSERT INTO parties (party_id) VALUES ('oecd')")
        conn.execute("INSERT INTO party_names (name_row_id,party_id,name,form_type,"
                     "document_id,recorded_at,decided_by,status) VALUES "
                     "('oecd.name.1','oecd','OECD','preferred','oecd-source',"
                     "'2026-09-28','fixture','accepted')")
    bulk = tmp_path / 'bulk'
    bulk.mkdir()
    name = 'crs_IDN_2020_micro.csv.gz'
    with (LEDGER_DIR / 'comparison/crs/crs_IDN_2020_Q.csv').open(newline='') as handle:
        fields = next(csv.reader(handle))
    source_rows = []
    for ordinal, price in enumerate(('Q', 'V', 'Q'), 1):
        row = dict.fromkeys(fields, '')
        row.update(DONOR='FRA', RECIPIENT='IDN', SECTOR='23210', MEASURE='11',
                   CHANNEL='0', MODALITY='C01', FLOW_TYPE='C', PRICE_BASE=price,
                   MD_DIM='DD', MD_ID=str(ordinal), UNIT_MEASURE='USD',
                   TIME_PERIOD='2020', PROJECT_TITLE='Energy source row')
        source_rows.append(row)
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(source_rows)
    raw = stream.getvalue().encode()
    (bulk / name).write_bytes(gzip.compress(raw, mtime=0))
    manifest = {name: dict(country='IDN', year=2020,
        url='https://example.test/crs', retrieved_at='2026-09-28T10:00:00+00:00',
        response_sha256=hashlib.sha256(raw).hexdigest(), response_bytes=len(raw),
        rows=3, price_q_rows=2, field_count=51)}
    reviewed = tmp_path / 'reviewed.json'
    reviewed.write_text(json.dumps(manifest))
    (bulk / 'manifest.json').write_bytes(reviewed.read_bytes())

    assert materialize(base, output, bulk, reviewed, require_full=False) == 3
    with sqlite3.connect(output) as conn:
        assert conn.execute("SELECT COUNT(*) FROM lines WHERE line_id LIKE 'oecd-crs-all-%'").fetchone()[0] == 3
        assert conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM documents WHERE document_id LIKE 'oecd-crs-all-%'").fetchone()[0] == 1
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
    with sqlite3.connect(base) as conn:
        assert conn.execute('SELECT COUNT(*) FROM lines').fetchone()[0] == 0
    assert not list(tmp_path.glob('*.csv'))


def test_two_activities_over_two_years_keep_flow_and_marker_meanings(tmp_path):
    ledger = tmp_path / 'jetp'
    ledger.mkdir()
    schema = load_schema()
    for table in schema.tables:
        write_table(ledger, table, [], schema=schema)
    shutil.copy2(LEDGER_DIR / 'ontology/terms.csv', ledger / 'ontology/terms.csv')
    (ledger / 'lines.csv').unlink()
    (ledger / 'lines.d').mkdir()
    source_dir = ledger / 'comparison/crs'
    source_dir.mkdir(parents=True)
    with (LEDGER_DIR / 'comparison/crs/crs_IDN_2020_Q.csv').open(newline='') as handle:
        fields = next(csv.reader(handle))
    manifest = []
    for year in (2020, 2021):
        sample = []
        for ordinal, activity in enumerate(('A', 'B'), 1):
            row = dict.fromkeys(fields, '')
            row.update(DATAFLOW='OECD.DCD.FSD:DSD_CRS@DF_CRS(1.6)',
                DONOR='FRA', RECIPIENT='IDN', SECTOR='23210', MEASURE='11',
                CHANNEL='0', MODALITY='C01', FLOW_TYPE='C' if year == 2020 else 'D',
                PRICE_BASE='Q', MD_DIM='DD', MD_ID=f'T{year}{ordinal}',
                UNIT_MEASURE='USD', TIME_PERIOD=str(year),
                OBS_VALUE='2.5' if activity == 'A' else '0', BASE_PER='2024',
                UNIT_MULT='6', OECD_ID=f'O{activity}', DONOR_PROJECT_ID=f'P{activity}',
                PROJECT_TITLE=f'Energy project {activity}',
                CLIMATE_MITIGATION='2' if activity == 'A' else '')
            sample.append(row)
        output = io.StringIO()
        writer = csv.DictWriter(output, fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(sample)
        data = output.getvalue().encode()
        name = f'crs_IDN_{year}_Q.csv'
        (source_dir / name).write_bytes(data)
        manifest.append(dict(country='IDN', year=year, projection_file=name,
            projection_sha256=hashlib.sha256(data).hexdigest(),
            projection_bytes=len(data), q_rows=2, source_sha256='fixture'))
    with (source_dir / 'manifest.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, manifest[0], lineterminator='\n')
        writer.writeheader()
        writer.writerows(manifest)

    assert ingest(source_dir, ledger, recorded_at='2026-10-01', require_full=False) == 4
    assert build(ledger) == []
    crs_lines = [row for row in rows(ledger, 'lines')
                 if row['line_id'].startswith('oecd-crs-energy-')]
    assert len(crs_lines) == 4
    assert sum(row['relation'] == 'same_as' and row['from_id'] in {
        line['line_id'] for line in crs_lines} for row in rows(ledger, 'relations')) == 2
    observations = [row for row in rows(ledger, 'observations')
                    if row['method'] == 'oecd_crs_energy_microdata']
    flows = [row for row in observations if row['measure'] == 'flow']
    assert len(flows) == 4
    assert {row['flow_type'] for row in flows} == {'commitment', 'disbursement'}
    assert {row['value'] for row in flows} == {'2500000', '0'}
    assert all(row['currency'] == 'USD' and 'no FX' in row['notes'] for row in flows)
    mitigation = [row for row in observations if row['indicator_code'] == 'mitigation']
    assert {row['own_status'] for row in mitigation} == {'not_screened', '2'}
    assert all(row['value'] is None for row in mitigation
               if row['own_status'] == 'not_screened')
    assert all(row['value'] == '2' for row in mitigation if row['own_status'] == '2')
    assert {row['year'] for row in rows(ledger, 'deflators')
            if row['series'].startswith('oecd-crs-Q')} == {'2020', '2021'}
    assert {row['value'] for row in rows(ledger, 'deflators')} == {'1'}
    assert all(row['project_id'] not in {f'P{activity}' for activity in ('A', 'B')}
               for row in rows(ledger, 'projects'))
    assert ingest(source_dir, ledger, recorded_at='2026-10-01', require_full=False) == 4
    assert len([row for row in rows(ledger, 'lines') if row in crs_lines]) == 4
    assert len(rows(ledger, 'deflators')) == 2


@pytest.mark.slow
def test_deposited_crs_slice_has_source_identifiers_and_sourced_coefficients():
    """Reads the deposited ledger: JETP gate and full check, not the fast loop."""
    crs_lines = [row for row in rows(LEDGER_DIR, 'lines')
                 if row['line_id'].startswith('oecd-crs-energy-')]
    assert len(crs_lines) == 8029
    assert {country: sum(row['country'] == country for row in crs_lines)
            for country in ('IDN', 'SEN', 'VNM', 'ZAF')} == {
                'IDN': 2716, 'SEN': 1356, 'VNM': 2486, 'ZAF': 1471}
    external = {row['id'] for row in rows(LEDGER_DIR, 'external_ids')
                if row['scheme'] == 'oecd-crs-crs-id'}
    assert external == {row['line_id'] for row in crs_lines}
    by_line_id = {row['line_id']: row for row in crs_lines}
    same_as = [row for row in rows(LEDGER_DIR, 'relations')
               if row['relation_id'].startswith('same-as-oecd-crs-energy-')]
    assert len(same_as) == 2864
    assert all(by_line_id[row['from_id']]['locator'].rsplit('/', 1)[-1] !=
               by_line_id[row['to_id']]['locator'].rsplit('/', 1)[-1]
               for row in same_as)
    assert len(rows(LEDGER_DIR, 'marker_coefficients')) == 12
    assert all(row['line_id'] for row in rows(LEDGER_DIR, 'marker_coefficients'))
