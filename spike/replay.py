"""Replay limit for LLM-read statements (extraction s10): regenerate the text layer from the
bytes and check that every admitted locator still resolves once and still contains its label
and values; then a positive control (one statement deliberately altered must fail), and an
idempotence check of the deterministic locator step (run twice, identical output)."""
import copy
import hashlib
import json
import subprocess
import sys

sys.path.insert(0, 'spike')
import assisted  # noqa: E402

DOCS = {'vnm-decision-1009-2023': 'ada382c38c4c3b1ce1d6281c661b24f510d8a58fea1ff517c333a4b99fbd52fd',
        'vnm-moit-newsletter-08-2025-10': 'c5cd6cb1225fd7b5483ce83b5fe92863c252229ddcf0cd9d2653bc907e5f345b',
        'vnm-moit-newsletter-13-2026-03': 'fa7d149b3d8165b85b7090584a3df3d35fbd6b097bb8a08844df330a3410fc39'}


def check(stmts, tl):
    fails = []
    alltext = ' '.join(p['joined'] for p in tl['pages'])
    for s in stmts:
        pg = tl['pages'][s['page'] - 1]['joined']
        a = s['locator']['text_anchor']
        ok = alltext.count(a) == 1 and assisted.ws(s['label']) in pg
        ok = ok and all(assisted.ws(str(v)) in pg for v in (s.get('fields') or {}).values() if v)
        if not ok:
            fails.append(s['ordinal'])
    return fails


res = {}
for doc, sha in DOCS.items():
    before = hashlib.sha256(open(f'spike/out/{doc}/located.json', 'rb').read()).hexdigest()
    subprocess.run([sys.executable, 'spike/textlayer.py', sha], capture_output=True)  # regenerate
    tl = json.load(open(f'spike/out/textlayer/{sha}.json'))
    kept = json.load(open(f'spike/out/{doc}/located.json'))['kept']
    fails = check(kept, tl)
    bad = copy.deepcopy(kept)
    bad[0]['label'] = bad[0]['label'] + ' X'  # positive control
    control_fires = bad[0]['ordinal'] in check(bad, tl)
    assisted.stage_locate(doc, sha)  # rerun deterministic step
    after = hashlib.sha256(open(f'spike/out/{doc}/located.json', 'rb').read()).hexdigest()
    res[doc] = {'statements': len(kept), 'replay_failures': fails, 'positive_control_fires': control_fires,
                'locator_step_idempotent': before == after,
                'outside_replay_reach': f'{len(kept)} statements by assisted-reading (not regenerable)'}
json.dump(res, open('spike/out/replay.json', 'w'), indent=1)
print(json.dumps(res, indent=1))
