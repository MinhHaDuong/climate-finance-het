"""Series stages for the two newsletter issues.

1. restatement: pair the admitted statements of issue 8 (earlier) and issue 13 (later) and
   classify each pair as restatement / change, and each leftover as unpaired, following
   extraction spec s8 (applied, by analogy, across two issues of one serial: see REPORT.md,
   the spec defines s8 only for snapshots of ONE document).
   Pairing without a publisher's key goes through the fusion s3 proposers: tier 2
   (normalised label tokens) then tier 4 (an LLM reading of the remaining candidates).
   Content comparison is field by field on verbatim fields after whitespace join (s8).
2. match: one candidate match of a statement to an existing identity, judged by two LLM
   readers from two vendors, blind, then combined by a versioned rule (fusion s3).
"""
import json
import re
import sys
import time
import unicodedata

sys.path.insert(0, 'spike')
import llm  # noqa: E402
from assisted import CONFIDENCE, LIKELIHOOD, timing, ws  # noqa: E402

A = 'vnm-moit-newsletter-08-2025-10'
B = 'vnm-moit-newsletter-13-2026-03'
PAIR_MODEL = 'mistralai/mistral-medium-3.1'  # large-2512 returned HTTP 429
PAIR_PRICE = (0.4, 2.0)
JUDGES = [('mistralai/mistral-medium-3.1', (0.4, 2.0)), ('deepseek/deepseek-v3.2', (0.28, 0.42))]
RULE_VERSION = 'combine-2readers-v1'


def norm(s):
    s = unicodedata.normalize('NFD', s or '').lower()
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').replace('đ', 'd')
    return set(re.findall(r'[a-z0-9]+', s)) - {'va', 'cac', 'cua', 'trong', 'the', 'du', 'an'}


def admitted(doc):
    """Statements admitted for the spike: kept by the locator check and not judged wrong by
    the checker (the author's review is simulated as 'not overturned')."""
    loc = json.load(open(f'spike/out/{doc}/located.json'))['kept']
    ch = {c['ordinal']: c for c in json.load(open(f'spike/out/{doc}/checks.json')).get('checks', [])}
    out = []
    for s in loc:
        c = ch.get(s['ordinal'], {})
        if c.get('stance') == 'wrong':
            continue
        out.append({'id': f"{doc}-text-{s['ordinal']}", 'page': s['page'], 'label': s['label'],
                    'classification': s['classification'], 'fields': s.get('fields') or {},
                    'anchor': s['anchor'], 'method': 'assisted-reading'})
    import os
    add = f'spike/out/{doc}/author_additions.json'
    if os.path.exists(add):
        a = json.load(open(add))
        tl = json.load(open(f'spike/out/textlayer/{SHA[doc]}.json'))
        alltext = ' '.join(p['joined'] for p in tl['pages'])
        for k, s in enumerate(a['statements'], 1):
            pg = tl['pages'][s['page'] - 1]['joined']
            assert alltext.count(s['anchor']) == 1 and s['label'] in pg and all(v in pg for v in s['fields'].values()), s
            # appended under a new identifier after the reader's ordinals (extraction spec s9)
            out.append({'id': f"{doc}-text-a{k}", 'page': s['page'], 'label': s['label'],
                        'classification': s['classification'], 'fields': s['fields'],
                        'anchor': s['anchor'], 'method': a['method']})
    return out


SHA = {A: 'c5cd6cb1225fd7b5483ce83b5fe92863c252229ddcf0cd9d2653bc907e5f345b',
       B: 'fa7d149b3d8165b85b7090584a3df3d35fbd6b097bb8a08844df330a3410fc39'}


