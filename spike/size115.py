"""Size of the text of the 115 pending documents, for the cost projection.
PDF: poppler pdftotext; HTML: tags and scripts stripped crudely (upper bound of prose);
other formats: bytes / 2 as a rough stand-in. Writes spike/out/size115.csv."""
import csv
import re
import subprocess

snaps = {r['sha256']: r for r in csv.DictReader(open('data/jetp/snapshots.csv'))}
rows = [r for r in csv.DictReader(open('spike/out/pending.csv')) if r['n_snapshots'] != '0' and r['n_lines'] == '0']
out = csv.writer(open('spike/out/size115.csv', 'w'))
out.writerow(['document_id', 'country', 'document_type', 'language', 'format', 'chars', 'pages'])
tot = 0
for r in rows:
    chars = pages = 0
    fmt = '?'
    for sha in r['sha256s'].split():
        p = 'data/jetp/documents/' + snaps[sha]['storage_path']
        b = open(p, 'rb').read()
        if b[:5] == b'%PDF-':
            fmt = 'pdf'
            t = subprocess.run(['pdftotext', p, '-'], capture_output=True, text=True).stdout
            info = subprocess.run(['pdfinfo', p], capture_output=True, text=True).stdout
            m = re.search(r'Pages:\s+(\d+)', info)
            pages += int(m.group(1)) if m else 0
            chars += len(re.sub(r'\s+', ' ', t))
        elif b.lstrip()[:1] == b'<':
            fmt = 'html'
            s = b.decode('utf-8', 'replace')
            s = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', s)
            s = re.sub(r'<[^>]+>', ' ', s)
            chars += len(re.sub(r'\s+', ' ', s))
        else:
            fmt = snaps[sha]['content_type'].split(';')[0]
            chars += len(b) // 2
    tot += chars
    out.writerow([r['document_id'], r['country'], r['document_type'], r['language'], fmt, chars, pages])
print(len(rows), 'documents', tot, 'chars')
