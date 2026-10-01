"""Coverage of the proposed capacity terms on the panel v1 rows (ticket 1960, item 3).

Every value carrying an energy or power unit that a v1 member wrote, in the
"other" slot or a field, is mapped to (quantity kind, unit, basis) or flagged.
"""
import collections
import csv
import gzip
import json
import re

ROWS = 'data/jetp/reference/panel-v1/rows.csv.gz'  # run from the repository root
NUM = r'(\d[\d\s.,]*)'
UNIT = re.compile(NUM + r'\s*(k|K|M|G|T)?\s*(Wh|WH|wh|VA|kva|KVA|Ah|AH|W|w|J)(p|c|e|th|t)?\b')
PREFIX = {None: 1, 'k': 1e3, 'K': 1e3, 'M': 1e6, 'G': 1e9, 'T': 1e12}


def kind_of(unit, suffix, context):
    u = unit.lower()
    if u == 'wh' or u == 'j':
        return 'energy'
    if u == 'va' or u == 'kva':
        return 'apparent power'
    if u == 'ah':
        return 'electric charge'
    if suffix in ('th', 't') or re.search(r'thermi|thermal|nhiệt|heat', context, re.I):
        return 'thermal power'
    return 'electric power'


def basis_of(context):
    if re.search(r'\bnet\b|\bnette?\b|thuần', context, re.I):
        return 'net'
    if re.search(r'\bgross\b|\bbrute?\b|installée|installed|nameplate|lắp đặt', context, re.I):
        return 'gross'
    return 'unstated'


hits, flags = [], []
seen = set()
with gzip.open(ROWS, 'rt', encoding='utf-8') as fh:
    for r in csv.DictReader(fh):
        if r['status'] != 'resolved':
            continue
        items = [(o['name'], o['value']) for o in json.loads(r['other'])] if r['other'] else []
        items.append(('amount', r['amount']))
        for name, value in items:
            text = f'{name}: {value}'
            for m in UNIT.finditer(value or ''):
                key = (r['document_id'], value)
                if key in seen:
                    continue
                seen.add(key)
                number, prefix, unit, suffix = m.groups()
                if unit.lower() == 'w' and prefix is None and not re.search(r'puissance|power|capacit|công suất|W\b', name, re.I):
                    flags.append((r['document_id'], text, 'bare W without a capacity label'))
                    continue
                hits.append({'document': r['document_id'], 'printed': value.strip()[:60], 'field': name[:30],
                             'kind': kind_of(unit, suffix, text), 'unit': (prefix or '') + unit + (suffix or ''),
                             'basis': basis_of(text)})
        # capacity-like names without a recognised unit
        for name, value in items[:-1]:
            if re.search(r'capacit|puissance|công suất|power|productible', name, re.I) and not UNIT.search(value or ''):
                flags.append((r['document_id'], f'{name}: {value}'[:80], 'capacity label, no recognised unit'))

print('mapped', len(hits))
print(collections.Counter(h['kind'] for h in hits))
print(collections.Counter(h['basis'] for h in hits))
print(collections.Counter(h['unit'] for h in hits).most_common(20))
for h in hits[:40]:
    print(' ', h['document'][:24], '|', h['field'], '|', h['printed'], '->', h['kind'], h['unit'], h['basis'])
print('flagged', len(flags))
for f in flags[:40]:
    print(' ', f)
json.dump({'mapped': hits, 'flagged': flags}, open('docs/jetp-study/1960-capacity-coverage.json', 'w'),
          ensure_ascii=False, indent=1)
