# JETP observatory MVP validation — 13 September 2026

Ticket 0734 delivers the local preview for steps 1–4. It does not complete public
deployment, the full publication dataset, the monthly release process or the
matched acceleration study (0726–0730).

## Delivered evidence and interface

- 383 named portfolio identities; Viet Nam's 21 unpublished slots remain separate.
- Four country narratives with attributed financing/portfolio headlines and dates.
- Country synthesis, financing-evidence composition and theme/technology summaries.
- Search/filter catalogue, project sources and qualified event/report timelines.
- 97 closed historical World Bank energy-related operations: IDN 38, VNM 32,
  SEN 17, ZAF 10. Full projected country pools retained with pagination provenance.
- Instrument, vintage, country and additional-financing filters; an administrative
  approval-to-reported-closing distribution. No construction or acceleration claim.
- Local-only runtime: static HTML/CSS/JavaScript and six JSON handoffs, downloadable
  without access to DVC. Input hashes match the files used to generate the snapshot.

Source/transform commit: `58e21737a6210497fdae6457201eef034f8d0a70`.
Frozen handoff and tracked HTML: `b690b25e`.
The final frontend formatting does not change the data input hashes.

## Checks

- Seven scientific-boundary tests: register dates, status-report dates, retrospective
  event ordering, cohort selection, missing duration dates, duplicate/conflicting
  financial observations, undisclosed slots and incomplete pagination.
- `make check-fast PYTHON=.venv/bin/python`: 1,542 passed, 7 skipped.
- `make lint PYTHON='env RUFF_CACHE_DIR=/tmp/jetp-mvp-ruff .venv/bin/python'`:
  337 passed, 6 skipped after correcting the helper-module naming convention.
- Full `make check`: 2,467 passed, 43 skipped, 11 failures in the restricted
  environment. Failures concerned localhost sockets, Git worktree metadata,
  writable uv cache, missing `python` on PATH and one subprocess timeout.
- All 11 failed tests passed on targeted rerun with the existing virtualenv on
  PATH, writable temporary cache, `UV_NO_SYNC=1`, and permission for localhost,
  temporary environments and Git worktrees. No unresolved failure remains.
- Chromium: homepage, all country narratives, project search, source links,
  historical country/instrument filters, empty results, JSON downloads and mobile
  overflow checks passed. JavaScript reported no page errors.
- `node --check`, `git diff --check`, `erg check` and input SHA-256 verification pass.

The full-suite environment rerun is explicitly recorded rather than described as
an uninterrupted green full-suite run. Tests did not require changes to unrelated
pipeline code. Temporary worktrees were managed by the existing test cleanup.

## Remaining limits

National headline stages and dates differ; no cross-country money total is
computed. Portfolio identities can include overlapping programmes/components.
Viet Nam's financial-event coding remains incomplete even where source pages
report financing. Historical closed status is administrative and may reflect an
older API update; the selected cohort is descriptive, not a matched causal control.
The website uses reviewed country Markdown but does not yet render optional
project-specific Markdown dossiers. Monthly edition/deposit validation remains
in 0726/0728; this preview is not claimed to be an immutable public release.

## Senegal refresh, 14 September 2026

Merged main through PR #1332 (`b6d5f761`); #1322 is a different, open prose PR.
Updated the Senegal narrative and regenerated the preview from input revision
`5945a42d`. The preview retains 383 named records and 97 historical operations;
source coverage grows from 260 to 301. Senegal has 21 collected, 19 central-only
and three blocked project identities. The ANER conditional budget remains a
need; no project-level disbursement total is inferred.

Validation: 1,545 fast tests passed (seven skipped); lint passed; Chromium
navigation, filtering, downloads and mobile checks passed. This refresh changes
source data, prose and generated views, not the builder. The earlier full-suite
results above are historical validation, not a fresh full-suite run.

The separate data-science review identifies scientific export issues that these
software checks do not catch; passing tests is not approval for analytical use.

## Scientific corrections, 14 September 2026

The three review findings are repaired in `e35988a7`; failing regression cases
were first committed in `95fd9181`. The frozen exports identify clean input
revision `e35988a7065c628dc75dddde4df18d6658701b40`; all 22 recorded input hashes
were checked against their files. This includes the explicit timing registry.

- Real-record regression checks cover three Indonesian portal approvals, four
  ANER observations, PUELEC publication timing, Diass's milestone/publication
  distinction, and the ZAF implementation-start placeholder. Interval bounds,
  authority independence, registry coverage and invalid timing are also tested.
- All 451 published observations have explicit timing classifications: six
  supported day dates, two approval-year intervals, and 443 with unknown event
  precision. These counts describe coding coverage, not source exhaustiveness.
- Typed provisional source links and claim verdicts survive export and rendering.
  Historical snapshots retain their acquisition dates and query hashes even when
  the edition cutoff changes; substantive source-update dates remain unknown.
- Fourteen observatory tests pass. Fast suite: **1,552 passed, seven skipped**.
  Lint: **337 passed, six skipped**. A test import-order issue was corrected
  before the successful lint run.
- Fresh full `make check`: **2,506 passed, 25 skipped**, in 214.52 seconds.
  This uninterrupted successful run used the existing virtualenv on PATH,
  writable temporary uv/ruff caches, `UV_NO_SYNC=1`, and permission for local
  sockets and Git test repositories. No failed-test rerun was needed.
- Chromium navigation, filters, downloads, mobile layout, the provisional
  Linguère source card and PUELEC's qualified timeline pass on the final exports.
  JavaScript syntax and `git diff --check` pass.

This repair does not constitute the independent Imperial Dragon merge gate.
Ticket 0734 remains open pending verification; the PR remains a draft. Public
publication, monthly releases, complete financial-stage reconciliation and a
comparable early-lifecycle cohort remain separate work.

## Independent checkpoint validation, 14 September 2026

Fresh checks on checkpoint `f417998b`: fast **1,552 passed, seven skipped**;
lint/adherence **337 passed, six skipped**; full suite **2,506 passed, 25
skipped**, uninterrupted in 204.78 seconds. The environment is the same documented
virtualenv, temporary caches, local-socket and Git-test configuration above.
All 14 observatory regressions also passed independently in 0.38 seconds.

Three independent reviews covered correctness/adversarial data, documentation/
architecture, and scope/scientific interpretation. They independently reconciled
all 22 input hashes and the current exported counts. They did not re-adjudicate
301 original sources or recompute absent raw World Bank response bytes.

Review correction `8a3aa373` updates storage status and removes two website
phrases implying matching was already selected. Only documentation, ticket0727
and those two display strings changed after the tests started; Python, tests
and all data bytes remained unchanged. Chromium was rerun successfully after
that correction, covering navigation, filtering, downloads, qualified source
cards/timelines and mobile layout. No page errors were reported.

Optional future-refresh hardening is recorded in 0727: interval-aware chronology,
rejecting unsupported unreviewed bounds, and deriving all undisclosed counts from
the export. The current observations contain neither identified timing edge case.
The existing financial-stage coding caveat remains part of release work0726.

The final independent evidence-gate verdict and per-criterion references are
recorded on PR #1343. Public release, deployment, monthly operation and causal
identification remain outside the completed local MVP scope.
