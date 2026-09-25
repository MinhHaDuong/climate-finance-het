# JETP Observatory — local MVP

A static, Markdown-first preview of the four JETPs: their paper trail from each
document to the projects it names, the numbers we counted from it, and a
historical reference pool. No server application, database, external fonts or
JavaScript dependencies are required.

## Open the preview

From the repository root:

```bash
make jetp-observatory
make jetp-observatory-preview
```

Open <http://127.0.0.1:8765>. The build reads local snapshots only; it does not
collect documents or access DVC. A static host can serve this directory as-is;
the public site is its tracked tree, see [Publish on GitHub Pages](#publish-on-github-pages).
Use `PYTHON=.venv/bin/python` on the make commands to reuse the installed
interpreter when the machine's uv cache is unavailable.

## Links to documents: the publisher's page, and the archived copy where served

Every document the pages name links to the page it was collected from — the
`url` of `data/documents.json` — labelled "Publisher's page — <host>", with the
collection date and the SHA-256 of the bytes read. Where a locator names a PDF
page and the origin served a PDF, the link carries `#page=N`; the page number
refers to the bytes read, and the publisher's current file may differ. A failed
collection keeps its publisher link and says it failed.

The archived copy is an extra link, never a replacement. The pages draw it only
for a copy listed in `documents/index.json`, which `make
jetp-observatory-documents` (and `-refresh`) writes beside the staged copies,
and which the pages fetch once at load. `documents/` is git-ignored, so the
public bundle, the tracked tree, has no index and shows no archived link: there
is one `app.js`, one set of served views and no build flag (ticket 0915).

## Web Archive copies and link checks

Publisher pages rot (ticket 0925). Beside each "Publisher's page" link the
pages show "Web Archive copy — <date>", a copy held by the Internet Archive,
where one is recorded. For a PDF the copy opens as the archived bytes
themselves (Wayback's `id_` form, at the same `#page=N`), and the page says
our SHA-256 lets a reader check it is the same file; for a web page it opens
in the Wayback replay, and the page says the capture is not byte-identical to
what we read. When the periodic check finds a publisher link dead, the pages
say "publisher link dead since <date>" and put the Web Archive copy first.
The publisher's address is never rewritten.

Two tables of their own, never columns of the collection registry, each
served as its own view and joined by the page to `documents.json` on the
address:

| Table | Served as | Written by |
|-------|-----------|------------|
| `data/jetp/web-archive-captures.csv` (`source_id`, `url`, `outcome`, `capture_url`, `captured_at`, `attempted_at`, `error`) | `data/web-archive.json` | `make jetp-web-archive` |
| `data/jetp/publisher-link-checks.csv` (`url`, `checked_at`, `method`, `http_status`, `outcome`, `dead_since`, `error`) | `data/publisher-links.json` | `make jetp-link-check` |

`make jetp-link-views` rebuilds the two served files from the two tables, and
nothing else: the other views and their input hashes do not move.

**Capture** (`scripts/jetp/corpus_web_archive_capture.py`). `make jetp-harvest` runs
it after collecting; `make jetp-web-archive` runs it on everything. For each
collected document it reuses a Wayback snapshot taken within a year of the
collection date (`reused`), else asks Save Page Now for a new one
(`captured`); a failure is recorded with its reason (`failed`) and never
blocks; a Common Crawl WARC record is `not_applicable`. Save Page Now is
asked with the project's Internet Archive account when
`~/.config/keys/archive.env` holds `IA_S3_ACCESS_KEY` and `IA_S3_SECRET_KEY`
(read just before each request, sent only as its `Authorization` header,
never logged or recorded): three documents in flight, submissions 5 s apart.
Without that file it runs anonymously, one at a time, 15 s apart; anonymous
capture has been refused with HTTP 401 since 2026-09-24, so `--no-save` then
looks up existing snapshots only. It backs off on rate limits and resumes:
what is captured or reused is skipped, what failed is tried again. After five
consecutive connection failures to Save Page Now it stops requesting captures
for that run, still reusing existing snapshots, and marks the rest
`wayback_unreachable` for the next run.

**Link check** (`scripts/jetp/corpus_check_publisher_links.py`). HEAD, then GET
(body never read) when HEAD is refused; 1.5 s between requests, 30 s timeout.
`alive` is a 2xx/3xx answer; `dead` is 404, 410 or a host name that no longer
resolves; anything else (403 to robots, 5xx, timeout, TLS) is `unreachable`
and is never displayed as dead. `dead_since` is the first check of the
current dead run: an `unreachable` check neither starts nor ends it. One row
per address, rewritten in place; git history is the month-by-month record.

**Monthly on padme — the author's step; nothing is installed by the repo.**
The check needs network and the repo checkout, nothing else. A user timer
such as

```ini
# ~/.config/systemd/user/jetp-link-check.service
[Service]
Type=oneshot
WorkingDirectory=%h/CNRS/projets/actifs/climate-finance-het
Environment=PATH=%h/.local/bin:/usr/bin:/bin
ExecStart=/usr/bin/make jetp-link-check jetp-web-archive jetp-link-views

# ~/.config/systemd/user/jetp-link-check.timer
[Timer]
OnCalendar=monthly
RandomizedDelaySec=6h
Persistent=true
[Install]
WantedBy=timers.target
```

(`systemctl --user enable --now jetp-link-check.timer`; units as real files,
not symlinks) runs the check, retries the failed captures and rebuilds the
two views. It leaves the result uncommitted in the checkout: review the diff,
commit it on a branch, open a PR, and republish (`make
jetp-observatory-publish`) after merge. A cron line
(`0 4 1 * * cd ~/CNRS/projets/actifs/climate-finance-het && PATH=$HOME/.local/bin:$PATH make jetp-link-check jetp-web-archive jetp-link-views`)
does the same.

## How the pages are organised

The pages follow the four objects of [`docs/jetp-language.md`](../../docs/jetp-language.md)
without naming them, in the vocabulary of
[`docs/jetp-observatory-presentation.md`](../../docs/jetp-observatory-presentation.md)
(ticket 0881; the author's decisions of 2026-09-23). The header holds three
sections as tabs. Each tab's label links to the section's landing page, and
a disclosure button beside it opens a dropdown of the section's pages; at
phone width the three stack inside one collapsible nav. Under the header, on
every page of a section, the section's sub-bar lists its pages as plain
sibling tabs with the current one selected. The same component serves all
three sections.

- **The paper trail** (`#the-paper-trail`, a short page on what each step
  holds and why they run in that order): **Documents** · **Document rows** ·
  **Statements** · **Projects** · **Funding** · **Organisations**, in trail order.
  Organisations combines a name's funder and operator roles in one country;
  reviewed name forms appear as aliases, while unreviewed matches stay apart. The
  selected tab marks the step and the tabs beside it are its neighbours. A
  page scoped to a country shows it at the bar's right as a removable chip,
  and the trail tabs keep the country.
- **The tallies** (the tab lands on Counts): **Counts** is one table, a row
  per figure we computed (what it is, value, unit, what it covers, as of,
  and a link to what was counted), grouped by country and never summed
  across countries, then two numbered, captioned figures. **Non-JETP energy
  operations** is the historical World Bank pool. The accounts page of ticket 0877 will join
  as Money. A number we calculated carries "Our calculation"; a number a
  publisher printed carries "As published" and reads "according to" that
  publisher, with the date.
- **About** (`#about`): **Glossary**, the words the pages use, grouped by
  theme (what we track, how documents are read, statuses, measures,
  relations) and alphabetical within each group, generated from the ledger's
  term tables (ticket 0882): each term in force with its definition, its
  external scheme and SKOS relation, and the rows it superseded; a relation
  shows the classes it connects, a shared status the publishers' own words
  the status crosswalk maps to it. The five ontology tables are served one
  file each under `data/ontology/`, empty ones included, by
  `scripts/jetp/build_ontology_views.py` (`make jetp-ontology-views`). A term
  shown elsewhere links to `#glossary?term=<list>/<term_id>`. **Methods**: what was done, what the observatory does not do, and
  the downloads; the release history is linked from here. **Who we are**:
  the author's own text, from his published homepage bio, with links to his
  homepage and ORCID.

Breadcrumbs appear on detail pages only. The title block is an h1 and a
one-sentence lede, with the page's longer explanation folded under "About
this page". Nothing is there for causal explanations: the observatory tests
none.

### Addresses

Each page's address is its label's slug. The site was never published, so
no earlier address is kept, and an internal page key is not an address.

| Page | Address |
|---|---|
| Landing page | `#overview` |
| The paper trail | `#the-paper-trail` |
| Documents | `#documents`, `#documents?country=<CODE>` |
| Document rows | `#document-rows`, `#document-rows/<CODE>`, `#document-rows/<CODE>?row=N` |
| Statements | `#statements`, `#statements/<CODE>` |
| Projects | `#projects`, `#projects?country=<CODE>`, `#project/<project_id>` |
| Funding | `#funding`, `#funding/<CODE>` |
| Organisations | `#organisations`, `#organisations?country=<CODE>` |
| Counts | `#counts` |
| Non-JETP energy operations | `#non-jetp-energy-operations`, with `?country=<CODE>` |
| About | `#about` |
| Glossary | `#glossary` |
| Methods | `#methods` |
| Who we are | `#who-we-are` |
| Release history | `#release-history` |

## What is included

- The four partnerships, each with its national headline as its publisher
  reported it, with its own date and milestone.
- 383 named projects and 21 separately disclosed unnamed slots, with their
  themes and the furthest financing milestone on the record for each.
- For each project: what is on the record about it, its financial amounts,
  its documents and its timeline.
- 97 historical closed energy-related World Bank operations in the same countries,
  with instrument, vintage, country, name and additional-finance filters.
- Downloadable JSON and input SHA-256 hashes. Country prose lives in
  `data/jetp/editorial/countries/`; headline policy is in `config/jetp_observatory.yaml`.
- A Documents page with one row per document, on its best collection attempt
  (the latest collected one, else the latest), with every attempt recorded in
  `data/documents.json` listed under a fold (ticket 1210); status, content type,
  size and origin URL, and filters and counts that count documents. The archived copies
  themselves are staged locally by `make jetp-observatory-documents` into
  `documents/`, with the index of what was staged. That staging happens once;
  after a `dvc checkout` moves the snapshot to another revision, `make
  jetp-observatory-refresh` restages it. `documents/` is local-preview only:
  it is git-ignored, so the public bundle never holds it, and any public
  release carries the registry and the origin URL alone.
  `scripts/jetp/_public_release.py` copies the whole tree at a pinned commit and
  does not go through that exclusion; it is out of scope until the next release.
- The document rows of ZAF, IDN, VNM and SEN (the frozen M1a inventories). These
  keep every selected document row, the publisher's issue and its cutoff,
  without matching identities. Their manifest counts field, identity and
  availability unknowns separately for each document extract, and again per
  country for the same export. The Document rows page shows the per-extract figures
  and, on its count line, the size of the export ("rows in this export"),
  labelled as such: the extracts overlap, so that number is a file size, not a
  project count (ticket 0856).
  `#document-rows/<CODE>` explores them row by row: the CSV stays the download
  artefact, while the page reads the `<CODE>.json` companion the same build
  writes from the same rows — column names once, then one array of values per
  row, so the browser parses no CSV text and the file stays under the
  repository's committed-file ceiling. Each row links to its document's page on
  the publisher's site, at its PDF page where the document gives one and the
  origin is a PDF, and to the archived copy where the preview serves it. The export width is per country,
  so the page wires only the five facets every country carries and shows every
  other column in the row detail. HTTP(S) URLs in `raw_project_description`
  open as links without changing the archived text or the export.
- Statements for the same four countries, at
  `#statements/<CODE>`, the step after Document rows: the 766 rows of `data/jetp/events.csv`,
  `implementation-events.csv` and `project-source-links.csv`, served verbatim
  under `data/observations/<CODE>.json` with the table, the kind, the
  verification word the ledger wrote, and the fingerprint and PDF page of the
  document each was read from. Each item reads "according to" its publisher,
  with the document's date, as the country view names them. Counts are shown
  per table and per country. Document rows and these items are two extractions
  of the same documents under two schemas; they are read separately and are
  never added together. No amount is summed, converted or promoted here, and
  no verification state is recoded.
- Each Funding country page now lists one row per recorded financing statement,
  with the project, milestone, original amount and currency, funder, date role,
  and document location. Financing needs appear in a separate section. This
  replaces the first eight rows of the Projects table; repeated milestones
  and currencies are never summed.
- Organisations combines a name's funder and operator roles within a country,
  shows up to three project names directly, and unfolds the rest. The
  `data/party-names.json` view comes from reviewed `parties.csv` and
  `party-names.csv` rows; only those reviewed names are displayed as aliases.
- The step down from a project to the statements recorded about it, and the
  step up from a document to what relies on it. Each named project's page
  carries a review-state badge and a statements fold-out: the items addressed
  to that identity, read from `data/observations/<CODE>.json` — the view
  `#statements/<CODE>` loads — and filtered on `project_id` in the browser.
  Each item links to the publisher's page and, in the local preview, to the archived
  document where the collection holds one. The country view carries no copy
  of them: `ZAF.json` has a publication cap of 512 000 bytes
  (`config/jetp-zaf-migration.json`), and the 338 ZAF rows copied into it put
  it 280 kB over (ticket 0855). Each Documents row lists what was extracted
  from that document (its document rows and statements, one fold-out
  and one count each — never their sum, since a row and a statement can
  describe the same paragraph of the same file, ticket 0856) and which
  projects and reviewed items rely on it — separate lists, never a total, and
  a document nothing cites says so. That step is a join the page makes at
  read time (ticket 0858; one served file is one table, so `documents.json` is
  the collection registry alone and carries no index of it): the fold-outs
  load, once per country and per session, `data/m1a/<CODE>.json` and
  `data/observations/<CODE>.json` for the attempt's country — the same views
  the document rows page reads, through the same cache — and filter them on
  `source_id`; the projects are the country views' projects whose documents
  name it and the reviewed items one of whose proofs does. Each entry in that
  fold-out links to its own row (`#document-rows/<CODE>?row=N`, `N` the row's rank
  in the export) and, where its locator names a PDF page, to that page of the
  publisher's PDF and of the archived copy where served — the page read by the same port of `_m1a_document_links.py`
  the document rows page uses; the document's own links open at the first page the
  extracted rows name, when every extraction that names one agrees, and at its
  own first page otherwise — no page is ever fabricated (ticket 0857). A
  reviewed item's pedigree links to the bytes its fingerprint pins. The Viet Nam
  page shows the 279 positions of the RMP 2023 table and the 24 projects of
  the 2025 portfolio side by side; no link between them is established here.

This is a preview, not the complete public release of 0726 or deployment of 0727.
There is no pooled disbursement rate or causal acceleration estimate. Headline
national amounts come from attributed reports; repeated project events are not
summed. Historical financing windows are not construction durations.

## Publish on GitHub Pages

The public site is the tracked tree of this directory at one commit — nothing
added, nothing rewritten — served from the `gh-pages` branch of this public
repository (ticket 0915). There is no CI (ticket 0321); the commands below are
the whole path. They publish the local `origin/main` by default; set
`JETP_PAGES_REF=<ref>` to publish another commit.

```bash
git fetch origin
make jetp-observatory-bundle          # extract the public tree into data/derived/jetp/observatory-pages
.venv/bin/python -m http.server 8773 --bind 127.0.0.1 --directory data/derived/jetp/observatory-pages
.venv/bin/python tests/browser/jetp_observatory.py --url http://127.0.0.1:8773
bash scripts/jetp/publish_observatory_pages.sh   # dry run: builds the gh-pages commit, pushes nothing
make jetp-observatory-publish         # push that commit to origin/gh-pages
```

The bundle and the push use the same tree object, so what was previewed is what
goes out. Both refuse a tree holding `documents/`. The push is not forced: if
`gh-pages` moved meanwhile, it is refused rather than overwritten.

**Pushing `gh-pages` publishes nothing while GitHub Pages is disabled.**
Enabling it is the author's step, taken after the demonstration and his
explicit go-ahead: in the repository's Settings → Pages, set *Source* to
*Deploy from a branch*, branch `gh-pages`, folder `/ (root)`. The site then
serves at <https://minhhaduong.github.io/climate-finance-het/>. Check that
address in a browser, including the release and input revision shown on the
Methods page. `.nojekyll` keeps GitHub from running Jekyll over the tree.

## Validation

Unit boundary checks are in `tests/test_jetp_observatory_mvp.py`; what the
pages render, including the organisation and vocabulary of ticket 0881, is in
`tests/test_jetp_observatory_render.py`.
Manual Chromium checks live in `tests/browser/jetp_observatory.py` and cover
navigation, the paper trail walked both ways, filtering, document access,
download payloads and mobile overflow.
Playwright is a development dependency; its browser is installed once per
machine. The recipe runs the same checks on the local preview and on the
public bundle; only its archived-copy checks depend on `documents/index.json`
being served. Start the preview, then run:

```bash
uv sync && uv run playwright install chromium
uv run python tests/browser/jetp_observatory.py --screenshot /tmp/jetp-overview.png
```

The initial data export is committed as a small handoff, not hidden in a DVC
remote. Every build invocation writes exactly one JSON view. Rebuild with
`make -B jetp-observatory` after changing source inputs; the input hash manifest
makes changed bytes explicit. A non-null input Git SHA is emitted only when all
listed input files match that commit. Uncommitted previews rely on file hashes.
Rebuild the entries alone with `make jetp-data jetp-m1a`; this is an
offline replay from pinned local inputs and never refreshes a document.
Rebuild what is on the record alone with `make jetp-data jetp-observations`. The
ordinary observatory build serves the committed export without requiring DVC.
