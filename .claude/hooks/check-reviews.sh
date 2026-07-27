#!/bin/bash
# PreToolUse hook: block PR merge unless enough review cycles completed.
#
# Reads tool_input from stdin (JSON). Extracts PR number, queries GitHub API
# for review count, compares against threshold from PR labels.
#
# Proportionality:
#   - label "review:trivial"  → 1 review cycle minimum
#   - default                 → 2 review cycles minimum
#
# Output: JSON with permissionDecision "allow" or "deny".

set -euo pipefail

cd "$CLAUDE_PROJECT_DIR" || exit 0

# .env no longer carries AGENT_GH_TOKEN (ticket 0343) — the keystore loader
# exports it. Still sourced for the non-secret settings, and the fallback below
# takes whichever of the two is populated, so this works either way.
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi
export GH_TOKEN="${AGENT_GH_TOKEN:-${GH_TOKEN:-}}"

OWNER="minhhaduong"
REPO="oeconomia-climate-finance"

# Read stdin (Claude Code sends JSON with tool_input)
INPUT=$(cat)

# Extract PR number from tool input.
# For Bash(*gh pr merge*): parse from command string
# For mcp__github__merge_pull_request: parse from pull_number field
PR_NUMBER=""

# Try MCP tool input first (pullNumber camelCase, or pull_number snake_case)
PR_NUMBER=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
ti = data.get('tool_input', {})
# MCP merge tool sends 'pullNumber' (camelCase); accept snake_case as fallback
pn = ti.get('pullNumber', '') or ti.get('pull_number', '')
if pn:
    print(pn)
    sys.exit(0)
# Bash: extract from command string like 'gh pr merge 42'
import re
cmd = ti.get('command', '')
m = re.search(r'gh\s+pr\s+merge\s+(\d+)', cmd)
if m:
    print(m.group(1))
    sys.exit(0)
# Also try URL patterns like 'gh pr merge https://...pull/42'
m = re.search(r'/pull/(\d+)', cmd)
if m:
    print(m.group(1))
    sys.exit(0)
sys.exit(1)
" 2>/dev/null) || true

if [ -z "$PR_NUMBER" ]; then
    # Can't determine PR number — allow (don't block non-PR merges like git merge)
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"Could not determine PR number — allowing."}}'
    exit 0
fi

# Count reviews by any accepted reviewer on this PR.
# HDMX-coding-agent: a git author name only — no such GitHub account exists
#   (`gh api users/HDMX-coding-agent` returns 404), so it can never appear as a
#   review author and this half of the list matches nothing. The gate therefore
#   rests entirely on the entry below. Left in place rather than silently
#   dropped: whether to provision a real machine account is the author's call.
# MinhHaDuong: personal identity used by the web MCP token (same as PR author).
#   Accepting it enables web-agent merges at the cost of permitting self-review.
AGENT_LOGINS="HDMX-coding-agent MinhHaDuong"
REVIEW_COUNT=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews" 2>/dev/null \
    | AGENT_LOGINS="$AGENT_LOGINS" python3 -c "
import os, sys, json
allowed = set(os.environ['AGENT_LOGINS'].split())
reviews = json.load(sys.stdin)
count = sum(1 for r in reviews if r.get('user',{}).get('login') in allowed)
print(count)
" 2>/dev/null) || REVIEW_COUNT=0

# Check for review:trivial label
HAS_TRIVIAL=$(gh api "repos/$OWNER/$REPO/issues/$PR_NUMBER/labels" 2>/dev/null \
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
    echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"allow\",\"permissionDecisionReason\":\"$REVIEW_COUNT review(s) found, $REQUIRED required. Merge allowed.\"}}"
    exit 0
else
    echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"Only $REVIEW_COUNT review(s) found, $REQUIRED required. Run /review-pr $PR_NUMBER before merging.\"}}"
    exit 0
fi
