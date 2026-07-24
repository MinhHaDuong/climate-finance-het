# Cut plan v2: data-paper.qmd word budget 4,100 → 2,500

Prepared 2026-07-24, revised same day per author feedback (ticket-ref 0274).
Plan only — no manuscript edits made. Remark IDs from `ledger.dedup.jsonl` in
this directory.

Changes from v1: a whole-removal pass now comes first (v1 was
condensation-only); Tier 2 is dropped from the actionable plan; every
"move to supplement" is rewritten as a file or README section in the Zenodo
data package (kit structure per `ed04-zenodo-restructure-upload.md`, ticket
0280) with a one-line pointer in the paper — RDJ4HSS gets no formal
electronic supplement.

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
needs only ~1,240 of cuts. This plan works under the *strict* reading
(everything counts). Generated pipe tables (tbl-sources, tbl-openalex-limits)
and the three generated includes are not counted here in either reading; if
the journal counts table text, flag it — tbl-openalex-limits alone is ~150
words and answers ED-01/R1-11, so it should be defended, not cut.

## 2. Remove whole — taken first

Candid criterion: which passages are weak, distracting, redundant with the
deposited artifacts, or serve no referee remark — and can be deleted outright,
at most leaving a one-line pointer? Each entry states the ledger check: no
remark loses its only coverage.

| # | Section | Passage (first words) | Now | Action | Save | Weakness (candid) | Ledger check |
|---|---|---|---|---|---|---|---|
| W1 | §1 | Six-bullet literature-confirmations list + lead-in ("Beyond coverage, the corpus can re-test…") | 311 | Remove whole; replace with a ~35-word paragraph: the corpus reproduces six published results of the prior literature, statistics in `tab_lit_confirmations.csv` / `tab_semantic_robustness.csv`, shipped under `data/products/` in the Zenodo package (add them to the ed04 kit) | 276 | This is the weakest block in the paper: six analysis findings with test statistics in a *data paper's introduction*. It reads as results smuggled from the companion paper, distracts from the data-description mandate, and duplicates deposited artifacts verbatim. A referee skimming for "what is the dataset?" hits a wall of chi-squares first. | ED-02/R1-18 (added value) keep triple coverage: the prior-mappings coverage percentages (§1), the pointer sentence itself, §4 proof-of-use + directions paragraphs. |
| W2 | §4 | Three-method-families paragraph ("Can such a corpus serve the history of economic thought?…") | 129 | Remove the method-family enumeration whole; keep one ~29-word sentence: companion paper as proof of use, corroborative epistemic role, and the calendar-blind 2007 structural break | 100 | The semantic/lexical/descriptive taxonomy is the companion paper's methodology, restated here for no data-paper purpose. It tells readers how *another* paper analyses the data instead of what the data are. Padding by borrowed depth. | ED-02 coverage survives in the retained sentence (companion-paper reference + blind-break claim). No other remark maps here. |
| W3 | §3 | Temporal citation-coverage paragraph ("Citation coverage --- the share of corpus works…") | 85 | Remove whole; the 27%/47% figures and the early-period-undercount warning become a "Citation coverage over time" note in `codebook.md` (data/products/, ed04 kit); no in-text pointer needed — the citations.csv paragraph already states the 28% no-DOI undercount and its mechanism | 85 | Redundant in mechanism with the citations.csv paragraph three paragraphs earlier (same DOI/indexing explanation, restated). Usage guidance of this granularity belongs with the data dictionary, not the paper. | R1-13 keeps its coverage via the 99.0% audit, reference-count statistics, and GROBID sentences — this paragraph was adjacent support only, never a remark's answer. |
| W4 | §2.1 | Multilingual-by-design paragraph ("The corpus is multilingual by design…") | 52 | Remove whole | 52 | Pure repetition: the English share, the eight-language targeting, and the cross-linguistic-foundation claim all reappear in §2.3's biases paragraph and in tbl-languages. Self-congratulatory framing ("deliberate", "foundation") with zero new facts. | No remark maps solely here; language-share facts survive in §2.3 + tbl-languages include (R1-16c's answering sentence is in §2.3, untouched). |
| W5 | §2.3 | Near-duplicate COP27 paragraph ("Near-duplicate detection identified…") | 48 | Remove whole; fold `@atwoli_etal2022` as one example clause into §2.2's near-duplicate paragraph | 40 | Third telling of the same mechanism: §2.2 describes detection, tbl-openalex-limits has a duplicate-records row, and this paragraph re-explains both to deliver one anecdote. | No remark solely here; dedup coverage (ED-01, R1-11, R1-12) rests on §2.2, §2.4, and the table row. |
| W6 | §2.2 | Teaching-canon construction sentence ("The teaching canon was built by scraping…") | 45 | Remove whole; the existing companion-technical-report pointer in the same sentence's tail stays as the one-line pointer | 40 | Method detail for a *source*, parked mid-paragraph inside the protection-criteria discussion — a digression at the wrong altitude. The technical report already documents it. | No remark maps here. |
| W7 | §3 | Open-Access/fulltext-URL sentences at the end of the source-catalogs paragraph ("The corpus does not include a dedicated Open Access…") | 45 | Remove whole; becomes a "Recovering OA links" note in the Zenodo package README (ed04 kit) | 40 | Defensive how-to trivia (reconstruct URLs from identifiers) that answers no reviewer and interests only a user already inside the package — which is exactly where the README lives. | No remark maps here. |

