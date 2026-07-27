"""Ticket 0343 — the project `.env` carries no secret literal.

A secret written as a literal in `.env` is exported into *every* process the
session spawns, including test subprocesses that dump their environment on
failure. That is how two live credentials leaked on 2026-07-27. The fix is not
better scrubbing: it is not having the value in the environment of processes
that do not need it.

Secrets live in `~/.config/keys/<provider>.env` and are selected per project by
the `KEYS=` line that `~/.claude/scripts/bash-env.sh` reads. `.env` therefore
holds only non-secret settings plus that one selection line.

What this buys is narrower than it looks, and worth stating exactly: a selected
credential still reaches every bash subprocess, because the loader runs on each
one. What changes is that the repository directory holds no credential at rest,
and that the selection is default-deny — an unlisted provider is never loaded,
so a sibling project's keys no longer arrive in this project's environment. The
selection forms this project uses (`provider:VAR`, `provider:SRC=DST`) export
one named variable each; a bare `provider` entry would source the whole provider
file instead, which is why the KEYS= line here names every variable explicitly.

**These tests never print a value they reject — variable NAME only.** A guard
that echoes the credential it found reproduces the defect it exists to prevent.

They skip (never fail) when `.env` is absent, so a fresh clone reports no false
defect.
"""

import os
import re
import subprocess

import pytest

# Mechanical adherence gate (`make lint` / `pytest -m adherence`).
pytestmark = pytest.mark.adherence

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

# Names allowed to carry a literal value in `.env`: deployment settings and the
# agent's public identity. Default-deny — a name absent from this set fails, so
# adding one is a deliberate decision, not a silent drift. A new *credential*
# belongs in the keystore and never on this list.
NON_SECRET_NAMES = frozenset(
    {
        "CLIMATE_FINANCE_DATA",  # data root path (see .claude/rules/architecture.md)
        "AGENT_GIT_NAME",  # public committer name
        "AGENT_GIT_EMAIL",  # public committer email
    }
)

# The keystore selection line. Its value is a provider/variable list, not a secret.
KEYS_NAME = "KEYS"

# Credentials that must resolve for work started in this repo. Each must be
# selected by `KEYS=` under the plain name its consumer reads from `os.environ`,
# so deleting an entry (and silently breaking auth) fails here rather than at the
# next API call.
#
# "Consumer" is wider than "code in this tree", because the loader's precedence
# makes it so: bash-env.sh exports every project-`.env` key verbatim, `KEYS`
# included, so a project `KEYS=` line *replaces* the harness one rather than
# adding to it. Whatever runs with this directory as its startup cwd therefore
# gets this line and only this line. Measured, not assumed: from a directory
# whose `.env` selects only `openalex`, `HAL_ID` is unset even though
# `~/.claude/.env` selects `hal` (ticket 0364).
REQUIRED_KEYS_EXPORTS = frozenset(
    {
        "AGENT_GH_TOKEN",  # .claude/hooks/check-reviews.sh, .agent/runbooks/on-start.md
        "OPENALEX_API_KEY",  # scripts/pipeline_io.py and the harvest/enrich scripts
        "S2_API_KEY",  # scripts/harvest/catalog_semanticscholar.py
        "OPENROUTER_API_KEY",  # scripts/filter_flags_llm.py (via litellm)
        # No code here reads these two: the harness `update-publist` skill does,
        # and a deposit run launched from this repo root inherits this selection.
        "HAL_ID",  # HAL SWORD deposit (harness skill update-publist)
        "HAL_PASSWORD",  # idem
    }
)

# High-precision credential markers. A value carrying one of these is a token
# whatever the variable is called.
CREDENTIAL_PREFIXES = (
    "sk-",  # OpenAI, OpenRouter (sk-or-...), Anthropic (sk-ant-...)
    "ghp_",  # GitHub personal access token (classic)
    "gho_",  # GitHub OAuth token
    "github_pat_",  # GitHub fine-grained PAT
    "hf_",  # Hugging Face
    "AKIA",  # AWS access key id
    "xox",  # Slack
)

