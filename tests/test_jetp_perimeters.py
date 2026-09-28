"""Ticket 0877: perimeters preserve source units and cited membership."""

import csv
import shutil
from pathlib import Path

import pytest
from jetp import build_perimeters
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

    for relative in ('observations.csv', 'timings.csv', 'retrievals.csv',
                     'migration/0875-dispositions.csv',
                     'migration/0970-event-adjudications.csv',
                     'migration/1120-event-adjudications.csv',
                     'migration/1160-citation-decisions.csv'):
        copy(relative)
    for source in (LEDGER / 'lines.d').glob('*.csv'):
        copy(Path('lines.d') / source.name)

    observation = next(r for r in csv.DictReader((tmp_path / 'observations.csv').open())
                       if r['observation_id'] == '0877.zaf-founding-pledge')
    observation.update(observation_id='later.comparator-one', method='comparator_record')
    with (tmp_path / 'observations.csv').open('a', newline='', encoding='utf-8') as handle:
        csv.DictWriter(handle, fieldnames=observation).writerow(observation)
    timing = next(r for r in csv.DictReader((tmp_path / 'timings.csv').open())
                  if r['observation_id'] == '0877.zaf-founding-pledge')
    timing.update(timing_id='later.comparator-one.report_date',
                  observation_id='later.comparator-one')
    with (tmp_path / 'timings.csv').open('a', newline='', encoding='utf-8') as handle:
        csv.DictWriter(handle, fieldnames=timing).writerow(timing)

    def legacy(table):
        with (LEDGER / table).open(newline='', encoding='utf-8') as handle:
            return list(csv.DictReader(handle))

    write_normalized_event_tables(tmp_path, legacy('events.csv'),
                                  legacy('implementation-events.csv'),
                                  legacy('event-timing.csv'))
    with (tmp_path / 'observations.csv').open(newline='', encoding='utf-8') as handle:
        ids = {r['observation_id'] for r in csv.DictReader(handle)}
    with (tmp_path / 'timings.csv').open(newline='', encoding='utf-8') as handle:
        timing_ids = {r['timing_id'] for r in csv.DictReader(handle)}
    assert {'0877.zaf-founding-pledge', 'later.comparator-one'} <= ids
    assert {'0877.zaf-founding-pledge.report_date',
            'later.comparator-one.report_date'} <= timing_ids
