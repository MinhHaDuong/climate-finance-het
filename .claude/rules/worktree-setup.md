---
paths:
  - ".worktreeinclude"
  - ".githooks/**"
  - ".dvc/**"
  - ".env"
  - "tests/test_post_checkout_hook.py"
---

# Worktree setup (project-specific)

Split from `workflow.md` and `git.md`.

## Worktree file copying

`.worktreeinclude` auto-copies `.env` and `.dvc/config.local` into the worktree.
`.githooks/post-checkout` then symlinks `.venv` and `.dvc/cache` at their shared
originals, so nothing heavy is copied. JETP documents are initialized with private
reflinks only when the primary checkout's DVC pointer matches; otherwise run
`make jetp-data`. The bulk corpus is not checked out at creation
time: run `make data` once in the worktree when you need it
(`.claude/rules/data-location.md`).

- **`.worktreeinclude`**: auto-copies `.env` and `.dvc/config.local` into worktrees created by `EnterWorktree`. `.githooks/post-checkout` completes the setup by symlinking `.venv` and `.dvc/cache` at their shared originals, and initializing matching JETP snapshots with private reflinks when supported. Use `make jetp-data` for those snapshots on demand, or `make data` for the whole corpus (see `.claude/rules/data-location.md`).
