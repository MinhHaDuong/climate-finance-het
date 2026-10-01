# M2.3 reading design: survey of libraries and candidate designs

1 October 2026. Ticket 1890 (M2.3-0, tracker 1500). Phase: Imagine. **No design
is chosen here.** This report is the survey input to the pre-registered pilot
of ticket 1890. Readers on padme and OpenRouter will be selected by ticket 1873
once the pilot has picked a design.

Tags: **[O]** observed on a page or file read on 2026-10-01, with its URL or
path; **[D]** derived by arithmetic on observed figures; **[J]** judgement.
Release dates and licences come from the PyPI JSON API, the GitHub API and the
Hugging Face API, queried on 2026-10-01. Two research agents gathered the web
evidence: one on libraries, one on models and hosted prices. The coordinator
merged their results and checked the repository facts.

## 0. Summary

- **The design levers are where the gains are, and three of them compose.**
  First, extraction by *pointing*: readers return addresses of numbered text
  units, not retyped quotes. Second, *ontology-constrained decoding*: closed
  lists from `terms.csv` become JSON Schema enums with an explicit `other`
  escape. Third, *templates first* for the repeated layouts among the 115
  documents. Each one removes a failure mode the spike measured. Choosing
  models matters less [J].
- **The spec's default pair is feasible but untested on our languages.** No
  open-weight model that fits one card has published Indonesian or
  Vietnamese extraction or table-reading scores [O, § 3.6]. A hosted pair
  under zero retention costs about USD 1–3 per full pass for both readers
  [D]. The arbiter dominates cost in every design.
- **The reference set is thin, and where it comes from cannot be verified.**
  There are 130 decision-scoped lines (Indonesia 84, Senegal 46). 363 lines
  are candidates when the legacy migrated lines are included. Neither set has
  any Vietnamese, Indonesian-language or transcription lines. South Africa
  and Viet Nam hold 74 of the 115 pending documents but only 53 candidate
  lines. No family records that a person made the line blind to machine
  reading (§ 6).
- **No commercial service is admissible. Each one leads to the same open
  pipeline:** a layout-aware text layer with positions, then schema-guided
  extraction, then per-field verbatim citations, then a confidence score. All
  four parts exist as open software or are already specified in our code
  (§ 2.4).

## 1. Frame: what binds a design

From the accepted spec v1 (tag `jetp-spec-v1`):

- **Untrusted input and local reading.** Readers get no tools. Documents
  marked `local_only` are read on padme only (extraction § 6.3).
- **What a reader returns** (extraction § 3 and § 6.3). It proposes, blind
  to the other reader:
  - a label as printed;
  - a verbatim quote;
  - a classification from the closed list of 13;
  - the verbatim fields of the field list that the method version fixes per
    document type (`data/jetp/line-field-specs.csv`);
  - a self-score.

  A reader never proposes a field and is never asked for the status axis.
- **Locator check.** Code derives the locator from the quote. It must
  resolve and contain the label and values. One repair call is allowed, then
  the proposal is marked failed.
- **Agreement and arbiter.** An item both readers agree on stands. Every
  other item goes to the hosted arbiter. Every item ends with a stance or as
  undetermined. Nothing is queued for the author.
- **Calibration** is done on held-out reference answers, stratified by
  language × statement shape. A stratum with fewer than 30 items is
  uninformative and runs under the fallback: every item goes to the arbiter,
  and the stratum is named uncalibrated.
- **Pinning.** A method version pins model, weights, quantisation, template,
  sampling and serving software (operation § 5). The structured-output
  backend joins that list (§ 2.2).
- **Budgets** (operation § 7.2, proposed defaults): USD 3 per document,
  USD 60 for the full M2 pass, USD 20 per selection run, 10 hours of GPU
  wall time per run.

What the spike measured (`docs/jetp-spec-review/wave-1/ledger.md`) [O]:

- 22 of 28 "missed" items in one run were the pipeline's own locator
  rejections (W1, line 101).
- A field-name change moved one document from 57/59 kept to 13/46 (W1,
  line 185).
- The spike projected 7,000–12,000 proposals for the 115 documents (W1,
  line 127).
- Two of seven pairings were false at "likely" or above before calibration
  (W1, line 345).

These are the losses a design should remove.

### 1.1 Ontology binding today (coordinator's check, confirmed)

- **Binding is post hoc.** `violation_closed_list` in `config/jetp-ledger.sql`
  compares closed-list columns with `terms_in_force`. That view keeps rows
  with `status = 'accepted'` that nothing supersedes (around line 471) [O].
  Parsers hardcode their values.
- **Only the line classification has a growth path.** "Cannot classify"
  records the statement without admitting it. The panel groups such
  statements and proposes classes, the author adopts them in a new method
  version, and earlier items are read again (extraction § 3) [O].
- **The other lists have no channel from a run to a decision.** Measures,
  roles, flow types, timing roles and units are "extended by decision" with
  nothing feeding them. Most of them are M3b slots, not M2 reader output
  [O, ontology § 4].
- **Fields are fixed per type.** Information outside the field list is lost
  silently.
- **The `terms` table already supports proposals.** Its `status` list is
  `accepted | candidate | rejected`, and one `candidate` row exists [O,
  `terms.csv`]. A proposal written as a `candidate` row therefore classifies
  nothing by construction: no schema change is needed. The coordinator's
  "proposed" status is spelled `candidate` here.

## 2. Survey of libraries

Each table cell says what the project offers and how it fits our
constraints. "Open-world fallback" is the author's added criterion: how the
tool behaves when a value is not in the closed list.

### 2.1 Grounded and ontology-driven extraction

