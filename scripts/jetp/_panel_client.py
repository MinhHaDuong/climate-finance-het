"""A zero-retention OpenRouter client that fails closed (ticket 1895).

Every hosted call of the panel goes through ``call``: the request pins the
member's one zero-retention provider (``provider.only``, ``zdr: true``,
``data_collection: deny``, no fallback), and the response is checked against
the zero-retention endpoint list read at run start. A response served by any
other provider raises ``ClosedFail`` and the run stops. Each call is
appended to the cost ledger with the provider and model version that served
it and the cost OpenRouter reports; the budget is checked before each call.

The key is read from the machine keystore at the point of use and never
logged (``scripts/pipeline_keystore.py``).
"""

import csv
import datetime
import json
import os
import threading
import time
import urllib.error
import urllib.request

from pipeline_keystore import read_credential

API = 'https://openrouter.ai/api/v1'
LEDGER_COLUMNS = ['called_at', 'prompt_version', 'member', 'model', 'document_id', 'part',
                  'provider', 'served_model', 'zdr', 'prompt_tokens',
                  'completion_tokens', 'reasoning_tokens', 'cost_usd',
                  'finish_reason', 'seconds']


class ClosedFail(RuntimeError):
    """A call that must not stand: unlisted provider, budget, refusal."""


def _key():
    key = (read_credential('openrouter', 'OPENROUTER_API_KEY_CLIMATEFINANCE')
           or read_credential('openrouter', 'OPENROUTER_API_KEY'))
    if not key:
        raise ClosedFail('no OpenRouter key in the keystore')
    return key


def _request(path, body=None, timeout=900):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        API + path, data=data,
        headers={'Authorization': f'Bearer {_key()}',
                 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def zdr_endpoints(models):
    """The zero-retention endpoints listed now for ``models``: rows of dicts."""
    rows = _request('/endpoints/zdr')['data']
    return [{'model_id': r['model_id'], 'provider_name': r['provider_name'],
             'tag': r['tag'], 'prompt': r['pricing']['prompt'],
             'completion': r['pricing']['completion']}
            for r in rows if r['model_id'] in models]


def check_members(members, endpoints):
    """Raise unless every member's pinned provider is a listed ZDR endpoint."""
    for m in members:
        if not any(e['model_id'] == m['model'] and e['provider_name'] == m['provider_name']
                   for e in endpoints):
            raise ClosedFail(f"{m['key']}: {m['model']} via {m['provider_name']} "
                             'is not a listed zero-retention endpoint')


class Ledger:
    """Cost ledger (CSV, appended) and the budget it enforces."""

    def __init__(self, path, budget_usd):
        self.path = path
        self.budget = budget_usd
        self.lock = threading.Lock()
        self.spent = 0.0
        self.pending = 0.0
        if os.path.exists(path):
            with open(path, newline='') as fh:
                self.spent = sum(float(r['cost_usd'] or 0) for r in csv.DictReader(fh))

    def reserve(self, estimate):
        with self.lock:
            if self.spent + self.pending + estimate > self.budget:
                raise ClosedFail(f'budget: spent {self.spent:.2f} + in flight '
                                 f'{self.pending:.2f} + estimate {estimate:.2f} '
                                 f'> cap {self.budget:.2f} USD')
            self.pending += estimate

    def release(self, estimate):
        with self.lock:
            self.pending -= estimate

    def record(self, row):
        with self.lock:
            self.spent += float(row['cost_usd'] or 0)
            new = not os.path.exists(self.path)
            with open(self.path, 'a', newline='') as fh:
                writer = csv.DictWriter(fh, LEDGER_COLUMNS)
                if new:
                    writer.writeheader()
                writer.writerow(row)


def request_body(member, messages, schema, cfg):
    return {
        'model': member['model'],
        'messages': messages,
        'provider': {'only': [member['provider']], 'allow_fallbacks': False,
                     'require_parameters': True, 'zdr': True, 'data_collection': 'deny'},
        'response_format': {'type': 'json_schema',
                            'json_schema': {'name': 'statements', 'strict': True,
                                            'schema': schema}},
        'reasoning': {'effort': cfg['reasoning_effort']},
        'max_tokens': cfg['max_output_tokens'],
        'usage': {'include': True},
    }


def check_served(member, response):
    """Raise unless the provider that served the call is the pinned one."""
    served = response.get('provider')
    if served != member['provider_name']:
        raise ClosedFail(f"{member['key']}: served by {served!r}, "
                         f"pinned {member['provider_name']!r}; run stopped")


def call(member, messages, schema, cfg, ledger, document_id, part, retries=3):
    """One member call; returns ``(content_text, response)``."""
    prompt_chars = sum(len(m['content']) for m in messages)
    estimate = (prompt_chars / 3 * member['price_in_per_m']
                + 20000 * member['price_out_per_m']) / 1e6
    ledger.reserve(estimate)
    body = request_body(member, messages, schema, cfg)
    try:
        for attempt in range(retries):
            started = time.time()
            try:
                response = _request('/chat/completions', body)
                break
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
                if attempt == retries - 1:
                    raise
                time.sleep(30 * (attempt + 1))
    finally:
        ledger.release(estimate)
    usage = response.get('usage') or {}
    choice = (response.get('choices') or [{}])[0]
    ledger.record({
        'called_at': datetime.datetime.now(datetime.UTC).isoformat(timespec='seconds'),
        'prompt_version': cfg['prompt_version'],
        'member': member['key'], 'model': member['model'],
        'document_id': document_id, 'part': part,
        'provider': response.get('provider'), 'served_model': response.get('model'),
        'zdr': 'requested+pinned',
        'prompt_tokens': usage.get('prompt_tokens'),
        'completion_tokens': usage.get('completion_tokens'),
        'reasoning_tokens': (usage.get('completion_tokens_details') or {}).get('reasoning_tokens'),
        'cost_usd': usage.get('cost') if usage.get('cost') is not None else (
            (usage.get('prompt_tokens') or 0) * member['price_in_per_m']
            + (usage.get('completion_tokens') or 0) * member['price_out_per_m']) / 1e6,
        'finish_reason': choice.get('finish_reason'),
        'seconds': round(time.time() - started, 1),
    })
    check_served(member, response)
    return (choice.get('message') or {}).get('content') or '', response
