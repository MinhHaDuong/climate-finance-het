"""Freeze projected World Bank API records from downloaded response pages."""

import argparse
import hashlib
import json
from pathlib import Path

FIELDS = ('id', 'project_name', 'status', 'boardapprovaldate', 'closingdate',
          'lendinginstr', 'sector_namecode', 'supplementprojectflg', 'url')


def freeze(paths, country, retrieved):
    """Keep all selection fields and prove pagination covers the source total."""
    rows = {}
    pages = []
    total = None
    for path in paths:
        raw = path.read_bytes()
        data = json.loads(raw)
        total = int(data['total'])
        offset = data.get('os', '0')
        pages.append({'url': f'https://search.worldbank.org/api/v2/projects?format=json&countrycode_exact={country}&rows=500&os={offset}',
                      'response_sha256': hashlib.sha256(raw).hexdigest(), 'offset': int(offset)})
        for key, row in data['projects'].items():
            if isinstance(row, dict) and row.get('id'):
                rows[key] = {field: row.get(field) for field in FIELDS}
    if len(rows) != total:
        raise ValueError(f'Incomplete API pagination: {len(rows)} of {total}')
    return {'publisher': 'World Bank', 'retrieved_on': retrieved, 'country_code': country,
            'source_total': total, 'projection_fields': FIELDS, 'pages': pages,
            'records': sorted(rows.values(), key=lambda row: row['id'])}


def main():
    """Write one source-field snapshot with pagination provenance."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', nargs='+', type=Path, required=True)
    parser.add_argument('--country', required=True)
    parser.add_argument('--retrieved-on', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    payload = freeze(args.input, args.country, args.retrieved_on)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
