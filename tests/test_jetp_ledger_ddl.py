"""The one ledger DDL, its generated CSV headers and the derived SQLite (ticket 0871).

A fixture of five tiny tables (terms, documents, snapshots, retrievals, lines)
is broken three ways: a foreign key that points nowhere, a value outside a
closed list (refused through the fixture's `terms` table, not a CHECK) and a
header that diverges from the DDL. The build fails once per breakage with a
named reason, passes when all three are fixed, and two builds of the same input
give the same SQLite byte for byte.
"""

import csv
import json
from pathlib import Path

import pytest
from jetp import ledger_build, ledger_headers

ROOT = Path(__file__).resolve().parents[1]
SHA_A = 'a' * 64


def _term(term_id, list_name):
    return {
        'term_row_id': f'{list_name}.{term_id}.1', 'term_id': term_id,
        'kind': 'value', 'list': list_name, 'label': term_id,
        'definition': f'The {term_id} value.', 'mapping_relation': 'local',
        'recorded_at': '2026-09-23', 'decided_by': 'fixture',
        'status': 'accepted',
    }


def _valid_tables():
    return {
        'terms': [_term('named_item', 'line_classification'),
                  _term('heading', 'line_classification')],
        'documents': [{'document_id': 'doc-1', 'country': 'ZAF',
                       'title': 'Register', 'language': 'en'}],
        'snapshots': [{'sha256': SHA_A, 'storage_path': 'store/a',
                       'size_bytes': '10'}],
        'retrievals': [{'retrieval_id': 'ret-1', 'document_id': 'doc-1',
                        'retrieved_at': '2026-09-23T10:00Z', 'status': 'ok',
                        'sha256': SHA_A}],
        'lines': [
            {'line_id': 'doc-1-t1-2', 'country': 'ZAF', 'sha256': SHA_A,
             'locator': 'p1 r2', 'ordinal': '2', 'classification': 'named_item',
             'recorded_at': '2026-09-23'},
            {'line_id': 'doc-1-t1-1', 'country': 'ZAF', 'sha256': SHA_A,
             'locator': 'p1 r1', 'ordinal': '1', 'classification': 'heading',
             'recorded_at': '2026-09-23'},
        ],
    }


def _write(ledger_dir, tables, header_override=None):
    schema = ledger_headers.load_schema()
    for table, rows in tables.items():
        path = ledger_headers.table_path(ledger_dir, table)
        path.parent.mkdir(parents=True, exist_ok=True)
        header = schema.header(table)
        written = (header_override or {}).get(table, header)
        with path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.writer(handle, lineterminator='\n')
            writer.writerow(written)
            for row in rows:
                writer.writerow([row.get(column, '') for column in header])


def _break_foreign_key(tables):
    tables['retrievals'][0]['document_id'] = 'doc-missing'
    return {}


def _break_closed_list(tables):
    tables['lines'][0]['classification'] = 'programme'
    return {}


def _break_header(tables):
    header = ledger_headers.load_schema().header('lines')
    return {'lines': [c if c != 'locator' else 'loc' for c in header]}


BREAKAGES = {
    'foreign_key': (_break_foreign_key, ('retrievals.document_id', 'doc-missing', 'documents')),
    'closed_list': (_break_closed_list, ('lines.classification', 'programme',
                                         'line_classification')),
    'header': (_break_header, ('lines.csv', 'locator', 'loc')),
}


# --- The DDL and its headers ------------------------------------------------

def test_ddl_declares_the_common_tables_in_file_order():
    schema = ledger_headers.load_schema()
    assert {'terms', 'publishers', 'documents', 'document_publishers',
            'retrievals', 'snapshots', 'lines', 'line_field_specs', 'projects',
            'assets', 'agreements', 'parties', 'line_referents', 'relations',
            'observations', 'timings', 'external_ids', 'adjudications',
            'adjudication_members', 'rates', 'deflators', 'routes',
            'coverage'} == set(schema.tables)
    assert schema.header('lines')[:4] == ['line_id', 'country', 'sha256', 'locator']
    assert schema.header('document_publishers') == ['document_id', 'publisher_id', 'role']


