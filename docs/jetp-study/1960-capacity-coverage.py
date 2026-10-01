"""Coverage of the proposed capacity terms on the panel v1 rows (ticket 1960, item 3).

Every value carrying an energy or power unit that a v1 member wrote, in the
"other" slot or the amount field of a resolved row, is mapped to (quantity
kind, unit, basis) or flagged. A capacity label whose value carries no
recognised unit is flagged. Run from the repository root; writes the JSON
beside this script.
"""
import collections
import csv
import gzip
import json
import re

ROWS = 'data/jetp/reference/panel-v1/rows.csv.gz'
OUTPUT = 'docs/jetp-study/1960-capacity-coverage.json'
NUM = r'(\d[\d\s.,]*)'
# An optional hyphen ("30-kW"), an SI prefix, the unit, then a suffix:
# p and c (crête) for peak, th or t for thermal, e for electric.
UNIT = re.compile(NUM + r'\s*-?\s*(k|K|M|G|T)?\s*(Wh|WH|wh|VA|kva|KVA|Ah|AH|W|w|J)(p|c|e|th|t)?\b')
CAPACITY_LABEL = re.compile(r'capacit|puissance|công suất|power|productible', re.I)


def kind_of(unit, suffix, context):
    u = unit.lower()
    if u in ('wh', 'j'):
        return 'energy'
    if u in ('va', 'kva'):
        return 'apparent power'
    if u == 'ah':
        return 'electric charge'
    if suffix in ('th', 't') or re.search(r'thermi|thermal|nhiệt|heat', context, re.I):
        return 'thermal power'
    if suffix in ('p', 'c'):
        return 'peak electric power'
    return 'electric power'


def basis_of(context):
    if re.search(r'\bnet\b|\bnette?\b|thuần', context, re.I):
        return 'net'
    if re.search(r'\bgross\b|\bbrute?\b|installée|installed|nameplate|lắp đặt', context, re.I):
        return 'gross'
    return 'unstated'


def scan(rows):
    hits, flags, seen = [], [], set()
    for r in rows:
        if r['status'] != 'resolved':
            continue
        items = [(o['name'], o['value']) for o in json.loads(r['other'])] if r['other'] else []
        items.append(('amount', r['amount']))
        for name, value in items:
            text = f'{name}: {value}'
            matched = False
            for m in UNIT.finditer(value or ''):
                matched = True
                if (r['document_id'], value) in seen:
                    continue
                seen.add((r['document_id'], value))
                _, prefix, unit, suffix = m.groups()
                hits.append({'document': r['document_id'], 'printed': value.strip()[:60],
                             'field': name[:30], 'kind': kind_of(unit, suffix, text),
                             'unit': (prefix or '') + unit + (suffix or ''), 'basis': basis_of(text)})
            if not matched and name != 'amount' and CAPACITY_LABEL.search(name):
                flags.append({'document': r['document_id'], 'printed': text[:80],
                              'reason': 'capacity label, no recognised unit'})
    return hits, flags


def main():
    with gzip.open(ROWS, 'rt', encoding='utf-8') as fh:
        hits, flags = scan(csv.DictReader(fh))
    print('mapped', len(hits), 'flagged', len(flags))
    print(collections.Counter(h['kind'] for h in hits))
    print(collections.Counter(h['basis'] for h in hits))
    print(collections.Counter(h['unit'] for h in hits).most_common())
    for f in flags:
        print('  flagged', f)
    with open(OUTPUT, 'w', encoding='utf-8') as fh:
        json.dump({'mapped': hits, 'flagged': flags}, fh, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
