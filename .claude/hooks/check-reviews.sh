#!/bin/bash
# PreToolUse hook: block PR merge unless enough review cycles completed.
#
# Reads the hook payload from stdin (JSON). Resolves *which PR on which repo*
# the command targets, queries GitHub for that PR's review count, and compares
# against a threshold taken from the PR labels.
#
# Proportionality:
#   - label "review:trivial"  → 1 review cycle minimum
#   - default                 → 2 review cycles minimum
#
# Output: JSON with permissionDecision "allow", "deny" or "ask".
#
# Why the repo is resolved and never assumed (harness ticket 0900): this script
# used to carry two repo-identity literals and read only the PR *number* from
# the command. A merge issued from this project against another repo was judged
# on this project's PR of the same number — a real, unrelated PR — and the
# verdict was pronounced with full confidence. It allowed one unreviewed merge
# and refused a properly reviewed one within the same hour. A gate whose
# failure is indistinguishable from a pass is not a gate, so when the target
# cannot be determined this hook now abstains ("ask") instead of guessing.

set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# .env no longer carries AGENT_GH_TOKEN (ticket 0343) — the keystore loader
# exports it. Still sourced for the non-secret settings, and the fallback below
# takes whichever of the two is populated, so this works either way.
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi
export GH_TOKEN="${AGENT_GH_TOKEN:-${GH_TOKEN:-}}"

# Read stdin (Claude Code sends the hook payload as JSON)
INPUT=$(cat)

