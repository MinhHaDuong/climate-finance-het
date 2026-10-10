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

- **Retired** (**MOE-recommended**, not yet confirmed): the staged screening of the
  `t1654-citation-chaining` branch (design B, Stage 2, Luna facet waves,
  correction and waiver chain) and the discipline catch-up as separate stages.
  Scoring replaces them.
- **Kept**: the 1654 collector (`scripts/_rel_chaining.py`), its seed roster and
  round-1 records, delivered as a lane.
- **Waits**: round 2 of chaining chooses its frontier from the new scores
  (**MOE-recommended**).
- **Split of 1654** (**author-decided** in principle): a lane child for the
  collector and delivery, a round-2 decision child after scoring. The earlier
  A/B/C split is superseded.

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
| 4 | scoring on the filtered pool; the lane for chaining round 1 delivered in parallel | go for paid calls | roughly USD 15-25 for two experts over about 400k works (scaled from the 205k-work Haiku batch at USD 4.73, a derived figure) |
| 5 | arbiter on divergent works, alpha-cut, count | review the set | overnight local, or USD 20-80 with an API third vendor |
| 6 | chaining round 2 from the new frontier | decision | as step 4 |

The deadline is about 2026-12-06 (ticket 0700). Steps 0 to 3 fit in the next
week if step 1 does; the later steps scale with how many works the filter lets
through.
