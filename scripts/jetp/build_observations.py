"""Serve current JETP observations and cited referents from ledger v2."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from jetp._country_views_v2 import (
    _current,
    _document_index,
    _line_documents,
    load_country_inputs,
)
from jetp._m1a_document_links import pdf_page_of

ROOT = Path(__file__).resolve().parents[2]
COUNTRIES = ('ZAF', 'IDN', 'VNM', 'SEN')
SUBJECT_IDS = {'project': 'project_id', 'agreement': 'agreement_id',
               'asset': 'asset_id', 'perimeter': 'perimeter_id'}


def served_views(tables):
    """Keep statements and identity citations distinct, each with one source."""
    sources, by_digest = _document_index(tables)
    lines = {row['line_id']: row for row in tables['lines']}
    line_documents = _line_documents(lines, by_digest)
    subjects = defaultdict(set)
    for kind, key in SUBJECT_IDS.items():
        for row in tables[kind + 's']:
            if row.get('country') in COUNTRIES:
                subjects[row['country']].add((kind, row[key]))
    observations = _current(tables['observations'], 'observation_id')
    referents = _current(tables['line_referents'], 'referent_row_id')
    views = {}
    for code in COUNTRIES:
        entries = []

        def cited_line(line_id):
            line = lines.get(line_id)
            source = line_documents.get(line_id)
            if line is None or source is None or source not in sources:
                raise ValueError(f'{code}: cited line lacks one document: {line_id}')
            return line, source

        for row in observations:
            if (row['subject_kind'], row['subject_id']) not in subjects[code]:
                continue
            line, source = cited_line(row['line_id'])
            entries.append(dict(
                table='observations', kind=f"{row['axis'] or 'reported'} / {row['measure']}",
                observation_id=row['observation_id'], country=code,
                axis=row['axis'], measure=row['measure'],
                subject_kind=row['subject_kind'], subject_id=row['subject_id'],
                source_id=source, line_id=row['line_id'],
                locator=line['locator'], pdf_page=pdf_page_of(line['locator']),
                sha256=line['sha256'], verification=row['status'],
                value=row['value'], unit=row['unit'], currency=row['currency'],
                own_status=row['own_status'], notes=row['notes'],
            ))
        for row in referents:
            if (row['referent_kind'], row['referent_id']) not in subjects[code]:
                continue
            line, source = cited_line(row['line_id'])
            entries.append(dict(
                table='line-referents', kind=f"{row['referent_kind']} identity",
                referent_row_id=row['referent_row_id'], country=code,
                subject_kind=row['referent_kind'], subject_id=row['referent_id'],
                source_id=source, line_id=row['line_id'],
                locator=line['locator'], pdf_page=pdf_page_of(line['locator']),
                sha256=line['sha256'], verification=row['status'],
                label=line['label'], method=row['method'], notes=row['notes'],
            ))
        views[code] = entries
    return views


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'deliverables/jetp-observatory/data/observations')
    args = parser.parse_args()
    views = served_views(load_country_inputs(ROOT / 'data/jetp'))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for code, entries in views.items():
        (args.output_dir / f'{code}.json').write_text(
            json.dumps(entries, ensure_ascii=False, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