def restatement():
    t0 = time.time()
    a, b = admitted(A), admitted(B)
    # tier 2: normalised label + field tokens, Jaccard
    cands = []
    for x in a:
        for y in b:
            tx = norm(x['label'] + ' ' + ' '.join(map(str, x['fields'].values())))
            ty = norm(y['label'] + ' ' + ' '.join(map(str, y['fields'].values())))
            j = len(tx & ty) / max(1, len(tx | ty))
            if j >= 0.2:
                cands.append({'a': x['id'], 'b': y['id'], 'jaccard': round(j, 2)})
    # tier 4: an LLM reads both lists and the tier-2 candidates, proposes same-item pairs
    user = f"""Two issues of the same monthly newsletter by Viet Nam's Ministry of Industry and Trade (issue 8, October 2025; issue 13, March 2026). Below are the statements read from each (label and verbatim fields as printed, Vietnamese).

Issue 8 statements:
{json.dumps(a, ensure_ascii=False)}

Issue 13 statements:
{json.dumps(b, ensure_ascii=False)}

Candidate pairs from a string-similarity proposer (may be incomplete or wrong): {json.dumps(cands)}

Task: list the pairs (one statement of issue 8, one of issue 13) that assert something about the SAME item (the same count, the same amount, the same project, the same portfolio or envelope). For each pair give stance "same" or "undetermined", a likelihood from {LIKELIHOOD}, a confidence from {CONFIDENCE}, and a short basis quoting both labels. Do not pair statements that are merely about the same topic. Return JSON {{"pairs": [{{"a": id, "b": id, "stance": str, "likelihood": str, "confidence": str, "basis": str}}]}}"""
    out, rec = llm.call(PAIR_MODEL, [{'role': 'user', 'content': user}], stage='restatement-pairing',
                        max_tokens=6000, price=PAIR_PRICE)
    pairs = llm.parse_json(out).get('pairs', [])
    ia, ib = {x['id']: x for x in a}, {y['id']: y for y in b}
    results = []
    for p in pairs:
        x, y = ia.get(p['a']), ib.get(p['b'])
        if not x or not y:
            continue
        fx = {k: ws(str(v)) for k, v in x['fields'].items()}
        fy = {k: ws(str(v)) for k, v in y['fields'].items()}
        same_content = fx == fy and ws(x['label']) == ws(y['label'])
        diffs = {k: (fx.get(k), fy.get(k)) for k in set(fx) | set(fy) if fx.get(k) != fy.get(k)}
        results.append({**p, 'a_label': x['label'], 'b_label': y['label'],
                        'kind': 'restatement' if same_content else 'change', 'field_differences': diffs,
                        'label_differs': ws(x['label']) != ws(y['label'])})
    paired_a = {r['a'] for r in results}
    paired_b = {r['b'] for r in results}
    res = {'method': {'tier2': 'normalised-token-jaccard>=0.2', 'tier4': PAIR_MODEL, 'call': rec},
           'n_a': len(a), 'n_b': len(b), 'tier2_candidates': cands, 'pairs': results,
           'unpaired_earlier': [x['id'] for x in a if x['id'] not in paired_a],
           'new_in_later': [y['id'] for y in b if y['id'] not in paired_b]}
    json.dump(res, open('spike/out/restatement.json', 'w'), ensure_ascii=False, indent=1)
    timing('restatement', f'{A}+{B}', t0, cost=rec['cost_usd'], pairs=len(results))
    print('tier2 candidates', len(cands), 'pairs', len(results))
    for r in results:
        print(' ', r['kind'], r['likelihood'], '|', r['a_label'][:60], '||', r['b_label'][:60], '|', json.dumps(r['field_differences'], ensure_ascii=False)[:200])


def match(stmt_doc, stmt_ordinal, rid):
    t0 = time.time()
    loc = json.load(open(f'spike/out/{stmt_doc}/located.json'))['kept']
    s = next(x for x in loc if x['ordinal'] == int(stmt_ordinal))
    ctx = json.load(open(f'spike/out/identity-{rid}.json'))
    stmt = {'id': f'{stmt_doc}-text-{s["ordinal"]}', 'label': s['label'], 'fields': s.get('fields'),
            'classification': s['classification'], 'document': stmt_doc, 'page': s['page']}
    ident = {'referent_id': rid, 'record': ctx['identity'],
             'statements_it_rests_on': [{k: l[k] for k in ('line_id', 'document_id', 'label', 'classification')} for l in ctx['lines']]}
    user = f"""Candidate match for a documentary ledger of JETP projects. Is the statement about the existing identity (the same project)?

Statement (read from a Vietnamese government newsletter; label and fields as printed):
{json.dumps(stmt, ensure_ascii=False)}

Existing identity and the statements it rests on:
{json.dumps(ident, ensure_ascii=False)}

Answer with a stance ("same", "different" or "undetermined"), the likelihood that the stance "same" is true, chosen from {LIKELIHOOD}, a confidence from {CONFIDENCE} (amount and quality of evidence), and a basis quoting the words you rely on. Note any spelling difference between the names and whether it matters. Return JSON {{"stance": str, "likelihood": str, "confidence": str, "basis": str}}"""
    readings = []
    for model, price in JUDGES:
        out, rec = llm.call(model, [{'role': 'user', 'content': user}], stage=f'match:{model}',
                            max_tokens=1500, price=price)
        r = llm.parse_json(out)
        r['reader'] = model
        r['call'] = rec
        readings.append(r)
    # versioned combination rule
    st = {r['stance'] for r in readings}
    if len(st) == 1:
        idx = [LIKELIHOOD.index(r['likelihood']) if r['likelihood'] in LIKELIHOOD else 3 for r in readings]
        cidx = [CONFIDENCE.index(r['confidence']) if r['confidence'] in CONFIDENCE else 0 for r in readings]
        judgement = {'stance': st.pop(), 'likelihood': LIKELIHOOD[max(idx)], 'confidence': CONFIDENCE[min(cidx)]}
    else:
        judgement = {'stance': 'undetermined', 'likelihood': 'about as likely as not', 'confidence': 'low',
                     'to_author': True}
    rec = {'candidate_match': {'statement': stmt['id'], 'identity': rid}, 'readings': readings,
           'judgement': {**judgement, 'rule': RULE_VERSION, 'decided_at': time.strftime('%Y-%m-%d'),
                         'proposer': 'tier4-llm (tier2 normalised label also run: see below)'},
           'tier2': {'statement_tokens': sorted(norm(s['label'])), 'identity_tokens': sorted(norm(ctx['identity'][0]['canonical_name']))}}
    json.dump(rec, open('spike/out/match.json', 'w'), ensure_ascii=False, indent=1)
    timing('match', stmt_doc, t0, cost=sum(r['call']['cost_usd'] or 0 for r in readings))
    print(json.dumps({k: rec[k] for k in ('judgement', 'tier2')}, ensure_ascii=False))
    for r in readings:
        print(' ', r['reader'], r['stance'], r['likelihood'], r['confidence'], r['basis'][:200])


if __name__ == '__main__':
    if sys.argv[1] == 'restatement':
        restatement()
    else:
        match(*sys.argv[2:5])
