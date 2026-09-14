"""Frozen watch attempts must never promote content or erase evidence."""

from copy import deepcopy

from jetp._source_watch import freeze_sweep, record_check, summarize


def watch(source):
    return {'watch_id': source, 'watch_revision_id': 'watch-' + source,
            'source_id': source, 'source_revision_id': 'revision-' + source,
            'recorded_at': '2026-09-01T00:00:00Z', 'review_state': 'reviewed',
            'review_reference': 'fixture-policy-review', 'owner': 'fixture',
            'purpose': 'fixture refresh', 'active': True, 'priority': 1,
            'expected_publication_cadence': 'unknown', 'check_interval_days': 30,
            'retry_days': 2, 'max_retry_days': 8, 'method': 'fixture',
            'route': 'https://example.test/' + source, 'access_limitations': [],
            'scope': {'countries': ['VNM'], 'sectors': [], 'languages': [], 'topics': []},
            'acceptance_criteria': 'named source only', 'budget': {'calls': 1, 'seconds': 10}}


def fixture():
    sources = [{'source_id': name, 'source_revision_id': 'revision-' + name,
                'recorded_at': '2026-09-01T00:00:00Z', 'source_kind': 'document',
                'triage_state': 'accepted_for_use', 'metadata': {'publisher': 'Original'}}
               for name in ('unchanged', 'revised', 'blocked', 'deferred')]
    return freeze_sweep(sources, [watch(row['source_id']) for row in sources],
                        sweep_id='fixture-sweep', created_at='2026-09-14T00:00:00Z',
                        owner='fixture', purpose='bounded fixture',
                        registry_revision='fixture-registry', configuration_revision='fixture-policy',
                        budget={'calls': 4, 'seconds': 40},
                        deferrals={'deferred': 'budget explicitly reserved for next sweep'})


def check(name, outcome, attempt='1'):
    return {'check_id': name + '-' + attempt, 'watch_revision_id': 'watch-' + name,
            'started_at': '2026-09-14T01:00:00Z', 'ended_at': '2026-09-14T01:01:00Z',
            'recorded_at': '2026-09-14T01:01:00Z', 'method': 'fixture',
            'route': 'https://example.test/' + name, 'outcome': outcome,
            'coverage_complete': outcome in {'checked_no_change', 'changed'},
            'coverage_limit': 'only pinned route', 'error': '403' if outcome == 'blocked' else '',
            'retry_reason': 'access blocked' if outcome == 'blocked' else ''}


def test_frozen_unchanged_revised_blocked_deferred_preserves_coverage_and_evidence():
    plan = fixture()
    original = deepcopy(plan)
    checks = []
    for name, outcome in [('unchanged', 'checked_no_change'), ('revised', 'changed'),
                          ('blocked', 'blocked')]:
        checks = record_check(plan, checks, check(name, outcome))
    report = summarize(plan, checks)
    assert plan == original
    assert len(report['targets']) == 4
    assert report['complete'] is True
    rows = {row['watch_id']: row for row in report['targets']}
    assert rows['unchanged']['last_successful_check_at'] == '2026-09-14T01:01:00Z'
    assert rows['revised']['last_changed_at'] == '2026-09-14T01:01:00Z'
    assert rows['blocked']['last_successful_check_at'] is None
    assert rows['deferred']['status'] == 'deferred'
    assert report['publication_action'] == 'none'
    assert report['evidence_action'] == 'preserve'


import pytest
from jetp._contracts import ContractError
from jetp._source_watch import (
    change_report,
    link_acquisition,
    record_discovery,
    registry_at,
    source_revision,
)


def test_missing_and_repeated_attempts_keep_success_and_retry():
    plan = fixture()
    assert summarize(plan, [])['complete'] is False
    first = check('unchanged', 'checked_no_change')
    checks = record_check(plan, [], first)
    assert record_check(plan, checks, first) == checks
    failed = check('unchanged', 'blocked', '2')
    failed.update(started_at='2026-09-15T00:00:00Z', ended_at='2026-09-15T00:01:00Z',
                  recorded_at='2026-09-15T00:01:00Z')
    checks = record_check(plan, checks, failed)
    row = summarize(plan, checks)['targets'][0]
    assert row['last_successful_check_at'] == first['ended_at']
    assert row['failure_streak'] == 1
    assert row['next_check_at'] == '2026-09-17T00:01:00Z'
    assert len(checks) == 2
    with pytest.raises(ContractError, match='collision'):
        record_check(plan, checks, {**first, 'coverage_limit': 'different scope'})
    cutoff = summarize(plan, checks, cutoff='2026-09-14T02:00:00Z')
    assert cutoff['targets'][0]['last_attempt_at'] == first['started_at']


