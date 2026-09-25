"""Ticket 1477 — consumers read only their own machine credential."""

import os

import pytest
from pipeline_keystore import (
    credential_environment,
    parse_env_file,
    read_credential,
)

pytestmark = pytest.mark.wp_shared

@pytest.fixture
def keystore(tmp_path):
    """Synthetic provider files; no live credential is read by these tests."""
    (tmp_path / "github.env").write_text(
        "AGENT_GH_TOKEN_CLIMATEFINANCE=tok-project\n"
        "AGENT_GH_TOKEN_OTHER=tok-other\n",
        encoding="utf-8",
    )
    (tmp_path / "openrouter.env").write_text(
        '# comment\nexport OPENROUTER_API_KEY_CLIMATEFINANCE="tok-openrouter"\n'
        "OPENROUTER_API_KEY_OTHER=tok-other\n",
        encoding="utf-8",
    )
    return str(tmp_path)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in (
        "AGENT_GH_TOKEN_CLIMATEFINANCE",
        "AGENT_GH_TOKEN_OTHER",
        "OPENROUTER_API_KEY",
        "OPENROUTER_API_KEY_CLIMATEFINANCE",
        "OPENROUTER_API_KEY_OTHER",
    ):
        monkeypatch.delenv(name, raising=False)


def test_parser_takes_assignments_literally(keystore):
    values = parse_env_file(os.path.join(keystore, "openrouter.env"))
    assert values == {
        "OPENROUTER_API_KEY_CLIMATEFINANCE": "tok-openrouter",
        "OPENROUTER_API_KEY_OTHER": "tok-other",
    }


def test_consumer_reads_only_the_requested_value(keystore):
    value = read_credential(
        "github", "AGENT_GH_TOKEN_CLIMATEFINANCE", keys_dir=keystore
    )
    assert value == "tok-project"
    assert "AGENT_GH_TOKEN_OTHER" not in os.environ


def test_deliberately_supplied_value_wins(keystore, monkeypatch):
    monkeypatch.setenv("AGENT_GH_TOKEN_CLIMATEFINANCE", "supplied-by-caller")
    assert (
        read_credential(
            "github", "AGENT_GH_TOKEN_CLIMATEFINANCE", keys_dir=keystore
        )
        == "supplied-by-caller"
    )


def test_renamed_environment_value_exists_only_inside_context(keystore):
    with credential_environment(
        "openrouter",
        "OPENROUTER_API_KEY_CLIMATEFINANCE",
        "OPENROUTER_API_KEY",
        keys_dir=keystore,
    ):
        assert os.environ["OPENROUTER_API_KEY"] == "tok-openrouter"
        assert "OPENROUTER_API_KEY_OTHER" not in os.environ
    assert "OPENROUTER_API_KEY" not in os.environ


def test_context_preserves_existing_destination(keystore, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "supplied-by-caller")
    with credential_environment(
        "openrouter",
        "OPENROUTER_API_KEY_CLIMATEFINANCE",
        "OPENROUTER_API_KEY",
        keys_dir=keystore,
    ):
        assert os.environ["OPENROUTER_API_KEY"] == "supplied-by-caller"
    assert os.environ["OPENROUTER_API_KEY"] == "supplied-by-caller"


@pytest.mark.parametrize(
    ("provider", "source"),
    [
        ("../../../etc/passwd", "AGENT_GH_TOKEN_CLIMATEFINANCE"),
        ("Github", "AGENT_GH_TOKEN_CLIMATEFINANCE"),
        ("github", "not-an-identifier"),
        ("github", "MISSING_VAR"),
    ],
)
def test_invalid_or_missing_request_returns_empty(keystore, provider, source):
    assert read_credential(provider, source, keys_dir=keystore) == ""


def test_missing_provider_file_degrades_quietly(tmp_path):
    assert (
        read_credential(
            "github", "AGENT_GH_TOKEN_CLIMATEFINANCE", keys_dir=str(tmp_path)
        )
        == ""
    )


def test_overlapping_contexts_keep_the_value_until_the_last_exit(keystore):
    """Concurrent LLM calls share one process environment (syllabi_process
    runs llm_call in a 20-worker pool): the first caller to leave must not
    pop the key out from under a call still in flight."""
    first = credential_environment(
        "openrouter",
        "OPENROUTER_API_KEY_CLIMATEFINANCE",
        "OPENROUTER_API_KEY",
        keys_dir=keystore,
    )
    second = credential_environment(
        "openrouter",
        "OPENROUTER_API_KEY_CLIMATEFINANCE",
        "OPENROUTER_API_KEY",
        keys_dir=keystore,
    )
    first.__enter__()
    second.__enter__()
    first.__exit__(None, None, None)
    assert os.environ.get("OPENROUTER_API_KEY") == "tok-openrouter"
    second.__exit__(None, None, None)
    assert "OPENROUTER_API_KEY" not in os.environ
