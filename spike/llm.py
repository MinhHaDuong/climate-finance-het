"""Minimal LLM client for the spike: OpenRouter (key read at use, never logged)
and the local llama-server on padme. Every call is appended to spike/out/spend.jsonl
with model, tokens, cost and wall time; a call is refused when the logged spend
plus a pessimistic estimate of the next call would exceed the budget.
"""
import json
import os
import time

import httpx

BUDGET_USD = 5.00
LOG = 'spike/out/spend.jsonl'
KEYFILE = os.path.expanduser('~/.config/keys/openrouter.env')
KEYNAME = 'OPENROUTER_API_KEY_CLIMATEFINANCE'
# pessimistic USD per million tokens (input, output) used only for the pre-call guard
GUARD_PRICE = {'default': (3.0, 15.0)}


def _key():
    for line in open(KEYFILE):
        if line.startswith(KEYNAME + '='):
            return line.split('=', 1)[1].strip().strip('"')
    raise RuntimeError('key not found')


def spent():
    if not os.path.exists(LOG):
        return 0.0
    return sum(json.loads(l).get('cost_usd', 0) or 0 for l in open(LOG))


def _call(model, messages, stage, max_tokens=8000, temperature=0.0, json_mode=True, price=None):
    local = model.startswith('local/')
    est_in = sum(len(m['content']) for m in messages) / 2.5  # Vietnamese ~2.5 chars/token
    pin, pout = price or GUARD_PRICE['default']
    guard = 0 if local else (est_in * pin + max_tokens * pout) / 1e6
    if spent() + guard > BUDGET_USD:
        raise RuntimeError(f'budget guard: spent {spent():.4f} + next <= {guard:.4f} > {BUDGET_USD}')
    body = {'model': model.removeprefix('local/'), 'messages': messages,
            'temperature': temperature, 'max_tokens': max_tokens}
    if json_mode:
        body['response_format'] = {'type': 'json_object'}
    if local:
        url, headers = 'http://127.0.0.1:8080/v1/chat/completions', {}
    else:
        url = 'https://openrouter.ai/api/v1/chat/completions'
        headers = {'Authorization': 'Bearer ' + _key()}
        body['usage'] = {'include': True}
    t0 = time.time()
    r = httpx.post(url, json=body, headers=headers, timeout=1200)
    dt = time.time() - t0
    r.raise_for_status()
    j = r.json()
    u = j.get('usage', {}) or {}
    rec = {'t': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'stage': stage, 'model': model,
           'served_model': j.get('model'), 'provider': j.get('provider'),
           'prompt_tokens': u.get('prompt_tokens'), 'completion_tokens': u.get('completion_tokens'),
           'cost_usd': 0.0 if local else u.get('cost'), 'wall_s': round(dt, 1),
           'temperature': temperature, 'max_tokens': max_tokens}
    with open(LOG, 'a') as f:
        f.write(json.dumps(rec) + '\n')
    os.makedirs('spike/out/raw', exist_ok=True)
    safe = stage.replace(':', '_').replace('/', '_')
    json.dump(j, open(f"spike/out/raw/{safe}-{rec['t']}.json", 'w'), ensure_ascii=False, indent=1)
    content = j['choices'][0]['message']['content']
    return content, rec


def parse_json(s):
    s = s.strip()
    if s.startswith('```'):
        s = s.split('\n', 1)[1].rsplit('```', 1)[0]
    if '</think>' in s:
        s = s.split('</think>', 1)[1]
    i = min(x for x in (s.find('{'), s.find('['), len(s)) if x >= 0)
    obj, _ = json.JSONDecoder().raw_decode(s[i:])  # tolerate trailing text
    if isinstance(obj, list):  # a bare array of statements
        obj = {'statements': obj}
    return obj


def call(*a, retries=2, **kw):
    """Retry when the provider ends the completion with finish_reason=error (seen twice
    with gemini-3.8-flash on OpenRouter: zero tokens, no content)."""
    for attempt in range(retries + 1):
        content, rec = _call(*a, **kw)
        if content:
            return content, rec
    raise RuntimeError(f"no content after {retries + 1} attempts: {rec}")
