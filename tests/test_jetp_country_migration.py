"""Inventory membership must not manufacture named projects or event timing."""

import pytest
from jetp._country_migration import inventory_positions, legacy_dispositions
from jetp._source_crosswalk import migrate_sources
from test_jetp_source_crosswalk import table


def test_official_rows_without_pages_exact_mapping_and_unnamed_count():
    rows = [
        dict(inventory_id='I.1', ordinal=1, pages=[155], source_wording='Named wind project'),
        dict(inventory_id='I.1', ordinal=2, pages=[155], source_wording='Bac Ai pumped storage'),
        dict(inventory_id='I.2', ordinal=1, pages=[159],
             source_wording='Pilot testing for 3-4 suitable coal-fired power plants (CFPPs)'),
    ]
    projects = [dict(project_id='vnm-bac-ai', canonical_name='Bac Ai pumped storage')]
    joins = {'I.1:2': dict(project_ids=['vnm-bac-ai'],
                          source_wording='Bac Ai pumped storage',
                          rationale='Exact named pumped-storage asset; fixture adjudication')}
    result = inventory_positions('VNM', rows, projects, joins)
    assert [r['disposition'] for r in result] == [
        'unresolved_inventory_membership', 'explicit_identity_mapping',
        'unresolved_inventory_membership']
    assert result[1]['entity_ids'] == ['vnm-bac-ai']
    assert result[2]['entity_ids'] == []
    assert result[2]['source_wording'] == rows[2]['source_wording']
    assert all(r['transition_date'] is None and r['payment_amount'] is None for r in result)
    assert result == inventory_positions('VNM', rows, projects, joins)


def test_tri_an_solar_does_not_join_hydropower_by_place():
    rows = [dict(inventory_id='I.1', ordinal=22, pages=[156],
                 source_wording='KN Tri An Floating Solar Farm')]
    projects = [dict(project_id='vnm-project-tri-an-expansion',
                     canonical_name='Tri An hydropower plant expansion')]
    assert inventory_positions('VNM', rows, projects, {})[0]['entity_ids'] == []


def test_legacy_states_and_unknown_count_slots_survive_losslessly(tmp_path):
    rows = [dict(observation_id='o1', country='VNM', event_date='2025-07',
                 legacy_status='cancelled', project_count='24', amount_original='7040000000')]
    table(tmp_path, 'vnm-pilot-observations.csv', rows)
    table(tmp_path, 'projects.csv', [dict(project_id='slot-1', country='VNM',
                                         verification_status='official_count_slot')])
    table(tmp_path, 'dry-searches.csv', [dict(country='VNM', outcome='not_attempted')])
    crosswalk = migrate_sources(tmp_path)
    policy = {'o1': dict(classification='reported_portfolio_count', reason='Count, not identities')}
    result = legacy_dispositions(crosswalk, 'VNM', policy)
    assert len(result) == 3
    retained = next(r for r in result if r['original'].get('observation_id') == 'o1')
    assert retained['original'] == rows[0]
    assert retained['transition_date'] is None
    assert retained['payment_amount'] is None
    assert all(r['disposition'] == 'retained_legacy_authority' for r in result)
    with pytest.raises(ValueError, match='Missing observation disposition'):
        legacy_dispositions(crosswalk, 'VNM', {})


def test_country_disposition_follows_financial_and_implementation_timing_links(tmp_path):
    table(tmp_path, 'projects.csv', [dict(project_id='zaf-p', country='ZAF')])
    table(tmp_path, 'events.csv', [dict(event_id='finance', project_id='zaf-p', country='ZAF')])
    table(tmp_path, 'implementation-events.csv', [dict(event_id='physical', project_id='zaf-p', country='ZAF')])
    table(tmp_path, 'event-timing.csv', [dict(event_id='finance', date_role='register'),
                                      dict(event_id='physical', date_role='observed'),
                                      dict(event_id='finance', date_role='register'),
                                      dict(event_id='foreign', date_role='event')])
    crosswalk = migrate_sources(tmp_path)
    result = legacy_dispositions(crosswalk, 'ZAF', {})
    timing = [row for row in result if row['path'].endswith('event-timing.csv')]
    assert {row['original']['event_id'] for row in timing} == {'finance', 'physical'}
    assert all(row['classification'] == 'legacy_timing_retained' for row in timing)

    assert len(timing) == 3
    assert len({row['row_id'] for row in timing}) == 3
    assert any(row['row'].get('event_id') == 'foreign' for row in crosswalk['retained'])
