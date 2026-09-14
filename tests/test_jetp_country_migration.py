"""Inventory membership must not manufacture named projects or event timing."""

from jetp._country_migration import inventory_positions


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
