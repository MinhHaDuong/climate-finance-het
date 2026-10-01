"""Parser for the South African JET Grants Register series (ticket 1950).

Extraction section 6.1: one purpose-built parser reads the whole series. The
JET Project Management Unit's grants register is held in four editions: two
PDFs (2023 Q3, 2024 Q1-Q2) and two workbooks (2024 Q3, 2025 Q1). Every
edition is one or more tables of grants, one row per grant, with an
exchange-rate note above the table, a printed total below it and footnotes
under the total. The layouts are read by ``_zaf_grants_layouts.py``.

For each edition the parser:

- refuses bytes it was not written for (fingerprint), and within them checks
  the layout's landmarks (sheet names, header labels, column grid);
- cuts each declared table into records, mends a record split by a page
  break (one statement whose locator spans both pages), and keeps every cell
  as printed under its printed header (the verbatim fields);
- checks each table against its printed totals and the edition against its
  reviewed row counts; one failed control fails the whole document, and
  nothing of it is admitted;
- writes one ``register_allocation`` line per grant row and one ``heading``
  line per title with exchange-rate note and per footnote, through the
  ledger writers, signed with the parser's method and version in ``notes``;
  a snapshot that already has lines is replayed and must come out identical.

Declared extraction scope: the grant tables. Out of scope, with the reason
recorded in the run report: pivot tables, the analysis dashboard and the
"Financing Status" pledge summary, the hidden "Dropdowns" sheet, and page
furniture (folios).

Usage::

    python scripts/jetp/build_zaf_grants_register.py check
    python scripts/jetp/build_zaf_grants_register.py admit --recorded-at 2026-10-01 \\
        --output docs/jetp-study/1950-zaf-grants-register-run.json
"""

import argparse
import csv
import hashlib
import io
import json
import logging
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from jetp import _pdf_ruled_table as ruled
from jetp import _xlsx_cells as xlsx
from jetp import _zaf_grants_layouts as layouts
from jetp._ledger_headers import (
    LEDGER_DIR,
    file_ceiling,
    load_schema,
    read_table,
    write_table,
)
from jetp._zaf_grants_layouts import RegisterError
from jetp.build_comparators import _add, _rows
from jetp.build_iati_comparators import _append_lines

ROOT = Path(__file__).resolve().parents[2]
METHOD = 'zaf-grants-register-parser'
VERSION = '1'
COUNTRY = 'ZAF'
REPORT = ROOT / 'docs' / 'jetp-study' / '1950-zaf-grants-register-run.json'
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Edition:
    """Bytes the parser was written for, and their reviewed shape."""

    document_id: str
    sha256: str
    layout: str          # 'pdf-2023', 'pdf-2024', 'xlsx'
    rows: dict           # table slug -> reviewed grant-row count
    mismatch: dict = None  # reviewed overall/register difference (workbooks)


EDITIONS = {e.document_id: e for e in (
    Edition('zaf-jet-grants-register-2023-q3',
            'fa8fd693d1d0d53c7478e9b3850da16ad83955bf2c715c5983634819c2315d16',
            'pdf-2023', {'register': 138}),
    Edition('zaf-jet-grants-register-2024-q2',
            '8f6fcef78bf9ddb9c67fee3225448e0b6ac6f1d88a6c77cd58a9282cd0ebaf06',
            'pdf-2024', {'overall': 152, 'eu-register': 8, 'uk-register': 14,
                         'ger-register': 22, 'fr-register': 13, 'us-register': 34,
                         'actip-register': 2, 'dk-register': 9, 'nl-register': 6,
                         'can-register': 4, 'swiss-register': 9}),
    Edition('zaf-jet-grants-register-2024-q3',
            '07645661df0c9a4ef97e0a172b8a3f5c92cc5371f992c70a2b3d5420f93c8147',
            'xlsx', {'overall': 164, 'eu-register': 8, 'uk-register': 45,
                     'ger-register': 22, 'fr-register': 20, 'us-register': 35,
                     'actip-register': 2, 'dk-register': 13, 'nl-register': 6,
                     'can-register': 4, 'swiss-register': 11},
            # The identifier sets differ, but only DK011 and DK013 are missing
            # grants: the overall table leaves out the workbook's two
            # "A. Planned" rows. The FR differences are a relabelling: paired
            # by position, the 20 FR rows agree on every field, amounts
            # included, and from the 11th row the overall table carries the
            # pre-renumbering identifiers (overall FR013..FR024 against
            # register FR012..FR022). Identifiers are not stable keys (1980).
            {'only_overall': {'FR021', 'FR024'},
             'only_registers': {'DK011', 'DK013', 'FR012', 'FR015'},
             'reading': 'the FR identifiers are relabelled in the overall table '
                        '(paired by position, 0 field differences); only DK011 '
                        'and DK013, the two "A. Planned" rows, are left out'}),
    Edition('zaf-jet-grants-register-2025-q1',
            '6eae2fffc800f6c82c2d03b21af150ba633bf60992bd8e37a98515808e44d9c0',
            'xlsx', {'overall': 129, 'eu-register': 8, 'uk-register': 47,
                     'ger-register': 22, 'fr-register': 20, 'actip-register': 2,
                     'dk-register': 11, 'nl-register': 6, 'can-register': 4,
                     'swiss-register': 9}),
)}


