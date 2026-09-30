"""Probe candidate snapshots: format from bytes (spec s5), pages, text-layer size."""
import csv
import hashlib
import sys

import pdfplumber

snaps = {r['sha256']: r for r in csv.DictReader(open('data/jetp/snapshots.csv'))}
for sha in sys.argv[1:]:
    p = 'data/jetp/documents/' + snaps[sha]['storage_path']
    b = open(p, 'rb').read()
    ok = hashlib.sha256(b).hexdigest() == sha
    magic = b[:5]
    with pdfplumber.open(p) as pdf:
        n = len(pdf.pages)
        chars = [len(pg.extract_text() or '') for pg in pdf.pages]
    print(sha[:12], 'hash_ok', ok, 'magic', magic, 'declared', snaps[sha]['content_type'],
          'pages', n, 'chars/page', chars[:12], 'total', sum(chars))
