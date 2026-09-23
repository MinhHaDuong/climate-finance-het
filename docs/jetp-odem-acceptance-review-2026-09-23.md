# JETP ontology, storage and migration: acceptance review against ODEM

Review of 23 September 2026. It reads the JETP ledger design against the ODEM
scientific cycle (`~/CNRS/projets/actifs/ODUM/conception/`, note and technical
appendix v2.0 of 22 September 2026) and against what the repository contains.
Inputs:

- `origin/main` at `d1f60f00`: [backend design, revision 5](jetp-backend-design.md) and its [implementation plan](jetp-backend-implementation-plan.md);
- PR #1449, not yet merged: `docs/jetp-ontology.md` (ontology v2, ten author decisions of 22 September), the revised backend design, and the migration train 0870–0879.

Ontology v2 supersedes sections 2–4 and 9 of the backend design, so this review
judges v2 and treats revision 5 as history. It changes no code, data or ticket.

## Verdicts

| Object | Verdict | In one line |
|---|---|---|
| Ontology (v2) | **Accept, with one required addition** | The line as the first-class unit matches ODEM's D exactly. The vocabulary itself is not yet versioned in time, so an as-of query cannot reconstruct the O that was in force |
| Storage (v2 §5, §10) | **Accept** | CSV in Git stays the record; SQLite derived is the validator and build engine; one file per table |
| Migration record (0760–0770) | **Correct the record** | Closed as done on 15 September, but ownership never left the legacy tables; v2 §8 already says so for 0762, 0768 and 0769 |
| Migration plan (0870–0879) | **Accept, with two sequencing fixes** | 0833 (M1b) and 0860 are built on the contract 0870 removes and must be re-scoped before either runs |

## 1. The four ODEM objects, and where the JETP ledger falls

ODEM writes the state of an inquiry as `S_t = (O_t, D_t, E_t, M_t)`:

- **Ontology**: concepts, categories, units and measurement definitions, with explicit revisions.
- **Data**: what was observed, with transformations, quality and provenance. Source documents sit in a separate register.
- **Evidence**: reproducible results and their interpretation as constraints. Each result is relative to a version of O, a snapshot of D and stated assumptions.
- **Models**: precise candidate causal mechanisms and research queries.

Queries, decisions and provenance persist as artifacts. They are not a fifth
component.

### Mapping of ontology v2

| Ontology v2 construct | ODEM object | Remark |
|---|---|---|
| Closed lists: line classification, `measure`, `basis`, `flow_type`, `modality`, date roles | **O** | Held in the DDL and `config/jetp_tracking.yaml`; extended "by decision recorded in `decisions.md`" |
| Shared status axes (OC4IDS, GEM, IATI) and sector (DAC purpose codes) | **O** | External lists pinned as the shared vocabulary |
| `status-crosswalk`, `sector-crosswalk` | **O** (measurement mapping) | Each maps a publisher's word onto a shared concept: ODEM's `Observable` → `Concept` link |
| `perimeters.definition` | **O** (population of a measurement) | Membership (`member_of`) is D |
| `marker-coefficients` | **O** (a rule, as v2 itself says) | Stored as a sourced record; it is a measurement convention, not an observation |
| Publishers, documents, retrievals, snapshots | **D register** (ODEM A4, "registre documentaire séparé") | |
| `lines`, `line-fields` | **D observations** | The unit ODEM calls an observation with provenance |
| `observations`, `timings` | **D** (transformations of lines by a named method version) | v2's "reading a line into observations is itself a method" is ODEM's transformation-with-provenance |
| `line-referents`, `relations`, `adjudications` | **D transformations recorded as decisions** | ODEM: decisions persist, never a fifth object |
| `coverage`, `dry-searches` | **D observation process** (ODEM `sampling_design`, quality report) | |
| Derived accounts, counts per perimeter, residuals | **E results** | v2 §5: computed at build time with run ID and two cutoffs |
| 0730 descriptive snapshot, 0823 figure | **E results** without constraint interpretation | |
| Reconciliation tiers 4–5 (model, then person) | ODEM §9 in miniature | The model proposes, the person decides, the record keeps both |
| Exposure, time zero, endpoints; causal acceleration | **M** | Empty: 0729 recorded DEFER. Legitimate in ODEM |

