"""Documentary evidence identity and historical admission regressions (0762)."""

import hashlib
from copy import deepcopy

import pytest
from jetp.contracts import ContractError
from test_jetp_contracts import (
    AUGUST,
    JULY,
    SEPTEMBER,
    assertion,
    decision,
    read,
    ref,
    row,
)

DIGEST = hashlib.sha256(b'Fixture report: project-a construction completed.').hexdigest()
OTHER_DIGEST = hashlib.sha256(b'A different report.').hexdigest()
TARGET = ref('implementation_event', 'completed')
EVIDENCE = ref('evidence', 'report-excerpt')


def evidence_records():
    return [
        row('entity', 'project-a', country='VNM'),
        row('source', 'report-url', url='https://example.invalid/report.pdf'),
        row('acquisition', 'saved-report', source=ref('source', 'report-url'),
            retrieved_at=JULY, outcome='saved', document_sha256=DIGEST),
        row('edition', 'annual-report', publication_key='annual-2026',
            title='Annual report', publisher='Fixture publisher',
            publication_date='2026-06-30', publication_precision='day'),
        row('edition_snapshot', 'annual-bytes', edition=ref('edition', 'annual-report'),
            document_sha256=DIGEST),
        row('extraction', 'report-text', document_sha256=DIGEST,
            parser_version='fixture-parser/1', locators=['page=7;paragraph=2']),
        assertion('implementation_event', 'completed', evidence=[EVIDENCE], evidence_gap=None),
        row('evidence', 'report-excerpt', target=TARGET,
            edition=ref('edition', 'annual-report'),
            acquisition=ref('acquisition', 'saved-report'), document_sha256=DIGEST,
            locator='page=7;paragraph=2', extraction=ref('extraction', 'report-text'),
            support_role='supporting'),
        decision('completed-accepted', TARGET),
    ]


def find(records, kind):
    return next(record for record in records if record['record_kind'] == kind)


def test_evidence_tuple_round_trips_matching_bytes_edition_extraction_and_locator():
    records = evidence_records()
    store = read(records)
    assert store.to_dict()['records'] == records
    assert store.at(AUGUST, policy_version='fixture-v1').accepted(TARGET)
    # A consumer mutating an export cannot rewrite the validated evidence bytes.
    exported = store.to_dict()
    find(exported['records'], 'evidence')['document_sha256'] = OTHER_DIGEST
    assert find(store.to_dict()['records'], 'evidence')['document_sha256'] == DIGEST


@pytest.mark.parametrize('kind', ['acquisition', 'extraction', 'edition_snapshot', 'evidence'])
def test_different_document_bytes_cannot_complete_evidence_tuple(kind):
    records = evidence_records()
    find(records, kind)['document_sha256'] = OTHER_DIGEST
    with pytest.raises(ContractError, match='hash'):
        read(records)


def test_different_edition_cannot_borrow_another_editions_snapshot():
    records = evidence_records()
    other = deepcopy(find(records, 'edition'))
    other['record_id'] = 'different-edition'
    records.append(other)
    find(records, 'evidence')['edition'] = ref('edition', 'different-edition')
    with pytest.raises(ContractError, match='edition'):
        read(records)


def test_locator_must_resolve_in_the_pinned_extraction():
    records = evidence_records()
    find(records, 'evidence')['locator'] = 'page=8;paragraph=2'
    with pytest.raises(ContractError, match='locator'):
        read(records)


@pytest.mark.parametrize('outcome', ['failed', 'blocked'])
def test_failed_or_blocked_acquisition_cannot_supply_evidence(outcome):
    records = evidence_records()
    acquisition = find(records, 'acquisition')
    acquisition['outcome'] = outcome
    acquisition.pop('document_sha256')
    with pytest.raises(ContractError, match='hash'):
        read(records)


@pytest.mark.parametrize('kind', [
    'source', 'acquisition', 'edition', 'edition_snapshot', 'extraction', 'evidence',
])
def test_late_evidence_dependency_hides_assertion_at_earlier_cutoff(kind):
    records = evidence_records()
    find(records, kind)['recorded_at'] = '2026-09-02T00:00:00Z'
    store = read(records)
    early = store.at(AUGUST, policy_version='fixture-v1')
    assert not early.accepted(TARGET)
    assert ('implementation_event', 'completed') not in early.records
    assert store.at(SEPTEMBER, policy_version='fixture-v1').accepted(TARGET)
    assert store.at(AUGUST, policy_version='fixture-v1').to_dict() == early.to_dict()


def test_new_snapshot_and_extraction_do_not_rebind_old_evidence():
    records = evidence_records()
    for kind in ('acquisition', 'edition_snapshot', 'extraction'):
        old = find(records, kind)
        replacement = dict(old, record_id=old['record_id'] + '-new',
                           recorded_at='2026-09-02T00:00:00Z',
                           document_sha256=OTHER_DIGEST, supersedes=ref(kind, old['record_id']),
                           correction_reason='Updated document acquired at the same URL')
        records.append(replacement)
    store = read(records)
    for cutoff in (AUGUST, SEPTEMBER):
        view = store.at(cutoff, policy_version='fixture-v1')
        assert view.accepted(TARGET)
        assert view.records[('evidence', 'report-excerpt')]['document_sha256'] == DIGEST
        assert view.records[('acquisition', 'saved-report')]['document_sha256'] == DIGEST


def test_an_assertion_cannot_borrow_evidence_whose_target_is_another_assertion():
    records = evidence_records()
    records.append(assertion('implementation_event', 'unsupported',
                             evidence=[EVIDENCE], evidence_gap=None))
    records.append(decision('unsupported-accepted', ref('implementation_event', 'unsupported')))
    with pytest.raises(ContractError, match='evidence|target'):
        read(records)
