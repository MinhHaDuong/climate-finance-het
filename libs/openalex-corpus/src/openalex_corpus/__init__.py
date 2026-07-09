"""openalex-corpus — shared OpenAlex crawl + canonical-text conventions.

Model-agnostic conventions reused across papers that build corpora from
OpenAlex. This repo (climate-finance-het) is the source of truth; other
repos (e.g. polycentric_activity) depend on it as a git source. The engine
repo's own ``scripts/`` modules re-export these to preserve their public API.

Scope note: this package holds *conventions* only. Deployment config
(``MAILTO``, API keys) is injected by the caller, never shipped here. The
HTTP layer (``retry_get``) is a separate follow-up slice (ticket 0170, A2).
"""

from openalex_corpus.embedding import build_text, is_boilerplate_abstract
from openalex_corpus.text import normalize_doi, reconstruct_abstract

__all__ = [
    "build_text",
    "is_boilerplate_abstract",
    "normalize_doi",
    "reconstruct_abstract",
]