JETP is an **O + D + descriptive-E** system with an empty M. ODEM lists JETP only
as a later lead (note §7). Nothing in ontology v2 blocks that later use, because
the reconciliation record already has the shape ODEM asks of decisions.

### Two vocabulary points

1. **"Evidence" means documentary support in the JETP documents** ("the evidence layer", "evidence is the line"). In ODEM that is D's provenance. ODEM's E is the account or count computed from D. v2 has already retired "source"; one glossary paragraph in `jetp-ontology.md` §2 pinning "evidence" to documentary support would stop the two meanings from meeting in a paper that cites both.
2. **Stage 3 of the MVP holds two ODEM objects.** Referents and their observations are D; accounts and perimeter counts are E. v2 §7 names stage 3 "identities with their observations", which is D. The derived accounts need their own label when they reach a page. The 21 Viet Nam count slots show the difference: under v2 they become a perimeter with two `count` observations (D), and any total drawn from them is E.

## 2. Ontology v2: accept, with one required addition

**What ODEM confirms.** The four choices that carry v2 are the ones ODEM requires
of D:

- the published line as the unit;
- identities minted only by reviewed decisions;
- the publisher's word kept verbatim and mapped through a crosswalk, never overwritten;
- supersession chains with `recorded_at`, so that an as-of state at K is a query.

The closed lists of measures and flow types, and the ban on a script carrying a
rate, match ODEM's rule that a transformation references the measurement it came
from (A3).

**What is missing: O is versioned by editing, not by revision.** Every *record*
row carries `recorded_at` and `supersedes`. The *vocabulary* rows do not:

| Table | Columns in v2 §5 | Consequence |
|---|---|---|
| `status-crosswalk` | axis, shared_status, decided_at, decided_by, notes | No `supersedes`, no `status`, no `recorded_at`. Remapping `D. Completed` from `closed` to `finalisation` rewrites every past shared status |
| `sector-crosswalk` | purpose_code, decided_at, decided_by, notes | Same |
| `perimeters` | country, name, scope, definition, notes | A changed definition has no revision chain (revision 5 required a new ID; v2 dropped it) |
| Closed lists | DDL checks and `decisions.md` prose | A new value is logged, but an account does not record which list it was computed under |

ODEM's requirement (note §2.2, appendix A3 `OntologyRevision`) is that a result
never silently moves when a definition changes: the old result stays under its
old definition. For the ledger that means three small changes to v2 §5:

1. give `status-crosswalk`, `sector-crosswalk` and `perimeters` the same `recorded_at` / `status` / `supersedes` columns as the decision tables, and put them under the same in-force rule;
2. have the as-of algorithm read crosswalks at cutoff K like any other decision row;
3. have each derived account's run record carry the DDL hash and the crosswalk state it used, beside its two cutoffs.

That is the whole of ODEM's O discipline at this scale. It needs no ontology
server and no new table.

## 3. Storage: accept

v2 §10 settles storage well:

- CSV in Git remains the record, because adjudication happens by reading a diff;
- one DDL generates the headers and runs as the validator through a derived SQLite file;
- served views stay one JSON file per table (0858);
- a graph engine is rejected because every question is a fixed-length path.

ODEM's appendix proposes Parquet and DuckDB; at the volumes v2 projects (tens of
thousands of lines a year) SQLite over CSV answers the same need. The bulk
comparator lines (CRS, IATI) are reviewed by manifest rather than row by row,
which keeps the diff review where assertions are made.

One ODEM rule to keep in view: **a committed result never points at "latest"**
(A2). The frozen bundles pin their inputs by hash. The derived SQLite file must
carry the input commit and DDL hash in its build record, or an account computed
from it cannot be replayed.

## 4. The migration record: 0760–0770

The first migration train (opened 14 September 13:51, tracker closed 15 September
05:12) delivered:

