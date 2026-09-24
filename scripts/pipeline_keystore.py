"""Read one credential for one consumer from the machine keystore.

Credential files live outside the repository at
``~/.config/keys/<provider>.env``. A caller names the provider and source
variable it needs at the point of use; this module only parses that one file
and returns that one value. It never logs values and never exports a provider
file wholesale.

Most API clients accept a key as a parameter and should use
``read_credential``. Libraries that insist on reading an environment variable
can use ``credential_environment`` to expose it only for the duration of the
call and restore the process environment afterwards.
"""

import logging
import os
import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager

_log = logging.getLogger("pipeline.keystore")

DEFAULT_KEYS_DIR = os.path.join(os.path.expanduser("~"), ".config", "keys")

_PROVIDER_RE = re.compile(r"\A[a-z0-9-]+\Z")
_IDENTIFIER_RE = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*\Z")


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_env_file(path: str) -> dict[str, str]:
    """Read simple assignments literally, without shell evaluation."""
    values: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return values
    for raw in lines:
        line = raw.rstrip("\n").rstrip("\r").lstrip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if _IDENTIFIER_RE.match(name):
            values[name] = _strip_quotes(value)
    return values


def read_credential(
    provider: str,
    source: str,
    *,
    keys_dir: str | None = None,
) -> str:
    """Return one requested credential, or ``""`` when it is unavailable.

    A deliberately supplied process value wins. Otherwise only ``source`` is
    read from the named provider file; sibling variables never leave the
    parser's local dictionary.
    """
    if not _PROVIDER_RE.match(provider):
        _log.warning("ignoring invalid credential provider: %r", provider)
        return ""
    if not _IDENTIFIER_RE.match(source):
        _log.warning("ignoring invalid credential name: %r", source)
        return ""
    if os.environ.get(source):
        return os.environ[source]

    directory = (
        keys_dir or os.environ.get("CLIMATE_FINANCE_KEYS_DIR") or DEFAULT_KEYS_DIR
    )
    stored = parse_env_file(os.path.join(directory, f"{provider}.env"))
    if source not in stored:
        _log.debug("credential unavailable: %s:%s", provider, source)
        return ""
    return stored[source]


# Destinations this module has set, with the number of contexts relying on
# each. os.environ is process-global and LLM calls run in thread pools, so the
# first context to exit must not pop a value another call still uses.
_ENV_LOCK = threading.Lock()
_ENV_HOLDERS: dict[str, int] = {}


@contextmanager
def credential_environment(
    provider: str,
    source: str,
    destination: str,
    *,
    keys_dir: str | None = None,
) -> Iterator[None]:
    """Expose one credential under ``destination`` only inside the context.

    Overlapping contexts share the value: it is set by the first entrant and
    removed when the last one exits. A value the caller supplied before any
    context is never touched.
    """
    if not _IDENTIFIER_RE.match(destination):
        _log.warning("ignoring invalid credential destination: %r", destination)
        yield
        return

    with _ENV_LOCK:
        if destination in _ENV_HOLDERS:
            _ENV_HOLDERS[destination] += 1
            held = True
        elif os.environ.get(destination):
            held = False
        else:
            value = read_credential(provider, source, keys_dir=keys_dir)
            held = bool(value)
            if held:
                os.environ[destination] = value
                _ENV_HOLDERS[destination] = 1
    try:
        yield
    finally:
        if held:
            with _ENV_LOCK:
                _ENV_HOLDERS[destination] -= 1
                if not _ENV_HOLDERS[destination]:
                    del _ENV_HOLDERS[destination]
                    os.environ.pop(destination, None)
