# Ticket 0738 validation record

- First red commit: `761c0b72`; missing implementation caused acceptance-test
  collection failure. Five semantic guardrail tests passed with the green freeze.
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

Full-suite gate and PR review results will be added after the current upstream
integration. The full run started against 7f89c356; upstream advanced with an
independent release-safety change, requiring rebase before the final gate.

DVC publication succeeded: 15 objects sent to the existing machine-local project
remote `/data/projets/dvc/oeconomia-climate-finance`. The default SSH route failed
because this machine resolves padme to localhost with no SSH listener; copying
the existing primary worktree's `.dvc/config.local` selected its working local
remote. No new remote was invented and the override is untracked.
