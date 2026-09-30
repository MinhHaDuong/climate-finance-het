# JETP programme data

Start with the [storage contract](../../docs/jetp-ledger-storage.md), the
[ontology](../../docs/jetp-ontology.md) and the
[information fusion rules](../../docs/jetp-fusion.md).

- `editorial/`: Markdown country/project narratives and monthly commentary.
- Root CSV files: canonical identities, observations, source references and
  collection history; their ownership is defined in the tracking contract.
- `ledger-snapshots/world-bank/`: frozen World Bank source fields for the historical reference pool.
- `documents/`: content-addressed source snapshots, tracked by `documents.dvc`.
- `releases/`: versioned publication descriptor guidance; no edition released yet.
- `decisions.md`: adjudications; unresolved pilot observations remain staged.

Edit prose in Markdown and structured facts in their registry. Website tables,
timelines and totals are generated from a pinned release, not hand-maintained here.
This directory is shared by the observatory and academic work; it is not a website
backend. Existing registries and DVC objects have not been moved.

Link rot (ticket 0925) has two tables of its own, never columns of the
collection registry: `web-archive-captures.csv`, the public Web Archive copy
of each collected document's address (or why there is none), and
`publisher-link-checks.csv`, the latest periodic check of each publisher
address, with the date a dead run began. Their scripts, schedule and served
views are described in
[`deliverables/jetp-observatory/README.md`](../../deliverables/jetp-observatory/README.md)
§ Web Archive copies and link checks.

The current ledger tables and their storage locations are listed in
[`jetp-ledger-storage.md`](../../docs/jetp-ledger-storage.md). Documentary
collection appends to `retrievals.csv` and `snapshots.csv`; it never rewrites
the reviewed `documents.csv` identities. The collection commands are
`make jetp-harvest`, `make jetp-harvest-blocked`, and
`make jetp-collect-downloads`. The static observatory reads the v2 ledger.
The historical design notes in this directory describe earlier ingestion
steps; they are not instructions to regenerate retired tables.

## Snapshots in worktrees

With hooks enabled (`make setup`), a fresh linked worktree initializes
`data/jetp/documents/` from the primary checkout when both `documents.dvc`
pointers match and the filesystem supports reflinks. Reflinks share the file's
disk blocks initially, while each checkout owns its inode: writing or deleting
the worktree's copy cannot change the primary copy. Source bytes are only read;
an existing local documents directory, file or symlink is left untouched.

Set `JETP_SNAPSHOT_SOURCE=/path/to/documents` in the environment of
`git worktree add` to use another local snapshot directory. Its companion
`/path/to/documents.dvc` must match the worktree pointer. This pointer check
prevents automatic provisioning from a different recorded revision; the
manifest's SHA-256 checks still validate the bytes themselves.

Initialization makes no network requests and never falls back to a full copy.
If the source is absent, the pointers differ, or reflinks are unsupported, the
hook warns and leaves data absent. Run `make jetp-data` inside that worktree to
materialize **only** `data/jetp/documents.dvc` from the shared local DVC cache.
If the cache lacks those objects, explicitly fetch them with
`uv run dvc pull data/jetp/documents.dvc`. The broader `make data` still
materializes all DVC outputs.

For an existing worktree with no documents directory, rerun
`sh .githooks/post-checkout` to attempt the same initialization. Tests continue
to read worktree-relative paths. Tests that open archived PDFs or HTML are in
the slow tier (`make check`); their content and hash assertions remain strict,
so that gate requires the snapshots. `make check-fast` needs no archived bytes.
