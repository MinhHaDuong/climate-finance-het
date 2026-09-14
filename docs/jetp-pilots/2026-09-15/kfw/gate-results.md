# Ticket 0738 validation record

- First red commit: `761c0b72`; missing implementation caused acceptance-test
  collection failure. Five semantic guardrail tests passed with the green freeze.
  A later isolated naive-mapping mutation produced exactly four intended failures
  (duplicate population, exact payment day, equal-start delay, cancellation);
  the fifth deterministic-sample test passed. No production monkeypatch persisted.
- Core offline replay reproduced all six generated artifacts byte-for-byte.
- Independent scientific verification: [verification.md](verification.md).
- `make check-fast PYTHON=/tmp/jetp-audit-0735/.venv/bin/python`: 1,721 passed,
  12 skipped. Initial missing-document failures were worktree hydration issues;
  copying the existing canonical document objects resolved them without code edits.
- `make lint` with the same interpreter and writable RUFF/MYPY caches:
  330 passed, 15 skipped. A naming violation found in the first pass was fixed
  by renaming the calculation to `analyze_jetp_kfw_pilot.py`.
- `/verify-adherence t0738-kfw-feasibility worktree=/tmp/t0738-pilot`:
  import-resolution probe and all five affected tests passed; full adherence suite
  passed; no TeX/QMD/BIB changes, trace input or architectural rule changes.

```yaml
adherence: PASS
mechanical_failures: []
semantic_findings: []
untested_rules: []
```

The final full suite runs against integrated base `0f97bbf6`. Initial exploratory
runs were interrupted for upstream integration and worktree input hydration;
these are not reported as passing runs. The existing literature catalog objects
were linked into this worktree, without source edits; corpus acceptance/flow then
passed 68 tests (12 skipped).

The shared I/O wrapper was brought into compliance with script-io.md; all five
acceptance tests and six byte-identical offline artifacts passed again. Final
adherence after that change: 330 passed, 15 skipped.

Sandbox integration failures were reproduced and resolved by focused reruns with
`UV_NO_SYNC=1`, writable UV cache and approved environment access:

- Local HTTP document harvest, both package-installability checks, reference-count
  subprocess and worktree-hook checks: 20 passed (7 previously blocked tests plus
  surrounding hook checks).
- Citation resume-preview test: 1 passed with network access; sandbox retries had
  exceeded its fixed 10-second subprocess timeout.

The completed `make check` reported **2,722 passed, 54 skipped, 9 failed** in
326.90 seconds. All nine failures were the sandbox-dependent checks named above
plus the venue-concentration subprocess; that final subprocess also passed its
focused retry. Thus all observed failures have passing follow-up evidence, while
the original full command itself remains recorded as nonzero. No code/data
regression remained unresolved, and no test was weakened or skipped to obtain
these passes. The PR review result will be appended after its independent panel.

DVC publication succeeded: 15 objects sent to the existing machine-local project
remote `/data/projets/dvc/oeconomia-climate-finance`. The default SSH route failed
because this machine resolves padme to localhost with no SSH listener; copying
the existing primary worktree's `.dvc/config.local` selected its working local
remote. No new remote was invented and the override is untracked.
