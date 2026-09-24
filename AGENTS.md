# AI Agent Guidelines for Climate Finance History Project

> No `CLAUDE.md` here: Claude Code (2.1.277+) loads this file natively, plus the parent `~/CNRS/AGENTS.md`. Do not add a `CLAUDE.md` or `.claude/CLAUDE.md`; either one disables that fallback (enforced by pre-commit hook).

The generic workflow lives in the harness rules (`~/.claude/rules/`) and skill
catalog; project rules in `.claude/rules/` load when you touch the files they
cover. This file holds only what every session here needs.

## Credentials

`.env` holds machine settings and public Git identity only. Credentials live in
`~/.config/keys/`; each tool reads only its own value immediately before use.
Never write a credential into `.env` (details: `.claude/rules/keystore.md`).

## Merge gate

`make check-fast` + `make lint` (~40 s), then push and open a PR. Run the full
`make check` first only when the diff touches the pipeline surface (`scripts/`,
`libs/`, `dvc.yaml`, the Makefiles, or slow/integration tests).

**There is no CI** (ticket 0321). The slow tier runs ex post: `/lair` step 9 runs
the full `make check` on main and tickets each new failure. A merged PR is not
proof that main is green; failures your branch did not cause get their own ticket.

## Verify in proportion to what can break

Before merging, decide which checks the change needs and state them on the PR:

- **Tickets only**: `erg check` plus the ID-collision scan (`.claude/rules/git.md`).
- **Docs, config, STATE**: the merge gate, and a read of the loaded or rendered result.
- **Prose**: recompile the artifact; `/review-pr-prose` for manuscript text.
- **Data**: byte-compare the served views, build twice for determinism, check counts.
- **Code, pipeline, analysis**: tests for the changed behaviour, and the full `make check` when the pipeline surface moved.

Anything beyond tickets gets at least one reviewer on a model other than the
coder's (`/review-pr`, scoped to the risk); the merge hook counts review cycles,
not independence, so that choice is yours. Then `/verify-gate`: every ticket exit
criterion needs concrete evidence (commit SHA + file:line, or a test id). Two
review rounds at most, then escalate. The merge is the author's call when
interactive, the raid's when autonomous.

## Scope

One ticket per Execute conversation. Sub-issues found on the way become new
tickets, not a wider diff.
