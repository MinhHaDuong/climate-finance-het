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

| Location | Purpose |
|----------|---------|
| `~/.claude/rules/` | Generic rules (git, workflow, coding, state-roadmap) |
| `~/.claude/skills/` | Generic skills (celebrate, review-pr, memory, etc.) |
| `~/.claude/hooks/` | Generic hooks (on-start identity setup) |
| `.claude/rules/` | Project-specific rules (writing, architecture, oeconomia-style, etc.) |
| `.claude/skills/` | Project-specific skills (submission-branch, submission-readiness) |
| `.claude/hooks/` | Project-specific hooks (merge gate review check) |
| `.claude/settings.json` | Project permissions and hooks |
| `.githooks/` | Git hooks (pre-commit, pre-push, post-checkout) |
| `.claude/rules/tickets.md` | %erg v1 ticket format spec and validator rules (scoped to tickets/) |

## Imperial Dragon workflow

Every task passes through five phases (five claws). Announce transitions inline: `[Phase → Phase] reason`.

### Imagine
Interactive discussion with the user on an `explore-{topic}` branch. Imagine specs, gather information, brainstorm freely. Ask questions, surface motivations, explore what success looks like.
Generate portfolio of options with their probabilities. Go beyond conventional habits to explore new approaches. Take the high road.
Act as my high-level advisor. Challenge my thinking, question my assumptions, and expose blind spots. Stop defaulting to agreement. If my reasoning is weak, break it down and show me why.

Commits are workspace artifacts unless the conversation produces a small fix. Deliverable: a shared vision, plus one of:

- **Tickets** — non-trivial work gets one ticket per action item (`/new-ticket`).
- **Small fix** — if it fits in one red/green/refactor cycle, do it on the explore branch. TDD still applies.
- **Nothing actionable** — delete the branch at session end.

### Plan
Explore alternatives, design strategies, prototype approaches. Use GitHub Issues as the planning artifact — write tickets with full context (`/new-ticket`). **Specify the first test in the ticket** — the Execute phase enforces TDD. Review tickets for intent over metrics. No production commits yet. Deliverable: a ticket with test spec.

### Execute
Runs in a fresh context — the ticket is the only input. Launch via `/start-ticket`.

Autonomous execution using test-driven development. The inner cycle is:

1. **Red**: write a failing test that defines the expected behavior. Commit.
2. **Green**: write the minimum code to make it pass. Commit.
3. **Refactor**: clean up, then confirm tests still pass. Use `make check-fast` during development. Commit.
4. **PR**: Pass `make check` gate, then push and open a PR.

Use `make check-fast` during development, `make check` before opening a PR. Makefile truth: prerequisites and targets must match each script's actual file reads and writes.

**There is no CI.** This repo has no `.github/workflows/`, by decision (ticket 0321, 2026-07-27). Nothing runs the suite on push or on a pull request: `make check` is a purely local gate, and a green main is only ever whatever the last session verified on its own machine. Two consequences. Run `make check` yourself before opening a PR — no forge job will do it for you. And never read a merged PR as proof that main is green: when a full `make check` surfaces failures your branch did not cause, they belong to main, and they get their own ticket.

### Verify
Gate each PR before merging via `/verify <pr-number>`. The skill runs the full loop:

1. `/verify-adherence` — mechanical-first rule check (hygiene tests + grep ratchet, LLM fallback only for semantic residue).
2. `/review` (built-in) + `/review-pr` or `/review-pr-prose` (skill) — read-only review fan-out.
3. `/simplify` — reuse / quality / efficiency, applies fixes.
4. `/verify-gate` — anti-rubber-stamp gate. Every ticket exit criterion requires concrete evidence (commit SHA + file:line OR test_id). "CI passes" / "simplify ran" are NOT evidence.

Verdict: APPROVED / REROLL / ESCALATE. Two rounds max — round 3 is forbidden. `/verify` never merges; merge is the author's call (interactive) or `/celebrate`'s call (autonomous).

`--force-approve` is a loud human override, logged on the PR. Use it sparingly.

### Celebrate (autonomous)
Runs via `/celebrate`. Celebrating is not a formality — it closes the energy cycle. Reflect on what was accomplished and learned, consolidate memory, dream forward.

### Phase state

The agent must always know and declare its current phase.

- **At conversation start**: workflow rule infers the initial phase and announces it (e.g., `[→ Imagine]`).
- **At each transition**: announce explicitly with `[Phase → Phase] reason`.
- **No implicit transitions**: if no announcement was made, the phase hasn't changed.

## Skills (slash commands)

| Skill | When | Purpose |
|-------|------|---------|
| `/start-ticket N` | Starting work on a GitHub issue | Create worktree, write first test, transition to Execute |
| `/celebrate` | After completing a ticket | Reflect, update STATE/ROADMAP, clean up |
| `/end-session` | User ends a work session | Push branches, run tests, refresh STATE |
| `/new-ticket` | Creating a GitHub issue | Write handoff document with test spec |
| `/verify N` | Gating a PR before merge | Full loop: adherence + review + review-pr + simplify + gate; bounces PR for at most one retry |
| `/verify-adherence N` | Rule-check a branch | Mechanical-first (tests + grep ratchet); LLM fallback emits suggested_test entries |
| `/verify-gate N` | Standalone merge gate | Anti-rubber-stamp; per-exit-criterion evidence required |
| `/review-pr N` | Lightweight code review | Multi-perspective agents; posts comments only, no fixes, no gate |
| `/review-pr-prose N` | Lightweight prose review | Simulated peer review panel |
| `/memory` | Writing or sweeping persistent memory | Enforce caps, TTLs, staleness |
| `/autonomous` | Unsupervised autonomous session | Imperial Dragon cycles with 60/40 balance |
| `/submission-branch` | Creating a submission branch | Sprout, freeze, revision lifecycle |
| `/submission-readiness` | Pre-submission gate | Checklist before sprouting |

## Autonomous workflow

When issue exploration leads to multiple action items, open one ticket for each under a tracking ticket. Then work in waves, learning from each.

### Wave cycle

1. **Select** — pick ripe tickets (dependencies met, blockers cleared).
2. **Launch** — each ticket in its own worktree, independent tickets in parallel.
3. **Verify** — gate each PR via `/verify` (in its own worktree).
4. **Learn** — for each result:
   - **Success**: `/celebrate`, save what worked as feedback memory.
   - **Failure**: diagnose root cause, save lesson, re-ticket with diagnosis.
5. **Adapt** — read feedback memories before planning the next wave.
6. **Clean up** — worktrees, branches, stale PRs. Then start the next wave.

## Conversation scope

**Imagine conversations**: may produce zero or many tickets, or inline small fixes. The explore branch is the workspace; the tickets (or PR) are the deliverables.

**Execute conversations**: one ticket per conversation. Transition to Celebrate when the PR is merged and ticket closed. If investigation reveals sub-issues, open them as new tickets — don't scope-creep.
