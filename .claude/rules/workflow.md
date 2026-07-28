# Session Start (project-specific)

Generic session workflow is in `~/.claude/rules/workflow.md`. This file adds project-specific details.

## Worktree file copying

`.worktreeinclude` auto-copies `.env` and `.dvc/config.local` into the worktree.
`.githooks/post-checkout` then symlinks `.venv` and `.dvc/cache` at their shared
originals, so nothing heavy is copied. The corpus is not checked out at creation
time: run `make data` once in the worktree when you need it
(`.claude/rules/architecture.md` § Data location).

## When to Ask the Author

In addition to the generic escalation protocol:
- See writing rules for manuscript-specific guidance.

## Severity floor for the tooling lane

This repo holds two lanes. The **science lane** — corpus, manuscript,
deliverables, analysis — files tickets normally. The **tooling lane** —
guards, Makefile plumbing, test infrastructure, discovery helpers — is
governed by the harness severity floor (`~/.claude/rules/workflow.md`
§ Autonomous Action Rules), which until 2026-07-27 exempted science repos and
so had never applied here.

A tooling-lane finding earns a ticket only when it can put a wrong value in a
deliverable, corrupt state, or block a merge. Below that bar it is fixed in
the change that found it, recorded in memory, or dropped. Sweeps report such
findings; they do not file them.

The discriminator that does the work in practice: **an instance is not a
guard.** A live defect that reaches a rendered document, a deposited artifact,
or the corpus is science-lane and gets a ticket. A gap in the machinery that
watches for that class — a guard with a blind spot, a guard that checks the
declaration rather than the behaviour, a guard proposed so a fixed class
cannot return — is tooling-lane and does not.

Why this exists. On 2026-07-27 the repo filed 74 tickets and closed 41, and
40 of the 95 then open were less than a day old. Almost none came from the
paper; they came from sweeps auditing the harness, and three of them proposed
building new guards, which become new machinery for the next sweep to audit.
The floor was applied retroactively that day and closed 13 of them.

Two things the first pass got wrong, worth knowing before the next one. The
estimate was ~28 closures and the floor condemned 13: most tickets that read
as machinery from their titles carried a live instance in a deliverable, so
the titles cannot be triaged without reading the bodies. And the floor is
about *filing*, never about *fixing* — a closed tooling ticket whose defect
later reaches a deliverable is refiled without apology.

## Harness behaviour

- **Rules files are linter-protected in the main checkout**: `.claude/rules/` files are loaded into context at session start; the harness keeps disk and context in sync by restoring them. Always edit rule files from a worktree (EnterWorktree), not the main checkout.