**Whole-removal subtotal: 633 words.**

## 3. Condensations — cover the remainder only

Tier 1 condensations, v1 list minus the items W1–W7 replace (v1 #1, #6, #13,
#18, #21) and with v1 #16 reduced (its merge-with-§2.1 component is now W4).
All "supplement" destinations rewritten as Zenodo-package files.

| # | Section | Passage | Now | Action | Save | Risk (remark coverage) |
|---|---|---|---|---|---|---|
| 1 | §2.4 | "Deduplication is the residual weak point" audit paragraph | 211 | Condense to ~110: keep the false-negative/false-positive counts and the author-matching future-release sentence; mechanism detail goes into notes accompanying the deposited `tab_dedup_error_estimates.csv` (data/products/, ed04 kit) | 100 | R1-12 (dedup). Core counts must survive; §2.2 also reports per-pass removal counts, and tbl-openalex-limits has a dedup row |
| 2 | §2.3 | National-institutions scope paragraph | 207 | Condense to ~100: keep the boundary rationale (category constituted in UNFCCC/OECD arenas), the @campiglio_etal2025 tractability example, and the extension path | 105 | R1-06, R1-08. Protected core — condense only, never delete |
| 3 | §3 | fig-global-map caption | 137 | Condense to ~60: keep takeaway (bipolar field) + one method sentence; reading-guide/layout/registry detail moves to a `figure-notes.md` in the Zenodo package (data/products/, ed04 kit) | 75 | R1-14 (network demo). The figure itself is the answer; caption keeps the takeaway |
| 4 | §3 | citations.csv paragraph | 164 | Condense to ~100: keep GROBID reference-string parsing and the 28% no-DOI caveat | 65 | R1-13. GROBID sentences are protected |
| 5 | §3 | embeddings.npz paragraph | 142 | Condense to ~85: keep model, dimensions, normalisation, boilerplate exclusion; drop usage suggestions (BERTopic/top2vec) | 55 | None directly; boilerplate-exclusion clause supports R1-16b |
| 6 | §2.1 | API-bounds / raw-pool paragraph | 121 | Condense to ~70: **keep the RePEc/NBER/MPRA sentence verbatim** (answers R1-16a); pool-storage and overlap-validation detail moves to the Zenodo package README (ed04 kit) | 50 | R1-16a. That one sentence is the only coverage — protected |
| 7 | §2.3 | Reference-list completeness paragraph | 120 | Condense to ~70: keep median/zero-tail counts and the "screening variable" advice | 50 | R1-13 (reference counts). Keep the numbers; also echoed in tbl-openalex-limits |
| 8 | §2.4 | Abstract-field paragraph | 115 | Condense to ~70: keep boilerplate detector + fig-bars bias direction | 45 | R1-16b. Keep both facts |
| 9 | §3 | corpus.csv paragraph | 150 | Condense to ~105: keep @tbl-variables pointer, codebook, filter recipe, near-duplicate column | 45 | ED-03, R1-19. Table include + codebook sentence protected |
| 10 | §4 | Referee-reply paragraph | 116 | Condense to ~70: keep the candid "task-specific cleaning" concession; trim the Negishi/Barrett illustration to one clause | 45 | R1-18. Concession sentence protected |
| 11 | §2.3 | Reranker calibration paragraph | 96 | Condense to ~55: keep AUC 0.818 human validation and contested-category caveat | 40 | R1-11 (query false positives) — AUC figure also cited in tbl-openalex-limits |
| 12 | §2.3 | Citation-verification paragraph ("As tbl-quality shows…") | 104 | Condense to ~70: keep 99.0% audit and the corrected non-English wording | 35 | R1-13 (audit), R1-16c (the reworded coverage sentence is here — keep it) |
| 13 | §2.3 | Biases paragraph | 105 | Condense to ~70 (the v1 merge with §2.1's multilingual paragraph is superseded by W4) | 35 | None solely; language-share facts also in tbl-languages include |
| 14 | §3 | fig-sem-composition caption | 79 | Condense to ~45 | 35 | Boilerplate-exclusion clause supports R1-16b — keep it |
| 15 | §1 | Prior-mappings coverage paragraph | 113 | Condense to ~85: keep the three coverage percentages | 30 | ED-02 (added value) — percentages protected |
| 16 | §2.1 | Search-strategy paragraph | 96 | Condense to ~66 | 30 | None; taxonomy detail in deposited YAML |
| 17 | §4 | Final provenance/future paragraph | 63 | Condense to ~40 | 20 | ED-01's regional-databases answer is in §2.4, not here — safe |

**Condensation subtotal: 860 words.**

*Tier-2 reserve:* a further ~253 words of second-order cuts (v1 items 23–28:
column-definition footnote move, abstract tightening, opening-paragraph
merges) remain identified and available if Tier 1 under-delivers; they are
not part of the actionable plan.

## 4. Protected passages (must survive, at least condensed)

- §2.1 "OpenAlex indexes economics working papers from RePEc, NBER, MPRA…" — only coverage of **R1-16a**.
- §2.3 "the five smaller sources increase the corpus's non-English, institutional, and pedagogical coverage" (corrected wording) — **R1-16c**.
- §2.3 national-institutions boundary paragraph (rationale + Campiglio + extension path) — **R1-06/R1-08**.
- §2.4 entire section skeleton: tbl-openalex-limits table + regional-databases paragraph (SciELO, Garuda) — **ED-01, R1-10, R1-11, R1-16b**. The table is the point-by-point answer; do not cut the table.
- §2.2 + §2.4 dedup per-pass counts and false-negative/false-positive audit numbers — **R1-12**.
- §2.3 99.0% citation-link audit; reference-count median/zero-tail numbers; §3 GROBID sentences — **R1-13**.
- §3 fig-global-map figure + community paragraph — **R1-14** (also fig-sem-composition for the text-analysis angle).
- §3 corpus.csv description + `@tbl-variables` include + codebook sentence — **ED-03, R1-19**.
- §3 Zenodo three-part structure sentence (code / inputs / products) — **ED-04**.
- §1 W1 pointer sentence + prior-mappings percentages + §4 proof-of-use and directions paragraphs — **ED-02, R1-18**.
- §4 "task-specific cleaning" concession — **R1-18**.

## 5. Arithmetic

- Current prose total: **4,068** (strict count; 3,740 if abstract + captions excluded).
- Words to cut (strict): 4,068 − 2,500 = **1,568**.
- Whole removals (taken first): **633**. Condensations (remainder): **860**. Sum: **1,493** → lands at **2,575** under the strict reading.
- Residual 75 words under the strict reading come from the Tier-2 reserve (253 available — first candidates: column-definition footnote move ~50, abstract tightening ~25).
- Under the lenient reading (abstract + captions excluded, 3,740 countable), this plan lands at ≈2,247 with ~250 words of slack — some condensations could then be relaxed.

**Verdict: 2,500 is reachable without deleting any remark's only coverage.**
Whole removals do the structural work (633 words, and the paper reads more
like a data paper for it); condensations cover the rest. Every displaced
detail becomes a file or README section in the Zenodo data package (ed04 kit
structure) with at most a one-line pointer in the paper — no journal
electronic supplement. The tight spots are condensation #1 (R1-12 dedup
audit) and #2 (R1-06 national institutions), where load-bearing numbers and
rationale must survive. Author arbitration recommended on: the counting
ambiguity, and whether to draw the final ~75 words from the reserve or relax
toward the lenient reading.
