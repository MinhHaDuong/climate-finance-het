---
paths:
  - ".claude/**"
  - "AGENTS.md"
---

# Editing agent rules (project-specific)

Split from `workflow.md`.

## Harness behaviour

- **Rules files are linter-protected in the main checkout**: `.claude/rules/` files are loaded into context at session start; the harness keeps disk and context in sync by restoring them. Always edit rule files from a worktree (EnterWorktree), not the main checkout.
