"""Series parser for the MOIT 'Bản tin JETP Việt Nam' newsletters (extraction spec s6.1).

What a parser can read deterministically in this series: the masthead (issue number and
month) and the article headlines (set in a larger font). It cannot read the prose
assertions under them; those go to assisted reading (s6.3). The parser:
- declares the snapshots it can read by landmarks and refuses others (s6.1 bullet 1);
- emits `heading` statements with page, text anchor and ordinal;
- has no printed totals to use as controls (s6.1 bullet 2 cannot apply).
Usage: python spike/nl_parser.py <sha256> [...]
"""
import csv
import json
import re
import sys

import pdfplumber

PARSER = 'vnm-moit-newsletter-parser'
VERSION = '0.1-spike'
MAST = re.compile(r'BẢN TIN JETP VIỆT NAM\s*Số\s*(\d+)\s*[–-]\s*Tháng\s*(\d{1,2})/(\d{4})')
snaps = {r['sha256']: r for r in csv.DictReader(open('data/jetp/snapshots.csv'))}


def ws(s):
    return re.sub(r'\s+', ' ', s).strip()


def parse(sha):
    tl = json.load(open(f'spike/out/textlayer/{sha}.json'))
    p1 = tl['pages'][0]['joined']
    m = MAST.search(p1)
    if not m or 'QUAN HỆ ĐỐI TÁC CHUYỂN ĐỔI NĂNG LƯỢNG CÔNG BẰNG (JETP)' not in p1:
        return {'sha256': sha, 'refused': 'landmarks absent (masthead)'}
    out = {'sha256': sha, 'parser': PARSER, 'version': VERSION, 'issue': int(m.group(1)),
           'month': f'{m.group(3)}-{int(m.group(2)):02d}', 'statements': []}
    path = 'data/jetp/documents/' + snaps[sha]['storage_path']
    ordn = 0
    with pdfplumber.open(path) as pdf:
        for i, pg in enumerate(pdf.pages, 1):
            words = pg.extract_words(extra_attrs=['size'], keep_blank_chars=False, use_text_flow=True)
            # headline font: size strictly between body (9.5) and masthead (26, 40); page header 12
            big = [w for w in words if 13.0 <= w['size'] < 25.0]
            lines, cur, last_top = [], [], None
            for w in big:
                if last_top is not None and abs(w['top'] - last_top) > 30:
                    lines.append(cur)
                    cur = []
                cur.append(w)
                last_top = w['top']
            if cur:
                lines.append(cur)
            joined = tl['pages'][i - 1]['joined']
            for ln in lines:
                txt = ws(' '.join(w['text'] for w in ln))
                if len(txt) < 12 or txt.startswith('QUAN HỆ ĐỐI TÁC'):
                    continue
                anchor = txt[:81].rsplit(' ', 1)[0][:80] if len(txt) > 80 else txt
                if joined.count(anchor) != 1:
                    continue  # locator would not resolve uniquely: not admitted
                ordn += 1
                out['statements'].append({'ordinal': ordn, 'page': i, 'anchor': anchor, 'label': txt,
                                          'classification': 'heading',
                                          'method': PARSER, 'version': VERSION})
    return out


if __name__ == '__main__':
    res = [parse(s) for s in sys.argv[1:]]
    json.dump(res, open('spike/out/nl_parser.json', 'w'), ensure_ascii=False, indent=1)
    for r in res:
        print(r['sha256'][:12], r.get('refused') or (r['issue'], r['month'], [s['label'][:70] for s in r['statements']]))
