---
paths:
  - ".env"
  - "scripts/pipeline_keystore.py"
  - "tests/test_env_has_no_secret_literals.py"
---

# Credentials and the keystore

`.env` holds no secret. It carries machine settings and a `KEYS=` line naming
which credentials this project may load; the values live in
`~/.config/keys/<provider>.env` (mode 0600), outside the repository. Entry forms
are `provider`, `provider:VAR`, and `provider:SRC=DST` (rename on export), and
selection is default-deny — an unlisted provider is never loaded, which is what
stops a sibling project's keys from arriving here.

Two mechanisms apply the selection, because no single one covers every entry
point: the harness bash loader, which the Makefile wires into recipe shells via
`BASH_ENV`, and `scripts/pipeline_keystore.py`, which `pipeline_loaders` calls on
import so `dvc repro` and a bare `uv run python scripts/…` resolve too. Neither
overwrites an already-set variable. On a machine without the keystore both
degrade quietly and scripts report the missing key themselves.

This `KEYS=` line **overrides** the harness one; it does not add to it. The bash
loader exports every project-`.env` key verbatim, `KEYS` included, so whatever
starts with this directory as its cwd sees this selection and only this one —
including tools that have no code here, such as the harness `update-publist`
skill. A credential this repo never imports can still need naming here, which is
why `REQUIRED_KEYS_EXPORTS` in `tests/test_env_has_no_secret_literals.py` reads
"must resolve for work started in this repo" rather than "is read by code in this
repo" (ticket 0364).

Adding a credential means putting it in the right provider file and extending
`KEYS=` — never writing it into `.env`, which `tests/test_env_has_no_secret_literals.py`
enforces.
