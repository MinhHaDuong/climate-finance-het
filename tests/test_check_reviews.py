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


# --- Which repo the gate judges (ticket 0900) ---

# The two slugs of the experiment in harness ticket 0900. The gate lives in
# this project, so `OTHER_REPO` is the repo a command can target from here
# while the hook, before the fix, silently answered about `OWN_REPO`.
OWN_REPO = "MinhHaDuong/climate-finance-het"
OTHER_REPO = "MinhHaDuong/ImperialDragonHarness"

_TWO_REVIEWS = json.dumps(
    [{"user": {"login": "MinhHaDuong"}}, {"user": {"login": "MinhHaDuong"}}]
)
_NO_REVIEWS = "[]"


def make_payload(command: str, cwd: str | None = None) -> str:
    """Hook stdin for a Bash call, with the session cwd the payload carries.

    Claude Code sends `cwd` at the top level of every hook payload. That is
    the directory the command runs in, hence the repo `gh` resolves when the
    command names none — the only non-guessing answer available to the hook.
    """
    payload: dict = {"tool_input": {"command": command}}
    if cwd is not None:
        payload["cwd"] = cwd
    return json.dumps(payload)


def decision_of(result: dict) -> str:
    return result["stdout"]["hookSpecificOutput"]["permissionDecision"]


