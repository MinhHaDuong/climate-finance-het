"""The South African JET Grants Register parser (ticket 1950, extraction 6.1).

Fixtures are drawn from the real snapshots (``tests/fixtures/jetp/
zaf_grants_register/*.json``, each naming its source pages and the one
adaptation it carries) and rendered at test time: the workbook model as an
XLSX package, the PDF models as PDFs with the same words at the same places
and the same full-width rules. Each red test replays a defect of extraction
section 12 on that fixture and expects the whole document to fail.
"""

import copy
import csv
import json
import zipfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import pytest
from jetp import _pdf_ruled_table as ruled
from jetp import _xlsx_cells as xlsx
from jetp import _zaf_grants_layouts as layouts
from jetp import build_zaf_grants_register as grants
from jetp._ledger_headers import LEDGER_DIR, load_schema, read_table

pytestmark = pytest.mark.domain_jetp

FIXTURES = Path(__file__).parent / 'fixtures' / 'jetp' / 'zaf_grants_register'
DATE_COLUMNS = ('Date of Financing Agreement Signed*', 'End Date')


def _model(name):
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


# --- rendering the fixtures ---------------------------------------------------

def write_xlsx(model, path):
    """A minimal workbook: inline strings, numbers, dates as styled serials."""
    sheets = model['sheets']
    headers = {}
    for sheet in sheets:
        for row in sheet['rows']:
            for col, value in row['cells'].items():
                if value in DATE_COLUMNS:
                    headers[(sheet['name'], col)] = value
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<Types/>')
        epoch = date(1904, 1, 1) if model.get('date1904') else date(1899, 12, 30)
        properties = '<workbookPr date1904="1"/>' if model.get('date1904') else ''
        archive.writestr('xl/workbook.xml', (
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            + properties + '<sheets>' + ''.join(
                f'<sheet name="{escape(s["name"])}" sheetId="{i}" r:id="rId{i}"'
                + ('' if s['state'] == 'visible' else f' state="{s["state"]}"') + '/>'
                for i, s in enumerate(sheets, 1)) + '</sheets></workbook>'))
        archive.writestr('xl/_rels/workbook.xml.rels', (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + ''.join(f'<Relationship Id="rId{i}" Target="worksheets/sheet{i}.xml"/>'
                      for i in range(1, len(sheets) + 1)) + '</Relationships>'))
        archive.writestr('xl/styles.xml', (
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<cellXfs><xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>'))
        for i, sheet in enumerate(sheets, 1):
            rows = []
            for row in sheet['rows']:
                cells = []
                for col, value in row['cells'].items():
                    ref = f'{col}{row["r"]}'
                    dated = (sheet['name'], col) in headers and \
                        len(value) == 10 and value[4] == '-'
                    if dated:
                        serial = (date.fromisoformat(value) - epoch).days
                        cells.append(f'<c r="{ref}" s="1"><v>{serial}</v></c>')
                    elif _is_number(value):
                        cells.append(f'<c r="{ref}"><v>{value}</v></c>')
                    else:
                        cells.append(f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">'
                                     f'{escape(value)}</t></is></c>')
                hidden = ' hidden="1"' if row['hidden'] else ''
                rows.append(f'<row r="{row["r"]}"{hidden}>{"".join(cells)}</row>')
            cols = ''.join(f'<col min="{_index(c)}" max="{_index(c)}" hidden="1"/>'
                           for c in sheet.get('hidden_columns', ()))
            archive.writestr(f'xl/worksheets/sheet{i}.xml', (
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                + (f'<cols>{cols}</cols>' if cols else '')
                + f'<sheetData>{"".join(rows)}</sheetData></worksheet>'))
    return path


def _index(letters):
    return xlsx.column_index(letters)


def _letters(index):
    letters = ''
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def _is_number(value):
    try:
        float(value)
    except ValueError:
        return False
    return True


def write_pdf(model, path, shift=0.0):
    """The model's words at their places, its rules as lines, in a core font."""
    fpdf = pytest.importorskip('fpdf')
    pdf = fpdf.FPDF(unit='pt')
    pdf.set_auto_page_break(False)
    pdf.set_line_width(0.5)
    for page in model['pages']:
        pdf.add_page(format=(page['width'], page['height']))
        for y, left, right in page['rules']:
            pdf.line(left + shift, y, right + shift, y)
        for text, x0, top, width, height in page['words']:
            pdf.set_font('helvetica', size=max(height, 1.0))
            pdf.set_stretching(100)
            natural = pdf.get_string_width(text) or width
            pdf.set_stretching(100 * width / natural)
            pdf.text(x0 + shift, top + height * 0.8, text + ' ')   # the space ends the word
    pdf.output(str(path))
    return path


def _pdf_pages(model, tmp_path, shift=0.0):
    return ruled.read_pdf(write_pdf(model, tmp_path / 'fixture.pdf', shift))


# --- the XLSX text layer ------------------------------------------------------

def test_xlsx_reader_keeps_stored_values_hidden_flags_and_dates(tmp_path):
    model = {'sheets': [
        {'name': 'Sheet ', 'state': 'visible', 'rows': [
            {'r': 1, 'hidden': False, 'cells': {'A': 'End Date', 'B': 'Total US$'}},
            {'r': 3, 'hidden': True, 'cells': {'A': '2024-12-31', 'B': '7560000.0000000009'}}]},
        {'name': 'Lists', 'state': 'hidden', 'rows': [
            {'r': 1, 'hidden': False, 'cells': {'A': 'A. Planned '}}]}]}
    model['sheets'][0]['hidden_columns'] = ['B']
    sheets = xlsx.read_workbook(write_xlsx(model, tmp_path / 'w.xlsx'))
    assert [(s.name, s.state) for s in sheets] == [('Sheet ', 'visible'), ('Lists', 'hidden')]
    assert sheets[1].hidden and sheets[0].hidden_columns == {'B'}
    row = sheets[0].rows[1]
    assert row.hidden
    assert row.cells == {'A': '2024-12-31', 'B': '7560000.0000000009'}
    assert sheets[1].rows[0].cells == {'A': 'A. Planned '}


def test_xlsx_reader_honours_the_1904_date_system(tmp_path):
    model = {'date1904': True, 'sheets': [{'name': 'S', 'state': 'visible', 'rows': [
        {'r': 1, 'hidden': False, 'cells': {'A': 'End Date'}},
        {'r': 2, 'hidden': False, 'cells': {'A': '2024-12-31'}}]}]}
    sheets = xlsx.read_workbook(write_xlsx(model, tmp_path / 'w.xlsx'))
    assert sheets[0].rows[1].cells == {'A': '2024-12-31'}


@pytest.mark.parametrize('code, shows_date', [
    ('yyyy-mm-dd', True), ('[$-409]d-mmm-yy;@', True), ('dd/mm/yyyy h:mm AM/PM', True),
    ('General', False), ('Standard', False), ('#,##0.00', False), ('"Q"0', False)])
def test_xlsx_reader_tells_date_formats_from_others(code, shows_date):
    assert xlsx._is_date_format(code) is shows_date


def test_xlsx_reader_turns_corrupt_bytes_into_an_error_not_a_crash(tmp_path):
    bad = tmp_path / 'bad.xlsx'
    bad.write_bytes(b'not a zip')
    with pytest.raises(xlsx.XlsxError):
        xlsx.read_workbook(bad)


# --- workbook editions (2024 Q3, 2025 Q1) ---------------------------------------

def test_workbook_fixture_reads_every_grant_with_its_printed_headers(tmp_path):
    model = _model('xlsx-2025-q1.json')
    items, controls, counts, out = layouts.parse_xlsx(write_xlsx(model, tmp_path / 'w.xlsx'))
    assert counts == {'overall': 8, 'eu-register': 8}
    assert set(out) == {'sheet "Dropdowns"', 'sheet "Financing Status"'}
    rows = [i for i in items if i.classification == 'register_allocation']
    eu001 = next(i for i in rows if i.table == 'eu-register' and i.fields['Unique ID'] == 'EU001')
    source = next(r for s in model['sheets'] if s['name'] == 'EU-Register'
                  for r in s['rows'] if r['cells'].get('A') == 'EU001')
    assert eu001.locator == f'sheet "EU-Register", row {source["r"]}'
    assert eu001.fields['Euro - Amount'] == source['cells']['E']
    assert eu001.fields['Date of Financing Agreement Signed*'] == source['cells']['M']
    assert eu001.own_status == source['cells']['K'].strip()
    headings = [i for i in items if i.classification == 'heading']
    assert any('ZAR' in h.label for h in headings)          # the exchange-rate note
    assert any(h.label.startswith('Footnote 1') for h in headings)
    assert all(i.heading for i in rows)                       # every row names its note
    assert any('Euro - Amount sum of 8 rows' in c for c in controls)
    header = next(r for s in model['sheets'] if s['name'] == 'EU-Register'
                  for r in s['rows'] if r['cells'].get('A') == 'Unique ID')
    printed = [' '.join(v.split()) for _, v in sorted(header['cells'].items(),
                                                      key=lambda kv: xlsx.column_index(kv[0]))]
    assert [f for f in printed if f in eu001.fields] == list(eu001.fields)


def test_workbook_marks_rows_read_from_hidden_places(tmp_path):
    model = _model('xlsx-2025-q1.json')
    eu = _sheet(model, 'EU-Register')
    eu['hidden_columns'] = ['L']
    next(r for r in eu['rows'] if r['cells'].get('A') == 'EU002')['hidden'] = True
    items, _, _, _ = layouts.parse_xlsx(write_xlsx(model, tmp_path / 'w.xlsx'))
    notes = {i.fields['Unique ID']: i.note for i in items
             if i.table == 'eu-register' and i.classification != 'heading'}
    assert notes['EU002'] == 'hidden row; hidden column(s): Description'
    assert notes['EU001'] == 'hidden column(s): Description'


def test_workbook_red_undeclared_amount_header(tmp_path):
    model = _model('xlsx-2025-q1.json')
    header = next(r for r in _sheet(model, 'EU-Register')['rows']
                  if r['cells'].get('A') == 'Unique ID')
    header['cells']['E'] = 'Yen - Amount'
    with pytest.raises(grants.RegisterError, match='not declared for a total control'):
        layouts.parse_xlsx(write_xlsx(model, tmp_path / 'w.xlsx'))


@pytest.mark.parametrize('header', ['Yen - Amount', 'Funding USD', 'Sum', 'EUR'])
def test_workbook_red_money_headers_without_a_total_control(tmp_path, header):
    model = _model('xlsx-2025-q1.json')
    row = next(r for r in _sheet(model, 'EU-Register')['rows']
               if r['cells'].get('A') == 'Unique ID')
    row['cells']['E'] = header
    with pytest.raises(grants.RegisterError, match='not declared for a total control'):
        layouts.parse_xlsx(write_xlsx(model, tmp_path / 'w.xlsx'))


def test_admission_rerun_restores_a_spec_row_a_crash_lost(tmp_path):
    ledger = tmp_path / 'ledger'
    ledger.mkdir()
    extraction = _fixture_extraction(tmp_path)
    grants.admit([extraction], ledger, recorded_at='2026-10-01')
    specs = ledger / 'line-field-specs.csv'
    complete = specs.read_bytes()
    specs.write_text(specs.read_text().splitlines()[0] + '\n')   # header only
    assert grants.admit([extraction], ledger, recorded_at='2026-10-02') == {
        extraction.document_id: 0}
    assert specs.read_bytes() == complete


def test_admission_renders_every_file_before_writing_any(tmp_path, monkeypatch):
    ledger = tmp_path / 'ledger'
    ledger.mkdir()
    first = _fixture_extraction(tmp_path)
    second = copy.deepcopy(first)
    second.document_id, second.sha256 = 'zaf-jet-grants-register-2024-q3', 'e' * 64
    monkeypatch.setattr(grants, 'file_ceiling', lambda: 60_000)
    second.items[3].fields['Description'] = 'x' * 70_000
    with pytest.raises(grants.RegisterError, match='ceiling'):
        grants.admit([first, second], ledger, recorded_at='2026-10-01')
    assert not list(ledger.rglob('*.csv'))


def test_xlsx_reader_refuses_a_date_serial_that_is_no_date(tmp_path):
    model = {'sheets': [{'name': 'S', 'state': 'visible', 'rows': [
        {'r': 1, 'hidden': False, 'cells': {'A': 'End Date'}},
        {'r': 2, 'hidden': False, 'cells': {'A': '2024-12-31'}}]}]}
    path = write_xlsx(model, tmp_path / 'w.xlsx')
    with zipfile.ZipFile(path) as archive:
        parts = {n: archive.read(n) for n in archive.namelist()}
    parts['xl/worksheets/sheet1.xml'] = parts['xl/worksheets/sheet1.xml'].replace(
        b'<v>45657</v>', b'<v>1e30</v>')
    with zipfile.ZipFile(path, 'w') as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    with pytest.raises(xlsx.XlsxError, match='not a date'):
        xlsx.read_workbook(path)


def test_workbook_red_grant_identifier_under_the_total(tmp_path):
    model = _model('xlsx-2025-q1.json')
    rows = _sheet(model, 'EU-Register')['rows']
    rows.append({'r': rows[-1]['r'] + 2, 'hidden': False, 'cells': {'A': 'EU009'}})
    with pytest.raises(grants.RegisterError, match='neither a grant'):
        layouts.parse_xlsx(write_xlsx(model, tmp_path / 'w.xlsx'))


def _sheet(model, name):
    return next(s for s in model['sheets'] if s['name'].strip() == name)


def test_workbook_red_shifted_grid(tmp_path):
    model = _model('xlsx-2025-q1.json')
    for row in _sheet(model, 'EU-Register')['rows']:
        row['cells'] = {_letters(xlsx.column_index(c) + 1): v
                        for c, v in row['cells'].items()}
    with pytest.raises(grants.RegisterError, match='landmark absent'):
        layouts.parse_xlsx(write_xlsx(model, tmp_path / 'w.xlsx'))


def test_workbook_red_missing_sheet(tmp_path):
    model = _model('xlsx-2025-q1.json')
    model['sheets'] = [s for s in model['sheets'] if s['name'] != 'EU-Register']
    with pytest.raises(grants.RegisterError, match='list different grants'):
        layouts.parse_xlsx(write_xlsx(model, tmp_path / 'w.xlsx'))


def test_workbook_red_duplicated_row(tmp_path):
    model = _model('xlsx-2025-q1.json')
    rows = _sheet(model, 'EU-Register')['rows']
    first = next(i for i, r in enumerate(rows) if r['cells'].get('A') == 'EU001')
    for row in rows[first + 1:]:
        row['r'] += 1
    copy_row = copy.deepcopy(rows[first])
    copy_row['r'] += 1
    rows.insert(first + 1, copy_row)
    with pytest.raises(grants.RegisterError, match='printed twice'):
        layouts.parse_xlsx(write_xlsx(model, tmp_path / 'w.xlsx'))


def test_workbook_red_total_disagrees(tmp_path):
    model = _model('xlsx-2025-q1.json')
    total = next(r for r in _sheet(model, 'EU-Register')['rows']
                 if 'A' not in r['cells'] and 'D' in r['cells'] and 'E' in r['cells']
                 and r['r'] > 3)
    total['cells']['D'] = str(float(total['cells']['D']) + 1000)
    with pytest.raises(grants.RegisterError, match='printed total'):
        layouts.parse_xlsx(write_xlsx(model, tmp_path / 'w.xlsx'))


def test_workbook_red_undeclared_sheet(tmp_path):
    model = _model('xlsx-2025-q1.json')
    model['sheets'].append({'name': 'Notes', 'state': 'visible', 'rows': []})
    with pytest.raises(grants.RegisterError, match='neither a declared table'):
        layouts.parse_xlsx(write_xlsx(model, tmp_path / 'w.xlsx'))


# --- 2023 Q3 PDF ----------------------------------------------------------------

def test_2023_fixture_reads_rows_and_mends_the_page_break(tmp_path):
    model = _model('pdf-2023-q3.json')
    items, controls, counts, _ = layouts.parse_pdf_2023(_pdf_pages(model, tmp_path))
    rows = [i for i in items if i.classification == 'register_allocation']
    assert counts == {'register': len(rows)}
    assert len(rows) == 6 + 6 + 5
    spanning = [i for i in rows if i.locator.startswith('pages 2-3')]
    assert len(spanning) == 1                     # one statement over the page break
    page3 = model['pages'][2]
    carried = [w[0] for w in page3['words'] if page3['rules'][0][0] < w[2] < page3['rules'][1][0]]
    assert carried                                 # the continuation band holds text
    merged = ' '.join(spanning[0].fields.values())
    assert all(word in merged for word in carried)
    first = rows[0]
    assert first.locator == 'page 1, table 1, row 1'
    assert first.fields['Funder'] == 'EU' and first.fields['Total US$'] == '$162 000'
    assert first.own_sector == 'Electricity infrastructure'
    title, rate = [i for i in items if i.classification == 'heading']
    assert rate.label == 'USD to ZAR 17,05' and rate.heading == title.locator
    assert all(i.heading == rate.locator for i in rows)
    assert any(c.startswith('register: Total US$ sum of 17 rows') for c in controls)


def test_2023_red_shifted_grid(tmp_path):
    with pytest.raises(grants.RegisterError, match='landmark absent'):
        layouts.parse_pdf_2023(_pdf_pages(_model('pdf-2023-q3.json'), tmp_path, shift=40))


def test_2023_red_missing_page(tmp_path):
    model = _model('pdf-2023-q3.json')
    del model['pages'][1]
    with pytest.raises(grants.RegisterError, match='printed total'):
        layouts.parse_pdf_2023(_pdf_pages(model, tmp_path))


def test_2023_red_duplicated_rows(tmp_path):
    model = _model('pdf-2023-q3.json')
    model['pages'].insert(1, copy.deepcopy(model['pages'][1]))
    with pytest.raises(grants.RegisterError, match='printed total'):
        layouts.parse_pdf_2023(_pdf_pages(model, tmp_path))


def test_2023_red_total_disagrees(tmp_path):
    model = _model('pdf-2023-q3.json')
    last = model['pages'][-1]
    total_top = last['rules'][-2][0] + 4
    word = next(w for w in last['words'] if w[0].startswith('$') and w[2] == total_top)
    word[0] = '$151'                     # one figure of the total altered
    with pytest.raises(grants.RegisterError, match='printed total'):
        layouts.parse_pdf_2023(_pdf_pages(model, tmp_path))


# --- 2024 Q1-Q2 PDF -------------------------------------------------------------

def test_2024_fixture_reads_a_register_with_its_total_and_footnotes(tmp_path):
    pages = _pdf_pages(_model('pdf-2024-q2.json'), tmp_path)
    items, controls, counts, _ = layouts.parse_pdf_2024(pages, titles=('ACTIP-REGISTER',))
    assert counts == {'actip-register': 2}
    rows = [i for i in items if i.classification == 'register_allocation']
    assert [r.fields['Unique ID'] for r in rows] == ['ACTIP001', 'ACTIP002']
    assert rows[1].fields['Total US$'] == '$ 47,720,000'
    assert rows[1].fields['Status'] == 'B. Pledged'
    notes = [i for i in items if i.classification == 'heading']
    assert notes[0].label.startswith('ACTIP-REGISTER')
    assert any(n.label.startswith('Footnote 2') for n in notes)
    assert any('Total US$ sum of 2 rows' in c for c in controls)


def test_2024_red_total_disagrees(tmp_path):
    model = _model('pdf-2024-q2.json')
    page = model['pages'][0]
    word = next(w for w in page['words'] if w[0] == '50,000,000')
    word[0] = '51,000,000'
    with pytest.raises(grants.RegisterError, match='printed total'):
        layouts.parse_pdf_2024(_pdf_pages(model, tmp_path), titles=('ACTIP-REGISTER',))


def test_2024_red_declared_truncation_that_prints_a_total(tmp_path):
    pages = _pdf_pages(_model('pdf-2024-q2.json'), tmp_path)
    truncated = {'actip-register': {'reason': 'review', 'not_printed': set()}}
    with pytest.raises(grants.RegisterError, match='declared truncated'):
        layouts.parse_pdf_2024(pages, titles=('ACTIP-REGISTER',), truncated=truncated)


def test_2024_red_declared_illegible_total_that_prints_a_figure(tmp_path):
    pages = _pdf_pages(_model('pdf-2024-q2.json'), tmp_path)
    with pytest.raises(grants.RegisterError, match='declared illegible'):
        layouts.parse_pdf_2024(pages, titles=('ACTIP-REGISTER',),
                               illegible={('actip-register', 'Total ZAR')})


def test_2024_red_header_landmark_absent(tmp_path):
    model = _model('pdf-2024-q2.json')
    for word in model['pages'][0]['words']:
        if word[0] == 'Beneficiaries':
            word[0] = 'Recipients'
    with pytest.raises(grants.RegisterError, match='landmark absent'):
        layouts.parse_pdf_2024(_pdf_pages(model, tmp_path), titles=('ACTIP-REGISTER',))


# --- controls ---------------------------------------------------------------------

@pytest.mark.parametrize('text, value', [
    ('$ 162,000', 162000.0), ('$162 000', 162000.0), ('R 2,847,960', 2847960.0), ('R0', 0.0),
    ('139,646,000 kr.', 139646000.0), ('-1,000', -1000.0), ('CHF 1,000,000', 1000000.0),
    ('7560000.0000000009', 7560000.0000000009), ('-', None), ('##############', None)])
def test_amount_reads_one_printed_number(text, value):
    assert layouts.amount(text) == value


@pytest.mark.parametrize('text', ['ZAR 1,000 (approx 50 USD)', '1,000 and 2,000', '1.2.3',
                                  '1.000'])
def test_amount_refuses_what_is_not_one_number(text):
    with pytest.raises(grants.RegisterError, match='not one number'):
        layouts.amount(text)


def test_union_red_undeclared_difference_and_wrong_truncation():
    tables = {'overall': {'UK001', 'UK002', 'EU001'}, 'uk-register': {'UK001'},
              'eu-register': {'EU001'}}
    with pytest.raises(grants.RegisterError, match='list different grants'):
        layouts.check_overall_union(tables, [])
    truncated = {'uk-register': {'reason': 'review', 'not_printed': {'UK002'}}}
    controls = []
    layouts.check_overall_union(tables, controls, truncated)
    assert 'not printed in a truncated register' in controls[-1]
    truncated['uk-register']['not_printed'] = {'UK003'}
    with pytest.raises(grants.RegisterError, match='declared not printed'):
        layouts.check_overall_union(tables, [], truncated)
    declared = {'only_overall': {'UK002'}, 'only_registers': set()}
    layouts.check_overall_union(tables, controls, declared=declared)
    assert "publisher's own difference" in controls[-1]
    for wrong in ({'only_overall': {'UK002', 'UK009'}, 'only_registers': set()},   # superset
                  {'only_overall': set(), 'only_registers': set()}):                # subset
        with pytest.raises(grants.RegisterError, match='list different grants'):
            layouts.check_overall_union(tables, [], declared=wrong)


# --- one document, admission ------------------------------------------------------

def test_extract_refuses_bytes_it_was_not_written_for(tmp_path):
    path = write_xlsx(_model('xlsx-2025-q1.json'), tmp_path / 'w.xlsx')
    with pytest.raises(grants.RegisterError, match='not the snapshot'):
        grants.extract('zaf-jet-grants-register-2025-q1', path)
    with pytest.raises(grants.RegisterError, match='not an edition'):
        grants.extract('zaf-jet-investment-register-q1-2026', path)


def test_extract_red_row_count_differs_from_the_reviewed_one(tmp_path, monkeypatch):
    path = write_xlsx(_model('xlsx-2025-q1.json'), tmp_path / 'w.xlsx')
    edition = grants.Edition('fixture', grants.sha256_of(path), 'xlsx',
                             {'overall': 8, 'eu-register': 8})
    monkeypatch.setitem(grants.EDITIONS, 'fixture', edition)
    assert grants.extract('fixture', path).counts == edition.rows
    monkeypatch.setitem(grants.EDITIONS, 'fixture', grants.Edition(
        'fixture', edition.sha256, 'xlsx', {'overall': 8, 'eu-register': 9}))
    with pytest.raises(grants.RegisterError, match='reviewed'):
        grants.extract('fixture', path)


def _fixture_extraction(tmp_path):
    items, controls, counts, out = layouts.parse_xlsx(
        write_xlsx(_model('xlsx-2025-q1.json'), tmp_path / 'w.xlsx'))
    return grants.Extraction('zaf-jet-grants-register-2025-q1', 'f' * 64, 'fixture v1',
                             items, controls, counts, out)


def test_admission_mints_lines_once_and_replays_without_change(tmp_path):
    ledger = tmp_path / 'ledger'
    ledger.mkdir()
    extraction = _fixture_extraction(tmp_path)
    assert grants.admit([extraction], ledger, recorded_at='2026-10-01') == {
        'zaf-jet-grants-register-2025-q1': len(extraction.items)}
    schema = load_schema()
    lines, errors = read_table(ledger, 'lines', schema)
    assert not errors
    header = schema.header('lines')
    records = [dict(zip(header, row)) for row in lines]
    ids = [r['line_id'] for r in records]
    assert ids[0] == 'zaf-jet-grants-register-2025-q1-overall-1'
    assert len(set(ids)) == len(ids) == len(extraction.items)
    assert {r['classification'] for r in records} == {'heading', 'register_allocation'}
    assert all(r['notes'].startswith('method zaf-grants-register-parser v1') for r in records)
    by_id = {r['line_id']: r for r in records}
    assert all(by_id[r['groups']]['classification'] == 'heading'
               for r in records if r['groups'])
    with (ledger / 'line-fields' / 'zaf-jet-grants-register-2025-q1.csv').open() as handle:
        fields = list(csv.DictReader(handle))
    assert len(fields) == sum(1 for r in records if r['classification'] != 'heading')
    snapshot = sorted(p.read_bytes() for p in ledger.rglob('*.csv'))
    assert grants.admit([extraction], ledger, recorded_at='2026-10-02') == {
        'zaf-jet-grants-register-2025-q1': 0}
    assert sorted(p.read_bytes() for p in ledger.rglob('*.csv')) == snapshot
    changed = copy.deepcopy(extraction)
    changed.items[3].fields['Total US$'] = '1'
    changed.items[3].label = 'altered'
    with pytest.raises(grants.RegisterError, match='replay differs'):
        grants.admit([changed], ledger, recorded_at='2026-10-02')


def test_admission_writes_nothing_when_one_replay_of_the_batch_fails(tmp_path):
    ledger = tmp_path / 'ledger'
    ledger.mkdir()
    first = _fixture_extraction(tmp_path)
    grants.admit([first], ledger, recorded_at='2026-10-01')
    before = sorted((p.name, p.read_bytes()) for p in ledger.rglob('*.csv'))
    other = copy.deepcopy(first)
    other.document_id, other.sha256 = 'zaf-jet-grants-register-2024-q3', 'e' * 64
    changed = copy.deepcopy(first)
    changed.items[3].label = 'altered'
    with pytest.raises(grants.RegisterError, match='replay differs'):
        grants.admit([other, changed], ledger, recorded_at='2026-10-02')
    assert sorted((p.name, p.read_bytes()) for p in ledger.rglob('*.csv')) == before


# --- the held snapshots ------------------------------------------------------------

def _held(edition):
    path = LEDGER_DIR / 'documents' / 'objects' / edition.sha256[:2]
    found = list(path.glob(f'{edition.sha256}.*')) if path.is_dir() else []
    if not found:
        pytest.skip('snapshot bytes not materialised (make jetp-data)')
    return found[0]


@pytest.mark.slow
@pytest.mark.parametrize('document_id', sorted(grants.EDITIONS))
def test_every_held_edition_parses_to_its_reviewed_shape(document_id):
    edition = grants.EDITIONS[document_id]
    extraction = grants.extract(document_id, _held(edition))
    assert extraction.counts == edition.rows


@pytest.mark.slow
@pytest.mark.parametrize('document_id', sorted(grants.EDITIONS))
def test_every_held_edition_replays_to_its_lines_of_record(document_id):
    edition = grants.EDITIONS[document_id]
    extraction = grants.extract(document_id, _held(edition))
    schema = load_schema()
    lines, errors = read_table(LEDGER_DIR, 'lines', schema)
    assert not errors
    header = schema.header('lines')
    held = [dict(zip(header, row)) for row in lines if row[header.index('sha256')] ==
            edition.sha256]
    new_lines, field_rows = grants.to_rows(extraction, '2026-10-01')
    grants._replay(extraction, held, LEDGER_DIR, new_lines, field_rows)


@pytest.mark.slow
def test_2023_dollar_signs_are_each_accounted_for():
    edition = grants.EDITIONS['zaf-jet-grants-register-2023-q3']
    path = _held(edition)
    extraction = grants.extract(edition.document_id, path)
    rows = layouts.usd_reconciliation(ruled.read_pdf(path), extraction.items)
    tally = {}
    for row in rows:
        tally[row['disposition'].split(':')[0]] = tally.get(row['disposition'].split(':')[0], 0) + 1
    assert len(rows) == 160
    assert tally['grant row'] == 137
    assert tally['printed total (control)'] == 1 and tally['printed header'] == 1
    assert 'outside the table' not in tally and 'unattributed' not in tally


def test_the_four_editions_have_left_the_pending_list():
    schema = load_schema()
    lines, errors = read_table(LEDGER_DIR, 'lines', schema)
    assert not errors
    header = schema.header('lines')
    held = {}
    for row in lines:
        record = dict(zip(header, row))
        held[record['sha256']] = held.get(record['sha256'], 0) + 1
    for edition in grants.EDITIONS.values():
        assert held.get(edition.sha256), f'{edition.document_id} has no line'
