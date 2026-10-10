# REL ingestion pipeline redesign: design note

Draft of 2026-10-10 for author review. Nothing here is built, filed or merged.
Each decision carries a label: **author-decided**, **MOE-recommended** (needs
the author's yes) or **default**. Counts are quoted from tickets and notes with
their date; none was re-measured for this note. Estimated prices are marked
"estimate".

## 1. The pipeline

```
N upstream databases
   -> N harvesting lanes
   -> Pool of Records
   -> Deduplicate
   -> Pool of Works
   -> Filter on DataCite metadata completeness
   -> Scoring: expert A, expert B, arbiter on divergence
   -> Alpha-cut: final set of at most 10,000 works

Gavard set: hand-chosen, verified, sealed; calibrates the alpha-cut
Test set: 50 positives, 50 non-obvious negatives, hand-picked, sealed
Shot set: a few positive and negative examples, outside both sealed sets
```

One rule governs the whole chain (existing memory, **author-decided**): pool
every source raw and screen once, with one rule. No record enters a corpus
screened by a different rule.

## 2. Stages: what exists, what changes

### 2.1 Lanes and Pool of Records

Lane deliveries t1530, t1650, t1651 (Gavard-Schoch), t1652, t1653, t1790,
t1810 (RePEc, 79,522 records) and the catalogue lane follow the intake
contract (`docs/rel-intake-contract.md`). Ticket 2049 regenerated four of them on
2026-10-09, which changed `member_record_ids` and the author fields. The pool
of records had 426,636 rows on 2026-10-09. ISTEX recovered 81,051 abstracts of
148,437 DOIs queried (ticket 2046).

Citation chaining becomes one more lane, with no separate screening
(**MOE-recommended**, section 4).

The journal summaries lane (t1650, `sommaires`) is turned off (**author-decided**
2026-10-10); section 7 gives the evidence.

### 2.2 Deduplicate to Pool of Works

Dedup version 2 is merged but not the default (PR 1750, 2026-10-09). A working
paper and its published article are one work (**author-decided**), with a window
of -1 to +5 years and lane links overriding it. Works: 389,291 under version 1,
385,432 under version 2 with the rule on. The migration table lists 64,344
version-1 keys that disappear. Remaining: stage B2a (build the label migration in
scratch), then B2b (flip the default, DVC push), which needs the author.

If labels no longer carry the pipeline, the migration shrinks to a mapping for
the old labels used as a check (section 5).

### 2.3 Filter on DataCite metadata

Ticket 2043 holds the profile: identifier, creator, title, venue identity,
publication year, resource type (**author-decided**). A platform name in the
journal field never counts as a venue. On the enriched pool (2026-10-09, scratch)
the six-field profile excludes 22,159 works (5.7%). Venue is the largest
remaining cause: 12,042 works have no venue at all. The profile is still a
counting view; it does not yet gate any model call.

The author prefers an abstract-equivalent field as mandatory. The data say
otherwise today: 76,261 pool works still lack an abstract after ISTEX (67,386
with a DOI, 8,875 without), including serious journals. Crossref adds 0.5% and
Semantic Scholar about 2%, so the hole will not close by harvesting.
Two options, no decision yet:

| Option | Effect | Risk |
|---|---|---|
| Abstract optional in the profile; scorer sees title, venue and year | keeps the first act (a third of pre-2007 included works have no abstract, memory 2026-10-07) | weaker scoring for these works |
| Abstract mandatory | clean input for the scorer | drops serious journals; biases against 1990-2006 |

**MOE-recommended**: optional, with a recorded `no_abstract` flag and the
scorer's calibration reported separately for works with and without one.

### 2.4 Scoring

One structured-output pass per expert over about seven predicates (the predicate
list is not yet written; see section 3). Experts: Haiku (Anthropic) and Luna
(OpenAI), two vendors, hence decorrelated. A third reader arbitrates:

- Each model's probabilities are idiosyncratic, so scores are never averaged
  across models (**author-decided**). Each model gets its own cut, calibrated on
  the sealed sets.
- A work is divergent when the two models fall on opposite sides of their own
  cuts. Only divergent works are rescored (**author-decided**); a band around
  each cut is added only if the sealed sets show it is needed.
- The arbiter is a local model constrained with llguidance, with an explicit
  prompt and positive and negative few-shots. Whether a local model reads
  non-English well enough is to be measured, not assumed (**author-decided**).
  Fallback: a third API vendor.

### 2.5 Alpha-cut

Keep at most 10,000 works. The Gavard set is verified, sealed, then used to fix
the cut. The sealed 50/50 set tests it. Whether this calibration works, and how
many works it yields, is open (section 3).

## 3. Unknowns

| Unknown | Why it matters | How it resolves | Estimate |
|---|---|---|---|
| The seven predicates are not written | the scorer has no spec; calibration is meaningless without it | author drafts, trial freezes | 2-3 author-hours |
| Does calibrating on the sealed sets give a usable cut? | the Gavard set is positive-only; recall can be set, false positives need the negatives | trial: recall and size at each model's cut on the test set | trial below |
| Size of the output | the cut may give far more or fewer than 10k | count on the filtered pool after calibration; reference only: the old pipeline kept 7,499 fully graded works and labelled 11,982 `icf` before corrections | known after the trial |
| Divergent share | sets the arbiter's volume and the rescore cost | measured on the sealed sets, extrapolated | guess 5-20% |
| Local arbiter on non-English | the hardest cases may be non-English and first act | trial, with and without few-shots | half a day |
| Precision of the claims | 50 per class gives a Wilson interval of about 0.86 to 0.99 at 48 of 50 | stated in the report; small effects are noise | none |
| No-abstract works | 76,261 works; scoring on metadata only | separate calibration | in trial |
| Chaining volume | round 1 added about 208k works; scoring cost scales with them | scoring is cheap; the cost is gating | see 5 |

Trial design (**MOE-recommended**, trial itself accepted by the author): run
Haiku and Luna on the Gavard set and the 100-work test set; calibrate each
cut on the Gavard set plus a draw of clear old `out` works as negatives; run the
arbiter on the divergent cases with and without few-shots; report recall at the
cut, divergent share and per-language results. Few-shots come from a separate
shot set and never from a sealed set. The sealed files are hashed before any
model run, one line per work giving the reason for the pick. Paid cost,
estimate: a few USD. Author time: the shot set and the predicate list.

## 4. What changes in the current plan

- **Retired** (**author-decided** 2026-10-10): the staged screening of the
  `t1654-citation-chaining` branch (design B, Stage 2, Luna facet waves,
  correction and waiver chain) and the discipline catch-up as separate stages.
  Scoring replaces them.
- **Kept**: the 1654 collector (`scripts/_rel_chaining.py`), its seed roster and
  round-1 records, delivered as a lane.
- **Waits**: round 2 of chaining chooses its frontier from the new scores
  (**MOE-recommended**).
- **Split of 1654** (**author-decided** 2026-10-10, tickets filed in PR 1754):
  1654 is a tracker. Children: 2061 finish and archive the round-1 merge on
  dedup version 1 and land the collector as a lane; 2062 wind down the screening
  half (section 8); 2060 the scoring calibration trial (child of 0700); 2063
  round 2 after scoring exists, blocked by 2060 and 2061. The earlier A/B/C split
  is superseded. The staged screening half is retired (**author-decided**
  2026-10-10); its ledger was frozen the same day.

## 5. Reuse and lessons

### Data

| Asset | Verdict | Condition |
|---|---|---|
| Lane deliveries of 2026-10-09 | reuse | none |
| Pool builder, dedup v2, migration table | reuse | flip waits for B2b |
| ISTEX abstracts (81,051) | reuse | none |
| Venue tables and venue facet | reuse | feeds the profile and scorer |
| 1654 round-1 records and edges (about 208k works) | reuse as a lane | stay unscored until the new scorer exists |
| Old stage-1 and stage-2 labels | reuse as a cross-check and as a source of clear negatives, not as truth | the pipeline above must not inherit their waivers |
| `rel_dimensions.csv` (11,645 works) | reuse as a comparison set | none |
| Haiku Stage 1 batch results (205,448 works) | cross-check only | different prompt |
| Staged runners, metering and liability machinery | retire | the scoring runner stays small |

### Lessons carried over

- Intersect inputs before any paid run; two overlapping inputs cost about
  USD 5.9 derived (memory 2026-10-07).
- Probe the OpenAI credit three times; treat `insufficient_quota` as fatal, never
  as a retryable 429.
- A judge repeating its own `unsure` is not a vote; use another vendor. Sol returned
  `unsure` 83% of the time on its own unsure works.
- Local Gemma QAT lost non-English; llguidance works (memory). Both frame the
  arbiter trial.
- The old pipeline accumulated waivers (296 stage-2 residues, 59 title-less
  works, the waived final audit) at its hand-offs; fewer stages mean fewer.
- The 1654 branch grew to 28 commits and about 2,500 lines of mostly metering and
  recovery code. The new runner should be a small script, with batch
  accounting reused where it already works.
- A cited number traces to an archived pipeline output; a count that moves
  between passes is an alarm.
- Nothing from the sealed sets appears in a prompt.

## 6. Proposed sequence

| Step | Content | Author | Spend (estimate) |
|---|---|---|---|
| 0 | this note, reviewed | review | none |
| 1 | predicates written, Gavard set verified and sealed, 50/50 set and shot set picked and hashed | 3-6 hours | none |
| 2 | calibration trial | read the report | a few USD |
| 3 | go or revise the design | decision | none |
| 4 | scoring on the filtered pool; the lane for chaining round 1 delivered in parallel | go for paid calls | roughly USD 60-135 for two experts over about 400k works, central about USD 90 (derived, section 9; the first draft said USD 15-25 and omitted Luna's reasoning cost) |
| 5 | arbiter on divergent works, alpha-cut, count | review the set | 5-20 hours local, or USD 2-10 (Luna-class) to 12-100 (frontier-class, assumed price ratio) with an API third vendor (section 9) |
| 6 | chaining round 2 from the new frontier | decision | as step 4 |

The deadline is about 2026-12-06 (ticket 0700). Steps 0 to 3 fit in the next
week if step 1 does; the later steps scale with how many works the filter lets
through.

## 7. Lane analysis and the decision on journal summaries

Measured on 2026-10-10, read-only, on the merged pool of the
`t1654-citation-chaining` worktree (597,494 works, built 2026-10-09; baseline
389,291). "Final" is `rel_final` in that branch's view. "Unique" means the lane is
the work's only source. These labels come from the old staged screening, which
this redesign replaces, and chaining's screening is incomplete (47,604 works
`pending_stage2`, 14,272 `unsure_unresolved`); read the table as indicative.

| Lane | Works | Final | Unique, chaining removed | Unique, chaining counted |
|---|---|---|---|---|
| catalogue | 43,115 | 3,912 | 1,341 | 95 |
| t1530 Southern OpenAlex | 34,134 | 2,750 | 913 | 2 |
| t1652 causal search | 34,356 | 3,340 | 682 | 1 |
| t1810 RePEc | 77,501 | 1,959 | 433 | 278 |
| t1650 journal summaries | 214,863 | 1,121 | 201 (51 before 2007) | 0 |
| t1653 Southern, non-OpenAlex | 16,925 | 307 | 103 | 71 |
| t1654 chaining | 270,483 | 12,614 | n/a | 5,687 (793 before 2007) |

**Decision (author-decided, 2026-10-10): the journal summaries lane is turned off,
because chaining subsumes it.** Its 179,106 sole-source works are 30% of the merged
pool and 0.5% of its records reach final.

Consequences, **MOE-recommended**:

- The lane is withdrawn, not deleted. Its delivery stays in DVC and its counts
  stay in the PRISMA flow as "harvested, withdrawn: subsumed by chaining" (1656
  carries the line). The single-standard rule holds: no record is screened by a
  different rule.
- The pool build excludes t1650, which shrinks the merged pool by up to 179,106
  works (derived; works also delivered by another lane stay).
- Subsumption is measured on the old screening. 201 finals (51 before 2007) were
  found only by the summaries when chaining is removed. The recall-probe use is
  lost: 82% of the 1,121 summary finals were also found by another baseline lane
  (derived), a coverage figure no other lane gives. Re-check on the new scorer's
  output that those 201 are still reached by chaining or another lane. If not,
  recover them from the archived delivery; the lane can be turned back on.
- Only 34% of the sole-source summary works carry an abstract (60,545 of
  179,106), and the old screening needed one. The 0.5% yield is a lower bound.

## 8. Sequencing constraints and the fate of 1654

1. The round-1 merge was built on dedup version 1. Finish and archive it before the
   version-2 flip (ticket 2048, stage B2b), or the flip must carry a migration for
   the chaining records. Do not run both on the same pool at once.
2. Wind-down of the screening half (done on the ledger side, 2026-10-10): every
   provider batch is terminal, and the budget ledger is frozen with 12,073 calls
   all settled, USD 20.82 in total (usage-derived upper bound, not an invoice;
   up to USD 0.56 of it is assumed spent without outcome evidence), cap USD 30.
   No new paid wave starts. Labels already imported stay in the append-only
   tables and serve as a cross-check. Ticket 2062 holds what remains.
3. 1654 keeps its scientific aim (two rounds, a third only if round two adds
   admissible works) but its mechanism changes: new works are scored by the new
   scorer, not screened by the staged runners. Its exit criteria were rewritten
   on 2026-10-10 (PR 1754).
4. Round 2 waits for the scorer and the calibrated cut.

## 9. Cost and performance assessment (derived, 2026-10-10)

Nothing below is an invoice. Inputs are measurements from the 1654 archive; the
scaling to the new scorer is an assumption and is labelled.

**Measured inputs**

| Quantity | Value | Source |
|---|---|---|
| Haiku 5.5 Stage 1 batch | 205,694 labels, 10,273 requests (20 per request), USD 4.73 | usage-derived, ledger |
| Luna three-facet waves | 3,367 chunks for 67,331 records (20 per chunk); a wave of 500 requests used 3.49M input and 3.56M output tokens (2.13M reasoning), USD 1.11 at margin 1.0 and USD 1.17-1.24 at margin 1.1 | waves 01, 04, 06 |
| Luna wave wall-clock | 58 minutes for wave 06 (created to completed) | provider batch state |
| Local Qwen | 1.68 records per second on a 40-record pilot | 1654 log (small sample) |
| Format faults in the last full Luna wave | 55 of 10,000 records pending | 1654 log |

Per work, derived: Haiku Stage 1 USD 2.3e-5; Luna three-facet USD 1.1e-4 to 1.2e-4.

**Scoring set (derived).** The merged pool has 597,494 works; without the 179,106
works found only by t1650 it has 418,388; the DataCite profile excluded 5.7% of the
baseline pool on 2026-10-09, so about 394,000, taken as 400,000.

**Cost of the two experts over 400,000 works**

| Expert | At measured per-work rate | Scaled for seven predicates and longer structured output (assumption: 2-4x Haiku, 1-2x Luna) |
|---|---|---|
| Haiku | USD 9 | USD 18-37 |
| Luna | USD 44-48 | USD 44-96 |
| Both | USD 53-57 | USD 62-133, central about USD 90 |

**Arbiter.** Divergent share d is unmeasured (guess 5-20%), so 20,000 to 80,000
works. Local: 3.3 to 13.2 hours at 1.68 records per second, 5 to 20 hours with
few-shots lengthening the prompt (assumption, 1.5x); no API cost. API third vendor,
Luna-class at the Luna rate: USD 2-10; frontier-class: USD 12-100 (assumption, 5 to
10 times the Luna rate; not measured).

**Wall-clock.** 400,000 works at 20 per request is 20,000 requests, 40 waves of 500.
At 58 minutes a wave: about 13 hours with three waves in flight (the old scheduler's
cap), about 40 hours one wave at a time. Haiku runs as batch within the provider's
24-hour contract. Scoring plus arbiter: one to two days of machine time.

**Budget and author time.** The USD 30 cap of the 1654 ledger is spent (USD 20.82,
frozen) and does not carry over: the scale run needs a new authorization, about USD
60-145 including the API-arbiter fallback. The 100-work calibration trial costs
cents at these rates. Author hours to the cut: predicates 2-3, Gavard verification
and the 50/50 and shot sets 3-6 (excluding the Gavard verification, unmeasured),
trial review 1-2, alpha-cut review 2-3: about 10-15.

**What would move these numbers.** The 19% of the pool without an abstract (76,261
works) is scored on metadata and may need its own pass; a retry wave for format
faults adds about 0.5% of cost; a longer prompt or more reasoning raises Luna's
cost linearly. The data steps (pool rebuild, dedup version 2) were not timed; one
`make rel-pool` run in a populated worktree would measure them.
