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

The evidence layer of the ledger (ticket 0872, migration step 1 of
[`jetp-ledger-migration.md`](../../docs/jetp-ledger-migration.md)) is
`publishers.csv`, `documents.csv`, `document-publishers.csv`, `retrievals.csv`
and `snapshots.csv`, with the `same_as` candidates for mirrors and near-duplicate
publisher labels in `relations.csv`. They were rebuilt once from `sources.csv`
and `manifest.csv` by `scripts/jetp/build_evidence_layer.py`, and the Documents
view reads them. The two old tables stay, read only, until ticket 0878
retires them with their readers; a new collection is not yet written to the new
tables.

A local observatory MVP now lives in `deliverables/jetp-observatory/`; its
committed JSON handoffs are a preview, not a deposited monthly edition.

### Observatory timing adjudication

`event-timing.csv` keys reviewed timing to financial `event_id` or implementation
`implementation_event_id` (globally unique). It adds semantics without rewriting
legacy `event_date` values. Every current event has a timing row; new unclassified
observations export `date_role=unreviewed`, never an assumed event date. Orphaned
or conflicting timing keys fail the build.

`date_role` describes what the legacy date means: event, reporting cutoff,
publication, observation, register, other milestone, ambiguous, or unknown.
`event_precision` is independently day, month, year, interval, or unknown.
`event_start` and `event_end` bound only the observed milestone, not the source
publication or a different lifecycle stage. Day precision requires equal bounds;
unknown timing has no bounds. `observed_on` is a status observation or reporting
cutoff, `reported_on` is source publication, and `date_note` explains adjudication.
Collection timestamps remain in the source manifest and are exported separately.
A year interval is not converted into an arbitrary first-day event. Source
locators and notes remain in the event registries; uncertainty must survive both
JSON and the displayed timeline. The South African financing register remains a
register observation, not a verified signature date.

Project exports also retain `source_links` with relationship, review status,
locator and notes, plus source-claim `match_status`. A source being listed does
not confirm an entity join. Historical exports expose acquisition dates and
query/page hashes under per-country `snapshots`; the edition cutoff never updates
those dates, and `source_updated_on=null` explicitly means unknown.
