# JETP Observer: operation

This document says how the JETP Observer is run: on which machine each job
runs, who launches and supervises it, how the repository governs what
development agents may do, what each run may spend, where secrets live, what
happens when a run fails, and how the record is backed up and recovered. It
is the one document of the specification that names machines, commands,
schedules and budgets concretely. It serves the author and the development
agents of [purpose and requirements](jetp-requirements.md) § 3.2 (OP-1 to
OP-6), the constraints C1 to C4, C9 and C10, and Q14, Q15, Q17 and Q19.

Milestone tags in square brackets follow the [index](jetp-spec.md): M2 and
M3 need only what makes a run correct, reproducible and affordable;
scheduling, unattended refresh, link-rot checks, the pass launcher and the
move of the document store to Zotero are M4.

## 1. Principles

**Hand-launched runs until M4.** Every run is launched by a person or an
agent in a session, watched to its end, and reported. Nothing runs on a
timer. [M2]

**One run, one report, one budget.** A run is one bounded execution of one
job (an extraction batch, a discovery round, a fetch run, a replay). It has an
identifier, declares its budgets before it starts, stops when a budget is
reached, and ends with a report, including when it fails or finds nothing.
[M2]

**Bytes and LLMs on padme, supervision anywhere, data one way.** Jobs that
read document bytes or call an LLM run on padme. Data produced there
reaches the laptop by the repository and DVC, never the other way. [M2]

**The repository is the control plane.** Every change to code, rules or
data enters the record through a branch, a review and passing tests. A
decision is a ticket entry or a commit message, not a conversation. [M2]

**No machine judgement waits for the author.** Runs work in complete
autonomy under the protocol of extraction § 6.3, and nothing is queued for
the author (requirement C1). [M2]

## 2. Machines

| Machine | What it is | What it holds | What runs there |
|---|---|---|---|
| padme | Personal workstation: two consumer GPUs (RTX A4000 16 GB, RTX 3060 12 GB), 125 GB RAM, one 953 GB NVMe disk | The primary checkout, the DVC cache and the DVC remote, every document byte, the two local LLM readers (one per GPU), the credentials for paid services | Every job that reads document bytes or calls an LLM: fetch runs, extraction runs, replay, discovery rounds, matching to CRS and IATI, the release build, the Observatory build, the full test suite |
| doudou | Laptop | A checkout of the repository; DVC data only as pulled from padme | The author's sessions; development agents editing code, rules and tickets; the fast test tier; supervision of runs on padme; viewing padme's browser on its own screen |

- **padme runs the jobs**, in a git worktree or, from M4, in the persistent
  checkout of section 11. A development agent on doudou reaches padme over
  `ssh padme`. [M2]
- **doudou never has to hold all the bytes.** The fast test tier
  (`make check-fast`, `make lint`) needs no archived bytes and is the gate
  that runs on doudou; the slow tier (`make check`) runs on padme. The fast
  tier does not resolve locators, which needs the bytes and the pinned text
  adapter. [M2]
- **The primary checkout on padme is not a work area.** Runs use a worktree
  (populated with `make jetp-data`, a local copy from the DVC cache with no
  network), or from M4 the persistent checkout. [M2]
- **Non-interactive shells.** A command sent to padme over SSH does not get
  the interactive environment, so it sets the tool path itself (section 15).
  A run that fails because a tool is not found is reported as not started,
  not as failed. [M2]
- **Long runs survive the session.** padme has no systemd user linger, so a
  run expected to outlast the launching session runs inside a named `tmux`
  session on padme (one per run, named after the run identifier) and
  writes its progress to its report as it goes. [M2]
- **The local LLM is a shared service.** padme serves its local models
  through a system service that other projects use (section 15). A run
  never restarts or reconfigures it; more parallel slots, tool-calling
  flags or another LLM require the author's agreement first. [M2]

## 3. Data flow

**One direction.** Document bytes, DVC outputs and run products are created
on padme and travel to doudou by `git pull` and `dvc pull` (or
`make corpus-sync`). Nothing is copied from doudou to padme: no `scp`, no
`dvc push` from doudou. [M2]

**New documents found on the laptop travel as changes, not as data.** A
document the author spots while working on doudou enters as a register or
query change on a branch; padme then fetches it. [M2]

