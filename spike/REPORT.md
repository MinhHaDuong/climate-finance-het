**NEVER MERGE.** Throwaway prototype approved by the author on 2026-09-30 as part of the specification review (ticket 1710, "eating the pudding"). What it produces is evidence about the draft specification, not code to keep. It writes nothing to the ledger: every file is under `spike/`, and `data/jetp/` was only read. Close this PR without merging once the review has used it.

Note: the harness refused to let the prototype agent write `spike/REPORT.md` (subagents may not write report files). The report is in full below.

---

# Spike: the draft extraction specification run on three held documents

Specification versions tested:
- On main (`4e75951e`): `docs/jetp-fusion.md`, `jetp-ontology.md`, `jetp-ledger-storage.md`, `jetp-language.md`.
- Drafts: `jetp-extraction.md` at `a2b87b32`, `jetp-collection.md` at `ee4d1987`, `jetp-requirements.md` at `f96cc098`.

In the section references below, "ext" is extraction, "fus" fusion, "sto" storage, "col" collection and "req" requirements. The prototype ran on padme, 2026-09-30, 13:20 to 13:50 UTC.

## 1. What ran

| Step | Newsletter issue 8 (Oct 2025) | Newsletter issue 13 (Mar 2026) | Decision 1009/QĐ-TTg (one-off) |
|---|---|---|---|
| Pending list (document → retrieval sha256 → lines) | pending, 0 lines | pending, 0 lines | pending, 0 lines |
| Bytes (DVC store), re-hashed | `c5cd6cb1…`, 3 pp | `fa7d149b…`, 3 pp | `ada382c3…`, 15 pp |
| Text layer (ext §5) | poppler 24.02.0 | poppler 24.02.0 | poppler 24.02.0 |
| Series parser (ext §6.1) | masthead + 4 headlines | masthead + 3 headlines | refused (landmarks absent) |
| Scope and field list, then reader LLM (ext §4, §6.3) | 18 proposed | 13 proposed | 59 (v2) / 46 (v3) |
| Automatic locator check | 17 kept / 1 rejected | 12 / 1 | 57/2 (v2), 13/33 (v3) |
| Checker LLM from another vendor, every row | 16 agree / 1 disagree / 8 missed | 7 / 5 / 6 | 51/6/5 (v2), 8/5/28 (v3) |
| Author's review set | 12 items, ~15 min | 14 items, ~18 min | 21 items, ~21.5 min (v2); 36, ~51 min (v3) |
| Restatement check, issue 8 ↔ 13 (ext §8) | 7 pairs: 0 restatements, 7 changes, 2 false pairings | | n/a |
| Candidate match (fus §3) | "Bắc Ái" ↔ `project-vnm-project-bac-ai-pumped-hydro`: same, very likely, high | | not run |
| Figure traced to bytes | | count 44, every link re-verified | |
| Replay limit and positive control (ext §10) | pass | pass | pass |

- **The brief's series pair was not available.** Neither newsletter issue is extracted: all 13 MOIT issues are among the 115 pending. I chose issues 8 and 13 because both print the list of 44 JETP projects.
- **Decision 458/2026 is a scan** (23 pp, 149 characters of text). It would get `deferred` (ext §6.4, §7), so decision 1009 was the one-off instead.
- **Controls ran before any held document** (ext §12):
  - Planted-item control: issue 12 with a planted "Hòn Mây 2" loan of USD 212 million, and Trị An as the named absent item. It passed.
  - A fabricated locator was rejected automatically.
  - Under the v1 locator check, the planted item was found but then rejected, because its anchor ran over 80 characters.
- **Models:**
  - Reader: `google/gemini-3.8-flash`. Checker: `openai/gpt-5.4-mini`.
  - Restatement proposer and match judges: `mistralai/mistral-medium-3.1` and `deepseek/deepseek-v3.2`. `mistral-large-2512` returned HTTP 429.
  - All calls at temperature 0, through OpenRouter.

## 2. Examples

