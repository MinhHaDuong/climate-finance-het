# JETP Observer: operation

Status: draft for author review; budget amounts are proposed defaults awaiting the author's decision.

This document says how the JETP Observer is run: on which machine each job
runs, who launches and supervises it, how the repository governs what
development agents may do, what each run may spend, where secrets live, what
happens when a run fails, and how the record is backed up and recovered. It
is the one document of the specification that names machines, commands,
schedules and budgets concretely; the conceptual documents
([collection](jetp-collection.md), [extraction](jetp-extraction.md),
[fusion](jetp-fusion.md)) state what must be done and leave these to it.

It serves the author and the development agents of
[purpose and requirements](jetp-requirements.md) § 3.2 (questions OP-1 to OP-6) and the constraints C1 to C4, C9 and C10
there, with Q14, Q15, Q17 and Q19. The Observatory, the public website, is
also the author's instrument for noticing anomalies (requirement Q20); how
it shows them is the [presentation](jetp-observatory-presentation.md)'s
business.

Every rule carries, in square brackets, the milestone that needs it: M2 (an
extraction pipeline that works on every document held), M3a (discovery to a
cutoff, then the register frozen), M3b (the new documents extracted,
matched and released), M4 (operation), or later. The rule is "something
that works first, then M4 polishes": M2 and M3 need only what makes a run
correct, reproducible and affordable. Scheduling, unattended refresh,
link-rot checks, the pass launcher and the move of the document store to
Zotero are M4 and are not built before it.

## 1. Principles

**Hand-launched runs until M4.** Until M4 every run is launched by a person
or an agent in a session, watched to its end, and reported. Nothing runs on
a timer. [M2]

**One run, one report, one budget.** A run is one bounded execution of one
job (an extraction batch, a discovery round, a fetch run, a replay). It has an
identifier, declares its budgets before it starts, stops when a budget is
reached, and ends with a report, including when it fails or finds nothing.
[M2]

**Bytes and LLMs on padme, supervision anywhere, data one way.** Jobs that
read document bytes or call an LLM run on padme. Data produced
there reaches the laptop by the repository and DVC, never the other way.
[M2]

**The repository is the control plane.** Every change to code, rules or
data enters the record through a branch, a review and passing tests. A
decision is a ticket entry or a commit message, not a conversation. [M2]

**No machine judgement waits for the author.** Runs work in complete
autonomy: every item ends with a stance, possibly undetermined, and a
calibrated likelihood and confidence, recorded with every reader's and the
arbiter's answer. Nothing is queued for the author; the results are served
sorted by likelihood and confidence, and he examines them when he chooses.
Only a question that changes what a term or the contract means goes to
him, with the panel's stance. [M2]

## 2. Machines

| Machine | What it is | What it holds | What runs there |
|---|---|---|---|
| padme | Personal workstation: two consumer GPUs (RTX A4000 16 GB, RTX 3060 12 GB), 125 GB RAM, one 953 GB NVMe disk | The primary checkout, the DVC cache and the DVC remote, every document byte, the two local LLM readers (one per GPU), the credentials for paid services | Every job that reads document bytes or calls an LLM: fetch runs, extraction runs, replay, discovery rounds, matching to CRS and IATI, the release build, the Observatory build, the full test suite |
| doudou | Laptop | A checkout of the repository; DVC data only as pulled from padme | The author's sessions; development agents editing code, rules and tickets; the fast test tier; supervision of runs on padme; viewing padme's browser on its own screen |

- **padme runs the jobs.** A job that reads bytes or runs LLMs is launched on
  padme, in a git worktree or, from M4, in the persistent checkout of
  section 11. A development agent on doudou reaches padme over `ssh padme`.
  [M2]
- **doudou never has to hold all the bytes.** No job, test gate or review
  step requires the laptop to hold the document store. The fast test tier
  (`make check-fast`, `make lint`) needs no archived bytes and is the gate
  that runs on doudou; the slow tier (`make check`) runs on padme. The fast
  tier on doudou does not resolve locators, which needs the bytes and the
  pinned text adapter. [M2]