**Documents behind a browser check are collected on padme, displayed on
doudou.** When a site demands a human check or a login the author holds,
the author opens padme's browser on doudou's screen (remote display), passes
the check in person, and the bytes land on padme. The browser rungs of
collection (`make jetp-harvest-blocked`, which reuses the browser's
cookies for the hosts concerned, and `make jetp-collect-downloads`, which
records files the author saved) run on padme, against padme's browser
profile. [M3a; the documents held at M2 are already on padme]

**DVC is pushed from padme only, after review.** New objects are tracked
with `make jetp-documents-track` and pushed from padme once the branch that
records them has been reviewed (redirects, invalid content and dry searches
checked). [M2]

**Recovery is the one exception.** Restoring padme from the backup copy
(section 9) moves bytes towards padme. It is an explicit act of the author,
verified by hash against the DVC pointers, and never a synchronisation.
[M2]

## 4. The repository as control plane

**Gates.** [M2]

- Every change lands through a branch and a pull request; `main` is not
  written directly.
- The merge gate is `make check-fast` and `make lint`; a change to code that
  writes data, DVC outputs or deposits also passes the full `make check` on
  padme before merging.
- A change is reviewed by an LLM of another family than the one that wrote
  it (requirement Q19), and the review's findings are answered on the pull
  request before merge.
- The ticket a change serves is closed in the same pull request.

**Run outputs have their own gate.** A run writes its products
(statements, dispositions, candidates, retrievals, readings, its report) on
a branch and opens one pull request per run. Nothing a run produces reaches
`main`, the ledger of record or the Observatory without that review. A
run-output pull request carries no code; its gate checks the run rather
than its rows: [M2]

- the validator over the ledger with the run's rows;
- the planted-item and fabricated-locator controls of extraction § 12;
- replay and idempotence over the run's snapshots;
- the run report (section 8), which carries a table-aware summary: rows
  added, superseded and rejected per table and per document.

The reviewer (requirement Q19), of a family other than the readers' and the
arbiter's, reads the run report and a sample of traceability chains, each
from a statement or judgement down to its readings, its locator and its
snapshot, not every row. A pull request that changes code, rules or
configuration keeps the full gate above.

Ledger tables and bulky raw material are kept as storage contract § 3
states. [M2]

**What agents may do.** [M2]

- Write code, tests, rules and tickets on branches; open pull requests;
  answer reviews.
- Launch runs on padme within declared budgets, and resume or abandon them.
- Run the test tiers, the replay, the Observatory build for inspection.
- Merge a pull request that has passed its gates and review, when the change
  is within a scope the author has already decided.
- Push DVC objects from padme for a branch whose review has passed.
- File tickets for defects that reach a deliverable, and propose decisions
  to the author with a recommended default.

**What agents may not do.** [M2 unless stated]

- Raise a budget, draw on prepaid credit, or top up a paid account.
- Admit a document by hand, outside the triage of collection § 9; accept a
  milestone, freeze the register, cut a release, or publish the Observatory
  (`make jetp-observatory-publish` is run by the author, from `main`, after
  a release is accepted).
- Pass a site's human check, use a login the public cannot freely obtain, or
  fetch past a paywall (requirement C6).
- Restart or reconfigure the shared local LLM service (section 15).
- Run `dvc gc`, push DVC from doudou, force-push, or rewrite published
  history.
- Read, print, copy or commit a credential value (section 6).
- Overturn a judgement the author has made; an agent may only propose its
  supersession with a reason.
- Delete the `gh-pages` branch, which is the live Observatory.

**The author's decisions.** The author decides scope, budgets, milestone
acceptance, protocol changes, and the questions that change what a term or
the contract means. No item of a run is routed to him; when he chooses to
decide one, his decision is recorded as a judgement like any other
(section 5). Decisions are batched: an agent collects the foreseeable
questions of a run into one round, each with a recommended default. [M2]

**Reported errors.** A report of an error, received through the channel
named on the Observatory's methods page, is recorded as one ticket; the
ticket number is the report identifier, which the correction row cites.
The reporter's identity stays in the ticket and never enters a ledger
table. The report ends in one of the three outcomes of
[results and releases](jetp-results.md) § 9. A table of reports may be
derived from the tickets at M4 if their volume warrants it. [M3b; M4 for
the derived table]