**Decision 1009, run v2 (57 kept).** Classifications: 10 `heading`, 26 `unnamed_item`, 18 `named_item`, 2 `quota`, 1 `envelope`, and no `unclassified`.
- #3 `heading` "I. QUAN ĐIỂM". Checker: right, virtually certain.
- #45 `named_item` "a) Bộ Tài nguyên và Môi trường": a ministry's task list, read as a named item.
- #16 `quota` "…tỉ lệ năng lượng tái tạo đạt 47% … không quá 30.127 MW". Checker: **wrong**, very unlikely (a policy target is not a quota, and the list has no value for one).
- `own_status` "Phê duyệt" was put on axis `project_stage`: the reader gave an axis to the verb of a decision.
- **Field lists came from the reader, not the publisher.** v2 declared `section_number, section_heading, topic, responsible_entity, action_or_target, timeframe`. v3 declared `section, subsection, …`, and that change alone dropped the kept statements from 57/59 to 13/46. The 33 rejected proposals came back as 22 of the checker's 28 "missed" items.

**Newsletter issue 13.**
- #9 `count` "danh mục 44 dự án phù hợp JETP", `financial_amount` "trên 11 tỷ USD". Checker: partly right, likely, medium.
- #5 `count` "3 dự án nhận được tài trợ với tổng vốn trên 700 triệu USD". Checker: right.
- #12 `envelope` "cam kết tài chính công khoảng 7,75 tỷ USD", speaker "Đại diện IPG và GFANZ".
- #10 `named_item` "danh mục IPG23". Checker: wrong.

**Newsletter issue 8.**
- **The count of 44 was rejected by the locator check.** The text layer puts the footer box in the middle of "danh mục các dự án phù hợp JETP tới nay | gồm 44 dự án". The checker listed it as missed, and the operator entered it as a person's reading (ext §6.4), appended as `…-text-a1`.
- **The prose carries a printed total** (557 + 78 + 93 = 728 million USD), but ext §6.3 gives assisted reading no step to use it.

**Restatement between issues 8 and 13 (run v3s, with one shared field list).** Tier 2 proposed 14 candidates and tier 4 kept 7 pairs:
- **44-project list:** "hơn 10 tỷ USD" became "trên 11 tỷ USD". Recorded as a change, and the restated count 44 cannot be said.
- **Three funded projects:** "728 triệu USD" became "trên 700 triệu USD". A rounded restatement, recorded as a change.
- **False pairings at "likely" or above:** the EU EUR 430 million package ↔ IPG's USD 7.75 billion commitment, twice; and "7 dự án … từ năm 2024" ↔ the 44-project list.
- **Before the shared field list (run v3)**, every pair differed on field names alone (`funding_amount` against `financial_amount`).

**Candidate match.**
- Tier 2 overlaps only on {bac, ai} out of 10 tokens: the identity's name is in English, the statement's in Vietnamese.
- Mistral: same, very likely, high. DeepSeek: same, virtually certain, high.
- `combine-2readers-v1` gives same, very likely, high.
- Neither judge noticed that "Bắc" is a misprint of "Bác".

**Figure (`spike/out/figure_trace.json`).** The value is 44, unit "dự án", a count the publisher stated. The chain runs from issue 13 statement #9 → locator p3 "Đến nay, các bên đã xác định danh mục 44 dự án phù hợp JETP" (text layer regenerated, anchor resolves once) → snapshot `fa7d149b…` (bytes re-hashed) → retrieval `…:1` of 2026-09-12 → document → publisher MOIT. Every link was verified.
- **Gap:** the timing "Ngày 27/3" has no year. The year is on the masthead, which the reader's scope excluded as page furniture, so ext §11 has no statement to name.

## 3. Rule by rule

