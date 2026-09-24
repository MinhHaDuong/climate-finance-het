"""Serve the Web Archive captures and the publisher link checks (ticket 0925).

One invocation, one served file, one table: ``--view web-archive`` serves
``data/jetp/web-archive-captures.csv`` as ``{"captures": [...]}`` and
``--view publisher-links`` serves ``data/jetp/publisher-link-checks.csv`` as
``{"checks": [...]}``, each row as the CSV holds it, in key order. Neither
is joined here to the collection registry: the page joins both to
``documents.json`` on the document's address at read time, the way it joins
the stage-two views (ticket 0858). A separate script from
``build_observatory.py``, so a new capture or a monthly check rebuilds these
two files and leaves the other views and their recorded input hashes alone.
A missing table is served empty — the site then shows no copy and no dead
link — so a checkout that never ran either step still builds.
"""

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIEWS = {
    'web-archive': ('captures', 'web-archive-captures.csv', ('source_id', 'url')),
    'publisher-links': ('checks', 'publisher-link-checks.csv', ('url',)),
}


def view(ledger_dir, name):
    key, filename, order = VIEWS[name]
    path = Path(ledger_dir) / filename
    rows = []
    if path.is_file():
        with path.open(encoding='utf-8', newline='') as handle:
            rows = [{k: (v or None) for k, v in row.items()} for row in csv.DictReader(handle)]
    return {key: sorted(rows, key=lambda row: tuple(row[k] or '' for k in order))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--view', choices=sorted(VIEWS), required=True)
    parser.add_argument('--ledger-dir', type=Path, default=ROOT / 'data/jetp')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    result = view(args.ledger_dir, args.view)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
