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
`#project/<project_id>`, `#comparison`, `#documents`, `#methods`. Country-filter links use
`#projects?country=IDN` and `#comparison?country=IDN`.

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
  `documents/`, which is local-preview only: it is excluded from the bundle and
  from any public release, which carry the registry and the origin URL alone.
  `scripts/jetp/_public_release.py` copies the whole tree at a pinned commit and
  does not go through that exclusion; it is out of scope until the next edition.
- Frozen M1a CSV inventories for ZAF, IDN, VNM and SEN. These retain every
  selected source row, edition and cutoff without merging identities. Their
  manifest displays field, identity and source-availability unknowns separately.

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
offline replay from pinned local inputs and never refreshes a source. The
ordinary observatory build serves the committed export without requiring DVC.
