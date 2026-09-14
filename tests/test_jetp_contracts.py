"""Small documentary fixtures for the pre-migration contracts (0762)."""

import json
from copy import deepcopy

import pytest
from jetp._contracts import ContractError, read_contract

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


def relation(identity, source, target, relationship='alias_of', **fields):
    return row('relation', identity, **{'from': source, 'to': target},
               relationship=relationship, valid_from='2026-01-01', valid_to='open',
               date_precision='day', **fields)


def relation_store(relations, kind='entity'):
    records = [row(kind, identity, country='VNM') for identity in ('a', 'b', 'c')]
    for item in relations:
        records.extend([item, decision('accept-' + item['record_id'], ref('relation', item['record_id']))])
    return read(records)


@pytest.mark.parametrize('relationship,kind', [('alias_of', 'entity'), ('component_of', 'entity'),
                                               ('tranche_of', 'agreement')])
def test_active_containment_and_alias_cycles_rejected(relationship, kind):
    store = relation_store([relation('ab', ref(kind, 'a'), ref(kind, 'b'), relationship),
                            relation('ba', ref(kind, 'b'), ref(kind, 'a'), relationship)], kind)
    with pytest.raises(ContractError, match='cycle'):
        store.at(AUGUST, policy_version='fixture-v1').relations_at('2026-08-01')


@pytest.mark.parametrize('relationship,kind', [('alias_of', 'entity'), ('tranche_of', 'agreement')])
def test_multiple_active_parent_or_alias_targets_rejected(relationship, kind):
    store = relation_store([relation('ab', ref(kind, 'a'), ref(kind, 'b'), relationship),
                            relation('ac', ref(kind, 'a'), ref(kind, 'c'), relationship)], kind)
    with pytest.raises(ContractError, match='multiple active'):
        store.at(AUGUST, policy_version='fixture-v1').relations_at('2026-08-01')


def test_alias_chain_rejected_and_world_validity_is_half_open():
    ab = relation('ab', ref('entity', 'a'), ref('entity', 'b'))
    bc = relation('bc', ref('entity', 'b'), ref('entity', 'c'))
    with pytest.raises(ContractError, match='itself an alias'):
        relation_store([ab, bc]).at(AUGUST, policy_version='fixture-v1').relations_at('2026-08-01')
    ab['valid_to'] = '2026-08-01'
    assert relation_store([ab]).at(AUGUST, policy_version='fixture-v1').relations_at('2026-08-01') == []
    ab['valid_to'] = 'unknown'
    with pytest.raises(ContractError, match='unresolved relation'):
        relation_store([ab]).at(AUGUST, policy_version='fixture-v1').relations_at('2026-08-01')


def test_late_alias_replacement_preserves_earlier_canonical_target():
    ab = relation('ab', ref('entity', 'a'), ref('entity', 'b'))
    ac = relation('ac', ref('entity', 'a'), ref('entity', 'c'),
                  supersedes=ref('relation', 'ab'), correction_reason='Verified route target')
    records = relation_store([ab, ac]).to_dict()['records']
    records[-1]['reviewed_at'] = '2026-09-03T00:00:00Z'
    store = read(records)
    assert store.at(AUGUST, policy_version='fixture-v1').relations_at('2026-08-01')[0]['to'] == ref('entity', 'b')
    assert store.at(SEPTEMBER, policy_version='fixture-v1').relations_at('2026-08-01')[0]['to'] == ref('entity', 'c')


def test_supersession_cycle_and_active_fork_rejected():
    old = assertion('implementation_event', 'old', supersedes=ref('implementation_event', 'new'),
                    correction_reason='Fixture cycle')
    new = assertion('implementation_event', 'new', supersedes=ref('implementation_event', 'old'),
                    correction_reason='Fixture cycle')
    entity = row('entity', 'project-a', country='VNM')
    with pytest.raises(ContractError, match='cycle'):
        read([entity, old, new])
    del old['supersedes']
    fork = dict(new, record_id='fork')
    records = [entity, old, new, fork]
    records += [decision('accept-' + r['record_id'], ref(r['record_kind'], r['record_id']))
                for r in (old, new, fork)]
    with pytest.raises(ContractError, match='fork'):
        read(records).at(AUGUST, policy_version='fixture-v1')


