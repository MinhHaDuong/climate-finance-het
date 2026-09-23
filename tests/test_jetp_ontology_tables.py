"""The ontology tables, their revision rule and their alignment with the specification (ticket 0880).

Two halves. The fixture half rewords a term (same ``term_id``, a new row that
supersedes), then changes a meaning (a new ``term_id``), and remaps a status
crosswalk: the ontology read at a cutoff before a change gives the old words,
after it the new ones, and a data row that cited the old term stays valid.

The alignment half reads the real files. The English specification
(``docs/jetp-ontology.md``, with the storage contract for the tables it
declares) and the formal one (the DDL and ``data/jetp/ontology/terms.csv``)
must agree both ways: every value the specification writes in code type in
sections 2 to 4 is a term in force, every term in force appears in the
specification, every table and column of the contract is the DDL's, and the
DDL uses none of the retired words of ``docs/jetp-language.md``.
"""

import csv
import re
from pathlib import Path

import pytest
from jetp import _ledger_headers as ledger_headers
from jetp import _ontology as ontology
from jetp import build_ledger as ledger_build

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_DOC = ROOT / 'docs' / 'jetp-ontology.md'
STORAGE_DOC = ROOT / 'docs' / 'jetp-ledger-storage.md'
SHA_A = 'a' * 64

# Words the specification quotes in code type that are neither terms nor DDL
# names: a comparator's own field names, printed as the publisher prints them.
PUBLISHER_FIELD_NAMES = frozenset({'crs_id', 'donor_project_id'})

# Retired or restricted words that no DDL table or column may carry.
RETIRED_WORD = re.compile(r'(^|_)(evidence|model|layer|fact)(_|$)|(^|_)reconcil')


# --- Fixture ------------------------------------------------------------------

def _term(term_id, list_name, definition, recorded_at, row=1, supersedes=None,
          status='accepted'):
    return {'term_row_id': f'{list_name}.{term_id}.{row}', 'term_id': term_id,
            'kind': 'value', 'list': list_name, 'label': term_id,
            'definition': definition, 'mapping_relation': 'local',
            'recorded_at': recorded_at, 'decided_by': 'fixture', 'status': status,
            'supersedes': supersedes}


def _crosswalk(row_id, own_status, shared, recorded_at, supersedes=None):
    return {'crosswalk_row_id': row_id, 'publisher_id': 'pub-1',
            'own_status': own_status, 'axis': 'delivery', 'shared_status': shared,
            'recorded_at': recorded_at, 'decided_by': 'fixture', 'status': 'accepted',
            'supersedes': supersedes}


def _fixture_tables():
    return {
        'terms': [
            _term('delivery', 'axis', 'The IATI activity status axis.', '2026-01-01'),
            _term('pipeline', 'delivery', 'Not yet started.', '2026-01-01'),
            _term('implementation', 'delivery', 'Under way.', '2026-01-01'),
            _term('named_item', 'line_classification',
                  'A line that names one item.', '2026-01-01'),
            # Reworded on 2026-03-01: same term_id, a new row superseding the first.
            _term('named_item', 'line_classification',
                  'A line whose publisher names the one item it states.', '2026-03-01',
                  row=2, supersedes='line_classification.named_item.1'),
            # Meaning changed on 2026-06-01: a new term_id; the old one stays.
            _term('named_undertaking', 'line_classification',
                  'A line that names one undertaking with an owner and a scope.',
                  '2026-06-01'),
        ],
        'publishers': [{'publisher_id': 'pub-1', 'name': 'Secretariat'}],
        'status_crosswalk': [
            _crosswalk('cw-1', 'A. Planned', 'pipeline', '2026-01-01'),
            _crosswalk('cw-2', 'A. Planned', 'implementation', '2026-06-01',
                       supersedes='cw-1'),
        ],
        'documents': [{'document_id': 'doc-1', 'title': 'Register'}],
        'snapshots': [{'sha256': SHA_A, 'storage_path': 'store/a'}],
        'retrievals': [{'retrieval_id': 'ret-1', 'document_id': 'doc-1',
                        'retrieved_at': '2026-02-01', 'status': 'collected',
                        'sha256': SHA_A}],
        'lines': [{'line_id': 'doc-1-t1-1', 'country': 'ZAF', 'sha256': SHA_A,
                   'locator': 'p1 r1', 'ordinal': '1', 'classification': 'named_item',
                   'recorded_at': '2026-02-01'}],
    }