- **The primary checkout on padme is not a work area.** It may sit on
  another session's branch. Runs use a worktree (populated with
  `make jetp-data`, a local copy from the DVC cache with no network), or
  from M4 the persistent checkout. [M2]
- **Non-interactive shells.** `uv` is at `~/.local/bin/uv` and is not on the
  non-interactive PATH. A command sent over SSH prepends it:
  `ssh padme 'cd ~/CNRS/projets/actifs/climate-finance-het/<worktree> && PATH=$HOME/.local/bin:$PATH make <target>'`.
  A run that fails with "uv: command not found" has not started and is
  reported as not started, not as failed. [M2]
- **Long runs survive the session.** padme has no systemd user linger, so a
  user timer or `systemd-run --user` unit dies when the last session closes.
  A run expected to outlast the launching session runs inside a named
  `tmux` session on padme (one per run, named after the run identifier) and
  writes its progress to its report as it goes. [M2]
- **The local LLM is a shared service.** `llama-server.service`
  (llama.cpp, system unit) serves Qwen3.8-27B, quantised Q4_K_M, with a
  context of 131,072 tokens on `127.0.0.1:8080`, all layers on the two GPUs.
  Other projects use it. A run never restarts or reconfigures the unit;
  more parallel slots, tool-calling flags or another LLM require the
  author's agreement first. Requests send
  `"chat_template_kwargs": {"enable_thinking": false}`, without which the
  LLM spends its output on reasoning and returns nothing parsable. [M2]

## 3. Data flow

**One direction.** Document bytes, DVC outputs and run products are created
on padme and travel to doudou by `git pull` and `dvc pull` (or
`make corpus-sync`). Nothing is copied from doudou to padme: no `scp`, no
`dvc push` from doudou. [M2]

**New sources found on the laptop travel as changes, not as data.** A
document the author spots while working on doudou enters as a register or
query change on a branch; padme then fetches it. [M2]

**Documents behind a browser check are collected on padme, displayed on
doudou.** When a site demands a human check or a login the author holds,
the author opens padme's browser on doudou's screen (remote display), passes
the check in person, and the bytes land on padme. The browser rungs of
collection (`make jetp-harvest-blocked`, which reuses the browser's
cookies for the hosts concerned, and `make jetp-collect-downloads`, which
records files the author saved) therefore run on padme, against padme's
browser profile. [M3a; the documents held at M2 are already on padme]

**DVC is pushed from padme only, after review.** New objects are tracked
with `make jetp-documents-track` and pushed from padme once the branch that
records them has been reviewed (redirects, invalid content and dry searches
checked). [M2]

**Recovery is the one exception.** Restoring padme from the backup copy
(section 9) moves bytes towards padme. It is an explicit act of the author,
verified by hash against the DVC pointers, and never a synchronisation.
[M2]

## 4. The repository as control plane

The Observer is built and run through its repository. Development agents
write the code and launch the runs; tickets record decisions and their reasons;
tests and reviews by LLMs from another vendor gate every change; the
author steers, arbitrates and accepts each milestone (requirements § 3.2).

**Gates.** [M2]

- Every change lands through a branch and a pull request; `main` is not
  written directly.
- The merge gate is `make check-fast` and `make lint`; a change that writes
  data, DVC outputs or deposits also passes the full `make check` on padme
  before merging.
- A change is reviewed by an LLM of another family than the one that wrote
  it (requirement Q19), and the review's findings are answered on the pull
  request before merge.
- The ticket a change serves is closed in the same pull request.

**Run outputs are changes like any other.** A run writes its products
(statements, dispositions, candidates, retrievals, its report) on a branch
and opens a pull request. Nothing a run produces reaches `main`, the ledger
of record or the Observatory without that review. [M2]
<!-- wave-1 W1-20: pending author decision (a lighter gate for run-output pull requests) -->

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
- Admit a document, accept a milestone, freeze the register, cut a release,
  or publish the Observatory (`make jetp-observatory-publish` is run by the
  author, from `main`, after a release is accepted).
- Pass a site's human check, use a login the public cannot freely obtain, or
  fetch past a paywall (requirement C6).
- Restart or reconfigure the shared `llama-server.service`.
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

## 5. LLM readers and the checking rule