def test_transitive_replacement_does_not_resurrect_accepted_ancestor():
    records = [row('entity', 'project-a', country='VNM')]
    for identity, previous in [('a', None), ('b', 'a'), ('c', 'b')]:
        extra = {'supersedes': ref('implementation_event', previous),
                 'correction_reason': 'Revision'} if previous else {}
        records.append(assertion('implementation_event', identity, **extra))
        records.append(decision('accept-' + identity, ref('implementation_event', identity),
                                verdict='withdrawn' if identity == 'b' else 'accepted'))
    view = read(records).at(AUGUST, policy_version='fixture-v1')
    assert view.accepted(ref('implementation_event', 'c'))
    assert not view.accepted(ref('implementation_event', 'a'))


def test_decision_cardinality_and_conflicting_occurrence_membership_fail_closed():
    records = [row('entity', 'project-a', country='VNM'), assertion('financial_event', 'payment'),
               decision('accept', ref('financial_event', 'payment')), row('occurrence', 'a'),
               row('occurrence', 'b')]
    for identity in ('a', 'b'):
        records.append(row('adjudication', 'assign-' + identity, decision_type='occurrence_membership',
                           verdict='accepted', reason='Review', reviewer='reviewer', reviewed_at=JULY,
                           policy_version='fixture-v1', members=[
                               {'role': 'accepted', 'target': ref('financial_event', 'payment')},
                               {'role': 'occurrence', 'target': ref('occurrence', identity)}]))
    with pytest.raises(ContractError, match='multiple active occurrence'):
        read(records).at(AUGUST, policy_version='fixture-v1')
    records[-1]['members'] = []
    with pytest.raises(ContractError, match='cardinality'):
        read(records)


def test_frozen_frame_retains_active_and_cancelled_units_despite_later_exclusion():
    records = [row('entity', 'active', country='VNM'), row('entity', 'cancelled', country='VNM'),
               row('study', 'history', name='Historical operation visibility'),
               row('protocol_revision', 'protocol-1', study=ref('study', 'history'),
                   eligibility_rule='Operations present before intervention, including cancelled',
                   frozen_at=JULY, reviewer='researcher'),
               row('frame', 'pre-intervention', protocol=ref('protocol_revision', 'protocol-1'),
                   evidence_cutoff=AUGUST, eligibility_rule='Both operations in original inventory',
                   population_coverage='reconstructed')]
    for identity in ('active', 'cancelled'):
        records.extend([row('frame_member', identity, frame=ref('frame', 'pre-intervention'),
                            unit=ref('entity', identity), verdict='included', reason='Original inventory',
                            baseline_maturity=identity),
                        decision('include-' + identity, ref('frame_member', identity))])
    exclusion = row('frame_member', 'exclude-cancelled', frame=ref('frame', 'pre-intervention'),
                    unit=ref('entity', 'cancelled'), verdict='excluded', reason='Later completed list',
                    baseline_maturity='cancelled', supersedes=ref('frame_member', 'cancelled'),
                    correction_reason='Later selection')
    exclusion['recorded_at'] = '2026-09-01T00:00:00Z'
    records.extend([exclusion, decision('exclude-later', ref('frame_member', 'exclude-cancelled'))])
    view = read(records).at(SEPTEMBER, policy_version='fixture-v1')
    members = view.frozen_frame(ref('frame', 'pre-intervention'))
    assert {m['unit']['record_id'] for m in members} == {'active', 'cancelled'}
    assert {m['verdict'] for m in members} == {'included'}
    invalid = deepcopy(records)
    invalid[4]['population_coverage'] = 'completed_only'
    with pytest.raises(ContractError, match='unreconstructed'):
        read(invalid).at(SEPTEMBER, policy_version='fixture-v1').frozen_frame(ref('frame', 'pre-intervention'))


def test_coverage_attempt_preserves_failure_without_invented_evidence_or_endpoint():
    attempt = row('observation_attempt', 'blocked-check', subject=ref('entity', 'project-a'),
                  sought='Commissioning report', route='Official register', check_date='2026-07-02',
                  result='blocked')
    store = read([row('entity', 'project-a', country='VNM'), attempt])
    assert store.to_dict()['records'][1] == attempt
    assert 'timing' not in attempt and 'document_sha256' not in attempt
    attempt['result'] = 'not_sought'
    with pytest.raises(ContractError, match='not_sought'):
        read([row('entity', 'project-a', country='VNM'), attempt])


