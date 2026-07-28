"""Tests for .claude/hooks/check-reviews.sh merge gate.

Verifies that the hook blocks or allows PR merges based on review count
and proportional risk labels.
"""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

HOOK_SCRIPT = Path(__file__).parent.parent / ".claude" / "hooks" / "check-reviews.sh"


def run_hook(
    tool_input_json: str,
    gh_responses: dict[str, str] | None = None,
    tmp_path: Path | None = None,
) -> dict:
    """Run check-reviews.sh with mocked stdin and gh CLI.

    Parameters
    ----------
    tool_input_json : str
        JSON string to feed as stdin (simulates Claude Code hook input).
    gh_responses : dict
        Mapping of gh api URL fragments to JSON response strings.
        A mock `gh` script returns these based on the first positional arg.
    tmp_path : Path
        Temporary directory for mock scripts (from pytest fixture).

    Returns
    -------
    dict with keys: returncode, stdout (parsed JSON), stderr

    """
    project_dir = Path(__file__).parent.parent

    # Build a mock gh script that returns canned responses
    mock_gh = "#!/bin/bash\n"
    if gh_responses:
        for url_fragment, response in gh_responses.items():
            # gh api <url> --jq <expr> → we match on the URL fragment
            mock_gh += (
                f'if echo "$@" | grep -q "{url_fragment}"; then\n'
                f"  echo '{response}'\n"
                f"  exit 0\n"
                f"fi\n"
            )
    mock_gh += "echo '[]'\nexit 0\n"

    # Write mock gh to pytest-managed temp dir
    mock_dir = tmp_path or (project_dir / ".test_tmp")
    mock_dir.mkdir(exist_ok=True)
    mock_gh_path = mock_dir / "gh"
    mock_gh_path.write_text(mock_gh)
    mock_gh_path.chmod(0o755)

    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["PATH"] = f"{mock_dir}:{env['PATH']}"
    env["GH_TOKEN"] = "fake-token"
    env["AGENT_GH_TOKEN"] = "fake-token"
    env["AGENT_GIT_NAME"] = "HDMX-coding-agent"

    result = subprocess.run(
        ["bash", str(HOOK_SCRIPT)],
        input=tool_input_json,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    stdout_json = json.loads(result.stdout) if result.stdout.strip() else {}
    return {
        "returncode": result.returncode,
        "stdout": stdout_json,
        "stderr": result.stderr,
    }


def make_bash_input(command: str) -> str:
    """Create hook stdin JSON for a Bash tool call."""
    return json.dumps({"tool_input": {"command": command}})


def make_mcp_input(pull_number: int) -> str:
    """Create hook stdin JSON for an MCP merge tool call."""
    return json.dumps({"tool_input": {"pullNumber": pull_number}})


# --- Core gate logic ---


@pytest.mark.integration
class TestMergeGate:
    """Merge gate blocks or allows based on review count vs. threshold."""

    def test_zero_reviews_blocks(self, tmp_path):
        """0 reviews, no trivial label → deny (need 2)."""
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/reviews": "[]",
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert result["returncode"] == 0
        decision = result["stdout"]["hookSpecificOutput"]["permissionDecision"]
        assert decision == "deny"

    def test_one_review_no_trivial_blocks(self, tmp_path):
        """1 review, no trivial label → deny (need 2)."""
        reviews = json.dumps([{"user": {"login": "MinhHaDuong"}}])
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/reviews": reviews,
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        decision = result["stdout"]["hookSpecificOutput"]["permissionDecision"]
        assert decision == "deny"

    def test_one_review_with_trivial_allows(self, tmp_path):
        """1 review + review:trivial label → allow (need 1)."""
        reviews = json.dumps([{"user": {"login": "MinhHaDuong"}}])
        labels = json.dumps([{"name": "review:trivial"}])
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/reviews": reviews,
                "issues/42/labels": labels,
            },
            tmp_path=tmp_path,
        )
        decision = result["stdout"]["hookSpecificOutput"]["permissionDecision"]
        assert decision == "allow"

    def test_independent_bot_review_counts(self, tmp_path):
        """A Copilot review counts — it is the one reviewer not the PR author."""
        reviews = json.dumps(
            [
                {"user": {"login": "MinhHaDuong"}},
                {"user": {"login": "copilot-pull-request-reviewer[bot]"}},
            ]
        )
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/reviews": reviews,
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert result["stdout"]["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_unknown_login_does_not_count(self, tmp_path):
        """A review by a login outside the list does not satisfy the gate."""
        reviews = json.dumps(
            [
                {"user": {"login": "some-drive-by"}},
                {"user": {"login": "another-stranger"}},
            ]
        )
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/reviews": reviews,
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert result["stdout"]["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_two_reviews_allows(self, tmp_path):
        """2 reviews, no trivial label → allow (need 2)."""
        reviews = json.dumps(
            [
                {"user": {"login": "MinhHaDuong"}},
                {"user": {"login": "MinhHaDuong"}},
            ]
        )
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/reviews": reviews,
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        decision = result["stdout"]["hookSpecificOutput"]["permissionDecision"]
        assert decision == "allow"

    def test_minhhaduong_review_counts(self, tmp_path):
        """Review by MinhHaDuong (web MCP identity) counts toward threshold."""
        reviews = json.dumps([{"user": {"login": "MinhHaDuong"}}])
        labels = json.dumps([{"name": "review:trivial"}])
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/reviews": reviews,
                "issues/42/labels": labels,
            },
            tmp_path=tmp_path,
        )
        decision = result["stdout"]["hookSpecificOutput"]["permissionDecision"]
        assert decision == "allow"

    def test_unknown_reviewer_ignored(self, tmp_path):
        """Review by a login not in the allowlist does not count toward threshold."""
        reviews = json.dumps([{"user": {"login": "random-outsider"}}])
        labels = json.dumps([{"name": "review:trivial"}])
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/reviews": reviews,
                "issues/42/labels": labels,
            },
            tmp_path=tmp_path,
        )
        decision = result["stdout"]["hookSpecificOutput"]["permissionDecision"]
        assert decision == "deny"


