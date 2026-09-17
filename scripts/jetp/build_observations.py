"""Build the per-country ledger observation views for the observatory.

The second stage-two product.  The M1a inventories freeze what a source
published about its own projects; these are the ledger rows analysts wrote from
those same documents, under a different schema.  Two extractions, served side
by side and never added together: a row here and a row there can describe the
same paragraph of the same PDF.

One invocation writes all four countries, like the M1a writer and unlike the
single ``--view`` of ``build_observatory.py``: the four files share one pass
over the three tables and one collection registry.
"""

import argparse
import json
from pathlib import Path

from jetp._m1a_document_links import index_documents
from jetp._observatory_data import observation_entry
from jetp.build_observatory import documents_data, read_inputs

ROOT = Path(__file__).resolve().parents[2]
COUNTRIES = ('ZAF', 'IDN', 'VNM', 'SEN')
# Fixed order, and it is the served order: table, then the CSV's own row order.
# No further sort, so a regeneration is readable as a diff and a row keeps the
# position its ledger gives it.
OBSERVATION_TABLES = ('events', 'implementation-events', 'project-source-links')


def build_registry(root, tables):
    """Collapse the collection registry the way the Documents page does.

    ``documents_data`` already reads ``tables['manifest']`` and marks what is
    archived on disk; ``index_documents`` then applies the shared-identifier
    tie-break of ticket 0853.  Going through both means a row here and the same
    row on the Documents page resolve to the same file, rather than to whichever
    collection attempt a dict comprehension happened to keep last.
    """
    return index_documents(documents_data(root, tables)['documents'])


def observations_by_country(tables, registry):
    """Group every ledger row under the country its own row names.

    A country with no row in a table gets an empty list, not a missing key: the
    absence is a fact about the ledger — Viet Nam has only link rows, and
    neither Viet Nam nor South Africa has an implementation event — and a view
    that dropped it would make the page unreachable for that country.
    """
    result = {code: [] for code in COUNTRIES}
    for table in OBSERVATION_TABLES:
        for row in tables[table]:
            country = row['country']
            if country not in result:
                raise ValueError(f'Unsupported observation country: {country}')
            result[country].append(observation_entry(row, table, registry))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=ROOT / 'deliverables' / 'jetp-observatory' / 'data' / 'observations',
    )
    args = parser.parse_args()
    tables = read_inputs(ROOT)
    by_country = observations_by_country(tables, build_registry(ROOT, tables))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for code, entries in by_country.items():
        (args.output_dir / f'{code}.json').write_text(
            json.dumps(entries, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
        )


if __name__ == '__main__':
    main()
