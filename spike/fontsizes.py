"""Diagnostic: font-size histogram of a snapshot's words (to calibrate the headline rule)."""
import collections
import csv
import sys

import pdfplumber

snaps = {r['sha256']: r for r in csv.DictReader(open('data/jetp/snapshots.csv'))}
with pdfplumber.open('data/jetp/documents/' + snaps[sys.argv[1]]['storage_path']) as pdf:
    for i, pg in enumerate(pdf.pages, 1):
        c = collections.Counter()
        ex = {}
        for w in pg.extract_words(extra_attrs=['size']):
            k = round(w['size'], 1)
            c[k] += 1
            ex.setdefault(k, []).append(w['text'])
        for k, n in sorted(c.items()):
            print(i, k, n, ' '.join(ex[k][:10]))
