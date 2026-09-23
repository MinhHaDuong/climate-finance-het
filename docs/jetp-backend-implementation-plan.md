# JETP backend implementation and migration plan

**Terminology note (2026-09-23).** This document predates the ODEM language
of [`jetp-language.md`](jetp-language.md), which governs where the two
differ. Read *evidence* (a link, a layer, a table of documentary support) as
**justification**, and *evidence cutoff* as **knowledge cutoff**; *model* (of the
data) as **schema**; *reconciliation* as **matching** for identities or
**account** for the balance computation; *edition* of the ledger or site as
**release**; *layer*, *stage* and *fact* as the pipeline **steps D1 to D4** and
**observations**. In ODEM terms the observatory is Data guided by Ontology,
Evidence is computed on top, and there is no Model.

Proposed 14 September 2026, against `ff9cbe834a166c4ecbd2fbae20afc8988c43ebc9`
(the merged [backend design, revision 5](jetp-backend-design.md)). This is an
implementation proposal. No migration, source refresh or website deployment has
been performed by writing this plan.

## Delivery strategy

Keep the MVP usable throughout. Freeze its current inputs and complete static
output first; introduce the new stores behind compatibility readers; validate
candidate exports beside the current website; then switch bounded publication
combinations after reconciliation. A failed migration or update leaves the last
accepted static edition available.

Three approaches were considered: replace the stores and renderer together
(high disruption and difficult diagnosis); keep two editable backends (persistent
drift); or migrate behind a compatibility boundary (recommended). The third
costs temporary adapter code but gives a reviewable difference report and a
recoverable website at every stage. Its success depends chiefly on documentary
reconciliation, not database throughput; numerical success probabilities would
be speculative before the baseline audit.

Use the existing Python/CSV/Markdown/DVC pipeline and static renderer. The
initial work introduces no database service. SQLite remains an optional derived
query export. Existing release, website and monthly-edition tickets remain the
owners of publication; the new tickets below supply their backend prerequisites.
No estimator, completed manuscript or PyPSA model blocks the website.

## Baseline to protect

The repository inspection found 404 registry rows: the existing website separates
383 named records from 21 unnamed count slots. There are 380 financial rows,
71 implementation rows, 451 timing rows, 301 sources, 307 acquisition-manifest
rows, 149 source claims and 1,628 plan-project rows. Other inputs include country
observations, 315 project-source links, 141 project-coverage rows, 109 dry-search
rows, authority coverage, news leads and pilot acquisition records. These are
row counts, not independent projects, payments or sources of corroboration.
Recount and hash them in the first ticket; numbers here are a baseline, not future
fixed assertions.

Current build: `scripts/analysis/jetp_observatory.mk` invokes
`scripts/jetp/build_observatory.py` once per JSON output, using
`_observatory_data.py`. The browser in `deliverables/jetp-observatory/app.js`
loads overview, comparison and four country payloads. Preserve country/project
hash routes, filtering, timelines, evidence links, useful editorial prose and
JSON downloads. The historical comparison pool retains its descriptive label.

The checked-in ZAF payload is 508,002 bytes, close to the 512,000-byte file cap.
Do not append a full provenance graph to every country object. Introduce versioned
sidecars or bounded project chunks, with a renderer that supports the change,
before growing the payload. Preserve a complete downloadable package and offline
serving; splitting files must not introduce a backend service or missing links.

## Work packages and order

Each numbered item is a separate implementation ticket with a first failing
acceptance fixture. The four country migrations share code and run sequentially
at first; they are separate review units because their reporting semantics differ.
The filed ticket links are listed below. Tracker 0760 contributes to programme
0725; it does not replace the programme's scientific and publication criteria.

