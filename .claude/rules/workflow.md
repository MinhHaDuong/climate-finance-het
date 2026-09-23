# Session Start (project-specific)

Generic session workflow is in `~/.claude/rules/workflow.md`. This file adds project-specific details.

## Worktree file copying

`.worktreeinclude` auto-copies `.env` and `.dvc/config.local` into the worktree.
`.githooks/post-checkout` then symlinks `.venv` and `.dvc/cache` at their shared
originals, so nothing heavy is copied. JETP documents are initialized with private
reflinks only when the primary checkout's DVC pointer matches; otherwise run
`make jetp-data`. The bulk corpus is not checked out at creation
time: run `make data` once in the worktree when you need it
(`.claude/rules/architecture.md` § Data location).

## Severity floor: science lane vs tooling lane

The harness severity floor applies here. What decides a ticket in practice:
**an instance is not a guard.** A live defect that reaches a rendered document,
a deposited artifact, or the corpus is science-lane and gets a ticket. A gap in
the machinery that watches for that class (a guard with a blind spot, a guard
that checks the declaration rather than the behaviour, a guard proposed so a
fixed class cannot return) is tooling-lane and does not.

Triage by reading the bodies: tickets that read as machinery from their titles
often carry a live instance in a deliverable. The floor governs *filing*, never
*fixing*: a closed tooling ticket whose defect later reaches a deliverable is
refiled without apology.

## Harness behaviour

- **Rules files are linter-protected in the main checkout**: `.claude/rules/` files are loaded into context at session start; the harness keeps disk and context in sync by restoring them. Always edit rule files from a worktree (EnterWorktree), not the main checkout.