def test_metadata_snapshots_and_cutoff_are_immutable():
    old = source_revision({'source_id': 'one', 'publisher': 'Original'}, '2026-09-01T00:00:00Z')
    new = source_revision({'source_id': 'one', 'publisher': 'Corrected'}, '2026-09-15T00:00:00Z',
                          supersedes=old['source_revision_id'])
    assert registry_at([old, new], '2026-09-14T00:00:00Z') == [old]
    assert registry_at([old, new], '2026-09-16T00:00:00Z') == [new]
    plan = fixture()
    changed = deepcopy(plan)
    changed['targets'][0]['source']['metadata']['publisher'] = 'rewritten'
    with pytest.raises(ContractError, match='modified'):
        summarize(changed, [])


def test_discovery_identity_has_multiple_links_and_validated_acquisitions():
    plan = fixture()
    checks = record_check(plan, [], check('unchanged', 'checked_no_change'))
    checks = record_check(plan, checks, check('revised', 'changed'))
    source = {'source_id': 'same-document', 'source_revision_id': 'same-revision', 'source_kind': 'document'}
    discoveries = []
    for index, item in enumerate(checks):
        row = {'discovery_id': str(index), 'check_id': item['check_id'], **source,
               'locator': 'link 3', 'recorded_at': item['ended_at']}
        discoveries = record_discovery(plan, checks, discoveries, row, [source])
    assert len(discoveries) == 2
    assert len({row['source_id'] for row in discoveries}) == 1
    acquisition = {'acquisition_id': 'attempt', 'source_id': 'same-document',
                   'source_revision_id': 'same-revision', 'check_id': checks[0]['check_id'],
                   'check_role': 'discovered_document', 'document_sha256': 'a' * 64,
                   'retrieved_at': checks[0]['started_at'], 'outcome': 'collected',
                   'requested_url': 'https://example.test/document', 'final_url': 'https://example.test/document'}
    linked = link_acquisition(plan, checks, discoveries, [], acquisition, [source])
    assert link_acquisition(plan, checks, discoveries, linked, acquisition, [source]) == linked
    with pytest.raises(ContractError, match='discovery link'):
        link_acquisition(plan, checks, [], [], acquisition, [source])
    with pytest.raises(ContractError, match='differs from watch'):
        link_acquisition(plan, checks, discoveries, [], {**acquisition, 'check_role': 'target'}, [source])


def test_late_correction_and_editorial_queue_retains_claims_and_unknown_origin():
    plan = fixture()
    checks = record_check(plan, [], check('revised', 'changed'))
    claims = [{'claim_id': 'principal-claim', 'source_id': 'revised', 'text': 'old report',
               'principal_report': 'principal edition', 'publication_date': '2025-06-01'}]
    changes = [{'check_id': checks[0]['check_id'], 'source_id': 'revised', 'kind': kind,
                'publication_date': '2025-05-01', 'recorded_at': '2026-09-14T01:01:00Z'}
               for kind in ('late_report', 'correction', 'editorial_impact')]
    original = deepcopy(claims)
    report = change_report(plan, checks, [], claims, changes)
    assert len(report['queue']) == 3
    assert claims == original
    assert all(row['affected_claims'] == original and not row['factual_promotion'] for row in report['queue'])
    assert report['queue'][0]['origin_assessments'][0]['intelligence_role'] == 'unknown'
    assert report['handoff_ticket'] == '0728'
    assert report['publication_action'] == 'none'