**LangExtract** (Google) — fit: **reference implementation only**
- Licence and release: Apache-2.0; 1.7.0, 2026-09-13 [O]
- Ontology/schema binding: few-shot classes plus string attributes. An
  `output_schema` with enums is enforced on Gemini/OpenAI only [O].
- Verbatim offsets: `char_interval` plus an alignment status. Fuzzy matching
  is **on by default at 0.75** [O,
  [resolver.py](https://raw.githubusercontent.com/google/langextract/main/langextract/resolver.py)].
- Scans: no.
- Weight: the core pulls `google-genai` and `google-cloud-storage` [O].
- Open-world fallback: classes are free strings unless an enum is passed.
  It reports no out-of-vocabulary (OOV) rate.

**NuExtract3** (NuMind) — fit: **strongest local reader**
- Licence and release: Apache-2.0, built on Qwen3.5-4B; released 2026-05-12
  [O, [HF](https://huggingface.co/numind/NuExtract3)].
- Ontology/schema binding: a JSON template with typed leaves:
  `verbatim-string`, enum `[...]`, multi-label `[[...]]`, number, date [O].
- Verbatim offsets: verbatim copying, but no offsets and no self-score [O].
- Scans: yes, it is a vision-language model (VLM) [O].
- Weight: 4B parameters; served by vLLM with a 131k context [O].
- Open-world fallback: absent values return `null`. It has no `other`; one
  can be added to the enum [J].

**NuExtract 2.0** (2B/4B/8B) — fit: as NuExtract3, older
- Licence and release: MIT tags, built on Qwen2/2.5-VL. The 4B's base
  carries the Qwen Research licence [O].
- Ontology/schema binding: as NuExtract3.
- Verbatim offsets: none.
- Scans: yes.
- Weight: the 8B needs quantising for 16 GB [J].
- Open-world fallback: as NuExtract3.

**GLiNER2** (Fastino) — fit: **niche**, a cheap second classifier of a
quoted span
- Licence and release: Apache-2.0; 2.0.0, 2026-08-24 [O].
- Ontology/schema binding: closed `choices`, relations, records [O,
  [repo](https://github.com/fastino-ai/GLiNER2)].
- Verbatim offsets: character spans [O].
- Scans: no.
- Weight: a ~287M-parameter mDeBERTa encoder; torch for local use [O].
- Open-world fallback: choices are closed per call; an `other` choice can be
  added.

**OntoGPT / SPIRES** — fit: **reject**
- Licence and release: BSD-3; 1.2.0, 2026-09-09 [O].
- Ontology/schema binding: a LinkML schema walked class by class, with
  values grounded through OAK [O].
- Verbatim offsets: none found.
- Scans: no.
- Weight: heavy, and it needs `litellm>=1.95`, which conflicts with the
  repo's `<=1.82.6` pin (see § 2.6) [O].
- Open-world fallback: **ungrounded entities are kept under `AUTO:` ids**
  (`--auto-prefix`), but no rate is reported [O,
  [docs](https://monarch-initiative.github.io/ontogpt/functions/)].

**LinkML** (as a schema language) — fit: not needed; `terms.csv` with
pydantic or jsonschema covers it [J]
- Licence and release: Apache-2.0; 1.11.1 [O].
- Ontology/schema binding: enums with `meaning:` URIs.
- Weight: rdflib, sqlalchemy and others.
- Open-world fallback: `permissible_values` are closed.

**ReLiK, Sycamore, Zerox** — fit: **reject**
- ReLiK: last release 2024-09; pins torch 2.3.1 [O].
- Sycamore: Ray-based and tied to Aryn's cloud partitioner [O].
- Zerox: stale since 2024; hosted VLMs only [O].
- Open-world fallback: none useful.

### 2.2 Structured-output enforcement

**vLLM structured outputs** — fit: **natural for a vLLM reader on the
A4000**
- Licence and release: Apache-2.0; 0.30.0, 2026-09-22 [O].
- What it enforces: `choice`, `regex`, JSON Schema, EBNF/Lark grammars and
  structural tags. Backends: xgrammar, guidance (llguidance) and
  lm-format-enforcer [O,
  [docs](https://docs.vllm.ai/en/latest/features/structured_outputs.html)].
- Weight: torch and CUDA (big).
- Open-world fallback: the schema decides. `anyOf[{enum}, {other, quote}]`
  is expressible [J].

**llama.cpp grammars** — fit: **natural for the 3060**, GGUF
- Licence and release: MIT; release tag v0.5.0, 2026-09-23 [O].
- What it enforces: GBNF, and JSON Schema converted to GBNF in
  `llama-server` (enums, patterns) [O,
  [README](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)].
- Weight: light (already on padme).
- Open-world fallback: `anyOf`/`oneOf` are supported "with limitations", so
  the escape is put as an enum value plus a sibling field [O/J].

**llguidance** — fit: **key enabler**, spike needed
- Licence and release: MIT; 1.9.1, 2026-09-30 [O].
- What it enforces: Lark CFG, regex and JSON. **`%regex {"substring_words":
  …}` forces an output string to be a contiguous substring of a given text**
  [O, [syntax](https://github.com/guidance-ai/llguidance/blob/main/docs/syntax.md)].
- Weight: a Rust wheel with no dependencies; it runs inside vLLM and, with a
  build flag, inside llama.cpp [O].
- Open-world fallback: the Lark alternation `enum | "OTHER" quote`, with the
  quote constrained to a substring of the part.

**XGrammar** — fit: via vLLM only
- Licence and release: Apache-2.0; 0.2.8 [O].
- What it enforces: JSON, regex and CFG; it is vLLM's default backend [O].
- Weight: torch.
- Open-world fallback: as vLLM.

**SGLang** — fit: **reject**, no gain over vLLM
- Licence and release: Apache-2.0; 0.5.20 [O].
- What it enforces: the same backends as vLLM.
- Weight: very heavy [O].

**Outlines, Instructor, BAML** — fit: **reject**; they duplicate the
server-side backends plus the pydantic already in the repo, and BAML adds a
DSL [J]
- Licences: Apache-2.0, MIT and Apache-2.0 [O].
- Outlines enforces in-process. Instructor validates with pydantic and
  retries. BAML does schema-aligned parsing, not constrained decoding [O].
- Weight: light to medium.
- Open-world fallback: Instructor's documentation recommends always adding
  an `OTHER` member [O, [docs](https://python.useinstructor.com/concepts/enums/)].
  BAML has `@@dynamic` enums extended at run time [O].

Two observations and one judgement about pinning:

- Both servers on padme enforce JSON Schema `enum`, so every closed list can
  be enforced at decoding time, from a schema generated out of `terms.csv`
  and `line-field-specs.csv` [O].
- llguidance's substring constraint would make every quote resolve by
  construction [O syntax; J effect]. Unverified: that vLLM's guidance
  backend passes the Lark extension through, the compile cost on a part of
  30–100k characters, and any loss of quality. A one-hour spike on padme
  settles all three.
- [J] The backend and its version must join the method-version pin, because
  mask semantics differ between xgrammar and llguidance. vLLM's `auto`
  backend selection must be replaced by an explicit one.

### 2.3 Document parsing and text layers

What the repo has [O]: **pdfplumber 0.11.9**, pinned at the call site
(`scripts/jetp/_vnm_inventory.py`), and BeautifulSoup/lxml for HTML. There
is no OCR and no xlsx reader in `scripts/jetp/`.

**pdfplumber** — fit: **keep** as the default adapter
- Licence and release: MIT; 0.11.10 [O].
- Positions: characters with page and x/y.
- OCR: none.
- Tables: rule and text strategies.
- Weight: light.

**Docling** — fit: **second adapter** where pdfplumber fails. The weights
must be pre-fetched and pinned, and the run kept offline [J].
- Licence and release: MIT; 2.131.0, 2026-09-29 [O].
- Positions: `prov` gives page, bbox and charspan; tables come with row and
  column offsets [O,
  [docs](https://docling-project.github.io/docling/concepts/docling_document/)].
- OCR: EasyOCR, RapidOCR (`vi`) and Tesseract [O].
- Tables: TableFormer.
- Weight: torch plus Hugging Face weights; releases come almost weekly.

**Tesseract 5 + OCRmyPDF** — fit: **cheap, pinnable recogniser** for the
held scan (Decision 458)
- Licences and releases: Apache-2.0 and MPL-2.0; 5.5.3 and 17.13.0 [O].
- Positions: hOCR word boxes.
- OCR: `vie` and `ind` in tessdata_best; known confusions on stacked
  Vietnamese diacritics [O,
  [issue](https://github.com/tesseract-ocr/langdata/issues/66)].
- Tables: no.
- Weight: system packages.

**Surya** — fit: alternative recogniser, with a licence caveat
- Licence and release: code Apache-2.0, weights under an OpenRAIL-M
  variant; 0.22.1 [O].
- Positions: lines and layout.
- OCR: Vietnamese at a 73.2% pass rate on its own benchmark [O].
- Weight: torch.

**PaddleOCR-VL 1.5, MinerU2.5** (small VLM recognisers) — fit: candidate
recognisers, with Vietnamese support unverified
- Licence: MinerU is **Apache-2.0 plus conditions**, not OSI-approved [O].
- Positions: page-level.
- OCR: PaddleOCR-VL 1.5 scores 94.5 on OmniDocBench [O].
- Weight: 0.9B and 1.2B.

**Camelot, img2table** — fit: only if pdfplumber fails on ruled tables
- Licences and releases: MIT; 2.0.0 and 2.0.0 [O].
- Positions: cell bbox.
- Weight: opencv.

**Rejected parsers:**
- marker: weights under OpenRAIL-M with a revenue threshold; hosted-LLM SDKs
  in its core.
- olmOCR: English-centred; output without positions.
- Unstructured: heavy core.
- PyMuPDF: **AGPL**.
- table-transformer: repository archived.
- VietOCR: last release 2021.
- trafilatura: removes boilerplate that locators need.

### 2.4 Commercial services, read as leads to open cores (decision 2)

| Service | Observed pipeline | Open core it builds on or resembles | Admissible open equivalent [J] |
|---|---|---|---|
| Reducto | CV layout pass, VLM OCR correction, VLM interpretation; field-level bbox citations [O, [what-is](https://llms.reducto.ai/what-is-reducto)] | proprietary | Docling + local VLM reader + our quote→locator check |
| LlamaExtract / LlamaParse | schema extraction; `cite_sources` (page + verbatim text); confidence; schema generation that "over-generates fields" [O, [docs](https://developers.llamaindex.ai/llamaparse/extract/guides/extensions/)] | MIT client SDK, closed engine | NuExtract template + verbatim quote + our aligner; ExtractBench's grounding F1 as a metric idea [O, [arXiv 2607.29677](https://arxiv.org/abs/2607.29677)] |
| Unstract | AGPL platform, Prompt Studio, Ollama adapters; hosted text extraction (LLMWhisperer) [O, [repo](https://github.com/Zipstack/unstract)] | itself open | admissible by licence, rejected for weight (Django, Celery, RabbitMQ, Postgres, Redis) |
| Sensible | SenseML: a declarative layout template (anchor, column, table) plus LLM methods [O, [docs](https://docs.sensible.so/docs/layout-based-methods)] | template parsers | our § 6.1 parser per series on pdfplumber |
| Azure DI, Google Document AI, AWS Textract | custom models from a few labelled documents; schema + few-shot; block extraction [O, secondary source only] | proprietary | Docling + Tesseract/RapidOCR; LangExtract is Google's open analogue of schema + few-shot + grounding |
| Mistral OCR 4 | bbox, typed blocks, confidence, a JSON-schema mode; self-hosting "for enterprise customers" [O, [news](https://mistral.ai/news/ocr-4/)] | open weights **not confirmed** | Surya, RapidOCR, NuExtract3 |
| Extend | no technical page read | — | not verified |

### 2.5 Pipeline and prompt optimisation

**DSPy 3.4.0** (MIT, 2026-09-25) fits the spec's split exactly [O]: its
optimisers, GEPA among them, read only a training set and score on a metric.
A GEPA metric could be our own checks (locator resolves, fields equal the
reference, value in a closed list), with the failure reason as feedback
text. It is compatible with the litellm pin.

Not at M2 [J]: strata under 30 invite overfitting, and the *rendered*
prompt, not the DSPy program, would have to be the pinned artifact. Revisit
after the first calibration. TextGrad is rejected: no release since
2025-03.

### 2.6 Constraints found in the repository

- **litellm pin.** litellm is capped at `<=1.82.6`, just below releases
  1.82.7 and 1.82.8, which were compromised on PyPI on 2026-03-24 [O,
  [advisory](https://docs.litellm.ai/blog/security-update-march-2026)]. Any
  candidate that needs a later litellm cannot be added without lifting that
  cap.
- **The current padme service** is one Qwen3.8-27B (Q4_K_M, 131k context)
  split across both GPUs (operation § 15) [O]. That is not the spec's
  one-model-per-card layout, and the model fits neither card alone at 4 bits
  [D].

### 2.7 Open-world fallbacks across libraries (author's addendum)

- **No library reports OOV rates. That count is ours to compute** [O/J].
- **Patterns that exist:**
  - OntoGPT's `AUTO:` ids for ungrounded terms;
  - Instructor's advice to add `OTHER`;
  - BAML's dynamic enums (a closed list loaded per method version);
  - GLiNER's zero-shot labels (open-world by construction);
  - NuExtract3's `template-generation` and LlamaExtract's schema generation
    (they propose fields; the closed engine warns that it over-generates).
- **Constrained decoders have no built-in escape.** The escape is a choice
  made in the schema.
- **The portable form** [J], which works on llama.cpp's `anyOf`
  limitations:
  `{"value": enum(terms in force + "other"), "own_word": verbatim,
  "other_quote": verbatim, required iff value == "other"}`.
  The `own_word` and `other_quote` slots are constrained to substrings of the
  part where llguidance is available.
- **`other` is not `unknown`.** In `terms.csv`, `unknown` means "not stated"
  (basis, date precision, modality). The escape means "stated, but outside
  the list". The two must stay distinct.

## 3. Local serving and models

### 3.1 What fits one card [D from configs; overhead assumed ~1 GB]

| Model (maker) | Licence | 3060 12 GB | A4000 16 GB | Context | Notes |
|---|---|---|---|---|---|
| Qwen3.5-9B (Alibaba) | Apache-2.0 | Q6_K + 128k q8 KV ≈ 10.5 GB | Q8_0 + 128k ≈ 14.6 GB | 262k | vision built in; only 8 full-attention layers keep the KV cache small [O, [card](https://huggingface.co/Qwen/Qwen3.5-9B)] |
| Gemma 4 12B (Google) | Apache-2.0 | Q4_K_M + 128k ≈ 10.5 GB | Q6_K + 128k ≈ 13.1 GB | 256k | **not on OpenRouter** [O, [models API](https://openrouter.ai/api/v1/models)] |
| Ministral 3 14B (Mistral) | Apache-2.0 | no (Q3 only) | Q4_K_M + 64k q8 ≈ 14.8 GB | 256k native, but the KV cache is heavy (160 KiB per token at f16) | third maker |
| Ministral 3 8B (Mistral) | Apache-2.0 | Q4_K_M + 64k ≈ 10.4 GB | yes | 256k | |
| NuExtract3 4B (counts as **Alibaba**) | Apache-2.0 | yes | yes | ~131k served | fine-tune of Qwen3.5-4B |
| Gemma 4 26B-A4B, Qwen3.6-35B-A3B (MoE) | Apache-2.0 | expert offload to RAM only | expert offload only | 256–262k | unmeasured on padme |
| Qwen3.8-27B (current service) | Apache-2.0 | no | only at ~3 bits (quality unmeasured) | 262k | today spans both cards |

Throughput [D, not measured]: the ceiling is 35–42 tokens/s per single stream.
One full pass is 1.1M output tokens per reader, which is **7–9 hours per
reader**, at the edge of the 10-hour GPU budget. Parallel slots or a more
compact output are needed. Design D4 (§ 5) addresses the second.

Maker rule: every NuExtract, Sailor2 and Qwen-SEA-LION model is a Qwen
fine-tune, so it counts as Alibaba (operation § 5) [O for the bases; J for
the rule's reach]. A NuExtract reader must therefore be paired with a Gemma
or Mistral reader. The spec could say this about fine-tunes in one sentence.

### 3.2 Multilingual evidence

- **SEA-HELM (2026-09-18) ranks larger models.** Gemma 4 31B leads in both
  Indonesian (79.75) and Vietnamese (77.09). Qwen3.6-27B follows (77.96 and
  76.12) [O,
  [ID](https://leaderboard.sea-lion.ai/detailed/ID),
  [VI](https://leaderboard.sea-lion.ai/detailed/VI)].
- **None of the 8–14B models that fit one card is listed there**, nor on
  VMLU [O].
- **Table QA in these languages is hard for 8B models.** On M3TQA, the
  previous-generation Qwen3-8B scores 37.5 in Indonesian, 28.8 in Vietnamese
  and 36.6 in French. Fine-tuning lifts Indonesian to 60.6 [O,
  [arXiv 2508.16265](https://www.arxiv.org/pdf/2508.16265)].
- **INDOTABVQA** reports "substantial performance gaps" on Indonesian table
  images [O, [arXiv 2604.11970](https://arxiv.org/abs/2604.11970)].
- **No evidence exists** that any 8–14B model can extract dated statements
  from Indonesian, Vietnamese or French policy documents [O, negative within
  the searches run]. The tuning part will be the first measurement.

### 3.3 Hosted pair under zero retention

OpenRouter's zero-data-retention routing is per request, with
`"provider": {"zdr": true}`, or account-wide. 923 endpoints qualify today
[O, [docs](https://openrouter.ai/docs/features/zdr),
[endpoint list](https://openrouter.ai/api/v1/endpoints/zdr)]. They cover
Gemma 4 26B/31B, Qwen3.5-9B, Ministral, DeepSeek V4.1 Flash, GLM, GPT (on
Azure), Gemini (on Vertex) and Claude (on Bedrock/Vertex). They do not cover
SEA-LION, Sailor2 or NuExtract.

Cost of one hosted reader per full pass [D]. Assumptions:
- the high case: 5.8M input and 1.1M output tokens;
- 3 characters per token;
- thinking switched off.

Results:
- Qwen3.5-9B: about USD 0.75;
- Gemma 4 31B: about USD 1.17;
- Ministral 3 14B: about USD 1.38;
- Gemini 3.8 Flash: about USD 8.5;
- Claude Haiku 4.5: about USD 13.6.

The arbiter: USD 5–55, depending on its tier and the escalation rate. The
model agent assumed 20–40 items per document. The spike projected 60–100
(7,000–12,000 for 115 documents), so the arbiter cost may be **2–3 times**
the agent's range [D]. Prompt caching of a document's pages cuts the
arbiter's input cost [O for the cache price; J for the size of the effect].

## 4. Spec default (baseline D0)

Two local readers of different makers, one per card, return free JSON. Code
checks the locator, with one repair call. The hosted arbiter handles
escalations. Calibration follows § 6.3.

Strengths:
- the money cost is only the arbiter;
- `local_only` documents are covered.

Weaknesses that the evidence above makes concrete:
- quotes retyped by 4–12B models fail the exact locator check (22 of 28 spike
  losses);
- 7–9 GPU hours per reader per pass;
- no model on one card has id/vi evidence;
- the thin strata send everything to the arbiter.

## 5. Candidate designs

The designs are not exclusive. D2 and D4 are *output contracts* that wrap
any pair of readers. D1 is a *placement* choice. D3 is a *routing* choice
made before reading. D5 departs from the spec.

**Gain scale.** Expected gains are against D0, on the pilot metrics.
"P(works)" is the probability that the design behaves as described on our
documents. All P(works) values and gains are judgements [J], anchored where
possible on the observed spike losses.

### D1 — Hosted pair of different makers (allowed by operation § 5)

**What it is.** Two economy open-weight readers on OpenRouter under zero
retention, of different makers: for example Gemma 4 31B (Google), which
leads SEA-HELM, with Ministral 3 14B or DeepSeek V4.1 Flash. The hosted
arbiter stays. `local_only` documents fall back to D0 on padme.

**Ontology binding.** As D0, unless combined with D2. Structured-output
support on OpenRouter depends on the routed provider (unverified).

**Open-world channel.** As D0: "cannot classify" only.

**Gain [J].** P(works) 0.6 that larger hosted readers beat local 9–12B
readers by at least 5 points of precision in id/vi. Expected:
- **+3 points of precision** in the id/vi strata;
- 14–18 GPU hours freed per pass;
- about USD 2–3 more per pass.

The method then depends on hosted endpoint availability, so a reader retired
or repriced by a provider forces a new method version.

**Complexity.** Low: no serving to maintain.

### D2 — Ontology-constrained decoding with an explicit out-of-vocabulary slot

**What it is.** Code generates a JSON Schema per document type:
- fields from `line-field-specs.csv`;
- `classification` as an enum of the line classifications in force, plus
  `other`;
- each field as a verbatim string;
- a per-item `other_quote`, required when `other` is chosen;
- an item-level `outside_fields` list of verbatim quotes (see § 5.6 (d)).

vLLM or llama.cpp enforce the schema at decoding. The readers can be
NuExtract3 (whose template language maps onto this directly) paired with a
non-Qwen reader, or any instruct model. Our locator check and calibration
stay unchanged. LangExtract can be tried as an alternative harness only with
fuzzy alignment off; dependency weight is the argument against it.

**Ontology binding.** Strongest: an off-list value is impossible to emit,
and the escape is explicit and counted.

**Open-world channel.** (a) to (e) of § 5.6, directly.

**Gain [J].** P(works) 0.85, since both servers enforce enum [O]. Expected:
- ontology conformance reaches 100% by construction;
- about **+5 points** of admitted items, from fewer rejections and repair
  calls on malformed output;
- the M2 OOV channel the author asked for.

**Complexity.** Low to medium: a schema generator of about 100 lines, and the
backend joins the method-version pin.

### D3 — Templates and parsers first for repeated layouts (extraction § 6.1, extended)

**What it is.** Before any LLM reading, cluster the 115 documents by
publisher × document type × layout fingerprint, using HTML DOM paths and the
PDF page landmarks of the existing parsers.

Candidates from the tracker's counts [O, ticket 1500]:
- 27 project pages;
- 19 data portals;
- 24 progress updates (Viet Nam 14, South Africa 9);
- 8 project lists.

The first parser is already planned for the Viet Nam progress updates
(tracker 1500 § Pipeline stages). Each cluster of three or more documents
gets a parser. The parser may be drafted by an LLM from two examples and is
then reviewed as code, like Sensible's SenseML templates. The parser refuses
documents whose landmarks are missing. The residue goes to D2 and D4.

**Ontology binding.** Values are hardcoded but reviewed. The parser refuses
an unknown column or landmark, which is the cleanest "missing field"
detector there is.

**Open-world channel.** An unknown header or label is a refusal with the
header quoted. It becomes a field-list proposal (§ 5.6 (d)).

**Gain [J].** P(works) 0.6 that 30 or more of the 115 documents go to
parsers. On that share:
- precision at parser level, with no escalation and no calibration needed;
- the gain is largest in the thin South African and Vietnamese strata (the
  progress updates);
- expected: about **a quarter of the documents** leave the reading lane.

**Complexity.** Medium: one parser per cluster, but it reuses the § 6.1
machinery that M2.1 builds anyway.

### D4 — Extraction by pointing: readers address units, code writes quotes

**What it is.** Code segments the text layer of each part into numbered
units:
- PDF: lines, or table cells by row and column;
- HTML: blocks;
- spreadsheets: cells.

The reader sees the numbered units and returns, per item:
- the unit identifiers;
- the start and end word inside each unit for the label and each field;
- the classification (closed enum, per D2);
- a self-score.

Code reconstructs the verbatim quote and the locator from those addresses.
With llguidance, ids can be constrained to the part's unit set and spans to
its words.

**Ontology binding.** As D2, with which it composes.

**Open-world channel.** As D2. In addition, units with in-scope tokens
(currency, numerals with units, dates, party names) that no item addresses
can be counted: the **uncovered-unit census**, a mechanical gap detector
(§ 5.6 (d)).

**Gain [J].** P(works) 0.7 that 9–14B readers address units accurately.
The risk is mis-addressing a unit, which code cannot detect as a *failure*.
The § 6.3 rule that the "text there must contain the proposed label and
values" becomes "the readers agree on the address", so the planted-item
control matters more. Expected:
- locator resolution near 100% by construction, which removes most of the
  spike's 22-of-28 loss: about **+15 points of recall**;
- output tokens down by roughly half, which brings the 7–9 GPU hours under
  budget;
- simpler alignment of the two readers (same unit ids).

**Complexity.** Medium: a segmenter per format. It is mostly the § 5
locator code run in reverse.

### D5 — Single reader plus checker (considered, not proposed for the pilot)

**What it is.** One strong reader proposes. A second model of another maker
only checks each proposal against the quoted unit (yes, no or edit), and the
arbiter handles the disagreements.

**Why it is not proposed.**
- It breaks § 6.3's two blind readers.
- The agree-but-wrong rate is no longer measured on independent readings.
- Recall rests on one reader.

**Gain [J].** About **-40% reader cost**, at the price of a spec amendment,
an unmeasurable independence, and a recall loss.

Recommendation: keep it out of the pilot unless D1, D2 and D4 all fail the
budget.

### 5.6 How each design brings up new classes, values or fields (author's addendum)

**(a) A generic out-of-vocabulary answer for every closed-list slot, with
verbatim evidence.**
- D2 and D4 implement it at decoding time: `other` plus a substring-
  constrained `other_quote`.
- D0 and D1 have only "cannot classify", for classification alone.
- D3 has it as a parser refusal that quotes the unknown value.
- At M2 the readers fill only one closed list (classification). The others
  (measures, roles, flow types, timing roles, units) are filled at M3b
  (ontology § 4). The slot pattern should still be defined once now, so
  that M3b inherits it.

**(b) OOV counts per list in the run report.** These are new run-report
rows, keyed per list, per document type, per reader and per stratum. They
are computed from the readings journal. No library provides them (§ 2.7).
This is cheap in every design [J].

**(c) Proposals as `terms` rows.**
- The panel that already groups "cannot classify" items writes a
  `candidate` row: `decided_by` is the panel and the run, and `notes` cites
  the readings.
- `terms_in_force` keeps only `accepted` rows, so a candidate row
  classifies nothing [O, `config/jetp-ledger.sql`]. This matches extraction
  § 3's "a proposed class classifies nothing".
- Adoption is the author's, as a new method version that re-reads the
  recorded items.
- No schema change is needed. A storage check that every `candidate` row
  cites at least one reading would be the only addition [J].

**(d) Detecting missing fields.** Three mechanisms, by design:
- *Parser refusal* (D3): an unknown column header stops the parser, and the
  header is quoted.
- *Uncovered-unit census* (D4): units with in-scope tokens that no item
  addresses.
- *An `outside_fields` slot* (D2): the reader quotes an in-scope assertion
  that no fixed field can hold. It does not name a field, so the "a reader
  never proposes a field" rule holds.

The panel groups these quotes into field-list proposals for the author.
This feeds the same author-decision loop as new classes.

**(e) OOV rate as a pilot metric.** Report the rate per list and per stratum
as a descriptive metric. Report alongside it the **OOV precision**: the
share of `other` answers that the non-author checker judges genuinely
off-list. A reader that dumps hard items into `other` would otherwise score
well on conformance and badly on recall.

## 6. Reference lines per stratum (task C)

**Observation.** Counted on `origin/main` at 978fd68c, 2026-10-01, read-only
from:
- `data/jetp/lines.d/` (22 shards, 13,092 lines);
- `snapshots.csv`, `retrievals.csv` and `documents.csv`.

The script is in Appendix A.

The 10,452 comparator records are excluded: CRS 8,032, IATI 1,301 and World
Bank 1,119, all in snapshots kept outside the document store. 2,640 lines
remain. They fall into four method families, read from the identifier family
as storage contract § 1 prescribes for lines admitted before the method
columns existed:

| Family | Lines | What it is | Reference answer under § 6.3? |
|---|---:|---|---|
| R1 decision-scoped keys (`line-1160-…`, `idn-progress25-…`) | 130 | lines read from the source during the 0970 and 1160 reconciliations | the operational candidate; it equals the "about 130" of the wave-2 review (W2-04): Indonesia 84, Senegal 46 |
| R2 legacy migrated (`…-claim-N`, `…-portfolio-N`, `…-discovery-N`, the 0877 and 1620 lines) | 233 | source claims, Indonesian portfolio observations and legacy links carried over by 0874 and 0875 | candidate; provenance not recorded |
| R3 Viet Nam pilot ledger record (`vnm-pilot-observations-local-record-row-N`) | 112 | observations of the Viet Nam pilot. They are located in a ledger CSV ("CSV row 28"), not in the publisher's document, and their labels were composed in French | no: no proposal can be matched against them without re-anchoring |
| P parser output (Indonesian CIPP and progress report, Viet Nam RMP annexes, South African register, Senegal plan annexes) | 2,165 | extractor-minted rows of five reviewed parsers | no: machine-made. A possible "silver" set for table rows, but only by spec amendment |

**Provenance caveat (observation).** No family carries a flag saying a
person made the line blind to any machine reading:
- The closed tickets 0970 and 1160 name an LLM coding agent (Codex) as the
  author of the reconciliation that wrote R1.
- The R2 lines come from earlier tables whose authorship the ledger does
  not record.
- The wave-2 review already found the set "not derivable" (W2-04 (a)).

Whether any reference line is human-made in the sense of extraction § 6.3 is
therefore **unverified**. The pilot protocol must state which family it
treats as reference answers.

### 6.1 Language × statement shape

**How shape is assigned.** A heuristic over the locator and the document
type:
- *table row*: the locator names a table, row, annex, appendix, cell or
  unique ID;
- *record page*: a JSON or API record, a project page or a data-portal page;
- *prose span*: everything else.

No line is a transcription.

**Held-out assumption: a 50/50 split.** The spec fixes a seeded split into a
tuning part and a held-out part, but states no proportion (extraction
§ 6.3). Under 50/50, a stratum needs 60 lines to reach 30 held-out items.

| Language | Shape | R1 | R1+R2 | Held-out at 50/50 (R1+R2) | Informative (≥ 30)? |
|---|---|---:|---:|---:|---|
| English | table row | 81 | 100 | 50 | yes |
| English | prose span | 2 | 76 | 38 | yes (R1 alone: no) |
| English | record page | 1 | 60 | 30 | borderline (R1 alone: no) |
| French | table row | 29 | 35 | 17 | **no** |
| French | prose span | 11 | 51 | 25 | **no** |
| French | record page | 6 | 24 | 12 | **no** |
| Indonesian | any | 0 | 0 | 0 | **no** |
| Vietnamese | any | 0 | 0 | 0 | **no** |
| any | transcription | 0 | 0 | 0 | **no** |
| language not recorded | prose, record, table | 0 | 14 | 7 | **no** |
| Japanese, German, Chinese | prose span | 0 | 3 | 1 | **no** |
| **Total** | | **130** | **363** | | |

With R1 alone, the only informative stratum is English table rows: 81 lines,
40 held-out, all from Indonesia. Under either definition, every French,
Indonesian, Vietnamese and transcription stratum is thin.

The parser rows (P) are all table rows, none of them Vietnamese-language:
- Indonesia: 1,142 English rows and 437 rows with no recorded language
  (Indonesian labels);
- Viet Nam: 279 English rows;
- South Africa: 257 English rows;
- Senegal: 39 French rows.

### 6.2 Country

| Country | R1 | R1+R2 | Held-out at 50/50 | Pending documents (of 115) |
|---|---:|---:|---:|---:|
| Indonesia | 84 | 180 | 90 | 13 |
| Senegal | 46 | 130 | 65 | 28 |
| South Africa | 0 | 52 | 26 (**thin**) | 49 |
| Viet Nam | 0 | 1 | 0 (**thin**) | 25 |

**Inference.** The reference set and the pending work are mismatched:
- South Africa and Viet Nam hold 74 of the 115 pending documents, but only
  53 of the 363 candidate reference lines.
- The 20 pending Vietnamese-language documents have no reference line at
  all.

Under the accepted fallback (author default of 2026-09-30), those strata run
with every item sent to the arbiter and are named uncalibrated. Hence:
- D3 is worth most there (parsers need no calibration);
- D4 and D2 cut what reaches the arbiter in every stratum.

## 7. Draft pilot protocol (to be committed under ticket 1890 before any call)

This is a draft. Ticket 1890's exit criterion is the committed version.

**Arms.** Arms A1 and A2 differ only in where the readers run, so their
difference measures D1.
- **A0 = D0**: the spec default, with free JSON.
- **A1 = D2 + D4, local pair**: NuExtract3 on the A4000 with a Gemma 4 12B
  or Ministral reader on the 3060. Gemma 4 12B is scored locally because it
  is not on OpenRouter.
- **A2 = D2 + D4, hosted pair**: for example Gemma 4 31B with Ministral 3 14B
  or DeepSeek V4.1 Flash, under zero retention.
- **D3 is not an arm.** It is a triage step. The pilot measures how many of
  the 115 documents it routes to parsers, and the parser itself is tested
  under § 6.1.

**Samples.**
1. *Scored sample.* Drawn from the tuning part only (the split is made first,
   by a recorded seed), stratified by country × format × statement shape.
   The documents that hold the reference lines are read in full, and
   proposals are matched to reference lines by the match rule of W2-04
   (same snapshot and page, same classification, and the reference numerals,
   dates and party contained in the quote). Size: every tuning-part line of
   at most 12 documents, chosen to cover each non-empty stratum at least
   once.
2. *Unscored sample.* Drawn from the 115 pending documents: 3 per country
   (12 in total), covering PDF with tables, HTML, a spreadsheet and the
   largest text layer (as a part plan, not whole). These measure what needs
   no reference: locator resolution, conformance, OOV, cost and wall time.

**Metrics,** per arm and per stratum:
- precision, recall and the agree-but-wrong rate (scored sample, Wilson
  intervals);
- locator-resolution rate before and after the repair call;
- ontology-conformance rate (values in force, or `other` with a quote);
- OOV rate and OOV precision (§ 5.6 (e));
- the uncovered-unit census (arms with D4);
- the escalation rate and arbiter calls;
- USD per document, and GPU wall time per document;
- operational complexity, scored on a fixed checklist: services to run,
  pinned artifacts, failure modes seen.

**Quality check.** A non-author, cross-model checker of a third maker. It
reads a random 20% of admitted items per arm, and every OOV answer. Only its
residue is reported to the author (pilot rule, tracker 1500).

**Decision rule (pre-registered).**
1. Exclude any arm whose locator resolution after repair is below 0.95, or
   whose projected full-pass cost exceeds USD 60 or 10 GPU hours per reader.
2. Among the rest, choose the highest recall, provided that the lower Wilson
   bound of end-to-end precision is at least A0's point estimate and the
   agree-but-wrong rate is no higher than A0's.
3. If two arms fall within one standard error, choose the lower operational
   complexity.
4. If A2 wins, `local_only` documents still run under A1, as another method
   version.

**Budget [D].** About 24 documents × 3 arms. Hosted reading costs under
USD 5 and the arbiter under USD 10. That fits the USD 20 selection run.

## 8. Expected gains, ranked [J]

| Rank | Design | P(works) | Expected gain against D0 |
|---|---|---:|---|
| 1 | D4 pointing | 0.7 | +15 recall points; output tokens down by about half; GPU time within budget |
| 2 | D3 templates first | 0.6 | about a quarter of documents leave the reading lane, at parser precision, mainly in the thin South African and Vietnamese strata |
| 3 | D2 constrained decoding + OOV slot | 0.85 | 100% conformance; about +5 points of admitted items; the OOV channel |
| 4 | D1 hosted pair | 0.6 | +3 precision points in id/vi; frees 14–18 GPU hours; +USD 2–3 per pass |
| — | D5 single reader + checker | — | -40% reader cost, but needs a spec amendment; not proposed |

All the figures above are judgements. They are anchored on the spike's 22
of 28 locator losses, on the tracker's counts by type, and on the observed
enforcement of enums by both servers. They become measurements only through
the pilot.

## 9. Not verified

- That vLLM's guidance backend accepts llguidance's `substring_words`, and
  the compile cost on a 30–100k-character part.
- NuExtract3's language coverage and accuracy in Vietnamese and Indonesian,
  and whether its reasoning mode keeps verbatim strings exact.
- Any Indonesian or Vietnamese score for the 8–14B models that fit one card.
- padme's real throughput (the figure above is a bandwidth-derived ceiling).
- Statements per document for the 115 documents, and the escalation rate.
  Together they move the arbiter cost by a factor of 4 or more.
- Docling's handling of hidden XLSX sheets and hidden HTML, and whether it
  makes network calls after its weights are cached.
- Whether Mistral OCR 4 is released with open weights; Extend (no technical
  page read).
- Whether any reference line is person-made and blind to machine reading
  (§ 6).
- The statement-shape heuristic, which was not hand-checked line by line.
- The JETP spike cost (USD 14–26, from the brief). No cost record of it was
  found in `conception/`, `docs/` or `tickets/`.

## Appendix A. Count script (read-only; run from the repository root)

```python
import csv, glob, collections, re
D = 'data/jetp/'
rows = [r for f in sorted(glob.glob(D + 'lines.d/*.csv')) for r in csv.DictReader(open(f))]
snaps = {s['sha256']: s for s in csv.DictReader(open(D + 'snapshots.csv'))}
docs = {d['document_id']: d for d in csv.DictReader(open(D + 'documents.csv'))}
sha2doc = collections.defaultdict(set)
for r in csv.DictReader(open(D + 'retrievals.csv')):
    if r['sha256']:
        sha2doc[r['sha256']].add(r['document_id'])
PARSER = ('idn-jetp-progress-report-2025', 'idn-cipp-2023', 'vnm-rmp-2023',
          'zaf-jet-investment-register', 'sen-investment-plan')

def group(lid, path):
    if path.startswith(('../comparison/', '../iati')) or 'world-bank' in path:
        return 'comparator'
    if path.startswith('../ledger-snapshots'):
        return 'R3'
    if lid.startswith(('line-1160', 'idn-progress25')):
        return 'R1'
    if lid.startswith(PARSER) and not re.search(r'-claim-\d+$', lid):
        return 'P'
    return 'R2'

def shape(loc, doc, ctype):
    if re.search(r'table|row|annex|appendix|cell|unique id|csv row', loc, re.I):
        return 'table row'
    if 'json' in ctype or loc.startswith(('API', 'Project heading')) \
            or doc.get('document_type') in ('project_page', 'data_portal'):
        return 'record page'
    return 'prose span'

tab = collections.Counter()
for r in rows:
    s = snaps.get(r['sha256'], {})
    g = group(r['line_id'], s.get('storage_path', ''))
    ds = sorted(sha2doc.get(r['sha256'], []))
    doc = docs.get(ds[0], {}) if ds else {}
    tab[(g, r['country'], doc.get('language') or '(none)',
         shape(r['locator'], doc, s.get('content_type', '')))] += 1
for k, v in sorted(tab.items()):
    print(*k, v, sep='\t')
```