**Two local readers, a hosted arbiter.** An LLM judgement (a statement
extracted, a disposition proposed, a candidate triaged, a match) is made on
every item by two LLM readers on padme, from different model families,
each blind to the other. Where they agree at a calibrated likelihood at or
above the level the method declares, the result stands; where they
disagree, or either is below that level, a stronger model reached through
OpenRouter arbitrates, given both readings and the source pages. Every
item ends with a stance and a calibrated likelihood and confidence, and
nothing is queued for the author. The rules are those of extraction § 6.3,
collection § 9 and fusion § 3; this section only says what runs where. [M2 for statements extracted and document identity
judgements; M3a for discovery and triage; M3b for the other identity
judgements and for preference judgements]

**One model per GPU.** Each local reader is one model sized to fit its
card: one on the RTX A4000 (16 GB), the other on the RTX 3060 (12 GB), the
two from different families, served side by side. [M2]

**Selection and calibration before installation.** Model selection and
calibration run first on OpenRouter, over candidate open-weight models of
the sizes that fit each card, scored on held-out reference answers: lines
of the extracted documents made by hand, for extraction; the accepted and
rejected match judgements of the M1b catalogue, for matching. Each
candidate's raw self-scores are mapped to the likelihood terms of fusion
§ 1 from those scores, and a candidate that fails its positive controls is
weighted out. Only the winning pair, the best-scoring model for each card
with the two from different families, is installed on padme. The arbiter, a
stronger hosted model, is calibrated on the same answers. The scores, the
mapping and the models chosen are recorded as a method version, and no
unattended run starts before them. [M2, before the first unattended run]

**Replacing a reader.** A reader or the arbiter that is retired, repriced
or unavailable is replaced only under extraction § 6.3: the replacement
passes the controls of extraction § 12 and its calibration on the held-out
reference answers, stratified by language, before it reads, and the change
is a new method version. [M2]

**Vendor means LLM family, not billing channel.** An LLM reached through
an aggregator (OpenRouter) counts under its maker, and so does a local
model: a Qwen model counts as Alibaba. The two readers are from different
makers. [M2]

**Where each reader runs.** [M2]

| Role | Default | Alternatives |
|---|---|---|
| Reader | The selected open-weight model on padme's RTX A4000 (16 GB) | The same model through OpenRouter |
| Second reader | The selected open-weight model, of another family, on padme's RTX 3060 (12 GB) | The same model through OpenRouter |
| Arbiter | A stronger hosted model through OpenRouter, calibrated like the readers | Another hosted model that passed calibration |

A document longer than a reader's context is split into parts with their
own scope, as extraction § 6.3 provides; the largest held PDF has a text
layer of about 950,000 characters, beyond a local reader's context. [M2]

**Every call is recorded.** Each LLM call records the run, the LLM
identifier, the prompt version, the sampling settings where the service
exposes them, the tokens in and out, and its cost in US dollars as reported
by the service or computed from its published price. A local call records
tokens and wall time and a cost of zero, with its GPU time counted against
the GPU budget. [M2, requirement Q17]

## 6. Secrets

- **Where they live.** Each credential is in
  `~/.config/keys/<provider>.env`, mode 0600, outside the repository, on the
  machine that uses it. Runs happen on padme, so padme holds the keys for
  paid services; doudou holds only those its own sessions need (the
  repository-scoped GitHub token). [M2]
- **Providers in use.** LLM readers: `anthropic`, `openai`,
  `mistral`, `deepseek`, `alibaba`, `openrouter`. Search and bibliography:
  `openalex`, `tavily`, `semanticscholar`. Archiving: `archive` (Internet
  Archive account). Forge: `github`, with the repository-scoped token only.
  Deposit: `zenodo` [M3b]. Document store: `zotero` [M4]. [M2 unless
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
  of record: 278 objects, 282 MB; the 91 other snapshots, CRS and World Bank
  extracts and IATI country files, are kept under the comparator data
  directories; the reconciliation of these counts is requirements DA2). The 84 PDFs have a text layer of 11.65
  million characters in all (median 54,000 per document, 90th percentile
  463,000, largest 947,000). The 194 other objects (HTML, spreadsheets,
  structured records) total 31.9 MB of bytes; their text share was not
  measured.
