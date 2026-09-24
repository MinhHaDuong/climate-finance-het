# Session Start (project-specific)

Generic session workflow is in `~/.claude/rules/workflow.md`. This file adds project-specific details.

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

Worktree setup is in `worktree-setup.md`; editing rule files, in `rules-editing.md` (both path-scoped).
