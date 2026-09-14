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
