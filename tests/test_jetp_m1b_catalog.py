"""The bounded catalogue preserves decisions, candidates and frozen lines."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest
from jetp.build_m1b_catalog import (
    catalog_country,
    check_catalog,
    coverage_dispositions,
    write_catalog,
)

pytestmark = pytest.mark.domain_jetp


@pytest.fixture
def ledger():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    ddl = Path(__file__).resolve().parents[1] / 'config/jetp-ledger.sql'
    conn.executescript(ddl.read_text())
    sha256 = 'a' * 64
    conn.execute('INSERT INTO snapshots (sha256,storage_path,size_bytes) VALUES (?,?,?)',
                 (sha256, 'fixture.pdf', 1))
    for document_id in ('document', 'outside-m1a'):
        conn.execute('INSERT INTO documents (document_id,country,title) VALUES (?,?,?)',
                     (document_id, 'IDN', document_id))
    conn.execute('INSERT INTO retrievals (retrieval_id,document_id,retrieved_at,status,sha256,'
                 'collection_method) VALUES (?,?,?,?,?,?)',
                 ('retrieval', 'document', '2026-09-24', 'collected', sha256, 'script'))
    for line_id, groups in [('a', None), ('b', None), ('heading', None), ('child', 'heading')]:
        conn.execute('INSERT INTO lines (line_id,country,sha256,locator,ordinal,label,'
                     'classification,groups,recorded_at) VALUES (?,?,?,?,?,?,?,?,?)',
                     (line_id, 'IDN', sha256, line_id, 1, line_id,
                      'heading' if line_id == 'heading' else 'named_item', groups, '2026-09-24'))
    conn.execute("INSERT INTO projects (project_id,country,canonical_name) VALUES ('p','IDN','Plant')")
    conn.execute("INSERT INTO projects (project_id,country,canonical_name) VALUES ('c','IDN','Component')")
    for row_id, line_id in [('mint-a', 'a'), ('mint-b', 'b')]:
        conn.execute('INSERT INTO line_referents (referent_row_id,line_id,referent_kind,'
                     'referent_id,status,method,justification_line_ids,decided_at,decided_by) '
                     'VALUES (?,?,?,?,?,?,?,?,?)',
                     (row_id, line_id, 'project', 'p', 'accepted', 'exact_id', line_id,
                      '2026-09-24', 'fixture'))
    conn.execute("INSERT INTO line_referents (referent_row_id,line_id,referent_kind,referent_id,"
                 "status,method,justification_line_ids,decided_at,decided_by) VALUES "
                 "('mint-child','child','project','c','accepted','exact_id','child','2026-09-24','fixture')")
    for row_id, source, relation, target, status, justification in [
        ('duplicate', 'a', 'same_as', 'b', 'accepted', 'a'),
        ('component', 'c', 'component_of', 'p', 'accepted', 'heading'),
        ('proposal', 'b', 'same_as', 'child', 'candidate', 'b'),
    ]:
        conn.execute('INSERT INTO relations (relation_id,from_kind,from_id,relation,to_kind,'
                     'to_id,status,method,decided_at,decided_by,line_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                     (row_id, 'project' if relation == 'component_of' else 'line', source, relation,
                      'project' if relation == 'component_of' else 'line', target, status,
                      'fixture', '2026-09-24', 'fixture', justification))
    assert list(conn.execute('PRAGMA foreign_key_check')) == []
    yield conn
    conn.close()


def test_justified_duplicate_component_and_unjustified_candidate(ledger):
    result = catalog_country(ledger, 'IDN', {'a', 'b', 'heading', 'child'}, set())
    assert result['counts']['referents'] == {'project': 2, 'asset': 0, 'agreement': 0, 'party': 0}
    assert result['counts']['candidate_relations'] == {'same_as': 1}
    assert [row['relation_id'] for row in result['relations']] == ['component', 'duplicate']
    assert next(row for row in result['referents'] if row['id'] == 'p')['decision_ids'] == ['mint-a', 'mint-b']
    assert list(ledger.execute('SELECT * FROM violation_line_groups')) == []
    assert result['candidates']['relations'][0]['relation_id'] == 'proposal'
    assert result['candidates']['in_force'] is False


@pytest.mark.parametrize('line_id', ['heading', 'a'])
def test_missing_justification_refuses_accepted_output(ledger, line_id):
    ledger.execute('DELETE FROM lines WHERE line_id = ?', (line_id,))
    with pytest.raises(ValueError, match='justification'):
        catalog_country(ledger, 'IDN', {'a', 'b', 'heading', 'child'}, set())


def test_rejecting_candidate_changes_no_accepted_identity_or_relation(ledger):
    before = catalog_country(ledger, 'IDN', {'a', 'b', 'heading', 'child'}, set())
    ledger.execute("INSERT INTO relations (relation_id,from_kind,from_id,relation,to_kind,to_id,"
                   "status,method,decided_at,decided_by,supersedes,line_id) VALUES "
                   "('reject','line','b','same_as','line','child','rejected','fixture',"
                   "'2026-09-25','fixture','proposal','b')")
    after = catalog_country(ledger, 'IDN', {'a', 'b', 'heading', 'child'}, set())
    assert before['referents'] == after['referents']
    assert before['relations'] == after['relations']
    assert after['candidates']['relations'] == []


def test_accepted_supersession_is_applied_before_scope_selection(ledger):
    ledger.execute("INSERT INTO line_referents (referent_row_id,line_id,referent_kind,referent_id,"
                   "status,method,decided_at,decided_by,supersedes) VALUES "
                   "('revoke','child','project','p','rejected','fixture','2026-09-25','fixture','mint-a')")
    result = catalog_country(ledger, 'IDN', {'a'}, set())
    assert result['counts']['referents']['project'] == 0


def test_unrelated_snapshot_line_does_not_enter_catalogue(ledger):
    result = catalog_country(ledger, 'IDN', {'a', 'b'}, set())
    assert result['scope_line_ids'] == ['a', 'b']
    assert 'child' not in result['scope_line_ids']
    assert json.loads(json.dumps(result)) == result


def test_all_carried_coverage_identifiers_keep_recorded_dispositions():
    root = Path(__file__).resolve().parents[1]
    rows, _ = coverage_dispositions(root / 'data/jetp')
    assert len(rows) == len({row['legacy_id'] for row in rows}) == 17
    assert all(row['disposition'].startswith('unresolved_') and not row['in_force'] for row in rows)
    assert all(row['ownership_decision']['owner'] == '0833' for row in rows)
    assert all(row['decision']['reviewed_by'] and row['decision']['reviewed_at'] for row in rows)


def test_party_role_is_counted_once_without_folding_pending_alias(ledger):
    for identity in ('funder', 'alias'):
        ledger.execute('INSERT INTO parties (party_id,authority_category) VALUES (?,?)',
                       (identity, 'bilateral_funder'))
        ledger.execute('INSERT INTO party_names (name_row_id,party_id,name,form_type,document_id,'
                       'recorded_at,decided_by,status) VALUES (?,?,?,?,?,?,?,?)',
                       (identity + '-name', identity, identity, 'preferred', 'outside-m1a',
                        '2026-09-24', 'fixture', 'accepted'))
    for identity, line_id in [('role-a', 'a'), ('role-b', 'b')]:
        ledger.execute('INSERT INTO relations (relation_id,from_kind,from_id,relation,to_kind,to_id,'
                       'status,method,decided_at,decided_by,line_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                       (identity, 'party', 'funder', 'role_in', 'project', 'p', 'accepted',
                        'fixture', '2026-09-24', 'fixture', line_id))
    ledger.execute("INSERT INTO relations (relation_id,from_kind,from_id,relation,to_kind,to_id,"
                   "status,method,decided_at,decided_by) VALUES "
                   "('party-alias','party','funder','same_as','party','alias','candidate',"
                   "'fixture','2026-09-24','fixture')")
    result = catalog_country(ledger, 'IDN', {'a', 'b'}, set())
    assert result['counts']['referents']['party'] == 1
    party = next(row for row in result['referents'] if row['kind'] == 'party')
    assert party['evidence_country'] == 'IDN'
    assert party['name_record']['document_id'] == 'outside-m1a'
    assert party['relation_decision_ids'] == ['role-a', 'role-b']
    assert 'party-alias' in [row['relation_id'] for row in result['candidates']['relations']]


def test_referent_endpoint_does_not_admit_outside_scope_accepted_relation(ledger):
    result = catalog_country(ledger, 'IDN', {'a', 'b'}, set())
    # Both projects exist, and p is counted; the heading justifying this
    # component relation is outside the selected frozen extraction.
    assert 'component' not in [row['relation_id'] for row in result['relations']]


def test_live_frozen_check_does_not_depend_on_current_ontology(tmp_path):
    root = Path(__file__).resolve().parents[1]
    (tmp_path / 'config').mkdir()
    (tmp_path / 'config/jetp-m1b-release.json').write_bytes((root / 'config/jetp-m1b-release.json').read_bytes())
    # No current ontology or ledger exists here: a live artifact check reads
    # the frozen O reference and output checksums only.
    descriptor = check_catalog(tmp_path, root / 'deliverables/jetp-observatory/data/m1b')
    assert descriptor['ontology']['release_id'] == 'O-v1'


def test_frozen_artifact_check_rejects_missing_decision_sidecar(tmp_path):
    root = Path(__file__).resolve().parents[1]
    destination = tmp_path / 'm1b'
    shutil.copytree(root / 'deliverables/jetp-observatory/data/m1b', destination)
    (destination / 'IDN-decisions.json').unlink()
    with pytest.raises(ValueError, match='artifact hash mismatch'):
        check_catalog(root, destination)


@pytest.mark.slow
def test_real_release_reproduces_without_editing_inventory_bytes(tmp_path):
    root = Path(__file__).resolve().parents[1]
    expected = root / 'deliverables/jetp-observatory/data/m1b'
    descriptor = json.loads((expected / 'manifest.json').read_text())
    if any(not (root / name).is_file() or hashlib.sha256((root / name).read_bytes()).hexdigest() != digest
           for name, digest in descriptor['inputs'].items()):
        pytest.skip('Historical M1b replay requires its original input hashes; live artifact checks remain active')
    protected = sorted((root / 'data/jetp').glob('lines*/*.csv'))
    protected += sorted((root / 'data/jetp/line-fields').glob('*.csv'))
    protected += sorted((root / 'deliverables/jetp-observatory/data/m1a').glob('*'))
    def fingerprints(paths):
        return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    before = fingerprints(protected)
    first = write_catalog(root, tmp_path / 'first')
    second = write_catalog(root, tmp_path / 'second')
    assert first == second
    assert {code: entry['counts']['lines'] for code, entry in first['countries'].items()} == {
        'ZAF': 257, 'IDN': 1579, 'VNM': 279, 'SEN': 49}
    for path in (tmp_path / 'first').iterdir():
        assert path.read_bytes() == (tmp_path / 'second' / path.name).read_bytes()
        assert path.read_bytes() == (expected / path.name).read_bytes()
    assert before == fingerprints(protected)


@pytest.mark.integration
def test_browser_projection_keeps_candidates_separate_and_justification_visible():
    from test_jetp_observatory_render import render
    page = render('referents/IDN')
    assert 'Pending matches — not in force' in page['main']
    assert '11 of 11 decisions' == page['elements']['m1b-candidates-count']['textContent']
    accepted = page['elements']['m1b-identities-results']['innerHTML']
    candidates = page['elements']['m1b-candidates-results']['innerHTML']
    assert '0875.tier2.' not in accepted
    assert '0875.tier2.' in candidates
    assert 'data-link="publisher"' in accepted
    assert 'data-sha256=' in accepted
    assert 'decided_by' in candidates
    assert '[object Object]' not in candidates