def _write(ledger_dir, tables):
    schema = ledger_headers.load_schema()
    for table, rows in tables.items():
        path = ledger_headers.table_path(ledger_dir, table)
        path.parent.mkdir(parents=True, exist_ok=True)
        header = schema.header(table)
        with path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.writer(handle, lineterminator='\n')
            writer.writerow(header)
            for row in rows:
                writer.writerow(['' if row.get(c) is None else row[c] for c in header])


def _fixture(tmp_path, tables=None):
    tables = tables or _fixture_tables()
    # The fixture's retrieval and crosswalk statuses must themselves be terms.
    tables['terms'] += [
        _term('collected', 'retrieval_status', 'Bytes came back.', '2026-01-01'),
        _term('accepted', 'decision_status', 'In force when terminal.', '2026-01-01')]
    _write(tmp_path, tables)
    return tmp_path


def _definition(onto, list_name, term_id):
    matches = [t['definition'] for t in onto['terms']
               if t['list'] == list_name and t['term_id'] == term_id]
    assert len(matches) <= 1, matches
    return matches[0] if matches else None


def test_ddl_declares_the_five_ontology_tables_under_ontology(tmp_path):
    schema = ledger_headers.load_schema()
    for table in ontology.ONTOLOGY_TABLES:
        assert table in schema.tables
        assert ledger_headers.table_path(tmp_path, table).parent == tmp_path / 'ontology'
        for column in ('recorded_at', 'decided_by', 'status', 'supersedes'):
            assert column in schema.header(table), (table, column)


def test_the_fixture_is_a_valid_ledger(tmp_path):
    assert ledger_build.build(_fixture(tmp_path), None) == []


def test_a_reworded_definition_is_read_as_of_its_cutoff(tmp_path):
    ledger = _fixture(tmp_path)
    before = ontology.ontology_as_of(ledger, '2026-02-15')
    after = ontology.ontology_as_of(ledger, '2026-03-01')
    assert _definition(before, 'line_classification', 'named_item') == \
        'A line that names one item.'
    assert _definition(after, 'line_classification', 'named_item') == \
        'A line whose publisher names the one item it states.'


def test_a_changed_meaning_mints_a_new_term_and_keeps_the_old(tmp_path):
    ledger = _fixture(tmp_path)
    before = ontology.ontology_as_of(ledger, '2026-05-31')
    after = ontology.ontology_as_of(ledger, '2026-06-01')
    assert _definition(before, 'line_classification', 'named_undertaking') is None
    assert _definition(after, 'line_classification', 'named_undertaking')
    assert _definition(after, 'line_classification', 'named_item')
    # The line that cited the old term stays valid after the new one is minted.
    assert ledger_build.build(ledger, None) == []


def test_a_remapped_crosswalk_does_not_move_an_earlier_shared_status(tmp_path):
    ledger = _fixture(tmp_path)
    early = ontology.ontology_as_of(ledger, '2026-03-01')
    late = ontology.ontology_as_of(ledger, '2026-07-01')
    assert ontology.shared_status(early, 'pub-1', 'A. Planned') == ('delivery', 'pipeline')
    assert ontology.shared_status(late, 'pub-1', 'A. Planned') == \
        ('delivery', 'implementation')
    assert ontology.shared_status(ontology.ontology_as_of(ledger, '2025-12-31'),
                                  'pub-1', 'A. Planned') is None


