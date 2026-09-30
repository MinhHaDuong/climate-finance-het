"""Tally spend and wall time per stage from spike/out/spend.jsonl and timings.jsonl."""
import collections
import json

sp = [json.loads(l) for l in open('spike/out/spend.jsonl')]
by = collections.defaultdict(lambda: [0, 0.0, 0.0, 0, 0])
for r in sp:
    k = r['stage']
    b = by[k]
    b[0] += 1
    b[1] += r['cost_usd'] or 0
    b[2] += r['wall_s']
    b[3] += r['prompt_tokens'] or 0
    b[4] += r['completion_tokens'] or 0
print(f"{'stage':55} calls   usd     wall_s  in_tok  out_tok")
for k, (n, c, w, i, o) in by.items():
    print(f'{k:55} {n:3} {c:8.4f} {w:7.1f} {i:7} {o:7}')
print('TOTAL calls', len(sp), 'usd', round(sum(r['cost_usd'] or 0 for r in sp), 4),
      'llm wall_s', round(sum(r['wall_s'] for r in sp), 1),
      'zero-token failures', sum(1 for r in sp if not r['completion_tokens']))