- contract validators and fixtures (`scripts/jetp/_contracts.py`, `tests/test_jetp_contracts.py`);
- a source crosswalk;
- one staging JSON per country (`data/jetp/releases/{vnm,zaf,idn,sen}-migration-076x.json.dvc`);
- a reconciliation engine that returns "unavailable" for South Africa;
- release rehearsals under `data/jetp/releases/`.

It did not transfer ownership of any table. Each country document says so, for
example `docs/jetp-vnm-migration.md`: "Publication and write ownership remain
**legacy**". None of revision 5's canonical stores exists on `main`. 0760's
criterion "no duplicate authority" held only because nothing moved. v2 §8
acknowledges this for 0762, 0768 and 0769 ("closed on the previous contract").
The tracker's own log does not, and STATE reads as though the backend migrated.

Two effects are already live. First, the Viet Nam staging JSON was built from
14 September inputs, and 0854 has since added seven acquisitions. Second, M1a
reads that staging JSON (`scripts/analysis/jetp_observatory.mk`). Both resolve
under 0870: 0873 replaces the M1a builder, and v2 §5 keeps the frozen M1a release
as an archived edition.

## 5. When to migrate: phasing and tickets

The author settled the method on 22 September: design the target, then rebuild
from snapshots, with no incremental patching (v2 decision 4). The 0870 train
follows it in eight waves, each checked byte for byte against the served views.
The remaining question is ordering against the other open work.

| Work | Relation to 0870 | Recommendation |
|---|---|---|
| **PR #1449** | Precondition | Approve and merge it first; 0870 says "do not launch before approval" |
| **Ontology revision (§2 above)** | Changes three table contracts in v2 §5 | Amend v2 before 0871 freezes the DDL; adding columns later is a second migration |
| **0871–0874** (DDL, documents, lines) | Waves 0–3 | Launch right after approval. They are rebuilds of existing bytes and can run with little author attention |
| **0833, M1b catalogue** | Written on revision 5: `same_as` / `component_of` rows and a `possible_matches` table | Same content as v2's `line-referents` and `relations` with `status = candidate`. Re-scope it as the acceptance of 0875 plus reconciliation tiers 1–2, and block it on 0875. Running it now builds on tables that 0878 removes |
| **0860, serve every table** | 0870 says it is "absorbed"; 0860 is still open with its own children | Close it as absorbed, or block it on 0877. Its first child serves `project-coverage.csv`, which v2 folds into `coverage`, and turns the 21 slots into perimeter observations |
| **0875–0877** (identity split, observations, perimeters) | Waves 4–6 | These need the author: 61 funder strings to split into funder and channel, a subject review for 71 implementation rows. Schedule them against the REL review due around 6 December |
| **0859, collect two Viet Nam sources** | Independent | Any time. It adds retrievals, which wave 1 carries over |
| **Models** | None | If a causal design survives 0729, an ODEM prototype consumes a frozen JETP edition. Nothing in 0870 is needed for that |

**Why start the first waves now rather than after M1b.** Every legacy edit
between now and wave 1 has to be replayed. 0854 already added seven acquisitions
after the first staging, and 0859 will add two more. Waves 0–3 only re-read bytes
that exist. They add no author load and stop the replay debt from growing.

**Ticket work proposed (none filed):**

1. **0760:** a log note recording that it delivered contracts and staging candidates, that ownership stayed legacy, and that 0870 is the migration.
2. **One amendment ticket, or an edit inside PR #1449**, for the §2 additions: revision columns on the two crosswalks and on perimeters, and the O reference in account run records.
3. **0833:** restate it in v2 terms and add `Blocked-by: 0875`.
4. **0860:** close it as absorbed by 0870, or add `Blocked-by: 0877`.
5. **STATE:** "contracts and staging done in September; ownership legacy; migration is 0870, pending approval of #1449".

## 6. What this review did not check

- It does not re-run the contract tests, the release rehearsals or the DVC hashes.
- It reads the six v2 review reports only through v2's own summary of them.
- It does not judge ODEM itself. ODEM is a preproject with no prototype, so the comparison is about concepts, not software.
- Row counts come from ticket bodies and from v2 §6, dated 14–22 September.
