"""Monthly JETP edition reports preserve releases and distinguish change meanings."""


def test_monthly_report_classifies_fixture_without_erasing_failed_source_or_old_release():
    from jetp._monthly_editions import compare_editions

    previous = {
        'edition': '2026-09', 'cutoff': '2026-09-13',
        'records': [
            {'id': 'unchanged', 'source_id': 'stable', 'event_date': '2026-09-01', 'amount': '10'},
            {'id': 'revised', 'source_id': 'revised-old', 'event_date': '2026-08-01', 'amount': '20'},
            {'id': 'retracted', 'source_id': 'withdrawn', 'event_date': '2026-07-01', 'claim': 'still planned'},
        ],
        'sources': [{'source_id': 'stable', 'status': 'found'},
                    {'source_id': 'blocked', 'status': 'blocked'}],
    }
    current = {
        'edition': '2026-10', 'cutoff': '2026-10-13',
        'records': [
            {'id': 'unchanged', 'source_id': 'stable', 'event_date': '2026-09-01', 'amount': '10'},
            {'id': 'revised', 'source_id': 'revised-new', 'event_date': '2026-08-01', 'amount': '25'},
            {'id': 'late', 'source_id': 'late-report', 'event_date': '2026-06-01', 'amount': '3'},
            {'id': 'retracted', 'source_id': 'withdrawn', 'event_date': '2026-07-01',
             'claim': 'still planned', 'status': 'retracted'},
        ],
        'sources': [{'source_id': 'stable', 'status': 'found'},
                    {'source_id': 'blocked', 'status': 'blocked'},
                    {'source_id': 'late-report', 'status': 'found'}],
    }

    report = compare_editions(previous, current)

    assert report['previous_edition'] == '2026-09'
    assert report['edition'] == '2026-10'
    assert report['unchanged'] == ['unchanged']
    assert report['corrections'] == [{'id': 'revised', 'changed_fields': ['amount', 'source_id']}]
    assert report['late_reports'] == ['late']
    assert report['retractions'] == ['retracted']
    assert report['failed_refreshes'] == [{'source_id': 'blocked', 'status': 'blocked'}]
    assert report['preserved_previous_record_ids'] == ['unchanged', 'revised', 'retracted']


def test_monthly_report_rejects_reused_or_out_of_order_editions():
    import pytest
    from jetp._monthly_editions import compare_editions

    edition = {'edition': '2026-09', 'cutoff': '2026-09-13', 'records': [], 'sources': []}
    with pytest.raises(ValueError, match='later'):
        compare_editions(edition, edition)


def test_release_history_lists_frozen_editions_for_static_site(tmp_path):
    import json

    from jetp._monthly_editions import release_history

    releases = tmp_path / 'releases'
    for edition, cutoff, state in [('2026-09', '2026-09-13', 'prepared'),
                                   ('2026-10', '2026-10-13', 'published')]:
        target = releases / edition
        target.mkdir(parents=True)
        (target / 'release.json').write_text(json.dumps({
            'edition': edition, 'observation_cutoff': cutoff,
            'release_state': state, 'release_prepared_date': cutoff,
            'publication_date': cutoff if state == 'published' else None,
        }))

    assert release_history(releases)['editions'] == [
        {'edition': '2026-10', 'observation_cutoff': '2026-10-13',
         'release_state': 'published', 'release_prepared_date': '2026-10-13',
         'publication_date': '2026-10-13'},
        {'edition': '2026-09', 'observation_cutoff': '2026-09-13',
         'release_state': 'prepared', 'release_prepared_date': '2026-09-13',
         'publication_date': None},
    ]


def test_monthly_report_rejects_candidate_that_drops_prior_record():
    import pytest

    from jetp._monthly_editions import compare_editions

    previous = {'edition': '2026-09', 'cutoff': '2026-09-13',
                'records': [{'id': 'retained', 'event_date': '2026-09-01'}], 'sources': []}
    current = {'edition': '2026-10', 'cutoff': '2026-10-13', 'records': [], 'sources': []}

    with pytest.raises(ValueError, match='omits prior record IDs: retained'):
        compare_editions(previous, current)
