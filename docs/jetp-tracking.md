# JETP documentary tracking contract

OECD CRS is the lagged comparison layer. The current state of the four JETPs
comes from dated official documents and project records. This contract keeps
the two roles separate and makes every aggregate reversible.

## Objects and ownership

| Object | Canonical location | Versioning | Meaning |
|---|---|---|---|
| Controlled vocabularies | `config/jetp_tracking.yaml` | git | Countries, authority classes, source types, event statuses and scopes |
| Source universe | `data/jetp/sources.csv` | git | One curated URL per source; a row is discovery, not proof that collection succeeded |
| Collection history | `data/jetp/manifest.csv` | git | Append-only observation for every retrieval attempt, including failure and `not_modified` |
| Binary snapshots | `data/jetp/documents/` | DVC | Content-addressed immutable objects; one object may support several source rows |
| Project identities | `data/jetp/projects.csv` | git | Stable projects and aliases, independent of individual financing events |
| Financial events | `data/jetp/events.csv` | git | One dated event at one status layer, tied to an exact document and locator |
| Implementation events | `data/jetp/implementation-events.csv` | git | Physical project delivery and closure states, kept separate from finance |
| Dry searches | `data/jetp/dry-searches.csv` | git | Expected but absent, blocked or unpublished material and the route checked |
| Human decisions | `data/jetp/decisions.md` | git | Adjudications that change coding conventions or resolve conflicts |

The small registries stay visible in git because they are research evidence.
The binary pool is excluded from git and captured with `dvc add
data/jetp/documents` on padme. A DVC push is never part of a harvest run and is
performed only from padme after review.

## Source-bounded exhaustiveness

Exhaustive does not mean an untestable claim to have found every web page. For
each country, the source universe is closed over these authorities:

1. national JETP portal or responsible ministry;
2. IPG co-leads and every public partner named in the package;
3. multilateral and private windows named in official financing tables;
4. the national electricity operator and named project operators;
5. every project in an official plan, pipeline or progress list.

The country ticket records a terminal verdict for every expected authority and
every listed project: collected, not published, blocked or not applicable.
Project pages are followed to their approval document, financing agreement and
official updates when those exist. News is searched after official sources;
secondary reporting remains a lead unless no primary document is public, in
which case the event is marked `secondary_only` during verification.

## Counting rules

- A project and a financial event are different objects. A project may have
  many funders, instruments, dates and status layers.
- `need`, `announced`, `mou`, `approved`, `signed` and `disbursed` are a
  chronology, not additive categories. Aggregates select one layer explicitly.
- `proposed`, `preparation`, `procurement`, `construction`, `operational`, `suspended`,
  `closure_proposed`, `closure_agreed`, `retired` and `cancelled` describe
  physical delivery. They never follow automatically from a financial status.
- The amount and currency stated by the primary document are canonical.
  Third-party conversions are retained as observations and excluded from sums.
- `jetp_strict` requires explicit JETP attribution in the source.
  `ipg_energy_extended` is reported separately and never silently fills the
  strict perimeter.
- Conflicting values are preserved as distinct observations. A human decision
  may choose an aggregation rule but must not erase the conflict.
- Missing publications and inaccessible documents are observations in the
  opacity map, not empty cells to be imputed.

## Refresh cycle

`make jetp-harvest` performs conditional HTTP requests, appends the result of
each check to the manifest and stores any new content by SHA-256. At a stable
URL, changed bytes create a second immutable object; a `304 Not Modified`
observation points back to the previous object. HTML error pages cannot enter
the PDF pool.

After collection, a researcher reviews redirects, invalid content and dry
searches before DVC capture. Extraction and reconciliation run only on source
rows accepted for evidence. A later refresh appends events and observations;
it never rewrites prior states to make the latest value look timeless.
