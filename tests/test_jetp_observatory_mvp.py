"""Scientific boundary checks for the observable website MVP."""

from jetp._observatory_data import historical_record, public_event, timeline


def test_static_renderer_exposes_current_route_and_derived_disclosure_count():
    """The preview follows coverage supplied by the frozen release handoff."""
    from pathlib import Path

    renderer = (Path(__file__).resolve().parents[1] /
                'deliverables/jetp-observatory/app.js').read_text()
    assert 'aria-current' in renderer
    assert 'overview.countries.reduce((total, c) => total + c.undisclosed, 0)' in renderer
    assert '21 unnamed Viet Nam' not in renderer


def test_register_dates_are_observations_not_verified_signatures():
    event = public_event({
        'event_id': 'e', 'financial_status': 'signed', 'event_date': '2021-01-01',
        'verification_status': 'official_register', 'source_id': 's',
        'amount_original': '10', 'currency_original': 'USD',
    })
    assert event['status'] == 'Registered financing'
    assert event['date'] is None
    assert event['recorded_date'] == '2021-01-01'
    assert event['amount'] == '10'


def test_timeline_uses_event_date_and_does_not_invent_missing_dates():
    rows = [{'date': None, 'status': 'Proposed'},
            {'date': '2025-11-30', 'status': 'Construction'},
            {'date': '2025-08-08', 'status': 'Operational'}]
    assert [r['date'] for r in timeline(rows)] == ['2025-08-08', '2025-11-30', None]


def test_historical_cohort_requires_closed_and_pre_jetp_energy():
    row = {'id': 'P1', 'project_name': 'Power', 'status': 'Closed',
           'boardapprovaldate': '2010-01-01T00:00:00Z',
           'closingdate': '1/1/2015 12:00:00 AM',
           'sector_namecode': [{'name': 'Energy Transmission and Distribution'}],
           'lendinginstr': 'Investment Project Financing'}
    item = historical_record(row, 'IDN', '2022-11-15')
    assert item['years'] > 4.9
    assert item['status'] == 'Closed'
    assert historical_record(dict(row, status='Active'), 'IDN', '2022-11-15') is None
    assert historical_record(dict(row, boardapprovaldate='2023-01-01'), 'IDN', '2022-11-15') is None
    assert historical_record(dict(row, sector_namecode=[]), 'IDN', '2022-11-15') is None
    assert historical_record(dict(row, closingdate=''), 'IDN', '2022-11-15')['years'] is None


def test_unknown_dates_and_report_dates_do_not_become_event_dates():
    event = public_event({'event_date': '2025-11-30', 'financial_status': 'approved',
                          'verification_status': 'official_report'})
    assert event['date'] is None
    assert event['date_role'] == 'unreviewed'
    assert event['observed_date'] is None


def test_duplicate_observations_are_not_new_financing():
    import pytest
    from jetp.build_observatory import unique_rows

    row = {'event_id': 'e', 'amount_original': '10'}
    assert unique_rows([row, row.copy()], 'event_id') == [row]
    with pytest.raises(ValueError, match='Conflicting'):
        unique_rows([row, dict(row, amount_original='20')], 'event_id')


def test_disclosure_slots_are_not_published_as_project_identities():
    from jetp.build_observatory import country_data

    named = {'project_id': 'named', 'country': 'VNM', 'canonical_name': 'A programme',
             'verification_status': 'official_report'}
    slot = dict(named, project_id='slot', verification_status='official_count_slot')
    tables = {key: [] for key in ('events', 'implementation-events', 'source-claims',
                                 'project-source-links', 'project-coverage', 'sources', 'manifest')}
    tables['projects'] = [named, slot]
    config = {'countries': {'VNM': {'headline_source': ''}}}
    from pathlib import Path

    result = country_data(Path('/nonexistent'), 'VNM', config, tables)
    assert result['undisclosed'] == 1
    assert [p['id'] for p in result['projects']] == ['named']
    assert result['projects'][0]['finance_stage'] == 'Not documented'
    assert result['projects'][0]['events'] == []


