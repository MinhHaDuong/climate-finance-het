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
  holds and why they run in that order): **Documents** · **Entries** · **On
  the record** · **Projects** · **Funding** · **Who's who**, in trail order.
  Who's who lists funders and operators as the project documents spell them,
  not yet matched to one another (the parties table of ticket 0875). The
  selected tab marks the step and the tabs beside it are its neighbours. A
  page scoped to a country shows it at the bar's right as a removable chip,
  and the trail tabs keep the country.
- **The tallies** (the tab lands on Counts): **Counts** is one table, a row
  per figure we computed (what it is, value, unit, what it covers, as of,
  and a link to what was counted), grouped by country and never summed
  across countries, then two numbered, captioned figures. **Comparisons** is
  the historical World Bank pool. The accounts page of ticket 0877 will join
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

Each page's address is its label's slug. The addresses of earlier previews
forward to the new ones in place, in one hop (`history.replaceState`, no
reload), query and deep link included. The pages emit only the new names.

| Page | Address | Earlier address, forwarded |
|---|---|---|
| Landing page | `#overview` | |
| The paper trail | `#the-paper-trail` | |
| Documents | `#documents`, `#documents?country=<CODE>` | |
| Entries | `#entries`, `#entries/<CODE>`, `#entries/<CODE>?row=N` | `#inventory/<CODE>`, `#inventory/<CODE>?row=N` |
| On the record | `#on-the-record`, `#on-the-record/<CODE>` | `#evidence`, `#inventory/<CODE>?tab=record` |
| Projects | `#projects`, `#projects?country=<CODE>`, `#project/<project_id>` | |
| Funding | `#funding`, `#funding/<CODE>` | `#countries`, `#country/<CODE>` |
| Who's who | `#whos-who`, `#whos-who?country=<CODE>` | |
| Counts | `#counts` | `#numbers`, `#by-the-numbers`, `#the-tallies` |
| Comparisons | `#comparisons`, `#comparisons?country=<CODE>` | `#comparison`, `#historical-comparison`, with `?country=<CODE>` |
| About | `#about` | |
| Glossary | `#glossary` | |
| Methods | `#methods` | `#how-we-did-this` |
| Who we are | `#who-we-are` | |
| Release history | `#release-history` | `#editions` |
The served views keep the addresses they were built with — `provenance.json`
names `#country/<CODE>` routes — and those forward like any other.

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
- A Documents page listing every collection attempt in `data/jetp/manifest.csv`
  with its status, content type, size and origin URL. The archived copies
  themselves are staged locally by `make jetp-observatory-documents` into
  `documents/`, with the index of what was staged. That staging happens once;
  after a `dvc checkout` moves the snapshot to another revision, `make
  jetp-observatory-refresh` restages it. `documents/` is local-preview only:
  it is git-ignored, so the public bundle never holds it, and any public
  release carries the registry and the origin URL alone.
  `scripts/jetp/_public_release.py` copies the whole tree at a pinned commit and
  does not go through that exclusion; it is out of scope until the next release.
- The entries of ZAF, IDN, VNM and SEN (the frozen M1a inventories). These
  keep every selected document row, the publisher's issue and its cutoff,
  without matching identities. Their manifest counts field, identity and
  availability unknowns separately for each document extract, and again per
  country for the same export. The entries page shows the per-extract figures
  and, on its count line, the size of the export ("rows in this export"),
  labelled as such: the extracts overlap, so that number is a file size, not a
  project count (ticket 0856).
  `#entries/<CODE>` explores them row by row: the CSV stays the download
  artefact, while the page reads the `<CODE>.json` companion the same build
  writes from the same rows — column names once, then one array of values per
  row, so the browser parses no CSV text and the file stays under the
  repository's committed-file ceiling. Each row links to its document's page on
  the publisher's site, at its PDF page where the document gives one and the
  origin is a PDF, and to the archived copy where the preview serves it. The export width is per country,
  so the page wires only the five facets every country carries and shows every
  other column in the row detail.
- What is on the record for the same four countries, at
  `#on-the-record/<CODE>`, the step after the entries: the 766 rows of `data/jetp/events.csv`,
  `implementation-events.csv` and `project-source-links.csv`, served verbatim
  under `data/observations/<CODE>.json` with the table, the kind, the
  verification word the ledger wrote, and the fingerprint and PDF page of the
  document each was read from. Each item reads "according to" its publisher,
  with the document's date, as the country view names them. Counts are shown
  per table and per country. The entries and these items are two extractions
  of the same documents under two schemas; they are read separately and are
  never added together. No amount is summed, converted or promoted here, and
  no verification state is recoded.
- The step down from a project to what is on the record about it, and the
  step up from a document to what relies on it. Each named project's page
  carries a review-state badge and an "On the record about this project"
  fold-out: the items addressed to that identity, read from
  `data/observations/<CODE>.json` — the view `#on-the-record/<CODE>` loads —
  and filtered on `project_id` in the browser, each linking to the publisher's
  page and, in the local preview, to the archived
  document where the collection holds one. The country view carries no copy
  of them: `ZAF.json` has a publication cap of 512 000 bytes
  (`config/jetp-zaf-migration.json`), and the 338 ZAF rows copied into it put
  it 280 kB over (ticket 0855). Each Documents row lists what was extracted
  from that document (its entries and its items on the record, one fold-out
  and one count each — never their sum, since an entry and an item can
  describe the same paragraph of the same file, ticket 0856) and which
  projects and reviewed items rely on it — separate lists, never a total, and
  a document nothing cites says so. That step is a join the page makes at
  read time (ticket 0858; one served file is one table, so `documents.json` is
  the collection registry alone and carries no index of it): the fold-outs
  load, once per country and per session, `data/m1a/<CODE>.json` and
  `data/observations/<CODE>.json` for the attempt's country — the same views
  the entries page reads, through the same cache — and filter them on
  `source_id`; the projects are the country views' projects whose documents
  name it and the reviewed items one of whose proofs does. Each entry in that
  fold-out links to its own row (`#entries/<CODE>?row=N`, `N` the row's rank
  in the export) and, where its locator names a PDF page, to that page of the
  publisher's PDF and of the archived copy where served — the page read by the same port of `_m1a_document_links.py`
  the entries page uses; the document's own links open at the first page the
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
