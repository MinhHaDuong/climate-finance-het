# JETP programme storage: Markdown first, static publication

Decision: 13 September 2026, Plan phase. This document organises the existing
corpus and specifies the publication boundary for tickets 0726–0728 and 0730.
It does not implement an exporter, migrate registries or deploy a website.

## Choice

Authors work in Markdown and review changes in Git. Structured observations
remain in the existing small CSV registries, with controlled vocabularies in
`config/jetp_tracking.yaml`. Archived source bytes remain content-addressed under
DVC. The website is built as static HTML with generated JSON/CSV for filters,
timelines, charts and downloads. Neither DVC nor SQLite is a website runtime.

Markdown first means the primary reading and editorial interface is a dossier,
not a database administration screen. It does not mean encoding every financial
transaction in prose or maintaining a second handwritten table of totals.

SQLite is optional later as a disposable query/export artifact. It must be
rebuildable from a frozen release and cannot become a second editable authority.
A live database is reconsidered only if a concrete requirement emerges, such as
transactional browser editing, an authenticated API or queries that cannot be
served acceptably from static country-level payloads. Record that decision and
its operational ownership before adding a backend. Browser-side SQLite is also
unnecessary for the initial site.

## Storage map

| Material | Authoritative home | Versioning / publication |
|---|---|---|
| Programme decisions | `conception/jetp-observatory-and-papers-plan.md`, this document | Git; planning references |
| Country narratives | `data/jetp/editorial/countries/<ISO3>.md` | Git; rendered with release-bound portfolio data |
| Project narratives | `data/jetp/editorial/projects/<project_id>.md` | Git; references an existing canonical identity |
| Monthly editorial notes | `data/jetp/editorial/editions/<edition_id>.md` | Git; draft until a release is validated |
| Editorial templates | `data/jetp/editorial/templates/` | Git; excluded from published content |
| Project identities and source-linked observations | Existing `data/jetp/*.csv` | Git; canonical field ownership unchanged |
| Source bytes | `data/jetp/documents/objects/<prefix>/<sha256>.<ext>` | DVC via existing `documents.dvc`; not served wholesale |
| Collection attempts | `data/jetp/manifest.csv` | Git; append-only, including failed retrievals |
| Release descriptors | `data/jetp/releases/<edition_id>/release.json` | Git; planned output of 0726/0728 |
| Analysis intermediates | `data/derived/jetp/` | Regenerable; gitignored; planned under 0730 |
| Site sources and selected-release handoff | `deliverables/jetp-observatory/` | Local MVP under 0734; public deployment under 0727; source and small handoff assets in Git |
| Frozen downloadable editions | Versioned public release or deposit archives | Immutable files, checksums and public URLs in release descriptor |
| Optional SQLite export | `data/derived/jetp/<edition_id>.sqlite` | Regenerable; never edited or required by the website |

The local MVP now includes four reviewed country narratives and generated project
pages; see the [MVP README](../deliverables/jetp-observatory/README.md). Further
project dossiers are added through reviewed work, rather than creating hundreds
of empty profiles that look like coverage. The website can generate a
basic source-backed project page from the registries when no narrative exists.
No directory move or new DVC target is needed to adopt this organisation.

## One owner for each fact

`projects.csv` owns canonical identity and essential structured features.
`events.csv` owns financial observations; `implementation-events.csv` owns
physical observations. `source-claims.csv` preserves attributed documentary
claims. Sources, snapshots, locators and review verdicts follow
[the tracking contract](jetp-tracking.md). The pilot and unresolved records keep
their existing staging status until reconciled; a Markdown page cannot ratify them.

Markdown owns explanation, interpretation and editorial context. Front matter
contains join IDs, draft/review state, editorial review date and referenced source
or claim IDs. It does not duplicate the project's operator, current financing
amount or stage. Numeric discussion may quote a specifically dated claim with a
reference, but is not an input to aggregation. A release review checks those
quotations against the selected snapshot.

