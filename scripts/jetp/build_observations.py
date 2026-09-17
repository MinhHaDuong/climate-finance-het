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

from jetp._observatory_data import observation_entry
from jetp.build_observatory import read_inputs

ROOT = Path(__file__).resolve().parents[2]
COUNTRIES = ('ZAF', 'IDN', 'VNM', 'SEN')
# Fixed order, and it is the served order: table, then the CSV's own row order.
# No further sort, so a regeneration is readable as a diff and a row keeps the
# position its ledger gives it.
OBSERVATION_TABLES = ('events', 'implementation-events', 'project-source-links')


def attempt_rank(row):
    """Rank one collection attempt by what it can address, never by disk state.

    An attempt that recorded no digest cannot address a document at all; among
    those that did, a completed collection outranks a revalidation.
    """
    if not row.get('sha256'):
        return 0
    return 2 if row.get('status') == 'collected' else 1


def build_registry(tables):
    """Collapse the collection registry to one attempt per source identifier.

    Twenty-one identifiers carry several attempts (ticket 0853) and six of them
    disagree on the digest, so the choice has to be made rather than left to the
    order of ``manifest.csv``.

    It is made on the digest, not on what happens to be staged on disk.  What
    this view publishes is a fingerprint; the local path is the renderer's
    business, resolved from ``data/documents.json`` in the browser.  Ranking on
    an archived copy — as ``index_documents`` does, correctly, for a page whose
    job is to open a file — would make the published value depend on whether
    the DVC snapshot happened to be checked out when the build ran, and one
    Senegal source did flip that way during this ticket's own development.
    """
    chosen = {}
    for row in tables['manifest']:
        source_id = row['source_id']
        if source_id not in chosen or attempt_rank(row) > attempt_rank(chosen[source_id]):
            chosen[source_id] = row
    return {
        source_id: {'sha256': row['sha256'] or None}
        for source_id, row in chosen.items()
    }


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
    by_country = observations_by_country(tables, build_registry(tables))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for code, entries in by_country.items():
        (args.output_dir / f'{code}.json').write_text(
            json.dumps(entries, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
        )


if __name__ == '__main__':
    main()
