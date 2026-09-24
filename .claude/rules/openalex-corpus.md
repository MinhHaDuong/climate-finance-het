---
paths:
  - "libs/**"
  - "scripts/utils.py"
  - "scripts/pipeline_io.py"
  - "scripts/harvest/enrich_embeddings.py"
  - "pyproject.toml"
  - "tests/_source_roots.py"
  - "tests/test_openalex_corpus_equivalence.py"
  - "tests/test_shim_resolution.py"
  - "build/**"
  - "data/het/**"
---

# Architecture — shared conventions package

Split from `architecture.md` (pipeline phases, Phase-2 rules, artifact homes); siblings: `deliverables.md`, `data-location.md`, `openalex-corpus.md`, `null-model.md`.

## Shared conventions package (`libs/openalex-corpus`)

The model-agnostic OpenAlex conventions — `retry_get` (polite HTTP with
backoff, `mailto` injected by the caller), `reconstruct_abstract`,
`normalize_doi`, `build_text`, `is_boilerplate_abstract` — live in a standalone
path package `libs/openalex-corpus`, this repo's source of truth for them
(ticket 0170). It ships no deployment config (`MAILTO`/API keys are injected as
parameters) and no embedding model choice.

This repo **imports the package as source** via the relative source root
`libs/openalex-corpus/src` on `PYTHONPATH` (ticket 0253). The single rule:
**the source roots (`scripts` + `libs/openalex-corpus/src`) are placed on the
path in every execution context — pytest (`pythonpath`), make (`export`), test
subprocesses (explicit env via `tests/_source_roots.py`), containers (Dockerfile
`ENV`), and archive scripts/Makefiles — never assumed ambient.** Concretely:
pytest gets them from `[tool.pytest.ini_options] pythonpath`, every Make/`.mk`
invocation from the top-level `export PYTHONPATH`, each test that launches a
script subprocess from `source_root_env()`, and the reproducibility archives
carry both the bundled `libs/openalex-corpus/` and the `PYTHONPATH` env/export.
The former non-editable `[tool.uv.sources]` wheel
install is retired; `libs/openalex-corpus/pyproject.toml` is kept so git-source
consumers (AEDIST, ticket 0229) still depend on it. Call sites import
`normalize_doi`, `reconstruct_abstract`, `build_text`, `is_boilerplate_abstract`
from `openalex_corpus.*` directly (the `utils` facade re-exposes the first two
from the package, unchanged for `from utils import …`). Two project-owned
adapters remain and are **not** pure pass-throughs: `pipeline_io.retry_get`
injects this repo's `MAILTO` and User-Agent, and `enrich_embeddings` re-exports
`build_text` / `is_boilerplate_abstract` where its own pipeline uses them.
Behavioural parity is pinned by `tests/test_openalex_corpus_equivalence.py`;
symbol resolution by `tests/test_shim_resolution.py`.

The package has no external consumers today. It was extracted so a sibling
paper's pipeline could share these conventions rather than reach into this
repo's `scripts/`; the concrete case — the embedding-based citation-overlap
figure for "Un théorème, sept costumes" (`polycentric_activity`) — was retired
when that paper moved to its own embedding-free swim-lane figure, and its
`het_*.py` scripts were deleted here (ticket 0170, Move B). A future sibling
repo would consume the package by git source. `data/het/seeds.csv` is kept:
`polycentric_activity`'s `conception/het_indirect_citations.py` still reads it
by path.