## 5. LLM readers and the checking rule

**Two local readers, a hosted arbiter.** An LLM judgement (a statement
extracted, a disposition proposed, a candidate triaged, a match) is made on
every item by two LLM readers on padme, from different model families,
each blind to the other; what they leave open or hold below the acceptance
level goes to a stronger model reached through OpenRouter. The rules are
those of extraction § 6.3, collection § 9 and fusion § 3; this section only
says what runs where. [M2 for statements extracted and document identity
judgements; M3a for discovery and triage; M3b for the other identity
judgements and for preference judgements]

**One model per GPU.** Each local reader is one model sized to fit its
card: one on the RTX A4000 (16 GB), the other on the RTX 3060 (12 GB), the
two from different families, served side by side. [M2]

**Selection and calibration before installation.** Candidate open-weight
models of the sizes that fit each card are selected and calibrated on
OpenRouter, on the reference answers of extraction § 6.3 (for matching,
the matches decided by hand of storage contract § 4), selection reading
only their tuning part; a candidate that fails its positive controls is
weighted out. The winning pair, the best-scoring model for each card, of
two families, is installed on padme. A reader is its exact weights,
quantisation, context, sampling, template and serving software, so the
installed pair is scored again on the held-out part before its first
unattended run, and that score, with the arbiter's, is the calibration the
method version runs under; a change of any of these, or a switch between
local and hosted, is a new method version. [M2, before the first
unattended run]

**Replacing a reader.** A reader or the arbiter that is retired, repriced
or unavailable is replaced only under extraction § 6.3. [M2]

**Vendor means LLM family, not billing channel.** An LLM reached through
an aggregator (OpenRouter) counts under its maker, and so does a local
model: a Qwen model counts as Alibaba. The two readers are from different
makers. [M2]

**Where each reader runs.** [M2]

| Role | Default | Alternatives |
|---|---|---|
| Reader | The selected open-weight model on padme's RTX A4000 (16 GB) | The same model through OpenRouter, as another method version |
| Second reader | The selected open-weight model, of another family, on padme's RTX 3060 (12 GB) | As for the reader |
| Arbiter | A stronger hosted model through OpenRouter, calibrated like the readers | Another hosted model that passed calibration |
| Transcription readers | Two vision-capable hosted models of different families through OpenRouter, for a document not `local_only`, within the per-document budget (extraction § 6.4) | — |

A document longer than a reader's context is split into parts with their
own scope, as extraction § 6.3 provides; the largest held PDF has a text
layer of about 950,000 characters, beyond a local reader's context. [M2]

**What reaches a hosted model.** A document whose recorded terms forbid
third-party processing by an explicit reservation is marked for local
reading only (the target column `documents.hosted_reading` of the storage
contract): it is never sent to OpenRouter, and what its local readers leave
open ends undetermined (extraction § 6.3). Every hosted call asks the
provider not to collect or retain the input (OpenRouter's data-collection
and zero-retention settings), goes only to an endpoint that honours them,
and fails closed when none does; the run records the settings and the
endpoint that served each call. The legal position on hosted calls, and the
agreements it may need, are the [legal note](jetp-legal-note.md)'s section
4, settled at the legal review before go-live. [M2]

**Every call is recorded.** Each LLM call records the run, the LLM
identifier, the prompt version, the sampling settings where the service
exposes them, the tokens in and out, and its cost in US dollars as reported
by the service or computed from its published price. A local call records
tokens and wall time and a cost of zero, with its GPU time counted against
the GPU budget. [M2, requirement Q17]

## 6. Secrets

- **Where they live.** Each credential is in
  `~/.config/keys/<provider>.env`, mode 0600, outside the repository, on the
  machine that uses it: padme holds the keys for paid services; doudou holds
  only those its own sessions need (the repository-scoped GitHub token).
  [M2]
- **Providers in use.** LLMs: `openrouter`; a direct provider key only when
  a role uses one. Search and bibliography: `openalex`, `tavily`,
  `semanticscholar`. Archiving: `archive` (Internet Archive account). Forge:
  `github`, with the repository-scoped token only. Off-site copy: `zotero`
  (the document store from M4). Deposit: `zenodo` [M3b]. [M2 unless
  stated]