# --- Tickets-only fast path (rules/git.md) ---


def make_files_response(*files: str | tuple[str, str]) -> str:
    """Build a pulls/N/files JSON response.

    Each item is a filename, or a (filename, previous_filename) tuple for a
    rename.
    """
    payload = []
    for f in files:
        if isinstance(f, tuple):
            payload.append({"filename": f[0], "previous_filename": f[1]})
        else:
            payload.append({"filename": f})
    return json.dumps(payload)


@pytest.mark.integration
class TestTicketsOnlyFastPath:
    """A diff that is only tickets/*.erg is exempt from the review count.

    rules/git.md ("Ticket-filing PRs take the fast path") says such a PR
    merges on `erg check` plus an ID-collision scan, with no review ceremony.
    The gate honours that: zero reviews, no label, still allowed — but only
    when every changed file (and every rename source) is a .erg under
    tickets/. Anything else falls through to the normal review gate.
    """

    def test_tickets_only_diff_allows_without_reviews(self, tmp_path):
        """Filing PR: one new tickets/*.erg, 0 reviews, no label → allow."""
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/files": make_files_response("tickets/0400-some-task.erg"),
                "pulls/42/reviews": "[]",
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert result["returncode"] == 0
        decision = result["stdout"]["hookSpecificOutput"]["permissionDecision"]
        assert decision == "allow"

    def test_ticket_close_rename_allows(self, tmp_path):
        """A close PR renaming tickets/*.erg into tickets/closed/ → allow."""
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/files": make_files_response(
                    ("tickets/closed/0400-some-task.erg", "tickets/0400-some-task.erg"),
                ),
                "pulls/42/reviews": "[]",
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        decision = result["stdout"]["hookSpecificOutput"]["permissionDecision"]
        assert decision == "allow"

    def test_mixed_diff_keeps_the_full_gate(self, tmp_path):
        """A ticket plus one code file → the review gate applies (deny at 0)."""
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/files": make_files_response(
                    "tickets/0400-some-task.erg", "scripts/compute_vars.py"
                ),
                "pulls/42/reviews": "[]",
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        decision = result["stdout"]["hookSpecificOutput"]["permissionDecision"]
        assert decision == "deny"

    def test_rename_from_outside_tickets_is_not_exempt(self, tmp_path):
        """A file smuggled in by renaming code into tickets/*.erg → deny."""
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/files": make_files_response(
                    ("tickets/0400-evil.erg", "scripts/compute_vars.py"),
                ),
                "pulls/42/reviews": "[]",
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        decision = result["stdout"]["hookSpecificOutput"]["permissionDecision"]
        assert decision == "deny"

    def test_non_erg_file_under_tickets_is_not_exempt(self, tmp_path):
        """tickets/.ergrc is config, not a ticket — the full gate applies."""
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/files": make_files_response("tickets/.ergrc"),
                "pulls/42/reviews": "[]",
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        decision = result["stdout"]["hookSpecificOutput"]["permissionDecision"]
        assert decision == "deny"

    def test_empty_file_list_is_not_exempt(self, tmp_path):
        """An empty files response proves nothing — fall through to the gate."""
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/files": "[]",
                "pulls/42/reviews": "[]",
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        decision = result["stdout"]["hookSpecificOutput"]["permissionDecision"]
        assert decision == "deny"

    def test_possibly_truncated_file_list_is_not_exempt(self, tmp_path):
        """100 files = the pagination cap; page 2 could hold code → deny.

        The hook asks for per_page=100 and does not paginate, so a list of
        exactly 100 ticket files cannot be distinguished from a longer diff
        whose tail is code. The exemption must refuse to guess.
        """
        files = make_files_response(
            *[f"tickets/{i:04d}-bulk.erg" for i in range(100)]
        )
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/files": files,
                "pulls/42/reviews": "[]",
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        decision = result["stdout"]["hookSpecificOutput"]["permissionDecision"]
        assert decision == "deny"

    def test_files_api_garbage_falls_through_to_review_gate(self, tmp_path):
        """A broken files response never crashes the hook; the gate still works."""
        reviews = json.dumps(
            [
                {"user": {"login": "MinhHaDuong"}},
                {"user": {"login": "MinhHaDuong"}},
            ]
        )
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/files": "this is not json",
                "pulls/42/reviews": reviews,
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert result["returncode"] == 0
        decision = result["stdout"]["hookSpecificOutput"]["permissionDecision"]
        assert decision == "allow"


