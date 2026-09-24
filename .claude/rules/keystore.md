---
paths:
  - ".env"
  - "scripts/pipeline_keystore.py"
  - "tests/test_env_has_no_secret_literals.py"
---

# Credentials and the keystore

`.env` holds machine settings and public Git identity only. Credential values
live in `~/.config/keys/<provider>.env` (mode 0600), outside the repository, and
must never be copied into `.env`, command arguments, logs, tickets, or commits.

Credentials are consumer-local. Each tool names the provider and source
variable it needs, reads that one value immediately before the authenticated
call, and does not export it into the surrounding shell. GitHub operations use
the repository-scoped `AGENT_GH_TOKEN_CLIMATEFINANCE`, never the generic token.

Python consumers use `scripts/pipeline_keystore.py`:

- `read_credential(provider, source)` for clients that accept a value directly;
- `credential_environment(provider, source, destination)` only for libraries
  that insist on an environment variable. The destination exists only inside
  the context and is restored afterwards.

The helper reads one provider file and returns only the requested source.
Missing files degrade quietly so clean-room builds retain their documented
free-tier or missing-key behaviour. A value explicitly supplied to the process
wins and is never overwritten.

Shell tools load at invocation time. For example, an authenticated GitHub call
reads `~/.config/keys/github.env` in a command substitution and supplies the
project token only in that `gh` process's environment. Do not create a session
export or a shared shell loader.
