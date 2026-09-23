"""Ingest the six M1a document extracts as ledger lines (ticket 0873).

Step 2 of the migration (``docs/jetp-ledger-migration.md``): the published
line is the primary unit. The pinned extracts the M1a builder used to read,
the South Africa register sidecar, ``plan-projects.csv`` and the Viet Nam
release, become rows of ``lines``, one ``line-fields/<document_id>.csv`` per
document with the document's own columns, verbatim, one ``line-field-specs``
row per document declaring those columns, and one ``routes`` row per
identifier the M1a export served for a plan or Viet Nam row. The M1a view
(``build_m1a_inventories.py``) is then read from these tables.

Decisions the ingestion takes, each visible in its output:

- A ``line_id`` is ``<document_id>-<table>-<ordinal>`` (storage contract
  section 1). The table is the one the extractor named for the publisher's
  table: the register tab for South Africa, the annex for Viet Nam, the
  technology group for a plan (one printed appendix or annex each, checked
  here). The ordinal is the row's position in that table, in extraction order.
- Classification per layer comes from the layer manifest
  (``config/jetp-m1a-inventories.json``): ``register_allocation`` for the
  register, ``named_item`` for the Indonesian plan lines, ``submission`` for
  both Senegalese documents; Viet Nam keeps its source classification through
  ``VNM_CLASSIFICATION`` (73 programme rows are ``heading``, 181 unresolved
  rows ``unnamed_item``, 25 named rows ``named_item``).
- The register's status letter is copied verbatim into ``own_status`` with
  axis ``delivery``; no other document prints a status column.
- A plan locator names the printed page and the row; where the layer declares
  the printed-to-PDF page offset, the PDF page is added (ticket 0861). Where
  the publisher printed the same row number twice in one table, the second
  line's locator adds its physical row (``PHYSICAL_ROW``), so no two lines
  claim the same place in the same bytes; the M1a view shows the printed
  locator.
- A locator that names no place finer than the document is refused.
- The fields of a plan line are the extractor's columns that transcribe the
  printed row; the columns that record our own reconciliation
  (``canonical_project_id``, ``reconciliation_status``) are identity
  decisions for ticket 0875, and those the ledger keeps on the line itself
  (country, fingerprint, locator, notes) are not repeated. The fields of a
  Viet Nam line are its printed cells under the annex's printed header; the
  three annexes print different headers, so the document's columns are their
  union, in order of first appearance.
- The register's method notes are not lines of the register tab: the OANDA
  exchange-rate note and the United States note are footnotes of the
  allocation summary table, and the one pro-rating is a sentence of one row's
  own description, kept verbatim in its fields. No line of these six extracts
  therefore ``groups`` another yet.

The output is a record, written once and reviewed as a diff; rerunning the
ingestion on the same pinned inputs rewrites the same bytes.
"""

import argparse
import csv
import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path

from jetp._ledger_headers import LEDGER_DIR, load_schema, write_table
from jetp.build_0818_zaf_q1_reconciliation import SOURCE_FIELDS as ZAF_FIELDS
from jetp.build_m1a_inventories import PHYSICAL_ROW, VNM_CLASSIFICATION

ROOT = Path(__file__).resolve().parents[2]
RECORDED_AT = '2026-09-23'

# The register's one table: the dashboard's "Overall - Data" tab.
ZAF_TABLE = 'overall-data'
ZAF_STATUS_AXIS = 'delivery'

# Columns of plan-projects.csv that transcribe the printed row.
PLAN_FIELDS = (
    'technology_group', 'priority_tier', 'ordinal', 'project_name', 'system',
    'estimated_start', 'capacity_value', 'capacity_unit',
    'estimated_investment_usd_mn', 'natural_retirement_year',
    'estimated_retirement_year', 'ruptl',
)

# Printed headers of the Resource Mobilisation Plan's three annexes (PDF pages
# 155, 159 and 175), a header printed over several lines joined by a space.
VNM_HEADERS = {
    'I.1': ('No.', 'Name of Project', 'Location', 'Capacity',
            'Expected commissioning year', 'Note'),
    'I.2': ('No', 'Name of plant/construction', 'Location', 'Capacity',
            'Expected commissioning year', 'Information/ Source/ Concept Note'),
    'II': ('No.', 'Project name, task group', 'Period', 'Source', 'Note'),
}

# A locator that names only the document, not a place in it.
_WHOLE_DOCUMENT = re.compile(r'(?i)\b(whole|entire|full)\s+(report|document|file|plan)\b')
_PRINTED_PAGE = re.compile(r'\bp\. ([0-9]+)\b')


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _slug(text):
    return re.sub(r'[^a-z0-9.]+', '-', str(text).lower()).strip('-')


