"""Publisher technology groups map only to defensible CRS purposes (ticket 0888)."""

from pathlib import Path

from jetp._ontology import ontology_as_of
from jetp.build_crosswalks import (
    IDN_PURPOSE,
    ZAF_PURPOSE,
    crosswalk_rows,
    distinct_field,
    publishing_party,
)

LEDGER = Path(__file__).resolve().parents[1] / 'data' / 'jetp'
REPORT = 'idn-jetp-progress-report-2025'


def test_report_groups_are_counted_against_the_fields_and_ambiguous_ones_stay_open():
    _, rows, unresolved = crosswalk_rows(LEDGER)
    own = distinct_field(LEDGER, REPORT, 'technology_group')
    party = publishing_party(LEDGER, REPORT)
    idn_rows = [row for row in rows if row['publisher_id'] == party]
    assert {row['own_sector'] for row in idn_rows} | unresolved >= own
    assert {'other_dispatchable', 'supply_chain'} <= unresolved
    assert {row['own_sector']: row['purpose_code'] for row in idn_rows} == {
        word: code for word, code in IDN_PURPOSE.items() if word in own}


def test_sector_rows_use_the_document_author_and_are_in_force():
    party = publishing_party(LEDGER, REPORT)
    rows = ontology_as_of(LEDGER)['sector_crosswalk']
    assert rows and sum(row['publisher_id'] == party for row in rows) == 4
    zaf = publishing_party(LEDGER, 'zaf-jet-investment-register-q1-2026')
    assert {row['own_sector']: row['purpose_code'] for row in rows
            if row['publisher_id'] == zaf} == ZAF_PURPOSE
    assert all(len(row['purpose_code']) == 5 for row in rows)
