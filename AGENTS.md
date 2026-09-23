# AI Agent Guidelines for Climate Finance History Project

> `CLAUDE.md` contains only `@AGENTS.md` — do not modify it (enforced by pre-commit hook).

## Credentials

`.env` holds no secret. It carries machine settings and a `KEYS=` line naming
which credentials this project may load; the values live in
`~/.config/keys/<provider>.env` (mode 0600), outside the repository. Entry forms
are `provider`, `provider:VAR`, and `provider:SRC=DST` (rename on export), and
selection is default-deny — an unlisted provider is never loaded, which is what
stops a sibling project's keys from arriving here.

Two mechanisms apply the selection, because no single one covers every entry
point: the harness bash loader, which the Makefile wires into recipe shells via
`BASH_ENV`, and `scripts/pipeline_keystore.py`, which `pipeline_loaders` calls on
import so `dvc repro` and a bare `uv run python scripts/…` resolve too. Neither
overwrites an already-set variable. On a machine without the keystore both
degrade quietly and scripts report the missing key themselves.

This `KEYS=` line **overrides** the harness one; it does not add to it. The bash
loader exports every project-`.env` key verbatim, `KEYS` included, so whatever
starts with this directory as its cwd sees this selection and only this one —
including tools that have no code here, such as the harness `update-publist`
skill. A credential this repo never imports can still need naming here, which is
why `REQUIRED_KEYS_EXPORTS` in `tests/test_env_has_no_secret_literals.py` reads
"must resolve for work started in this repo" rather than "is read by code in this
repo" (ticket 0364).

Adding a credential means putting it in the right provider file and extending
`KEYS=` — never writing it into `.env`, which `tests/test_env_has_no_secret_literals.py`
enforces.

## Configuration

The generic workflow (phases, worktrees, delegation, escalation, git discipline)
lives in the harness rules under `~/.claude/rules/`, loaded into every session,
and skills are listed in each session's skill catalog. This file holds only what
is specific to this repo. Do not copy harness content back here: the copy drifts.
The skills table this file used to carry named seven skills that no longer
existed, and agents routed to their nearest living neighbour.

| Location | Purpose |
|----------|---------|
| `~/.claude/rules/` | Generic rules (workflow, git, runtime) |
| `~/.claude/skills/` | Generic skills (hunt, raid, roar, lair, review-pr, verify-gate, …) |
| `.claude/rules/` | Project-specific rules (writing, architecture, oeconomia-style, etc.) |
| `.claude/skills/` | Project-specific skills (submission-branch, submission-readiness) |
| `.claude/hooks/` | Project-specific hooks (merge gate review check) |
| `.claude/settings.json` | Project permissions and hooks |
| `.githooks/` | Git hooks (pre-commit, pre-push, post-checkout) |
| `.claude/rules/tickets.md` | %erg v1 ticket format spec and validator rules (scoped to tickets/) |

## Imagine: advisor stance

In an Imagine conversation, act as my high-level advisor. Generate a portfolio of
options with their probabilities, and go beyond conventional habits. Challenge my
thinking, question my assumptions, and expose blind spots. Stop defaulting to
agreement. If my reasoning is weak, break it down and show me why.

## Merge gate

Pass `make check-fast` + `make lint` (~40 s combined), then push and open a PR.
Run the full `make check` before the PR only when the diff touches the pipeline
surface (`scripts/`, `libs/`, `dvc.yaml`, the Makefiles, or `tests/` files marked
slow/integration); doc, prose, config, and ticket diffs skip it. Makefile truth:
prerequisites and targets must match each script's actual file reads and writes.

**There is no CI.** This repo has no `.github/workflows/`, by decision (ticket 0321, 2026-07-27). Nothing runs the suite on push or on a pull request: the gate above is purely local, and the slow/integration tier is verified **ex post**, not per PR — `/lair` step 9 runs the full `make check` on main at end of day and opens a ticket for each new failure (gate eased 2026-07-28: 18 days of session logs showed the full suite costing 4–10 min per gate run while catching nothing the fast tiers missed; every observed failure was environmental or fast/adherence-tier). Never read a merged PR as proof that main is green: when a full `make check` surfaces failures your branch did not cause, they belong to main, and they get their own ticket.

## Verify in proportion to what can break

Before merging, decide which checks the change needs and state them on the PR:

- **Tickets only**: `erg check` plus the ID-collision scan (`.claude/rules/git.md`).
- **Docs, config, STATE**: the merge gate above, and a read of the loaded or rendered result.
- **Prose**: recompile the artifact; `/review-pr-prose` for manuscript text.
- **Data**: byte-compare the served views, build twice for determinism, check counts.
- **Code, pipeline, analysis**: tests for the changed behaviour, and the full `make check` when the pipeline surface moved.

Anything beyond tickets gets at least one independent reviewer on a model other
than the coder's (`/review-pr`, scoped to the risk). Then run `/verify-gate`:
every ticket exit criterion needs concrete evidence (commit SHA + file:line, or a
test id). Two review rounds at most, then escalate to the author. The merge is
the author's call when interactive, the raid's when autonomous.

This replaces a fixed full-battery loop that cost up to an hour and a million
tokens on diffs a ten-minute check covered (pilot opened 2026-09-23).
