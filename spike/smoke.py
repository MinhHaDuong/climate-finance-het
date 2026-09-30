"""Smoke test of a route: one tiny call, prints the raw usage block (no key printed)."""
import sys

sys.path.insert(0, 'spike')
import llm  # noqa: E402

out, rec = llm.call(sys.argv[1], [{'role': 'user', 'content': 'Return JSON {"a": [1, 2]}'}],
                    stage='smoke', max_tokens=300)
print(repr(out[:300]))
print(rec)
