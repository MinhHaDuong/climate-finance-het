# Git Discipline (project-specific)

Generic git discipline is in `~/.claude/rules/git.md`. This file adds project-specific conventions.

- **Branch naming**: `t{N}-short-description` (Execute), `explore-{topic}` (Imagine), or `submission/{journal}-{document}` (submission tracking).
- **Enforced by pre-commit hook** — see `.githooks/pre-commit` for specifics.
- **Git hooks** live in `.githooks/`. After cloning: `make setup`. Agents: set automatically at session start.
- **Agent identity**: commits are attributed to `HDMX-coding-agent`, which is a git author name, **not** a GitHub account. The public identity (`AGENT_GIT_NAME`, `AGENT_GIT_EMAIL`) is set in `.env`; authenticated `gh` calls read the repository-scoped `AGENT_GH_TOKEN_CLIMATEFINANCE` directly from `~/.config/keys/github.env` and expose it only to that invocation. No credential is ever a literal in `.env`; `tests/test_env_has_no_secret_literals.py` enforces it.
- **Submission branches** are protected: no merges (cherry-pick only), no deletion, no force-push.
- **Never pass `--delete-branch` to `gh pr merge`.** The repo sets `delete_branch_on_merge: true`, so the remote branch goes server-side. The flag only adds a client-side `git checkout main`, which aborts from every worktree (`fatal: 'main' is already used by worktree`). The merge lands anyway — verify with `gh pr view <N> --json state` instead of re-running.
- **Scoped siblings**: worktree setup (`.worktreeinclude`, hooks) is in `worktree-setup.md`; the ticket-filing fast path and the ID-collision scan are in `ticket-filing.md` (loaded when you touch `tickets/`).