def test_unsupported_closing_and_residual_remain_unavailable():
    result = read([]).at(AUGUST, policy_version='fixture-v1').closing_status()
    assert result['reconstructed_closing'] is None
    assert result['residual'] is None
    assert result['missing_reason']


def test_input_and_export_mutation_cannot_rewrite_admitted_history():
    records = [row('entity', 'project-a', country='VNM')]
    store = read(records)
    records[0]['country'] = 'ZAF'
    exported = store.to_dict()
    exported['records'][0]['country'] = 'SEN'
    assert store.to_dict()['records'][0]['country'] == 'VNM'


def test_money_normalization_cannot_disagree_with_original_scale():
    value = assertion('financial_event', 'scaled-wrong', value_type='money', value_text=None,
                      value_decimal='3.92', currency='USD', unit='USD',
                      original_value='3.92', original_scale='billion', coverage_gap='Unknown partners')
    with pytest.raises(ContractError, match='scale'):
        read([row('entity', 'project-a', country='VNM'), value])


def test_exact_coverage_is_an_interval_and_typed_event_roles_remain_separate():
    records = [row('entity', 'project-a', country='VNM'),
               assertion('position', 'q2', basis='period_flow', coverage_start='2026-04-01',
                         coverage_end='2026-06-30', coverage_precision='day'),
               assertion('financial_event', 'same', timing=[dict(date_role='event', event_start='2026-04-01',
                                                               event_end='2026-04-01', event_precision='day')]),
               assertion('implementation_event', 'same', timing=[dict(date_role='observed_state',
                                                                    event_start='2026-06-01', event_end='2026-06-30',
                                                                    event_precision='month')])]
    result = read(records).at(AUGUST, policy_version='fixture-v1').records
    assert result[('financial_event', 'same')]['timing'] != result[('implementation_event', 'same')]['timing']
    assert 'cutoff_earliest' not in result[('position', 'q2')]


def test_count_slot_route_is_retained_but_cannot_be_an_invented_project_subject():
    slot = row('entity', 'project-a', country='VNM', identity_type='legacy_count_slot')
    assert read([slot]).to_dict()['records'] == [slot]
    with pytest.raises(ContractError, match='count slot'):
        read([slot, assertion('implementation_event', 'imagined-project')])


def test_found_document_requires_evidence_but_not_sought_assessment_does_not():
    entity = row('entity', 'project-a', country='VNM')
    assessment = row('coverage_assessment', 'not-searched', subject=ref('entity', 'project-a'),
                     sought='Commissioning report', assessed_at=JULY, result='not_sought',
                     reason='Outside this sweep')
    assert read([entity, assessment]).to_dict()['records'][1] == assessment
    attempt = row('observation_attempt', 'claims-document', subject=ref('entity', 'project-a'),
                  sought='Commissioning report', route='Official site', check_date='2026-07-01', result='found')
    with pytest.raises(ContractError, match='evidence'):
        read([entity, attempt])


def test_dated_classification_changes_without_renaming_subject_or_route():
    unknown = assertion('implementation_event', 'unknown-kind', measure='entity_type', value_text='unknown')
    programme = assertion('implementation_event', 'programme-kind', measure='entity_type', value_text='programme',
                          supersedes=ref('implementation_event', 'unknown-kind'), correction_reason='Inventory clarified')
    accepted = decision('programme-reviewed', ref('implementation_event', 'programme-kind'))
    accepted['reviewed_at'] = '2026-09-03T00:00:00Z'
    store = read([row('entity', 'project-a', country='VNM'), unknown, programme,
                  decision('unknown-reviewed', ref('implementation_event', 'unknown-kind')), accepted])
    early = store.at(AUGUST, policy_version='fixture-v1')
    late = store.at(SEPTEMBER, policy_version='fixture-v1')
    assert early.accepted(ref('implementation_event', 'unknown-kind'))
    assert late.accepted(ref('implementation_event', 'programme-kind'))
    assert early.records[('entity', 'project-a')] == late.records[('entity', 'project-a')]
    assert unknown['subject'] == programme['subject'] == ref('entity', 'project-a')
