"""The six M1a extracts as ledger lines, and the M1a view read back from them (ticket 0873).

Step 2 of the migration: the inventory tab is the check. The view regenerated
from ``lines``, ``line-fields``, ``line-field-specs`` and ``routes`` is the
served view byte for byte; the ledger record replays from the pinned extracts;
the counts are those of the tables at launch; two lines never claim the same
place in the same bytes, a locator naming a whole report is refused, and a
member line's ``groups`` names its heading.
"""

import csv
from pathlib import Path

import pytest
from jetp import _ledger_headers as ledger_headers
from jetp import build_ledger
from jetp.build_m1a_inventories import build_existing_layers, write_inventories
from jetp.build_m1a_lines import check_locator, ingest, with_pdf_page, write_ledger

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'data' / 'jetp'
SERVED = ROOT / 'deliverables' / 'jetp-observatory' / 'data' / 'm1a'
COUNTRIES = ('ZAF', 'IDN', 'VNM', 'SEN')


@pytest.fixture(scope='module')
def regenerated(tmp_path_factory):
    output = tmp_path_factory.mktemp('m1a')
    write_inventories(build_existing_layers(ROOT), output)
    return output


@pytest.fixture(scope='module')
def ingested():
    return ingest(ROOT)


@pytest.mark.parametrize('country', COUNTRIES)
def test_the_view_read_from_the_lines_is_the_served_view_byte_for_byte(regenerated, country):
    for suffix in ('json', 'csv'):
        assert (regenerated / f'{country}.{suffix}').read_bytes() == (
            SERVED / f'{country}.{suffix}').read_bytes()


def test_the_ledger_record_replays_from_the_pinned_extracts(ingested, tmp_path):
    written = write_ledger(ingested, tmp_path)
    assert written
    for path in written:
        relative = path.relative_to(tmp_path)
        committed = LEDGER / relative
        if relative.parts[0] == 'lines.d':
            with path.open(encoding='utf-8', newline='') as handle:
                replay = list(csv.DictReader(handle))
            with committed.open(encoding='utf-8', newline='') as handle:
                current = {row['line_id']: row for row in csv.DictReader(handle)}
            # Ticket 0888 adds the publisher's verbatim sector to these same
            # lines; the M1a ingestion still owns every other column.
            assert replay == [dict(current[row['line_id']], own_sector='')
                              for row in replay], relative
        elif relative == Path('line-field-specs.csv'):
            with path.open(encoding='utf-8', newline='') as handle:
                replay = list(csv.DictReader(handle))
            with committed.open(encoding='utf-8', newline='') as handle:
                current = {row['document_id']: row for row in csv.DictReader(handle)}
            assert replay == [current[row['document_id']] for row in replay]
        else:
            assert path.read_bytes() == committed.read_bytes(), relative
    committed = {p.relative_to(LEDGER) for p in (LEDGER / 'line-fields').glob('*.csv')}
    committed |= {p.relative_to(LEDGER) for p in (LEDGER / 'lines.d').glob('*.csv')}
    assert {p.relative_to(tmp_path) for p in written} <= committed | {
        Path('line-field-specs.csv'), Path('routes.csv')}


def test_counts_are_those_of_the_tables_at_launch(ingested):
    per_country = {}
    for line in ingested['lines']:
        per_country[line['country']] = per_country.get(line['country'], 0) + 1
    assert per_country == {'ZAF': 257, 'IDN': 1579, 'VNM': 279, 'SEN': 49}
    vnm = [line['classification'] for line in ingested['lines'] if line['country'] == 'VNM']
    assert {term: vnm.count(term) for term in set(vnm)} == {
        'heading': 73, 'unnamed_item': 181, 'named_item': 25}
    zaf = [line for line in ingested['lines'] if line['country'] == 'ZAF']
    assert {line['classification'] for line in zaf} == {'register_allocation'}
    assert all(line['own_status'] and line['own_status_axis'] == 'delivery' for line in zaf)
    assert len(ingested['routes']) == 1579 + 49 + 279


def test_the_committed_ledger_is_valid():
    assert build_ledger.build(LEDGER) == []


# --- Refusals, on a fixture ledger -------------------------------------------

SHA = 'a' * 64


def _term(term_id, list_name):
    return {'term_row_id': f'{list_name}.{term_id}.1', 'term_id': term_id, 'kind': 'value',
            'list': list_name, 'label': term_id, 'definition': f'The {term_id} value.',
            'mapping_relation': 'local', 'recorded_at': '2026-09-23',
            'decided_by': 'fixture', 'status': 'accepted'}