def check_locator(locator):
    """Refuse a locator too coarse to name one place in the bytes."""
    text = (locator or '').strip()
    if not text or not re.search(r'\d', text) or _WHOLE_DOCUMENT.search(text):
        raise ValueError(f'locator names no place finer than the document: {locator!r}')
    return locator


def with_pdf_page(locator, offset):
    """Add the PDF page a printed ``p. N`` maps to, when the layer declares it."""
    if offset is None:
        return locator
    match = _PRINTED_PAGE.search(locator)
    if not match:
        raise ValueError(f'locator names no printed page to anchor: {locator!r}')
    return f'{locator}; PDF page {int(match.group(1)) + int(offset)}'


def _require_input(root, spec, path_key='input_path', sha_key='input_sha256'):
    path = Path(root) / str(spec[path_key])
    if not path.is_file() or _sha256(path) != spec[sha_key]:
        raise ValueError(f'frozen M1a input hash mismatch: {path}')
    return path


def _read_csv(path):
    with Path(path).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def _line(spec, table, ordinal, locator, label, classification, **extra):
    return {
        'line_id': f"{spec['source_id']}-{table}-{ordinal}",
        'country': spec['country'],
        'sha256': spec['source_sha256'],
        'locator': check_locator(locator),
        'ordinal': ordinal,
        'label': label or None,
        'classification': classification,
        'recorded_at': RECORDED_AT,
        **extra,
    }


def _zaf_lines(root, spec):
    rows = _read_csv(_require_input(root, spec))
    fields = _read_csv(_require_input(root, spec, 'fields_input_path', 'fields_input_sha256'))
    if len(rows) != len(fields):
        raise ValueError('South Africa register sidecar row count does not match')
    lines, line_fields = [], []
    for position, (row, field_row) in enumerate(zip(rows, fields, strict=True), start=1):
        if int(row['ordinal']) != position or field_row['ordinal'] != row['ordinal']:
            raise ValueError('South Africa register sidecar is not aligned by ordinal')
        if row['document_sha256'] != spec['source_sha256']:
            raise ValueError(f"source document hash changed: {spec['layer_id']}")
        line = _line(spec, ZAF_TABLE, position, row['locator'], field_row['Project Name'],
                     spec['classification'], own_status=field_row['Status'] or None,
                     own_status_axis=ZAF_STATUS_AXIS if field_row['Status'] else None)
        lines.append(line)
        line_fields.append({'line_id': line['line_id'],
                            **{name: field_row[name] for name in ZAF_FIELDS}})
    return lines, line_fields, list(ZAF_FIELDS), {}


def _plan_lines(root, spec, cache):
    path = _require_input(root, spec)
    rows = [row for row in cache.setdefault(path, _read_csv(path))
            if row['country'] == spec['country'] and row['source_id'] == spec['source_id']]
    offset = spec.get('printed_to_pdf_page_offset')
    lines, line_fields, routes = [], [], {}
    counters, taken, printed_table = {}, set(), {}
    for row in rows:
        if row['document_sha256'] != spec['source_sha256']:
            raise ValueError(f"source document hash changed: {spec['layer_id']}")
        table = _slug(row['technology_group'])
        # One technology group is one printed table: the printed part of the
        # locator before its row (or quick-win) number never changes within it.
        printed = re.split(r', (?:printed )?row |, QW|, p\. ', row['locator'])[0]
        if printed_table.setdefault(table, printed) != printed:
            raise ValueError(f"{spec['source_id']}: table {table} spans two printed tables")
        counters[table] = counters.get(table, 0) + 1
        ordinal = counters[table]
        if str(ordinal) != row['ordinal']:
            raise ValueError(f"{row['plan_project_id']}: ordinal {row['ordinal']} is not "
                             f'position {ordinal} of table {table}')
        locator = with_pdf_page(row['locator'], offset)
        if locator in taken:
            locator += PHYSICAL_ROW.format(ordinal)
        taken.add(locator)
        line = _line(spec, table, ordinal, locator, row['project_name'],
                     spec['classification'], notes=row['notes'] or None)
        lines.append(line)
        line_fields.append({'line_id': line['line_id'],
                            **{name: row[name] for name in PLAN_FIELDS}})
        routes[row['plan_project_id']] = line['line_id']
    return lines, line_fields, list(PLAN_FIELDS), routes


