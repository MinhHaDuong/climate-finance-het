"""Ticket 0343 — the KEYS= selection resolves for every entry point.

The bash loader only covers processes started from a bash that has BASH_ENV set.
`dvc repro` picks its stage shell from `$SHELL` or `/bin/sh`, and a bare
`uv run python scripts/…` gets no loader at all. `scripts/keystore.py` closes
that gap at the import every script already performs.

No test here reads a real credential: each builds its own keystore in a tmpdir.
"""

import os

import pytest
from pipeline_keystore import apply_keys_selection, parse_env_file


@pytest.fixture
def keystore(tmp_path):
    """A keystore directory with two providers, mirroring the real layout."""
    (tmp_path / "github.env").write_text(
        "AGENT_GH_TOKEN=tok-github\nAGENT_GIT_NAME=Someone\n", encoding="utf-8"
    )
    (tmp_path / "openrouter.env").write_text(
        '# comment\nexport OPENROUTER_API_KEY_PROJECT="tok-openrouter"\n'
        "OPENROUTER_API_KEY_OTHER=tok-other\n",
        encoding="utf-8",
    )
    return str(tmp_path)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in (
        "AGENT_GH_TOKEN",
        "AGENT_GIT_NAME",
        "OPENROUTER_API_KEY",
        "OPENROUTER_API_KEY_PROJECT",
        "OPENROUTER_API_KEY_OTHER",
        "KEYS",
    ):
        monkeypatch.delenv(name, raising=False)


def test_named_selection_exports_only_that_variable(keystore):
    applied = apply_keys_selection("github:AGENT_GH_TOKEN", keys_dir=keystore)
    assert applied == ["AGENT_GH_TOKEN"]
    assert os.environ["AGENT_GH_TOKEN"] == "tok-github"
    # The sibling in the same provider file must not ride along — that
    # narrowing is the whole point of the selection form.
    assert "AGENT_GIT_NAME" not in os.environ


def test_rename_form_exports_under_the_requested_name(keystore):
    apply_keys_selection(
        "openrouter:OPENROUTER_API_KEY_PROJECT=OPENROUTER_API_KEY", keys_dir=keystore
    )
    assert os.environ["OPENROUTER_API_KEY"] == "tok-openrouter"
    # The other project's key in the same file stays unexported. This is the
    # accident ticket 0343 records: an unsuffixed key from a sibling project
    # was reaching this one.
    assert "OPENROUTER_API_KEY_OTHER" not in os.environ


def test_bare_provider_takes_the_whole_file(keystore):
    applied = apply_keys_selection("github", keys_dir=keystore)
    assert sorted(applied) == ["AGENT_GH_TOKEN", "AGENT_GIT_NAME"]


def test_unlisted_provider_is_never_loaded(keystore):
    apply_keys_selection("github:AGENT_GH_TOKEN", keys_dir=keystore)
    assert "OPENROUTER_API_KEY_PROJECT" not in os.environ


def test_existing_value_is_not_overwritten(keystore, monkeypatch):
    """Whoever set it first wins, so this composes with the bash loader."""
    monkeypatch.setenv("AGENT_GH_TOKEN", "set-by-the-bash-loader")
    applied = apply_keys_selection("github:AGENT_GH_TOKEN", keys_dir=keystore)
    assert applied == []
    assert os.environ["AGENT_GH_TOKEN"] == "set-by-the-bash-loader"


@pytest.mark.parametrize(
    "entry",
    [
        "../../../etc/passwd:AGENT_GH_TOKEN",
        "Github:AGENT_GH_TOKEN",  # uppercase fails the provider pattern
        "github:not-an-identifier",
        "github:AGENT_GH_TOKEN=PATH",  # protected destination
        "github:MISSING_VAR",
    ],
)
def test_malformed_or_unsafe_entries_export_nothing(keystore, entry):
    assert apply_keys_selection(entry, keys_dir=keystore) == []


def test_absent_keystore_is_not_fatal(tmp_path):
    """A checkout without the keystore still runs; scripts report the gap."""
    missing = str(tmp_path / "nope")
    assert apply_keys_selection("github:AGENT_GH_TOKEN", keys_dir=missing) == []


def test_empty_keys_line_is_a_no_op(keystore):
    assert apply_keys_selection("", keys_dir=keystore) == []
    assert apply_keys_selection("   ,  ,", keys_dir=keystore) == []


def test_values_are_taken_literally(tmp_path):
    """No expansion, interpolation, or substitution touches a credential."""
    path = tmp_path / "p.env"
    path.write_text("K=$(echo pwned)\nL=${HOME}/x\n", encoding="utf-8")
    parsed = parse_env_file(str(path))
    assert parsed["K"] == "$(echo pwned)"
    assert parsed["L"] == "${HOME}/x"