# --- PR number extraction ---


@pytest.mark.integration
class TestPRNumberExtraction:
    """Hook extracts PR number from various tool input formats."""

    def test_bash_gh_pr_merge(self, tmp_path):
        """Extracts from 'gh pr merge 42'."""
        reviews = json.dumps(
            [
                {"user": {"login": "MinhHaDuong"}},
                {"user": {"login": "MinhHaDuong"}},
            ]
        )
        result = run_hook(
            make_bash_input("gh pr merge 42"),
            gh_responses={
                "pulls/42/reviews": reviews,
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        # If it found PR 42, it will have queried reviews — allow proves extraction worked
        assert result["stdout"]["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_mcp_merge_tool(self, tmp_path):
        """Extracts from MCP tool input with pullNumber (camelCase)."""
        reviews = json.dumps(
            [
                {"user": {"login": "MinhHaDuong"}},
                {"user": {"login": "MinhHaDuong"}},
            ]
        )
        result = run_hook(
            make_mcp_input(42),
            gh_responses={
                "pulls/42/reviews": reviews,
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert result["stdout"]["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_no_pr_number_allows(self, tmp_path):
        """If PR number can't be determined, allow (don't block git merge)."""
        result = run_hook(
            json.dumps({"tool_input": {"command": "git merge feature-branch"}}),
            tmp_path=tmp_path,
        )
        decision = result["stdout"]["hookSpecificOutput"]["permissionDecision"]
        assert decision == "allow"

    def test_url_format(self, tmp_path):
        """Extracts PR number from URL in command."""
        reviews = json.dumps(
            [
                {"user": {"login": "MinhHaDuong"}},
                {"user": {"login": "MinhHaDuong"}},
            ]
        )
        result = run_hook(
            make_bash_input(
                "gh pr merge https://github.com/minhhaduong/oeconomia-climate-finance/pull/42"
            ),
            gh_responses={
                "pulls/42/reviews": reviews,
                "issues/42/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert result["stdout"]["hookSpecificOutput"]["permissionDecision"] == "allow"


# --- Registration: a correct hook that never fires is not a gate ---

SETTINGS = Path(__file__).parent.parent / ".claude" / "settings.json"


def pretooluse_entries() -> list[dict]:
    """PreToolUse hook registrations from .claude/settings.json."""
    return json.loads(SETTINGS.read_text())["hooks"]["PreToolUse"]


def matches_tool(matcher: str, tool_name: str) -> bool:
    """Whether `matcher` fires on `tool_name`, as Claude Code resolves it.

    An uncompilable matcher fires on nothing, so it is False rather than an
    error — `Bash(*gh pr merge*)` is not valid regex ("nothing to repeat").
    """
    try:
        return re.fullmatch(matcher, tool_name) is not None
    except re.error:
        return False


class TestHookRegistration:
    """The gate must be wired to a matcher Claude Code will actually fire.

    Claude Code matches `matcher` against the **tool name** as a regex.
    Permission-rule syntax (`Bash(gh pr merge *)`) belongs in a handler's
    optional `if` field, not in `matcher`. Registered under a matcher that
    matches no tool name, a hook is silently inert: it never runs, never
    denies, and leaves no trace that it did not. Ticket 0365 found the merge
    gate in exactly that state — the script below passes every behavioural
    test above, yet 35 of the 40 most recent merged PRs carried zero reviews.
    """

    def test_merge_gate_matches_the_bash_tool_name(self):
        """Some PreToolUse entry running the gate matches the tool name 'Bash'."""
        matchers = [
            entry.get("matcher", "")
            for entry in pretooluse_entries()
            if any(
                "check-reviews.sh" in h.get("command", "")
                for h in entry.get("hooks", [])
            )
        ]
        assert matchers, "check-reviews.sh is not registered under any PreToolUse entry"
        assert any(matches_tool(m, "Bash") for m in matchers), (
            f"No matcher fires on the Bash tool: {matchers}. "
            "PreToolUse matchers match the tool name; narrow by command with "
            "an `if` field on the handler."
        )

    def test_merge_gate_narrows_to_merge_commands(self):
        """The Bash-matcher registration carries an `if` filter for the merge command.

        The matcher fires on every Bash call, so the `if` field is what makes
        this a merge gate rather than a tax on the whole session. Dropping or
        misspelling it satisfies the two tests around this one — the matcher is
        still `Bash`, still free of permission-rule syntax — while the hook
        shells out to the forge API before every command the agent runs.
        """
        handlers = [
            h
            for entry in pretooluse_entries()
            if matches_tool(entry.get("matcher", ""), "Bash")
            for h in entry.get("hooks", [])
            if "check-reviews.sh" in h.get("command", "")
        ]
        assert handlers, "the gate is not registered under a matcher firing on Bash"
        unfiltered = [h for h in handlers if "gh pr merge" not in h.get("if", "")]
        assert not unfiltered, (
            "A Bash-matcher gate with no `if` filter for 'gh pr merge' runs on "
            f"every Bash call: {unfiltered}"
        )

    def test_no_matcher_uses_permission_rule_syntax(self):
        """No PreToolUse matcher carries permission-rule parentheses."""
        offenders = [
            entry.get("matcher", "")
            for entry in pretooluse_entries()
            if "(" in entry.get("matcher", "")
        ]
        assert not offenders, (
            f"Matchers use permission-rule syntax and will never fire: {offenders}. "
            "Move the command pattern to an `if` field on the handler."
        )

    def test_agent_logins_are_resolvable_accounts(self):
        """Every login the gate counts must be able to author a review.

        A login that matches no forge account can never appear as a review
        author, so listing it inflates the apparent breadth of the gate while
        contributing nothing (ticket 0365).
        """
        script = HOOK_SCRIPT.read_text()
        match = re.search(r'^AGENT_LOGINS="([^"]*)"', script, re.MULTILINE)
        assert match, "AGENT_LOGINS not found in check-reviews.sh"
        logins = match.group(1).split()
        assert logins, "AGENT_LOGINS is empty — the gate would count nothing"
        assert "HDMX-coding-agent" not in logins, (
            "HDMX-coding-agent is a git author name, not a forge account "
            "(`gh api users/HDMX-coding-agent` → 404); it can never author a review."
        )
