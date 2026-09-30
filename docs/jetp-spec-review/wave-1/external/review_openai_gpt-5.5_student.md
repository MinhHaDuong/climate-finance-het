# Peer review — openai/gpt-5.5, persona: student

## Review of the JETP Observer system specification v0.1

### Summary judgement

This is an unusually thoughtful specification for a one-researcher documentary data system. The strongest parts are the insistence on append-only records, locators to exact snapshots, frozen citable releases, explicit uncertainty, and the refusal to collapse documentary statements into “facts.” Those choices are exactly right for a politically contested climate-finance dataset.

But as a system specification, it is not yet implementable at the level of trust it promises. The document mixes conceptual requirements, current legacy state, target schema, future operational aspirations, and methodological claims in ways that make several tests impossible or circular. The largest risks are: unclear bitemporal/provenance semantics; under-specified human validation; overconfidence in LLM agreement; legal/licensing exposure around redistribution and excerpts; and an entity-resolution/review workload that will likely swamp one researcher before 2030.

My overall verdict is **major revision**: the architecture is promising, but the spec should not be frozen or used as the binding implementation contract until the issues below are resolved.

---

# 1. Internal coherence

## 1.1 Conceptual “must hold” vs implementation “target” is not clean enough

The entry document says conceptual documents state what must hold, implementation documents state how. That separation is useful. But in practice the specification repeatedly depends on implementation details that are explicitly not yet present.

Examples:

- **Storage §1 “Target schema”** lists columns required by Fusion and Results — `recorded_at`, `stance`, `likelihood`, `basis`, decision-member rows, triage tables, frame entries, rounds, candidates, tracker claims — but says the DDL does not yet carry them. Yet Requirements assign many of the dependent behaviours to **M2 or M3b**.
- **Fusion §8** and **Results §9** rely on correction overlays and as-of states, but the storage contract admits current in-force views still implement an earlier supersession rule.
- **Collection §9** treats triage outcomes as recorded judgements at M3a, but the target tables for candidates and triage judgements are still future changes.

This makes the tests ambiguous: is a requirement “met” if the conceptual document says it, or only when the storage contract actually supports it? The spec needs a single conformance rule: **no requirement can be marked met while its required storage columns/tables are still “target.”**

## 1.2 The bitemporal model is close but not yet coherent

The spec rightly distinguishes world time and knowledge time, but there are more than two times in play:

1. event time — when a disbursement, approval, signature, etc. occurred;
2. publisher reporting cutoff;
3. publisher publication date;
4. retrieval time;
5. extraction/admission time;
6. judgement decision time;
7. release knowledge cutoff;
8. correction-overlay admission time.

These are partly captured across **Ontology §2 Observation**, **Fusion §1 “Two times”**, **Fusion §8**, **Storage §1**, and **Results §2**, but not as one formal temporal contract.

Specific confusions:

- **F10** says a result at cutoff K uses only what was admitted on or before K. But **Collection §11** says the frozen register has a discovery cutoff and the knowledge cutoff may be later. Which rows are admitted at which time: documents, snapshots, lines, observations, decisions, or all of them separately?
- **Storage §1** says M2 document admission is dated by earliest retrieval, while from M3a it is a triage judgement. This means the semantics of “admitted before K” changes across milestones.
- **Results §9** says a correction release keeps K and applies a named overlay. That is good, but the overlay rule needs formal constraints: which row types may be included? Can a correction overlay include a new line extracted after K from a snapshot retrieved before K? Can it include a newly discovered document whose publication date precedes K? The text says no later discovery, but edge cases need to be explicit.

Recommendation: add a short **Temporal contract** table listing every row type and its valid/event time, publication time, retrieval time, transaction/recorded time, and release-cutoff eligibility.

## 1.3 “Neutral documentary record” is underspecified and partly contradicted

The neutral-record rule is valuable, but it is too broad as written.

- **Q16** says the Observer does not assert findings in its own voice other than declared calculations.
- But **F8**, **Collection §3**, and **Results §4** require conclusions such as “not published,” “blocked,” “loss of visibility,” “stopped by cap,” and “tracker traceability rate.” These are not publisher statements; they are Observer findings.
- **F19** asks for gaps between announced, signed, reported and disbursed amounts. Those gaps can easily be read as evaluative even if labelled as calculations.

