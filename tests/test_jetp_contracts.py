"""Small documentary fixtures for the pre-migration contracts (0762)."""

from copy import deepcopy
import json

import pytest

from jetp.contracts import ContractError, read_contract

JULY = '2026-07-01T00:00:00Z'
AUGUST = '2026-08-31T00:00:00Z'
SEPTEMBER = '2026-09-30T00:00:00Z'


def ref(kind, identity):
    return {'record_kind': kind, 'record_id': identity}


def row(kind, identity, **fields):
    return dict(record_kind=kind, record_id=identity, recorded_at=JULY,
                recorded_by='fixture-author', **fields)


def decision(identity, target, *, verdict='accepted', **fields):
    return row('adjudication', identity, decision_type='acceptance', verdict=verdict,
               reason='Fixture documentary review', reviewer='fixture-reviewer',
               reviewed_at=JULY, policy_version='fixture-v1',
               members=[dict(role='candidate', target=target)], **fields)


def assertion(kind, identity, **fields):
    defaults = dict(subject=ref('entity', 'project-a'), measure='implementation_status',
                    value_type='status', value_text='completed', original_label='Completed',
                    evidence_gap='No saved document in this synthetic fixture')
    defaults.update(fields)
    return row(kind, identity, **defaults)


def document(*records):
    return {'schema_version': 'jetp-core-v1', 'records': list(records)}


def read(records):
    return read_contract(document(*records), supported_versions={'jetp-core-v1'})


def test_typed_collision_late_duplicate_and_pending_replacement():
    """0762-first: IDs collide; September review cannot leak into August."""
    financial = ref('financial_event', 'same-id')
    physical = ref('implementation_event', 'same-id')
    replacement = ref('financial_event', 'corrected')
    records = [row('entity', 'project-a', country='VNM'),
               assertion('financial_event', 'same-id'),
               assertion('implementation_event', 'same-id'),
               assertion('financial_event', 'corrected', supersedes=financial,
                         correction_reason='Correct transcription'),
               decision('finance-accepted', financial), decision('physical-accepted', physical),
               decision('correction-pending', replacement, verdict='pending'),
               row('occurrence', 'payment-1'), row('occurrence', 'payment-2'),
               row('adjudication', 'duplicate-late', decision_type='occurrence_membership',
                   verdict='accepted', reason='Same reported payment', reviewer='reviewer',
                   reviewed_at='2026-09-03T00:00:00Z', policy_version='fixture-v1',
                   members=[dict(role='accepted', target=financial),
                            dict(role='occurrence', target=ref('occurrence', 'payment-1'))])]
    store = read(records)
    early = store.at(AUGUST, policy_version='fixture-v1')
    late = store.at(SEPTEMBER, policy_version='fixture-v1')
    assert early.accepted(financial) and early.accepted(physical)
    assert not early.accepted(replacement)
    assert early.occurrence_for(financial) is None
    assert late.occurrence_for(financial) == ref('occurrence', 'payment-1')
    assert late.occurrence_for(physical) is None
    assert early.records[('financial_event', 'same-id')]['record_kind'] == 'financial_event'
    assert store.at(AUGUST, policy_version='fixture-v1').to_dict() == early.to_dict()


def test_late_acceptance_withdrawal_and_review_admission_are_distinct():
    target = ref('implementation_event', 'state')
    accepted = decision('accept', target)
    records = [row('entity', 'project-a', country='VNM'),
               assertion('implementation_event', 'state'), accepted]
    late = decision('withdraw', target, verdict='withdrawn',
                    supersedes=ref('adjudication', 'accept'), correction_reason='Retracted')
    late['recorded_at'] = '2026-09-01T00:00:00Z'
    records.append(late)
    store = read(records)
    assert store.at(AUGUST, policy_version='fixture-v1').accepted(target)
    assert not store.at(SEPTEMBER, policy_version='fixture-v1').accepted(target)
    accepted['reviewed_at'] = '2026-09-02T00:00:00Z'
    assert not read(records).at(AUGUST, policy_version='fixture-v1').accepted(target)


def test_accepted_correction_only_replaces_after_acceptance():
    old = ref('implementation_event', 'old')
    new = ref('implementation_event', 'new')
    records = [row('entity', 'project-a', country='VNM'),
               assertion('implementation_event', 'old'),
               assertion('implementation_event', 'new', supersedes=old,
                         correction_reason='Status correction'), decision('old-accepted', old)]
    late = decision('new-accepted', new)
    late['reviewed_at'] = '2026-09-03T00:00:00Z'
    records.append(late)
    assert read(records).at(AUGUST, policy_version='fixture-v1').accepted(old)
    current = read(records).at(SEPTEMBER, policy_version='fixture-v1')
    assert current.accepted(new) and not current.accepted(old)


def test_reject_unknown_version_and_typed_reference():
    with pytest.raises(ContractError, match='version'):
        read_contract(document(), supported_versions={'future-v2'})
    with pytest.raises(ContractError, match='reference'):
        read([decision('wrong-kind', ref('agreement', 'project-a')),
              row('entity', 'project-a', country='VNM')])


def test_money_scale_and_date_roles_round_trip_without_float_conversion():
    records = [row('entity', 'project-a', country='VNM'),
               row('perimeter', 'ipg', country='VNM', name='IPG', scope='jetp_strict',
                   definition='IPG gross pledges', membership_basis='undisclosed'),
               assertion('position', 'usd392', measure='pledge', value_type='money',
                         value_text=None, value_decimal='3920000000', currency='USD', unit='USD',
                         original_value='3.92', original_scale='billion',
                         perimeter=ref('perimeter', 'ipg'), basis='cumulative_amount',
                         original_label='USD 3.92 billion', value_lower='3915000000',
                         value_upper='3925000000', cutoff_earliest='2026-06-01',
                         cutoff_latest='2026-06-30', cutoff_precision='month'),
               assertion('implementation_event', 'same-id', timing=[{
                   'date_role': 'observed_state', 'event_start': '2026-06-30',
                   'event_end': '2026-06-30', 'event_precision': 'day'}])]
    store = read(records)
    exported = json.loads(json.dumps(store.to_dict()))
    assert exported == document(*records)
    assert read_contract(exported, supported_versions={'jetp-core-v1'}).to_dict() == exported
    assert exported['records'][2]['value_decimal'] == '3920000000'
    assert exported['records'][3]['timing'][0]['date_role'] == 'observed_state'


@pytest.mark.parametrize('changes', [
    {'value_decimal': 3920000000.0}, {'currency': None}, {'unit': 'billion USD'},
    {'value_text': '3.92'}, {'value_lower': '4000000000'},
])
def test_invalid_money_or_precision_is_rejected(changes):
    value = assertion('financial_event', 'money', value_type='money', value_text=None,
                      value_decimal='3920000000', currency='USD', unit='USD',
                      original_value='3.92', original_scale='billion',
                      perimeter=ref('perimeter', 'coverage'))
    value.update(changes)
    with pytest.raises(ContractError):
        read([row('entity', 'project-a', country='VNM'),
              row('perimeter', 'coverage', country='VNM', name='All', scope='jetp_strict',
                  definition='All original-currency payments', membership_basis='undisclosed'), value])
