"""Print a compact view of a document's scope, statements, checks and review set."""
import collections
import json
import sys

d = f'spike/out/{sys.argv[1]}'
sc = json.load(open(f'{d}/scope.json'))
print('FIELDS', [(f['name'], f['printed']) for f in sc['field_list']])
print('SCOPE OUT', [o['part'][:60] for o in sc['scope_out']])
loc = json.load(open(f'{d}/located.json'))
print('CLASSES', collections.Counter(s['classification'] for s in loc['kept']))
try:
    ch = {c['ordinal']: c for c in json.load(open(f'{d}/checks.json'))['checks']}
except FileNotFoundError:
    ch = {}
n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
for s in loc['kept'][:n]:
    c = ch.get(s['ordinal'], {})
    print(f"#{s['ordinal']} p{s['page']} [{s['classification']}] {s['label'][:90]!r}")
    print('    fields', json.dumps(s.get('fields'), ensure_ascii=False)[:220], '| group', (s.get('group_anchor') or '')[:40])
    print('    check', c.get('stance'), c.get('likelihood'), c.get('confidence'), (c.get('problem') or '')[:150])
try:
    rv = json.load(open(f'{d}/review_set.json'))
    print('DISAGREEMENTS')
    for s in rv['disagreements']:
        print(f"  #{s['ordinal']} {s['_check']['stance']} {s['_check']['likelihood']}/{s['_check']['confidence']}: {s['label'][:70]!r} -- {(s['_check'].get('problem') or '')[:160]}")
    print('MISSED')
    for m in rv['missed']:
        print(f"  p{m['page']} {m['label'][:90]!r} -- {m['why'][:100]}")
except FileNotFoundError:
    pass