This is not a fatal contradiction, but the rule should be reframed. The Observer cannot avoid making methodological findings. Better wording: **the Observer may assert only documentary, procedural, and calculation findings under declared methods; it does not assert compliance, blame, policy merit, or causal explanation.**

## 1.4 The same word sometimes has incompatible roles

The language document does a good job trying to retire terms, but some conflicts remain.

- **Statement**: Language says statement is generic; Extraction says statement is D2 line; Observatory’s Statements page shows D3 observations. This is likely to confuse users and developers. The presentation choice to call D3 “Statements” while builders call D2 “statements” is risky.
- **Operation**: Language admits both lender operation and running the Observer. That is manageable but dangerous in code, tickets and user docs.
- **Source** is retired, but many users will naturally ask for “sources.” Avoiding the word entirely may hurt usability.
- **Evidence** is reserved for computed results, while ordinary readers will treat documents as evidence. This may be internally consistent but externally counterintuitive.

I would strongly consider renaming the public “Statements” page to **Observations** or **Attributed statements**, and consistently using **Document rows** for D2.

## 1.5 Some tests are subjective or circular

Many tests are excellent and concrete. Others cannot really be tested.

Examples:

- **Q16**: “no evaluative wording” — requires human judgement and will be language-dependent.
- **F26**: “plain-language definition a general reader follows” — no testable reader population is defined.
- **Q13**: “no causal or speed claim” — easy to violate subtly; the test says an integration review finds none, but gives no review protocol.
- **Q10 known-item recall**: the known-item list is compiled by the same researcher who knows the field and may run the searches. **Collection §6** says blind use, but with one researcher true blindness is doubtful.
- **Q5 likelihood/confidence from LLMs**: no calibration test is given. LLM confidence language is not a calibrated probability estimate.

The spec should distinguish **mechanical validation**, **method review**, and **human editorial judgement**, rather than phrasing all as equally testable requirements.

## 1.6 Current counts conflict with M2 requirements unless M2 is explicitly future

**DA2** says there are 392 registered documents, 369 snapshots, 254 extracted, 115 held but not extracted, and 23 without snapshots. It also says every one of the 392 must satisfy F2 at M2. That is fine if M2 is future, but elsewhere M2 sounds like the immediate instrument and some ontology/storage parts are already “in force.”

Similarly:

- **DA5** requires no document has unknown language at M2, but says 20 of the 115 currently have none.
- **Q1** requires replay of already extracted statements, but many legacy statements predate method columns and anchor rules.

This is resolvable, but the spec should clearly label each count as **current state**, **M2 acceptance target**, or **post-M2 invariant**.

## 1.7 Publisher attribution for lines is not fully modelled

**F1** says each statement carries its publisher. **Ontology §2 Document** allows multiple publishers. **Extraction §4** allows quoted speakers. **Storage §1 lines** table does not appear to have a `publisher_id` or `speaker_id`; publisher is presumably inferred from document-publishers.

That fails in common cases:

- joint publications with multiple publishers;
- documents authored by a consultant for a commissioner;
- a news item quoting a ministry, bank, or operator;
- annexes within a larger report with different institutional responsibility.

If “who stated what” is central, a line/observation needs explicit attribution: publisher-as-document-responsible-party, printed speaker where relevant, and possibly author/commissioner.

## 1.8 Locator uniqueness may fail for prose

**Storage §1** requires `(sha256, locator)` unique across lines. **Extraction §4** says prose is extracted when it asserts something in scope, each assertion one statement anchored on its own words. But a single sentence can assert an amount, date, project status, and funder. Either:

- all assertions share the same locator, violating uniqueness; or
- locators need subspans or assertion identifiers within the same text span.

The spec should define whether one sentence with several in-scope assertions is one D2 line yielding several D3 observations, or several D2 lines with distinct sub-locators.

## 1.9 “External identifier decides” is too strong

**F12**, **Fusion §3 Organisations**, and **Ontology §2 External identifier** say an external identifier decides where one exists. In practice:

- IATI organisation identifiers are inconsistent and reused loosely.
- Wikidata items can split or merge entities incorrectly.
- LEIs can identify branches or legal entities, not necessarily the policy organisation of interest.
- ROR is incomplete for public agencies and utilities.

