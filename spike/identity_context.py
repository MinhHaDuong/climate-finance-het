"""Collect an existing identity's record and the statements (lines) it rests on,
from the tracked ledger (read only). Usage: identity_context.py <referent_id>"""
import csv
import glob
import json
import sys

D = 'data/jetp/'
rid = sys.argv[1]
proj = [r for r in csv.DictReader(open(D + 'projects.csv')) if r['project_id'] == rid]
refs = [r for r in csv.DictReader(open(D + 'line-referents.csv')) if r['referent_id'] == rid]
ids = {r['line_id'] for r in refs}
lines = []
for f in sorted(glob.glob(D + 'lines.d/*.csv')):
    lines += [r for r in csv.DictReader(open(f)) if r['line_id'] in ids]
ret = {}
for r in csv.DictReader(open(D + 'retrievals.csv')):
    if r['sha256']:
        ret.setdefault(r['sha256'], r['document_id'])
for ln in lines:
    ln['document_id'] = ret.get(ln['sha256'])
out = {'identity': proj, 'referent_rows': refs, 'lines': lines}
json.dump(out, open(f'spike/out/identity-{rid}.json', 'w'), ensure_ascii=False, indent=1)
print('project rows', len(proj), 'referent rows', len(refs), 'lines', len(lines))
for ln in lines:
    print(' ', ln['line_id'], ln['document_id'], ln['classification'], ln['label'][:90])