def test_a_row_recorded_on_the_cutoff_day_is_in_the_as_of_state(tmp_path):
    tables = _fixture_tables()
    tables['status_crosswalk'][1]['recorded_at'] = '2026-06-01T10:00Z'
    ledger = _fixture(tmp_path, tables)
    onto = ontology.ontology_as_of(ledger, '2026-06-01')
    assert ontology.shared_status(onto, 'pub-1', 'A. Planned') == \
        ('delivery', 'implementation')


def test_python_in_force_rule_matches_the_ddl_views(tmp_path):
    import sqlite3
    ledger = _fixture(tmp_path)
    output = tmp_path / 'ledger.sqlite'
    assert ledger_build.build(ledger, output) == []
    current = ontology.ontology_as_of(ledger)
    schema = ledger_headers.load_schema()
    conn = sqlite3.connect(output)
    try:
        for table in ontology.ONTOLOGY_TABLES:
            key = schema.keys[table][0]
            in_sql = {row[0] for row in conn.execute(
                f'SELECT "{key}" FROM "{table}_in_force"')}
            assert in_sql == {row[key] for row in current[table]}, table
    finally:
        conn.close()


@pytest.mark.parametrize('breakage, needle', [
    (lambda t: t['status_crosswalk'][1].update(shared_status='operating'),
     "shared_status = 'operating'"),
    (lambda t: t['terms'][4].update(term_id='named_thing'),
     'chain'),
    (lambda t: t['terms'].append(_term('pipeline', 'delivery', 'Twice.', '2026-02-01',
                                       row=9)),
     'more than one row in force'),
    # A revision recorded before the row it supersedes (2026-03-01 -> 2025-12-01).
    (lambda t: t['terms'][4].update(recorded_at='2025-12-01'),
     'terms line_classification.named_item.2: recorded_at 2025-12-01 is before '
     'that of the row it supersedes, line_classification.named_item.1'),
    (lambda t: t['lines'][0].update(classification='programme'),
     "lines.classification = 'programme'"),
])
def test_ontology_breakages_are_named(tmp_path, breakage, needle):
    tables = _fixture_tables()
    breakage(tables)
    errors = ledger_build.build(_fixture(tmp_path, tables), None)
    assert errors and any(needle in e for e in errors), errors


# --- ontology_ref -------------------------------------------------------------

def test_ontology_ref_is_stable_and_moves_with_its_inputs(tmp_path):
    ledger = _fixture(tmp_path)
    first = ontology.ontology_ref(ledger)
    assert first == ontology.ontology_ref(ledger)
    assert first.startswith('sha256:') and len(first) == len('sha256:') + 64
    terms = ledger_headers.table_path(ledger, 'terms')
    terms.write_text(terms.read_text(encoding='utf-8') + '\n', encoding='utf-8')
    assert ontology.ontology_ref(ledger) != first


def test_ontology_ref_covers_the_ddl(tmp_path):
    ledger = _fixture(tmp_path)
    ddl = tmp_path / 'other.sql'
    ddl.write_text(ledger_headers.DDL_PATH.read_text(encoding='utf-8') + '\n-- x\n',
                   encoding='utf-8')
    assert ontology.ontology_ref(ledger, ddl) != ontology.ontology_ref(ledger)


# --- The real terms -----------------------------------------------------------

@pytest.fixture(scope='module')
def terms():
    return ontology.ontology_as_of(ledger_headers.LEDGER_DIR)['terms']


def _in_list(terms, list_name):
    return {t['term_id'] for t in terms if t['list'] == list_name}


def test_the_real_ledger_is_valid():
    assert ledger_build.build(ledger_headers.LEDGER_DIR, None) == []


def test_every_term_in_force_has_a_definition(terms):
    assert terms
    assert [t['term_row_id'] for t in terms if not (t['definition'] or '').strip()] == []