# Shape heuristic, applied per TOKEN rather than to the whole value.
#
# The first version tested the value as a whole and exempted anything containing
# a path separator or a space. Review broke it in one line: a token pasted into
# a path (`/data/AKIA…`) or appended to the KEYS= list slipped past every check.
# Splitting on separators removes the hiding places — a credential embedded in a
# longer string is still a credential.
#
# Opaque means: a long run of letters and digits with no word separator inside.
# Real keys look like that (`ghp_` + 36 alnum, a 40-hex S2 key, `sk-or-v1-` + 64
# hex). Path and identifier segments that long are almost always broken up by
# `_`, `-` or `.`, which is what keeps CLIMATE_FINANCE_DATA and the KEYS= line
# itself from tripping the check.
TOKEN_SPLIT = re.compile(r"[/\\:;,=\s\"']+")
OPAQUE_MIN_LENGTH = 24
OPAQUE_TOKEN = re.compile(r"\A(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*\d)[A-Za-z0-9]+\Z")


def _parse_env(path: str) -> list[tuple[int, str, str]]:
    """Parse `.env` the way bash-env.sh does: strict KEY=VALUE, values literal.

    Returns (line number, name, value) triples. Mirroring the loader matters —
    a guard that parsed more loosely than the loader would flag lines the loader
    ignores, and one that parsed more strictly would miss lines it exports.
    """
    entries: list[tuple[int, str, str]] = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.rstrip("\n").rstrip("\r").lstrip()
            if not line or line.startswith("#"):
                continue
            line = line[len("export ") :] if line.startswith("export ") else line
            if "=" not in line:
                continue
            name, value = line.split("=", 1)
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                continue
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            entries.append((lineno, name, value))
    return entries


def _env_entries() -> list[tuple[int, str, str]]:
    if not os.path.exists(ENV_PATH):
        pytest.skip(".env absent (fresh clone or clean-room checkout)")
    return _parse_env(ENV_PATH)


def test_env_assignments_are_allowlisted_or_keys() -> None:
    """Every `.env` assignment is a known non-secret setting or the KEYS line."""
    unexpected = sorted(
        {
            f".env:{lineno} {name}"
            for lineno, name, _ in _env_entries()
            if name not in NON_SECRET_NAMES and name != KEYS_NAME
        }
    )
    assert not unexpected, (
        "`.env` assigns names outside the non-secret allowlist (names only, "
        "values deliberately not shown): "
        + ", ".join(unexpected)
        + ". Move each credential to ~/.config/keys/<provider>.env and select it "
        "via the KEYS= line; add a genuinely non-secret setting to "
        "NON_SECRET_NAMES in this file."
    )


def _credential_shaped_reason(value: str) -> str | None:
    """Why `value` looks like it carries a credential, or None if it does not."""
    for token in TOKEN_SPLIT.split(value):
        if not token:
            continue
        if token.startswith(CREDENTIAL_PREFIXES):
            return "known credential prefix"
        if len(token) >= OPAQUE_MIN_LENGTH and OPAQUE_TOKEN.match(token):
            return "long opaque token"
    return None


def test_env_values_do_not_look_like_credentials() -> None:
    """No `.env` value carries a credential-shaped token, whatever its name.

    The KEYS= line is scanned like every other value. It is the one place a
    secret could be appended and still look like configuration, so exempting it
    (as the first version did) left the widest hole in the whole guard.
    """
    suspicious: list[str] = []
    for lineno, name, value in _env_entries():
        reason = _credential_shaped_reason(value)
        if reason:
            suspicious.append(f".env:{lineno} {name} ({reason})")
    assert not suspicious, (
        "`.env` holds values shaped like credentials (names only, values "
        "deliberately not shown): " + ", ".join(sorted(suspicious))
    )