# ---------------------------------------------------------------------------
# Resolve the target: which PR, on which repo.
#
# Emits one tab-separated line: STATUS <TAB> NUMBER <TAB> SLUG <TAB> REASON
#   ok      — number and slug both determined
#   notapr  — the command is not a pull-request merge; the gate has no opinion
#   abstain — it *is* a PR merge, but the target cannot be determined
#
# Precedence, strongest evidence first: the MCP tool's own owner/repo fields,
# an explicit --repo/-R selector, the repo named inside a PR URL, and only then
# the origin remote of the directory the command runs in — which is a
# measurement of what `gh` itself would resolve, not a guess about it.
# ---------------------------------------------------------------------------
RESOLVED=$(echo "$INPUT" | python3 -c "
import json, os, re, shlex, subprocess, sys

# Flags of \`gh pr merge\` that consume the following token, so a digit sitting
# in a commit body is never mistaken for the PR number.
VALUE_FLAGS = {
    '-R', '--repo', '-b', '--body', '-F', '--body-file', '-t', '--subject',
    '--match-head-commit', '--author-email',
}
SEPARATORS = {'&&', '||', ';', '|', '&'}


def emit(status, number='', slug='', reason=''):
    print('\t'.join((status, str(number), slug, reason)))
    sys.exit(0)


def normalize(slug):
    \"\"\"Reduce a repo selector to owner/name, or None if it is not one.\"\"\"
    if not slug:
        return None
    slug = slug.strip().rstrip('/')
    m = re.match(r'^(?:https?://|ssh://(?:[^@/]+@)?|git@)?([^/:]+)[:/](.+)$', slug)
    if m and '.' in m.group(1):
        host, path = m.group(1), m.group(2)
        if host.lower() not in ('github.com', 'www.github.com'):
            return None
        slug = path
    slug = slug.removesuffix('.git')
    parts = [p for p in slug.split('/') if p]
    if len(parts) != 2:
        return None
    return '/'.join(parts)


def git_out(cwd, *args):
    try:
        r = subprocess.run(
            ['git', '-C', cwd, *args], capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def remote_slug(cwd):
    \"\"\"The repo a bare \`gh pr merge\` would target from this directory.

    \`gh repo set-default\` records the choice as remote.<name>.gh-resolved, and
    gh consults it before falling back to origin. Reading origin alone was
    called a measurement of what gh resolves; under a fork topology it is not
    the same answer, and the gate went back to answering confidently about a
    repo nobody targeted (ticket 0707). Follow the same order gh does.
    \"\"\"
    if not cwd or not os.path.isdir(cwd):
        return None
    resolved = git_out(cwd, 'config', '--get-regexp', r'^remote\..*\.gh-resolved$')
    for line in (resolved or '').splitlines():
        key, _, value = line.partition(' ')
        value = value.strip()
        # gh writes either the literal 'base' (use that remote's URL) or an
        # explicit owner/name it resolved earlier.
        if value and value != 'base':
            explicit = normalize(value)
            if explicit:
                return explicit
        name = key[len('remote.'):-len('.gh-resolved')]
        url = git_out(cwd, 'remote', 'get-url', name)
        if url:
            slug = normalize(url)
            if slug:
                return slug
    url = git_out(cwd, 'remote', 'get-url', 'origin')
    return normalize(url) if url else None


data = json.load(sys.stdin)
ti = data.get('tool_input') or {}
cmd = ti.get('command') or ''

# --- Is this a pull-request merge at all? ---
mcp_number = ti.get('pullNumber') or ti.get('pull_number')
gh_merge = re.search(r'\bgh\s+pr\s+merge\b', cmd) is not None

# The REST form merges a pull request just as surely as \`gh pr merge\`, and the
# harness's own worktree guard prescribes it by name when \`gh pr merge\` refuses
# to run from a worktree. Recognising only the porcelain left the gate blind to
# the one path it tells people to take (ticket 0707). The path itself names the
# repo and the number, so this form needs no other resolution.
api_merge = re.search(
    r'repos/([^/\s]+)/([^/\s]+)/pulls/(\d+)/merge\b', cmd
) if re.search(r'\bgh\s+api\b', cmd) else None

if not mcp_number and not gh_merge and not api_merge:
    # \`git merge\`, a PR read through the API, or anything else that reached
    # this hook: not our business.
    emit('notapr')

number = None
slug = None

if api_merge:
    number = api_merge.group(3)
    slug = normalize(f'{api_merge.group(1)}/{api_merge.group(2)}')
elif mcp_number:
    number = str(mcp_number)
    owner, repo = ti.get('owner'), ti.get('repo')
    if owner and repo:
        slug = normalize(f'{owner}/{repo}')
elif gh_merge:
    try:
        toks = shlex.split(cmd)
    except ValueError:
        toks = cmd.split()

    start = None
    for i in range(len(toks) - 2):
        if toks[i].split('/')[-1] == 'gh' and toks[i + 1] == 'pr' and toks[i + 2] == 'merge':
            start = i + 3
            break

    positionals = []
    i = start if start is not None else len(toks)
    while i < len(toks):
        tok = toks[i]
        if tok in SEPARATORS:
            break
        if tok.startswith('--repo=') or tok.startswith('-R='):
            slug = normalize(tok.split('=', 1)[1])
            i += 1
            continue
        if tok in ('-R', '--repo'):
            if i + 1 < len(toks):
                slug = normalize(toks[i + 1])
            i += 2
            continue
        if tok in VALUE_FLAGS:
            i += 2
            continue
        if tok.startswith('-'):
            i += 1
            continue
        positionals.append(tok)
        i += 1

    # \`gh pr merge [<number> | <url> | <branch>]\` — the first positional.
    target = positionals[0] if positionals else None
    if target and target.isdigit():
        number = target
    elif target:
        m = re.search(r'^(?:https?://)?([^/]+)/([^/]+)/([^/]+)/pull/(\d+)', target)
        if m:
            number = m.group(4)
            slug = slug or normalize(f'{m.group(2)}/{m.group(3)}')

    if number is None:
        m = re.search(r'/pull/(\d+)', cmd)
        if m:
            number = m.group(1)

if number is None:
    # A PR merge whose subject we cannot name — \`gh pr merge --squash\` on the
    # current branch, or a branch name we would have to resolve ourselves.
    emit('abstain', reason='could not determine which PR this merge targets')

if slug is None:
    # No selector: the repo is whatever \`gh\` resolves from its working
    # directory. A directory change inside the command moves that target
    # somewhere the payload no longer describes, so stop rather than assume.
    if re.search(r'(?:^|[;&|]\s*)\s*(?:cd|pushd)\s', cmd):
        emit('abstain', reason='the command changes directory before merging')
    cwd = data.get('cwd') or os.environ.get('CLAUDE_PROJECT_DIR') or ''
    slug = remote_slug(cwd)

if slug is None:
    emit(
        'abstain',
        number=number,
        reason='no --repo selector and no GitHub origin remote to resolve it from',
    )

emit('ok', number=number, slug=slug)
" 2>/dev/null) || RESOLVED=""

if [ -z "$RESOLVED" ]; then
    # The resolver itself failed. That is not an all-clear either.
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"Merge gate could not parse this command — it cannot say whether the PR was reviewed. Confirm manually, or re-run naming the PR and repo explicitly."}}'
    exit 0
fi

IFS=$'\t' read -r STATUS PR_NUMBER REPO_SLUG ABSTAIN_REASON <<<"$RESOLVED"

case "$STATUS" in
    notapr)
        echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"Not a pull-request merge — the review gate does not apply."}}'
        exit 0
        ;;
    abstain)
        printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"Merge gate abstains: %s. It has checked nothing, and says so rather than guessing (ticket 0900)."}}\n' "$ABSTAIN_REASON"
        exit 0
        ;;
esac

# Tickets-only fast path (rules/git.md, "Ticket-filing PRs take the fast
# path"): a PR whose diff is only .erg files under tickets/ merges on
# `erg check` plus an ID-collision scan — review ceremony would be a
# self-posted label plus a self-review, pure procedure with no content, so
# the gate exempts it. The determination is conservative, so it cannot
# weaken the gate for code PRs:
#   - any non-ticket path, any rename whose source is outside tickets/,
#     an empty file list, or a list at the pagination cap (>= 100 files,
#     possibly truncated) → no exemption;
#   - any API or parse error → no exemption either: fall through to the
#     normal review count below, leaving error behaviour exactly as it is
#     today. The hook itself never dies and never denies from this block.
# The predicate is structural, so it holds for whichever repo is being judged:
# every git-erg adopter shapes ticket-filing diffs the same way.
TICKETS_ONLY=$(gh api "repos/$REPO_SLUG/pulls/$PR_NUMBER/files?per_page=100" 2>/dev/null \
    | python3 -c "
import sys, json, re
files = json.load(sys.stdin)
def is_ticket(path):
    return re.fullmatch(r'tickets/.+\.erg', path or '') is not None
paths = [f.get('filename') for f in files]
renames = [f.get('previous_filename') for f in files if f.get('previous_filename')]
ok = 0 < len(files) < 100 and all(is_ticket(p) for p in paths + renames)
print('yes' if ok else 'no')
" 2>/dev/null) || TICKETS_ONLY="no"

if [ "$TICKETS_ONLY" = "yes" ]; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"Tickets-only diff — fast path per rules/git.md; erg check + ID-collision scan are the gate, no review cycles required."}}'
    exit 0
fi

# Count reviews by any accepted reviewer on this PR.
#
# What this gate asserts: that enough review cycles have been posted on the PR:
#   - label "review:trivial"  → 1 review cycle minimum
#   - default                 → 2 review cycles minimum
# It is a *procedural* check, not an independence check — the project has one
# forge identity, so these reviews may be authored by the same account that
# opened the PR (ticket 0365, option 3b). Independence would mean requiring a
# reviewer other than the PR author, which would stop autonomous waves from
# merging unattended; that trade was declined deliberately.
# The substantive merge gate is local: `make check-fast` + `make lint` plus
# /verify (the full `make check` runs ex post on main via /lair step 9, and
# pre-PR only for pipeline-surface diffs — AGENTS.md § Execute); this hook only
# stops a merge that skipped the review step entirely.
#
# These logins are *reviewer* identity, not repo identity: they say whose
# review counts, and travel with the author across every repo this gate may be
# asked about. They are not what ticket 0900 removed.
# MinhHaDuong: the single forge identity — the agent token and the web MCP
#   token both authenticate as it, and it is also the PR author.
#   `HDMX-coding-agent` is a git author name, not a forge account
#   (`gh api users/HDMX-coding-agent` → 404); it was removed from this list
#   because it can never author a review.
# copilot-pull-request-reviewer[bot]: genuinely independent of the PR author,
#   counted when present. Not required — it does not review every PR.
AGENT_LOGINS="MinhHaDuong copilot-pull-request-reviewer[bot]"
REVIEW_COUNT=$(gh api "repos/$REPO_SLUG/pulls/$PR_NUMBER/reviews" 2>/dev/null \
    | AGENT_LOGINS="$AGENT_LOGINS" python3 -c "
import os, sys, json
allowed = set(os.environ['AGENT_LOGINS'].split())
reviews = json.load(sys.stdin)
count = sum(1 for r in reviews if r.get('user',{}).get('login') in allowed)
print(count)
" 2>/dev/null) || REVIEW_COUNT=0

# Check for review:trivial label
HAS_TRIVIAL=$(gh api "repos/$REPO_SLUG/issues/$PR_NUMBER/labels" 2>/dev/null \
    | python3 -c "
import sys, json
labels = json.load(sys.stdin)
count = sum(1 for l in labels if l.get('name') == 'review:trivial')
print(count)
" 2>/dev/null) || HAS_TRIVIAL=0

# Determine threshold
if [ "$HAS_TRIVIAL" -gt 0 ]; then
    REQUIRED=1
else
    REQUIRED=2
fi

if [ "$REVIEW_COUNT" -ge "$REQUIRED" ]; then
    echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"allow\",\"permissionDecisionReason\":\"$REVIEW_COUNT review(s) found on $REPO_SLUG#$PR_NUMBER, $REQUIRED required. Merge allowed.\"}}"
    exit 0
else
    echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"Only $REVIEW_COUNT review(s) found on $REPO_SLUG#$PR_NUMBER, $REQUIRED required. Run /review-pr $PR_NUMBER before merging.\"}}"
    exit 0
fi
