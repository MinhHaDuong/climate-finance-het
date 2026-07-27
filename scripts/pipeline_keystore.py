"""Apply the `KEYS=` credential selection from `.env` (ticket 0343).

`.env` holds no secret. It carries a `KEYS=` line naming which credentials this
project may load; the values live in `~/.config/keys/<provider>.env`, outside
the repository. A bash loader applies that selection for shell entry points, but
it only covers processes started from bash with `BASH_ENV` set. `dvc repro`
picks its stage shell from `$SHELL` or `/bin/sh` and never sees it, and neither
does a bare `uv run python scripts/…`. Those paths would run unauthenticated —
silently, since every consumer treats a missing key as "use the free tier".

Resolving here instead puts the selection at the one place every entry point
already passes through: `pipeline_loaders` imports this, and every script
imports `pipeline_loaders`.

Two rules keep this composable with the bash loader rather than fighting it:

* An existing environment variable is never overwritten. Whoever set it first —
  the bash loader, a command-line prefix, a CI secret — wins.
* A missing provider file or an unreadable keystore is not fatal. A machine
  without the keystore (a reviewer's checkout, a container, the reproducibility
  archive) still runs; scripts then report the missing key themselves.

Nothing here logs a credential value. Log lines name variables, never contents.
"""

import logging
import os
import re

_log = logging.getLogger("pipeline.keystore")

DEFAULT_KEYS_DIR = os.path.join(os.path.expanduser("~"), ".config", "keys")

# Provider names index a file path, so they are validated before use: lowercase,
# digits and dashes only. This is what stops `KEYS=../../etc/shadow` from
# resolving anywhere outside the keystore directory.
_PROVIDER_RE = re.compile(r"\A[a-z0-9-]+\Z")
_IDENTIFIER_RE = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*\Z")

# Names an untrusted project `.env` must never bind, because the value would be
# interpreted rather than merely read: interpreter and loader search paths, and
# the shell's own execution hooks. Mirrors the bash loader's refusal list; kept
# short deliberately, since this resolver only ever sets os.environ for the
# current Python process.
_PROTECTED_NAMES = frozenset(
    {
        "PATH",
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONSTARTUP",
        "LD_PRELOAD",
        "LD_LIBRARY_PATH",
        "LD_AUDIT",
        "GCONV_PATH",
        "BASH_ENV",
        "ENV",
        "IFS",
        "NODE_OPTIONS",
        "PERL5LIB",
        "RUBYOPT",
    }
)


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_env_file(path: str) -> dict[str, str]:
    """Read a KEY=VALUE file into a dict, values taken literally.

    Deliberately not `dotenv`: these files are read for their values only, and
    no expansion, interpolation, or command substitution should ever apply to a
    credential.
    """
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


def _parse_selector(selector: str) -> tuple[str, str] | None:
    """`SRC=DST` renames on export; `VAR` exports under its own name."""
    if "=" in selector:
        src, dst = selector.split("=", 1)
    else:
        src = dst = selector
    if not _IDENTIFIER_RE.match(src) or not _IDENTIFIER_RE.match(dst):
        return None
    return src, dst


def apply_keys_selection(
    keys_line: str | None = None, keys_dir: str | None = None
) -> list[str]:
    """Export the credentials named by `KEYS=`. Returns the names newly set.

    `keys_line` defaults to `$KEYS`, which `load_dotenv` has already read from
    `.env` by the time `pipeline_loaders` calls this.
    """
    line = keys_line if keys_line is not None else os.environ.get("KEYS", "")
    if not line:
        return []
    directory = keys_dir or os.environ.get("CLIMATE_FINANCE_KEYS_DIR") or DEFAULT_KEYS_DIR

    applied: list[str] = []
    for raw_entry in line.split(","):
        entry = raw_entry.strip()
        if not entry:
            continue
        provider, _, selector = entry.partition(":")
        if not _PROVIDER_RE.match(provider):
            _log.warning("ignoring invalid KEYS provider: %r", provider)
            continue

        stored = parse_env_file(os.path.join(directory, f"{provider}.env"))
        if not stored:
            _log.debug("keystore provider %s unavailable or empty", provider)
            continue

        if not selector:
            # Bare `provider`: take the whole file, as the bash loader does.
            wanted = [(name, name) for name in stored]
        else:
            parsed = _parse_selector(selector)
            if parsed is None:
                _log.warning("ignoring invalid KEYS entry for provider %s", provider)
                continue
            wanted = [parsed]

        for src, dst in wanted:
            if dst in _PROTECTED_NAMES:
                _log.warning("refusing KEYS export to protected name: %s", dst)
                continue
            if src not in stored:
                _log.warning("KEYS var not found: %s:%s", provider, src)
                continue
            if os.environ.get(dst):
                continue  # already resolved upstream; first setter wins
            os.environ[dst] = stored[src]
            applied.append(dst)

    if applied:
        _log.debug("resolved %d credential(s) from the keystore", len(applied))
    return applied