External identifiers should be **high-weight evidence**, not automatic identity, unless the scheme and entity granularity are declared compatible.

---

# 2. Fitness for purpose

## 2.1 The core design is well matched to the users

For think tanks, journalists, researchers and negotiators, the most valuable features are:

- exact document/snapshot/locator trails;
- frozen releases with persistent identifiers;
- append-only corrections;
- visible disagreement and unknowns;
- separation between publisher statements and Observer calculations;
- “what was sought and not found” as data.

These are exactly the right design principles for a contested documentary dataset.

## 2.2 Trustworthiness will depend on validation, not just traceability

Traceability lets readers inspect errors; it does not by itself estimate error rates. The specification has many checks, but lacks an explicit validation design.

Missing:

- accuracy targets for extraction, reading, matching and preference judgement;
- sample-size calculation for human review;
- stratification by country, language, document type, publisher, extraction method and financial state;
- inter-reader agreement or second-reader protocol;
- serious-error definition;
- release-blocking quality thresholds.

The prompt says the dataset is “checked by a second reader and a sampled human review,” but the specification mostly mentions the author plus LLM reader/checker. If there is a second human reader, their role must be in Requirements, Operation, Extraction and Fusion.

For a citable dataset, I would expect something like:

- 100% human review for a small set of critical release figures;
- stratified random review of D2 lines and D3 observations;
- clerical review of high-impact entity matches;
- reported precision/recall/error rates with confidence intervals;
- a correction policy tied to severity.

## 2.3 Citable releases are well specified, but reproducibility is limited by document access

**Results §7** correctly says bytes are redistributed only where allowed. But **Q8** asks an independent reader to reconstruct results over documents that have a public copy. This is realistic, but the release should be honest that some results may not be independently reproducible if the source disappears and redistribution is prohibited.

The spec should classify each result by reproducibility level:

1. fully reproducible from redistributed bytes;
2. reproducible from public archive capture;
3. reproducible only if the source remains available;
4. not independently reproducible because the public source has disappeared and bytes cannot be redistributed.

This matters for journalists and negotiators who need durable citations.

## 2.4 The release licence is legally overconfident

**F30** says each release is under an open licence. But the release includes verbatim labels, short excerpts, possibly table rows, and metadata from third-party documents. The Observer can open-license its own database structure, annotations, decisions and calculations, but it may not be able to open-license copied text from source documents.

This is a serious issue. The release needs layered rights:

- Observer-created metadata and calculations: open licence, e.g. CC BY 4.0 or CC0 where possible.
- Third-party excerpts/labels: included under quotation/fair dealing/fair use or specific source terms, not relicensed.
- Source bytes: redistributed only under source terms.
- Code: OSI licence.
- Metadata record: preferably CC0.

Without this distinction, the release could overgrant rights it does not possess.

## 2.5 Some parts are over-built for M2/M3

The following seem heavier than needed before the first citable release:

- elaborate CSV sharding at 512 KB per file;
- ODEM terminology as an organising principle;
- full ontology table machinery for all value lists;
- future RDF/SKOS export discussion;
- detailed browser navigation mechanics;
- multiple milestone-specific operational constraints;
- agentic-development governance as a first-class architectural layer.

None is wrong, but they distract from the minimum needed for trust: provenance, validation, release packaging, and legal clarity.

## 2.6 Some parts are missing or under-built

More important missing items:

- data protection/privacy policy;
- copyright/licensing analysis;
- model/API data-retention policy;
- human validation plan;
- quality metrics and release gates;
- disaster recovery beyond local DVC copy;
- dependency lockfiles and long-term reproducibility strategy;
- governance for corrections, disputes and publisher challenges;
- citation style and metadata mapping to DataCite/Zenodo/RO-Crate;
- explicit data dictionary template.

---

# 3. State of the art in knowledge management and data science

## 3.1 Provenance: should align with PROV-O or RO-Crate earlier

The system already has provenance concepts: publisher, document, retrieval, snapshot, line, observation, method, run, decision, release. This maps naturally to:

