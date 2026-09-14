# JETP design-feasibility pilots: fresh-session handoff

Checkpoint: 14 September 2026. **Source discovery is sufficient to compare concrete
designs; a defensible primary causal design is not yet selected.** The author
requested a checkpoint now and pilot execution in a fresh session. No pilot,
effect estimate, institutional outreach or merge is launched by this handoff.

## Tomorrow's prepared protocol

For the 15 September session, use the [common protocol](jetp-pilots/2026-09-15/protocol.md)
and frozen lender briefs: [AFD](jetp-pilots/2026-09-15/afd-brief.md) (0737),
[KfW/BMZ](jetp-pilots/2026-09-15/kfw-brief.md) (0738), and
[FCDO](jetp-pilots/2026-09-15/fcdo-brief.md) (0739). These additions supersede the
sketches below wherever more specific. They fix the diagnostic country set,
baseline sensitivity grid, deterministic documentary selection, deliverable
schemas, acquisition allocation and GO/NARROW/DEFER rules. No pilot is scheduled
or launched by this preparation.

Recommended staffing: Sol at high effort leads; Terra at high effort may own a
bounded lender pilot. Use an independent Sol/Astra scientific review before
causal-design selection. The protocol records the recommendation's basis and limits.
Historical membership, not export size, remains the principal feasibility risk.
A missing denominator is an admissible DEFER result. Carry forward all seven
AFD award/signature reversals. First-payment intervals need verified earlier
coverage. Synthetic-control and support-allocation candidates remain deferred,
not rejected by their absence from the first-wave comparison below.

Read-only preflight on 14 September verified both open PR heads against local
clean worktrees, all 33 round-3 SHA-256 entries (406,032,031 bytes), and both
round-2/round-3 DVC object sets in both local caches. The audit Python environment
imports successfully and the existing AFD checker reproduces pivotal counts.
Remote DVC recovery was not retested; two local caches are not off-machine backup.
The preparation commit follows audit head `84904ef4`; resolve it at launch.

## Resume here

1. Read this handoff, [round-3 decision memo](jetp-audits/0735/round3/report.md),
   [AFD reconciliation](jetp-audits/0735/round3/afd/report.md), and the selection
   audit in PR #1348 (`docs/jetp-audits/0736/report.md`, chronology/comparators/rivals).
2. Read `tickets/0729-jetp-lifecycle-feasibility.erg` from PR #1348 and
   `conception/jetp-causal-design-options-2026-09-14.md`. The prior Astra/Claude
   discussion is an options portfolio, not a selected design.
3. Check live PR heads and local worktrees before editing. Evidence and updated
   design tracker are on separate open branches; main alone is not this checkpoint.
4. Freeze pilot briefs **before** any new retrieval. Round 3 wrote briefs late;
   do not repeat that sequencing error or call those briefs preregistered.
5. Launch AFD first. KfW and FCDO may run independently in parallel if authorized;
   defer JICA and USAID expansion until the first pilot wave is assessed. Use
   separate ticket-sized assignments/worktrees, linked under 0735 and 0729.

## Repository and publication state

