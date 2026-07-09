"""openalex-corpus — shared OpenAlex crawl + canonical-text conventions.

Model-agnostic conventions reused across papers that build corpora from
OpenAlex. This repo (climate-finance-het) is the source of truth; other
repos (e.g. polycentric_activity) depend on it as a git source. The engine
repo's own ``scripts/`` modules re-export these to preserve their public API.

Scope note: this package holds *conventions* only. Deployment config
(``MAILTO``, API keys) is injected by the caller, never shipped here.

Imports are lazy (PEP 562): pulling a pure-text symbol
(``normalize_doi``/``reconstruct_abstract``/``build_text``) does not load the
HTTP layer, so a text-only consumer never transitively imports ``requests``.
"""

import importlib

# symbol -> submodule that defines it
_LAZY = {
    "retry_get": "crawl",
    "RETRY_MAX_RETRIES": "crawl",
    "build_text": "embedding",
    "is_boilerplate_abstract": "embedding",
    "normalize_doi": "text",
    "reconstruct_abstract": "text",
}

__all__ = sorted(_LAZY)


def __getattr__(name: str):
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(f"{__name__}.{module}"), name)


def __dir__():
    return sorted(__all__)
