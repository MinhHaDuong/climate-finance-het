# JETP ontology, storage and migration: acceptance review against ODEM

Review of 23 September 2026, on `origin/main` at `d1f60f00`. It reads the
[backend design, revision 5](jetp-backend-design.md) and the
[implementation plan](jetp-backend-implementation-plan.md) against the ODEM
scientific cycle (`~/CNRS/projets/actifs/ODUM/conception/`, note and technical
appendix v2.0 of 22 September 2026), and against what the repository actually
contains. It changes no code, data or ticket.

## Verdicts

| Object | Verdict | In one line |
|---|---|---|
| Ontology | **Accept with a required revision** | Rich semantics for identity, time and money, but never made a versioned object of its own; M1b is where it must become one |
| Storage | **Accept** | Git CSV + DVC bytes + static JSON in normal form fits the scale and matches ODEM's register/snapshot split |
| Migration | **Not accepted as a migration** | 0760–0770 delivered contracts and staging candidates; no table changed owner, and the tracker's completion criteria were met vacuously |

## 1. The four ODEM objects, and where the JETP stages fall

ODEM writes the state of an inquiry as `S_t = (O_t, D_t, E_t, M_t)`:

- **Ontology**: what we talk about and how we measure it, meaning concepts, categories, units, measurement definitions and revisions.
- **Data**: what was actually observed, meaning observations, samples, transformations, quality and provenance. Source documents sit in a separate register.
- **Evidence**: what restrictions the observations support, meaning reproducible results and their interpretation as constraints. Each result is relative to a version of O, a snapshot of D and stated assumptions.
- **Models**: which causal explanations remain possible, meaning precise candidate mechanisms and research queries.

Queries, decisions and provenance persist as artifacts. They are not a fifth
component.

### The vocabulary collision

The JETP documents use **"evidence"** for documentary support: an
`evidence-links.csv` row ties an assertion to exact bytes and a locator, and a
"frozen evidence edition" is a released package of reviewed inputs. In ODEM terms
that is **D's provenance** and a **D snapshot**, not E. ODEM's E is the result
computed from D (an account, a count with its perimeter, a descriptive table) and
its interpretation. Left unresolved, the collision will put the reconciled accounts
and the source links in the same drawer, and they obey different rules. A source
link is true or false about a document. An account is correct *relative to* a
metric, a perimeter, a coverage decision and an evidence cutoff.

The same applies to "layer" (0832), "étage" (0834) and "stage" (STATE, M1a pages),
which denote the same three things. None of the three words is ODEM's.

### Mapping table

| JETP construct (design rev. 5 / MVP) | ODEM object | Remark |
|---|---|---|
| Record kinds, measures, `value_type`, `basis`, `amount_basis`, missingness vocabulary | **O** | Exists partly in `config/jetp_tracking.yaml` (`version: 1`, 98 lines) |
| Metric dictionary, application profile, SKOS/IATI mappings | **O** | Proposed; `config/jetp-application-profile.yaml` does not exist |
| Perimeters, counting unit, classification level | **O** (MeasurementSpec: population, unit) | Design §3 is strong here; this is O content labelled as data |
| Entity *categories* (project, programme, component, count slot) | **O** | The category list is O; the claim "entity X is a programme" is D |
| Stage 1: documents, `manifest`, `sources` | **D register** (ODEM A4 "registre documentaire séparé") | Implemented, DVC by hash |
| Watches, sweeps, checks, `project-coverage`, `dry-searches` | **D observation process** (ODEM `sampling_design`, quality report) | Coverage is D, not working notes. That is the right frame for 0860 |
| Stage 2: M1a inventories, events, implementation events, positions | **D observations** | Row-level provenance present |
| Identity decisions: `same_as`, `component_of`, occurrences, adjudications | **D transformations**, recorded as decision artifacts | Not E. They define the population, they are not results about it |
| Stage 3a: canonical catalogue (M1b) | **D** (curated snapshot) | Currently merged with 3b under "faits réconciliés" |
| Stage 3b: counts, accounts, residuals, country aggregates | **E results** | Each needs its O version, D snapshot and assumptions (coverage completeness, perimeter) |
| "Account unavailable" (0768 ZAF) | **E status** | Same logic as ODEM's `not_applicable` / `not_evaluated`: not a rejection |
| 0730 descriptive snapshot, 0823 figure | **E results** without constraint interpretation | Correct as they stand |
| Editorial claims, website sentences | **Publication of E**, outside ODEM | The provenance index is the journal |
| Study protocols: exposure, time zero, endpoint, horizon | **M** (ResearchQuery) | The design places them in D stores |
| Causal acceleration hypothesis, selection mechanisms | **M** | Empty: 0729 recorded DEFER |
| `recorded_at`, evidence cutoff `K`, supersession | Versioning of `S_t` | JETP's bitemporal rule is stricter than ODEM's and should be kept |