def test_terms_describe_themselves_in_their_own_lists(terms):
    """kind, status and mapping_relation of terms are terms (checked here, not in the DDL)."""
    for column, list_name in (('kind', 'term_kind'), ('status', 'decision_status'),
                              ('mapping_relation', 'mapping_relation')):
        allowed = _in_list(terms, list_name)
        assert allowed, list_name
        assert {t[column] for t in terms} <= allowed, column


def _checked_lists():
    """List names of violation_closed_list, read from its (tbl, col, list, value) rows."""
    ddl = ledger_headers.DDL_PATH.read_text(encoding='utf-8')
    return set(re.findall(r"SELECT '\w+', '\w+', '(\w+)',", ddl))


def test_every_closed_list_the_ddl_checks_has_terms(terms):
    checked = _checked_lists()
    assert checked
    assert sorted(name for name in checked if not _in_list(terms, name)) == []


def test_the_legacy_kind_list_is_renamed_class(terms):
    """0871 named its typed-reference list `kind`, which reads as terms.kind; it is `class`."""
    assert 'kind' not in _checked_lists()
    assert {'line', 'project', 'asset', 'agreement', 'party', 'perimeter',
            'observation'} <= _in_list(terms, 'class')


# --- Alignment: specification <-> terms <-> DDL ----------------------------------

def _sections(text, first, last):
    """The text of sections ``first`` to ``last`` (level-2 headings ``## N.``)."""
    starts = {int(m.group(1)): m.start() for m in re.finditer(r'^## (\d+)\.', text, re.M)}
    end = starts.get(last + 1, len(text))
    return text[starts[first]:end]


# A value in code type: a lowercase word, a modality code (A01) or an ISO 3166
# alpha-3 country code (ZAF). The other uppercase tokens of sections 2 to 4 are
# deliberately left out: publisher words (`A. Planned` splits into `A.` and
# `Planned`) and a foreign schema's field name (OC4IDS `projectStatus`).
CODE_VALUE = re.compile(r'^(?:[a-z][a-z0-9_]*|[A-F]\d{2}|[A-Z]{3})$')


def spec_values(text):
    """Values the specification writes in code type in sections 2 to 4."""
    found = set()
    for span in re.findall(r'`([^`\n]+)`', _sections(text, 2, 4)):
        for token in re.split(r'[\s,()]+', span):
            if CODE_VALUE.match(token):
                found.add(token)
    return found


def unlisted_values(text, terms, schema):
    names = set(schema.tables)
    for columns in schema.tables.values():
        names |= set(columns)
    known = {t['term_id'] for t in terms} | names | PUBLISHER_FIELD_NAMES
    return sorted(v for v in spec_values(text) if v not in known)


def _list_block(text, anchor):
    """Code spans of the paragraph that follows ``anchor``."""
    start = text.index(anchor) + len(anchor)
    return re.findall(r'`([^`]+)`', text[start:text.index('\n\n', start + 2)])


def test_every_value_in_sections_2_to_4_is_a_term_in_force(terms):
    text = ONTOLOGY_DOC.read_text(encoding='utf-8')
    assert unlisted_values(text, terms, ledger_headers.load_schema()) == []


def test_the_alignment_check_fails_on_a_new_value_without_a_term(terms):
    text = ONTOLOGY_DOC.read_text(encoding='utf-8')
    anchor = '`named_item`, `unnamed_item`'
    assert anchor in text
    grown = text.replace(anchor, '`named_item`, `pooled_item`, `unnamed_item`')
    assert unlisted_values(grown, terms, ledger_headers.load_schema()) == ['pooled_item']