| Item | Checkpoint |
|---|---|
| Audit PR | [#1347](https://github.com/MinhHaDuong/climate-finance-het/pull/1347), open; research head before this handoff `d1b1da6813841c3c0a5ba36bf661317c42db6460` |
| Audit checkout | `/tmp/jetp-audit-0735`, branch `t0735-historical-pipeline-audit`; handoff/state commit follows that research head |
| Selection/design-tracker PR | [#1348](https://github.com/MinhHaDuong/climate-finance-het/pull/1348), open; head `63bb738ef8f8bf7c96db3201a8ce48b717136075` |
| Selection checkout | `/tmp/jetp-audit-0736`, branch `t0736-selection-timing-audit` |
| Main at checkpoint | `bbb3a2152a142bb88dc11b4538f5335af092f883`; check for later work before integration |
| Historical audit issue | 0735 / [#1345](https://github.com/MinhHaDuong/climate-finance-het/issues/1345) |
| Selection audit issue | 0736 / [#1346](https://github.com/MinhHaDuong/climate-finance-het/issues/1346) |
| Design tracker | 0729 / [#1337](https://github.com/MinhHaDuong/climate-finance-het/issues/1337), depends on both audits |
| Release/replication | 0726 / [#1334](https://github.com/MinhHaDuong/climate-finance-het/issues/1334) |

Both PRs have scientific audit checks; this does not substitute for the full
merge gate. Do not infer merge permission from a checkpoint request. Reuse
existing commits rather than recreate the audit. Main's untracked `data/book/`
is pre-existing user material and must remain untouched.

## First wave: bounded questions and acceptance tests

### AFD — first priority

**Question:** which pre-exposure country/sector/instrument cohorts and stage
transitions can be reconstructed with stable membership and date definitions?
Start with acquired files, not another broad web search. Maximum 30 new external
request units for missing specifications/records; stop earlier if the discriminating
source is unavailable and state exactly what decision remains blocked.

Current portal: 3,277 financing IDs. Seven-country XML: 317 financings under 225
projects; retains 223/224 legacy financings. The missing CMA123501 has no recorded
legacy first payment and zero reported cumulative payment. Across the full portal
comparison, 19 legacy IDs disappear. CTN129703 has a missing current signature
proxy; CZZ276103 changes date. Retained legacy zero-payment cases are not all
currently unpaid: 24 now report payments and six have no type-3 entries.

First documentary test: disappearance of CMA123501 must produce **loss of
visibility**, not cancellation or continued unpaid status. First date test:
period-end XML entries cannot pass as exact first-payment days. All 223 matched
signatures agree; none of 193 populated legacy first-payment dates equals the
minimum XML payment date. Award-like `value-date` matches populated legacy awards
but supplies generation-like dates for missing awards; do not fill that gap.

Deliver: reconcile missing IDs/date nonmatches; define finance/project joins,
loan/grant and policy/investment strata; establish source inclusion/retention and
older snapshot availability. Produce counts by country, sector, instrument,
entry cohort and observable stage, with missingness, calendar coverage and
loss-to-observation. Define possible baseline populations before examining
outcomes. Do not label retrospective coverage a contemporaneous census.

### KfW/BMZ — complementary population and period pilot

Use the acquired complete XML and exact agency reference `XM-DAC-5-2`.
4,036 activities include closed and finalising cases; this is not 4,036 loans.
Maximum 20 new external units for publisher semantics and historical/legal joins.

First tests: Country and Region downloads are byte-identical and cannot double
the population; quarter-end or reporting-date disbursements cannot pass as exact
first-payment days. Identical planned/actual starts do not establish zero delay.
Reconcile a fixed historical contract cohort, signed-since-2013/ongoing-in-2013
inclusion, cancellation retention, and commitment/start meanings. Return eligible
counts and period-resolution limits; keep BMZ mandates separate from other KfW.

### UK FCDO — earlier-stage documentary pilot

Use the acquired catalogue of 7,327 programmes and 17,955 components. Freeze
hierarchies separately. Maximum 20 new external units for business cases,
approval/procurement histories and source retention rules.

First tests: parent dates cannot replace component dates; historical expenditure
in GB-1-112151-101 prevents its later first type-3 record being interpreted as
first spending. Include pipeline and completed cases; current pipeline status
is not a verified approved-but-unsigned financing stage. Seek business-case
approval, procurement initiation/award and start evidence at a coherent unit.
Return document coverage and reproducible stage mappings. This scope is
FCDO/legacy DFID, not every UK institution.

## Design-selection checkpoint after the first wave

Compare three candidates without choosing based on an attractive effect:

| Candidate | Required discriminating evidence |
|---|---|
| Acceleration of an incumbent project population | Membership and maturity before plausible anticipation; unfinished/disappeared cases; consistently observed transitions |
| Changes in new financing/signature throughput | Stable cohort disclosure, usable pre-periods and comparable country populations; amendments and components not counted as new projects |
| Energy/non-energy differences across countries and time | Credible sector trends and administrative comparability; spillovers, concurrent reforms and selection cannot be assumed away |

The pilot output must report sample counts and stage definitions, baseline date
alternatives from the selection audit, pre-treatment coverage/trend diagnostics
where justified, comparator overlap, censoring/retention problems and likely
country-level uncertainty. Country conditions **plus project matching** remain
the user's intended comparison basis. Matching alone does not establish causality;
many projects do not create many independent treated countries. Negotiation,
declaration, plan release and actual intervention dates stay distinct. India is
not automatically untreated. A causal design may be narrowed or rejected with
explicit reasons; no blanket rejection merely because allocation was nonrandom.

JICA follow-up: reconstruct an older annual signing cohort, separating amendments
and phases, then link originals regardless of completion. USAID follow-up:
project/award ID crosswalk and accounting granularity in a project-focused country
slice; the acquired 190-activity administrative XML contains 2015–2017 financial
dates despite 2026 generation. Neither is a reason for immediate bulk expansion.

## Storage and verification

Markdown reports and JSON/CSV audit profiles are versioned in Git. Original
bytes remain separate DVC audit bundles; canonical ledgers and website totals
were not changed. Round 2 has eight payloads; round 3 has 33 payloads/response
artifacts, 406,032,031 bytes, with SHA-256 manifest and explicit partial-CSV label.
Use `data/jetp/audit-evidence/0735-round2.dvc` and `0735-round3.dvc`.

Round-3 DVC status is clean; all 34 cache objects including directory metadata
are hash-verified in both worktree and primary checkout caches. The configured
padme remote refuses `127.0.1.1:22`: **remote retrieval is not guaranteed**.
Preserve caches/worktrees until replication or another verified recovery path.
Do not mistake the Git pointer for a public data release. Reuse acquired bytes
before downloading large files again. Source scripts under `/tmp/jetp-round3-*`
are temporary calculations, not the authoritative production pipeline.

Audit checks: 1,549 fast tests passed (12 skipped), 330 adherence checks passed
(15 skipped), all JSON/CSV parsed and archive hashes matched. Independent AFD and
synthesis reviews reproduced pivotal counts; precision fixes were applied.
See `docs/jetp-audits/0735/round3/verification.md`. No CI runs on GitHub.

## Programme remains two tracks

Observatory: citable release 0726 → hosted website 0727 → monthly editions 0728;
aggregate evidence and comparison browsing remain required, not only dossiers.
Academic work: feasibility/design 0729 → analysis 0730 → short paper 0732;
data paper 0731 follows a citable release; long paper 0733 with Christophe.
The website and data paper do not depend on finding acceleration. Construction
speed is not the near-term JETP outcome. No publication text or estimator is frozen.

## Suggested fresh-session instruction

> Resume the prepared 15 September pilot protocol from the updated PR #1347.
> Read docs/jetp-pilots/2026-09-15/protocol.md and ticket 0737; use the pinned
> selection/design inputs from PR #1348. Sol at high effort leads. Launch AFD
> first in a fresh worktree; independent Terra agents may execute tickets 0738
> and 0739 in their own worktrees. Before retrieval, verify input hashes and
> commit the deterministic selection and route list. Return the common
> feasibility matrix and an independent scientific review; stop before primary
> estimation or merging. JICA/USAID expansion remains deferred.
