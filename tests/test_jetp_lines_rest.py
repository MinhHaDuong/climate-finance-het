"""The remaining JETP lines are replayable from legacy inputs (ticket 0874)."""

import csv
import hashlib
import shutil
import sqlite3
from pathlib import Path

import pytest
from jetp._ledger_headers import load_schema, read_table
from jetp.build_lines import (
    _classification,
    _pilot_classification,
    _shortest_locator,
    rebuild,
)

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'data' / 'jetp'
INPUTS = ('vnm-pilot-manifest.csv', 'vnm-pilot-observations.csv',
          'idn-portfolio-observations.csv', 'source-claims.csv',
          'project-source-links.csv')
TABLES = ('documents.csv', 'retrievals.csv', 'snapshots.csv', 'line-field-specs.csv')


pytestmark = pytest.mark.wp_jetp

def _fixture(tmp_path):
    for name in INPUTS + TABLES:
        shutil.copyfile(LEDGER / name, tmp_path / name)
    shutil.copytree(LEDGER / 'lines.d', tmp_path / 'lines.d')
    return tmp_path


def _rows(directory, table):
    schema = load_schema()
    rows, errors = read_table(directory, table, schema)
    assert errors == []
    return [dict(zip(schema.header(table), row)) for row in rows]


def test_rebuild_counts_pending_and_repeat_bytes(tmp_path):
    ledger = _fixture(tmp_path)
    counts, pending, candidates = rebuild(ledger, write=True)
    # Ticket 0926 collected blocked sources through the author's browser
    # session: two more claims and two more discoveries now cite archived
    # bytes, and seven records leave the pending list (146/35/55 before).
    # Ticket 1160 adds reviewed lines for seven source snapshots that otherwise
    # needed generic discovery lines. The replay must preserve those citations.
    assert dict(counts) == {'pilot_manifest': 66, 'pilot_observation': 46,
                            'portfolio': 46, 'claim': 148, 'discovery': 30}
    assert len(pending) == 47  # The AfDB MURP source was collected by 0926.
    assert len(candidates) == 304
    paths = sorted((ledger / 'lines.d').glob('*.csv'))
    paths += sorted((ledger / 'migration').glob('*.csv'))
    before = {str(path): path.read_bytes() for path in paths}
    assert rebuild(ledger, write=True)[0] == counts
    assert before == {str(path): path.read_bytes() for path in paths}
    assert not (ledger / 'projects.csv').exists()
    assert not (ledger / 'line-referents.csv').exists()


def test_pilot_lines_cite_frozen_local_bytes_and_plan_ruptl_stays_on_the_line():
    lines = _rows(LEDGER, 'lines')
    snapshots = {row['sha256']: row for row in _rows(LEDGER, 'snapshots')}
    for stem in ('vnm-pilot-manifest', 'vnm-pilot-observations'):
        content = (LEDGER / f'{stem}.csv').read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        assert (LEDGER / 'ledger-snapshots' / f'{sha}.csv').read_bytes() == content
        assert snapshots[sha]['storage_path'] == f'../ledger-snapshots/{sha}.csv'
    assert sum((row['notes'] or '').startswith('method=pilot_manifest;') for row in lines) == 66
    assert sum((row['notes'] or '').startswith('method=pilot_observation;') for row in lines) == 46
    assert any(row['classification'] == 'envelope' and
               'zaf-annex25-finance-aggregate' in (row['notes'] or '') for row in lines)
    with (LEDGER / 'line-fields' / 'idn-cipp-2023-cpr-mirror.csv').open(
            encoding='utf-8', newline='') as handle:
        fields = list(csv.DictReader(handle))
    assert sum(row['ruptl'] == 'YES' for row in fields) >= 230


def test_an_old_project_id_is_not_a_typed_referent():
    conn = sqlite3.connect(':memory:')
    try:
        conn.executescript((ROOT / 'config' / 'jetp-ledger.sql').read_text())
        conn.execute("INSERT INTO line_referents "
                     "(referent_row_id,line_id,referent_kind,referent_id,status,method,decided_at,decided_by) "
                     "VALUES ('candidate','line-1','project','legacy-project-id','accepted',"
                     "'legacy_link','2026-09-24','fixture')")
        details = [row[0] for row in conn.execute('SELECT detail FROM violation_typed_reference')]
        assert any("project 'legacy-project-id' does not exist" in row for row in details)
    finally:
        conn.close()


def test_discovery_uses_the_shortest_precise_locator():
    links = [
        {'link_id': 'a', 'locator': 'pp. 32-37, CERER/PTB infrastructure quality programme'},
        {'link_id': 'b', 'locator': 'Related programme or geographic lead'},
        {'link_id': 'c', 'locator': 'Printed p.15: Gandiaye pilot'},
    ]
    assert _shortest_locator(links)['link_id'] == 'c'


def test_claim_type_is_independent_of_a_legacy_project_match():
    with (LEDGER / 'source-claims.csv').open(encoding='utf-8', newline='') as handle:
        claims = {row['claim_id']: row for row in csv.DictReader(handle)}
    assert _classification(claims['zaf-growth26-pipeline']) == 'count'
    assert _classification(claims['zaf-growth26-funnel']) == 'count'
    assert _classification(claims['zaf-growth26-investment-need']) == 'envelope'
    assert _classification(claims['zaf-annex25-dbsa-credit']) == 'named_item'
    for claim_id in ('zaf-annex25-eu-cso-grants', 'zaf-annex25-uk-utility-reform',
                     'zaf-annex25-uk-six-municipalities', 'zaf-annex25-youth-skills'):
        assert _classification(claims[claim_id]) == 'count'


def test_pilot_aggregate_type_uses_portfolio_role_and_meaning():
    with (LEDGER / 'vnm-pilot-observations.csv').open(encoding='utf-8', newline='') as handle:
        rows = {row['observation_id'][-3:]: row for row in csv.DictReader(handle)}
    for row_id in ('005', '014', '027', '029', '034', '035', '036', '037', '038'):
        assert _pilot_classification(rows[row_id]) == 'envelope'
    assert _pilot_classification(rows['016']) == 'named_item'
    assert _pilot_classification(rows['039']) == 'absence'
