"""The three layouts of the South African JET Grants Register (ticket 1950).

Each layout function turns a text layer into statements before admission
(``Item``) and the outcome of its controls, or raises ``RegisterError``:
one failed landmark or control fails the whole document (extraction 6.1).

- ``parse_xlsx``: the workbooks (2024 Q3, 2025 Q1), cells as stored;
- ``parse_pdf_2023``: the JET-IP Grant Mapping Register (2023 Q3), one wide
  table on a fixed twenty-column grid;
- ``parse_pdf_2024``: the 2024 Q1-Q2 PDF, the workbook printed, one titled
  table per page run, columns found from the printed header labels.

The constants below are the parser's reviewed declarations: header labels,
grids, sheets out of scope and the publisher's own defects the controls met
and that were reviewed. Changing any of them is a new parser version.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from jetp import _pdf_ruled_table as ruled
from jetp import _xlsx_cells as xlsx

ID_PATTERN = re.compile(r'^[A-Z]{2,5}\d{3}[a-z]?\*?$')
GRID_TOLERANCE = 1.5
# A printed amount: one number, an optional sign and currency mark before it
# (or kr. after it), grouped by commas or spaces.
PRINTED_AMOUNT = re.compile(
    r'(?P<sign>-)?\s*(?:\$|R|€|£|CHF|CAD|US\$)?\s*'
    r'(?P<number>\d{1,3}(?:[ ,]\d{3})+|\d+)(?P<decimals>\.\d+)?\s*(?:kr\.?)?')
# A header naming money must be one of AMOUNT_COLUMNS, which get a total control.
# The word list is a net, not a proof: headers are also pinned per edition by the
# landmarks and the reviewed counts, so a new money column needs a new version.
MONEY_HEADER = re.compile(r'(?i)\b(amounts?|totals?|sum|usd|eur|euro|gbp|chf|cad|dkk|zar)\b'
                          r'|[$€£]')
AMOUNT_COLUMNS = ('Total US$', 'Total ZAR', 'Euro - Amount', 'Euro - Amounts', 'Euro: Amount',
                  'GBP - Amount', 'DKK - Amount', 'CAD - Amount', 'CHF: Amount')

# Workbooks: the sheets out of the declared scope, and why.
XLSX_SCOPE_OUT = {
    'PivotTables': 'pivot tables: aggregates of the grant rows, not grant rows',
    'Analysis - Dashboard': 'dashboard: aggregates and commentary on the grant rows',
    'Dropdowns': 'hidden data-validation lists: no assertion',
    'Financing Status': 'pledge summary of the whole partnership by instrument, '
                        'not grant rows; left to a later method version',
}
OVERALL_SHEET = 'DataTable - Overall'

# 2023 Q3 PDF: one table, twenty columns at fixed x (points, page 1 grid).
GRID_2023 = (72, 129, 204, 262, 299, 362, 427, 469, 519, 582, 646, 682, 760, 816,
             901, 972, 1036, 1086, 1206, 1251, 1296)
HEADERS_2023 = ('Priority Area', 'Priority Areas (Description)', 'Purpose', 'Source Group',
                'Activities - Descriptions', 'Implementing institution', 'Funder',
                'Funding instrument', 'Total US$', 'Total ZAR', 'Source',
                'Parties to the funding agreement(s)', 'Other key beneficiaries',
                'Key terms and conditions', 'Disbursements status', 'Status - Dynamic',
                '% Completed', 'Detailed Descriptions', 'Start Date', 'End Date')
# A band with none of these cells continues the row above it across a page break.
IDENTITY_2023 = ('Priority Area', 'Funder', 'Total US$', 'Total ZAR', 'Start Date',
                 'End Date')

# 2024 Q1-Q2 PDF: the workbook printed, one table per title, in this order.
TITLES_2024 = ('DATATABLE OVERALL', 'EU-REGISTER', 'UK-REGISTER', 'GER-REGISTER',
               'FR-REGISTER', 'US-REGISTER', 'ACTIP-REGISTER', 'DK-REGISTER',
               'NL-REGISTER', 'CAN-REGISTER', 'SWISS-REGISTER')
_HEAD = ('Unique ID', 'Portfolios', 'Priority Areas')
_TAIL = ('Status', 'Description', 'Date of Financing Agreement Signed*', 'End Date')
_OVERALL = (*_HEAD, 'Total US$', 'Total ZAR', 'Source', 'Implementing Entity', *_TAIL)


def _register(currency):
    return (*_HEAD, 'Total US$', currency, 'Total ZAR', 'Source', 'Implementing Entity', *_TAIL)


HEADERS_2024 = {
    'DATATABLE OVERALL': _OVERALL,
    'EU-REGISTER': _register('Euro - Amount'),
    'UK-REGISTER': _register('GBP - Amount'),
    'GER-REGISTER': (*_HEAD, 'Implementing Partners', 'Total US$', 'Euro - Amounts',
                     'Total ZAR', 'Source', 'Implementing Entity', *_TAIL),
    'FR-REGISTER': _register('Euro - Amount'),
    'US-REGISTER': _OVERALL,
    'ACTIP-REGISTER': (*_HEAD, 'Total US$', 'Total ZAR', 'Source', 'Implementing Entity',
                       'Beneficiaries', *_TAIL),
    'DK-REGISTER': _register('DKK - Amount'),
    'NL-REGISTER': _register('Euro: Amount'),
    'CAN-REGISTER': (*_HEAD, 'Total US$', 'CAD - Amount', 'Total ZAR', 'Source',
                     'Implementing Entity', 'Beneficiaries', *_TAIL),
    'SWISS-REGISTER': _register('CHF: Amount'),
}

# Reviewed print defects of the 2024 Q1-Q2 PDF. A register whose print stops
# before its last rows prints no total: its rows are read as printed and the
# overall table, which lists them all, is their control. A total too wide for
# its column prints as '#' signs: there is no figure to compare.
TRUNCATED_2024 = {
    'uk-register': {
        'reason': 'the printed UK register stops at UK015 (page 19): the rows after it '
                  'and its total are not printed; the overall table lists them',
        'not_printed': {f'UK{n:03d}' for n in (*range(16, 32), 33, 34, 35, 37, 39,
                                               *range(42, 52))},
    },
}
ILLEGIBLE_2024 = {('nl-register', 'Total ZAR')}


class RegisterError(ValueError):
    """A control or landmark failed: the document is not admitted."""


@dataclass
class Item:
    """One statement before admission."""

    table: str
    locator: str
    label: str
    classification: str
    fields: dict = field(default_factory=dict)
    own_status: str = ''
    own_sector: str = ''
    heading: str = ''      # locator of the heading that governs it, same table
    note: str = ''


def join(text):
    return ' '.join(str(text).split())


def amount(text):
    """The one number of a printed or stored amount; None when it prints no digit.

    A stored value is a plain or scientific number; a printed one matches
    ``PRINTED_AMOUNT``. Anything else with a digit in it (two numbers, a word
    between digits, a dot grouping thousands) is refused: a control must not
    sum what it cannot read.
    """
    if text is None:
        return None
    text = str(text).strip()
    if not re.search(r'\d', text):
        return None
    if re.fullmatch(r'-?\d{1,3}(\.\d{3})+', text):
        raise RegisterError(f'amount {text!r} is not one number: dots group thousands '
                            'or mark decimals')
    if re.fullmatch(r'-?\d+(\.\d+)?([eE][-+]?\d+)?', text):
        return float(text)
    match = PRINTED_AMOUNT.fullmatch(text)
    if match is None:
        raise RegisterError(f'amount {text!r} is not one number')
    value = float(re.sub(r'[ ,]', '', match['number']) + (match['decimals'] or ''))
    return -value if match['sign'] else value


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------

def check_total(table, column, rows, printed, controls, rounded=False):
    """Rows must sum to the printed total.

    A stored workbook value sums exactly (to half a unit). A printed PDF value
    is rounded to the unit for display, so the sum of printed rows may stray
    from the printed total by at most half a unit per row: beyond that bound
    the total disagrees.
    """
    printed_cells = [row.get(column) for row in rows if row.get(column)]
    values = [v for v in (amount(cell) for cell in printed_cells) if v is not None]
    total = sum(values)
    if printed is None:
        raise RegisterError(f'{table}: no printed total for {column!r}')
    # Half a unit per rounded value is the exact bound; a small row lost under
    # it is caught by the reviewed row count of the edition, not by the sum.
    tolerance = 0.5 * (len(values) + 1) if rounded else 0.5
    gap = total - printed
    if abs(gap) > tolerance:
        raise RegisterError(f'{table}: {column!r} rows sum to {total:,.2f}, '
                            f'the printed total is {printed:,.2f}')
    blank = len(printed_cells) - len(values)
    controls.append(f'{table}: {column} sum of {len(values)} rows {total:,.2f}, '
                    f'printed total {printed:,.2f} (gap {gap:+,.2f}, bound {tolerance:,.1f})'
                    + (f'; {blank} cells print no number' if blank else '')
                    + ('; a misread below the bound is not seen by the sum, a lost row is '
                       'seen by the reviewed row count' if rounded else ''))


def check_ids(table, rows, controls):
    ids = [row['Unique ID'] for row in rows]
    duplicated = sorted(i for i, n in Counter(ids).items() if n > 1)
    if duplicated:
        raise RegisterError(f'{table}: Unique ID printed twice: {", ".join(duplicated)}')
    controls.append(f'{table}: {len(ids)} distinct Unique IDs')


def check_overall_union(ids_by_table, controls, truncated=None, declared=None):
    """The overall table lists exactly the grants of the donor registers.

    A register declared truncated in print lacks exactly the rows declared as
    not printed. A difference the publisher made between its overall table
    and its registers is recorded as the publisher's own (extraction section
    15) once reviewed: the difference found must then be exactly the one
    declared. A declaration may carry a ``reading``, the reviewed explanation
    of the difference, which the control line prints; it never alters the
    comparison.
    """
    if 'overall' not in ids_by_table:
        controls.append('no overall table: the registers are not compared to one')
        return
    registers = set().union(*(ids for table, ids in ids_by_table.items() if table != 'overall'))
    overall = ids_by_table['overall']
    not_printed = set().union(*(d['not_printed'] for d in (truncated or {}).values()))
    if not not_printed <= overall - registers:
        raise RegisterError('rows declared not printed are printed or absent from the '
                            f'overall table: {sorted(not_printed - (overall - registers))}')
    only_overall = overall - registers - not_printed
    only_registers = registers - overall
    expected = declared or {'only_overall': set(), 'only_registers': set()}
    if (only_overall, only_registers) != (set(expected['only_overall']),
                                          set(expected['only_registers'])):
        raise RegisterError('overall table and donor registers list different grants: '
                            f'only overall {sorted(only_overall)}, '
                            f'only registers {sorted(only_registers)}')
    missing = sorted(not_printed)
    text = f'overall: {len(overall)} Unique IDs, donor registers {len(registers)}'
    if missing:
        text += (f'; {len(missing)} not printed in a truncated register '
                 f'({missing[0]}..{missing[-1]})')
    if only_overall or only_registers:
        text += ("; publisher's own difference, reviewed: only in overall "
                 f'{sorted(only_overall)}, only in registers {sorted(only_registers)}')
        if expected.get('reading'):
            text += f" (reading: {expected['reading']})"
    controls.append(text)


def _slug(title):
    title = join(title)
    if title.upper() in ('DATATABLE OVERALL', OVERALL_SHEET.upper()):
        return 'overall'
    return re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')


# ---------------------------------------------------------------------------
# Workbooks (2024 Q3, 2025 Q1)
# ---------------------------------------------------------------------------

def parse_xlsx(path, mismatch=None):
    """Grant tables of a register workbook, controlled against their printed totals."""
    sheets = xlsx.read_workbook(path)
    if OVERALL_SHEET not in [join(s.name) for s in sheets]:
        raise RegisterError(f'landmark absent: no sheet {OVERALL_SHEET!r}')
    items, controls, counts, out, ids_by_table = [], [], {}, {}, {}
    for sheet in sheets:
        name = join(sheet.name)
        if name in XLSX_SCOPE_OUT:
            out[f'sheet "{sheet.name}"'] = XLSX_SCOPE_OUT[name]
            continue
        if name != OVERALL_SHEET and not name.endswith('-Register'):
            raise RegisterError(f'sheet {sheet.name!r} is neither a declared table '
                                'nor declared out of scope')
        table = _slug(name)
        sheet_items, rows = _xlsx_table(sheet, table, controls)
        items.extend(sheet_items)
        counts[table] = len(rows)
        ids_by_table[table] = {row['Unique ID'] for row in rows}
    check_overall_union(ids_by_table, controls, declared=mismatch)
    return items, controls, counts, out


def _locator_xlsx(sheet, ref):
    return f'sheet "{sheet.name}", {ref}'


def _xlsx_header(rows, table):
    at = next((i for i, row in enumerate(rows) if join(row.cells.get('A', '')) == 'Unique ID'),
              None)
    if at is None:
        raise RegisterError(f'{table}: landmark absent: no "Unique ID" header in column A')
    headers = {c: join(v) for c, v in rows[at].cells.items()}
    if len(set(headers.values())) != len(headers):
        raise RegisterError(f'{table}: a header is printed twice')
    for needed in ('Unique ID', 'Total US$', 'Total ZAR', 'Status'):
        if needed not in headers.values():
            raise RegisterError(f'{table}: landmark absent: header {needed!r}')
    undeclared = [h for h in headers.values()
                  if MONEY_HEADER.search(h) and h not in AMOUNT_COLUMNS]
    if undeclared:
        raise RegisterError(f'{table}: amount header(s) {undeclared} not declared for a '
                            'total control')
    return at, dict(sorted(headers.items(), key=lambda kv: xlsx.column_index(kv[0])))


def _xlsx_note_above(sheet, table, above):
    last = max((c for row in above for c in row.cells), key=xlsx.column_index)
    texts = [join(row.cells[c]) for row in above
             for c in sorted(row.cells, key=xlsx.column_index)]
    locator = _locator_xlsx(sheet, f'A{above[0].number}:{last}{above[-1].number}')
    return Item(table, locator, ' '.join(texts), 'heading',
                note='exchange-rate note and title above the table')


def _hidden_note(sheet, row, headers):
    """What of a grant row was read from a hidden sheet, row or column."""
    marks = ['hidden sheet'] if sheet.hidden else []
    if row.hidden:
        marks.append('hidden row')
    columns = [headers[c] for c in row.cells if c in sheet.hidden_columns]
    if columns:
        marks.append(f'hidden column(s): {", ".join(columns)}')
    return '; '.join(marks)


def _xlsx_table(sheet, table, controls):
    rows = [row for row in sheet.rows if row.cells]
    at, headers = _xlsx_header(rows, table)
    items = [_xlsx_note_above(sheet, table, rows[:at])] if at else []
    heading = items[0].locator if items else ''
    grants, total, notes = [], None, []
    for row in rows[at + 1:]:
        unique = join(row.cells.get('A', ''))
        stray = [c for c in row.cells if c not in headers]
        if total is None and ID_PATTERN.match(unique) and not stray:
            fields = {headers[c]: row.cells[c] for c in headers if c in row.cells}
            fields['Unique ID'] = unique
            items.append(Item(table, _locator_xlsx(sheet, f'row {row.number}'),
                              join(fields.get('Description', '')) or unique,
                              'register_allocation', fields,
                              own_status=join(fields.get('Status', '')),
                              own_sector=join(fields.get('Portfolios', '')), heading=heading,
                              note=_hidden_note(sheet, row, headers)))
            grants.append(fields)
        elif total is None and not unique and not stray and \
                any(headers[c] == 'Total US$' for c in row.cells):
            total = {headers[c]: v for c, v in row.cells.items()}
        elif total is not None and set(row.cells) == {'A'} and not ID_PATTERN.match(unique):
            notes.append(Item(table, _locator_xlsx(sheet, f'A{row.number}'),
                              join(row.cells['A']), 'heading', heading=heading,
                              note='footnote under the table'))
        else:
            raise RegisterError(f'{table}: row {row.number} is neither a grant, the total '
                                'nor a footnote')
    if total is None:
        raise RegisterError(f'{table}: no printed total row')
    check_ids(table, grants, controls)
    for column in AMOUNT_COLUMNS:
        if column in headers.values():
            check_total(table, column, grants, amount(total.get(column)), controls)
    return items + notes, grants


# ---------------------------------------------------------------------------
# Shared by both PDF layouts: records cut from bands
# ---------------------------------------------------------------------------

def _new_record(cells, page, position):
    return {'cells': cells, 'page': page.number, 'last_page': page.number, 'row': position}


def _continue(record, cells, page):
    """A band opening a page that carries on the last row of the page before."""
    for name, text in cells.items():
        record['cells'][name] = join(f"{record['cells'].get(name, '')} {text}")
    record['last_page'] = page.number


def _record_locator(record, table_number):
    pages = (f"page {record['page']}" if record['page'] == record['last_page']
             else f"pages {record['page']}-{record['last_page']}")
    return f"{pages}, table {table_number}, row {record['row']}"


# ---------------------------------------------------------------------------
# 2023 Q3 PDF: JET-IP Grant Mapping Register, one wide table
# ---------------------------------------------------------------------------

def grid_column(word, grid):
    start = word.x0 + GRID_TOLERANCE  # a cell's text starts inside its cell
    for index in range(len(grid) - 1):
        if grid[index] <= start < grid[index + 1]:
            return index
    return None


def _band_cells(page, top, bottom):
    cells = {}
    for word in page.words_between(top, bottom):
        index = grid_column(word, GRID_2023)
        if index is None:
            raise RegisterError(f'page {page.number}: word {word.text!r} at x={word.x0:.0f} '
                                'lies outside the column grid: landmark absent (shifted grid)')
        cells.setdefault(HEADERS_2023[index], []).append(word)
    return {name: ruled.cell_text(words) for name, words in cells.items()}


def _headings_2023(first):
    header = _band_cells(first, first.rules[0], first.rules[1])
    found = tuple(header.get(h, '') for h in HEADERS_2023)
    if found != HEADERS_2023:
        wrong = [f'{want!r} read {got!r}' for want, got in zip(HEADERS_2023, found)
                 if want != got]
        raise RegisterError('landmark absent: header of the 2023 grid differs: '
                            + '; '.join(wrong))
    above = [w for w in first.words if w.middle < first.rules[0]]
    title = Item('register', 'page 1, above table 1, title',
                 ruled.cell_text([w for w in above if w.x1 < GRID_2023[9]]), 'heading',
                 note='title of the register')
    rate = Item('register', 'page 1, above table 1, exchange-rate note',
                ruled.cell_text([w for w in above if w.x0 >= GRID_2023[8]]), 'heading',
                heading=title.locator, note='exchange-rate note governing every row')
    return [title, rate]


def _outside_bands_2023(page, first):
    """Only page furniture lies outside the ruled table: the folio, and on page
    1 the title and exchange-rate note above it."""
    for word in page.words:
        if word.middle > page.rules[-1] and not word.text.isdigit():
            raise RegisterError(f'page {page.number}: text {word.text!r} under the table')
        if word.middle < page.rules[0] and page is not first:
            raise RegisterError(f'page {page.number}: text {word.text!r} above the table')


def _records_2023(pages):
    records, total = [], None
    for page in pages:
        if not page.rules:
            raise RegisterError(f'page {page.number}: no ruled table')
        _outside_bands_2023(page, pages[0])
        bands = page.bands()[1:] if page is pages[0] else page.bands()
        for position, (top, bottom) in enumerate(bands, 1):
            cells = _band_cells(page, top, bottom)
            identified = any(cells.get(h) for h in IDENTITY_2023)
            if not cells:
                continue
            if not identified and position == 1 and records and page is not pages[0]:
                _continue(records[-1], cells, page)
            elif set(cells) <= {'Total US$', 'Total ZAR'} and page is pages[-1] \
                    and position == len(bands):
                total = cells
            elif identified:
                records.append(_new_record(cells, page, position))
            else:
                raise RegisterError(f'page {page.number}, row {position}: a band with no '
                                    'identifying cell that does not open the page')
    if total is None:
        raise RegisterError('no printed total row at the end of the table')
    return records, total


def parse_pdf_2023(pages):
    """The grant rows of the 2023 Q3 register, controlled against its printed total."""
    if not pages or len(pages[0].rules) < 3:
        raise RegisterError('landmark absent: no ruled table on page 1')
    items = _headings_2023(pages[0])
    records, total = _records_2023(pages)
    grants, controls = [], []
    for record in records:
        cells = {name: join(record['cells'][name]) for name in HEADERS_2023
                 if name in record['cells']}
        label = cells.get('Activities - Descriptions') or cells.get('Detailed Descriptions', '')
        items.append(Item('register', _record_locator(record, 1), label, 'register_allocation',
                          cells, own_status=cells.get('Status - Dynamic', ''),
                          own_sector=cells.get('Priority Area', ''), heading=items[1].locator))
        grants.append(cells)
    for column in ('Total US$', 'Total ZAR'):
        check_total('register', column, grants, amount(total[column]), controls, rounded=True)
    return items, controls, {'register': len(grants)}, {
        'page furniture': 'printed folios at the foot of each page'}


def usd_reconciliation(pages, items):
    """Every dollar sign of the 2023 Q3 text layer, and what it is.

    Each ``$`` glyph is located in its band and column: the printed header, a
    grant row's Total US$ cell (one statement each), the printed total (the
    control), or an amount written inside another cell of a grant row (text
    of that statement's verbatim fields, not a row).
    """
    by_place = {}
    for item in items:
        match = re.match(r'pages? (\d+)(?:-(\d+))?, table 1, row (\d+)$', item.locator)
        if match:
            first, last, row = int(match[1]), int(match[2] or match[1]), int(match[3])
            by_place[(first, row)] = item
            if last != first:
                by_place[(last, 1)] = item
    rows = []
    for page in pages:
        bands = page.bands()
        offset = 1 if page.number == 1 else 0
        for text, x0, top, bottom in page.chars:
            if text != '$':
                continue
            middle = (top + bottom) / 2
            index = next((i for i, (a, b) in enumerate(bands) if a < middle < b), None)
            column = next((HEADERS_2023[i] for i in range(len(GRID_2023) - 1)
                           if GRID_2023[i] <= x0 + 1 < GRID_2023[i + 1]), '')
            word = next((w.text for w in page.words
                         if w.x0 - 0.5 <= x0 <= w.x1 and abs(w.top - top) < 2), '$')
            place = {'page': page.number, 'x': round(x0), 'y': round(top), 'column': column,
                     'text': word, 'locator': ''}
            item = None if index is None else by_place.get((page.number, index + 1 - offset))
            closing = page is pages[-1] and index == len(bands) - 1
            if index is None:
                disposition = 'outside the table'
            elif page.number == 1 and index == 0:
                disposition = 'printed header'
            elif item is None and closing:
                disposition = 'printed total (control)'
            elif item is None:
                disposition = 'unattributed'
            elif column == 'Total US$':
                disposition = 'grant row: Total US$ cell'
            else:
                disposition = (f'inside the {column} cell of a grant row: '
                               'an amount in its text, not a row')
            if item is not None:
                place['locator'] = item.locator
            rows.append({**place, 'disposition': disposition})
    return rows


# ---------------------------------------------------------------------------
# 2024 Q1-Q2 PDF: the workbook printed, one table per title
# ---------------------------------------------------------------------------

def _header_starts(page, labels):
    """x where each declared header label starts, read in content-stream order."""
    top, bottom = page.rules[0], page.rules[1]
    chars = [c for c in page.chars if top < (c[2] + c[3]) / 2 < bottom]
    squeezed = [(i, c[0]) for i, c in enumerate(chars) if not c[0].isspace()]
    flat = ''.join(ch for _, ch in squeezed)
    starts, cursor = [], 0
    for label in labels:
        target = ''.join(label.split())
        found = flat.find(target, cursor)
        if found < 0:
            raise RegisterError(f'page {page.number}: landmark absent: header {label!r}')
        starts.append(chars[squeezed[found][0]][1])
        cursor = found + len(target)
    if starts != sorted(starts):
        raise RegisterError(f'page {page.number}: landmark absent: header labels out of order')
    return starts


def _columns_2024(page, top, bottom, starts, labels):
    cells = {}
    for word in page.words_between(top, bottom):
        index = max((i for i, s in enumerate(starts) if word.x0 >= s - GRID_TOLERANCE * 2),
                    default=None)
        if index is None:
            raise RegisterError(f'page {page.number}: word {word.text!r} lies left of the '
                                'first column')
        cells.setdefault(labels[index], []).append(word)
    return {name: join(ruled.cell_text(words)) for name, words in cells.items()}


def _tables_2024(pages, titles):
    tables = []
    for page in pages:
        if len(page.rules) < 2:
            raise RegisterError(f'page {page.number}: no ruled table')
        above = [w for w in page.words if w.middle < page.rules[0]]
        text = join(' '.join(w.text for w in above))
        title = next((t for t in titles if text.startswith(t)), None)
        if title is not None:
            tables.append({'title': title, 'pages': [page], 'above': above})
        elif not tables:
            raise RegisterError(f'landmark absent: page {page.number} opens no titled table')
        elif above:
            raise RegisterError(f'page {page.number}: text above a continued table')
        else:
            tables[-1]['pages'].append(page)
    if [t['title'] for t in tables] != list(titles):
        raise RegisterError(f"tables found {[t['title'] for t in tables]}, "
                            f'declared {list(titles)}')
    return tables


def _records_2024(table, labels):
    records, total = [], None
    first, last = table['pages'][0], table['pages'][-1]
    for page in table['pages']:
        starts = _header_starts(page, labels)
        bands = page.bands()[1:]
        for position, (top, bottom) in enumerate(bands, 1):
            cells = _columns_2024(page, top, bottom, starts, labels)
            unique = cells.get('Unique ID', '')
            if not cells:
                continue
            if ID_PATTERN.match(unique):
                records.append(_new_record(cells, page, position))
            elif unique:
                raise RegisterError(f'page {page.number}, row {position}: Unique ID '
                                    f'{unique!r} is not of the declared form')
            elif page is last and position == len(bands) and '$' in cells.get('Total US$', ''):
                total = cells
            elif position == 1 and records and page is not first:
                _continue(records[-1], cells, page)
            else:
                raise RegisterError(f'page {page.number}, row {position}: no Unique ID '
                                    'and not a continuation')
    return records, total


def _lines(words):
    lines = []
    for word in sorted(words, key=lambda w: (w.top, w.x0)):
        if lines and abs(lines[-1][0] - word.top) < 2:
            lines[-1][1].append(word)
        else:
            lines.append([word.top, [word]])
    return [(top, ' '.join(w.text for w in sorted(ws, key=lambda w: w.x0)), ws)
            for top, ws in lines]


def _below_2024(page, labels, number, slug, heading, total):
    """The printed total, when it sits under the last rule, and the footnotes."""
    lines = _lines([w for w in page.words if w.middle > page.rules[-1]])
    if total is None:
        if not lines or '$' not in lines[0][1]:
            raise RegisterError(f'page {page.number}: no printed total under table {number}')
        top = lines[0][0]
        total = _columns_2024(page, top - 1, top + 6, _header_starts(page, labels), labels)
        lines = lines[1:]
    notes = []
    for _, text, _ in lines:
        if text.startswith(('Footnote', '*')) or not notes:
            notes.append(text)
        else:
            notes[-1] = f'{notes[-1]} {text}'
    footnotes = [Item(slug, f'page {page.number}, under table {number}, footnote {index}',
                      join(text), 'heading', heading=heading, note='footnote under the table')
                 for index, text in enumerate(notes, 1)]
    return total, footnotes


def _totals_2024(slug, labels, grants, total, illegible, controls):
    for column in AMOUNT_COLUMNS:
        if column not in labels:
            continue
        printed = total.get(column, '')
        if (slug, column) in illegible:
            if not re.fullmatch(r'#+', printed):
                raise RegisterError(f'{slug}: {column!r} declared illegible, prints {printed!r}')
            controls.append(f'{slug}: {column} printed total illegible ({printed}), '
                            'not compared')
            continue
        check_total(slug, column, grants, amount(printed), controls, rounded=True)


def parse_pdf_2024(pages, titles=TITLES_2024, truncated=None, illegible=None):
    """Grant tables of the 2024 Q1-Q2 register, controlled against their printed totals.

    ``titles`` are the tables the bytes must hold, in order; ``truncated`` and
    ``illegible`` the reviewed print defects (defaults: the edition's own).
    """
    truncated = TRUNCATED_2024 if truncated is None else truncated
    illegible = ILLEGIBLE_2024 if illegible is None else illegible
    items, controls, counts, ids_by_table = [], [], {}, {}
    for number, table in enumerate(_tables_2024(pages, titles), 1):
        slug, labels = _slug(table['title']), HEADERS_2024[table['title']]
        heading = f"page {table['pages'][0].number}, above table {number}"
        items.append(Item(slug, heading, ruled.cell_text(table['above']), 'heading',
                          note='title and exchange-rate note above the table'))
        records, total = _records_2024(table, labels)
        last = table['pages'][-1]
        if slug in truncated:
            if total is not None or any(w.middle > last.rules[-1] for w in last.words):
                raise RegisterError(f'{slug}: declared truncated, yet prints a total or notes')
            controls.append(f"{slug}: no printed total; {truncated[slug]['reason']}")
            footnotes = []
        else:
            total, footnotes = _below_2024(last, labels, number, slug, heading, total)
        for record in records:
            record['cells'] = {name: record['cells'][name] for name in labels
                               if name in record['cells']}
        grants = [record['cells'] for record in records]
        items.extend(Item(slug, _record_locator(record, number),
                          record['cells'].get('Description') or record['cells']['Unique ID'],
                          'register_allocation', record['cells'],
                          own_status=record['cells'].get('Status', ''),
                          own_sector=record['cells'].get('Portfolios', ''), heading=heading)
                     for record in records)
        items.extend(footnotes)
        check_ids(slug, grants, controls)
        if slug not in truncated:
            _totals_2024(slug, labels, grants, total, illegible, controls)
        counts[slug] = len(grants)
        ids_by_table[slug] = {g['Unique ID'] for g in grants}
    check_overall_union(ids_by_table, controls, truncated)
    return items, controls, counts, {'page furniture': 'none printed'}
