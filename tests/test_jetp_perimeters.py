"""Ticket 0877: perimeters preserve source units and cited membership."""

import csv
import shutil
from pathlib import Path

import pytest
from jetp import build_perimeters
from jetp._ledger_headers import load_schema, read_table, table_files, write_table
from jetp.build_observations import write_normalized_event_tables
from jetp.build_perimeters import build_rows, ruptl_memberships

LEDGER = Path(__file__).resolve().parents[1] / 'data' / 'jetp'
pytestmark = pytest.mark.wp_jetp


def test_two_source_marked_lines_join_ruptl_without_minting_projects():
    plans = [
        dict(country='IDN', plan_project_id='a', ruptl='YES', reconciliation_status='plan_only'),
        dict(country='IDN', plan_project_id='b', ruptl='YES', reconciliation_status='plan_only'),
        dict(country='IDN', plan_project_id='c', ruptl='NO', reconciliation_status='plan_only'),
        dict(country='IDN', plan_project_id='d', ruptl='YES', reconciliation_status='matched'),
    ]
    memberships = ruptl_memberships(plans, {'a': 'line-a', 'b': 'line-b'},
                                    {'line-a', 'line-b'}, expected_count=2)
    assert [(r['from_kind'], r['from_id'], r['to_id']) for r in memberships] == [
        ('line', 'line-a', 'idn-cipp-ruptl-plan-lines'),
        ('line', 'line-b', 'idn-cipp-ruptl-plan-lines'),
    ]
    with pytest.raises(ValueError, match='lacks routed line'):
        ruptl_memberships(plans, {'a': 'line-a'}, {'line-a'}, expected_count=2)


def test_published_counts_are_two_cited_perimeter_observations_not_slot_identities():
    rows = build_rows(LEDGER)
    by_id = {r['observation_id']: r for r in rows['observations']}
    for suffix, value, line in (
        ('initial', 7, 'vnm-pilot-observations-local-record-row-34'),
        ('screened', 17, 'vnm-pilot-observations-local-record-row-35'),
    ):
        count = by_id[f'0877.vnm-2025-{suffix}-count']
        assert (count['subject_kind'], count['subject_id'], count['measure'],
                count['value'], count['line_id']) == (
                    'perimeter', 'vnm-jetp-portfolio-2025', 'count', value, line)
    assert not any('undisclosed' in r['from_id'] for r in rows['relations'])
    assert len([r for r in rows['relations'] if r['relation_id'].startswith('0877.ruptl.')]) == 230


def test_aggregate_values_have_exact_cited_lines_and_no_summed_headline():
    rows = build_rows(LEDGER)
    lines = {r['line_id'] for r in rows['lines']}
    aggregates = [r for r in rows['observations'] if r['observation_id'].startswith('0877.')]
    assert len(aggregates) == 8
    assert all(r['line_id'] in lines for r in aggregates)
    zaf = {r['observation_id']: r for r in aggregates if r['subject_id'] == 'zaf-jetp'}
    assert zaf['0877.zaf-q126-allocated']['value'] == 6_120_000_000
    assert zaf['0877.zaf-founding-pledge']['value'] == 8_500_000_000
    own_timings = [r for r in rows['timings'] if r['timing_id'].startswith('0877.')]
    assert len(own_timings) == 9
    assert {r['observation_id'] for r in own_timings} == {
        r['observation_id'] for r in aggregates}


def test_uncited_perimeter_observation_is_refused(monkeypatch):
    broken = list(build_perimeters.COUNTS)
    broken[0] = ('initial', 7, 'missing-source-line', 'source count')
    monkeypatch.setattr(build_perimeters, 'COUNTS', tuple(broken))
    with pytest.raises(ValueError, match='count lacks cited line'):
        build_rows(LEDGER)


def test_legacy_event_rebuild_preserves_later_observations_and_their_timings(tmp_path):
    def copy(relative):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LEDGER / relative, target)

    for relative in ('retrievals.csv',
                     'migration/0875-dispositions.csv',
                     'migration/0970-event-adjudications.csv',
                     'migration/1120-event-adjudications.csv',
                     'migration/1160-citation-decisions.csv'):
        copy(relative)
    for source in (LEDGER / 'lines.d').glob('*.csv'):
        copy(Path('lines.d') / source.name)

    schema = load_schema()
    for table in ('observations', 'timings'):
        files, errors = table_files(LEDGER, table)
        assert not errors
        for source, _, _ in files:
            copy(source.relative_to(LEDGER))

    def ledger_rows(table):
        values, errors = read_table(tmp_path, table, schema)
        assert not errors
        return [dict(zip(schema.header(table), value)) for value in values]

    observations = ledger_rows('observations')
    observation = next(r for r in observations
                       if r['observation_id'] == '0877.zaf-founding-pledge')
    observation = dict(observation, observation_id='later.comparator-one',
                       method='comparator_record')
    observations.append(observation)
    timings = ledger_rows('timings')
    timing = next(r for r in timings
                  if r['observation_id'] == '0877.zaf-founding-pledge')
    timing = dict(timing, timing_id='later.comparator-one.report_date',
                  observation_id='later.comparator-one')
    timings.append(timing)
    line_country = {row['line_id']: row['country'] for row in ledger_rows('lines')}
    write_table(tmp_path, 'observations', observations, schema=schema,
                country_by_line_id=line_country)
    observation_country = {row['observation_id']: line_country[row['line_id']]
                           for row in observations}
    write_table(tmp_path, 'timings', timings, schema=schema,
                country_for_row=lambda row: observation_country[row['observation_id']])

    def legacy(table):
        with (LEDGER / table).open(newline='', encoding='utf-8') as handle:
            return list(csv.DictReader(handle))

    write_normalized_event_tables(tmp_path, legacy('events.csv'),
                                  legacy('implementation-events.csv'),
                                  legacy('event-timing.csv'))
    ids = {r['observation_id'] for r in ledger_rows('observations')}
    timing_ids = {r['timing_id'] for r in ledger_rows('timings')}
    assert {'0877.zaf-founding-pledge', 'later.comparator-one'} <= ids
    assert {'0877.zaf-founding-pledge.report_date',
            'later.comparator-one.report_date'} <= timing_ids
