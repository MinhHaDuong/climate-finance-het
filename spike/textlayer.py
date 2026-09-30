"""Stage 1: snapshot bytes -> text layer (extraction spec s5).

The text layer names the snapshot and the adapter + version that produced it.
Adapter: poppler pdftotext (reading-order mode), one call per page.
pdfplumber 0.11.9 was tried first and interleaved the newsletter's three
columns line by line (see REPORT.md); poppler's default mode keeps columns.
Output: spike/out/textlayer/<sha>.json (pages[{index, folio, text, joined}])
and a numbered .txt view given to the readers.
"""
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time

snaps = {r['sha256']: r for r in csv.DictReader(open('data/jetp/snapshots.csv'))}
os.makedirs('spike/out/textlayer', exist_ok=True)
ADAPTER = 'poppler-pdftotext'
ADAPTER_VERSION = subprocess.run(['pdftotext', '-v'], capture_output=True, text=True).stderr.split('\n')[0].split()[-1]


def ws(s):
    return re.sub(r'\s+', ' ', s).strip()


def npages(p):
    out = subprocess.run(['pdfinfo', p], capture_output=True, text=True).stdout
    return int(re.search(r'Pages:\s+(\d+)', out).group(1))


for sha in sys.argv[1:]:
    t0 = time.time()
    p = 'data/jetp/documents/' + snaps[sha]['storage_path']
    b = open(p, 'rb').read()
    assert hashlib.sha256(b).hexdigest() == sha
    fmt = 'pdf' if b[:5] == b'%PDF-' else 'unknown'
    pages = []
    for i in range(1, npages(p) + 1):
        txt = subprocess.run(['pdftotext', '-f', str(i), '-l', str(i), p, '-'],
                             capture_output=True, text=True).stdout
        pages.append({'index': i, 'folio': None, 'text': txt, 'joined': ws(txt)})
    out = {'sha256': sha, 'format_from_bytes': fmt, 'declared_type': snaps[sha]['content_type'],
           'adapter': ADAPTER, 'adapter_version': ADAPTER_VERSION, 'pages': pages}
    json.dump(out, open(f'spike/out/textlayer/{sha}.json', 'w'), ensure_ascii=False, indent=1)
    with open(f'spike/out/textlayer/{sha}.txt', 'w') as f:
        for pg in pages:
            f.write(f'\n=== page {pg["index"]} ===\n')
            paras = [ws(x) for x in re.split(r'\n\s*\n', pg['text']) if ws(x)]
            f.write('\n'.join(paras) + '\n')
    print(sha[:12], fmt, len(pages), 'pages', sum(len(x['joined']) for x in pages), 'chars',
          f'{time.time() - t0:.2f}s')
