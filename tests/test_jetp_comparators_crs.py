"""CRS microdata stays external line evidence, with typed money and Rio scores."""

import csv
import hashlib
import io
import shutil
from pathlib import Path

import pytest
from jetp._ledger_headers import LEDGER_DIR, load_schema, read_table, write_table
from jetp.build_crs_comparators import ingest
from jetp.build_ledger import build

pytestmark = pytest.mark.wp_jetp
ROOT = Path(__file__).resolve().parents[1]


def rows(directory, table):
    schema = load_schema()
    values, errors = read_table(directory, table, schema)
    assert errors == []
    return [dict(zip(schema.header(table), row)) for row in values]


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


def test_deposited_crs_slice_has_source_identifiers_and_sourced_coefficients():
    crs_lines = [row for row in rows(LEDGER_DIR, 'lines')
                 if row['line_id'].startswith('oecd-crs-energy-')]
    assert len(crs_lines) == 8029
    assert {country: sum(row['country'] == country for row in crs_lines)
            for country in ('IDN', 'SEN', 'VNM', 'ZAF')} == {
                'IDN': 2716, 'SEN': 1356, 'VNM': 2486, 'ZAF': 1471}
    external = {row['id'] for row in rows(LEDGER_DIR, 'external_ids')
                if row['scheme'] == 'oecd-crs-crs-id'}
    assert external == {row['line_id'] for row in crs_lines}
    assert len(rows(LEDGER_DIR, 'marker_coefficients')) == 12
    assert all(row['line_id'] for row in rows(LEDGER_DIR, 'marker_coefficients'))