| Rule | Verdict | Evidence |
|---|---|---|
| ext §1 Read, do not interpret | **wrong for prose** | 4/4 field lists reader-supplied. Summaries and comma-joined parties failed 9/14 proposals in issue 8 (v2). An axis was put on a verb. |
| ext §1 Traceable to bytes | followed | Figure chain re-verified. |
| ext §1 Complete within declared scope | ambiguous | "Every item" is undefined for prose. 6–8 missed per 3-page issue, some of them scope creep. |
| ext §1 Declared method; reading mints nothing | followed | Model, prompt version, temperature and adapter recorded. No identity minted. |
| ext §1, §6.1 Parser per series | **ambiguous** | A prose series repeats a frame, not a structure. The parser reads 13/13 issues' masthead and headlines only; no controls apply. |
| ext §2 Pending list | followed | 115 of 392 reproduced. |
| col §10 series as `edition_of`; ext §2, §8 | **wrong** | An issue is not an edition. Restatement is defined only between snapshots of one document. |
| ext §3 / sto Locator: page, folio, anchor ≤80 | ambiguous | Folio not detectable by any stated rule. LLMs miscount 80 characters. Labels can be non-contiguous in the text layer. |
| ext §3 Ordinal; sto `line_id` `<doc>-<table>-<n>` | ambiguous | Prose has no sequence and no table. |
| ext §3 Label as printed | ambiguous | Varied from a noun phrase to a clause. |
| ext §3 Classification list; "wait for review" | **wrong for prose** | `unclassified` was never used in 88 statements. Targets → `quota`; ministries and meetings → `named_item`. |
| ext §3 Own status word and axis | ambiguous | In prose every verb is a status word. |
| ext §3, sto `line-field-specs` Field list per document | **wrong for prose and series** | Unstable across runs (57/59 → 13/46 kept) and across issues (every pair a "change"). |
| ext §4 Declared scope | followed, unstable | The spec does not say who declares it. It dropped the dated masthead. |
| ext §4 Printed totals as controls | not applied | A total exists in prose, but no step for assisted reading uses it. |
| ext §5 Format from bytes; adapter in provenance | followed | pdfplumber interleaved three columns; poppler did not. The adapter decides whether statements exist. |
| ext §6.3 Locator check "the text there" | **ambiguous** | The window definition moves results (planted-control rejections 6 → 5 → 3). |
| ext §6.3 Checker, calibrated terms, missed items | followed | The checker sees only survivors. Rejections come back as "missed" (22/28), and some missed items duplicate kept rows. |
| ext §6.3 Author set: disagreements, missed, sample | followed | "Disagree" is undefined. Spike rule: stance ≠ right or likelihood < likely; sample 20 %, floor 3. |
| ext §6.3 Budget for the author's attention | estimated | This budget, not the model spend, is what limits the run (§4). |
| ext §6.3, §12 Planted item, fabricated locator | followed | Passed at v2 and v3. Failed under v1, as the rule says it should. |
| ext §8 Restatement by field equality | **wrong for prose** | 0 of 7 pairs; rounded repeats read as "change". |
| ext §8 Pairing without a key at M4 | conflict | Needed at M2 for series. 2 of 7 pairs false at "likely" or above. |
| ext §10 Replay limit, positive control, idempotence | followed | 39 LLM statements re-resolve; one altered row fails; the locator step is byte-identical when rerun. |
| fus §1 Calibrated language; §3 judgement and versioned rule; cutoff per result | followed | The judges got **no** positive controls. Tier 2 fails across languages. |
| fus §7 Count names its unit | followed | 44 "dự án", a publisher-stated count. |
| req Q15 Measured spend and minutes; C4 budget | followed | The per-call log matched OpenRouter's key counter to the cent (USD 0.4796). A guard stopped any call before it could exceed USD 5. |

## 4. Cost and time

Measured over 33 calls, including 3 provider failures (`finish_reason: error`, 0 tokens, cost 0, retried) and the v1–v3 iterations:

| Stage | USD | LLM s |
|---|---|---|
| Planted control (3 prompt versions) | 0.150 | 318 |
| Decision 1009 (v2 + v3) | 0.167 | 185 |
| Issue 8 (v2, v3, v3s) | 0.099 | 119 |
| Issue 13 | 0.056 | 70 |
| Restatement pairing | 0.007 | 12 |
| Match (2 judges) | 0.001 | 13 |
| Smoke test | 0.001 | 2 |
| **Total** | **0.480** | **719** |

- **Deterministic stages were fast:** text layer under 0.2 s per document, locator check under 0.01 s, parser under 1 s. The whole spike took about 30 minutes elapsed.
- **One clean pass per document** (scope, read, check):
  - Decision 1009: USD 0.08.
  - A newsletter issue: USD 0.03–0.04.
  - That is USD 2.7–5.0 per million characters.