# Synthetic samples in the real formats. Never a live credential — the point is
# to prove the heuristic bites, which a guard tested only against a clean .env
# cannot show.
CREDENTIAL_SAMPLES = (
    "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8",
    "github_pat_" + "11ABCDEFG0" + "a1b2c3d4e5" * 3,
    "sk-or-v1-" + "0123456789abcdef" * 4,
    "sk-ant-api03-" + "Zz9Yy8Xx7Ww6Vv5Uu4Tt3Ss2Rr1Qq0",
    "AKIA" + "IOSFODNN7EXAMPLE",
    "hf_" + "aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789",
    "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",  # bare 40-hex, no prefix
)


def test_shape_heuristic_catches_credentials_in_every_hiding_place() -> None:
    """Each sample is caught bare, buried in a path, and appended to KEYS=."""
    escaped: list[str] = []
    for sample in CREDENTIAL_SAMPLES:
        contexts = {
            "bare": sample,
            "inside a path": f"/home/user/data/{sample}/corpus",
            "appended to KEYS=": f"openrouter:OPENROUTER_API_KEY,github:{sample}",
            "quoted with spaces": f"prefix {sample} suffix",
        }
        for label, value in contexts.items():
            if _credential_shaped_reason(value) is None:
                escaped.append(f"{sample[:6]}… {label}")
    assert not escaped, "credential-shaped tokens the heuristic missed: " + ", ".join(
        escaped
    )


def test_shape_heuristic_accepts_the_real_non_secret_settings() -> None:
    """The live `.env` non-secret values must not trip the heuristic.

    Guards the other failure direction: a check that flags everything is as
    useless as one that flags nothing, and would push the next person to weaken
    it rather than fix a real finding.
    """
    benign = (
        "data",
        "/home/haduong/Climate_finance/data",
        "HDMX-coding-agent",
        "HDMX-coding-agent@users.noreply.github.com",
        "openrouter:OPENROUTER_API_KEY_CLIMATEFINANCE=OPENROUTER_API_KEY,"
        "github:AGENT_GH_TOKEN,openalex:OPENALEX_API_KEY,"
        "semanticscholar:S2_API_KEY,hal:HAL_ID,hal:HAL_PASSWORD",
    )
    flagged = [v for v in benign if _credential_shaped_reason(v) is not None]
    assert not flagged, f"heuristic false-positives on benign settings: {flagged}"


def test_keys_line_selects_every_consumed_credential() -> None:
    """`KEYS=` exports each credential this project's code reads from the env."""
    entries = _env_entries()
    keys_values = [value for _, name, value in entries if name == KEYS_NAME]
    assert keys_values, (
        "`.env` has no KEYS= line, so no credential resolves from the keystore. "
        "Expected exports: " + ", ".join(sorted(REQUIRED_KEYS_EXPORTS))
    )

    exported: set[str] = set()
    for value in keys_values:
        for entry in value.split(","):
            entry = entry.strip()
            if ":" not in entry:
                continue  # bare `provider` — sources the file, exports no fixed name
            selector = entry.split(":", 1)[1]
            # `SRC=DST` renames on export; `VAR` exports under its own name.
            exported.add(selector.split("=", 1)[1] if "=" in selector else selector)

    missing = sorted(REQUIRED_KEYS_EXPORTS - exported)
    assert not missing, (
        "KEYS= does not select these credentials, so consuming code will not "
        "resolve them: " + ", ".join(missing)
    )


# --- ratchets: keep prose and build wiring honest about the mechanism --------
#
# Both defects below were caught by review on this ticket's own branch, not by a
# test. They are lexically stable, so a grep holds them permanently.