- **Tokens** (derived). At about four characters per token for English, the
  PDFs hold about 2.9 million tokens; assuming the non-PDF objects yield 10 to
  20 % of their bytes as text, they add about 1 million. The held documents
  are therefore about 4 million tokens. Vietnamese and Indonesian text uses
  more tokens per character, so this is a floor.
- **Prices per million tokens, input / output** (derived by regressing the
  recorded cost on recorded tokens over the AEDIST benchmark's measurement
  log): frontier tier, Anthropic Opus 5 / 25 and OpenAI GPT-5.5 2.5 / 15;
  mid tier, Anthropic Sonnet 3 / 15 and Qwen3.7-max 2.5 / 7.5; economy tier,
  Mistral Large 0.5 / 1.5, DeepSeek V3.2 0.26 / 0.38, Gemini Flash-Lite
  0.1 / 0.4. Prices move; the run records the actual cost.
- **The M2 assisted pass** (derived). The LLM readers read only the 115
  documents with a snapshot and nothing extracted (requirements DA2); the
  254 documents already extracted are replayed without an LLM (extraction
  § 10), so a rerun of the pipeline costs nothing in LLM spend. The
  prototype run measured USD 0.03 to 0.08 per document with hosted readers;
  with a margin for parts and repair calls, the M2 pass costs about USD 15
  to 30. For scale only: a full assisted pass over every held object, reader
  and second reader each reading the whole text (about 9 million input tokens with
  prompts and 1 million output tokens), would cost about USD 42 at mid tier,
  USD 55 with a frontier pair and USD 5 with an economy pair.
- **Local LLM throughput** (measured on padme, short-record screening with
  thinking disabled): about 1.7 records per second, decoding about 95 % of
  the time, against about 19 records per second for a hosted small LLM
  with six workers. Throughput on long documents has not been measured;
  the first run of the installed readers measures it on padme.
- **OpenAlex** (measured): the project key carries a free allowance of
  USD 1 per day, reported in every response header with the remaining
  balance and the reset time; a full 88-query search pass costs about
  USD 0.25 to 0.30 (derived). A prepaid balance exists and belongs to the
  corpus work of the same repository.

### 7.2 Proposed amounts

| Budget | Proposed default | Basis |
|---|---|---|
| Paid LLM spend per document (hosted readers and arbiter together) | USD 3 | Derived: covers the largest held PDF (about 240,000 tokens) read once by a frontier pair; the median document costs well under USD 0.10 |
| Paid LLM spend per run | USD 20 for an ordinary batch; USD 60 for the full M2 pass | Derived: the M2 pass over the 115 pending documents is about USD 15 to 30, so USD 60 covers it with room for a second attempt |
| Paid LLM spend per calendar month, all vendors | USD 150 | Judgement: a full pass at frontier tier plus a partial rerun and the M3a discovery rounds |
| Paid LLM spend per vendor per month | USD 80 | Judgement: no single maker can take more than about half the month, which keeps the second vendor funded |
| Paid web search (discovery) per campaign | USD 25, and a query count per round declared in the round's protocol | Judgement: no measurement in the repository |
| OpenAlex | Within the free USD 1 per day; no draw on the prepaid balance | Measured allowance; the prepaid balance is not the Observer's |
| Internet Archive captures | No money; captures paced and stopped on the service's rate-limit responses | The account is free |
| Local GPU time per run | 10 hours of wall time; runs longer than 2 hours start in the evening or at the weekend | Judgement: the service is shared, and the author's daytime sessions need it responsive |
| Model selection and calibration on OpenRouter | USD 20 per selection run, counted in the monthly budget | Judgement: candidate models of 12 to 16 GB are economy-tier priced, and the reference answers are a few hundred items |

**Development sessions are not run spend.** The coding agents that build
the Observer work under the author's subscriptions, not under per-call
billing. Their cost is not charged to a run; the number of sessions and
their wall time are what the author can report. [M2]

