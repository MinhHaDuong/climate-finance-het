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
