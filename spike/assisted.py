"""Assisted reading of one snapshot, following extraction spec s6.3 as literally as possible.

Stages (each timed into spike/out/timings.jsonl):
  scope    reader LLM declares scope + field list (s4 'Declared scope', s3 'Verbatim fields')
  read     reader LLM proposes statements given text layer + scope + field list (s6.3 bullet 1)
  locate   automatic locator check against the stored bytes' text layer (s6.3 bullet 2)
  check    checker LLM from another vendor examines every surviving proposal (s6.3 bullet 3)
  review   builds the author's review set: disagreements + missed + random sample (s6.3 bullet 4)

Usage: python spike/assisted.py <document_id> <sha256> <stage|all>
"""
import csv
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, 'spike')
import llm  # noqa: E402

READER = os.environ.get('SPIKE_READER', 'google/gemini-3.8-flash')
READER_PRICE = (0.75, 3.75)
CHECKER = os.environ.get('SPIKE_CHECKER', 'openai/gpt-5.4-mini')
CHECKER_PRICE = (0.75, 4.5)
PROMPT_VERSION = 'spike-2026-09-30.3'
CLASSES = ['named_item', 'unnamed_item', 'quota', 'heading', 'submission', 'evaluation',
           'register_allocation', 'count', 'envelope', 'absence']
LIKELIHOOD = ['virtually certain', 'very likely', 'likely', 'about as likely as not',
              'unlikely', 'very unlikely', 'exceptionally unlikely']
CONFIDENCE = ['very low', 'low', 'medium', 'high', 'very high']
TRIM = os.environ.get('SPIKE_TRIM', '1') == '1'  # locator check v3; v2 = no trim
PURPOSE = ("The ledger records statements about the Just Energy Transition Partnerships' "
           "projects, money, perimeters, parties and states (signatures, approvals, amounts, "
           "dates, stages).")


