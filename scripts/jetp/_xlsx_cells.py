"""Cell-level XLSX text layer, standard library only (extraction section 5).

A workbook is read sheet by sheet as the publisher stored it: the cached value
of every cell (formulas are never re-evaluated), with hidden sheets and hidden
rows read like visible ones and marked. Nothing in the package is executed or
followed: only ``xl/workbook.xml``, its relationships, the shared strings, the
styles and the worksheets are parsed; macros, embedded objects, connections and
external links are never opened.

A number keeps its stored text. A cell whose number format is a date format
is rendered as an ISO date (``YYYY-MM-DD``, with ``THH:MM`` when the stored
serial carries a time of day), the form the publisher displays; the stored
serial is what the adapter version converts, so the conversion is part of the
adapter, named by ``ADAPTER`` and ``VERSION``.

Why not openpyxl: it is not a dependency of the project, and this reader needs
exactly the stored values, the hidden flags and nothing else (ticket 1950).
"""

import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET

ADAPTER = 'jetp-xlsx-cells'
VERSION = '1'

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'pr': 'http://schemas.openxmlformats.org/package/2006/relationships'}
REL_ID = '{%s}id' % NS['r']

# Built-in number formats that display a date or a time (ECMA-376 18.8.30).
BUILTIN_DATE_FORMATS = {14, 15, 16, 17, 18, 19, 20, 21, 22, 27, 30, 36, 45, 46, 47,
                        50, 57}
EPOCH = datetime(1899, 12, 30)


@dataclass
class Row:
    number: int
    hidden: bool
    cells: dict = field(default_factory=dict)  # column letters -> text


@dataclass
class Sheet:
    name: str
    state: str          # visible, hidden or veryHidden
    rows: list          # list of Row, in row order

    @property
    def hidden(self):
        return self.state != 'visible'

    def row(self, number):
        return next((row for row in self.rows if row.number == number), None)


class XlsxError(ValueError):
    """The bytes are not a workbook this adapter can read."""


def column_index(letters):
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - 64)
    return index


def column_letters(index):
    letters = ''
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def _text(node):
    """The visible text of a shared or inline string (runs joined, phonetics dropped)."""
    if node is None:
        return ''
    parts = []
    for child in node:
        tag = child.tag.rsplit('}', 1)[-1]
        if tag == 't':
            parts.append(child.text or '')
        elif tag == 'r':
            parts.extend(t.text or '' for t in child.findall('m:t', NS))
    return ''.join(parts)


def _is_date_format(code):
    stripped = re.sub(r'"[^"]*"|\\.|\[[^\]]*\]', '', code)
    return bool(re.search(r'[dmyhs]', stripped, re.IGNORECASE)) and \
        not re.fullmatch(r'[#0.,%\s]*', stripped)


def _date_styles(archive):
    """Indexes of cellXfs whose number format shows a date."""
    try:
        root = ET.fromstring(archive.read('xl/styles.xml'))
    except KeyError:
        return set()
    custom = {int(fmt.get('numFmtId')): fmt.get('formatCode', '')
              for fmt in root.findall('m:numFmts/m:numFmt', NS)}
    dates = set()
    for index, xf in enumerate(root.findall('m:cellXfs/m:xf', NS)):
        fmt = int(xf.get('numFmtId', '0'))
        if fmt in BUILTIN_DATE_FORMATS or (fmt in custom and _is_date_format(custom[fmt])):
            dates.add(index)
    return dates


def _iso(serial_text):
    value = float(serial_text)
    moment = EPOCH + timedelta(days=value)
    moment = moment.replace(microsecond=0)
    if moment.second >= 30:
        moment += timedelta(seconds=60 - moment.second)
    if (moment.hour, moment.minute) == (0, 0):
        return moment.strftime('%Y-%m-%d')
    return moment.strftime('%Y-%m-%dT%H:%M')


def _sheet_paths(archive):
    workbook = ET.fromstring(archive.read('xl/workbook.xml'))
    rels = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
    targets = {rel.get('Id'): rel.get('Target') for rel in rels.findall('pr:Relationship', NS)}
    for sheet in workbook.findall('m:sheets/m:sheet', NS):
        target = targets[sheet.get(REL_ID)]
        path = target.lstrip('/') if target.startswith('/') else str(PurePosixPath('xl') / target)
        yield sheet.get('name'), sheet.get('state', 'visible'), path


def read_workbook(path):
    """Every sheet of a workbook, with its rows' stored cell values as text."""
    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise XlsxError(f'not an XLSX package: {exc}') from exc
    with archive:
        names = set(archive.namelist())
        if 'xl/workbook.xml' not in names:
            raise XlsxError('no xl/workbook.xml')
        shared = []
        if 'xl/sharedStrings.xml' in names:
            root = ET.fromstring(archive.read('xl/sharedStrings.xml'))
            shared = [_text(si) for si in root.findall('m:si', NS)]
        dates = _date_styles(archive)
        sheets = []
        for name, state, part in _sheet_paths(archive):
            if part not in names:
                raise XlsxError(f'sheet {name!r}: missing part {part}')
            root = ET.fromstring(archive.read(part))
            rows = []
            for row in root.findall('m:sheetData/m:row', NS):
                record = Row(int(row.get('r')), row.get('hidden') in ('1', 'true'))
                for cell in row.findall('m:c', NS):
                    ref = re.match(r'([A-Z]+)(\d+)$', cell.get('r', ''))
                    if ref is None:
                        raise XlsxError(f'sheet {name!r}: cell without reference')
                    kind = cell.get('t', 'n')
                    value = cell.find('m:v', NS)
                    raw = value.text if value is not None else None
                    if kind == 's':
                        text = shared[int(raw)] if raw is not None else ''
                    elif kind == 'inlineStr':
                        text = _text(cell.find('m:is', NS))
                    elif kind == 'b':
                        text = {'1': 'TRUE', '0': 'FALSE'}.get(raw or '', '')
                    elif raw is None:
                        text = ''
                    elif kind == 'n' and int(cell.get('s', '0')) in dates:
                        text = _iso(raw)
                    else:
                        text = raw
                    if text != '':
                        record.cells[ref.group(1)] = text
                rows.append(record)
            sheets.append(Sheet(name, state, rows))
        return sheets