- **Author minutes** are estimated from the item counts of the ext §6.3 rule: 1.5 min per disagreement or missed item, 0.5 min per sampled row. That comes to 0.67–2.4 min per 1,000 characters. Reviewing the scope and field list is not counted.

**Projection to the 115 pending documents** (`spike/out/size115.csv`):
- **Routes:**
  - Assisted reading: 44 PDFs (4.77 M characters) and 65 HTML pages (≤0.45 M characters).
  - Parser: 2 xlsx grants registers.
  - Bulk reading or `no_extractable_content`: 2 JavaScript portal bundles (5.0 M characters) and 2 JSON files.
  - Deferred: 1 scan.
- **Model spend:** about **USD 14–26** before chunking, well within budget. Twelve documents exceed 100,000 characters, and the ZAF plan runs to 304 pages. At about 285 output tokens per statement, a 32k output cap allows roughly 110 statements per call, so these documents have to be split.
- **LLM time:** about 3.6 hours sequential; it parallelises.
- **Proposals:** **7,000–12,000**.
- **Author review:** **58–210 hours** before any scope cut. The missed-item list is the largest share, and part of it could be removed mechanically. The author, not the model spend, is the binding constraint of ext §6.3.

## 5. The three most important changes

1. **Prose needs its own statement shape, and field lists should be fixed per document class or series, not per reading.** Evidence:
   - 4 of 4 field lists were reader-supplied.
   - A change in the field list alone moved decision 1009 from 57/59 to 13/46 statements kept.
   - Two issues of one series got different field names, so every cross-issue comparison came out as a change.
   - The closed classification list never yielded `unclassified`, and forced targets into `quota` and ministries into `named_item`.

   Proposal: a statement in prose is an anchored span whose label is the verbatim span, with typed value spans inside it (amount, count, date, party). The field schema is set once per class or series. Classification values are added for events, decisions and targets.

2. **The locator check needs a definition, and its order relative to the checker should change.** Evidence:
   - Results depend on the window, anchor length and adapter, none of which the spec fixes. Under v1 the planted item was found and then rejected.
   - A label can be non-contiguous in the text layer: the footer box split the count of 44 in issue 8.
   - Because the checker sees only survivors, 22 of 28 "missed" items in 1009 v3 were the pipeline's own rejections, shown to the author without the reader's proposal.

   Proposal: span locators (start and end anchor, whitespace-normalised, able to skip page furniture), and a deterministic signed trim for over-long anchors. Rejected proposals go back to the reader once for repair, then to the checker marked as failed. Missed items are de-duplicated against the proposals.

3. **A serial's issues are neither editions nor snapshots, and restatement should be judged per typed value, not by field equality.** Evidence:
   - Issues 8 and 13 share the list of 44 projects, yet 0 of 7 pairs came out as restatements: both a rounded repeat and a count repeated beside a changed amount read as "change".
   - 2 of 7 LLM pairings were false at "likely" or above.
   - col §10's `edition_of` contradicts ext §2 and §8.

   Proposal: an `issue_of` relation; restatement per value, with the bounds given by printed qualifiers ("trên", "khoảng", "hơn"); key-less pairing for serials moved to M2, with the author seeing every pair; ext §6.1 recast as "parser for the frame, assisted reading for the prose".

## 6. Not done

- No replay oracle: neither issue has earlier extraction to compare against.
- No HTML or spreadsheet was read.
- The match judges got no positive controls.
- No admission step or writer was built, so there are no `recorded_at` values and no dispositions.
- The author's review was simulated; one person reading was entered by the operator.
- The local model was not used.

Files: scripts are in `spike/*.py`; outputs are in `spike/out/`, one directory per document with the v2 and v3 runs kept, plus `restatement.json`, `match.json`, `figure_trace.json`, `replay.json`, `spend.jsonl`, `timings.jsonl`, `key_usage.jsonl`, `size115.csv`, `raw/` and `textlayer/`.

Ticket-ref: tickets/1710-spec-review-wave-1-seven-lenses-paper-walkthroug.erg

🤖 Generated with [Claude Code](https://claude.com/claude-code)