@pytest.mark.integration
class TestGateJudgesTheTargetedRepo:
    """The gate must answer about the repo the command targets.

    Harness ticket 0900: the hook carried two repo-identity literals and never
    read the `--repo` selector, so a merge command issued from this project
    against another repo was judged on *this* repo's PR of the same number —
    a real PR, an unrelated one, and the verdict was pronounced on it.

    Every test here is a positive control in the ticket's sense: the wrong
    repo is stocked with the *opposite* review state, so a hook that reads the
    wrong one returns the opposite verdict rather than an accidentally correct
    one. A fixture where both repos agree would pass before and after the fix
    and would prove nothing.
    """

    def test_targeted_repo_unreviewed_is_denied_though_own_repo_is_reviewed(
        self, tmp_path
    ):
        """The false allow of 2026-09-10, in miniature.

        PR 859 on the targeted repo has no review and must be refused. PR 859
        on this project has two and would be waved through. Before the fix the
        hook allowed the merge, having checked a PR nobody asked about.
        """
        result = run_hook(
            make_payload(f"gh pr merge 859 --repo {OTHER_REPO}"),
            gh_responses={
                f"{OTHER_REPO}/pulls/859/reviews": _NO_REVIEWS,
                f"{OTHER_REPO}/issues/859/labels": "[]",
                f"{OWN_REPO}/pulls/859/reviews": _TWO_REVIEWS,
                f"{OWN_REPO}/issues/859/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert decision_of(result) == "deny"

    def test_targeted_repo_reviewed_is_allowed_though_own_repo_is_not(self, tmp_path):
        """The false deny an hour later — the bug blocking its own ticket.

        PR 861 on the targeted repo carries the two reviews the gate wants.
        PR 861 here carries none. Before the fix the hook denied a merge that
        had been reviewed exactly as required.
        """
        result = run_hook(
            make_payload(f"gh pr merge 861 --repo {OTHER_REPO}"),
            gh_responses={
                f"{OTHER_REPO}/pulls/861/reviews": _TWO_REVIEWS,
                f"{OTHER_REPO}/issues/861/labels": "[]",
                f"{OWN_REPO}/pulls/861/reviews": _NO_REVIEWS,
                f"{OWN_REPO}/issues/861/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert decision_of(result) == "allow"

    def test_short_repo_flag_is_read(self, tmp_path):
        """`-R` is the same selector spelled shorter, and gh accepts both."""
        result = run_hook(
            make_payload(f"gh pr merge 861 -R {OTHER_REPO}"),
            gh_responses={
                f"{OTHER_REPO}/pulls/861/reviews": _TWO_REVIEWS,
                f"{OTHER_REPO}/issues/861/labels": "[]",
                f"{OWN_REPO}/pulls/861/reviews": _NO_REVIEWS,
                f"{OWN_REPO}/issues/861/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert decision_of(result) == "allow"

    def test_pr_url_names_its_own_repo(self, tmp_path):
        """A PR URL carries owner and repo; the gate must not ignore them."""
        result = run_hook(
            make_payload(f"gh pr merge https://github.com/{OTHER_REPO}/pull/861"),
            gh_responses={
                f"{OTHER_REPO}/pulls/861/reviews": _TWO_REVIEWS,
                f"{OTHER_REPO}/issues/861/labels": "[]",
                f"{OWN_REPO}/pulls/861/reviews": _NO_REVIEWS,
                f"{OWN_REPO}/issues/861/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert decision_of(result) == "allow"

    def test_mcp_owner_and_repo_fields_are_read(self, tmp_path):
        """The MCP merge tool names the repo in its own fields."""
        owner, name = OTHER_REPO.split("/")
        payload = json.dumps(
            {"tool_input": {"owner": owner, "repo": name, "pullNumber": 861}}
        )
        result = run_hook(
            payload,
            gh_responses={
                f"{OTHER_REPO}/pulls/861/reviews": _TWO_REVIEWS,
                f"{OTHER_REPO}/issues/861/labels": "[]",
                f"{OWN_REPO}/pulls/861/reviews": _NO_REVIEWS,
                f"{OWN_REPO}/issues/861/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert decision_of(result) == "allow"

    def test_bare_number_resolves_against_the_session_cwd(self, tmp_path):
        """No selector → the repo `gh` itself would resolve: the cwd's remote.

        This is a measurement, not the guess the ticket forbids: it reads the
        origin remote of the directory the command runs in. Here that cwd is
        a scratch clone whose origin is the *other* repo, so a hook still
        answering about its own project returns the opposite verdict.
        """
        clone = tmp_path / "elsewhere"
        clone.mkdir()
        subprocess.run(["git", "init", "-q", str(clone)], check=True)
        subprocess.run(
            ["git", "-C", str(clone), "remote", "add", "origin",
             f"git@github.com:{OTHER_REPO}.git"],
            check=True,
        )
        result = run_hook(
            make_payload("gh pr merge 861", cwd=str(clone)),
            gh_responses={
                f"{OTHER_REPO}/pulls/861/reviews": _TWO_REVIEWS,
                f"{OTHER_REPO}/issues/861/labels": "[]",
                f"{OWN_REPO}/pulls/861/reviews": _NO_REVIEWS,
                f"{OWN_REPO}/issues/861/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert decision_of(result) == "allow"


@pytest.mark.integration
class TestUndeterminableRepoAbstains:
    """Cannot tell which repo → say so, never answer about a guess.

    The ticket's form defect: the hook emitted an "allow" indistinguishable
    from "I could not look". `ask` is the one verdict that is neither — it
    neither waves the merge through nor blocks a legitimate one, it hands the
    call back. A deny here would be just as wrong in the other direction: the
    gate would be refusing merges it has no opinion about.
    """

    def test_cwd_outside_any_repo_abstains(self, tmp_path):
        """No selector and a cwd with no origin remote → nothing to measure."""
        nowhere = tmp_path / "nowhere"
        nowhere.mkdir()
        result = run_hook(
            make_payload("gh pr merge 861", cwd=str(nowhere)),
            gh_responses={
                f"{OWN_REPO}/pulls/861/reviews": _TWO_REVIEWS,
                f"{OWN_REPO}/issues/861/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert decision_of(result) == "ask"

    def test_directory_change_in_the_command_abstains(self, tmp_path):
        """A `cd` moves the merge somewhere the payload cwd no longer describes."""
        result = run_hook(
            make_payload("cd ../other-project && gh pr merge 861", cwd="/tmp"),
            gh_responses={
                f"{OWN_REPO}/pulls/861/reviews": _TWO_REVIEWS,
                f"{OWN_REPO}/issues/861/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert decision_of(result) == "ask"

    def test_non_github_remote_abstains(self, tmp_path):
        """The gate speaks one forge's API; another host is not its business."""
        clone = tmp_path / "gitlab-clone"
        clone.mkdir()
        subprocess.run(["git", "init", "-q", str(clone)], check=True)
        subprocess.run(
            ["git", "-C", str(clone), "remote", "add", "origin",
             "git@gitlab.com:someone/elsewhere.git"],
            check=True,
        )
        result = run_hook(
            make_payload("gh pr merge 861", cwd=str(clone)),
            tmp_path=tmp_path,
        )
        assert decision_of(result) == "ask"

    def test_pr_merge_without_a_number_abstains(self, tmp_path):
        """`gh pr merge --squash` merges the current branch's PR, unnamed.

        The number is as undeterminable as the repo, and the same rule applies:
        before the fix this returned "allow", the exact shape the ticket's
        "défaut de forme" section names. A command that is not a PR merge at
        all still allows — see `test_no_pr_number_allows`; the gate has no
        opinion about `git merge`, which is different from having lost track
        of a PR merge it was asked to judge.
        """
        result = run_hook(
            make_payload("gh pr merge --squash --delete-branch", cwd="/tmp"),
            tmp_path=tmp_path,
        )
        assert decision_of(result) == "ask"


    def test_mcp_without_owner_and_repo_abstains(self, tmp_path):
        """The MCP tool can send a PR number and name no repo at all.

        Closing a bypass shape found in review: a repo identity reintroduced on
        this path would be invisible to the command-line cases above, since no
        `--repo` selector and no command string are involved. The behavioural
        tests are what catch a reintroduced literal — the two source guards
        below only catch it spelled verbatim — so this path needs one of its
        own.
        """
        nowhere = tmp_path / "mcp-nowhere"
        nowhere.mkdir()
        payload = json.dumps({"cwd": str(nowhere), "tool_input": {"pullNumber": 861}})
        result = run_hook(
            payload,
            gh_responses={
                f"{OWN_REPO}/pulls/861/reviews": _TWO_REVIEWS,
                f"{OWN_REPO}/issues/861/labels": "[]",
            },
            tmp_path=tmp_path,
        )
        assert decision_of(result) == "ask"


class TestNoRepoIdentityLiteralSurvives:
    """Exit criterion 5: the decision logic names no repo of its own.

    A literal is what made the gate answer about the wrong PR while believing
    it had checked the right one. The gate stays in this repo, so nothing but a
    test stops a future edit from reintroducing the identity it just lost.

    These two catch the defect spelled verbatim, and only that. A red-team pass
    on the decision PR built a split-literal variant
    (``_proj = 'climate' + '-finance' + '-het'``) that passes both of them. The
    guard against the *class* is the behavioural suite above: that variant
    replaced the abstention fallback, and ``test_cwd_outside_any_repo_abstains``
    and ``test_non_github_remote_abstains`` both went red on it. Read these two
    as a readability ratchet — a literal is easy to see and easy to grep — and
    the behavioural tests as the guard that actually holds.
    """

    REPO_NAME_LITERALS = ("climate-finance-het", "oeconomia-climate-finance")

    def _code_lines(self) -> list[str]:
        """Script lines with comments and blanks removed."""
        out = []
        for line in HOOK_SCRIPT.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            out.append(line)
        return out

    def test_no_repo_identity_assignment(self):
        """No `OWNER=`/`REPO=` literal at the top of the script."""
        offenders = [
            ln
            for ln in self._code_lines()
            if re.match(r'^\s*(OWNER|REPO)=["\']?[A-Za-z0-9_.-]+["\']?\s*$', ln)
        ]
        assert not offenders, (
            f"repo identity is hardcoded again: {offenders}. The gate must "
            "resolve the repo from the command it is judging."
        )

    def test_no_repo_name_in_executable_code(self):
        """This project's slug appears in prose only, never in the logic."""
        offenders = [
            ln
            for ln in self._code_lines()
            if any(lit in ln for lit in self.REPO_NAME_LITERALS)
        ]
        assert not offenders, (
            f"a repo name literal is back in the decision logic: {offenders}"
        )
