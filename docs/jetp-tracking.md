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
| Project follow-up | `data/jetp/project-coverage.csv` | git | One direct-source review verdict per canonical project, preserving pending and dry searches |
| Indonesia grant observations | `data/jetp/idn-portfolio-observations.csv` | git | One official-portal row per financing modality, reconciled without overwriting the 2025 report value |
| Viet Nam pilot manifest | `data/jetp/vnm-pilot-manifest.csv` | git | Lossless staging of all 66 pilot collection attempts before canonical source reconciliation |
| Viet Nam pilot observations | `data/jetp/vnm-pilot-observations.csv` | git | All 46 pilot evidence rows joined to their verification verdicts; unresolved human ratifications remain blank |
| Plan-project lines | `data/jetp/plan-projects.csv` | git | Every row in an official plan or pipeline, with explicit canonical reconciliation |
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

## Country checkpoints

| Country | Project review | Current checkpoint |
|---|---:|---|
| South Africa | 263/263 | Complete; register, reports, project pages and dry searches reconciled |
| Indonesia | 74/74 | Complete; 66 collected, 6 central-only after explicit search, 2 archive-blocked |
| Viet Nam | 24/24 July 2025 records | 3 named projects followed to direct MOIT and funder sources; 21 identities explicitly not published |
| Senegal | 43 project/programme records reviewed | 49 plan lines retained; 20 direct corroborations, 20 central-only reviews and 3 blocked ASER routes as of 13 September 2026 |

The Indonesia checkpoint includes 53 approved projects in the 30 November 2025
portfolio snapshot (9 loan or equity projects and 44 grants), 20 finance-pipeline
entries including AICET, 1,579 plan rows, and all 14 CMEA monitoring entries.
The earlier March 2025 total of 54 projects is preserved as a separate dated
observation rather than overwritten.

The Viet Nam staging tables preserve the pilot's 54 successful collections,
8 blocked requests and 4 unlocated documents as distinct outcomes. They also
encode the July 2025 count of 24 total projects separately from the 17 newly
screened proposals; neither count is inferred from the other. Pilot verdicts
do not constitute author ratification, so the original blank ratification field
is retained pending explicit decisions.

The official Viet Nam corpus adds the 248-page Vietnamese RMP, the signed
decisions 1009/QD-TTg and 458/QD-TTg, and all thirteen MOIT JETP newsletters
published for March 2025 through March 2026. The date of Decision 458 is coded
as 20 March 2026 from the signed text and current MOIT portal, correcting the
pilot note that reported 23 March. Decision 1929/QD-BCT is confirmed by dated
official-operator news, but its signed full text was not exposed by the JETP
document index, portal search or ministry legal register at this checkpoint;
that gap remains a dry-search observation rather than an inferred document.

The July 2025 Viet Nam portfolio is represented by 24 source-bounded records.
MOIT and the IPG co-chair account name Bac Ai pumped storage, the Binh Duong
and Dong Nai transmission investments, and the Tri An expansion. Direct MOIT,
EVN and EIB pages are linked to those three records. The same official account
describes the other 4 initial projects and 17 newly screened proposals only by
count. Those 21 rows are therefore explicit count slots with
`not_published` follow-up verdicts, not invented project identities. The
current MOIT index still exposed only the three named profiles when checked on
12 September 2026.

ADB and British International Investment are covered without forcing their
climate-finance leads into the strict 24. ADB project pages 55327-001 and
58382-001 were located but remained blocked to automated collection; the
accessible ADB VinFast announcement predates the JETP and contains no strict
portfolio attribution. BII and VPBank directly confirm BII's USD 50 million
share of a USD 350 million sustainable-finance facility, but neither page calls
it a JETP project. The September 2026 IATI publisher profile for BII reports no
valid activity rows, so it cannot supply the missing crosswalk. These are
terminal authority verdicts and explicit dry searches, not project matches.

The Senegal checkpoint starts from the 2023 political declaration and the
354-page 2025 investment plan, not from an OECD cut-off. Annex 2 contributes
38 numbered projects received for evaluation, while the main plan separately
identifies eleven quick wins. Neither cohort is treated as approved finance or
physical implementation. The main-plan statement that 34 projects were
collected and the annex's 38 numbered submissions remain two dated claims, not
one silently repaired total. The plan itself also names quick win 11 as 2,000
hybridised boreholes on pages 33 and 354 but as 1,000 solarised boreholes on
page 78; the ledger retains that internal conflict for later adjudication.