| Wave | Ticket | Deliverable and first discriminating check | Website at completion |
|---|---|---|---|
| A | 0761 | Freeze baseline inputs/static assets, route and semantic inventory, candidate-output boundary and restoration drill. Interrupt a candidate build: accepted files and routes remain available. | Current MVP, recoverable as a complete bundle. |
| A | 0762 | Implement small schema/identity/evidence/time fixtures and versioned compatibility interfaces. Colliding typed IDs, late decisions and pending supersession must resolve correctly. | Current reader remains authoritative; candidate model has no public ownership. |
| B | 0763 | Crosswalk source revisions, acquisition attempts, editions, extractions and assertion evidence; preserve coverage and origin uncertainty. Refresh a URL: an old assertion still resolves to its old bytes. | Legacy-compatible exports; missing archival evidence is explicitly unresolved. |
| C | 0764 | Pilot Vietnam: ingest saved official RMP inventories completely; classify existing observations and preserve all legacy rows. Every source inventory row has an accepted mapping or explicit disposition. | Four-country MVP stays usable; VNM candidate diff becomes reviewable. |
| C | 0765–0767 | Apply the migration to ZAF, IDN and SEN, one country per ticket. Preserve register states, approvals, plans and programme/component distinctions. | Accepted country changes only; no global switch or pooled financial total. |
| D | 0768 | Implement agreement/occurrence/coverage decisions and the first original-currency gross-disbursement account. Duplicate reports and overlapping flows count once; unsupported closing remains unavailable. | Reported headlines continue; reconstructed measures remain candidates until accepted. |
| D | 0769 | Add publication provenance, compatible chunked output, editorial claim links and controlled publication selection. Two displays sharing one field remain distinct; a partial or duplicate-ownership combination cannot publish. | Small accepted combinations switch; routes/downloads remain valid. |
| D | 0770 | Implement source watch policies, frozen sweeps and candidate change reports. A blocked check cannot advance successful coverage or publish changes. | Refreshes produce reviewable candidates; accepted edition remains stable. |
| E | Existing 0726–0728 | Freeze a public package, verify browser/hosting, rehearse a second edition and restoration. A late report/correction changes the new edition while the old one replays. | Versioned viable website and reviewed update routine. |

Dependency order: 0761 precedes 0762; 0762 precedes 0763; 0763 precedes the
Vietnam pilot. ZAF/IDN/SEN follow that pilot to reuse its accepted importer and
crosswalk conventions. Account work depends on the pilot plus ZAF migration;
publication work depends on the Vietnam pilot and can expose traced reported
positions before the financial account engine is ready. Its account-enabled
acceptance additionally requires 0768; other combinations remain legacy. Watch/sweep work depends on 0763 and can proceed independently of
financial reconciliation. Release acceptance requires all four country migration
reports, publication validation and the existing 0726 requirements. The full
monthly rehearsal additionally requires 0770 and existing 0727 acceptance.

Begin with 0761 only. Use its actual migration counts and browser/build results
to confirm the next wave. Do not launch all tickets simultaneously or allocate
a calendar commitment before the pilot measures extraction and review effort.

## Proposed implementation issues