**The clarified picture.** JETP today is an **O + D + descriptive-E** system with
an empty M, and that is a legitimate state in ODEM. ODEM itself lists JETP only as
a later lead (note §7). The three stages cover D and part of E. Ontology has no
stage at all, and that is the gap.

### Consequence for stage 3

"Faits réconciliés" (0834) holds two kinds of object that ODEM keeps apart:

- **3a, catalogue (D):** canonical records and the relations between them. These are wrong if a relation lacks its source.
- **3b, measures (E):** counts, amounts and accounts. These are wrong if they lack their perimeter, coverage or metric version.

The "21 unpublished" of Viet Nam shows the difference. The count is an E result
(an official count within a source-defined perimeter). Its 21 coverage rows are
D (observation process). 0860 serves the D so that the reader can check the E.
The M1a pages and 0833 should name 3a and 3b separately.

## 2. Ontology: accept with a required revision

**What is good.** The identity, time and money semantics are the best part of the
design:

- typed references;
- half-open validity intervals;
- the ban on summing across hierarchy levels;
- a perimeter declared before any count;
- decimals in whole currency units;
- a distinction between "unknown" and zero;
- separate date roles and bounds.

On all of these the design is ahead of ODEM's appendix A3, which says nothing
about perimeters or evidence cutoffs.

**What is missing.**

1. **O is not a versioned object.** ODEM requires `OntologyRevision` (before, after, change kind, rationale, mapping, affected references), and requires every E result to cite an O version. The design only says "breaking schema/meaning changes require version increments, crosswalks and release notes" (§6). `jetp_tracking.yaml` carries `version: 1` and has never had a revision record.
2. **O is scattered.** Measures live in `jetp_tracking.yaml`. Categories live in `jetp_observatory.yaml` and the migration configs. Perimeters are planned as a *data* table (`perimeters.csv`). Mappings are planned in an application profile that does not exist. ODEM's discipline, "one definition per concept", is stated in the design (§2) but not implemented.
3. **Perimeter sits in the wrong column.** A perimeter's *definition* (what a "JETP-strict IPG pledge" means) is O. Its *membership* (`member_of` rows) is D. The design puts both in D, so a changed definition would look like a data correction.

**Required revision (design rev. 6, short):**

- a glossary that pins "evidence" (JETP: documentary support), "stage", "catalogue" and "measure" against ODEM;
- the O/D split for perimeters;
- an `OntologyRevision` contract, so that each E result cites the O version it was computed under.

No rewrite of sections 3–8 is needed.

## 3. Storage: accept

The choices hold up against ODEM and against actual use:

- Git CSV for reviewed tables;
- DVC by content hash for source bytes;
- generated static JSON;
- SQLite deferred;
- one file per table with joins at read time (0858).

ODEM's appendix proposes Parquet and DuckDB for observations. At 300 to 2,000 rows
per table that buys nothing. The design's own trigger list (§12: measured build
cost, file size, concurrent edits, access control) is the right test, and none of
its conditions has fired. The one pressure point is payload size: `ZAF.json` sits
at about 509 KB under a 512 KB cap. The normal-form sidecars of 0855 and 0858 are
the correct answer, and they need no database.

One requirement carries over from ODEM: **a committed result never points at
"latest"** (A2). The static bundle already pins its inputs by hash. The staging
artifacts do too. The legacy CSVs do not: the live website reads
`data/jetp/*.csv` at whatever commit it is built from.

## 4. Migration: not accepted as a migration

**What was delivered (14–15 September, 0761–0770).** The migration tickets were
opened at 13:51 and the tracker closed at 05:12 the next morning. They delivered:

- contract validators and fixtures (`scripts/jetp/_contracts.py`, `tests/test_jetp_contracts.py`, `tests/test_jetp_evidence_contracts.py`);
- a source crosswalk (`data/jetp/releases/source-crosswalk-0763.json.gz.dvc`);
- one **staging** JSON per country (`data/jetp/releases/{vnm,zaf,idn,sen}-migration-076x.json.dvc`);
- a reconciliation engine that returns "unavailable" for South Africa (`docs/jetp-zaf-gross-disbursement-0768.md`);
- source-watch configuration (`config/jetp-source-watches.yaml`);
- release rehearsals under `data/jetp/releases/2026-09` to `2026-11-r1`.

**What was not delivered.** None of the canonical stores in design §2 exists:

- no `reported-positions.csv`;
- no `evidence-links.csv`;
- no `adjudications.csv`;
- no `agreements.csv`, `occurrences.csv`, `entity-relations.csv` or `perimeters.csv`;
- no `source-editions.csv`, `edition-snapshots.csv` or `source-checks.csv`.

Each country document says so plainly. For example, `docs/jetp-vnm-migration.md`
reads "Publication and write ownership remain **legacy**", and
`docs/jetp-zaf-migration.md` says the same. The website is built by
`scripts/jetp/build_observatory.py` from the nine legacy tables.

