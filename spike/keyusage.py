"""Read OpenRouter's own usage counter for the key (direct measurement of spend,
independent of the per-call log). Prints usage figures only, never the key."""
import json
import sys
import time

import httpx

sys.path.insert(0, 'spike')
import llm  # noqa: E402

r = httpx.get('https://openrouter.ai/api/v1/key', headers={'Authorization': 'Bearer ' + llm._key()}, timeout=30)
d = r.json().get('data', {})
rec = {'t': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'label': sys.argv[1] if len(sys.argv) > 1 else '',
       'usage': d.get('usage'), 'usage_daily': d.get('usage_daily')}
open('spike/out/key_usage.jsonl', 'a').write(json.dumps(rec) + '\n')
print(rec)