- **The reading rule.** A tool names the provider and the variable it needs
  and reads that one value immediately before the authenticated call,
  through `scripts/pipeline_keystore.py` in Python or a command
  substitution scoped to one process in shell. No value is exported to a
  session, written to `.env`, passed as a command argument, or copied into a
  log, run report, ticket, commit, pull request or release. A run report
  names the provider and the LLM, never the key. [M2, requirement C9]
- **Missing key.** A run whose key is absent does not fall back to another
  paid provider silently: it stops before its first paid call and reports
  which provider's key is missing. [M2]
- **Leak.** A credential found in any tracked file, report or log is
  revoked at the provider first, then removed from history; the incident is
  recorded without the value. [M2]

## 7. Budgets

A budget is declared before a run, in its report header, and enforced by the
run: a paid call that would take the run past its budget is not made, and
the run stops, reports what it completed, and leaves the rest pending
(requirement C4). The amounts below are **proposed defaults, for the
author to set**. Each says whether its basis is measured, derived from
measurements, or a judgement. [M2]

### 7.1 The measurements

- **Size of the held documents** (measured on padme, on the document store
  of record: 278 objects, 282 MB; the 91 other snapshots are kept under the
  comparator data directories; the counts add up in requirements DA2). The
  84 PDFs have a text layer of 11.65 million characters in all (median
  54,000 per document, 90th percentile 463,000, largest 947,000). The 194
  other objects (HTML, spreadsheets, structured records) total 31.9 MB of
  bytes; their text share was not measured.
- **Tokens** (derived). At about four characters per token for English, the
  PDFs hold about 2.9 million tokens; assuming the non-PDF objects yield 10 to
  20 % of their bytes as text, they add about 1 million: about 4 million
  tokens in all, a floor since Vietnamese and Indonesian text uses more
  tokens per character.
- **The M2 assisted pass.** The readers read only the 115 documents with a
  snapshot and nothing extracted (requirements DA2); the 254 already
  extracted are replayed without an LLM (extraction § 10). The paid spend
  is the arbiter's calls on what the local readers leave open, the
  transcription of the held scan and the selection runs; none is measured
  yet. The first calibration run measures the arbiter's rate and cost, and
  the first run of the installed readers their GPU time.
- **Local LLM throughput** (measured on padme, short-record screening with
  thinking disabled): about 1.7 records per second, against about 19
  records per second for a hosted small LLM with six workers. Throughput on
  long documents is measured by the first run of the installed readers.
- **OpenAlex** (measured): the project key carries a free allowance of
  USD 1 per day, reported in every response header with the remaining
  balance and the reset time; a full 88-query search pass costs about
  USD 0.25 to 0.30 (derived). A prepaid balance exists and belongs to the
  corpus work of the same repository.

### 7.2 Proposed amounts

| Budget | Proposed default | Basis |
|---|---|---|
| Paid LLM spend per document (arbiter and hosted transcription) | USD 3 | Judgement: the arbiter reads a few pages per escalated item; revised on the first calibration run |
| Paid LLM spend per run | USD 20 for an ordinary batch; USD 60 for the full M2 pass | Judgement, revised on the first calibration run |
| Paid LLM spend per calendar month, all vendors | USD 150 | Judgement: the arbiter's calls, the selection runs and the M3a discovery rounds |
| Paid LLM spend per vendor per month | USD 80 | Judgement: a cap on the arbiter's maker |
| Paid web search (discovery) per campaign | USD 25, and a query count per round declared in the round's protocol | Judgement: no measurement in the repository |
| OpenAlex | Within the free USD 1 per day; no draw on the prepaid balance | Measured allowance; the prepaid balance is not the Observer's |
| Internet Archive captures | No money; captures paced and stopped on the service's rate-limit responses | The account is free |
| Local GPU time per run | 10 hours of wall time; runs longer than 2 hours start in the evening or at the weekend | Judgement: the service is shared, and the author's daytime sessions need it responsive |
| Model selection and calibration on OpenRouter | USD 20 per selection run, counted in the monthly budget | Judgement: candidate models of 12 to 16 GB are economy-tier priced, and the reference answers are a few hundred items |