def test_snapshot_rejects_incomplete_pagination(tmp_path):
    import json

    import pytest
    from jetp.build_wb_snapshot import freeze

    page = tmp_path / 'page.json'
    page.write_text(json.dumps({'total': '2', 'projects': {'P1': {'id': 'P1'}}}))
    with pytest.raises(ValueError, match='Incomplete API pagination'):
        freeze([page], 'ID', '2026-09-13')


def actual_project(pid):
    from jetp.build_observatory import ROOT, project_data, read_inputs
    tables = read_inputs(ROOT)
    row = next(r for r in tables['projects'] if r['project_id'] == pid)
    return project_data(row, tables)


def actual_events():
    from jetp.build_observatory import ROOT, project_data, read_inputs
    tables = read_inputs(ROOT)
    return {e['id']: e for p in tables['projects'] for e in project_data(p, tables)['events']}


def test_real_portal_and_aner_snapshots_have_no_event_date():
    events = actual_events()
    for eid in ('idn-portal-gecs-kfw-2026', 'idn-portal-nagajaya-norfund-2026',
                'idn-portal-hululais-jica-2026',
                'sen-project-annex-20-proposed-2026-09-13',
                'sen-project-annex-22-proposed-2026-09-13',
                'sen-project-annex-27-proposed-2026-09-13',
                'sen-project-annex-31-proposed-2026-09-13'):
        event = events[eid]
        assert event['date'] is None, eid
        assert event['date_role'] == 'observation'
        assert event['event_precision'] == 'unknown'
        assert event['observed_date'] in ('2026-09-12', '2026-09-13')
        assert event['collected_on']


def test_real_reports_and_groundbreaking_keep_different_date_roles():
    events = actual_events()
    puelec = events['sen-puelec-three-villages-reported-20251109']
    assert puelec['date'] is None
    assert puelec['reported_on'] == '2025-11-09'
    assert puelec['event_precision'] == 'unknown'
    assert puelec['date_role'] == 'publication'
    launch = events['sen-diass-groundbreaking-20260331']
    assert launch['date'] == '2026-03-31'
    assert launch['reported_on'] == '2026-04-20'
    report = events['sen-diass-kfw-reported-20260420']
    assert report['date'] is None
    assert report['reported_on'] == '2026-04-20'
    assert report['date_role'] == 'publication'
    # A programme start month is not a dated financial approval.
    assert events['zaf-eepbip-maf-approved-2018']['date'] is None


def test_explicit_interval_is_not_collapsed_to_a_day():
    event = public_event({'event_id': 'e', 'event_date': '2025-11-30'},
                         {'date_role': 'reporting_cutoff', 'event_precision': 'year',
                          'event_start': '2022-01-01', 'event_end': '2022-12-31',
                          'observed_on': '2025-11-30'})
    assert event['date'] is None
    assert event['event_start'] == '2022-01-01'
    assert event['event_end'] == '2022-12-31'
    assert event['event_precision'] == 'year'


def test_real_provisional_source_link_and_claim_verdict_survive_export():
    project = actual_project('sen-project-qw-02')
    link = next(r for r in project['source_links'] if r['link_id'] == 'round4-boad-linguere')
    assert link['relationship'] == 'possible_match'
    assert link['review_status'] == 'provisional'
    assert link['locator']
    assert 'JETP' in link['notes']
    from jetp.build_observatory import ROOT, read_inputs
    tables = read_inputs(ROOT)
    claims = actual_project('zaf-register-gr039')['claims']
    assert any(r['claim_id'] == 'zaf-annex25-dpo3' for r in claims)
    for claim in claims:
        raw = next(r for r in tables['source-claims'] if r['claim_id'] == claim['claim_id'])
        assert claim['match_status'] == raw['match_status']


