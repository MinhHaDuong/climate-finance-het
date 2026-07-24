# Cut plan: data-paper.qmd word budget 4,100 → 2,500

Prepared 2026-07-24 (ticket-ref 0274). Plan only — no manuscript edits made.
Remark IDs from `ledger.dedup.jsonl` in this directory.

## 1. Measured word counts

Counting method (script in commit message context, reproducible): strip YAML
front matter and HTML comments; each `{{< meta … >}}` shortcode counts as one
word; pipe-table rows and table captions excluded; generated includes
(`tab_corpus_sources.md`, `tab_languages.md`, `tab_variables.md`) excluded;
figure captions **included**; citation keys excluded; abstract (in YAML)
counted separately. `wc = len(text.split())` on the cleaned prose.

| Section | Words |
|---|---|
| Abstract | 95 |
| Preamble (related-dataset line) | 24 |
| 1. Introduction | 611 |
| 2.1 Sources | 304 |
| 2.2 Data Structure | 303 |
| 2.3 Quality, Completeness, Biases | 835 |
| 2.4 OpenAlex limitations | 419 |
| 3. Data | 992 |
| 4. Concluding Remarks | 407 |
| Data and Code Availability | 53 |
| **Total** | **4,068** |

Figure captions alone: fig-bars 17 + fig-global-map 137 + fig-sem-composition 79 = 233 words.

**Counting ambiguity for the author.** RDJ4HSS says "max 2,500 words" without
stating whether abstract, figure captions, and tables count. If abstract (95)
and captions (233) are excluded, the effective total is 3,740 and the target
needs only ~1,240 of cuts. This plan reaches 2,500 under the *strict* reading
(everything counts). Generated pipe tables (tbl-sources, tbl-openalex-limits)
and the three generated includes are not counted here in either reading; if
the journal counts table text, flag it — tbl-openalex-limits alone is ~150
words and answers ED-01/R1-11, so it should be defended, not cut.

## 2. Ranked cut list

Tier 1 — condensations (prose stays in the paper, tighter):

| # | Section | Passage | Now | Action | Save | Risk (remark coverage) |
|---|---|---|---|---|---|---|
| 1 | §1 Intro | Six-bullet literature-confirmations list + lead-in | 311 | Condense to ~90-word summary paragraph; full six statistics already live in generated tables (`tab_lit_confirmations.csv` etc.) — move the detailed enumeration to Zenodo README / supplement, keep a pointer | 220 | ED-02, R1-18 (added value). Safe: the condensed summary + §4 directions paragraph + companion-paper reference keep coverage; the statistics survive in deposited tables |
| 2 | §2.4 | "Deduplication is the residual weak point" audit paragraph | 211 | Condense to ~110: keep the false-negative/false-positive counts and the author-matching future-release sentence; move mechanism detail to the deposited audit table's notes | 100 | R1-12 (dedup). Core counts must survive; §2.2 also reports per-pass removal counts, and tbl-openalex-limits has a dedup row |
| 3 | §2.3 | National-institutions scope paragraph | 207 | Condense to ~100: keep the boundary rationale (category constituted in UNFCCC/OECD arenas), the @campiglio_etal2025 tractability example, and the extension path | 105 | R1-06, R1-08. Protected core — condense only, never delete |
| 4 | §3 | fig-global-map caption | 137 | Condense to ~60: keep takeaway (bipolar field) + one method sentence; move layout/registry detail to supplement or figure-notes file | 75 | R1-14 (network demo). The figure itself is the answer; caption keeps the takeaway |
| 5 | §3 | citations.csv paragraph | 164 | Condense to ~100: keep GROBID reference-string parsing and the 28% no-DOI caveat | 65 | R1-13. GROBID sentences are protected |
| 6 | §4 | Companion-paper three-method-families paragraph | 129 | Condense to ~70: keep proof-of-use claim and the blind-2007-break sentence | 60 | ED-02 (partially). Keep companion-paper reference |
| 7 | §3 | embeddings.npz paragraph | 142 | Condense to ~85: keep model, dimensions, normalisation, boilerplate exclusion; drop usage suggestions (BERTopic/top2vec) | 55 | None directly; boilerplate-exclusion clause supports R1-16b |
| 8 | §2.1 | API-bounds / raw-pool paragraph | 121 | Condense to ~70: **keep the RePEc/NBER/MPRA sentence verbatim** (answers R1-16a); move pool-storage and overlap-validation detail to Zenodo README | 50 | R1-16a. That one sentence is the only coverage — protected |
| 9 | §2.3 | Reference-list completeness paragraph | 120 | Condense to ~70: keep median/zero-tail counts and the "screening variable" advice | 50 | R1-13 (reference counts). Keep the numbers; also echoed in tbl-openalex-limits |
| 10 | §2.4 | Abstract-field paragraph | 115 | Condense to ~70: keep boilerplate detector + fig-bars bias direction | 45 | R1-16b. Keep both facts |
| 11 | §3 | corpus.csv paragraph | 150 | Condense to ~105: keep @tbl-variables pointer, codebook, filter recipe, near-duplicate column | 45 | ED-03, R1-19. Table include + codebook sentence protected |
| 12 | §4 | Referee-reply paragraph | 116 | Condense to ~70: keep the candid "task-specific cleaning" concession; trim the Negishi/Barrett illustration to one clause | 45 | R1-18. Concession sentence protected |
| 13 | §2.3 | Near-duplicate (COP27 editorial) paragraph | 48 | Delete; fold the @atwoli_etal2022 example as one clause into §2.2's near-duplicate paragraph | 40 | None solely here — mechanism covered in §2.2 and tbl-openalex-limits row |
| 14 | §2.3 | Reranker calibration paragraph | 96 | Condense to ~55: keep AUC 0.818 human validation and contested-category caveat | 40 | R1-11 (query false positives) — AUC figure also cited in tbl-openalex-limits |
| 15 | §2.3 | Citation-verification paragraph ("As tbl-quality shows…") | 104 | Condense to ~70: keep 99.0% audit and the corrected non-English wording | 35 | R1-13 (audit), R1-16c (the reworded coverage sentence is here — keep it) |
| 16 | §2.3 | Biases paragraph | 105 | Condense to ~70; absorb §2.1's multilingual-by-design paragraph (52 → drop ~25 by merging) | 60 | None solely; language-share facts also in tbl-languages include |
| 17 | §3 | fig-sem-composition caption | 79 | Condense to ~45 | 35 | Boilerplate-exclusion clause supports R1-16b — keep it |
| 18 | §3 | Temporal citation-coverage paragraph | 85 | Condense to ~55: keep 27%/47% numbers and the user warning | 30 | Supports R1-13-adjacent guidance |
| 19 | §1 | Prior-mappings coverage paragraph | 113 | Condense to ~85: keep the three coverage percentages | 30 | ED-02 (added value) — percentages protected |
| 20 | §2.1 | Search-strategy paragraph | 96 | Condense to ~66 | 30 | None; taxonomy detail in deposited YAML |
| 21 | §2.2 | Protection-criteria paragraph | 75 | Trim teaching-canon construction detail to the existing tech-report pointer | 30 | None |
| 22 | §4 | Final provenance/future paragraph | 63 | Condense to ~40 | 20 | ED-01's regional-databases answer is in §2.4, not here — safe |