@pytest.mark.integration
def test_frozen_http_harvester_unchanged_revised_blocked_and_catalog_mutation(tmp_path, monkeypatch):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    import requests
    from jetp._source_watch import run_document_check

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/blocked':
                self.send_response(403)
                self.end_headers()
                return
            if self.path == '/unchanged' and self.headers.get('If-None-Match'):
                self.send_response(304)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('ETag', 'fixture-etag')
            self.end_headers()
            self.wfile.write(b'%PDF-1.4\nChanged or initial report')

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        plan = fixture()
        sources, watches = [], []
        for target in plan['targets']:
            source, policy = deepcopy(target['source']), deepcopy(target['watch'])
            policy['method'] = 'http_get'
            policy['route'] = f'http://127.0.0.1:{server.server_port}/' + policy['source_id']
            source['metadata'].update(source_id=source['source_id'], country='VNM',
                                      expected_format='pdf', url=policy['route'])
            sources.append(source)
            watches.append(policy)
        plan = freeze_sweep(sources, watches, sweep_id='http', created_at='2026-09-14T00:00:00Z',
                            owner='fixture', purpose='live adapter fixture', registry_revision='registry',
                            configuration_revision='policy', budget={'calls': 4, 'seconds': 40},
                            deferrals={'deferred': 'budget'})
        sources[0]['metadata']['url'] = 'https://must-not-be-requested.invalid/'
        checks, acquisitions = [], []
        with requests.Session() as session:
            for name in ('unchanged', 'revised', 'blocked'):
                previous = None
                if name == 'unchanged':
                    _, initial = run_document_check(plan, 'watch-' + name, check_id='initial',
                        storage_root=tmp_path, session=session, clock=lambda: '2026-09-14T01:00:00Z')
                    previous = initial['manifest_row']
                item, material = run_document_check(plan, 'watch-' + name, check_id=name,
                    storage_root=tmp_path, previous=previous, session=session,
                    clock=lambda: '2026-09-14T01:01:00Z')
                checks = record_check(plan, checks, item)
                acquisitions = link_acquisition(plan, checks, [], acquisitions, material,
                                               [target['source'] for target in plan['targets']])
        assert [row['outcome'] for row in checks] == ['checked_no_change', 'changed', 'blocked']
        assert [row['outcome'] for row in acquisitions] == ['not_modified', 'collected', 'blocked']
        assert acquisitions[0]['requested_url'].endswith('/unchanged')
        assert acquisitions[2]['document_sha256'] is None
        assert summarize(plan, checks)['complete']
        report = change_report(plan, checks, [], [{'claim_id': 'claim', 'source_id': 'revised'}],
                               [{'check_id': 'revised', 'source_id': 'revised', 'kind': 'byte_change'}])
        assert report['queue'][0]['affected_claims'][0]['claim_id'] == 'claim'
        assert report['publication_action'] == 'none'
        import json

        from jetp import build_source_sweep as builder

        real_check = builder.run_document_check

        def interrupted(plan, revision, **kwargs):
            if revision == 'watch-revised':
                raise RuntimeError('interrupted between targets')
            return real_check(plan, revision, **kwargs)

        monkeypatch.setattr(builder, 'run_document_check', interrupted)
        output = tmp_path / 'durable.json'
        with pytest.raises(RuntimeError, match='between targets'):
            builder.execute_sweep(tmp_path / 'checkout', output, candidate=candidate(plan),
                attempt_id='durable-run', storage_root=tmp_path / 'candidate-objects',
                clock=lambda: '2026-09-14T02:00:00Z')
        partial = json.loads(output.read_text())
        assert len(partial['checks']) == 1
        assert not partial['summary']['complete']
        monkeypatch.setattr(builder, 'run_document_check', real_check)
        complete = builder.execute_sweep(tmp_path / 'checkout', output, candidate=candidate(plan),
            attempt_id='durable-run', storage_root=tmp_path / 'candidate-objects',
            clock=lambda: '2026-09-14T02:00:00Z')
        assert complete['summary']['complete']
        assert len(complete['acquisitions']) == 3
        assert builder.execute_sweep(tmp_path / 'checkout', output, candidate=candidate(plan),
            attempt_id='durable-run', storage_root=tmp_path / 'candidate-objects') == complete
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def candidate(plan=None):
    from jetp._source_watch import SCHEMA_VERSION

    plan = plan or fixture()
    return {'schema_version': SCHEMA_VERSION, 'admission_status': 'unadmitted_candidate',
            'publication_action': 'none', 'handoff_ticket': '0728', 'inputs': {'fixture': {'sha256': 'a' * 64}},
            'plan': plan, 'checks': [], 'discoveries': [], 'acquisitions': [],
            'summary': summarize(plan, []), 'archive_verifications': [], 'claim_review_queue': [],
            'changes': [], 'change_report': change_report(plan, [], [], [], []),
            'source_revisions': [target['source'] for target in plan['targets']]}


