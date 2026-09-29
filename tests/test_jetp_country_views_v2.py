"""The observatory's country projection respects v2 referent kinds."""

from pathlib import Path

import pytest
import yaml
from jetp._country_views_v2 import country_view, load_country_inputs

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.wp_jetp


def test_current_country_views_keep_agreements_out_of_project_counts():
    ledger = ROOT / 'data/jetp'
    config = yaml.safe_load((ROOT / 'config/jetp_observatory.yaml').read_text())
    tables = load_country_inputs(ledger)
    views = {code: country_view(ledger, code, country, tables=tables)
             for code, country in config['countries'].items()}

    assert {code: view['project_count'] for code, view in views.items()} == {
        'ZAF': 5, 'IDN': 13, 'VNM': 1, 'SEN': 45}
    assert {code: view['agreement_count'] for code, view in views.items()} == {
        'ZAF': 258, 'IDN': 57, 'VNM': 0, 'SEN': 0}
    assert sum(len(view['statements']) for view in views.values()) == 340
    for view in views.values():
        project_ids = {row['id'] for row in view['projects']}
        agreement_ids = {row['id'] for row in view['agreements']}
        assert not project_ids & agreement_ids
        for project in view['projects']:
            for cited in project['evidence']:
                assert cited['line_id'] and cited['locator']
                assert cited['source_id'] in project['sources']
        for statement in view['statements']:
            assert statement['line_id'] and statement['sha256']
            assert statement['source_id'] in view['sources']
            assert statement['subject_id'] in (project_ids | agreement_ids | {
                row['asset_id'] for row in tables['assets']})


def test_south_africa_country_view_stays_within_publication_ceiling():
    path = ROOT / 'deliverables/jetp-observatory/data/ZAF.json'
    assert path.stat().st_size < 512_000


@pytest.fixture(scope='module')
def views():
    ledger = ROOT / 'data/jetp'
    config = yaml.safe_load((ROOT / 'config/jetp_observatory.yaml').read_text())
    tables = load_country_inputs(ledger)
    return tables, {code: country_view(ledger, code, country, tables=tables)
                    for code, country in config['countries'].items()}


def test_a_project_view_carries_no_field_the_ledger_cannot_fill(views):
    # Ticket 1610: the 0878 retirement left `claims` and `source_links`
    # hard-coded empty. A field nothing in the ledger fills is not served;
    # the identity citations they once held are the `evidence` rows.
    _, by_code = views
    for view in by_code.values():
        for project in view['projects']:
            assert 'claims' not in project and 'source_links' not in project


def test_project_funders_are_the_funders_of_its_component_agreements(views):
    # A project has no party_in row of its own: its funders are derived from
    # the agreements recorded as its components, never typed. A project
    # without a component agreement has none.
    tables, by_code = views
    components = {}
    for row in tables['relations']:
        if row['status'] == 'accepted' and row['relation'] == 'component_of' \
                and row['from_kind'] == 'agreement' and row['to_kind'] == 'project':
            components.setdefault(row['to_id'], set()).add(row['from_id'])
    with_funders = 0
    for view in by_code.values():
        agreements = {row['id']: row for row in view['agreements']}
        for project in view['projects']:
            expected = sorted({name for agreement in components.get(project['id'], ())
                               for name in agreements[agreement]['funders']})
            assert project['funders'] == expected, project['id']
            with_funders += bool(expected)
    assert with_funders, 'the positive control: no project derives a funder'


def test_a_channel_party_is_not_a_funder(views):
    # Author's decision, 2026-09-29: a party_in row with role `channel` names
    # the channel an agreement's money passes through, not a funder. Neither
    # an agreement, nor the project it is a component of, nor a statement
    # about either lists it under funders.
    tables, by_code = views
    preferred = {row['party_id']: row['name'] for row in tables['party_names']
                 if row['form_type'] == 'preferred' and row['status'] == 'accepted'}
    channels = {(row['to_id'], preferred.get(row['from_id'], row['from_id']))
                for row in tables['relations']
                if row['relation'] == 'party_in' and row['role'] == 'channel'
                and row['status'] == 'accepted'}
    assert channels, 'the positive control: the ledger names no channel party'
    for view in by_code.values():
        for agreement in view['agreements']:
            assert not [name for name in agreement['funders']
                        if (agreement['id'], name) in channels], agreement['id']
        for statement in view['statements']:
            assert not [name for _, name in channels
                        if name in statement['funder'].split('; ')
                        and (statement['subject_id'], name) in channels], statement['id']
        for project in view['projects']:
            assert 'GIZ' not in project['funders'] or project['id'] != 'project-page-zaf-project-cpd4e-germany'


def test_funders_keep_the_funder_role_only():
    from jetp._country_views_v2 import _funders
    names = [dict(name_row_id=f'n{i}', party_id=p, name=n, form_type='preferred',
                  status='accepted', supersedes='')
             for i, (p, n) in enumerate([('p-de', 'Germany'), ('p-giz', 'GIZ')])]
    relations = [
        dict(relation_id='r1', from_kind='party', from_id='p-de', relation='party_in',
             to_kind='agreement', to_id='a1', role='funder', status='accepted', supersedes=''),
        dict(relation_id='r2', from_kind='party', from_id='p-giz', relation='party_in',
             to_kind='agreement', to_id='a1', role='channel', status='accepted', supersedes=''),
        dict(relation_id='r3', from_kind='agreement', from_id='a1', relation='component_of',
             to_kind='project', to_id='pr1', role=None, status='accepted', supersedes=''),
    ]
    funders, project_funders = _funders({'relations': relations, 'party_names': names}, {'a1': {}})
    assert dict(funders) == {'a1': {'Germany'}}
    assert dict(project_funders) == {'pr1': {'Germany'}}


def test_the_coverage_review_is_listed_apart_from_the_cited_documents(views):
    # A coverage row is a review record: what was collected for the project,
    # not what a document says. Its documents are served on their own and
    # never join the cited documents or the country's document index.
    tables, by_code = views
    coverage = {(row['referent_kind'], row['referent_id']): row for row in tables['coverage']}
    uncited = 0
    for view in by_code.values():
        for project in view['projects']:
            review = coverage.get(('project', project['id']))
            collected = [d for d in (review['document_ids'] or '').split(';') if d] if review else []
            assert project['coverage_documents'] == collected, project['id']
            assert project['coverage_checked_at'] == ((review or {}).get('checked_at') or '')
            cited = {row['source_id'] for row in project['evidence']} | {
                row['source_id'] for row in view['statements']
                if row['subject_kind'] == 'project' and row['subject_id'] == project['id']
                and row['source_id']}
            assert set(project['sources']) == cited, project['id']
            uncited += len(set(collected) - cited)
    assert uncited, 'the positive control: every collected document is also cited'