def _line(ordinal, locator, classification='named_item', groups=''):
    return {'line_id': f'doc-1-t-{ordinal}', 'country': 'ZAF', 'sha256': SHA,
            'locator': locator, 'ordinal': str(ordinal), 'classification': classification,
            'groups': groups, 'recorded_at': '2026-09-23'}


def _build(ledger_dir, lines):
    tables = {
        'terms': [_term('named_item', 'line_classification'),
                  _term('heading', 'line_classification'),
                  _term('collected', 'retrieval_status')],
        'documents': [{'document_id': 'doc-1', 'country': 'ZAF', 'title': 'Register'}],
        'snapshots': [{'sha256': SHA, 'storage_path': 'store/a', 'size_bytes': '10'}],
        'retrievals': [{'retrieval_id': 'doc-1:1', 'document_id': 'doc-1',
                        'retrieved_at': '2026-09-23T10:00Z', 'status': 'collected',
                        'sha256': SHA, 'collection_method': 'script'}],
        'lines': lines,
    }
    schema = ledger_headers.load_schema()
    for table, rows in tables.items():
        path = ledger_headers.table_path(ledger_dir, table)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.writer(handle, lineterminator='\n')
            writer.writerow(schema.header(table))
            writer.writerows([row.get(c, '') for c in schema.header(table)] for row in rows)
    return build_ledger.build(ledger_dir)


def test_two_lines_at_one_place_in_the_same_bytes_are_refused(tmp_path):
    errors = _build(tmp_path, [_line(1, 'p. 3, row 1'), _line(2, 'p. 3, row 1')])
    assert any(e.startswith('unique:') and 'lines.sha256, lines.locator' in e for e in errors)
    assert _build(tmp_path, [_line(1, 'p. 3, row 1'), _line(2, 'p. 3, row 2')]) == []


def test_the_ingestion_refuses_a_repeated_place(ingested):
    from jetp.build_m1a_lines import _check_unique

    lines = ingested['lines']
    with pytest.raises(ValueError, match='sha256/locator'):
        _check_unique([lines[0], dict(lines[1], locator=lines[0]['locator'],
                                      sha256=lines[0]['sha256'])], ('sha256', 'locator'))


@pytest.mark.parametrize('locator', ['whole report', 'Whole Report', 'full document',
                                     'Annual report', '', '   '])
def test_a_locator_naming_only_the_document_is_refused(locator):
    with pytest.raises(ValueError, match='no place finer'):
        check_locator(locator)


def test_a_locator_naming_a_place_passes():
    for locator in ('Annex 2, p. 13, row 1; PDF page 13', 'Overall - Data, Unique ID ACTIP001',
                    'Annex I.1; PDF pages 155; printed pages 139; ordinal 1'):
        assert check_locator(locator) == locator


def test_a_member_line_names_its_heading_in_groups(tmp_path):
    heading = _line(1, 'p. 3, note 1', classification='heading')
    member = _line(2, 'p. 3, row 1', groups=heading['line_id'])
    assert _build(tmp_path / 'ok', [heading, member]) == []

    missing = _build(tmp_path / 'missing', [heading, dict(member, groups='doc-1-t-9')])
    assert any(e.startswith('foreign_key:') and "lines.groups = 'doc-1-t-9'" in e
               for e in missing)

    not_heading = _build(tmp_path / 'item', [dict(heading, classification='named_item'), member])
    assert any(e.startswith('line_groups:') and 'not a heading' in e for e in not_heading)

    itself = _build(tmp_path / 'self', [dict(heading, groups=heading['line_id'])])
    assert any(e.startswith('line_groups:') and 'the line itself' in e for e in itself)


def test_a_declared_page_offset_adds_the_pdf_page_and_an_undeclared_one_adds_nothing():
    # Ticket 0861, moved with the plan adapter into the ingestion.
    assert with_pdf_page('Annex 2, p. 13, row 1', None) == 'Annex 2, p. 13, row 1'
    assert with_pdf_page('Annex 2, p. 13, row 1', 16) == 'Annex 2, p. 13, row 1; PDF page 29'
    with pytest.raises(ValueError, match='no printed page'):
        with_pdf_page('Appendix 1, table 4, printed row 48', 0)
