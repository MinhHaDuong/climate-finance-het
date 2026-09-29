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


def test_a_channel_is_served_beside_the_funders_under_its_own_name(views):
    # Author, 2026-09-29: the channel is shown as a second line, never as a
    # funder. Agreements, their statements and the projects they compose
    # carry `channels`, the preferred name forms, sorted, from the same rows.
    tables, by_code = views
    preferred = {row['party_id']: row['name'] for row in tables['party_names']
                 if row['form_type'] == 'preferred' and row['status'] == 'accepted'}
    channels = {}
    for row in tables['relations']:
        if row['relation'] == 'party_in' and row['role'] == 'channel' and row['status'] == 'accepted':
            channels.setdefault(row['to_id'], set()).add(preferred[row['from_id']])
    served = 0
    for view in by_code.values():
        for agreement in view['agreements']:
            assert agreement['channels'] == sorted(channels.get(agreement['id'], ()))
            served += bool(agreement['channels'])
        for statement in view['statements']:
            expected = channels.get(statement['subject_id'], ()) if statement['subject_kind'] == 'agreement' else ()
            assert statement['channels'] == '; '.join(sorted(expected))
    assert served == len(channels), 'the positive control: every channel row is served once'
    # A project's channels are those of its component agreements, derived,
    # and a channel there is never among that project's funders.
    components = {}
    for row in tables['relations']:
        if row['status'] == 'accepted' and row['relation'] == 'component_of' \
                and row['from_kind'] == 'agreement' and row['to_kind'] == 'project':
            components.setdefault(row['to_id'], set()).add(row['from_id'])
    with_channels = 0
    for view in by_code.values():
        for project in view['projects']:
            expected = sorted({name for agreement in components.get(project['id'], ())
                               for name in channels.get(agreement, ())})
            assert project['channels'] == expected, project['id']
            with_channels += bool(expected)
    assert with_channels, 'the positive control: no project reaches a channel'


def test_funders_keep_the_funder_role_and_channels_the_channel_role():
    from jetp._country_views_v2 import _parties
    # The World Bank is the channel of a1 and the funder of a2, both
    # components of pr1: a role is per agreement, so the project lists it on
    # both lines (Codex review, 2026-09-29).
    names = [dict(name_row_id=f'n{i}', party_id=p, name=n, form_type='preferred',
                  status='accepted', supersedes='')
             for i, (p, n) in enumerate([('p-de', 'Germany'), ('p-giz', 'GIZ'), ('p-wb', 'World Bank')])]
    party_in = [('r1', 'p-de', 'a1', 'funder'), ('r2', 'p-giz', 'a1', 'channel'),
                ('r3', 'p-wb', 'a1', 'channel'), ('r4', 'p-wb', 'a2', 'funder')]
    relations = [
        dict(relation_id=rid, from_kind='party', from_id=party, relation='party_in',
             to_kind='agreement', to_id=agreement, role=role, status='accepted', supersedes='')
        for rid, party, agreement, role in party_in
    ] + [
        dict(relation_id=f'c{agreement}', from_kind='agreement', from_id=agreement, relation='component_of',
             to_kind='project', to_id='pr1', role=None, status='accepted', supersedes='')
        for agreement in ('a1', 'a2')
    ]
    parties, by_project = _parties({'relations': relations, 'party_names': names}, {'a1': {}, 'a2': {}})
    def held(mapping):
        return {k: v for k, v in mapping.items() if v}

    assert held(parties['funder']) == {'a1': {'Germany'}, 'a2': {'World Bank'}}
    assert held(parties['channel']) == {'a1': {'GIZ', 'World Bank'}}
    assert held(by_project['funder']) == {'pr1': {'Germany', 'World Bank'}}
    assert held(by_project['channel']) == {'pr1': {'GIZ', 'World Bank'}}


def test_an_unknown_collected_document_fails_loud_and_does_not_block(views, caplog, capsys):
    # Author's ruling, 2026-09-29: a build-time assert fails loud and does
    # not block. The unknown id is logged at ERROR with the row citing it,
    # counted once at the end, left out of the served list, and nothing in
    # the views hides it.
    import copy
    tables, _ = views
    tables = dict(tables, coverage=copy.deepcopy(tables['coverage']))
    row = next(r for r in tables['coverage'] if r['referent_kind'] == 'project'
               and r['referent_id'] == 'project-vnm-project-bac-ai-pumped-hydro')
    row['document_ids'] += ';vnm-no-such-document'
    config = yaml.safe_load((ROOT / 'config/jetp_observatory.yaml').read_text())
    with caplog.at_level('ERROR'):
        view = country_view(ROOT / 'data/jetp', 'VNM', config['countries']['VNM'], tables=tables)
    project = next(p for p in view['projects'] if p['id'] == row['referent_id'])
    assert 'vnm-no-such-document' not in project['coverage_documents']
    assert project['coverage_documents'] == row['document_ids'].split(';')[:-1]
    errors = [r for r in caplog.records if r.levelname == 'ERROR' and 'vnm-no-such-document' in r.getMessage()]
    assert len(errors) == 1 and 'project-vnm-project-bac-ai-pumped-hydro' in errors[0].getMessage()
    assert 'coverage: 1 unknown document ids, not served' in capsys.readouterr().err
    assert 'vnm-no-such-document' not in str(view)


def test_every_coverage_row_of_the_country_is_checked_not_only_the_projects(views, caplog, capsys):
    # Codex review, 2026-09-29: agreement, asset, party and perimeter rows
    # cite documents too. An unknown id on an agreement row of the country
    # is logged and counted like a project's, though no view lists it.
    import copy
    tables, _ = views
    tables = dict(tables, coverage=copy.deepcopy(tables['coverage']))
    row = next(r for r in tables['coverage'] if r['referent_kind'] == 'agreement'
               and r['referent_id'] == 'agreement-idn-fin-isle-1')
    row['document_ids'] += ';idn-no-such-document'
    config = yaml.safe_load((ROOT / 'config/jetp_observatory.yaml').read_text())
    with caplog.at_level('ERROR'):
        country_view(ROOT / 'data/jetp', 'IDN', config['countries']['IDN'], tables=tables)
    errors = [r.getMessage() for r in caplog.records if r.levelname == 'ERROR']
    assert [m for m in errors if 'agreement-idn-fin-isle-1' in m and 'idn-no-such-document' in m]
    assert 'coverage: 1 unknown document ids, not served' in capsys.readouterr().err


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
