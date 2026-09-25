---
paths:
  - "data/**"
  - "dvc.yaml"
  - "dvc.lock"
  - "**/*.dvc"
  - ".dvc/**"
  - ".env"
  - ".githooks/post-checkout"
  - ".worktreeinclude"
  - "scripts/utils.py"
  - "scripts/pipeline_loaders.py"
  - "scripts/pipeline_io.py"
  - "scripts/harvest/**"
  - "tests/test_post_checkout_hook.py"
  - "tests/test_phase_layout.py"
---

# Architecture — data location

Split from `architecture.md` (pipeline phases, Phase-2 rules, artifact homes); siblings: `deliverables.md`, `data-location.md`, `openalex-corpus.md`, `null-model.md`.

## Data location

`DATA_DIR` defaults to `<repo>/data` and can be relocated onto another disk by
setting `CLIMATE_FINANCE_DATA` in `.env`. `scripts/utils.py` re-exports `DATA_DIR`,
`CATALOGS_DIR`, `DERIVED_TABLES_DIR`, `EMBEDDINGS_PATH` from `pipeline_loaders`.
Resolve paths through those constants — never hardcode `data/catalogs/` in a script.

**A worktree needs `make data` for the bulk corpus.** DVC-managed data is
normally absent in a fresh worktree. The exception is JETP documents: the hook
attempts a private reflink from the primary checkout when `documents.dvc`
matches; otherwise use `make jetp-data` (see `docs/jetp-storage.md`).
`.githooks/post-checkout` symlinks the
worktree's `.dvc/cache` at the primary checkout's cache, which is what lets
`make data` (a `dvc checkout`, no network) populate `data/` from local blobs.
Corpus work therefore belongs in a worktree like any other work. Running Phase 1
in the primary checkout gives up git isolation and skips the `dvc commit` /
`dvc push` that a normal PR carries, which is how ticket 0347 left `dvc.lock`
pointing at a superseded corpus (ticket 0360).

On this machine that costs almost no disk. `cache.type` is unset, so DVC tries
its default chain, reflink then copy, and the repo sits on btrfs: a checked-out
file shares its physical extents with the cache blob and gets its own copy only
on write. Measured, because inode identity cannot tell reflink from copy — after
a full `make data` in a probe worktree, `filefrag` reported the same extents
flagged `shared` for workspace file and cache blob, and free space was unchanged.
On a filesystem without reflink DVC falls back to a real copy, and there the same
checkout costs the full 2.2 GB.

Leave `cache.type` unset, and never set `hardlink` or `symlink`. Reflink is
safe because a write breaks the sharing; hardlinked files share one inode, so a
writer that opens the target in place writes straight into the cache blob and
corrupts it for every checkout at once. Phase 1 has both kinds of writer:
`pipeline_io.save_csv()` writes a temp file and `os.replace()`s it, an atomic
rename onto a fresh inode that would survive even a hardlinked cache, but
`np.savez_compressed(path, …)` in `enrich_embeddings` and `corpus_align` opens
the embeddings `.npz` directly and truncates it. One in-place writer is enough.
`tests/test_post_checkout_hook.py::test_dvc_cache_type_is_not_an_aliasing_type`
enforces this, because the setting can live in the gitignored
`.dvc/config.local` where no diff would show it.

**One cache, every checkout: think before `dvc gc`.** Sharing the cache widens
that command's blast radius. It prunes by reachability computed from whichever
checkout invokes it, so a stale worktree pinned to an old `dvc.lock`, or one
mid-rebuild that has not pushed, can delete blobs the primary still needs. Run
it from the primary checkout on a current `dvc.lock`, or not at all — ticket
0252 kept 8 orphan pointers for this reason.

`data/` is split by dataflow phase, so the directory names which phase owns a file:

```
data/
├── catalogs/     Phase-1 corpus (contract: refined_works/embeddings/citations)   DVC (dvc.yaml outs)
│   └── run_reports/  Phase-1 QA run summaries (pipeline_io.save_run_report)      DVC (run_reports.dvc)
├── pool/         Phase-1 raw source pulls                                         DVC (data/pool.dvc)
├── exports/      Phase-1 exports                                                  DVC (data/exports.dvc)
├── syllabi/      Phase-1 teaching sources                                         DVC (data/syllabi.dvc)
├── het/          seed lists (small, stable)                                       git-tracked
├── raw/          Phase-1 scratch                                                  gitignored
└── derived/      Phase-2 derived data (intermediates + derived tables)            gitignored, regenerable
```

The load-bearing rule: **`data/catalogs/` = corpus (Phase 1, DVC-managed);
`data/derived/` = analysis outputs (Phase 2, regenerable, gitignored).** No Phase-2
output belongs under `data/catalogs/` — guard `tests/test_phase_layout.py` fails if
a script or Make constant resolves one there.

## Data direction and corpus reruns

**Data flows padme → doudou, never back.** On padme: `make corpus` (DVC repro +
push; bare `dvc repro` skips the push). On doudou: `make corpus-sync`. New data
found on doudou travels as a query-config change that padme re-collects; never
`scp` data or `dvc push` from doudou (2026-03-17: hours of drift). JETP likewise:
push DVC outputs from padme; a fresh clone needs `dvc pull data/jetp/documents.dvc`
before `make jetp-data`, which is cache-only.

**A corpus rerun is never "obviously additive"; measure it** (tickets 0347, 0350):
the relevance cache keys on DOI, so no-DOI works are rescored on every
`--extend`, and a model or library drift moves the refined count.

- Back up to `data/raw/<ticket>-backup/` with `sha256sum` before the first
  write; byte-compare every stage (unified → enriched → extended → refined,
  plus `corpus_audit.csv`) column by column. Matching headline counts are
  necessary, not sufficient.
- Force the network closed: `HTTP_PROXY=http://127.0.0.1:9 HF_HUB_OFFLINE=1
  TRANSFORMERS_OFFLINE=1`, or seeds may newly fetch and flip flags.
- Finish with `dvc commit` + `dvc push` and land the `dvc.lock` diff in the same
  PR; check `md5sum <out>` against `dvc.lock`. Never `dvc commit` a stage you
  did not run. A new dependency must move nothing else in the `uv lock` diff.