def test_table_paths_follow_the_contract(tmp_path):
    assert ledger_headers.table_path(tmp_path, 'line_referents') == tmp_path / 'line-referents.csv'
    assert ledger_headers.table_path(tmp_path, 'terms') == tmp_path / 'ontology' / 'terms.csv'


def test_no_closed_list_is_enumerated_in_a_check():
    """A closed list lives in `terms` only (ticket 0880's invariant)."""
    ddl = ledger_headers.DDL_PATH.read_text(encoding='utf-8')
    for fragment in ('CHECK (status IN', 'CHECK (measure IN', 'CHECK (classification IN',
                     "IN ('accepted'"):
        assert fragment not in ddl


def test_file_ceiling_is_read_from_the_pre_commit_hook():
    assert ledger_headers.file_ceiling() == 512000


def test_every_present_ledger_csv_carries_the_generated_header():
    assert ledger_headers.check_headers(ROOT / 'data' / 'jetp') == []


# --- Build: three named failures, then a pass ---------------------------------

def test_valid_fixture_builds(tmp_path):
    _write(tmp_path / 'ledger', _valid_tables())
    output = tmp_path / 'ledger.sqlite'
    assert ledger_build.build(tmp_path / 'ledger', output) == []
    assert output.stat().st_size > 0


@pytest.mark.parametrize('name', sorted(BREAKAGES))
def test_each_breakage_fails_with_its_named_reason(tmp_path, name):
    tables = _valid_tables()
    breaker, needles = BREAKAGES[name]
    override = breaker(tables)
    _write(tmp_path / 'ledger', tables, override)
    output = tmp_path / 'ledger.sqlite'
    errors = ledger_build.build(tmp_path / 'ledger', output)
    assert len(errors) == 1, errors
    assert errors[0].startswith(f'{name}:'), errors
    for needle in needles:
        assert needle in errors[0]
    assert not output.exists()


def test_three_breakages_fail_three_times_then_pass(tmp_path):
    """Fix one reason at a time: three failing builds, three named reasons, then a pass.

    A table whose header diverges is not loaded, so it can mask a value error
    in the same table until the header is fixed; the reasons are counted over
    the three builds, not required of the first.
    """
    remaining = sorted(BREAKAGES)
    seen = set()
    for attempt in range(len(BREAKAGES)):
        tables, override = _valid_tables(), {}
        for name in remaining:
            override.update(BREAKAGES[name][0](tables))
        _write(tmp_path / str(attempt), tables, override)
        reasons = {e.split(':')[0] for e in ledger_build.build(tmp_path / str(attempt), None)}
        assert reasons and reasons <= set(remaining), reasons
        seen |= reasons
        remaining.remove(sorted(reasons)[0])
    assert seen == set(BREAKAGES)
    _write(tmp_path / 'fixed', _valid_tables())
    assert ledger_build.build(tmp_path / 'fixed', None) == []


def test_two_builds_are_byte_identical(tmp_path, monkeypatch):
    monkeypatch.setenv('SOURCE_DATE_EPOCH', '1790000000')
    _write(tmp_path / 'ledger', _valid_tables())
    first, second = tmp_path / 'one.sqlite', tmp_path / 'two.sqlite'
    assert ledger_build.build(tmp_path / 'ledger', first) == []
    assert ledger_build.build(tmp_path / 'ledger', second) == []
    assert first.read_bytes() == second.read_bytes()
    assert int(first.stat().st_mtime) == 1790000000


def test_row_order_does_not_change_the_database(tmp_path):
    tables = _valid_tables()
    _write(tmp_path / 'a', tables)
    tables['lines'].reverse()
    _write(tmp_path / 'b', tables)
    assert ledger_build.build(tmp_path / 'a', tmp_path / 'a.sqlite') == []
    assert ledger_build.build(tmp_path / 'b', tmp_path / 'b.sqlite') == []
    assert (tmp_path / 'a.sqlite').read_bytes() == (tmp_path / 'b.sqlite').read_bytes()