def test_historical_acquisition_dates_do_not_follow_edition_cutoff():
    import json

    import yaml
    from jetp.build_observatory import ROOT, comparison_data
    config = yaml.safe_load((ROOT / 'config/jetp_observatory.yaml').read_text())
    config['cutoff'] = '2027-03-31'
    result = comparison_data(ROOT, config)
    assert 'retrieved_on' not in result  # country snapshots can have different dates
    for code, country in config['countries'].items():
        raw = json.loads((ROOT / 'data/jetp/comparison' / f"{country['iso2']}.json").read_text())
        snapshot = result['snapshots'][code]
        assert snapshot['retrieved_on'] == raw['retrieved_on']
        assert snapshot['pages'] == raw['pages']
        assert snapshot['source_updated_on'] is None


def test_current_timing_registry_covers_each_observation_and_is_independent_of_authority():
    from jetp.build_observatory import ROOT, read_inputs
    tables = read_inputs(ROOT)
    ids = {r['event_id'] for r in tables['events']} | {
        r['implementation_event_id'] for r in tables['implementation-events']}
    assert {r['event_id'] for r in tables['event-timing']} == ids
    day = {'date_role': 'event', 'event_precision': 'day',
           'event_start': '2025-08-08', 'event_end': '2025-08-08'}
    for authority in ('official_report', 'primary_source', 'official_portal_snapshot'):
        assert public_event({'verification_status': authority}, day)['date'] == '2025-08-08'
    assert public_event({'verification_status': 'primary_source',
                         'event_date': '2026-01-01'})['date'] is None


def test_invalid_timing_cannot_silently_become_an_event():
    import pytest
    for timing in ({'date_role': 'typo'}, {'event_precision': 'typo'},
                   {'event_precision': 'unknown', 'event_start': '2025-01-01'},
                   {'date_role': 'publication', 'event_precision': 'day',
                    'event_start': '2025-01-01', 'event_end': '2025-01-01'},
                   {'date_role': 'event', 'event_precision': 'day',
                    'event_start': '2025-01-01', 'event_end': '2025-01-02'},
                   {'event_precision': 'interval', 'event_start': '2025-02-01',
                    'event_end': '2025-01-01'}):
        with pytest.raises(ValueError):
            public_event({}, timing)


def test_static_renderer_exposes_release_history_and_monthly_change_route():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    renderer = (root / 'deliverables/jetp-observatory/app.js').read_text()
    assert 'editionHistoryPage' in renderer
    assert 'data/editions.json' in renderer
    assert 'catch(() => ({ editions: [] }))' in renderer
    assert '#editions' in (root / 'deliverables/jetp-observatory/index.html').read_text()


def test_static_renderer_has_a_non_aggregate_reviewed_evidence_route():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    renderer = (root / 'deliverables/jetp-observatory/app.js').read_text()
    assert 'function evidencePage()' in renderer
    assert 'data-reviewed-evidence-id' in renderer
    assert 'Non-aggregate record.' in renderer
    assert 'comparative staging snapshot is derived research material' in renderer
    assert '#evidence' in (root / 'deliverables/jetp-observatory/index.html').read_text()


def test_edition_history_distinguishes_canonical_sources_and_staged_depth():
    """The MVP must make recent extraction visible without promoting it."""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    renderer = (root / 'deliverables/jetp-observatory/app.js').read_text()
    evidence = json.loads((root / 'deliverables/jetp-observatory/data/reviewed-evidence.json').read_text())

    assert 'evidenceDepthSummary' in renderer
    assert evidence['evidence_depth'] == {
        'canonical_named_records': 383,
        'frozen_source_documents': 301,
        'structured_atomic_observations': {
            'total': 1740,
            'by_country': {'ZAF': 257, 'IDN': 1148, 'VNM': 325, 'SEN': 10},
            'vnm_rmp_positions': 279,
            'status': 'not_deployed',
        },
    }
    assert 'not deployed as canonical facts' in renderer
    assert 'not a common record total' in renderer