@dataclass
class Extraction:
    document_id: str
    sha256: str
    adapter: str
    items: list
    controls: list         # control outcomes, all passed
    counts: dict           # table slug -> grant rows
    out_of_scope: dict     # part -> reason


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract(document_id, path):
    """Every statement of one edition, or ``RegisterError`` and nothing."""
    edition = EDITIONS.get(document_id)
    if edition is None:
        raise RegisterError(f'{document_id}: not an edition this parser was written for')
    digest = sha256_of(path)
    if digest != edition.sha256:
        raise RegisterError(f'{document_id}: bytes {digest[:12]} are not the snapshot '
                            f'{edition.sha256[:12]} the parser was written for')
    if edition.layout == 'xlsx':
        adapter = f'{xlsx.ADAPTER} v{xlsx.VERSION}'
        try:
            items, controls, counts, out = layouts.parse_xlsx(path, edition.mismatch)
        except xlsx.XlsxError as exc:
            raise RegisterError(f'{document_id}: {exc}') from exc
    else:
        adapter = f'{ruled.ADAPTER} v{ruled.VERSION}'
        parse = layouts.parse_pdf_2023 if edition.layout == 'pdf-2023' else \
            layouts.parse_pdf_2024
        items, controls, counts, out = parse(ruled.read_pdf(path))
    if counts != edition.rows:
        raise RegisterError(f'{document_id}: grant rows {counts}, reviewed {edition.rows}')
    clash = [loc for loc, n in Counter(i.locator for i in items).items() if n > 1]
    if clash:
        raise RegisterError(f'{document_id}: two statements claim one place: {clash[:3]}')
    return Extraction(document_id, digest, adapter, items, controls, counts, out)


# ---------------------------------------------------------------------------
# Admission through the ledger writers
# ---------------------------------------------------------------------------

def field_columns(extraction):
    """The edition's verbatim field list: each table's printed headers in grid
    order, a header placed where the first table that prints it puts it."""
    columns = []
    for item in extraction.items:
        columns.extend(name for name in item.fields if name not in columns)
    return columns


def to_rows(extraction, recorded_at):
    """Ledger ``lines`` rows and per-document field rows of one extraction."""
    ordinals, line_of = Counter(), {}
    lines, fields = [], []
    for item in extraction.items:
        ordinals[item.table] += 1
        line_id = f'{extraction.document_id}-{item.table}-{ordinals[item.table]}'
        line_of[(item.table, item.locator)] = line_id
        group = line_of.get((item.table, item.heading)) if item.heading else None
        if item.heading and group is None:
            raise RegisterError(f'{line_id}: its heading is not minted before it')
        note = '; '.join(filter(None, (f'method {METHOD} v{VERSION}',
                                       f'adapter {extraction.adapter}', item.note)))
        lines.append({'line_id': line_id, 'country': COUNTRY, 'sha256': extraction.sha256,
                      'locator': item.locator, 'ordinal': ordinals[item.table],
                      'label': item.label, 'classification': item.classification,
                      'own_status': item.own_status or None, 'own_status_axis': None,
                      'own_sector': item.own_sector or None, 'groups': group,
                      'recorded_at': recorded_at, 'notes': note})
        if item.classification != 'heading':
            fields.append({'line_id': line_id, **item.fields})
    return lines, fields


def _comparable(rows, skip=('recorded_at',)):
    return [{k: '' if v is None else str(v) for k, v in row.items() if k not in skip}
            for row in rows]


def _replay(extraction, held, ledger_dir, new_lines, field_rows):
    """Extraction section 10: the lines and fields of record, regenerated exactly."""
    path = ledger_dir / 'line-fields' / f'{extraction.document_id}.csv'
    with path.open(newline='', encoding='utf-8') as handle:
        fields_of_record = list(csv.DictReader(handle))
    columns = ['line_id', *field_columns(extraction)]
    regenerated = [{c: row.get(c) for c in columns} for row in field_rows]
    if _comparable(held) != _comparable(new_lines) or \
            _comparable(fields_of_record) != _comparable(regenerated):
        raise RegisterError(f'{extraction.document_id}: replay differs from the lines of record')


def _spec(extraction):
    return {'document_id': extraction.document_id,
            'columns': json.dumps(field_columns(extraction), ensure_ascii=False)}


