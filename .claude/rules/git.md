# Git Discipline (project-specific)

Generic git discipline is in `~/.claude/rules/git.md`. This file adds project-specific conventions.

- **Branch naming**: `t{N}-short-description` (Execute), `explore-{topic}` (Imagine), or `submission/{journal}-{document}` (submission tracking).
- **Enforced by pre-commit hook** — see `.githooks/pre-commit` for specifics.
- **`.worktreeinclude`**: auto-copies `.env` and `.dvc/config.local` into worktrees created by `EnterWorktree`.
- **Git hooks** live in `.githooks/`. After cloning: `make setup`. Agents: set automatically at session start.
- **Agent identity**: commits are attributed to `HDMX-coding-agent`, which is a git author name, **not** a GitHub account — `AGENT_GH_TOKEN` authenticates to the forge as the repository owner. The public identity (`AGENT_GIT_NAME`, `AGENT_GIT_EMAIL`) is set in `.env`; the token `AGENT_GH_TOKEN` is **not** — it lives in `~/.config/keys/github.env` and reaches the environment through the `KEYS=` line in `.env` (ticket 0343). No credential is ever a literal in `.env`; `tests/test_env_has_no_secret_literals.py` enforces it.
- **Submission branches** are protected: no merges (cherry-pick only), no deletion, no force-push.