def ws(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def timing(stage, doc, t0, **kw):
    with open('spike/out/timings.jsonl', 'a') as f:
        f.write(json.dumps({'stage': stage, 'document_id': doc, 'wall_s': round(time.time() - t0, 2), **kw}) + '\n')


def load(doc, sha):
    tl = json.load(open(f'spike/out/textlayer/{sha}.json'))
    view = open(f'spike/out/textlayer/{sha}.txt').read()
    d = f'spike/out/{doc}'
    os.makedirs(d, exist_ok=True)
    return tl, view, d


def stage_scope(doc, sha):
    tl, view, d = load(doc, sha)
    t0 = time.time()
    sys_p = ("You declare the scope of a reading before any statement is read, for a documentary "
             "ledger. " + PURPOSE + " Answer in JSON only.")
    user = f"""Document id: {doc}. Text layer (pages marked '=== page N ==='):

{view}

Task, following the reading specification:
1. Declared scope: name the parts of the document the reading covers and, for each part left out, why it is out of scope. Navigation, boilerplate, legal notices, contents and repeated page furniture are out of scope unless you say otherwise.
2. Declared field list: the list of verbatim field names that every statement of this document will use for 'everything else the publisher printed for the item'. Field names must be the publisher's own field names as printed where the publisher prints any (column headers, labels); if the document is prose and prints no field names, say so explicitly and propose the smallest list of field names you need, marking each as 'printed' or 'not printed (reader-supplied)'.
3. Charts or figures whose values have no text behind them: list them for the scope note.
Return JSON: {{"scope_in": [{{"part": str, "pages": [int]}}], "scope_out": [{{"part": str, "reason": str}}], "field_list": [{{"name": str, "printed": bool}}], "charts_without_text": [str], "notes": str}}"""
    out, rec = llm.call(READER, [{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user}],
                        stage=f'scope:{doc}', max_tokens=4000, price=READER_PRICE)
    j = llm.parse_json(out)
    j['_method'] = {'model': READER, 'prompt_version': PROMPT_VERSION, 'call': rec}
    json.dump(j, open(f'{d}/scope.json', 'w'), ensure_ascii=False, indent=1)
    timing('scope', doc, t0, cost=rec['cost_usd'])
    print('scope', json.dumps(j, ensure_ascii=False)[:1500])


def stage_read(doc, sha):
    tl, view, d = load(doc, sha)
    scope = json.load(open(f'{d}/scope.json'))
    fields = [f['name'] for f in scope['field_list']]
    t0 = time.time()
    sys_p = ("You read statements from a document for a documentary ledger, recording what the "
             "publisher printed, as printed, never interpreting. " + PURPOSE +
             " A reader who is unsure writes unknown; a guess is never a reading. JSON only.")
    user = f"""Document id: {doc}. Text layer (pages marked '=== page N ==='):

{view}

Declared scope (read every item inside it, nothing outside it):
{json.dumps({'in': scope['scope_in'], 'out': scope['scope_out']}, ensure_ascii=False)}

Declared field list (every statement uses only these field names; omit a field the item does not print):
{json.dumps(fields, ensure_ascii=False)}

Rules:
- One statement is one assertion at one place. An item of a list is one statement. A heading that groups items is a statement with classification 'heading'. A count given without naming what is counted is one 'count' statement; do not invent items for the uncounted rest. The same value printed in two places is two statements. Prose is read when it asserts something in scope (a signature, an approval, an amount, a date, a state); each assertion is one statement anchored on its own words, attributed to its speaker when the publisher quotes someone.
- label: the item's name or description copied verbatim in the document's language (Vietnamese stays Vietnamese), whitespace joined, no other change.
- anchor: a verbatim substring of AT MOST 80 characters (about 10 to 12 Vietnamese words; count them), copied exactly from the text layer, that starts the assertion and occurs only once in the document.
- page: the page number (from '=== page N ===') where the anchor is.
- classification: exactly one of {CLASSES}, assigned from what the publisher presents, never from words in the label; if you cannot tell, write "unclassified" and say why in note.
- own_status / own_sector: the publisher's own status or sector word copied as printed, or null; own_status_axis: which of project_stage, asset_state, money, delivery the word belongs to, or null.
- group_anchor: the anchor of the heading statement that governs this one, or null.
- fields: {{field name: value}}. Each value is an exact substring of the text layer, copied from the same sentence or paragraph as the anchor, with its printed unit and scale; never convert, never normalise, never summarise, never join several phrases with ';'. If a phrase names several parties, copy the phrase whole. If the item does not print a field, omit it.
- label: must itself be an exact substring of the text layer (the item's printed name or the words of the assertion), not a paraphrase.
- speaker: the person or organisation quoted, as printed, or null.
Return JSON: {{"statements": [{{"page": int, "anchor": str, "label": str, "classification": str, "own_status": str|null, "own_status_axis": str|null, "own_sector": str|null, "group_anchor": str|null, "fields": {{}}, "speaker": str|null, "note": str|null}}]}}"""
    out, rec = llm.call(READER, [{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user}],
                        stage=f'read:{doc}', max_tokens=32000, price=READER_PRICE)
    j = llm.parse_json(out)
    j['_method'] = {'method': 'assisted-reading', 'version': PROMPT_VERSION, 'reader': READER,
                    'temperature': 0.0, 'call': rec, 'adapter': tl['adapter'],
                    'adapter_version': tl['adapter_version']}
    json.dump(j, open(f'{d}/proposals.json', 'w'), ensure_ascii=False, indent=1)
    timing('read', doc, t0, cost=rec['cost_usd'], n=len(j['statements']))
    print('proposals', len(j['statements']))


def stage_locate(doc, sha):
    """s6.3 bullet 2: locator must resolve in the stored bytes' text layer and the text
    'there' must contain the label and values. 'There' is not defined by the spec for an
    80-char anchor; the spike takes the page's joined text from the anchor's start to
    ±1000 characters around the anchor (v1 used anchor to +2000 and rejected values printed just before the anchor), and the label must be found on that page."""
    tl, view, d = load(doc, sha)
    t0 = time.time()
    props = json.load(open(f'{d}/proposals.json'))['statements']
    fields_decl = [f['name'] for f in json.load(open(f'{d}/scope.json'))['field_list']]
    alltext = ' '.join(p['joined'] for p in tl['pages'])
    kept, rejected = [], []
    for i, s in enumerate(props):
        reasons = []
        anc = ws(s.get('anchor'))
        pg = next((p for p in tl['pages'] if p['index'] == s.get('page')), None)
        if TRIM and len(anc) > 80 and pg and anc in pg['joined']:
            # v3: deterministic trim of a verbatim over-long anchor to its longest
            # word-boundary prefix <= 80 chars, only when the full anchor is verbatim
            cut = anc[:81].rsplit(' ', 1)[0][:80]
            s['_anchor_trimmed_from'] = anc
            s['anchor'] = anc = cut
        if not anc or len(anc) > 80:
            reasons.append('anchor empty or longer than 80 characters')
        elif alltext.count(anc) != 1:
            reasons.append(f'anchor occurs {alltext.count(anc)} times in the snapshot (must be 1)')
        elif pg is None or anc not in pg['joined']:
            reasons.append('anchor not on the stated page')
        if not reasons:
            pos = pg['joined'].index(anc)
            window = pg['joined'][max(0, pos - 1000):pos + 1000]
            if ws(s.get('label')) not in pg['joined']:
                reasons.append('label not found verbatim on the page')
            for k, v in (s.get('fields') or {}).items():
                if k not in fields_decl:
                    reasons.append(f'field {k!r} not in the declared field list')
                elif v is not None and ws(str(v)) and ws(str(v)) not in window:
                    reasons.append(f'value of {k!r} not found near the anchor: {v!r}')
        s['_proposal_index'] = i
        (rejected if reasons else kept).append({**s, '_reasons': reasons} if reasons else s)
    # ordinal in reading order across the snapshot, computed, never proposed
    def pos_key(s):
        pg = next(p for p in tl['pages'] if p['index'] == s['page'])
        return (s['page'], pg['joined'].index(ws(s['anchor'])))
    kept.sort(key=pos_key)
    for n, s in enumerate(kept, 1):
        s['ordinal'] = n
        s['locator'] = {'page_index': s['page'], 'folio': None, 'text_anchor': ws(s['anchor']),
                        'adapter': f"{tl['adapter']} {tl['adapter_version']}"}
    json.dump({'kept': kept, 'rejected': rejected}, open(f'{d}/located.json', 'w'), ensure_ascii=False, indent=1)
    timing('locate', doc, t0, kept=len(kept), rejected=len(rejected))
    print('locator check: kept', len(kept), 'rejected', len(rejected))
    for r in rejected:
        print('  REJ', r['_proposal_index'], r['_reasons'][:2], ws(r.get('label'))[:80])


def stage_check(doc, sha):
    tl, view, d = load(doc, sha)
    loc = json.load(open(f'{d}/located.json'))
    scope = json.load(open(f'{d}/scope.json'))
    t0 = time.time()
    items = [{'ordinal': s['ordinal'], 'page': s['page'], 'anchor': s['anchor'], 'label': s['label'],
              'classification': s['classification'], 'own_status': s.get('own_status'),
              'own_status_axis': s.get('own_status_axis'), 'group_anchor': s.get('group_anchor'),
              'fields': s.get('fields'), 'speaker': s.get('speaker')} for s in loc['kept']]
    sys_p = ("You check another reader's statements against the document, in the document's "
             "language, for a documentary ledger. " + PURPOSE + " JSON only.")
    user = f"""Document id: {doc}. Text layer:

{view}

Declared scope: {json.dumps({'in': scope['scope_in'], 'out': scope['scope_out']}, ensure_ascii=False)}
Declared field list: {json.dumps([f['name'] for f in scope['field_list']], ensure_ascii=False)}
Allowed classifications: {CLASSES} (or "unclassified").

Proposed statements (by another reader):
{json.dumps(items, ensure_ascii=False, indent=0)}

For EVERY proposed statement, state whether it is right: the label and field values are copied verbatim, the classification fits what the publisher presents, the fields hold what the publisher printed, and it is one assertion in scope. Give:
- stance: "right", "wrong" or "partly right" (say what is wrong)
- likelihood that the statement is right, one of {LIKELIHOOD}
- confidence, one of {CONFIDENCE}
- basis: a short verbatim quote from the document supporting your stance.
Then list items inside the declared scope that the reader missed (one assertion each, with page, a verbatim anchor of at most 80 characters, label and why it is in scope).
Return JSON: {{"checks": [{{"ordinal": int, "stance": str, "likelihood": str, "confidence": str, "basis": str, "problem": str|null}}], "missed": [{{"page": int, "anchor": str, "label": str, "why": str}}]}}"""
    out, rec = llm.call(CHECKER, [{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user}],
                        stage=f'check:{doc}', max_tokens=32000, price=CHECKER_PRICE)
    j = llm.parse_json(out)
    j['_method'] = {'checker': CHECKER, 'prompt_version': PROMPT_VERSION, 'temperature': 0.0, 'call': rec}
    json.dump(j, open(f'{d}/checks.json', 'w'), ensure_ascii=False, indent=1)
    timing('check', doc, t0, cost=rec['cost_usd'], n=len(j.get('checks', [])), missed=len(j.get('missed', [])))
    print('checks', len(j.get('checks', [])), 'missed', len(j.get('missed', [])))


def stage_review(doc, sha, sample_share=0.2, sample_floor=3, seed=1710):
    """s6.3 bullet 4. 'Disagree' is not defined by the spec; the spike counts a proposal as a
    disagreement when the checker's stance is not 'right' or its likelihood is below 'likely'."""
    tl, view, d = load(doc, sha)
    t0 = time.time()
    loc = json.load(open(f'{d}/located.json'))
    ch = json.load(open(f'{d}/checks.json'))
    by = {c['ordinal']: c for c in ch.get('checks', [])}
    agree, disagree, unchecked = [], [], []
    for s in loc['kept']:
        c = by.get(s['ordinal'])
        if c is None:
            unchecked.append(s)
            continue
        s['_check'] = c
        ok = c['stance'] == 'right' and c['likelihood'] in LIKELIHOOD[:3]
        (agree if ok else disagree).append(s)
    rnd = random.Random(seed)
    k = min(len(agree), max(sample_floor, round(sample_share * len(agree))))
    sample = rnd.sample(agree, k)
    order = lambda s: (LIKELIHOOD.index(s['_check']['likelihood']) if s['_check']['likelihood'] in LIKELIHOOD else 9,
                       -CONFIDENCE.index(s['_check']['confidence']) if s['_check']['confidence'] in CONFIDENCE else 9)
    missed = ch.get('missed', [])
    unclassified = [s for s in loc['kept'] if s['classification'] not in CLASSES]
    rev = {'disagreements': sorted(disagree, key=order), 'missed': missed, 'sample_of_agreed': sorted(sample, key=order),
           'unchecked': unchecked, 'counts': {'proposed': len(loc['kept']) + len(loc['rejected']),
                                              'rejected_by_locator': len(loc['rejected']), 'agreed': len(agree),
                                              'disagreements': len(disagree), 'missed': len(missed),
                                              'sample': k, 'unchecked': len(unchecked),
                                              'unclassified_waiting_review': len(unclassified)}}
    # author minutes: 1.5 min per disagreement or missed item (locate, read Vietnamese, decide),
    # 0.5 min per sampled agreed row, 1 min per unclassified row not already shown
    shown = {id(s) for s in disagree + sample}
    extra_uncl = sum(1 for s in unclassified if id(s) not in shown)
    rev['author_minutes_estimate'] = round(1.5 * (len(disagree) + len(missed)) + 0.5 * k + 1.0 * extra_uncl, 1)
    json.dump(rev, open(f'{d}/review_set.json', 'w'), ensure_ascii=False, indent=1)
    timing('review_set', doc, t0, **rev['counts'], author_minutes=rev['author_minutes_estimate'])
    print(json.dumps(rev['counts']), 'author minutes', rev['author_minutes_estimate'])


if __name__ == '__main__':
    doc, sha, st = sys.argv[1:4]
    stages = ['scope', 'read', 'locate', 'check', 'review'] if st == 'all' else st.split(',')
    for s in stages:
        globals()['stage_' + s](doc, sha)