def _render_fields(columns, rows):
    """A field file's text, refused when over the per-file ceiling."""
    output = io.StringIO()
    writer = csv.DictWriter(output, ['line_id', *columns], lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    text = output.getvalue()
    if len(text.encode('utf-8')) > file_ceiling():
        raise RegisterError('a field file exceeds the per-file ceiling')
    return text


def admit(extractions, ledger_dir=LEDGER_DIR, *, recorded_at):
    """Append the lines of every extraction not yet admitted; replay the others.

    All or nothing across the batch: every replay, identifier check and file
    rendering (with its size ceiling) runs before the first byte is written,
    so a failed check leaves the ledger as it was. Writes go field files,
    then lines, then specs; a process that dies between them is repaired by
    running again: an edition with lines is replayed and its spec row
    restored, one without lines is appended whole, its field file rewritten.
    """
    ledger_dir = Path(ledger_dir)
    schema = load_schema()
    lines = _rows(ledger_dir, 'lines', schema)
    specs = _rows(ledger_dir, 'line_field_specs', schema)
    existing = {row['line_id'] for row in lines}
    admitted, pending = {}, []
    for extraction in extractions:
        new_lines, field_rows = to_rows(extraction, recorded_at)
        held = [row for row in lines if row['sha256'] == extraction.sha256]
        if held:
            _replay(extraction, held, ledger_dir, new_lines, field_rows)
            _add(specs, _spec(extraction), ('document_id',))   # restores one a crash lost
            admitted[extraction.document_id] = 0
            continue
        minted = [row['line_id'] for row in new_lines if row['line_id'] in existing]
        if minted:
            raise RegisterError(f'{minted[0]}: identifier already minted')
        pending.append((extraction, new_lines, field_rows))
        admitted[extraction.document_id] = len(new_lines)
    rendered = []
    for extraction, new_lines, field_rows in pending:
        lines.extend(new_lines)
        _add(specs, _spec(extraction), ('document_id',))
        rendered.append((ledger_dir / 'line-fields' / f'{extraction.document_id}.csv',
                         _render_fields(field_columns(extraction), field_rows)))
    for path, text in rendered:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
    if pending:
        _append_lines(ledger_dir, schema, lines, existing, recorded_at)
    write_table(ledger_dir, 'line_field_specs', specs, schema=schema)
    return admitted


# ---------------------------------------------------------------------------
# Run report
# ---------------------------------------------------------------------------

def snapshot_path(sha256, ledger_dir=LEDGER_DIR):
    schema = load_schema()
    rows, errors = read_table(ledger_dir, 'snapshots', schema)
    if errors:
        raise RegisterError('; '.join(errors))
    header = schema.header('snapshots')
    for row in rows:
        record = dict(zip(header, row))
        if record['sha256'] == sha256:
            return Path(ledger_dir) / 'documents' / record['storage_path']
    raise RegisterError(f'snapshot {sha256[:12]} is not in the ledger')


def run_report(extractions, reconciliation=(), reconciliation_path=None):
    tally = Counter(row['disposition'] for row in reconciliation)
    return {
        'method': METHOD, 'version': VERSION, 'ticket': '1950',
        'declared_scope': 'the grant tables of each edition: one statement per grant row, '
                          'one heading per title with exchange-rate note and per footnote',
        'documents': [{
            'document_id': e.document_id, 'sha256': e.sha256, 'adapter': e.adapter,
            'grant_rows': e.counts, 'statements': len(e.items),
            'headings': sum(1 for i in e.items if i.classification == 'heading'),
            'controls': e.controls, 'out_of_scope': e.out_of_scope,
        } for e in extractions],
        'usd_reconciliation_2023_q3': {
            'dollar_signs_in_text_layer': len(reconciliation),
            'by_disposition': dict(sorted(tally.items())),
            'file': reconciliation_path,
        } if reconciliation else None,
    }


def _write_reconciliation(rows, path):
    with Path(path).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def _extract_all(ledger_dir):
    extractions = []
    for document_id, edition in EDITIONS.items():
        extraction = extract(document_id, snapshot_path(edition.sha256, ledger_dir))
        log.info('%s: %s grant rows, %d statements', document_id, extraction.counts,
                 len(extraction.items))
        extractions.append(extraction)
    first = EDITIONS['zaf-jet-grants-register-2023-q3']
    reconciliation = layouts.usd_reconciliation(
        ruled.read_pdf(snapshot_path(first.sha256, ledger_dir)),
        next(e for e in extractions if e.sha256 == first.sha256).items)
    return extractions, reconciliation


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--ledger-dir', type=Path, default=LEDGER_DIR)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('check', help='extract and control every edition; admit nothing')
    admitting = commands.add_parser('admit', help='admit the lines of every edition')
    admitting.add_argument('--recorded-at', required=True)
    admitting.add_argument('--output', type=Path, required=True,
                           help=f'run report (JSON), e.g. {REPORT.relative_to(ROOT)}; the '
                                '2023 Q3 dollar reconciliation is written beside it')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    extractions, reconciliation = _extract_all(args.ledger_dir)
    report = run_report(extractions, reconciliation)
    if args.command == 'check':
        log.info('2023 Q3 dollar signs: %s', report['usd_reconciliation_2023_q3'])
        return
    log.info('admitted: %s', admit(extractions, args.ledger_dir, recorded_at=args.recorded_at))
    output = args.output.resolve()
    beside = output.with_name(output.stem.removesuffix('-run') + '-2023-q3-usd.csv')
    _write_reconciliation(reconciliation, beside)
    relative = beside.relative_to(ROOT) if beside.is_relative_to(ROOT) else beside
    output.write_text(json.dumps(run_report(extractions, reconciliation, str(relative)),
                                 indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