def _vnm_lines(root, spec):
    payload = json.loads(_require_input(root, spec).read_text(encoding='utf-8'))
    positions = payload.get('inventory_positions')
    if not isinstance(positions, list):
        raise ValueError('Viet Nam migration lacks inventory_positions')
    columns = []
    for header in VNM_HEADERS.values():
        columns.extend(name for name in header if name not in columns)
    lines, line_fields, routes = [], [], {}
    counters = {}
    for row in positions:
        if row['evidence']['document_sha256'] != spec['source_sha256']:
            raise ValueError('Viet Nam source document hash changed')
        if str(row.get('value')) != spec['reported_status']:
            raise ValueError(f"{row['inventory_id']}: value {row.get('value')!r} is not "
                             f"the layer's {spec['reported_status']!r}")
        header = VNM_HEADERS[row['annex']]
        if len(row['source_cells']) != len(header):
            raise ValueError(f"{row['inventory_id']}: {len(row['source_cells'])} cells "
                             f"under a {len(header)}-column header")
        table = _slug(f"annex-{row['annex']}")
        counters[table] = counters.get(table, 0) + 1
        ordinal = counters[table]
        if ordinal != row['ordinal']:
            raise ValueError(f"{row['inventory_id']}: ordinal is not position {ordinal}")
        line = _line(spec, table, ordinal, row['locator'], row['source_wording'],
                     VNM_CLASSIFICATION[row['classification']])
        lines.append(line)
        cells = dict(zip(header, row['source_cells'], strict=True))
        line_fields.append({'line_id': line['line_id'],
                            **{name: cells.get(name, '') for name in columns}})
        routes[row['inventory_id']] = line['line_id']
    return lines, line_fields, columns, routes


def ingest(root=ROOT, config_path=None):
    """The ledger rows of the six extracts: lines, fields per document, specs, routes."""
    root = Path(root)
    config = json.loads(Path(config_path or root / 'config' / 'jetp-m1a-inventories.json')
                        .read_text(encoding='utf-8'))
    lines, fields, specs, routes = [], {}, [], []
    cache = {}
    for spec in config['layers']:
        adapter = spec['adapter']
        if adapter == 'zaf_register':
            layer = _zaf_lines(root, spec)
        elif adapter == 'plan_projects':
            layer = _plan_lines(root, spec, cache)
        elif adapter == 'vnm_rmp':
            layer = _vnm_lines(root, spec)
        else:
            raise ValueError(f'unknown M1a adapter: {adapter}')
        layer_lines, layer_fields, columns, layer_routes = layer
        if len(layer_lines) != spec['expected_rows']:
            raise ValueError(f"frozen layer row count changed: {spec['layer_id']}")
        lines.extend(layer_lines)
        fields[spec['source_id']] = (columns, layer_fields)
        specs.append({'document_id': spec['source_id'],
                      'columns': json.dumps(columns, ensure_ascii=False)})
        routes.extend({'old_id': old, 'kind': 'line', 'new_id': new}
                      for old, new in layer_routes.items())
    _check_unique(lines, ('line_id',))
    _check_unique(lines, ('sha256', 'locator'))
    _check_unique(routes, ('old_id',))
    return {'lines': lines, 'line_fields': fields,
            'line_field_specs': sorted(specs, key=lambda row: row['document_id']),
            'routes': routes}


def _check_unique(rows, key):
    seen = set()
    for row in rows:
        value = tuple(row[k] for k in key)
        if value in seen:
            raise ValueError(f"two lines claim {'/'.join(key)} = {'/'.join(map(str, value))}")
        seen.add(value)


def write_ledger(tables, ledger_dir=LEDGER_DIR):
    """Write the ingested tables under a ledger directory; return the paths."""
    ledger_dir = Path(ledger_dir)
    schema = load_schema()
    written = []
    for table in ('lines', 'line_field_specs', 'routes'):
        written += write_table(ledger_dir, table, tables[table], schema=schema)
    directory = ledger_dir / 'line-fields'
    directory.mkdir(parents=True, exist_ok=True)
    for document_id, (columns, rows) in sorted(tables['line_fields'].items()):
        path = directory / f'{document_id}.csv'
        with path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.writer(handle, lineterminator='\n')
            writer.writerow(['line_id', *columns])
            writer.writerows([row['line_id'], *(row[c] for c in columns)] for row in rows)
        written.append(path)
    return written


def main(argv: Sequence[str] | None = None) -> None:
    # Deliberate script-io exception: this writes three ledger tables and one
    # line-fields file per document into one directory, not one file to one
    # path, so the single --output contract of script_io_args does not fit.
    # Same multi-output precedent as build_evidence_layer.py.
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--output-dir', type=Path, default=LEDGER_DIR,
                        help='ledger directory the tables are written under')
    parser.add_argument('--config', type=Path)
    args = parser.parse_args(argv)
    write_ledger(ingest(ROOT, args.config), args.output_dir)


if __name__ == '__main__':
    main()
