# JETP pilot protocol for 15 September 2026

Prepared 14 September 2026. Phase: Plan. No pilot launched. This protocol and
three ticket briefs are to be committed before new JETP retrieval. The commit
containing them is the prospective pilot freeze, not a preregistration of the
previous audits or the primary causal analysis. Prior outcome/date inspection
is disclosed in round 3 and the 14 September handoff.

## Purpose and ownership

Return a comparative design-feasibility matrix under 0729 / GitHub #1337, using
historical audit 0735 / #1345. Start AFD (0737 / #1349); KfW (0738 / #1350) and FCDO (0739 / #1351)
are independently executable complements. Their work does not require the
parent trackers to close. Launch each in its own fresh session/worktree. Tomorrow's
launch instruction must explicitly name any parallel agents; preparation today
has not launched or scheduled them. JICA and USAID expansion remain deferred.

Sol at high reasoning effort is the recommended wave lead: brief enforcement,
evidence adjudication and synthesis. Terra at high effort is suitable for a
bounded lender assignment, particularly parsing, joins and reproducible tables.
Have an independent scientific reviewer examine population eligibility, date
semantics, censoring and comparator admissibility before design selection; use
Sol or Astra for that review. This is workload judgment, not a project benchmark.
Official positioning: [Sol and Terra comparison](https://developers.openai.com/api/docs/models/compare),
consulted 14 September 2026. A model change does not relax acceptance criteria.

## Startup and immutable inputs

1. Fetch and inspect live PR heads, worktree status and upstream overlap. At
   preflight, #1347 = `84904ef4b6cee7489408e1e15af06bc727a9d802` and
   #1348 = `63bb738ef8f8bf7c96db3201a8ce48b717136075`, both open. The preparation
   commit follows the former. Record actual input SHAs in `input-manifest.json`.
2. Use the updated #1347 head as the pilot base. Read selection inputs at the
   pinned #1348 SHA with `git show SHA:path`, or from a verified matching
   checkout. Do not silently use main's older 0729 text. Record hashes for the
   selection chronology, comparators, rivals, report, sources and 0729 ticket.
   The options portfolio is `conception/jetp-causal-design-options-2026-09-14.md`.
3. Verify local DVC bundle hashes before reading originals. Round 2 directory
   MD5: `6cd6406b227e6860cae66906cce21d9c.dir`; round 3:
   `4b1a54b98d1ff7df92afe3e7b95ec07e.dir`. Source manifests are under
   `docs/jetp-audits/0735/round2/` and `round3/`; paths resolve under
   `data/jetp/audit-evidence/`. Resolve legacy AFD by source ID `afd-full-export`.
4. Use the audit virtual environment, not an assumed bare `python`. Verify
   imports before running. The default `uv` route hits a read-only
   `/data/cache/uv` in this sandbox; use the verified existing interpreter for
   gates, e.g. `make check-fast PYTHON=/tmp/jetp-audit-0735/.venv/bin/python`,
   or configure a writable task cache if dependency installation is necessary.
   For lint, also prepend the worktree's `.venv/bin` to PATH and set
   `RUFF_CACHE_DIR` and `MYPY_CACHE_DIR` to writable task paths under `/tmp`.
   Adapt the interpreter path to the new worktree; do not install packages blindly.
   Preserve source bundles, caches and existing worktrees;
   main's untracked `data/book/` is user material. Missing local bytes block
   dependent calculations; remote retrieval has not been demonstrated.
5. Read this protocol, the assigned ticket and `docs/jetp-scout-brief.md`.
   Commit the first failing acceptance test, then the minimum implementation.
   Before new retrieval, commit `selection.csv` and the acquisition route list
   derived by the rules below. Log any later amendment before dependent work;
   preserve the original selection and explain deviations.

## Population and baseline rules

Local profiling covers each complete acquired lender export at its own unit.
The common diagnostic country set is AL, MA, IN, SN, ZA, ID, VN, across all
reported sectors and instruments. These seven countries inherit the audit's
schema/retention scope; they are not an admissible matching sample. Do not add
countries because of favorable outcomes. Broader export counts are separate
from the seven-country diagnostic table. Regional/multi-country records form a
separate stratum; never replicate them into country counts or silently discard
ambiguous allocations. Counts of distinct projects and financings stay separate.

Country labels use a frozen explicit mapping, including legacy `VIET-NAM` to
VN. No fuzzy identity joining. Preserve source sector vocabularies and instrument
codes. Energy uses DAC purpose codes 23000–23999 when the source declares DAC;
other vocabularies require an explicit crosswalk, with unmapped/mixed records
separate. Preserve contradictory classifications (including CMA123501).
Loan/grant and policy/investment classifications need source evidence; unknown
is an explicit stratum, not an inferred category from a title alone.

Report annual entry cohorts using validated stage dates; unvalidated proxies
and missing dates get separate counts. For membership sensitivity, use all these
landmarks, with dates understood as end-of-day cutoffs:

| Country | Early calendar landmark | Before documented discussions/selection | Before declaration |
|---|---|---|---|
| ZA | 2020-12-31 | 2021-09-28 | 2021-11-01 |
| ID | 2021-12-31 | 2022-03-15 | 2022-11-14 |
| VN | 2021-12-31 | 2022-03-15 | 2022-12-13 |
| SN | 2021-12-31 | 2022-03-15 | 2023-06-21 |

These are diagnostic alternatives derived from 0736, not verified unexposed
baselines or selected treatment dates. Private negotiation starts are unknown.
Apply the same landmark dates to candidate comparator records for calendar
alignment; IN remains negotiation-exposed, and AL/MA remain exposure-unassessed.
Plan-release and operation-specific intervention dates stay distinct and are
not substituted for these landmarks. Unknown dates remain unknown.

For each landmark distinguish (a) records now reporting an earlier event,
(b) records demonstrably members at that landmark, and (c) records demonstrably
pending at the stage then. Report separate counts and evidence. A source with
2024 metadata cannot alone establish any pre-declaration census here, even if
its event dates are old. A later snapshot may support reconstruction only with
independent inclusion/retention evidence. Signed-only data cannot establish an
approved-but-unsigned risk set. Do not select on post-exposure survival,
approval, payment or current completion status for an incumbent population.

## Dates and observation states

Preserve source value, source version, event meaning, precision and locator.
Use separate fields for approval, signature, start, payment, publication and
retrieval. Never repair a reversal by sorting dates. `value-date` is not a
missing-approval imputation. Zero, no entry, redaction and disappearance differ.

For lost records retain last observed snapshot/date and last observed stage;
classify `lost_visibility`, with disappearance bounded by snapshots where
possible. Do not infer cancellation, continued nonpayment or noninformative
censoring. Historical legacy metadata is not an independently observed snapshot.
A first positive periodic payment bounds first payment only if complete earlier
coverage and the period's meaning are supported. Otherwise record an observed
payment period with first-payment time unknown. Preserve negative corrections.

## Documentary selection and bounded acquisition

All local profiling is allowed without external units. Select documentary cases
before new retrieval and without inspecting speed or effect estimates. Each
lender brief defines its mandatory challenge cases and deterministic sample.
Challenge cases test known failure modes and are excluded from any claim of
representative document coverage. Sample nonresponse remains in the denominator;
no replacement with easier or faster cases.

One unit = one search query, URL open/click or HTTP request, including retries,
failed attempts and each URL/query in a batch. Log units, route, purpose, status,
retrieval date and bytes/hash where obtained. Reuse originals for verification.
Any extra external reviewer retrieval consumes the same lender cap; there is
no unbudgeted verification allowance. Reserve the final tranche for verification.
Stop when decisive evidence is obtained, named routes are exhausted, or the cap
is reached. Unavailable documents are an acceptable finding; never reset a cap.
No institutional contact, estimator fitting or effect-based selection is in scope.

## Common deliverables and reproducibility

Each ticket writes to `docs/jetp-pilots/2026-09-15/<lender>/`:

- `input-manifest.json`: input Git SHAs, paths, hashes, environment and freeze SHA.
- `selection.csv`: case ID, country, source unit, sample/challenge role, stratum,
  deterministic rank, selection reason and baseline alternatives.
- `units.csv`: source IDs, parent IDs, country allocation, sector/instrument raw
  and mapped values, snapshot/version, observation status and identity confidence.
- `events.csv`: unit ID, stage, raw field/value, normalized date or interval,
  precision, source coverage, validation status and evidence ID. Missing is empty,
  never zero; include an explicit missingness reason.
- `coverage.csv`: lender, country, sector, instrument, entry cohort, baseline,
  stage, unit, count kind (retrospective/member/pending), count, missing count,
  lost-visibility count, calendar coverage, denominator rule and evidence IDs.
  Unsupported counts are empty with reason; a measured empty cell is zero.
- `evidence.csv`: evidence ID, claim, issuer, URL, title/date, page/section,
  faithful paraphrase, contrary evidence, archive path/hash and limitations.
- `acquisition-log.csv`: one row per external unit; `anomalies.csv`: every known
  discrepancy and its resolved/unresolved disposition, including nonresponse.
- `report.md` and `verification.md`: acceptance-test evidence, source limitations,
  document coverage denominators, decisions and exact next discriminating document.

Version the calculation code with a documented command and explicit input/output
arguments; do not depend on `/tmp/jetp-round3-*`, glob order or network at rerun.
Use the existing round-3 scripts only as inspected exploratory references. Put
original new bytes in a separate ticket DVC bundle with a SHA-256 manifest.
Do not mutate canonical ledgers or website totals. Required repository gates
apply: check-fast and lint; full check if the diff touches the pipeline surface.

The coordinator writes `design-feasibility.csv` and `decision.md` at this
protocol's directory. Each candidate row identifies estimand, population/unit,
stage/resolution, baseline alternatives, usable countries/counts, pre-period
coverage, comparator overlap, assumption/evidence links, retention/censoring,
concurrent exposures, country-level uncertainty and verdict. Do not sum lender
populations. Pre-period descriptive diagnostics require stable measured series;
report unavailable otherwise. No universal minimum sample or pre-period threshold.

## Decisions and review

Per lender/stage: GO means evidence supports further design assessment; NARROW
names the supported scope; DEFER names the decisive unavailable evidence. None
of these means a causal effect is identified. An unknown historical denominator
can complete the pilot with DEFER. Distinguish missing-data/precision limitations
from failure of counterfactual assumptions.

Compare incumbent-pipeline acceleration, new-financing/signature throughput,
and energy/non-energy contrasts. Keep country-specific synthetic controls and
support-allocation designs as DEFERRED candidates with their evidence needs;
they were not rejected by omission. Signed-only retrospective award-to-signature
pairs can inform measurement feasibility, not an unconditional acceleration effect.
Non-energy spillovers make sector contrasts relative. Matching does not establish
exchangeability; many projects do not create many independent treated countries.

The independent reviewer checks originals and reproduces pivotal tables and
acceptance tests. Record evidence by test ID or commit plus file/line. Under
0729, propose a primary design only after this matrix; an author scope decision
is required on causal DEFER, with no automatic descriptive substitution. Primary
estimation remains under 0730 after an agreed protocol. No merge is authorized
by this preparation document.