The 13 September follow-up preserves all 49 plan lines and reconciles six
quick-win identities with submissions. QW1 groups the two 50 MW Senelec
projects (Annex 2 submission 15), as the main plan states on printed page 53.
QW5, QW6, QW7, QW9 and QW11 match submissions 11, 17, 19, 16 and 20.
QW4/PUELEC remains a separate programme: printed page 240 places the
600-village submission among several components. The 43 records therefore
include both programmes and components; their budgets and capacities must
not be summed without selecting a consistent level of aggregation.

The newly collected Annex 8 explicitly limits its evaluation to 34 proposals
from public promoters. This is recorded as an additional source claim;
the main plan's wording and the 38-submission Annex 2 table remain intact.
Annex 8 renumbers the public proposals, so its ordinals cannot be joined
directly to Annex 2 ordinals.

Direct evidence includes AEME programme pages and its 2023 report, ANER's
public project API and 2026 magazine, Senelec procurement documents, an
AFD Diass-storage factsheet, and a UASZ study of a component of Senelec's
Village Ecole Vert. Title-only AEME pages establish programme identity;
they do not establish delivery. ANER's generic `ongoing` label for solar
pumps remains a source claim, without being translated into construction,
commissioning or a delivered-pump count.

The Saloum notice supports procurement of 11 PV/BESS plants serving 18
villages. Its renewable-energy target remains a target. Its monetary bidder
qualification thresholds are not financing amounts. Diass's reported KfW
and AFD contributions remain undated financial observations in the extended
perimeter, without an inferred agreement or disbursement. The 2018 date on
the factsheet describes technical assistance, not the battery's commissioning.
The unconfirmed AFD–Senelec EUR 670 million figure remains excluded.

The [managed Senegal research rounds](jetp-senegal-managed-rounds-2026-09-13.md)
add four bounded distinctions. Senelec's mobility-electrification master-plan
procurement is a provisional Annex 35 preparation candidate and leaves its
coverage `central_only`. An archived ANER procurement notice preserves a
feasibility-study route for public-building autonomy without identifying the
whole Annex 23 submission. ARCOP identifies the two contracts behind the
reported PUELEC component, while issued advance-payment orders remain short of
settlement proof. BOAD's FCFA 41.5 billion approval is for partial financing of
the single Linguère plant; absent a Champions Nationaux ownership crosswalk or
JETP/IPG attribution, it remains context rather than QW2 finance.

Every remaining project has a dated route and explicit gap in
`project-coverage.csv` and `dry-searches.csv`. Related programmes, earlier
pilots and geographically similar developments are provisional leads, not
identity matches. Full prequalification and feasibility documents available
only on request remain gaps; no request email was sent. See
`docs/jetp-recovery-2026-09-13.md` for recovery and remote-byte verification.

The resumed pass adds a Senelec-reported Diass construction launch and IFC
advisory project 609428 for the BioGNV plant. The ledger now holds 34 plan
needs/estimates and five reported funding observations for Senegal; these
are separate observations, not an additive financing total. All 43 identities
have a plan/implementation baseline. The allocation table on printed page 46
reverses the QW5/QW6 labels, so amounts are joined by title. See the complete
[Senegal review](jetp-senegal-review-2026-09-13.md) for every project's evidence
and limitations. Twenty-four identities still lack a confirmed direct page.

## Counting rules

- A project and a financial event are different objects. A project may have
  many funders, instruments, dates and status layers.
- A plan-project line is also distinct: `plan_only` preserves a project listed
  in an investment plan without implying observed finance or implementation;
  `matched` records only a reviewed link to a canonical project identity.
- `priority` and `top_priority` reproduce the source plan's ranking (including
  coloured-cell coding); they do not imply finance or physical advancement.
  Extractors number physical rows consecutively and retain any printed row-number
  anomaly in the locator and notes, so no line is dropped or silently repaired.
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

The [13 September scout trial](jetp-senegal-scout-trial-2026-09-13.md) covers all 24 previously unresolved identities and corroborates one PUELEC component; 23 direct-source identities remain unresolved.

The later [managed rounds](jetp-senegal-managed-rounds-2026-09-13.md) refine
those leads without revising the historical trial counts: the checkpoint remains
20 collected, 20 `central_only`, three blocked and 23 unresolved direct identities.
