# Climate Finance History Project

Do not add `CLAUDE.md` or `.claude/CLAUDE.md`. Claude Code loads this file
natively and falls back to the parent `~/CNRS/AGENTS.md` only while neither
file exists; the pre-commit hook enforces this.

## Rules that need explicit loading

Project rules under `.claude/rules/` otherwise load when their governed paths
are touched.

- Before filing tickets with `erg`, read `.claude/rules/ticket-filing.md`.
  `erg` does not trigger its path scope.
- Before any JETP source search, scout, or research round, use the
  `jetp-research` skill.
- A fresh worktree has no bulk corpus. Run `make data` when it is needed, or
  `make jetp-data` for JETP documents only.

## Merge gate

Run `make check-fast` and `make lint`, then push and open a PR.

When a diff touches a domain pipeline or its slow/integration tests, run each
affected test-domain gate: `make check-domain-literature`,
`check-domain-corpus`, `check-domain-finance`, `check-domain-jetp`, or
`check-domain-writing`. Run full `make check` for shared pipeline
infrastructure (`dvc.yaml`, shared scripts or libraries, Makefiles) or a change
to test selection itself. Test domains and build workpackages are different
axes; README.md defines their relationship.

Run test-domain and full gates on padme (`ssh padme`) in a clean checkout of
the branch with the corpus and JETP documents present (`make data` and
`make jetp-data`; a fresh worktree may need `dvc checkout --force`, ticket
1060). padme's `.env` sets `PYTEST_WORKERS=16`. A doudou worktree lacks those
data by default, so its data-bound failures or skips are not evidence.

There is no CI (ticket 0321). `/lair` step 9 runs full `make check` on `main`
after merges and files tickets for new failures; a merged PR does not prove
that `main` is green.

Ticket-only PRs use the gate in `.claude/rules/ticket-filing.md` instead.

## Scope

One ticket per Execute conversation. File sub-issues rather than widening the
diff.
