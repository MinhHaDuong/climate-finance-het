"""Extract the pinned Q1 register and complete selected report tables losslessly."""

import hashlib
from pathlib import Path

import pdfplumber

from jetp.build_zaf_investment_register import parse_register_html


def extract_inventory(documents: Path, policy: dict) -> dict:
    """Require exact source bytes and table shapes before accepting any source row."""
    sources = {row['role']: row for row in policy['sources']}
    paths = {role: Path(documents) / source['storage_path'] for role, source in sources.items()}
    for role, path in paths.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != sources[role]['document_sha256']:
            raise ValueError(f'Unexpected {role} source bytes')
    if pdfplumber.__version__ != policy['parser_version']:
        raise ValueError('Pinned pdfplumber parser version required')
    register = parse_register_html(paths['register'].read_text())
    if len(register) != policy['register_row_count']:
        raise ValueError('Incomplete selected register inventory')
    report_rows, contexts = [], {}
    with pdfplumber.open(paths['report']) as pdf:
        for spec in policy['report_tables']:
            page = pdf.pages[spec['page'] - 1]
            matches = [table for table in page.extract_tables()
                       if table and table[0][0] == spec['first_header']]
            if len(matches) != 1:
                raise ValueError(f"Ambiguous extraction for {spec['table_id']}")
            table = matches[0]
            if len(table) != spec['table_rows'] or any(len(row) != spec['columns'] for row in table):
                raise ValueError(f"Incomplete selected report inventory {spec['table_id']}")
            contexts[spec['table_id']] = page.extract_text()
            for ordinal, cells in enumerate(table[spec['header_rows']:], 1):
                report_rows.append({
                    'inventory_id': spec['table_id'], 'ordinal': ordinal, 'pages': [spec['page']],
                    'locator': f"PDF page {spec['page']}, {spec['table_id']}, row {ordinal + spec['header_rows']}",
                    'source_role': 'report', 'perimeter': spec['perimeter'],
                    'source_fields': {'headers': table[:spec['header_rows']], 'cells': cells},
                    'source_wording': ' | '.join(cell or '' for cell in cells),
                    'classification': 'reported_financial_or_count_position',
                    'eligible_for_account': False})
    return {'register_rows': register, 'report_rows': report_rows, 'report_context': contexts}
