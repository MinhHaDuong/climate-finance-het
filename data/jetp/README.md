# JETP programme data

Start with [storage and publication](../../docs/jetp-storage.md), then the
[documentary tracking contract](../../docs/jetp-tracking.md).

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
