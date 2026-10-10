# REL: disposition of the retired staged screening (ticket 2062)

Author decision of 2026-10-10: the staged screening half of branch
`t1654-citation-chaining` is retired; the scorer of
[the redesign](rel-pipeline-redesign-2026-10-10.md) replaces it (§ 8, § 12, stage S1).
This note records what is retired, what stays, and where it is kept.

## Ledger (done, see the 2062 log)

Every provider batch is terminal. `data/rel_chaining/2026-10-08/budget.sqlite`
is frozen: 12,073 calls, all settled, USD 20.8215 usage-derived (not an invoice;
25 rows settled at their whole reserve as an upper bound, assumed spent, not
measured), cap USD 30. No paid call and no new reservation, for any reason.

## Retired

- **Runners**: the staged screening runners of the branch: design B stage 1
  (Haiku batches), stage-2 judges (Sol, Opus, Luna facet waves 01 to 07), the
  Fable and Opus correction chain, the local Qwen route, and the separate 1842
  discipline catch-up as a stage. No wave is restarted.
- **Scripts on the branch, not merged**: `scripts/corpus_rel_chaining_screen.py`
  and the screening parts of `scripts/_rel_chaining.py`, with
  `tests/test_rel_chaining_screen.py`. The collector half is carried by ticket
  2061, not by this note.
- **Waivers**: the author's waiver of the final stage-2 sample audit
  (2026-10-07), the historical 59-titleless waiver, and the Astra fallback for
  the 47 native titleless records (policy abstention). None extends to the new
  pipeline; they are listed as limitations in ticket 1656.

## Stays

- **Labels**: the screening labels already imported stay in the append-only
  tables (`icf_screen` and its dimensions) as a cross-check and a source of
  clear negatives, never as truth.
- **Ledgers**: `budget.sqlite` (frozen) and the provider pricing snapshots.
- **Archives**: `data/rel_chaining/2026-10-08/` (see below): raw responses,
  batch inputs and answers, checkpoints, gaze and incident evidence.
- **Unresolved works**: the 63,558 chaining works still unresolved under the old
  screening are not screened by it; they wait for the new scorer.

## Preserved commits

Annotated tag `archive/t1654-screening-half` at `f10a71dd` (tip of
`t1654-citation-chaining`, 29 commits ahead of `main` on 2026-10-10), so the
branch may later be deleted without losing them:

```
f10a71dd docs(rel): checkpoint verified main and incremental screening imports
9cd2a343 docs(rel): record strict metering and source-gap reuse contracts
42cf5f48 fix(rel): reject invalid metering and bind closure reuse evidence
d4e2b2d5 docs(rel): checkpoint native47 reconciliation and bounded wave04
3b21a103 ticket(1654): checkpoint native titleless intake and local screening
298c4493 1654: bind reused native pages to archived acquisition source
89dd9d74 1654: bind reused direction pages to exact seed filters
d8cc84fd 1654: validate archived direction reuse and protect metadata recovery
661376cb 1654: reconcile catch-up and guard exact citation frontier planning
389951a9 Distinguish citation candidates from source metadata updates
ed2a929c Record first guarded Luna production import checkpoint
b94d511a Record policy import and inert round-two preparation checkpoint
e1650d12 Require specific unassessed-family disposition for facet builds
47f07b31 Checkpoint bounded Luna batch and guarded family screening
0295a92e test: guard explicit changed-family facet reconciliation
7c7b6c6c docs: record local calibration failure and policy child
bea4e4a8 docs: record full-input facet release and public proof checkpoint
945888c9 corpus(1654): record three-facet pilot and pending evidence review
8810dcf1 corpus(1654): checkpoint completed Stage1 and model validation failures
2c482c7c fix(rel): validate native batch coverage and preserve pending decisions
83ba88dd fix(rel): preserve local-only screening and scientific checkpoint
810c7b6d fix(rel): bound every screening attempt and preserve exact source identities
cdec525b refactor(rel): share bounded citation and screening transport
e1768118 corpus(1654): keep incremental screening within baseline decisions
4f035bc1 corpus(1654): guard concurrent charges and preserve exact-key screening history
75a9424a corpus(1654): checkpoint resumable citation discovery and bounded v2 screening
3285505f raid: phase 4 feasibility for 1654 then 1656
ed951ee1 raid: phase 3 Actions for 1654 then 1656
c5940298 raid: phase 2 Imagine for 1654 then 1656
```

