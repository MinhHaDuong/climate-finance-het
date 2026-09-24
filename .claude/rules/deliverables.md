---
paths:
  - "deliverables/**"
  - "paths.mk"
  - "**/*.qmd"
  - "**/_quarto.yml"
  - "scripts/analysis/_vars_registry.py"
  - "scripts/analysis/compute_vars.py"
  - "config/unrendered-artifacts.txt"
  - "tests/_qmd_meta.py"
  - "tests/test_deliverable_artifacts.py"
  - "tests/test_doc_vars_completeness.py"
---

# Architecture — deliverables layout

Split from `architecture.md` (pipeline phases, Phase-2 rules, artifact homes); siblings: `deliverables.md`, `data-location.md`, `openalex-corpus.md`, `null-model.md`.

## Project structure

Each deliverable is its own Quarto project under `deliverables/<x>/` with its own
`_quarto.yml`, so `quarto render deliverables/<x>` selects it directly — no
exclusion-mask profile files (ticket 0226). Quarto's single-file render writes
the PDF/DOCX **next to the source** (`deliverables/<x>/<doc>.pdf`), so the Make
render target equals the output file and Make verifies it; the top-level
`output/` directory was retired. Shared assets (bibliography, `_includes/`,
generated `figures/` and `tables/`, `technical-report-vars.yml`) live in
`deliverables/_shared/` and are referenced by `../_shared/...` from each doc;
includes resolve relative to the top rendering doc, and every deliverable folder
sits one level under `deliverables/`, so the prefix is uniform.

**Consequence for anything that walks this graph.** A nested include's path is
resolved against the *root document's* directory, not against the file that
contains it — so a resolver must carry the root's directory as base through
every level of recursion. Joining each include against its own directory is the
natural implementation and it is wrong: it misses every nested include and
reports it as unreachable. A 2026-07-27 orphan sweep written that way returned
13 confident false positives, all of `_includes/zoo/*.md`, which
`_includes/techrep-zoo.md` reaches as `../_shared/_includes/zoo/…` from the zoo
deliverable's folder. Knowing the rule above did not prevent it, so it is
written here as the consequence rather than left to be re-derived (ticket 0359,
whose reachability guard depends on getting this right).

**`DOC_VARS` is the per-document variable contract, and `DOC_VARS_FILE` says
which metadata file each document loads.** Both live in
`scripts/analysis/_vars_registry.py` and are re-exported by `compute_vars`, so
`from compute_vars import DOC_VARS` still resolves but the file to edit is the
registry. Four documents
share `_shared/technical-report-vars.yml`, so that file is written with the
union of their declared keys. The registry states the sharing rather than
leaving the render to discover it, because an unregistered document does not
fail: Quarto resolves whatever the shared file happens to carry, writes
`?meta:key` for the rest, and exits 0. corpus-report sat outside the registry
that way and rendered 12 placeholders. `tests/test_doc_vars_completeness.py`
now discovers documents from disk, so the next unregistered one fails instead
of being skipped; a document whose vars file is hand-maintained goes in that
test's `PINNED_DOCS` (ticket 0357).

**`paths.mk` is the per-deliverable artifact contract.** Each document owns a
`*_INCLUDES` list (the shared files it composes) and a `*_FIGS` list (the
figures it embeds); its render rule takes both as prerequisites. Both answer
"which artifacts does this deliverable need?", and both drift silently — a
prose cut orphans a figure, a rewrite drops includes the list keeps. Two
markers carry the deliberate exceptions: a `# not-embedded: <file> — <reason>`
comment in `paths.mk` for a figure built on purpose and embedded nowhere, and
`config/unrendered-artifacts.txt` for a shared include or table no document
composes. `tests/test_deliverable_artifacts.py` diffs every list against the
real include closure in both directions and rejects a stale marker, so an
allowlist entry cannot rot into a mute skip (ticket 0359).

The 11 documents across 9 folders:

- `deliverables/manuscript/` — `manuscript.qmd` (main Œconomia article) +
  `manuscript-Gide.qmd` (Charles Gide conference variant); `manuscript-vars.yml`
  (pinned) and `manuscript.mk` (Phase-3 clean-room render) live here.
- `deliverables/corpus-report/corpus-report.qmd` — corpus construction, data quality, contents
- `deliverables/technical-report/technical-report.qmd` — analysis methods and results (composed of includes)
- `deliverables/data-paper/data-paper.qmd` — corpus data paper (RDJ4HSS submission)
- `deliverables/multilayer/` — `multilayer-detection.qmd` + `multilayer-detection-techrep.qmd`
- `deliverables/agentic/agentic-paper.qmd` — the agentic-workflow paper
- `deliverables/zoo/breakpoint-detect-method-zoo.qmd` — the breakpoint-detection method zoo
- `deliverables/slides-gide/`, `deliverables/slides-eshet/` — conference slide decks (deliverables, not papers)

(The former `companion-paper.qmd` no longer exists; the method paper is now the
`multilayer/` pair.)