@pytest.mark.parametrize('alias', ['direct', 'symlink', 'hardlink'])
@pytest.mark.parametrize('malformed', [True, False])
def test_writer_rejects_aliases_and_malformed_before_build(tmp_path, monkeypatch, alias, malformed):
    import json
    import os

    from jetp import build_source_sweep as builder

    payload = candidate()
    if malformed:
        payload['plan']['targets'][0]['source'] = {}
    target = tmp_path / 'protected.json'
    target.write_text(json.dumps(payload))
    output = tmp_path / 'output.json'
    if alias == 'symlink':
        output.symlink_to(target)
    elif alias == 'hardlink':
        os.link(target, output)
    else:
        output = target
    before = target.read_bytes()
    calls = []
    monkeypatch.setattr(builder, 'build_sweep', lambda *_args: calls.append(True) or candidate())
    if alias == 'direct' and not malformed:
        builder.write_sweep(tmp_path, output, policy_path=tmp_path / 'policy.yaml')
        assert calls == [True]
    else:
        with pytest.raises(ValueError):
            builder.write_sweep(tmp_path, output, policy_path=tmp_path / 'policy.yaml')
        assert calls == []
        assert target.read_bytes() == before


def test_safe_parent_alias_rerun_and_failing_builder_preserves_candidate(tmp_path, monkeypatch):
    from jetp import build_source_sweep as builder

    parent = tmp_path / 'candidates'
    parent.mkdir()
    alias = tmp_path / 'alias'
    alias.symlink_to(parent, target_is_directory=True)
    output = alias / 'sweep.json'
    monkeypatch.setattr(builder, 'build_sweep', lambda *_args: candidate())
    builder.write_sweep(tmp_path, output, policy_path=tmp_path / 'policy.yaml')
    before = output.read_bytes()
    builder.write_sweep(tmp_path, output, policy_path=tmp_path / 'policy.yaml')
    assert output.read_bytes() == before

    def failed(*_args):
        raise RuntimeError('interrupted before replacement')

    monkeypatch.setattr(builder, 'build_sweep', failed)
    with pytest.raises(RuntimeError):
        builder.write_sweep(tmp_path, output, policy_path=tmp_path / 'policy.yaml')
    assert output.read_bytes() == before


def test_previous_sweep_success_survives_new_failure_and_future_cutoff():
    prior = fixture()
    prior_checks = record_check(prior, [], check('unchanged', 'checked_no_change'))
    current = freeze_sweep([target['source'] for target in prior['targets']],
                          [target['watch'] for target in prior['targets']], sweep_id='next',
                          created_at='2026-09-15T00:00:00Z', owner='fixture', purpose='retry',
                          registry_revision='r', configuration_revision='p', budget={'calls': 4, 'seconds': 40},
                          deferrals={'deferred': 'budget'}, previous_sweeps=[{'plan': prior, 'checks': prior_checks}])
    assert current['targets'][0]['initial_due_at'] == '2026-10-14T01:01:00Z'
    assert summarize(current, [])['targets'][0]['status'] == 'missing'
    failure = check('unchanged', 'blocked', 'next')
    failure.update(started_at='2026-09-15T01:00:00Z', ended_at='2026-09-15T01:01:00Z',
                   recorded_at='2026-09-15T01:01:00Z')
    row = summarize(current, record_check(current, [], failure))['targets'][0]
    assert row['last_successful_check_at'] == prior_checks[0]['ended_at']
    assert row['failure_streak'] == 1


def test_pending_policy_and_archived_checks_cannot_claim_publisher_coverage():
    plan = fixture()
    archive = {**check('unchanged', 'checked_no_change'), 'check_scope': 'archived_material'}
    row = summarize(plan, record_check(plan, [], archive))['targets'][0]
    assert row['last_successful_check_at'] is None
    assert row['status'] == 'partial_or_failed'
    proposed = watch('unchanged')
    proposed['review_state'] = 'pending_review'
    from jetp._source_watch import validate_watch
    with pytest.raises(ContractError, match='reviewed'):
        validate_watch(proposed)