def test_cli_exits_nonzero_on_a_broken_ledger(tmp_path, capsys):
    tables = _valid_tables()
    _break_foreign_key(tables)
    _write(tmp_path / 'ledger', tables)
    assert ledger_build.main(['--ledger-dir', str(tmp_path / 'ledger'), '--check']) == 1
    assert 'foreign_key:' in capsys.readouterr().err


def test_empty_ledger_builds(tmp_path):
    (tmp_path / 'ledger').mkdir()
    assert ledger_build.build(tmp_path / 'ledger', tmp_path / 'empty.sqlite') == []


# --- Per-document fields tables ---------------------------------------------

def _with_line_fields(ledger_dir, spec, header):
    tables = _valid_tables()
    tables['line_field_specs'] = [{'document_id': 'doc-1', 'columns': json.dumps(spec)}]
    _write(ledger_dir, tables)
    path = ledger_dir / 'line-fields' / 'doc-1.csv'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(header)
        writer.writerow(['doc-1-t1-1', 'Kusile', 'A. Planned'])


def test_line_fields_header_matches_its_spec(tmp_path):
    _with_line_fields(tmp_path, ['Project', 'Status'], ['line_id', 'Project', 'Status'])
    assert ledger_build.build(tmp_path, None) == []


def test_line_fields_header_divergence_names_the_column(tmp_path):
    _with_line_fields(tmp_path, ['Project', 'Status'], ['line_id', 'Project', 'Stage'])
    errors = ledger_build.build(tmp_path, None)
    assert len(errors) == 1 and errors[0].startswith('header:')
    assert 'Stage' in errors[0] and 'Status' in errors[0]


def test_line_fields_without_a_spec_is_refused(tmp_path):
    _with_line_fields(tmp_path, ['Project', 'Status'], ['line_id', 'Project', 'Status'])
    ledger_headers.table_path(tmp_path, 'line_field_specs').unlink()
    errors = ledger_build.build(tmp_path, None)
    assert any('doc-1' in e and 'line_field_specs' in e for e in errors), errors


# --- Chunking by country and year -------------------------------------------

def test_oversized_table_is_chunked_and_reunited(tmp_path):
    tables = _valid_tables()
    tables['lines'].append({
        'line_id': 'doc-1-t1-3', 'country': 'VNM', 'sha256': SHA_A,
        'locator': 'p2 r1', 'ordinal': '3', 'classification': 'named_item',
        'recorded_at': '2025-01-10'})
    whole, chunked = tmp_path / 'whole', tmp_path / 'chunked'
    _write(whole, tables)
    lines = tables.pop('lines')
    _write(chunked, tables)
    written = ledger_headers.write_table(chunked, 'lines', lines, ceiling=200)
    assert sorted(p.name for p in written) == ['VNM-2025.csv', 'ZAF-2026.csv']
    assert not ledger_headers.table_path(chunked, 'lines').exists()

    assert ledger_build.build(whole, tmp_path / 'whole.sqlite') == []
    assert ledger_build.build(chunked, tmp_path / 'chunked.sqlite') == []
    assert (tmp_path / 'whole.sqlite').read_bytes() == (tmp_path / 'chunked.sqlite').read_bytes()


def test_small_table_is_written_as_one_file(tmp_path):
    written = ledger_headers.write_table(tmp_path, 'publishers',
                                         [{'publisher_id': 'pub-1', 'name': 'T'}])
    assert written == [tmp_path / 'publishers.csv']
    assert ledger_headers.check_headers(tmp_path) == []


def test_chunk_country_must_match_its_file(tmp_path):
    tables = _valid_tables()
    lines = tables.pop('lines')
    _write(tmp_path, tables)
    ledger_headers.write_table(tmp_path, 'lines', lines, ceiling=1)
    chunk = tmp_path / 'lines' / 'ZAF-2026.csv'
    chunk.rename(tmp_path / 'lines' / 'IDN-2026.csv')
    errors = ledger_build.build(tmp_path, None)
    assert any(e.startswith('chunk:') and 'IDN-2026.csv' in e for e in errors), errors