- **W3C PROV-O**: `Entity`, `Activity`, `Agent`, `wasGeneratedBy`, `wasDerivedFrom`, `wasAttributedTo`, `used`.
- **RO-Crate**: packaging release files, metadata, software, workflows and provenance.
- **DataCite**: persistent identifier metadata and relation types.
- **DCAT/schema.org Dataset**: discoverability.
- **Frictionless Data Package**: tabular data dictionary and constraints.

The spec says RDF projection is “later” and a graph engine is unwarranted. That is fine for the engine, but not for the metadata model. I would not wait for a consumer before using RO-Crate/DataCite/Frictionless-style metadata in the release package. It will reduce reinvention and improve FAIR compliance.

## 3.2 Bibliographic modelling: document/version/snapshot needs FRBR-like clarity

The spec has documents, editions, translations, retrievals and snapshots. This is good, but it partly reinvents bibliographic versioning.

Useful established distinctions:

- Work / Expression / Manifestation / Item from FRBR/LRM;
- web resource vs representation;
- Memento datetime negotiation concepts;
- WARC records for captures;
- Dublin Core bibliographic metadata;
- DataCite relation types: `IsNewVersionOf`, `IsPreviousVersionOf`, `IsTranslationOf`, `IsSourceOf`, etc.

Current ambiguities:

- Is a “document” a work, expression, manifestation, or logical publication?
- Is a PDF export and HTML page one document or two manifestations?
- Is a translation a different expression or a related document?
- Is a living page’s snapshot a version or an item state?

You do not need to adopt FRBR wholesale, but the spec should explicitly map to it or explain the simpler local model.

## 3.3 Bitemporal data: strong instinct, incomplete formalization

The “two times” principle is one of the best parts. But the state of the art in temporal databases would call for explicit:

- valid time / event time;
- transaction time / system time;
- assertion/publication time;
- retrieval/observation time;
- correction vs restatement semantics.

At present these are spread across Fusion, Storage, Extraction and Results. A compact bitemporal design note would prevent many future errors.

## 3.4 Entity resolution: pairwise judgements and depth-one equality are fragile

**Fusion §3** bounds equality between referents to depth one: chains are raised as conflicts and resolved manually. I understand why: transitive closure can silently create bad clusters. But making equality non-transitive is also semantically odd and operationally expensive.

State-of-the-art record linkage typically uses:

- blocking/candidate generation;
- pairwise scoring;
- clerical review;
- clustering with constraints;
- cluster-level diagnostics;
- active learning;
- labelled benchmark sets;
- metrics such as pairwise precision/recall, B-cubed, CEAF, cluster purity, split/merge rates.

Tools such as **Splink**, **Dedupe**, or even a simple Fellegi–Sunter model could provide a more disciplined baseline than ad hoc tiers plus LLM judgement.

The spec does mention blocking recall, pairwise precision/recall and one cluster metric, which is good. But it needs an explicit ER evaluation protocol and a feasible clerical-review budget.

## 3.5 Uncertainty communication: good principles, weak calibration

The IPCC likelihood/confidence scale is a sensible human-facing vocabulary. But LLMs cannot be assumed to emit calibrated likelihood/confidence. The spec should require calibration checks:

- reliability diagrams or expected calibration error on a labelled set;
- Brier score for binary match decisions;
- separate calibration by language and document type;
- “confidence” derived from evidence quality and reader agreement, not simply model self-report.

Also, the inclusive threshold “about as likely as not or more, any confidence” in **Results §3** is too permissive for public figures. “Any confidence” includes very low confidence. If used, it should be clearly labelled as a stress-test scenario, not an inclusive estimate.

## 3.6 LLM-as-judge practice: promising, but not sufficient

Good practices already present:

- reader/checker separation;
- different vendors;
- no tools/network for document-reading prompts;
- prompt-injection controls;
- recorded prompts, model versions and costs;
- retained outputs rather than re-running nondeterministic calls.

Missing or weak:

- no primary human gold standard except sampled author review;
- no acceptance thresholds;
- no model-retirement strategy beyond replacement testing;
- no vendor API data-retention assessment;
- no structured-output validation details;
- no adversarial multilingual evaluation;
- no plan for prompt/version drift over years.

For high-stakes release figures, “two LLMs agree” should not be enough. Agreement between similar systems can be correlated error, especially on finance terminology and multilingual documents.

## 3.7 FAIR: mostly right direction, but incomplete

The FAIR assessment is thoughtful. To be more state-of-the-art:

- Use **DataCite** metadata for releases.
- Include **ORCID** for creator, **ROR** for affiliations where applicable.
- Use **SPDX** licence identifiers.
- Include **CITATION.cff** and **CodeMeta** for code.
- Package data with **RO-Crate** or **Frictionless Data Package**.
- Publish machine-readable schema constraints.
- Provide stable landing pages and content hashes.
- Document non-redistributable source limitations as FAIR exceptions.

The spec talks about FAIR but needs a concrete FAIR implementation profile.

---

# 4. Implementation realism for one researcher and a workstation

## 4.1 The human review budget is the main bottleneck

The author’s attention is correctly identified as the scarce resource. But the proposed controls do not yet make the workload bounded in practice.

Potential explosions:

- every LLM extraction proposal checked by another LLM;
- author reviews all disagreements, missed items, and a random sample;
- entity matching across plans, progress reports, CRS, IATI, World Bank, project pages and operators;
- correction propagation;
- release validation;
- legal/rights decisions per document;
- discovery rounds in four countries and four languages;
- weekly living-document snapshots by M4.

The Indonesian example alone — 437 CIPP lines against 1,142 progress-report lines — implies a large candidate space. If CRS/IATI comparator records add thousands more, clerical review will grow quickly unless blocking and active learning are very strong.

The open question in **Extraction §14** — sample size shown to the author — is not minor. It is central to feasibility and quality.

## 4.2 Cost estimates are plausible for extraction, not for the whole system

**Operation §7** estimates M2 LLM costs at USD 15–30 for the 115 unextracted documents. That may be plausible for extraction if prompts are compact and documents are chunked efficiently.

But total cost is not just extraction:

- checker calls;
- repair calls;
- missed-item detection;
- matching judgements;
- discovery triage;
- preference/conflict judgements;
- repeated M4 refresh;
- model replacement validation;
- long PDFs near one million characters;
- multilingual tokenization overhead;
- retries and malformed outputs.

The spec should separate measured prototype costs by task type: extraction, observation reading, triage, matching, preference judgement, release validation.

## 4.3 The CSV-in-Git plus SQLite-derived engine is workable but brittle

Keeping CSV in Git as the adjudicated record is defensible. But the current design is elaborate:

- 512 KB file ceiling;
- chunk directories with `.d`;
- country-year shards;
- numbered shards;
- per-document field tables;
- special global buckets;
- pending markers for interrupted layout changes;
- DVC document store;
- SQLite derived validator/build engine.

For tens or hundreds of thousands of rows, this can work, but one researcher may spend a lot of time on file mechanics rather than data quality. SQLite as the source of record with exportable CSV diffs, or a small append-only event log plus generated tables, might be simpler.

If staying with CSV, I recommend:

- raise or justify the 512 KB limit;
- minimize sharding until necessary;
- generate consistent data packages at release time;
- keep manual review focused on decision rows, not bulk comparator rows.

## 4.4 The “agentic development” control plane needs more safety details

The spec assumes coding agents can safely modify the system with tests and LLM reviews. That is plausible, but the operational risks are under-addressed:

- dependency pinning and lockfiles;
- supply-chain security;
- test isolation;
- destructive command protection;
- DVC garbage collection safeguards;
- branch protection rules;
- audit logs;
- local model/server contention;
- reproducible environments over years.

The prohibition list in **Operation §4** is good. It should be complemented by a technical enforcement plan.

## 4.5 Weekly snapshots until 2030 may be unrealistic

**DA11** says about ten times current documents and weekly snapshots of each living document without design change. This is ambitious. Weekly captures can produce:

- many identical or near-identical snapshots;
- repeated locator validation work;
- huge numbers of restatements;
- link-rot and terms-of-use drift;
- matching across versions;
- large DVC storage and backup needs.

The “identical text” rule helps, but M4 should probably adopt adaptive scheduling: high-change pages weekly, stable pages monthly or quarterly, critical pages before release.

---

# 5. Dead angles and failure modes

## 5.1 Legal and terms-of-use exposure is the largest dead angle

The spec discusses robots rules and source terms, but several risks remain.

### Copyright and licensing

As noted above, an open licence cannot automatically cover third-party text, labels, excerpts, tables or screenshots. This is especially important if releases serve verbatim excerpts.

