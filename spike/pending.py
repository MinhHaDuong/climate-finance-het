"""Pending list per extraction spec s2: held documents whose snapshots have no lines.

Join: documents -> retrievals.sha256 -> lines.sha256 (snapshots.csv has no document_id).
"""
import collections
import csv
import glob

D = 'data/jetp/'
docs = {r['document_id']: r for r in csv.DictReader(open(D + 'documents.csv'))}
ret = list(csv.DictReader(open(D + 'retrievals.csv')))
snaps = {r['sha256']: r for r in csv.DictReader(open(D + 'snapshots.csv'))}
lines_by_sha = collections.Counter()
for f in sorted(glob.glob(D + 'lines.d/*.csv')):
    for r in csv.DictReader(open(f)):
        lines_by_sha[r['sha256']] += 1
doc_shas = collections.defaultdict(set)
for r in ret:
    if r['sha256']:
        doc_shas[r['document_id']].add(r['sha256'])
out = csv.writer(open('spike/out/pending.csv', 'w'))
out.writerow(['document_id', 'country', 'document_type', 'language', 'n_snapshots',
              'n_lines', 'sha256s', 'content_types'])
n = 0
for d, r in docs.items():
    shas = sorted(doc_shas.get(d, []))
    nl = sum(lines_by_sha[s] for s in shas)
    if shas and nl == 0:
        n += 1
    out.writerow([d, r['country'], r['document_type'], r['language'], len(shas), nl,
                  ' '.join(shas), ' '.join(snaps.get(s, {}).get('content_type', '?') for s in shas)])
print('documents', len(docs), 'pending (snapshotted, zero lines):', n)
