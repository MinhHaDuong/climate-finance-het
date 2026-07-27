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

# Credentials this project consumes. Each must be selected by `KEYS=` under the
# plain name its consuming code reads from `os.environ`, so deleting an entry
# (and silently breaking auth) fails here rather than at the next API call.
REQUIRED_KEYS_EXPORTS = frozenset(
    {
        "AGENT_GH_TOKEN",  # .claude/hooks/check-reviews.sh, .agent/runbooks/on-start.md
        "OPENALEX_API_KEY",  # scripts/pipeline_io.py and the harvest/enrich scripts
        "S2_API_KEY",  # scripts/harvest/catalog_semanticscholar.py
        "OPENROUTER_API_KEY",  # scripts/filter_flags_llm.py (via litellm)
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

# Shape heuristic: a long unbroken opaque string. Paths and URLs are the common
# benign case, so a value containing a separator is exempt (CLIMATE_FINANCE_DATA
# is a filesystem path well over the length bound).
OPAQUE_MIN_LENGTH = 20
PATHISH = ("/", "\\", "@", " ", "\t")


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


def test_env_values_do_not_look_like_credentials() -> None:
    """No `.env` value has the shape of a credential, whatever its name."""
    suspicious: list[str] = []
    for lineno, name, value in _env_entries():
        if name == KEYS_NAME:
            continue  # a provider/variable selection list, not a secret
        if value.startswith(CREDENTIAL_PREFIXES):
            suspicious.append(f".env:{lineno} {name} (known credential prefix)")
        elif len(value) > OPAQUE_MIN_LENGTH and not any(c in value for c in PATHISH):
            suspicious.append(f".env:{lineno} {name} (long opaque value)")
    assert not suspicious, (
        "`.env` holds values shaped like credentials (names only, values "
        "deliberately not shown): " + ", ".join(sorted(suspicious))
    )


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
    "not exported into every process",  # the overclaim in the other direction
)

# Docs and deliverables that describe the credential mechanism. Kept explicit:
# a repo-wide walk would sweep .venv and the ticket archive, where these strings
# legitimately appear as history.
MECHANISM_DOCS = (
    "docs/data-management-plan.md",
    "docs/roadmap-datapaper.md",
    "deliverables/_shared/_includes/agentic-workflow.md",
    "deliverables/agentic/agentic-paper.qmd",
    "scripts/pipeline_loaders.py",
    "scripts/run_corpus_pipeline.sh",
    "Makefile",
    ".claude/rules/git.md",
    ".agent/runbooks/on-start.md",
)


def test_no_doc_claims_env_supplies_credentials() -> None:
    """No tracked doc still says `.env` holds the API keys."""
    stale: list[str] = []
    for rel in MECHANISM_DOCS:
        path = os.path.join(PROJECT_ROOT, rel)
        if not os.path.exists(path):
            continue
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