def test_the_alignment_check_sees_country_codes(terms):
    """Uppercase codes count: dropping the ZAF term leaves the spec's `ZAF` unlisted."""
    text = ONTOLOGY_DOC.read_text(encoding='utf-8')
    assert '`ZAF`' in _sections(text, 2, 4)
    without = [t for t in terms if not (t['list'] == 'country' and t['term_id'] == 'ZAF')]
    assert len(without) == len(terms) - 1
    assert unlisted_values(text, without, ledger_headers.load_schema()) == ['ZAF']


def test_the_line_classification_list_is_the_terms_list(terms):
    text = ONTOLOGY_DOC.read_text(encoding='utf-8')
    listed = set(_list_block(text, 'from a closed list:\n\n'))
    assert listed == _in_list(terms, 'line_classification')


def test_the_relation_table_is_the_terms_list(terms):
    section = _sections(ONTOLOGY_DOC.read_text(encoding='utf-8'), 3, 3)
    listed = set(re.findall(r'^\| `(\w+)`', section, re.M))
    assert listed == _in_list(terms, 'relation')
    relations = [t for t in terms if t['kind'] == 'relation']
    assert relations and all(t['domain'] and t['range'] for t in relations)


def _spec_text():
    return (ONTOLOGY_DOC.read_text(encoding='utf-8') + '\n'
            + STORAGE_DOC.read_text(encoding='utf-8'))


def _code_tokens(text):
    tokens = set()
    for span in re.findall(r'`([^`\n]+)`', text):
        tokens |= set(re.split(r'[\s,()]+', span))
    return tokens


def missing_terms(text, terms):
    """Terms in force the specification never mentions.

    A value must appear in code type, as the specification writes values; a
    class or a relation may appear by its label, as a heading or in prose.
    """
    code, lower = _code_tokens(text), text.lower()
    missing = []
    for term in terms:
        if term['kind'] == 'value':
            found = term['term_id'] in code
        else:
            found = any(form in lower for form in (
                term['term_id'].lower(), term['label'].lower(),
                term['term_id'].replace('_', ' ').lower()))
        if not found:
            missing.append(f"{term['list']}.{term['term_id']}")
    return missing


def test_every_term_in_force_appears_in_the_specification(terms):
    assert missing_terms(_spec_text(), terms) == []


def test_the_reverse_check_fails_on_a_term_the_specification_dropped(terms):
    text = _spec_text()
    assert '`quarter`, ' in text
    assert missing_terms(text.replace('`quarter`, ', ''), terms) == ['date_precision.quarter']


def _contract_tables():
    """Tables and their columns as the two contract tables declare them."""
    rows = {}
    for path, section in ((STORAGE_DOC, 1), (ONTOLOGY_DOC, 5)):
        text = _sections(path.read_text(encoding='utf-8'), section, section)
        for name, key, columns in re.findall(
                r'^\| `([\w-]+)` \| ([^|]+) \| ([^|]*) \|$', text, re.M):
            if 'as today' in key or '<' in name:
                continue
            rows[name.replace('-', '_')] = _columns(key, columns)
    return rows


def _columns(key, columns):
    """Key columns, then the others; a chain key in italics is a tuple of columns."""
    names = [k.strip() for k in key.replace('`', '').strip().strip('()').split(',')]
    columns = columns.replace('*', '')
    # A parenthesised tuple of names is columns; any other parenthesis is a note.
    columns = re.sub(r'\(((?:\w+, )+\w+)\)', r'\1', columns)
    columns = re.sub(r'\s*\([^)]*\)', '', columns)
    return names + [c.strip() for c in columns.split(',') if c.strip()]


def test_contract_tables_and_columns_are_the_ddl():
    schema = ledger_headers.load_schema()
    contract = _contract_tables()
    assert set(contract) == set(schema.tables)
    for table, columns in contract.items():
        assert columns == schema.header(table), table


def test_the_ddl_uses_no_retired_word():
    schema = ledger_headers.load_schema()
    names = set(schema.tables) | {c for cols in schema.tables.values() for c in cols}
    assert sorted(n for n in names if RETIRED_WORD.search(n)) == []
