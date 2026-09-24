# On start — conversation start trigger

Runs after the user's first message, before the agent's first response.

## 1. Setup

Load `.env`, set agent identity, and activate hooks:
```bash
set -a && source .env && set +a
git config user.name  "$AGENT_GIT_NAME"
git config user.email "$AGENT_GIT_EMAIL"
git config core.hooksPath .githooks
```

`.env` supplies only these non-secret settings. For an authenticated GitHub
call, read the repository-scoped value immediately before the invocation:

```bash
GH_TOKEN="$(. "$HOME/.config/keys/github.env" && \
  printf '%s' "$AGENT_GH_TOKEN_CLIMATEFINANCE")" gh <arguments>
```

Do not export that value into the session or fall back to the generic token.
## 2. Orient

Read `STATE.md` and `ROADMAP.md`.

## 3. Branch and announce phase

**GATE — nothing below this step runs until a branch is checked out.**

Infer the DD phase from context, create or checkout the working branch,
then announce. The pre-commit hook blocks all commits on main, no exceptions.
**Branch immediately** — even for "small" fixes. Don't start editing files
on main and discover the hook at commit time.

| Context | Phase | Branch |
|---------|-------|--------|
| Fresh conversation, no ticket | `[→ Dreaming]` | Create `explore-{topic}` (name inferred from user's opening message) |
| Ticket reference but no branch | `[→ Planning]` | Create `explore-{topic}`; the `start-ticket` runbook shall create the `t{N}` branch when Doing begins |
| Active feature branch + open PR | `[→ Doing]` | Checkout existing branch |

If the conversation turns out to be a quick question with no file edits,
the branch is harmless — delete it at session end if empty.