# Claims that .env supplies credentials. Each was true before ticket 0343.
STALE_ENV_CLAIMS = (
    "find their API keys",
    "access to data paths and API keys",
    "secrets like API keys live here",
    "secrets sourced from project .env",
    "Load .env for GH_TOKEN",
    "not exported into every process",  # the overclaim in the other direction
    # Two phrasings of "this skill reads its credentials from .env" (ticket 0364).
    # The project fork of update-publist carried the first and was deleted; the
    # harness copy that supersedes it carries the second. Pasting either sentence
    # into this repo trips the guard instead of restoring the claim.
    #
    # The second is anchored on the credential name rather than cut at "from the
    # project `.env`": .env legitimately supplies non-secret settings, so the
    # shorter form would eventually fire on a true sentence about, say,
    # CLIMATE_FINANCE_DATA. A guard that cries wolf on correct prose gets edited
    # out, and then it guards nothing. The cost of the anchor is that a partial
    # paste slips through — accepted, since the whole-sentence paste is the way
    # this defect actually travels.
    "Credentials from `.env`",
    "HAL_PASSWORD` from the project `.env`",
)

# Files the stale-claim scan covers: every tracked text file, discovered rather
# than listed. A hardcoded list was the first design and it failed immediately —
# it missed the identical stale claim in dvc.yaml, on the very branch that added
# the guard. Auto-discovery is the standing rule here for exactly this reason
# (memory: feedback_autodiscovery_class_guard).
#
# `git ls-files` sees only tracked files, so .venv and other gitignored trees
# never enter. Only tickets/ needs excluding: a closed ticket legitimately
# records the old mechanism as history, and rewriting history to satisfy a
# guard would be the wrong direction.
SCAN_EXTENSIONS = (".md", ".qmd", ".py", ".sh", ".yaml", ".yml", ".mk", ".toml")
SCAN_EXTRA_NAMES = ("Makefile", "dvc.yaml")
SCAN_EXCLUDED_PREFIXES = ("tickets/",)


def _tracked_text_files() -> list[str]:
    """Every tracked file whose text could describe the credential mechanism."""
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    paths = [p for p in out.stdout.split("\0") if p]
    return [
        p
        for p in paths
        if not p.startswith(SCAN_EXCLUDED_PREFIXES)
        and (p.endswith(SCAN_EXTENSIONS) or os.path.basename(p) in SCAN_EXTRA_NAMES)
    ]


def test_no_doc_claims_env_supplies_credentials() -> None:
    """No tracked file still says `.env` holds the API keys."""
    stale: list[str] = []
    for rel in _tracked_text_files():
        path = os.path.join(PROJECT_ROOT, rel)
        if not os.path.exists(path):
            continue  # tracked but deleted in the working tree
        if os.path.abspath(path) == os.path.abspath(__file__):
            continue  # this file lists the phrases in order to search for them
        with open(path, encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, start=1):
                for claim in STALE_ENV_CLAIMS:
                    if claim in line:
                        stale.append(f"{rel}:{lineno} ({claim!r})")
    assert not stale, (
        "These lines describe the pre-0343 mechanism, in which `.env` carried "
        "the credentials: " + ", ".join(stale)
    )


def test_makefile_wires_the_keystore_loader() -> None:
    """The build resolves credentials for the author's shell, not just the agent's.

    `uv run --env-file .env` stopped supplying credentials the moment they left
    `.env`. Recipes get them from the keystore loader, which bash reads via
    BASH_ENV — and only when SHELL is bash, since BASH_ENV is a bash mechanism.
    Losing either half silently breaks `make corpus` in a plain terminal while
    leaving the agent's own path (where BASH_ENV is already set) working, so the
    breakage would not show up in an agent-run build.
    """
    with open(os.path.join(PROJECT_ROOT, "Makefile"), encoding="utf-8") as fh:
        makefile = fh.read()

    assert re.search(r"^export BASH_ENV\s*:?=", makefile, re.MULTILINE), (
        "Makefile does not export BASH_ENV, so recipes never load the keystore "
        "and every credential is absent in a shell that has not loaded it."
    )
    assert re.search(r"^SHELL\s*:?=.*bash", makefile, re.MULTILINE), (
        "Makefile does not set SHELL to bash, so BASH_ENV is ignored and the "
        "keystore loader never runs."
    )
