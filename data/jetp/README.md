# JETP programme data

Start with [storage and publication](../../docs/jetp-storage.md), then the
[documentary tracking contract](../../docs/jetp-tracking.md).

- `editorial/`: Markdown country/project narratives and monthly commentary.
- Root CSV files: canonical identities, observations, source references and
  collection history; their ownership is defined in the tracking contract.
- `comparison/`: frozen World Bank source fields for the historical reference pool.
- `documents/`: content-addressed source snapshots, tracked by `documents.dvc`.
- `releases/`: versioned publication descriptor guidance; no edition released yet.
- `decisions.md`: adjudications; unresolved pilot observations remain staged.

Edit prose in Markdown and structured facts in their registry. Website tables,
timelines and totals are generated from a pinned release, not hand-maintained here.
This directory is shared by the observatory and academic work; it is not a website
backend. Existing registries and DVC objects have not been moved.

A local observatory MVP now lives in `deliverables/jetp-observatory/`; its
committed JSON handoffs are a preview, not a deposited monthly edition.