**Reaching a budget.** At the per-document budget the document is split
into parts or deferred with that reason (extraction § 7). At the per-run
budget the run stops and reports. At the monthly or per-vendor budget, no
new paid run starts until the author raises it or the month turns. A run
never switches vendor to stay under a vendor budget without the author's
agreement, since that changes the method. [M2]

## 8. Logging spend and compute time

**The run report.** Every run writes one report, committed with its
products on the run's branch. It gives: run identifier, job, commit of the
code, machine, start and end times, declared budgets, spend per vendor and
per LLM with token counts, GPU wall time, documents or rounds attempted,
completed, failed and deferred with their reasons, the number of items
that stood on the readers' agreement, went to the arbiter and ended
undetermined, the calibration version in force, and a final state
(section 10). The report of a build lists the
trails that do not resolve. A run that found nothing says so. [M2 for extraction runs; M3a for discovery rounds, requirement Q14]

**Compute time.** Each run records its local GPU wall time and its paid
spend per document; the document's class, type and extraction method are
joined later, since classes are assigned only from M3a. [M2, so that the
M3b release can state spend and compute time per document class, document
type and extraction method, requirement Q15, including for the documents
extracted at M2]

**Monthly tally.** Spend per vendor against the monthly budgets, and GPU
time, are tallied from the run reports and shown to the author. [M2 as a computed table; M4 on the Observatory's
supervision view]

## 9. Backups and recovery

**What is where.**

| Content | System of record | Copies |
|---|---|---|
| Code, rules, tickets, ledger tables (the register included), run reports | The git repository | GitHub; every checkout |
| Document bytes, structured bulk data | DVC cache on padme | The DVC remote, on the same padme disk |
| Retained text layers of snapshots with admitted statements | DVC cache on padme, beside the document bytes | As for the document bytes; a lost layer is regenerated only by the same adapter version |
| Public copies of document addresses | The Internet Archive | — |
| A frozen release | The release deposit [M3b] | Zenodo |
| Local LLM weights | Downloaded | Re-downloadable |

**The gap.** The DVC cache and the DVC remote are on the same NVMe
partition of padme. A disk failure loses every document byte not otherwise
recoverable, and the Internet Archive holds only the documents it captured,
not those collected by browser or behind a check.

**Rule: a second copy off padme.** After every DVC push of document bytes,
doudou pulls them (`dvc pull data/jetp/documents.dvc`), in the permitted
direction; this copy is a backup only, which no job reads, and the laptop may
drop it without harm to operation. The author may prefer an external or
institutional disk instead; either satisfies the rule. [M2]
<!-- wave-1 W1-22: pending author decision (where the retained second copy lives) -->

**Recovery.** [M2]

- Code and ledger: clone from GitHub.
- Document bytes: restore the DVC remote on padme from the backup copy,
  then check every object against the hashes in the DVC pointers and the
  SHA-256 of `snapshots.csv`; an object that fails is refetched from its
  publisher or its Web Archive copy, as a new retrieval, never substituted
  silently.
- A recovery is recorded as a run with its report, listing what was
  restored, refetched and lost.

**Test of recovery.** Once per milestone the author or an agent restores the
document store into an empty worktree on padme from the backup copy and
runs the replay; it must pass. [M2 once; M4 per release]

## 10. Failure handling

**Run states.** A run ends `complete` (everything in its scope done or
disposed of), `partial` (stopped by a budget, a cap, an interruption or an
error, with a list of what remains), `failed` (stopped before producing a
usable product), or `not started` (a precondition failed: SSH, a missing
key, `uv` not found, the store absent). The report states which. A run
without a final state is treated as failed. [M2]

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
blocked joins the unreachable list, which is data (collection § 8). A change
of a site's robots rules or terms is flagged in the report. [M2 for the
record of an attempt; M3a for the rungs and the unreachable list]

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
not start leaves a report saying so. No run disappears in silence. [M2 for
hand-launched runs; M4 for scheduled runs]

## 11. What changes at M4

M4 is the operation of what M2 and M3 built. None of the following is built
earlier.