Tier 1 subtotal: **1,315 words saved** → 4,068 − 1,315 = **2,753**.

Tier 2 — needed only under the strict reading (abstract + captions count):

| # | Item | Action | Save |
|---|---|---|---|
| 23 | §2.3 lead-in column-definitions paragraph (74) | Move %non-EN/%DOI/%Abstract/%Refs definitions into the generated table's footnote (edit the table generator, not prose) | 50 |
| 24 | §2.4 dedup + §2.3 reference-stats residue | Second-pass move of remaining audit numbers to a one-page "quality supplement" in the Zenodo deposit, pointers in text | 120 |
| 25 | Abstract | Tighten 95 → 70 | 25 |
| 26 | §3 Zenodo-structure lead paragraph (70) | Condense to ~50 — keep the three-part inputs/products split (ED-04 protected) | 20 |
| 27 | §4 opening paragraph (41) | Merge into directions paragraph | 20 |
| 28 | §1 opening paragraph (83) | Tighten to ~65 | 18 |

Tier 2 subtotal: **253** → running total **2,500**. If the journal excludes
abstract and captions (3,740 effective), Tier 1 alone lands at ~2,420 and
Tier 2 is unnecessary.

## 3. Protected passages (must survive, at least condensed)

- §2.1 "OpenAlex indexes economics working papers from RePEc, NBER, MPRA…" — only coverage of **R1-16a**.
- §2.3 "the five smaller sources increase the corpus's non-English, institutional, and pedagogical coverage" (corrected wording) — **R1-16c**.
- §2.3 national-institutions boundary paragraph (rationale + Campiglio + extension path) — **R1-06/R1-08**.
- §2.4 entire section skeleton: tbl-openalex-limits table + regional-databases paragraph (SciELO, Garuda) — **ED-01, R1-10, R1-11, R1-16b**. The table is the point-by-point answer; do not cut the table.
- §2.2 + §2.4 dedup per-pass counts and false-negative/false-positive audit numbers — **R1-12**.
- §2.3 99.0% citation-link audit; reference-count median/zero-tail numbers; §3 GROBID sentences — **R1-13**.
- §3 fig-global-map figure + community paragraph — **R1-14** (also fig-sem-composition for the text-analysis angle).
- §3 corpus.csv description + `@tbl-variables` include + codebook sentence — **ED-03, R1-19**.
- §3 Zenodo three-part structure sentence (code / inputs / products) — **ED-04**.
- §1 condensed added-value summary + §4 directions paragraph + companion-paper references — **ED-02, R1-18**.
- §4 "task-specific cleaning" concession — **R1-18**.

## 4. Arithmetic

- Current prose total: **4,068** (strict count; 3,740 if abstract + captions excluded).
- Words to cut (strict): 4,068 − 2,500 = **1,568**.
- Tier 1 savings: **1,315**. Tier 2 savings: **253**. Sum: **1,568** → exactly 2,500.
- Under the lenient reading, Tier 1 alone suffices (≈2,420 countable words) with ~80 words of slack.

**Verdict: 2,500 is reachable without deleting any remark's only coverage.**
Every cut is a condensation or a move-to-supplement with an in-text pointer;
no remark listed in the ledger loses its answering passage. The tight spots
are #2 (R1-12 dedup audit) and #3 (R1-06 national institutions), where
condensation must be done carefully — both keep their load-bearing numbers
and rationale. Author arbitration recommended on: the counting ambiguity,
Tier 2 item 24 (supplement move), and how far to shrink the intro bullet list.
