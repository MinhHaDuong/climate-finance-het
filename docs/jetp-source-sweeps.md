# Source-watch candidate handoff (0770)

The current MVP remains authoritative. This implementation supplies ticket
[0728](../tickets/0728-jetp-monthly-editions.erg) with frozen monitoring
plans and review candidates; it has no publication or evidence-admission operation.

## Actual bounded rehearsal

`data/jetp/releases/source-sweep-0770.json` was generated with code/input commit
`2c5d03ed` from the committed source registry, acquisition manifests and source
claims. It pins their hashes, the relevant implementation files, the document DVC
pointer and `config/jetp-source-watches.yaml`. The artifact is 189,725 bytes, below
the 512,000-byte Git cap; SHA-256:
`d632bf7b130d2b4f9fd5a16278ad5de174eb5a89dbbe5441c3c4bf190ba2015c`.

Four proposed document watches cover the Vietnam RMP, South Africa Q1 2026
report, Indonesia 2025 progress report and Senegal official investment-plan
route. All are **pending policy review and explicitly deferred**. They have not
been polled. The frozen plan accounts for every target without pretending a
successful source refresh.

The rehearsal retains seven historical manifest attempts: four available-material
rows (including repeated Vietnam acquisitions) and three failed Senegal official
route attempts. It verifies three distinct saved hashes. The failed attempts
remain visible; the mirror's existence does not rewrite their outcomes. Original
retrieval times and crosswalk acquisition IDs survive. These are local archive
verifications, not new acquisitions, historical admissions, or current publisher
coverage.

All 149 original source claims enter an editorial review queue. Comparing the
catalogued publication dates with the explicitly selected report baselines gives
20 later, 20 same-date, 67 earlier and 42 unknown-date claims. These are date
relations, not proof of a substantive change, late arrival, correction or
independent confirmation. Original wording and source identity are retained;
claim origin and dependency independence remain unknown. The queue makes no
factual promotion. Vietnam's older RMP remains an explicit selected reference,
not a claim that it is the latest report.

## Deliberate live refresh

The new layer reuses `corpus_harvest_documents._harvest_one`: conditional headers,
content validation, content-addressed bytes and the original manifest-row schema.
It does not add another HTTP collector or edit the legacy manifest. Frozen source
metadata, route, method, budgets and watch revisions control each check even if
the editable catalog subsequently changes. The adapter uses one request, no
redirects or automatic retries, a response-size bound and a stream time budget.
Redirects and access errors become retained failures for review.

Review the policy and source triage separately before creating an executable
plan with `freeze_sweep`. A reviewed policy needs a review reference; proposed
policies can only be frozen with an explicit deferral. Registry defaults never
supply claim-level origin decisions. UTC day intervals and bounded exponential
retries are explicit; expected publication windows accelerate checks only through
an explicit interval rule. A new reviewed revision represents a manual scheduling
change. Prior validated sweeps supply successful-coverage history and due dates.

The CLI supports the same validated candidate contract for a deliberate refresh:

```sh
UV_NO_SYNC=1 PYTHONPATH=scripts:libs/openalex-corpus/src uv run python \
  scripts/jetp/build_source_sweep.py --input . \
  --execute-candidate /tmp/reviewed-sweep.json --attempt-id deliberate-refresh-1 \
  --storage-root /tmp/refresh-materials --output /tmp/refresh-candidate.json
```

`execute_sweep` persists the plan first and then each target result atomically.
Replaying the same attempt ID resumes missing targets without duplicating completed
attempts. A new attempt ID retains prior results and is limited by the frozen
call/time budget; exhausted budgets need a reviewed supplemental sweep. Failed,
partial and blocked checks cannot advance successful publisher coverage. The
summary distinguishes a missing result from a completed, failed or deferred target.

A channel check establishes only its specified route/page scope. It does not
fetch linked documents or establish project follow-up. Explicit discovery records
retain multiple sightings of the same curated source ID. `link_acquisition`
requires the exact target revision, or a discovered-document link for that check;
URLs are not identity keys. Newly selected targets require a separate linked plan.
The engine exposes these append operations for deliberate triage; there is no
unattended crawler or scheduler.

`change_report` accepts attributable new/changed, late-report, correction and
editorial-impact candidates and identifies their affected source claims. It never
rewrites those claims. Claim-origin proposals have immutable revision IDs and
cutoff views. A cited-but-unacquired upstream remains a citation; linked dependency
endpoints must pass the shared exact acquisition/extraction/edition tuple validator.
Acceptance and public display selection remain outside this writer.

## Validation and recovery

The first RED commit is `47c5bad5`. The focused acceptance suite is
`tests/test_jetp_source_watch.py`: unchanged/revised/blocked/deferred target
accounting; repeated attempts and prior-sweep coverage; metadata and origin cutoffs;
multiple discovery links; acquisition-role mismatches; late/correction queues;
lexical symlink/hardlink and malformed-output rejection; safe parent aliases;
failure preservation; and the actual registry rehearsal. Its localhost HTTP test
runs the existing harvester, mutates the catalog after freezing, exercises 304,
changed bytes and 403, and interrupts/resumes a persisted multi-target sweep.

The three saved hashes were checked against the independently recovered document
directory from the 0764 empty-cache DVC recovery, not merely pointer declarations:

| Source | SHA-256 |
|---|---|
| Vietnam RMP | `b145af2e7f4a441dc87d7ec2d99a29e1e6d7b265406d398dd64013dd4560733c` |
| South Africa Q1 2026 | `1b62a65fd70c70b0234379fcc4fcda064e9175fc9aee21a37c97b283e1b8dc13` |
| Indonesia 2025 progress | `74fb460fd09e76607e3cff308f5ba2754f2ebd91b0c9b7613c1a041e7b361162` |

No binary or DVC pointer changes are introduced. Regenerate the candidate with:

```sh
UV_NO_SYNC=1 PYTHONPATH=scripts:libs/openalex-corpus/src uv run python \
  scripts/jetp/build_source_sweep.py --input . \
  --policy config/jetp-source-watches.yaml --output /tmp/source-sweep-0770.json
```

A changed metadata snapshot requires a new destination; it cannot overwrite a
prior frozen sweep. Both writers reject final-component symlinks, hardlinks and
malformed lookalikes before building. Existing canonical inputs and release
metadata are protected. The 16-file preservation snapshot and frozen MVP ZIP hash
remain unchanged. No renderer or accepted-output change requires another browser
run; the previously passed 0764 browser exercise remains applicable to the same
assets. Final gate SHA and test logs belong to the PR review record.
