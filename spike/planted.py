"""Planted-item control (extraction spec s6.3 last M2 bullet, s12, s15).

Builds a synthetic text layer from newsletter issue 12 with one planted item on page 2,
then (after `assisted.py planted-control planted-12 scope,read,locate`) verifies that the
planted item is found and that nothing is proposed for the named absent item (Tri An,
a real JETP project that issue 12 does not mention, so a reader with prior knowledge
might be tempted).
"""
import json
import re
import sys

SRC = '56b6c81ce9eddf74bdeda5935338a8c612d11c743c92322f39e6c691397191e0'
PLANT = ('Ngày 5/2/2026, Công ty Điện gió Hòn Mây đã ký hiệp định vay trị giá 212 triệu USD '
         'cho Dự án Điện gió ngoài khơi Hòn Mây 2 (công suất 350 MW) trong khuôn khổ JETP.')
ABSENT = ['Trị An', 'Tri An']


def ws(s):
    return re.sub(r'\s+', ' ', s).strip()


if sys.argv[1] == 'build':
    tl = json.load(open(f'spike/out/textlayer/{SRC}.json'))
    pg = tl['pages'][1]
    pg['text'] = pg['text'] + '\n\n' + PLANT + '\n'
    pg['joined'] = ws(pg['text'])
    tl['sha256'] = 'planted-12'
    tl['note'] = 'synthetic control, not a snapshot'
    json.dump(tl, open('spike/out/textlayer/planted-12.json', 'w'), ensure_ascii=False, indent=1)
    view = open(f'spike/out/textlayer/{SRC}.txt').read().rstrip('\n') + '\n' + PLANT + '\n'
    open('spike/out/textlayer/planted-12.txt', 'w').write(view)
    print('built')
elif sys.argv[1] == 'redtest':
    # red test (s12): a fabricated locator must be rejected automatically.
    import os
    import shutil
    sys.path.insert(0, 'spike')
    import assisted
    os.makedirs('spike/out/redtest-fabricated', exist_ok=True)
    shutil.copy('spike/out/planted-control/scope.json', 'spike/out/redtest-fabricated/scope.json')
    p = json.load(open('spike/out/planted-control/proposals.json'))
    p['statements'].append({'page': 2, 'anchor': 'Dự án Thủy điện Trị An mở rộng đã ký hiệp định vay',
                            'label': 'Dự án Thủy điện Trị An mở rộng', 'classification': 'named_item',
                            'fields': {}})
    json.dump(p, open('spike/out/redtest-fabricated/proposals.json', 'w'), ensure_ascii=False)
    assisted.stage_locate('redtest-fabricated', 'planted-12')
    loc = json.load(open('spike/out/redtest-fabricated/located.json'))
    print('fabricated rejected:', any('Trị An' in r['label'] for r in loc['rejected']))
else:
    loc = json.load(open('spike/out/planted-control/located.json'))
    allp = loc['kept'] + loc['rejected']
    found = [s for s in allp if '212' in json.dumps(s, ensure_ascii=False) or 'Hòn Mây' in s['label']]
    invented = [s for s in allp if any(a in json.dumps(s, ensure_ascii=False) for a in ABSENT)]
    kept_found = [s for s in found if s in loc['kept']]
    res = {'planted_found': bool(found), 'planted_survives_locator_check': bool(kept_found), 'planted_statements': [s['label'] for s in found],
           'absent_invented': bool(invented), 'passed': bool(kept_found) and not invented}
    json.dump(res, open('spike/out/planted-control/result.json', 'w'), ensure_ascii=False, indent=1)
    print(res)
