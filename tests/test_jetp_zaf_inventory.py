"""Pinned South African register and principal-report inventories remain distinct."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.wp_jetp

@pytest.mark.slow
def test_saved_zaf_register_and_finance_tables_are_complete():
    from jetp._zaf_inventory import extract_inventory

    root = Path(__file__).resolve().parents[1]
    policy = json.loads((root / 'config/jetp-zaf-migration.json').read_text())
    result = extract_inventory(root / 'data/jetp/documents', policy)
    assert len(result['register_rows']) == 257
    assert len(result['report_rows']) == 82
    assert {r['inventory_id'] for r in result['report_rows']} == {f'Table {n}' for n in range(1, 12)}
    assert len({r['locator'] for r in result['report_rows']}) == 82
    table1 = next(r for r in result['report_rows'] if r['inventory_id'] == 'Table 1')
    assert table1['source_fields']['cells'][1:3] == ['ZAR 17.51', 'ZAR 15.26']
    assert all(r['pages'] and r['source_fields'] for r in result['report_rows'])
    totals = next(r for r in result['report_rows'] if r['inventory_id'] == 'Table 5'
                  and r['source_fields']['cells'][0] == 'Grand Total')
    assert totals['source_fields']['cells'][-3:] == ['129', '87', '257']
