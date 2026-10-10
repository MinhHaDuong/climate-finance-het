# REL ingestion pipeline redesign: design note

Draft of 2026-10-10 for author review. Nothing here is built, filed or merged.
Each decision carries a label: **author-decided**, **MOE-recommended** (needs
the author's yes) or **default**. Counts are quoted from tickets and notes with
their date; none was re-measured for this note. Estimated prices are marked
"estimate".

The staged plan of section 12 (author-decided 2026-10-10) governs the order of
work: one cheap scorer first, and a second scorer and a referee only if that run
shows they are needed. Where earlier sections describe two experts and an arbiter
as the base design, read them as the conditional stage S5.

## 1. The pipeline

```
N upstream databases
   -> N harvesting lanes
   -> Pool of Records
   -> Deduplicate
   -> Pool of Works
   -> Filter on DataCite metadata completeness
   -> Scoring: one cheap scorer (S4); a second scorer and a referee on the band only if S5 asks for them
   -> Alpha-cut: final set of at most 10,000 works

Gavard set: hand-chosen, verified, sealed; calibrates the alpha-cut
Test set: 60 positives, 60 non-obvious negatives, hand-picked, sealed
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

Before the cut, each expert answers one short question set per work. The
predicates were set by the author on 2026-10-09 (session on OpenAI's Decisions
endpoint; the transport is not yet tested):

- five membership predicates, each asked about the work's main studied object:
  `research` (from one `choice` question: research / institutional / other),
  `economic` (the contribution bears on the economics, policy or governance of
  climate finance, the contribution test of the old discipline facet),
  `international`, `climate` and `finance`;
- `venue`, computed from metadata (tier of journal, series or publisher, with
  trusted-index evidence at the publication year), and the metadata gate
  (ticket 2043); no model call;
- certainty fields that widen an interval and never enter the minimum:
  `input_quality`, and per facet the evidence type (supports / contradicts /
  insufficient), as `choice` questions where the endpoint allows. They separate
  "unknown" from "half true", which a bare 0.5 cannot.

The work's membership is the minimum over the facets. `config/rel_stage2_prompt_v3.md`
(ticket 2010) is the earlier three-facet design (0, 0.5, 1 with evidence strings)
and the source of the contribution-test wording; it is not used unchanged.
Descriptors (contribution type, mechanism, field, geography) are not asked here:
section 10.

First run (S4, author-decided 2026-10-10): one cheap scorer, Haiku by structured
output or Luna on the Decisions endpoint, whichever the trial finds cheaper at
adequate recall. Its cut is calibrated on the sealed sets. A second scorer and a
referee on the band are adopted only if the first run shows they are needed (S5).
If adopted, the design is: Haiku (Anthropic) and Luna (OpenAI), two vendors,
hence decorrelated, and a third reader arbitrates:

- Each model's probabilities are idiosyncratic, so scores are never averaged
  across models (**author-decided**). Each model gets its own cut, calibrated on
  the sealed sets.
- A work is divergent when the two models fall on opposite sides of their own
  cuts, which is a three-way decision (accept, reject, defer to the arbiter). Only divergent works are rescored (**author-decided**); a band around
  each cut is added only if the sealed sets show it is needed.
- The arbiter is a local model constrained with llguidance, with an explicit
  prompt and positive and negative few-shots. Whether a local model reads
  non-English well enough is to be measured, not assumed (**author-decided**).
  Fallback: a third API vendor.

### 2.5 Alpha-cut

Keep at most 10,000 works. The Gavard set is verified, sealed, then used to fix
the cut. The sealed 60/60 set tests it. Whether this calibration works, and how
many works it yields, is open (section 3).

## 3. Unknowns

| Unknown | Why it matters | How it resolves | Estimate |
|---|---|---|---|
| Luna transport: Decisions endpoint or chat-completions batch | per-work cost differs about threefold (section 9); Decisions is public beta, input-token pricing, no batch tier, rate limits unknown | untested; a trial arm measures it | cents |
| Does calibrating on the sealed sets give a usable cut? | the Gavard set is positive-only; recall can be set, false positives need the negatives | trial: recall and size at the scorer's cut on the test set | trial below |
| Size of the output | the cut may give far more or fewer than 10k | count on the filtered pool after calibration; reference only: the old pipeline kept 7,499 fully graded works and labelled 11,982 `icf` before corrections | known after the trial |
| Width of the band around the cut | decides whether a second scorer or a referee is worth buying (S5) | measured in S4 on the sealed sets and the run | guess 5-20% of works inside the band |
| Local referee on non-English (only if S5 adopts one) | the hardest cases may be non-English and first act | trial arm, with and without few-shots | half a day |
| Precision of the claims | 60 per class gives a Wilson interval of about 0.89 to 0.99 at 58 of 60 (0.87 to 0.99 at 48 of 50) | stated in the report; small effects are noise | none |
| No-abstract works | 76,261 works; scoring on metadata only | separate calibration | in trial |
| Chaining volume | round 1 added about 208k works; scoring cost scales with them | scoring is cheap; the cost is gating | see 5 |

Trial design (**MOE-recommended**, trial itself accepted by the author): run
the cheap-scorer candidates (Haiku, Luna on Decisions) on the Gavard set and the
120-work test set; calibrate the cut on the Gavard set plus a draw of clear old
`out` works as negatives; report recall at the cut, the width of the band and
per-language results. The second-scorer and referee arms (divergence, local
arbiter with and without few-shots) run on the sealed sets only, to inform S5,
not at scale. Few-shots come from a separate shot set and never from a sealed
set. The sealed files are hashed before any model run, one line per work giving
the reason for the pick. Paid cost, estimate: a few USD. Author time: the shot
set and the two sealed sets.

## 4. What changes in the current plan

- **Retired** (**author-decided** 2026-10-10): the staged screening of the
  `t1654-citation-chaining` branch (design B, Stage 2, Luna facet waves,
  correction and waiver chain) and the discipline catch-up as separate stages.
  Scoring replaces them.
- **Kept**: the 1654 collector (`scripts/_rel_chaining.py`), its seed roster and
  round-1 records, delivered as a lane.
- **Waits**: round 2 of chaining chooses its frontier from the new scores, so it
  runs after the end-to-end run S4 (**MOE-recommended**).
- **Split of 1654** (**author-decided** 2026-10-10, tickets filed in PR 1754):
  1654 is a tracker. Children: 2061 finish and archive the round-1 merge on
  dedup version 1 and land the collector as a lane; 2062 wind down the screening
  half (section 8); 2060 the scoring calibration trial (child of 0700); 2063
  round 2 after scoring exists, blocked by 2060 and 2061 and, since the staged plan,
  by the end-to-end run 2071. The earlier A/B/C split
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

Superseded by the staged plan of section 12. The earlier six-step table assumed
two experts and an arbiter from the start.

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

**First run: one cheap scorer (S4).** Haiku by structured output, USD 9-37 over
400,000 works; Luna on Decisions, USD 16-40 (derived, unmeasured). Evaluating
`venue` first removes about 21% of works before any call, so about USD 7-29 for
Haiku and USD 13-32 for Luna on Decisions. A second scorer would add the other
figure. The author's ceiling for the run is still to be set (ticket 2060).

**Cost of the two experts over 400,000 works (stage S5 only)**

| Expert | At measured per-work rate | Scaled for longer structured output (assumption: 2-4x Haiku, 1-2x Luna) |
|---|---|---|
| Haiku | USD 9 | USD 18-37 |
| Luna | USD 44-48 | USD 44-96 |
| Both | USD 53-57 | USD 62-133, central about USD 90 |

**If Luna runs on the Decisions endpoint.** The endpoint page, as read on
2026-10-09 and not re-checked, bills input tokens only at USD 0.10 per 1M, with
no output or cache charge. At 400 to 1,000 input tokens per work (questions plus
title and abstract; an assumption, unmeasured) that is USD 16-40 over 400,000
works. With Haiku (USD 9-37) the two experts cost about USD 25-77, central about
USD 45. Evaluating `venue` first removes works before any call: 88,862 of
418,388 carried the old seriousness exclusion (21%, to be recomputed on the new
rule), so about USD 20-60. One trap: the alias lexicon (8,229 bytes) and the v3
prompt (7,855 bytes) are about 4 to 5 thousand tokens, so sent with every work
they would cost about USD 180 over 400,000 works; the aliases run as a free
regex in code and the model sees only the hits.

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
60-145 including the API-arbiter fallback. The 120-work calibration trial costs
cents at these rates. Author hours to the cut: Gavard verification
and the 60/60 and shot sets 4-7 (excluding the Gavard verification, unmeasured),
trial review 1-2, alpha-cut review 2-3: about 7-12.

**What would move these numbers.** The 19% of the pool without an abstract (76,261
works) is scored on metadata and may need its own pass; a retry wave for format
faults adds about 0.5% of cost; a longer prompt or more reasoning raises Luna's
cost linearly. The data steps (pool rebuild, dedup version 2) were not timed; one
`make rel-pool` run in a populated worktree would measure them.

## 10. Post-cut descriptors (author decisions of 2026-10-10; value lists are drafts)

Asked only of the final set (at most 10,000 works), after the cut, never in the
pre-cut pass. Every descriptor is multi-valued unless noted. Cost over 10,000
works about USD 5-8, derived: the alias lexicon in the prompt is about 4,500
tokens, so 45M tokens at USD 0.10 per 1M is about USD 4.5; the other descriptors
add under USD 2. Unmeasured.

| Descriptor | Referential | Values |
|---|---|---|
| `contribution_type` | REL coding grid, section 9.1 of `conception/carte-causale-icf-co2.md` | `concepts`, `data`, `evidence`, `models` (the grid's ontologie, donnees, preuves, modeles) and `review`, `policy` (from the v3 types; names set by the author) |
| `result_type` | same grid, `type_resultat` | `description`, `association`, `identified_effect`, `simulation`; only where `evidence` or `models` |
| `research_design` | same grid, `design`, and section 9.2 | `panel_FE`, `RDD`, `IV`, `SC`, `DiD`, `MSM`, `LCA`, `model`, `case_study`, `other`; only where `evidence` or `models` |
| `unfccc_mechanism` | UNFCCC referential and `config/rel_mechanism_lexicon_v3.md` | atomic list below |
| `spatial` | ISO 3166-1 and UN M49 | countries and regions; `001` for World; null for a conceptual work |
| `field` | OECD FORD, two levels, and JEL where the record carries it | main field plus subfields from the model's category probabilities |

`contribution_type` replaces the old `ctype` and is redetermined on the final
set, as the author decided. The shortlist draws on the REL grid, with JEL
method categories (C, B4, C8, Y1; from memory, unverified), the RePEc/NetEc
document types (genre only, already covered by `resourceTypeGeneral`), OpenAlex
`type` and PubMed publication types for `review`.

`unfccc_mechanism` values (draft; family comes from a lookup, not from the
model; combined lexicon entries are split):

| Family | Values |
|---|---|
| Kyoto | `cdm`, `ji`, `iet` (candidate, not in the lexicon) |
| Paris Article 6 | `art6_2`, `art6_4`, `art6_8` |
| Financial mechanism | `gcf`, `gef` |
| Funds | `adaptation_fund`, `ldcf`, `sccf`, `cif` (candidate, named in the lexicon) |
| Loss and damage | `frld` |
| Forest | `redd_plus`, `fcpf_readiness`, `fcpf_carbon`, `biocf_isfl`, `nicfi`, `un_redd`, `amazon_fund` |
| Risk | `global_shield`, `insuresilience`, `arc`, `ccrif` |
| Flows | `oda_mdb_climate`, `private_mobilisation` |
| Goal | `ncqg` |
| Country platform | `jetp` (author addition; the country comes from `spatial`) |
| Escape | `other_international`, `none` |

An alias hit is evidence, not membership, as in the lexicon. `none` never
excludes: bilateral and multilateral-bank climate finance stays in scope. A
free-form `main_object` is dropped from the model pass: objects are discovered
afterwards from the embedding clusters of ticket 0702, whose test is that every
cluster can be named.

## 11. Dublin Core application profile (draft)

| DC term | Pool field | Referential |
|---|---|---|
| `dcterms:identifier` | `doi`, `openalex_id`, handles | DOI, OpenAlex id, RePEc, OAI, HAL, hdl |
| `dcterms:title`, `dcterms:creator`, `dcterms:date` | `title`, `first_author` / `all_authors`, `year` | ISO 8601 for dates |
| `dcterms:source` / publisher | `journal`, venue identity | ISSN (ISO 3297), series, publisher |
| `dcterms:type` | `doc_type` | DataCite `resourceTypeGeneral` |
| `dcterms:language` | `language` | ISO 639-1, ISO 639-3 if none; metadata, local detector when blank (44.1% blank on 2026-10-10: 85% of t1650, 83% of RePEc; `eng` against `en`) |
| `dcterms:abstract` | `abstract` | optional in the profile, with a `no_abstract` flag (MOE-recommended) |
| `dcterms:spatial` | `spatial` | ISO 3166-1, UN M49 (the LDC, LLDC and SIDS groupings are codes 199, 432, 722, from memory) |
| `dcterms:subject` | `field`, `unfccc_mechanism` | OECD FORD, JEL, UNFCCC list |
| `dcterms:isVersionOf` | `version_hint` | DOI of the published version |

The mandatory set is the DataCite set of ticket 2043. Models' command of FORD and
M49 is assumed, not measured; the 2060 trial checks it on 20 abstracts.

## 12. Staged plan (author-decided 2026-10-10)

| Stage | Content | Tickets | Leave the stage when |
|---|---|---|---|
| S1 | Finish 1654: archive the round-one merge and land the collector; wind down the staged screening | 2061, 2062 | merged and archived on dedup version 1; archive pushed to DVC |
| S2 | The corpus ticket train: dedup version 2 and its migration, the metadata profile switched on, t1650 withdrawn in the next pool build | 2043, 2048, 2051 (deferred), a pool build | the pool of works is frozen for scoring and its counts reconciled |
| S3 | Hand-pick 60 positives and 60 non-obvious negatives; verify and seal the Gavard set; pick the shot set; hash all | 2060 | hashes recorded before any model run |
| S4 | End to end with one cheap scorer: calibrate on the sealed sets, score the pool, alpha-cut | 2060 (trial), 2071 (run) | the cut yields at most 10,000 works at a stated recall, within the author's cost ceiling |
| S5 | Decide whether a second scorer and a referee on the band are worth buying | 2072 | the author decides, from the measured band width and recall |
| After | Round 2 of chaining from the scored frontier, third-round decision, closure of 1654; then the freeze | 2063, 1656 | |

The tracker for this sequence is ticket 2070. MOE-recommended, not yet decided:
S2 and S3 run in parallel (the hand-pick waits only on the author), and round 2
stays after S4 because its frontier is chosen by score, so 1654 closes after
2063 and S1 closes the part that can be finished now. The deadline is about
2026-12-06 (ticket 0700); S3 is the author-time item on the critical path.