The tag also preserves the collector commits interleaved with them; 2061 lands
the collector on `main` separately.

## Archive: location and DVC scope (author choice relayed by the orchestrator, 2026-10-10)

Location today: `data/rel_chaining/2026-10-08/` in the worktree
`.claude/worktrees/t1654-citation-chaining` on padme, the only copy. Measured
2026-10-10 with `du` (read-only): 20 GB, 30,867 files.

| Part | Size |
|---|---:|
| `operations/` (batches, imports, gaze and incident evidence) | 11 GB |
| of which `round2-local-preparation` | 6.4 GB |
| of which `titleless177-exact-doi-metadata` | 1.9 GB |
| `round1/` | 8.3 GB |
| of which `checkpoint.sqlite` | 5.9 GB |
| of which `raw` | 1.5 GB |
| of which `screen` | 928 MB |
| `baseline/` (pool, icf_screen, rel_view snapshots) | 943 MB |
| `budget.sqlite` | 15 MB |
| `provider-pricing/` | 3.8 MB |
| `producer/` | 136 KB |

Scope (author choice relayed by the orchestrator, 2026-10-10): push everything in
`data/rel_chaining/2026-10-08/` (about 14 GB expected after deduplication)
except `operations/round2-local-preparation/round1-as-of.sqlite` (5.9 GB).
That file is a copy of `round1/checkpoint.sqlite` made for round-2 preparation
and is rebuilt by copying it: `cmp -i 100` of the two exits 0 (identical apart
from the 100-byte SQLite header); sha256 `a95e0ba62b1dc511e742e7584671bc1097117126a8c782891c68b28adcdaeb6c`
(copy) and `6a275485f2c0a489d57edc8d22e81b2de1b7edda16ef002d46cd0ca1ba8745ab`
(`round1/checkpoint.sqlite`). Nothing else is excluded: `round1/raw`,
`round1/checkpoint.sqlite`, `budget.sqlite`, the answers and ledgers, the
`titleless177` tree, the stage-2 input variants,
`candidate-superset-attempt2.sqlite` and `baseline/icf_screen.csv` are pushed.

Mechanism, done 2026-10-10: the archive was reflinked (btrfs, no space used)
into a worktree without `operations/round2-local-preparation/round1-as-of.sqlite`,
then added with one plain `dvc add data/rel_chaining/2026-10-08` and pushed to
remote `padme`: pointer `data/rel_chaining/2026-10-08.dvc`, md5
`aa629e0f3e425b8bdd45c9ac16377e5e.dir`, 30,863 files, 14,601,070,257 bytes;
`dvc status -c` in sync; a fresh `dvc get` restored 30,863 files, and
`budget.sqlite` and `round1/checkpoint.sqlite` match the originals by sha256.
`cmp -i 100` of the excluded copy against `round1/checkpoint.sqlite` was
re-run just before the push and was identical after the header. The original
copy stays in the `t1654-citation-chaining` worktree, untouched.

Three tiny archived copies of repo pointers could not sit inside a DVC output
(DVC refuses a directory that overlaps another tracked output) and were left
out of the pushed set, in
`operations/astra-parent-publication-packaging-decision/`:
`reference-data__pool.dvc` (sha256 054e81e2...), `reference-data__rel_screen.dvc`
(c76f7093...) and `reference-data__rel_venues.dvc` (f019c938...), 107 to 111
bytes each. They point at pools already in DVC; they remain in the original
worktree.

Provenance: `producer/checkpoint.json` in the archive names producer head
`9bbdfe2d1ee53d5481fa56b0caf424d68cd73e4b` ("Native raw pages and cursor
checkpoint are authoritative"). The archived `producer/_rel_chaining.py`
differs from `scripts/_rel_chaining.py` both at `f10a71dd` and in the
`t1654-citation-chaining` working tree (`cmp`, first difference at line 13), so
the archive's own `producer/` copy, not the tag, is the code that produced it.
