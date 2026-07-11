"""Shared source-root PYTHONPATH for test subprocesses (ticket 0253).

The repo places two relative source roots — ``scripts`` and
``libs/openalex-corpus/src`` — on the path in *every* execution context so flat
imports (``from utils import …``, ``import openalex_corpus``) resolve without an
ambient ``PYTHONPATH``. pytest itself gets them from
``[tool.pytest.ini_options] pythonpath``; this helper hands the SAME roots to any
subprocess a test launches (``python scripts/x.py``), which does not inherit the
parent's ``sys.path`` — only its environment. Absolute paths, so the child
resolves them regardless of its cwd, and independent of whether the (retired)
openalex-corpus wheel happens to be installed.
"""

import os

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Absolute source roots, in path-priority order.
SOURCE_ROOTS = [
    os.path.join(_REPO_ROOT, "scripts"),
    os.path.join(_REPO_ROOT, "libs", "openalex-corpus", "src"),
]


def source_root_pythonpath(existing: str | None = None) -> str:
    """Return a PYTHONPATH value with the source roots prepended to ``existing``."""
    parts = list(SOURCE_ROOTS)
    if existing:
        parts.append(existing)
    return os.pathsep.join(parts)


def source_root_env(base: dict[str, str] | None = None) -> dict[str, str]:
    """Return an environment dict with the source roots on ``PYTHONPATH``.

    ``base`` defaults to ``os.environ``; the caller's existing ``PYTHONPATH`` is
    preserved after the source roots.
    """
    env = dict(os.environ if base is None else base)
    env["PYTHONPATH"] = source_root_pythonpath(env.get("PYTHONPATH"))
    return env
