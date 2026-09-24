"""Credential-policy adherence tests.

The project file contains machine paths and public Git identity only. Secrets
stay in the user keystore until the individual API consumer reads the one value
it needs. These tests report variable names and locations, never values.
"""

import os
import re
import subprocess

import pytest

pytestmark = pytest.mark.adherence

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

NON_SECRET_NAMES = frozenset(
    {
        "CLIMATE_FINANCE_DATA",
        "AGENT_GIT_NAME",
        "AGENT_GIT_EMAIL",
    }
)

AMBIENT_CREDENTIAL_NAMES = frozenset(
    {
        "AGENT_GH_TOKEN",
        "AGENT_GH_TOKEN_CLIMATEFINANCE",
        "GH_TOKEN",
        "OPENALEX_API_KEY",
        "OPENROUTER_API_KEY",
        "OPENROUTER_API_KEY_CLIMATEFINANCE",
        "S2_API_KEY",
        "HAL_ID",
        "HAL_PASSWORD",
        "ZENODO_TOKEN",
    }
)

# Assemble these spellings so the guard is governed by its own lexical rule.
RETIRED_CREDENTIAL_MARKERS = ("KEYS" + "=", "BASH" + "_ENV")

CREDENTIAL_PREFIXES = (
    "sk-",
    "ghp_",
    "gho_",
    "github_pat_",
    "hf_",
    "AKIA",
    "xox",
)
TOKEN_SPLIT = re.compile(r"[/\\:;,=\s\"']+")
OPAQUE_MIN_LENGTH = 24
OPAQUE_TOKEN = re.compile(r"\A(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*\d)[A-Za-z0-9]+\Z")


def _parse_env(path: str) -> list[tuple[int, str, str]]:
    """Parse simple assignments literally, without shell evaluation."""
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


def _credential_shaped_reason(value: str) -> str | None:
    for token in TOKEN_SPLIT.split(value):
        if not token:
            continue
        if token.startswith(CREDENTIAL_PREFIXES):
            return "known credential prefix"
        if len(token) >= OPAQUE_MIN_LENGTH and OPAQUE_TOKEN.match(token):
            return "long opaque token"
    return None


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [path for path in result.stdout.split("\0") if path]


def test_env_assignments_are_non_secret_settings() -> None:
    unexpected = sorted(
        f".env:{lineno} {name}"
        for lineno, name, _ in _env_entries()
        if name not in NON_SECRET_NAMES
    )
    assert not unexpected, (
        ".env assigns names outside the non-secret allowlist (names only): "
        + ", ".join(unexpected)
    )


def test_env_values_do_not_look_like_credentials() -> None:
    suspicious = sorted(
        f".env:{lineno} {name} ({reason})"
        for lineno, name, value in _env_entries()
        if (reason := _credential_shaped_reason(value))
    )
    assert not suspicious, (
        ".env holds values shaped like credentials (names only): "
        + ", ".join(suspicious)
    )


CREDENTIAL_SAMPLES = (
    "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8",
    "github_pat_" + "11ABCDEFG0" + "a1b2c3d4e5" * 3,
    "sk-or-v1-" + "0123456789abcdef" * 4,
    "sk-ant-api03-" + "Zz9Yy8Xx7Ww6Vv5Uu4Tt3Ss2Rr1Qq0",
    "AKIA" + "IOSFODNN7EXAMPLE",
    "hf_" + "aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789",
    "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
)


def test_shape_heuristic_catches_credentials_in_common_hiding_places() -> None:
    escaped: list[str] = []
    for sample in CREDENTIAL_SAMPLES:
        for label, value in {
            "bare": sample,
            "inside a path": f"/home/user/data/{sample}/corpus",
            "inside a list": f"provider:VARIABLE,github:{sample}",
            "quoted with spaces": f"prefix {sample} suffix",
        }.items():
            if _credential_shaped_reason(value) is None:
                escaped.append(f"{sample[:6]}… {label}")
    assert not escaped, "credential-shaped tokens the heuristic missed: " + ", ".join(
        escaped
    )


def test_shape_heuristic_accepts_real_non_secret_settings() -> None:
    benign = (
        "data",
        "/home/haduong/Climate_finance/data",
        "HDMX-coding-agent",
        "HDMX-coding-agent@users.noreply.github.com",
    )
    flagged = [value for value in benign if _credential_shaped_reason(value)]
    assert not flagged, f"heuristic false-positives on benign settings: {flagged}"


def test_live_files_do_not_name_the_retired_shell_loader() -> None:
    """Closed tickets are historical records; every live file follows now."""
    stale: list[str] = []
    candidates = [
        rel for rel in _tracked_files() if not rel.startswith("tickets/closed/")
    ]
    if os.path.exists(ENV_PATH):
        candidates.append(".env")
    for rel in candidates:
        path = os.path.join(PROJECT_ROOT, rel)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for lineno, line in enumerate(fh, start=1):
                    for marker in RETIRED_CREDENTIAL_MARKERS:
                        if marker in line:
                            stale.append(f"{rel}:{lineno} ({marker!r})")
        except OSError:
            continue
    assert not stale, "retired credential-loader references: " + ", ".join(stale)


def test_fresh_bash_exposes_no_credential_names() -> None:
    clean_env = {
        name: value
        for name, value in os.environ.items()
        if name not in AMBIENT_CREDENTIAL_NAMES and name != "BASH" + "_ENV"
    }
    result = subprocess.run(
        ["/bin/bash", "-c", "env"],
        cwd=PROJECT_ROOT,
        env=clean_env,
        capture_output=True,
        text=True,
        check=True,
    )
    visible = {line.partition("=")[0] for line in result.stdout.splitlines()}
    leaked = sorted(AMBIENT_CREDENTIAL_NAMES & visible)
    assert not leaked, "fresh bash exposed credential names: " + ", ".join(leaked)