- **The pass launcher.** A persistent checkout on padme outside the
  worktree area, fast-forwarded to `origin/main` before each pass, with one
  wrapper per pass and one report per pass in the format of section 8. A
  pass refuses to run while the previous result of the same pass is still
  unreviewed. Scheduled by cron, which needs no linger; the alternative is
  enabling linger for the user account.
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
  live Zotero. The Zotero cloud copy then also closes part of the backup gap
  of section 9.
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

1. Runs launched by hand on padme, each with an identifier, declared
   budgets, a `tmux` session when long, and a report with a final state.
2. Bytes and LLMs on padme, data one way, DVC pushed from padme after
   review, a backup copy of document bytes off padme.
3. The repository gates of section 4, and the agents' permissions and
   prohibitions.
4. Two local readers from different model families, one per GPU,
   selected and calibrated on OpenRouter before installation, and a hosted
   arbiter, on every LLM judgement; every call recorded with its cost.
5. Budgets enforced per document, per run, per month and per vendor;
   GPU time logged per run; secrets read at use only.

## 13. Open questions

Each has a default, applied unless the author decides otherwise.

- **Budget amounts** (section 7.2). Default: the table as proposed.
- **Backup location.** Default: a copy on doudou pulled after each push;
  alternative, an external or institutional disk.
- **Paid web search provider for discovery.** Default: the search API whose
  key is already in the keystore, under the per-campaign budget.

## 14. Checks an operation must pass

| Constructed situation | Correct outcome |
|---|---|
| An agent on doudou starts an extraction run while the laptop holds no document bytes. | The run is launched on padme over SSH; nothing requires the bytes on doudou. |
| `ssh padme` times out when a run is due to start. | The run is not attempted on doudou; it is deferred, and the deferral is said in the session and noted on its ticket. |
| A run is launched over SSH and fails with "uv: command not found". | The report says `not started`, not `failed`; the command is corrected with the PATH prefix. |
| The author finds a relevant report on the laptop and has the PDF in the download folder. | The document enters as a register change on a branch; padme fetches it, or the author saves it through padme's browser on doudou's screen. No file is copied from doudou to padme. |
| A run reaches its USD 20 budget after 40 of 60 documents. | No further paid call is made; the report says `partial`, lists 20 documents pending, and the 40 completed documents may be admitted whole through the pull request. |
| The monthly tally shows USD 80 spent with one vendor. | No new run using that vendor starts this month; the run does not switch vendor on its own. |
| The readers of a run leave 240 items open. | All 240 go to the arbiter within the run's budget; at the budget the run stops with the rest pending; nothing is queued for the author and nothing is admitted unjudged. |
| The two local readers read a document. | They are from different makers, one per GPU; each call records tokens and GPU time with a cost of zero. |
| A candidate reader fails its positive controls during selection on OpenRouter. | It is weighted out and never installed on padme. |
| A run is killed midway by a power cut. | The report, written as the run goes, has no final state and is treated as failed; the rerun takes the pending list, and nothing already admitted is renumbered. |
| An extraction run completes over half the countries of a release's scope. | No release and no Observatory publication are built until every run in the scope is complete. |
| An agent needs more parallel slots from the local LLM. | It asks the author; it does not restart `llama-server.service`. |
| The Anthropic key is missing on padme. | The run stops before its first paid call and reports the missing provider; it does not fall back to another vendor. |
| A run report is about to include a request header with an API key. | The report names the provider and the LLM only; the key never appears. A key found in a tracked file is revoked first, then removed. |
| An agent's branch adds 12 new document objects. | They are tracked and pushed to DVC from padme only after the branch's review passes; doudou then pulls them as the backup copy. |
| padme's disk fails. | Code and ledger are cloned from GitHub; document bytes are restored from the backup copy and checked against their hashes; an object that fails is refetched as a new retrieval and the losses are listed in a recovery report. |
| The author, browsing results sorted by confidence, overturns 3 of 80 low-confidence items. | Each decision is recorded as a judgement of the role author, beside the readers' and the arbiter's answers, superseding the earlier judgement with his reason; no run waited for him. |
| An agent proposes to publish the Observatory after merging a run. | It does not: publication is the author's act, from `main`, after the release is accepted. |
| At M2, someone proposes a weekly cron job for discovery. | Declined as M4; M2 and M3 runs are launched by hand. |