Changing a ledger observation must not silently leave a contradictory narrative
published. The release check lists affected dossiers for review. Missing dossiers
are acceptable; unsupported narrative assertions are not. Do not implement
bidirectional Markdown/CSV/SQLite synchronisation.

## Lifecycle dates and identifiers

Keep existing IDs stable; filenames and site routes use project IDs rather than
display names. Programme/component and multi-funder relationships are preserved
by the release schema in 0726; neither a Markdown title nor a similar capacity
establishes a match. Historical comparator projects receive their own namespace
and belong to the analysis dataset, not automatically to the public JETP list.

The release schema must distinguish event date, source publication date,
retrieval date, editorial review date and release cutoff. It must support date
precision, intervals, unknown dates and a status observed by a given date.
Existing first_seen/last_seen or register start dates must never silently become
approval or signature dates. Record both JETP entry and earlier project history.
Effectiveness/first-payment and preparation transitions require a reviewed schema
extension; do not invent new enum values in Markdown outside the registry contract.

## Build and monthly release boundary

1. Collect/review evidence using the existing harvester and country workflow.
   Rendering never fetches sources or triggers collection.
2. Commit reviewed registries and Markdown. Validate IDs, source links, schema,
   date semantics, programme overlaps and aggregation policies (0726).
3. Pin a full input Git SHA and the DVC object pointer at that SHA. Build a frozen
   publication package from those inputs, containing permitted evidence metadata,
   editorial content, CSV/JSON exports, schema and aggregation definitions.
4. Validate the written files, compute checksums and review the edition changes.
   Create the descriptor in a later release commit: input_git_sha identifies the
   already existing input commit, avoiding a self-referential commit hash.
5. Render the website exclusively from that package. Ship small country/project
   JSON payloads, with lazy loading if needed, and static HTML. Public visitors
   need no Python, DVC, database service or archive credentials.
6. Publish immutable versioned downloads and pages after the reviewed release
   procedure. Advance the current-edition link only after the complete edition
   passes validation. Failed updates leave the last good edition available.

Edition IDs use `YYYY-MM` for the regular monthly edition and `YYYY-MM-rN` for
corrections, starting at r1. New editions record supersession; never replace the
bytes at a published edition URL. Papers pin an edition and input SHA, not a
moving current link. Analytical sample selection and code have their own version
references in addition to the observation release.

DVC retains binary evidence using the existing padme ownership rules. Public
release archives are an additional dissemination layer: their contents must be
usable without the private SSH DVC remote. Source URLs, hashes and locators can
be public even when the archived document itself is not redistributed. A public
archive includes raw documents only where release terms allow it. Verify required
DVC objects exist at the pinned remote before claiming full internal reproduction.

## Acceptance examples for implementation

- A reader edits a project explanation in Markdown and changes an amount in the
  financial registry; rebuilding updates the page and its derived total once.
- A programme and component, two loan tranches and repeated status observations
  do not become four additive projects or duplicate financing.
- A blocked source refresh preserves the previous observation and records the gap.
- A reported operational state with an earlier event date does not create a
  backwards lifecycle simply because its publication came later.
- An old edition and its chart reproduce after the current registry changes.
- A fresh static-site render from a frozen package works without DVC/network
  access; raw-evidence reconstruction is a separate documented operation.

These checks belong to existing tickets 0726–0728/0730. No new database or storage
implementation ticket is needed solely to establish this documentation.

## Technical references

[DVC metadata files](https://doc.dvc.org/user-guide/project-structure/dvc-files)
track data objects through Git-versioned pointers.
[SQLite's appropriate uses](https://www.sqlite.org/whentouse.html) include local
analysis and website storage, but suitability alone does not require adoption.
[Static hosting](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
can serve HTML, CSS and JavaScript; GitHub Pages is an option, not a hosting
selection made by this decision.
