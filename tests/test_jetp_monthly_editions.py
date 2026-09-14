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
