# Git Discipline (project-specific)

Generic git discipline is in `~/.claude/rules/git.md`. This file adds project-specific conventions.

- **Branch naming**: `t{N}-short-description` (Execute), `explore-{topic}` (Imagine), or `submission/{journal}-{document}` (submission tracking).
- **Enforced by pre-commit hook** — see `.githooks/pre-commit` for specifics.
- **`.worktreeinclude`**: auto-copies `.env` and `.dvc/config.local` into worktrees created by `EnterWorktree`. `.githooks/post-checkout` completes the setup by symlinking `.venv` and `.dvc/cache` at their shared originals; the corpus itself is fetched on demand with `make data` (see `.claude/rules/architecture.md` § Data location).
- **Git hooks** live in `.githooks/`. After cloning: `make setup`. Agents: set automatically at session start.
- **Agent identity**: commits are attributed to `HDMX-coding-agent`, which is a git author name, **not** a GitHub account — `AGENT_GH_TOKEN` authenticates to the forge as the repository owner. The public identity (`AGENT_GIT_NAME`, `AGENT_GIT_EMAIL`) is set in `.env`; the token `AGENT_GH_TOKEN` is **not** — it lives in `~/.config/keys/github.env` and reaches the environment through the `KEYS=` line in `.env` (ticket 0343). No credential is ever a literal in `.env`; `tests/test_env_has_no_secret_literals.py` enforces it.
- **Submission branches** are protected: no merges (cherry-pick only), no deletion, no force-push.
- **Never pass `--delete-branch` to `gh pr merge`.** The repo sets `delete_branch_on_merge: true`, so the remote branch goes server-side. The flag only adds a client-side `git checkout main`, which aborts from every worktree (`fatal: 'main' is already used by worktree`). The merge lands anyway — verify with `gh pr view <N> --json state` instead of re-running.
- **Ticket-filing PRs take the fast path.** A PR whose diff is only `tickets/*.erg` merges on `erg check` plus an ID-collision scan: no draft, no `/verify`, no review request. `main` is unprotected and there is no CI, so nothing gates such a PR and `allow_auto_merge` would wait on an empty requirement set — the friction was procedural, not a check. Use `Ticket-ref:` so the filing PR does not close the ticket it files. Code PRs keep the full gate.
- **The ID-collision scan is the one real risk on that fast path, and it has three failure modes worth naming** (all three fired on 2026-07-27: one filing collided three times, and `origin/main` failed `erg check` on a duplicate ID twice).
  - *Scanning open PRs with `gh pr list --json files` is not scanning.* `gh pr list` does not populate `files`, so a list-plus-filter returns empty regardless of content — "no collision" and "I never looked" are the same output. Enumerate, then query each PR:
    ```bash
    for n in $(gh pr list --state open --limit 60 --json number --jq '.[].number'); do
      gh pr view "$n" --json files --jq '.files[].path' | grep -q "tickets/$ID" && echo "PR $n uses $ID"
    done
    ```
  - *On collision, renumber clear of the frontier — never to the next free ID.* Every parallel session computes the same next-free value and races for it, so that renumber is as collision-prone as the original allocation. 0384 → 0385 → 0386 each collided in turn; 0400, twelve above the frontier, held first try. IDs are free and a gap costs nothing.
  - *Verify after merging, against `origin/main`.* Since this repo has no CI, `erg check` on the branch is the only gate — and it passes by construction, because each branch's IDs are unique within itself. It structurally cannot see a cross-PR duplicate. Run `erg check tickets/` against `origin/main` once the PR lands; that is the only check that catches a duplicate which has already shipped.