- [0760: Coordinate backend migration while preserving the JETP MVP](https://github.com/MinhHaDuong/climate-finance-het/issues/1353)
- [0761: Freeze a recoverable MVP baseline and isolate candidate builds](https://github.com/MinhHaDuong/climate-finance-het/issues/1354)
- [0762: Implement typed evidence and temporal contracts behind compatibility readers](https://github.com/MinhHaDuong/climate-finance-het/issues/1355)
- [0763: Migrate source and acquisition identity with immutable evidence crosswalks](https://github.com/MinhHaDuong/climate-finance-het/issues/1356)
- [0764: Pilot official-inventory and legacy-position migration in Vietnam](https://github.com/MinhHaDuong/climate-finance-het/issues/1357)
- [0765: Migrate South African register states and legacy observations](https://github.com/MinhHaDuong/climate-finance-het/issues/1358)
- [0766: Migrate Indonesian portfolio positions and legacy observations](https://github.com/MinhHaDuong/climate-finance-het/issues/1359)
- [0767: Migrate Senegal plan and programme positions with explicit scope](https://github.com/MinhHaDuong/climate-finance-het/issues/1360)
- [0768: Implement bounded agreement and gross-disbursement reconciliation](https://github.com/MinhHaDuong/climate-finance-het/issues/1361)
- [0769: Publish migrated combinations through compatible traced website outputs](https://github.com/MinhHaDuong/climate-finance-het/issues/1362)
- [0770: Implement source-registry sweeps and reviewable evidence refreshes](https://github.com/MinhHaDuong/climate-finance-het/issues/1363)

## Data migration protocol

1. **Freeze and enumerate.** Record input Git/DVC revisions, hashes, CSV headers,
   row keys, duplicates, all consumed files and stable public routes. Include
   coverage, failed searches, country observation and pilot tables, not only the
   nine tables currently read by the website. Verify source bytes by hash; a DVC
   pointer alone is not proof of recoverability.
2. **Map without replacing.** Migration code writes candidate tables and a
   manifest with old table/typed ID (or frozen row locator), new typed IDs,
   transformation/version, reason, disposition and review state. Support one-to-many
   mappings, explicit exclusions and unresolved rows. A rerun on the same inputs
   is idempotent. No unexplained row may disappear; row-count equality is not a
   substitute for semantic reconciliation.
3. **Preserve knowledge and meaning.** Keep event, state/cutoff, coverage,
   publication, acquisition and admission times distinct. Old review dates and
   origin classifications remain unknown where unsupported. Preserve original
   wording/amount/currency and durable source locators. Do not turn a register
   start into a signature, an allocation into a payment, or a count slot into a
   named project. Retain failed searches and cancelled/nonselected observations
   for future study frames; do not infer that their history is complete.
4. **Review inventories and differences.** Each country's report lists all
   inventory rows and all legacy rows, their dispositions, added/retained IDs,
   reported totals, scope/unit/currency mismatches, unknowns and resulting page
   changes. Start from the principal official report and its inventories, then
   reconcile supplementary evidence. Pin the actual editions used; newly found
   reports are a separate, attributable evidence refresh.
5. **Transfer ownership once.** Until acceptance, legacy records are the sole
   writable authority for an unmigrated assertion. Candidate rows are regenerated
   and reviewed against pinned inputs. At acceptance, transfer that assertion's
   write ownership to the new stores; retained legacy rows become historical
   evidence or generated compatibility output. Never edit both versions. Pending
   legacy updates must be replayed and reconciled before transfer, not lost in a
   prolonged freeze.
6. **Select publication separately.** The manifest selects legacy/reconciled mode
   per typed subject, measure and perimeter. A reconciled combination requires
   complete ownership and dependency resolution for all contributors. Unresolved
   evidence can remain in the corpus but must block any unsupported claim or
   aggregate. Do not switch an entire country merely because some rows migrated.
   Changes to meaning may legitimately change counts or wording: accept those
   differences explicitly rather than force false equality with the MVP.

A country may finish migration with unresolved evidence and unavailable metrics.
Completeness here means every input has a documented disposition; it does not
mean every project is identified or every account can be closed.

## Website contract, publication and rollback

The compatibility adapter initially supplies the current public JSON fields from
accepted inputs. Add a versioned output contract and validate renderer/package
compatibility together. Candidate builds go to a separate output directory. A
package contains the matching HTML, JS, CSS, JSON/chunks, glossary, evidence index,
editorial content and descriptor; never replace a few live JSON files mid-build.
Local preview publication switches the complete accepted bundle. The existing
hosting ticket chooses the equivalent atomic mechanism for the eventual host.

Compare candidate and accepted output at semantic level: route/ID continuity,
country coverage, visible records, meaningful date roles, amounts/statuses,
source targets, editorial text and downloads. Record intentional changes with
source and reviewer rationale. Dynamic metadata may differ; that does not excuse
unexplained scientific differences. Add compatibility/browser fixtures for the
existing timing-bound and hardcoded-count follow-ups in 0727.

The homepage retains only the principal official source link; country pages add
latest official news since that reference, when available. Headlines and useful
summaries draw on the entire reviewed evidence set. Missing news or Vietnam's
imperfect principal reference remains explicit rather than silently replaced by
a secondary source. The migration does not label an old report as current merely
because it was recently acquired. Vocabulary definitions remain unobtrusive and
keyboard/touch accessible.

Every substantive claim has traceable evidence or a named derivation. Its display
identity is `(release_id, display_id)`, including repeated uses of a field on one
page, several routes or manuscript artifacts. Put detailed dependency data in
shared sidecars rather than duplicating it throughout country payloads.

**Rollback has two different meanings.** Before transfer, discard a candidate and
continue the legacy writer. After transfer, restore the last accepted complete
website package if publication fails; preserve newer evidence and its ownership.
Do not re-enable stale legacy writers or destructively reverse a migration to
recover the website. A restored edition shows its real cutoff. Later corrections
produce a new candidate edition.

## Research and existing-ticket handoffs

Research contracts enter the foundation through typed references, immutable
assertions/decisions, coverage attempts and schema fixtures. During country
migration preserve source-row populations, exclusions and external IDs now;
otherwise a later study cannot recover the sampling history.

Implement actual protocols, frozen frames, episode/coding exports and run/artifact
manifests with their consuming studies, not empty registries for every future
possibility. Before 0730 analysis, 0729 must settle the exposure/frame/endpoint
contract from 0735–0739 evidence. Before 0731/0732/0733 publish results, their
artifacts must resolve to frozen inputs and claims. Qualitative annotations and
contrary evidence stay independently recoverable. Reuse 0762/0763/0769 contracts;
no separate research database. A website release requires provenance for its own
claims, not completed causal or qualitative papers.

| Existing owner | Implementation handoff to add before its next execution |
|---|---|
| 0726 / #1334 | Consume country migration reports and 0768/0769 outputs; freeze dictionary, permitted downloads, exact-input descriptor and public replay. Retry and verify clean-cache retrieval of the previously unreplicated 0735 audit bundles before relying on them. |
| 0727 / #1335 | Preserve routes and filters; review two source roles, accessible glossary, chunk loading, real download completeness, timing/count follow-ups, desktop/mobile/keyboard behaviour. Hosting and live verification remain here. |
| 0728 / #1336 | Consume 0770 sweep/change records; nominate review owner and rehearse late report, correction, failed retrieval and restoration across two editions. No unattended publication. |
| 0729–0733 | Pin protocol/frame/coding/run dependencies at their scientific decision gates. Keep the historical closed-operation pool descriptive until a research design is accepted. |

These are proposed handoffs, not changes to existing ticket exit criteria or
claims of delivery. Update those tickets when this plan is adopted. Standards
mappings cover the vocabulary actually used in each slice; RDF services, general
ontology ingestion and whole-transition/PyPSA implementation remain outside it.

## Acceptance and completion

Each code ticket starts with its discriminating failing fixture, then runs the
repository's required local checks and applicable full pipeline checks before PR.
Website/output changes additionally run the browser exercise in
`tests/browser/jetp_observatory.py` against the candidate bundle. Existing unit
coverage is in `tests/test_jetp_observatory_mvp.py`; reuse and extend it where the
public contract belongs. Validation reports must cite exact inputs and commits.

The migration is complete when all existing tables have documented dispositions,
all four official inventories have coverage/disposition reports, writer ownership
is unambiguous, accepted published combinations satisfy the new contracts, and
the website has passed a two-edition replay/restoration exercise. Unsupported
metrics remain unavailable. Retire a compatibility path only after its last
consumer is migrated and retained editions still replay. Keep historical evidence
and crosswalks; do not delete them as cleanup.

This plan is checked for ticket dependencies, local references and alignment
with revision 5. The described migration/browser acceptance tests have not yet
been implemented or run as part of this planning task.