**Why the tracker could close.** The plan's step 5 is "transfer ownership once",
and 0760's criterion is "writer ownership and publication selection have no
duplicate authority". That criterion holds only because nothing was transferred:
it is an all-clear that does not distinguish "migrated cleanly" from "never
migrated". The same goes for "every legacy row has a disposition": the disposition
is "retained authority".

**Two consequences that are already live:**

1. **Staging has drifted from legacy.** The Vietnam candidate was built on the 14 September inputs. Since then 0854 (22 September) added seven Vietnamese acquisitions to `manifest.csv`. The plan warns that "pending legacy updates must be replayed and reconciled before transfer". Every legacy edit since the 14th adds to that replay.
2. **A staging artifact has acquired a consumer.** `scripts/analysis/jetp_observatory.mk` makes the M1a inventories depend on `data/jetp/releases/vnm-migration-0764.json`. M1a, now accepted, therefore reads an artifact that the plan defines as "unadmitted staging, not a canonical store". That is harmless while the artifact is frozen, but it is a second read path with no owner.

This is not a defect in the design. The plan chose to migrate behind a
compatibility boundary, and the boundary works: the MVP never broke. The defect
is in the status record. STATE, 0725 and 0760 read as though the backend has
migrated, and it has not.

## 5. When to migrate: phasing and tickets

**Principle.** Transfer ownership one table at a time, at the moment a product
needs a property the legacy table cannot carry. Do not transfer on a calendar and
do not transfer everything at once. The design's slices remain valid. What
changes is the trigger.

| Milestone | What the product needs | Table that changes owner | ODEM object |
|---|---|---|---|
| **M1a close (now)** | Nothing new | None | — |
| **0860, serve every table** | Show coverage, claims, timing verbatim | None: serve the legacy tables as they are | D (observation process) made visible |
| **M1b (0833)** | Relations with source and locator; a frozen taxonomy | **First real transfer:** `entity-relations.csv` (with `possible_matches` beside it) becomes canonical. The taxonomy lands as versioned O | O v1 + D catalogue |
| **Design rev. 6** | Glossary, perimeter split, `OntologyRevision` | None (documentation) | O |
| **M2, live monthly refresh** | Knowing what was known when; corrections without overwriting | `sources` + `manifest` → source revisions, acquisitions, editions and checks (the 0763/0770 contracts). Then assertions country by country, starting with Viet Nam: `events` → `reported-positions` + `evidence-links` | D with bitemporal versioning |
| **First paper claim on an account** | A reconciled figure with residual | `agreements`, `occurrences`, `adjudications` for that one subject | E |
| **A causal design survives 0729** | Queries, candidate mechanisms | None in JETP: M belongs in an ODEM prototype that consumes a frozen JETP edition | M |

**Why M1b is the right first cut.**

- 0833 already requires relations with source ID and locator, a deterministic ID rule, and byte-identical M1a. That is the design's `entity-relations.csv` contract, applied to a table that has no legacy writer to replay.
- It is the only transfer with zero replay cost.
- Its taxonomy is the first moment where O becomes an explicit, frozen object.

**Why M2 is the trigger for the heavier transfers.** The evidence-cutoff machinery
(design §6) exists to answer "what did the system know on date K". A single
edition never asks that question. The first monthly refresh that has to correct a
published figure does. Before then, the bitemporal stores would be carrying a
property that nobody reads.

**Proposed ticket work** (none filed yet):

1. **0760: record the actual state, do not reopen it.** Add a log note saying it delivered contracts and staging candidates, that ownership stayed legacy, and that its criteria 1 and 3 were met by "retained" dispositions.
2. **New tracker, "backend cutover by table"**, with one child per row of the table above. Each child is `Blocked-by` its real product trigger (0833, the first M2 refresh), never by the tracker.
3. **Amend 0833:**
   - its taxonomy is O v1, versioned, with a revision record;
   - `entity-relations.csv` is its canonical output under the design §3 contract;
   - it names catalogue (3a) and measures (3b) separately.
4. **One design rev. 6 ticket** (documentation): glossary, perimeter O/D split, `OntologyRevision`.
5. **Staging artifacts:**
   - declare the four `*-migration-076x.json` frozen at their 14 September inputs;
   - regenerate them at cutover rather than keeping them current;
   - give the M1a dependency on `vnm-migration-0764.json` an explicit note in `config/jetp-m1a-inventories.json`, so that its cutover plans for it.
6. **STATE and 0725:** replace any wording that implies the backend migrated with "contracts and staging done; ownership legacy; first transfer at M1b".

## 6. What this review did not check

- It does not re-run the contract tests or the release rehearsals.
- It does not verify the staging artifacts against their DVC hashes.
- It does not judge ODEM itself. ODEM is a preproject whose prototype does not exist, so the comparison is about concepts, not software.
- The row counts cited come from ticket bodies and documentation dated 14–22 September, not from a fresh count.
