# Pilot preparation verification — 14 September 2026

Phase: Plan. Prepared for 15 September; no pilot run, scheduled task, primary
estimation, institutional outreach or merge. Preparation is on audit PR #1347.

## Checked inputs

Live #1347 head before preparation: `84904ef4b6cee7489408e1e15af06bc727a9d802`;
#1348: `63bb738ef8f8bf7c96db3201a8ce48b717136075`; both open, local worktrees clean
before edits. Fetch found no newer main changes to reconcile. Read round-3
synthesis and lender reports, AFD profiles, selection chronology/comparators/rivals,
0729 and the causal options portfolio. Selection source-byte archival remains a
known gap; existing documentary statements retain that limitation.

All 33 round-3 source entries passed SHA-256 and byte-length checks, totaling
406,032,031 bytes. Both round-2 (8 payloads) and round-3 (33 payloads) directory
objects and constituent MD5 objects matched in audit and primary caches. These
copies are on one machine. Remote DVC recovery was not retested and remains
unproven; retain caches and worktrees.

The existing exploratory AFD checker reproduced 223/224 sample retention,
19 full-table disappearances, two signature discrepancies, 223 agreeing sample
signatures and 0/193 exact first-payment date matches. The checker is not the
future production calculation: it contains temporary paths and an initial
incorrect country spelling followed by correction. Tickets require versioned,
parameterized calculations and an explicit country crosswalk.

## Protocol review

The common protocol now distinguishes retrospective event coverage, demonstrated
historical membership and demonstrated pending-stage membership. It preserves
unknown first-payment timing where earlier coverage is absent. Baseline choices
are a sensitivity grid, not asserted anticipation-free treatment definitions.
All three assignments include deterministic samples, separate challenge cases,
nonresponse denominators, budget reserves and a valid DEFER outcome. The AFD
brief explicitly includes seven reversed award/signature pairs. Synthetic-control
and allocation-mechanism candidates remain deferred rather than silently rejected.

The three local tickets contain their full lender briefs. `erg check tickets/`
passes with 452 tickets; open PR paths were inspected before allocating 0737–0739.
GitHub issues #1349, #1350 and #1351 were created and read back. Parent issues
#1345 and #1337 link all three; their updated bodies were read back and compared.
This is a preparation review, not independent scientific or full PR gate approval.

## Local gates

- `make check-fast PYTHON=/tmp/jetp-audit-0735/.venv/bin/python`: 1,549 passed,
  12 skipped in the root suite; the prerequisite package suite also passed.
- `make lint` with that interpreter, worktree `.venv/bin` first on PATH,
  `RUFF_CACHE_DIR=/tmp/jetp-pilot-prep-ruff` and
  `MYPY_CACHE_DIR=/tmp/jetp-pilot-prep-mypy`: 330 passed, 15 skipped.
- `git diff --check` and ticket/brief consistency checks passed.

Initial default invocation could not write `/data/cache/uv`; initial lint could
not write `/data/cache/ruff`. These were environment failures resolved through
the existing interpreter and writable task caches, with no code/test changes.
The full suite is not required for this documentation/ticket-only change.
Raw gate logs remain at `/tmp/jetp-pilot-prep-check-fast.log` and
`/tmp/jetp-pilot-prep-lint.log`; this report preserves the outcomes durably.