**Development sessions are not run spend.** The coding agents that build
the Observer work under the author's subscriptions, not under per-call
billing; the number of sessions and their wall time are what the author
can report. [M2]

**Reaching a budget.** At the per-document budget the document is left
pending, with the reason in the run report. At the per-run budget the run
stops and reports. At the monthly or per-vendor budget, no new paid run
starts until the author raises it or the month turns. A run never switches
vendor to stay under a vendor budget without the author's agreement, since
that changes the method. [M2]

## 8. Logging spend and compute time

**The run report.** Every run writes one report, committed with its
products on the run's branch. It gives: run identifier, job, commit of the
code, machine, start and end times, declared budgets, spend per vendor and
per LLM with token counts, GPU wall time, documents or rounds attempted,
completed, failed and deferred with their reasons, the number of items
that stood on the readers' agreement, went to the arbiter and ended
undetermined, the calibration version in force, the declared scope, its
notes and the part plan of each snapshot read, any reviewed locator or
layer mapping (extraction §§ 5, 9), and a final state (section 10). The
report of a build lists the trails that do not resolve. A run that found
nothing says so. [M2 for extraction runs; M3a for discovery rounds,
requirement Q14]

**Compute time.** Each run records its local GPU wall time and its paid
spend per document; the document's class, type and extraction method are
joined later, since classes are assigned only from M3a, so that the M3b
release can state spend and compute time per document class, document type
and extraction method (requirement Q15). [M2]