### Database rights

EU/database-right issues may arise for structured portals, CRS/IATI extracts, development-bank APIs, procurement portals and project databases.

### Robots and terms

**Collection §1** says a single fetch of a known document goes ahead even if crawler rules disallow automated access. That may be acceptable technically, but it is legally and ethically delicate. Robots.txt is not the same as terms of use, but the distinction should be reviewed.

### Free-registration sites

The spec treats public free-registration portals as public documents. That is often reasonable, but some portals prohibit automated downloading or redistribution. The spec needs a per-site rights/access assessment.

### Internet Archive captures

Capturing documents into the Internet Archive may itself conflict with source terms or publisher expectations. The spec should state when captures are made and under what basis.

### Personal data

Natural persons are mostly out of scope, but **Extraction §4** allows signatory names, and release validation screens only email addresses and telephone numbers. Names, signatures, job titles and scanned signatures may be personal data. A GDPR/privacy review is needed.

## 5.2 API/vendor exposure is under-specified

Documents are public, but sending them to LLM vendors still has implications:

- vendor retention/training policies;
- cross-border data transfer;
- API terms;
- sensitive political context;
- embargoed release preparation;
- cost shocks and model deprecation.

The spec should record vendor policies and allow per-document “do not send to vendor” flags if source terms require it.

## 5.3 Single points of failure

The design has several:

- one researcher;
- one workstation;
- DVC remote on same NVMe partition as cache, with doudou only as backup;
- local LLM service shared with other projects;
- GitHub repository;
- API providers;
- persistent identifier repository;
- tacit knowledge of domain and judgement history.

The declared 2030 horizon makes this important. At minimum, there should be a quarterly restore test, offsite backup, exported release package, and a “successor maintainer” handover note.

## 5.4 Drift to 2030

Likely drift sources:

- JETP terminology changes;
- publishers redesign portals;
- CRS/IATI schema changes;
- LLM model retirements;
- prices change;
- source terms change;
- web archives disappear or block captures;
- ministries reorganize;
- organisations merge or rename;
- political disputes over figures intensify.

The spec has pieces of a drift plan but not a consolidated one. M4 should include a **drift register**: source availability, schema changes, model changes, method changes, legal changes, ontology changes.

## 5.5 Adversarial and prompt-injection risks are partly handled but not fully

The spec correctly treats documents as untrusted input and disables tools/network for LLM readers. Good.

Remaining risks:

- malicious text can still manipulate extraction if prompt isolation fails;
- HTML hidden text and scripts may contain misleading content;
- PDFs can contain invisible/overlaid text;
- OCR can hallucinate;
- source pages can be personalized by cookies/session;
- browser-saved documents may not be reproducible by others.

The text-layer policy should include adversarial fixtures: invisible text, white-on-white text, conflicting OCR/text layer, script-injected fake data, and PDF annotations.

---

# 6. Priority changes before freezing the specification

## 1. Add a formal provenance and temporal contract

Create one short, authoritative table covering documents, retrievals, snapshots, lines, observations, decisions, results and releases. For each, define:

- identifier;
- source/provenance;
- recorded/transaction time;
- publication/retrieval time where relevant;
- event/valid time where relevant;
- supersession semantics;
- eligibility for knowledge cutoff K;
- correction-overlay eligibility.

Map the release package to RO-Crate/DataCite/Frictionless or explain deviations.

## 2. Define the human validation and quality plan

Before relying on LLM agreement, specify:

- second human reader role, if any;
- stratified sample design;
- sample sizes;
- release-blocking thresholds;
- serious-error taxonomy;
- extraction, observation, matching and account accuracy metrics;
- calibration checks for LLM likelihood/confidence;
- high-impact figure review rules.

This is the biggest gap between “traceable” and “trustworthy.”

## 3. Resolve target-schema dependencies before milestone acceptance

No M2/M3 requirement should depend on a target column or table. Either:

- implement the target schema now; or
- move the dependent requirement to a later milestone; or
- define a temporary conforming representation.

In particular, fix `recorded_at`, decision-row shape, triage/candidate tables, correction overlays, and in-force views.

## 4. Add a legal/licensing/privacy policy

Separate rights for:

