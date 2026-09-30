"""How many of the checker's 'missed' items duplicate a statement already kept or one the
locator check rejected (so would add author minutes for nothing / would recover a rejection)."""
import json
import re
import sys


def ws(s):
    return re.sub(r'\s+', ' ', s or '').strip().lower()


for d in sys.argv[1:]:
    rv = json.load(open(f'{d}/review_set.json'))
    loc = json.load(open(f'{d}/located.json'))
    kept = [ws(s['label']) for s in loc['kept']]
    rej = [ws(s['label']) for s in loc['rejected']]
    dup = rec = new = 0
    for m in rv['missed']:
        lab = ws(m['label'])
        if any(lab in k or k in lab for k in kept if k):
            dup += 1
        elif any(lab in k or k in lab for k in rej if k):
            rec += 1
        else:
            new += 1
    print(d.split('/')[-2] if d.endswith('v2') or d.endswith('v3') else d.split('/')[-1], d[-2:],
          'missed', len(rv['missed']), 'duplicate_of_kept', dup, 'recovers_rejected', rec, 'new', new)