def test_unacquired_origin_stays_citation_and_invalid_dependency_is_rejected():
    from jetp._source_watch import assess_origin

    result = assess_origin({'evidence_id': 'claim'}, intelligence_role='secondary',
                           rationale='report attributes lender total', upstream_status='cited_not_acquired',
                           citation='Lender report, page unknown')
    assert result['dependency_ids'] == []
    assert result['review_state'] == 'pending_review'
    with pytest.raises(ContractError, match='acquired evidence'):
        assess_origin({'evidence_id': 'claim'}, upstream_status='linked')


def test_origin_revision_cutoff_keeps_previous_unknown_assessment():
    from jetp._source_watch import assess_origin, origins_at, record_origin

    unknown = assess_origin({'evidence_id': 'evidence'})
    rows = record_origin([], unknown, recorded_at='2026-09-01T00:00:00Z')
    old = deepcopy(rows)
    new = assess_origin({'evidence_id': 'evidence'}, intelligence_role='secondary',
                        rationale='explicit lender citation', upstream_status='cited_not_acquired',
                        citation='Lender series, not acquired')
    rows = record_origin(rows, new, recorded_at='2026-09-15T00:00:00Z',
                         supersedes=rows[0]['origin_revision_id'])
    assert origins_at(rows, '2026-09-14T00:00:00Z') == old
    assert origins_at(rows, '2026-09-16T00:00:00Z')[0]['intelligence_role'] == 'secondary'


@pytest.mark.slow
def test_actual_registry_handoff_keeps_all_claims_and_offline_scope():
    from pathlib import Path

    from jetp.build_source_sweep import build_sweep

    root = Path(__file__).resolve().parents[1]
    result = build_sweep(root, root / 'config/jetp-source-watches.yaml')
    assert len(result['plan']['targets']) == 4
    assert all(row['status'] == 'deferred' and row['last_successful_check_at'] is None
               for row in result['summary']['targets'])
    assert result['checks'] == []
    assert result['archive_verifications']
    assert all(not row['publisher_coverage_advanced'] for row in result['archive_verifications'])
    assert {row['source_id'] for row in result['archive_verifications'] if row['byte_status'] == 'available'} == {
        'vnm-rmp-2023', 'zaf-jet-quarterly-2026-q1', 'idn-jetp-progress-report-2025'}
    assert all(row['byte_reason'] == 'failed_acquisition' and row['document_sha256'] is None
               for row in result['archive_verifications'] if row['source_id'] == 'sen-investment-plan-l4')
    assert len(result['claim_review_queue']) == result['inputs']['data/jetp/source-claims.csv']['row_count']
    assert {row['date_relation'] for row in result['claim_review_queue']} >= {'after_principal', 'before_principal'}
    assert all(row['origin_assessment']['intelligence_role'] == 'unknown' for row in result['claim_review_queue'])


@pytest.mark.parametrize('alias', ['direct', 'symlink', 'hardlink'])
def test_ids_only_snapshot_lookalike_rejected_before_builder(tmp_path, monkeypatch, alias):
    import json
    import os

    from jetp import build_source_sweep as builder
    from jetp._source_crosswalk import _identity

    payload = candidate()
    original = payload['plan']['targets'][0]['source']
    malformed = {key: original[key] for key in ('source_id', 'source_revision_id')}
    payload['plan']['targets'][0]['source'] = malformed
    payload['source_revisions'][0] = malformed
    body = {key: value for key, value in payload['plan'].items() if key != 'plan_digest'}
    payload['plan']['plan_digest'] = _identity('plan', body)
    protected = tmp_path / 'source-snapshot.json'
    protected.write_text(json.dumps(payload))
    output = tmp_path / 'output.json'
    if alias == 'symlink':
        output.symlink_to(protected)
    elif alias == 'hardlink':
        os.link(protected, output)
    else:
        output = protected
    before = protected.read_bytes()
    calls = []
    monkeypatch.setattr(builder, 'build_sweep', lambda *_args: calls.append(True) or candidate())
    with pytest.raises(ValueError):
        builder.write_sweep(tmp_path, output, policy_path=tmp_path / 'policy.yaml')
    assert not calls
    assert protected.read_bytes() == before
