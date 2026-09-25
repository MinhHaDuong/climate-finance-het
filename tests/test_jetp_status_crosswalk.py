"""Publisher words map to the intended shared status axis (ticket 0887)."""

from pathlib import Path

import pytest
from jetp._ontology import ontology_as_of, shared_status
from jetp.build_crosswalks import ZAF_DELIVERY, crosswalk_rows, publishing_party

LEDGER = Path(__file__).resolve().parents[1] / 'data' / 'jetp'


pytestmark = pytest.mark.wp_jetp

def test_register_words_are_verbatim_and_map_only_to_delivery():
    status, _, _ = crosswalk_rows(LEDGER)
    party = publishing_party(LEDGER, 'zaf-jet-investment-register-q1-2026')
    actual = {row['own_status']: (row['axis'], row['shared_status'])
              for row in status if row['publisher_id'] == party}
    assert actual == {own: ('delivery', shared) for own, shared in ZAF_DELIVERY.items()}
    ontology = ontology_as_of(LEDGER)
    assert shared_status(ontology, party, 'Publisher word not covered') is None


def test_indonesian_approval_maps_to_money_only():
    ontology = ontology_as_of(LEDGER)
    party = publishing_party(LEDGER, 'idn-jetp-progress-report-2025')
    assert shared_status(ontology, party, 'Approved') == ('money', 'approved')
    assert shared_status(ontology, party, 'suspended') is None
