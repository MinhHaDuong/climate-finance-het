"""Ticket 0877: perimeters preserve source units and cited membership."""

from pathlib import Path

import pytest
from jetp import build_perimeters
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