**Monthly tally.** Spend per vendor against the monthly budgets, and GPU
time, are tallied from the run reports and shown to the author. [M2 as a
computed table; M4 on the Observatory's supervision view]

## 9. Backups and recovery

**What is where.**

| Content | System of record | Copies |
|---|---|---|
| Code, rules, tickets, ledger tables (the register included), run reports | The git repository | GitHub; every checkout; padme's machine backup |
| Document bytes (the document store and the comparator data directories) | DVC cache on padme | The DVC remote, on the same padme disk; the Zotero group (each snapshot, off-site); padme's machine backup (off-site) |
| Retained text layers and raw model responses | DVC cache on padme, beside the document bytes | The DVC remote; padme's machine backup; a lost layer is regenerated only by the same adapter version |
| Public copies of document addresses | The Internet Archive | — |
| A frozen release | The release deposit [M3b] | Zenodo |
| Local LLM weights | Downloaded | Re-downloadable |

Two copies off the disk are required because the DVC cache and the DVC
remote share one NVMe partition, and the Internet Archive holds only the
documents it captured.

**The off-site copy: Zotero.** Each snapshot is uploaded, one way, to the
project's Zotero group, with its SHA-256 in the item's metadata, when it is
pushed to DVC; the objects pushed before the rule are uploaded once. The
group is private, its attachments visible to members only. No job reads
from Zotero: DVC stays the working store until the document store moves
behind the same interface at M4 (section 11). [M2]

**The machine backup.** padme runs a nightly restic backup of
`/home/haduong`, `/data` and `/etc` to a Hetzner Storage Box, keeping 7
daily, 4 weekly, 12 monthly and 5 yearly snapshots. It covers the DVC cache
and remote, the retained layers and the repository checkouts. The test of
recovery reads the date of the latest backup snapshot, so that a backup
that stops silently is seen. [M2]

**Recovery.** [M2]

- Code and ledger: clone from GitHub.
- Document bytes: restore the DVC remote on padme from the machine backup,
  or object by object from the Zotero group by SHA-256, then check every
  object against the hashes in the DVC pointers and the SHA-256 of
  `snapshots.csv`; an object that fails is refetched from its publisher or
  its Web Archive copy, as a new retrieval, never substituted silently.
- A recovery is recorded as a run with its report, listing what was
  restored, refetched and lost.

**Test of recovery.** At M2, one snapshot is restored from each copy, the
Zotero group and the machine backup, and checked against its hash. Once per
milestone the author or an agent restores the document store into an empty
worktree on padme from the machine backup and runs the replay; it must
pass. [M2, then before the M3a freeze and before each release]

**Handover note.** Before the first release identifier is minted, a note in
the repository states where each credential lives (by provider, never the
value), who owns the repository, the release deposits and the Observatory's
domain, and the restore steps of this section, so that the cited releases
stay retrievable and a withdrawal (results § 9) can be carried out when the
author cannot act. It is reread at each release. [M3b]

<!-- batch-2 X-24: pending author decision -->

## 10. Failure handling

**Run states.** A run ends `complete` (everything in its scope done or
disposed of), `partial` (stopped by a budget, a cap, an interruption or an
error, with a list of what remains), `failed` (stopped before producing a
usable product), or `not started` (a precondition failed: SSH, a missing
key, `uv` not found, the store absent). The report states which. A run
whose `runs` row is still `running` when its session is gone is closed as
failed (storage contract § 1). [M2]

**Partial runs are never published.** A partial run's completed documents
may be admitted through its pull request, each whole; the documents it did
not reach stay pending and are the input of the next run. No extraction is
admitted in part (extraction § 6.1). A release and an Observatory
publication are built only from a state in which every run in the release's
scope is complete. [M2 for admission; M3b for releases]

**Resumption.** A rerun over the pending list continues where a partial run
stopped; idempotence (extraction § 10) guarantees that documents already
extracted are not extracted or renumbered again. [M2]

**Blocked sites.** A fetch refused by a site is recorded as `blocked` with
the attempt, and does not advance the last successful coverage. It is
retried at the next rung (the browser's cookies, then the author's manual
save on padme's browser), never by circumventing the check. What remains
blocked joins the unreachable list (collection § 8). A change of a site's
robots rules or terms is flagged in the report. [M2 for the record of an
attempt; M3a for the rungs and the unreachable list]

**Service failures.** An LLM service that errors or times out is retried
with backoff a bounded number of times (default: three), then the document
is left pending with the error recorded. An answer that does not parse is a
failed reading, never a partial one. The local LLM returning empty output
is checked first for the thinking setting. [M2]

**Budget reached.** The run stops as a partial run (section 7). [M2]

**Supervision and deferral.** At M2 and M3, the launcher of a run (an agent
or the author, usually from doudou) watches it to its end or reads its report
afterwards. When `ssh padme` does not answer, the run is not attempted
elsewhere: it is deferred, and the deferral is said in the session and noted
on the ticket it serves. At M4, a check from doudou reads the reports of
scheduled runs, flags a run whose report is missing, late or not complete,
and surfaces it in the end-of-day wrap-up; a scheduled run that padme could
not start leaves a report saying so. [M2 for hand-launched runs; M4 for
scheduled runs]

## 11. What changes at M4

M4 is the operation of what M2 and M3 built. None of the following is built
earlier.

- **The pass launcher.** A persistent checkout on padme outside the
  worktree area, fast-forwarded to `origin/main` before each pass, with one
  wrapper per pass and one report per pass in the format of section 8. A
  pass refuses to run while the previous result of the same pass is still
  unreviewed. Scheduled by cron, which needs no linger.
- **Schedules.** Link-rot check and capture retry monthly, on the first of
  the month (`make jetp-link-check jetp-web-archive jetp-link-views`);
  discovery beyond the known sites weekly, by an agent on the local LLM,
  after a pilot comparing its recall and false positives with a hosted agent
  on one country; recollection of living documents at the frequency their
  site files declare; series watched for their next expected issue. Every
  pass proposes a pull request; nothing is admitted or published
  automatically.
- **The storage seam used.** Every retrieval already writes through the
  single document-write function; at M4 the document store behind it moves
  to a Zotero group library, the pipeline reading a committed export, never
  live Zotero.
- **Drift register.** A register of what moves under the Observer between
  releases, reviewed at each release: sources (addresses, formats, a site
  that stopped publishing), publishers' schemas and field lists, the models
  behind each role and their prices, sites' terms and robots rules, and the
  ontology's terms. Each entry names what it affects and the rule or
  method version that answers it.
- **Adaptive cadence.** A living document is refetched at an interval set
  from its observed rate of change, within the weekly maximum of
  requirement N6.
- **Recalibration.** Before a scheduled pass whose models or prompts
  changed, the readers and the arbiter are scored again on the held-out
  reference answers; the budgets of section 7 are revised on the measured
  cost of the first run.
- **Supervision view.** Changes between runs large enough to check, and the
  monthly tally of section 8, appear on the Observatory's supervision pages.
- **Horizon.** The Observer is maintained through 2030, with an extension
  decision in 2028 and an archived final release at the end, after which
  every cited release stays retrievable (requirement C10; the archiving is
  in [results and releases](jetp-results.md)).
- **Shared code.** Code shared with AEDIST moves to `libs/` when a second
  consumer runs on it.

## 12. The M2 and M3 slice

Runs launched by hand on padme with an identifier, declared budgets, a
`tmux` session when long, and a report with a final state; bytes and LLMs on
padme, data one way, DVC pushed from padme after review, two copies of
document bytes off padme's disk, each restored once; the repository gates of
section 4; two local readers from different model families and a hosted
arbiter on every LLM judgement, every call recorded with its cost; budgets
enforced per document, per run, per month and per vendor; secrets read at
use only.

## 13. Open questions

Each has a default, applied unless the author decides otherwise.

- **Budget amounts** (section 7.2). Default: the table as proposed.
- **Paid web search provider for discovery.** Default: the search API whose
  key is already in the keystore, under the per-campaign budget.

## 14. Checks an operation must pass

| Constructed situation | Correct outcome |
|---|---|
| `ssh padme` times out when a run is due to start. | The run is not attempted on doudou; it is deferred, and the deferral is said in the session and noted on its ticket. |
| A run is launched over SSH and fails with "uv: command not found". | The report says `not started`, not `failed`; the command is corrected with the PATH prefix. |
| The author finds a relevant report on the laptop and has the PDF in the download folder. | The document enters as a register change on a branch; padme fetches it, or the author saves it through padme's browser on doudou's screen. No file is copied from doudou to padme. |
| A run reaches its USD 20 budget after 40 of 60 documents. | No further paid call is made; the report says `partial`, lists 20 documents pending, and the 40 completed documents may be admitted whole through the pull request. |
| The monthly tally shows USD 80 spent with one vendor. | No new run using that vendor starts this month; the run does not switch vendor on its own. |
| The readers of a run leave 240 items open. | All 240 go to the arbiter within the run's budget; at the budget the run stops with the rest pending; nothing is queued for the author and nothing is admitted unjudged. |
| A run is killed midway by a power cut. | The report, written as the run goes, has no final state and is treated as failed; the rerun takes the pending list, and nothing already admitted is renumbered. |
| An extraction run completes over half the countries of a release's scope. | No release and no Observatory publication are built until every run in the scope is complete. |
| padme's disk fails. | Code and ledger are cloned from GitHub; document bytes are restored from the machine backup or the Zotero group and checked against their hashes; an object that fails is refetched as a new retrieval and the losses are listed in a recovery report. |
| The latest machine backup snapshot is two weeks old at a test of recovery. | The test fails and the backup is repaired before the milestone is accepted. |
| A run writes 3,000 rows and opens its pull request. | The gate runs the validator, the controls, replay and idempotence, and reads the run report; the cross-family reviewer reads the report and a sample of traceability chains, not the 3,000 rows. |
| The author, browsing results sorted by confidence, overturns 3 of 80 low-confidence items. | Each decision is recorded as a judgement of the role author, beside the readers' and the arbiter's answers, superseding the earlier judgement with his reason; no run waited for him. |

## 15. Runbook: facts of the current machines

The facts below describe padme and doudou as they are today. They are not
rules: they change without a change of the specification.

- **Tool path.** `uv` is at `~/.local/bin/uv`, not on the non-interactive
  PATH. A command sent over SSH prepends it:
  `ssh padme 'cd ~/CNRS/projets/actifs/climate-finance-het/<worktree> && PATH=$HOME/.local/bin:$PATH make <target>'`.
  "uv: command not found" means the run has not started.
- **Local LLM service.** `llama-server.service` (llama.cpp, system unit)
  serves Qwen3.8-27B, quantised Q4_K_M, with a context of 131,072 tokens on
  `127.0.0.1:8080`, all layers on the two GPUs, until the two selected
  readers of section 5 replace it. Requests send
  `"chat_template_kwargs": {"enable_thinking": false}`, without which the
  model spends its output on reasoning and returns nothing parsable; an
  empty answer is checked for this setting first (section 10).
