# JETP Observatory — local MVP

A static, Markdown-first preview of the four JETPs, with aggregate synthesis,
source-linked country/project views and a historical reference pool. No server
application, database, external fonts or JavaScript dependencies are required.

## Open the preview

From the repository root:

```bash
make jetp-observatory
make jetp-observatory-preview
```

Open <http://127.0.0.1:8765>. The build reads local snapshots only; it does not
collect sources or access DVC. A static host can serve this directory as-is.
Use `PYTHON=.venv/bin/python` on the make commands to reuse the installed
interpreter when the machine's uv cache is unavailable.

Routes: `#overview`, `#countries`, `#country/IDN`, `#projects`,
`#project/<project_id>`, `#comparison`, `#documents`, `#inventory/<CODE>`,
`#methods`. Country-filter links use `#projects?country=IDN` and
`#comparison?country=IDN`.

## What is included

- Country synthesis and attributed financing headlines with distinct dates/stages.
- Named-record financing evidence and theme/technology distributions.
- 383 named records and 21 separately disclosed unnamed slots.
- Source-linked observations, financial amounts, reports and project timelines.
- 97 historical closed energy-related World Bank operations in the same countries,
  with instrument, vintage, country, name and additional-finance filters.
- Downloadable JSON and input SHA-256 hashes. Country prose lives in
  `data/jetp/editorial/countries/`; headline policy is in `config/jetp_observatory.yaml`.
- A Documents page listing every collection attempt in `data/jetp/manifest.csv`
  with its status, content type, size and origin URL. The archived copies
  themselves are staged locally by `make jetp-observatory-documents` into
  `documents/`. That staging happens once; after a `dvc checkout` moves the
  snapshot to another revision, `make jetp-observatory-refresh` restages it.
  `documents/` is local-preview only: it is excluded from the bundle and
  from any public release, which carry the registry and the origin URL alone.
  `scripts/jetp/_public_release.py` copies the whole tree at a pinned commit and
  does not go through that exclusion; it is out of scope until the next edition.
- Frozen M1a inventories for ZAF, IDN, VNM and SEN. These retain every
  selected source row, edition and cutoff without merging identities. Their
  manifest displays field, identity and source-availability unknowns separately
  for each extraction sub-layer, and again as a per-country count of the same
  export. The inventory page shows the per-sub-layer figures and, on its count
  line, the size of the export ("rows in this export"), labelled as such: the
  sub-layers overlap, so that number is a file size, not a project count
  (ticket 0856).
  `#inventory/<CODE>` explores them row by row: the CSV stays the download
  artefact, while the page reads the `<CODE>.json` companion the same build
  writes from the same rows — column names once, then one array of values per
  row, so the browser parses no CSV text and the file stays under the
  repository's committed-file ceiling. Each row opens its archived source document, at
  its PDF page where the source publishes one. The export width is per country,
  so the page wires only the five facets every country carries and shows every
  other column in the row detail.
- Ledger observations for the same four countries, in the second tab of
  `#inventory/<CODE>`: the 766 rows of `data/jetp/events.csv`,
  `implementation-events.csv` and `project-source-links.csv`, served verbatim
  under `data/observations/<CODE>.json` with the table, the kind, the
  verification word the ledger wrote, and the fingerprint and PDF page of the
  document each was read from. Counts are shown per table and per country. The
  inventories and these rows are two extractions of the same documents under
  two schemas; they are read separately and are never added together. No amount
  is summed, converted or promoted here, and no verification state is recoded.
- The descent from a fact to its evidence, and the climb from a document to
  what cites it. Each named record's page carries a review-state badge and a
  "Ledger evidence" fold-out: the ledger observations addressed to that
  identity, read from `data/observations/<CODE>.json` — the view the
  Observations tab loads — and filtered on `project_id` in the browser, each
  opening its archived document where the collection holds one. The country
  view carries no copy of them: `ZAF.json` has a publication cap of 512 000
  bytes (`config/jetp-zaf-migration.json`), and the 338 ZAF rows copied under
  an `evidence` key put it 280 kB over (ticket 0855). Each Documents row lists, from `by_source_id` in
  `documents.json`, what was extracted from that source (ledger rows and frozen
  M1a rows, as references to their own views, one fold-out and one count per
  product — never their sum, since a ledger row and an M1a row can describe
  the same paragraph of the same file, ticket 0856) and which facts rely on it
  (named records and reviewed records) — separate lists, never a total, and a
  source nothing cites says so. Each M1a position in that fold-out links to
  its own inventory row (`#inventory/<CODE>?row=N`, `N` the row's rank in the
  export, written with the reference) and, where its locator names a PDF
  page, to that page of the archived copy; the copy's own link opens at the
  first page the extracted rows name, when every product that names one
  agrees (`first_pdf_page`), and at page 1 otherwise — no page is ever
  fabricated (ticket 0857). The reviewed-evidence pedigree opens the bytes
  its fingerprint pins. The Viet Nam page shows the 279 positions of the RMP
  2023 table and the 24 records of the 2025 portfolio side by side; no link
  between them is established here.

This is a preview, not the complete public release of 0726 or deployment of 0727.
There is no pooled disbursement rate or causal acceleration estimate. Headline
national amounts come from attributed reports; repeated project events are not
summed. Historical financing windows are not construction durations.

## Validation

Unit evidence-boundary checks are in `tests/test_jetp_observatory_mvp.py`.
Manual Chromium checks live in `tests/browser/jetp_observatory.py` and cover
navigation, filtering, source access, download payloads and mobile overflow.
Playwright is a development dependency; its browser is installed once per
machine. Start the preview, then run:

```bash
uv sync && uv run playwright install chromium
uv run python tests/browser/jetp_observatory.py --screenshot /tmp/jetp-overview.png
```

The initial data export is committed as a small handoff, not hidden in a DVC
remote. Every build invocation writes exactly one JSON view. Rebuild with
`make -B jetp-observatory` after changing source inputs; the input hash manifest
makes changed bytes explicit. A non-null input Git SHA is emitted only when all
listed input files match that commit. Uncommitted previews rely on file hashes.
Rebuild the frozen inventories alone with `make jetp-data jetp-m1a`; this is an
offline replay from pinned local inputs and never refreshes a source.
Rebuild the ledger observations alone with `make jetp-data jetp-observations`. The
ordinary observatory build serves the committed export without requiring DVC.