- Observer-created data;
- third-party verbatim text;
- source bytes;
- screenshots/scans;
- API records;
- personal data;
- public-archive captures.

Revise **F30**, **Results §7**, and release metadata so the Observer does not open-license material it does not own.

## 5. Replace ad hoc entity-resolution confidence with a measured ER protocol

Keep the judgement-based design, but add:

- labelled benchmark sets by country and entity type;
- blocking recall targets;
- pairwise and cluster metrics;
- active-learning/clerical-review workflow;
- constraints for external identifiers;
- explicit handling of mergers, subsidiaries, translations and acronyms;
- review budget estimates.

---

# 7. Things that are excellent and should be kept

1. **Append-only documentary record**: never overwriting statements, judgements or releases is exactly right.
2. **Snapshot-hash-plus-locator provenance**: this is the backbone of trust.
3. **Distinction between publisher statements and Observer calculations**: essential for neutrality.
4. **Frozen citable releases with correction releases**: strong reproducibility design.
5. **Unreachable/not-published/blocked as data**: very valuable for disclosure politics.
6. **Explicit uncertainty and unresolved disagreement**: better than false precision.
7. **Cost and human-time accounting**: unusually pragmatic and important.
8. **No automatic publication**: appropriate for a politically sensitive dataset.
9. **Recognition that structured channels are late and non-authoritative**: methodologically sound.
10. **Static Observatory tied to one release**: good for durability and citation.

---

# 8. Overall verdict

**Major revision.**

The design is conceptually strong and worth pursuing, but the specification is not ready to be frozen as the implementation contract. The main blockers are the incomplete temporal/provenance model, missing human validation design, unresolved target-schema dependencies, legal/licensing ambiguity, and likely review-load explosion.

---

# 9. Five most important changes, in priority order

1. **Write and enforce a single temporal/provenance contract** for all row types, decisions, corrections and releases.
2. **Add a statistical human-validation plan** with second-reader roles, sample sizes, error metrics, calibration checks and release gates.
3. **Make the storage schema actually support the M2/M3 promises** or move those promises to later milestones.
4. **Add a legal/licensing/privacy policy** and revise the open-licence claim for third-party excerpts and source-derived text.
5. **Redesign entity resolution around measured blocking, clustering and clerical review**, not only pairwise LLM judgements and depth-one equality.

---

# 10. Questions I would ask the author

1. What exactly is the role of the “second reader” mentioned in the project description, and why is it not specified as a first-class actor in Extraction, Fusion and Operation?

2. For each M2 and M3b requirement, can you mark whether the current DDL already supports it, or whether it depends on a “target schema” change?

3. What is the minimum human-reviewed gold set needed before the first citable release, stratified by language, country, document type and extraction method?

4. Which release figures are high-impact enough to require 100% human trace review before publication?

5. Can a correction overlay include a newly extracted line from a pre-K snapshot, or only supersession rows correcting rows already present at K?

6. How will you open-license the release while including third-party labels, excerpts and table text?

7. What happens if a source site allows public reading but forbids automated extraction or republication of extracted database contents?

8. Why should “about as likely as not, any confidence” be an inclusive public threshold rather than a diagnostic sensitivity scenario?

9. How will LLM likelihood and confidence be calibrated against human decisions, rather than accepted as model self-report?

10. What is the expected number of candidate matches for projects, agreements and parties after CRS/IATI/World Bank import, and how many can the author realistically review?

11. Is the one-researcher “blind” known-item recall test meaningful, or should an external colleague compile or hold the known-item list?

12. Should publisher attribution be explicit at line/observation level, especially for joint publications and quoted speakers?

13. What is the recovery plan if padme fails while doudou’s backup is stale or incomplete?

14. Which API/vendor terms allow document text to be sent to LLMs, retained in logs, or used for abuse monitoring?

15. Could the public “Statements” page be renamed to avoid conflict with the builder meaning of statement as D2 line?

---

# 11. One experiment I would run next

Run an end-to-end **pilot release for one country and 20–30 documents** — including extraction, observation reading, entity matching, one account, one timeline, release packaging, rights classification and human validation. Measure: LLM cost, author minutes, extraction error rate, observation error rate, match precision/recall, unresolved disagreements, legal redistribution categories, and whether an independent reviewer can reproduce one figure from the release package.
