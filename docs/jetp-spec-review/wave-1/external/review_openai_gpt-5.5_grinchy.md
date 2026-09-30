# Peer review — openai/gpt-5.5, persona: grinchy

## Review of JETP Observer system specification v0.1

### Overall assessment

**Verdict: not ready.**  
This is an unusually detailed specification, but it is not yet a dependable architecture for a trustworthy, citable documentary dataset. It mixes conceptual rules, implementation details, future targets, current ledger facts, and aspirational quality controls in a way that makes it hard to know what must actually be true at M2/M3b. The strongest parts are the insistence on frozen releases, locators, append-only evidence, and explicit uncertainty. The weakest parts are the LLM judgement methodology, the provenance/time model, legal exposure, and the sheer operational burden on one researcher.

The document repeatedly claims reproducibility, neutrality, bounded human attention, and citable reliability before it has specified the mechanisms that would make those claims credible. “Two LLMs from different vendors plus a sampled human review” is not a validation method unless the sampling design, error tolerances, calibration procedure, and escalation rules are nailed down. They are not.

Below are the major objections, prioritized.

---

## Major objections and required fixes

### 1. The milestone boundary is not clean enough to implement or audit  
**Refs:** Requirements §§2.2, 4–7; Extraction §13; Results §13; Operation §12; Storage §1 “target schema”.

The spec says each milestone delivers an end-to-end correct slice, but many M2/M3 requirements depend on “target” schema changes, open decisions, or later operational features. Examples:

- Storage §1 says the DDL “does not yet carry” columns required by Fusion and as-of reasoning, including `recorded_at`, `stance`, `likelihood`, `basis`, and proper judgement structures.
- Extraction §14 leaves the random sample size unresolved, yet Q5 and C1 rely on bounded human review.
- Operation §7 says budget amounts are “proposed defaults awaiting the author's decision,” but C4 treats budgets as binding controls.
- Results §13 says the first citable release needs full trails, thresholds, correction logic, provenance and release metadata, but several of the underlying tables are still target schema.

**Why this matters:** A reviewer, implementer, or future user cannot tell whether M2/M3b are achievable states or merely design aspirations.

**Fix:** Produce a milestone conformance matrix with three columns: **implemented now**, **required before milestone acceptance**, **explicitly deferred**. Remove “target schema” dependencies from any milestone that claims to be testable. For each M2/M3b requirement, identify the exact table/column/test that proves it.

---

### 2. “No automatic judgement” is contradicted by automated LLM acceptance and deterministic rules  
**Refs:** Requirements F7, Q5, N4; Collection §§1, 9; Fusion §§1, 3; Operation §5.

The spec repeatedly says no crawler, program, or rule admits a document, merges identities, prefers a value, or publishes a release “on its own.” But Collection §9 says two LLM readers agreeing puts a triage outcome “in force” unless the author samples it and overturns it. Fusion §3 allows programs to record accepted judgements under adopted rules. Operation §5 generalizes one-reader/one-checker judgement to statements, dispositions, triage and matches.

This may be defensible, but the language is currently muddled. A “recorded decision” can apparently mean:

1. a human decision,
2. an LLM panel decision,
3. a deterministic rule adopted earlier by the author,
4. a script-applied rule,
5. a candidate proposal not yet accepted.

Those are materially different authority levels.

**Fix:** Define a formal decision state machine:

- candidate/proposed,
- machine-accepted under adopted deterministic rule,
- LLM-panel-accepted,
- human-accepted,
- rejected,
- superseded,
- revoked.

Then specify which state is sufficient for each downstream use: extraction, release, public display, reference-answer status, financial aggregation, and correction. Stop using “decision” as if all decision types carry equal epistemic weight.

---

### 3. The provenance model reinvents established practice and is still incomplete  
**Refs:** Language ODEM; Ontology §§0, 5; Storage §§1, 3; Results §§2, 4–5; Presentation “Traceability”.

The system needs serious provenance, but it only gestures toward PROV-O as a later RDF projection. Provenance is central here, not an optional export. The spec invents its own mixture of `recorded_at`, `decided_at`, retrieval dates, publication dates, knowledge cutoffs, correction overlays, and method versions. This is fragile.

Specific gaps:

- No clear separation between **source publication time**, **retrieval time**, **snapshot capture time**, **extraction time**, **admission/decision time**, **release build time**, and **world/event time**.
- At M2, “document admitted” is proxied by earliest successful retrieval; at M3a it becomes a defeasible triage decision. That changes semantics mid-system.
- “World time” in Results §2 is not a full valid-time model; it is sometimes event time, sometimes reporting cutoff, sometimes position date, sometimes interval.
- Correction overlays are underspecified relative to bitemporal replay. They risk becoming an ad hoc patch system.

**Fix:** Adopt a standard provenance/time backbone before M3b:

- Use **W3C PROV** concepts internally: Entity, Activity, Agent, wasGeneratedBy, used, wasAttributedTo, wasDerivedFrom.
- Use explicit bitemporal fields: source-valid/event interval, source-publication date, retrieval/capture time, ledger-recorded time, decision-adopted time, release-cutoff time.
- Package releases with **RO-Crate** or **Frictionless Data Package** plus DataCite metadata.
- Treat PROV not as a later RDF export but as the conceptual model behind tables and validation.

---

### 4. The document/bibliographic model is not strong enough for editions, translations, mirrors, living pages and public access  
**Refs:** Ontology §2 Document/Retrieval/Snapshot; Collection §§2, 8, 10–11; Extraction §§2, 8; Results §7.

The current document model uses “document,” “edition,” “translation,” “snapshot,” “retrieval,” and “same_as” but does not cleanly distinguish bibliographic work/expression/manifestation/item levels. This creates ambiguity:

- Is a revised PDF a new document, a new edition, or a new snapshot?
- Is an abridged translation a translation, an edition, or a different document?
- Is a web archive capture a hosted mirror, a retrieval, or a separate document?
- If a multi-publisher document has line-level claims, who is the publisher of each line? F1 requires each statement to name its publisher, but the `lines` table does not appear to carry a publisher; it relies on document-level publishers.

Also, Collection §10 says relocation is a new address of the same document, but Storage §1 only has `document-addresses` as a target M4 table. That is too late for a system explicitly concerned with link rot.

**Fix:** Use a bibliographic pattern explicitly. FRBR/LRM terminology may be too heavy, but the distinctions are necessary:

- intellectual work,
- language expression,
- issued manifestation/edition,
- captured file/snapshot,
- retrieval event,
- web archive capture.

Add line-level publisher attribution rules for jointly published documents. Implement address history before the first citable release, not at M4.

---

### 5. The LLM-as-judge validation plan is methodologically inadequate  
**Refs:** Requirements Q5, Q17; Extraction §§6.3, 12, 14; Collection §9; Fusion §3; Operation §5.

The spec leans heavily on LLMs but does not define a credible statistical quality-control regime. “One reader and one checker from another vendor” is not enough. Vendor diversity does not guarantee independence; models share training data, benchmark contamination, common failure modes, and similar instruction-following weaknesses. Agreement between two LLMs is not an error bound.

Major missing pieces:

- No required human audit sample size.
- No acceptance criteria for precision/recall of extraction.
- No stratification by country, language, document type, extraction method, financial state, or source difficulty.
- No estimate of missed statements except a checker’s LLM-generated missed-item list.
- No inter-rater reliability or adjudication protocol.
- No calibration of likelihood/confidence labels.
- No red-team set for prompt injection beyond a planted instruction fixture.
- No policy for model version drift when vendors silently change models.

The open question in Extraction §14 about the random sample size is not minor. It is foundational.

**Fix:** Define an acceptance-sampling plan:

- Stratify by language, document type, extraction method, and source authority.
- Set minimum human review rates and hard floors per stratum.
- Report estimated false positive and false negative rates with confidence intervals.
- Maintain a gold/benchmark set, frozen per release.
- Require reliability checks for LLM likelihood/confidence labels.
- Define release-blocking thresholds, e.g. no critical financial extraction stratum released unless estimated serious-error rate is below a stated bound.

---

### 6. The human review and cost model is not credible for the proposed scope  
**Refs:** Requirements C1, Q5, Q15; Operation §§7–8; Extraction §§6.3, 11; Fusion §3.

The spec claims the author’s attention is bounded, but the workload drivers are enormous:

- 115 held but unextracted documents at M2.
- M3a discovery across four countries, multiple languages, multiple authority classes, secondary trackers and known-item recall.
- M3b extraction of new documents, CRS/IATI matching, identity resolution, preference judgements, accounts, release trails.
- Every LLM judgement checked by a second vendor.
- Author reviews disagreements, missed items and a random sample.
- Release must trace every number, status, and substantive narrative claim.

The proposed budget of “100 items presented” per run and “3 hours per week” is not connected to an estimated number of candidate statements, candidate matches, disagreements, or release-blocking judgements. The LLM dollar cost may be modest; the clerical review cost will not be.

**Fix:** Add a workload model before implementation:

- Expected number of statements per document class.
- Expected candidate matches per statement/referent.
- Expected disagreement rates from pilot data.
- Expected human minutes by task type.
- Worst-case bounds.
- Explicit scope cuts if the review queue exceeds capacity.

Do not claim C1 is satisfied until those estimates exist and are validated on a pilot.

---

### 7. Discovery and recall estimation are too weak for the claims made  
**Refs:** Collection §§3–7, 12; Requirements DA7–DA10, Q10.

The discovery protocol is thoughtful but still not strong enough to support “what exists” or even reliable coverage claims.

Problems:

- The known-item list is built by “the author or people who know the field.” With one researcher, blinding is hard to believe operationally.
- Minimum 40 known items across four countries gives very wide intervals. The example 36/40 = 90% has a Wilson interval of roughly 77–96%; that is not a strong stopping basis.
- Known-item recall over-captures visible/cited items, and the spec admits this. The alternative estimate is deferred.
- The “quiet tail” stopping rule depends on search order and may miss entire source classes if queries are weak.
- “Not published” is a strong terminal verdict, but the evidence standard varies by authority, language and site search quality.
- Secondary-to-primary traceability depends on a declared tracker list; omissions from that tracker list can materially bias coverage.

**Fix:** Downgrade the claim from recall to “known-item recovery and search-yield exhaustion,” unless a stronger method is implemented. Require independent construction of the known-item list, per-country reporting, sensitivity to search order, and a minimum search-log schema sufficient for external audit. Consider capture-recapture or dual independent search teams if recall is to be claimed quantitatively.

---

### 8. Entity resolution design is under-specified and contains a dubious anti-transitivity rule  
**Refs:** Fusion §3; Storage §4; Requirements F11, F12, F20.

The spec says equality between referents is bounded to depth one: if A same_as B and B same_as C, the system raises a conflict and requires A vs C review. That is operationally cautious, but it is not a coherent identity model. Equality is transitive. If you do not trust transitivity, you are not storing equality; you are storing pairwise “may refer to same thing” evidence.

Threshold-dependent referents also create problems:

- A project can exist as one entity at the inclusive threshold and two entities at the cautious threshold.
- Counts of referents will change direction depending on clustering choices.
- Revoking one match can split clusters; the spec does not describe cluster versioning.
- Pairwise precision/recall and “one cluster metric” are named but not defined.
- Blocking recall is promised but no gold-standard set size or sampling procedure is specified.

**Fix:** Recast identity as entity-resolution evidence plus thresholded clustering:

- Store pairwise match judgements, not threshold-dependent “truth.”
- Define clustering algorithm, constraints, split/merge behavior, and cluster versioning.
- Use established ER tools or patterns: Fellegi–Sunter/probabilistic linkage, Dedupe/Splink-style blocking and scoring, clerical review queues, pairwise constraints.
- Publish ER evaluation metrics on a frozen labelled set: pairwise precision/recall, B-cubed or CEAF, cluster split/merge counts.

---

### 9. The ontology borrows from standards but does not sufficiently align with them  
**Refs:** Ontology §§1–5; Storage §3; Requirements F31.

The spec says it avoids theoretical purity, but it repeatedly reinvents standard constructs: provenance, bibliographic metadata, status vocabularies, organizations, identifiers, code lists, data package metadata, and observation modeling.

Examples:

- PROV-O is deferred as an export, even though provenance is core.
- SKOS is used for mapping relations but not systematically embedded in the data model.
- DataCite metadata is implied but not fully specified.
- DCAT, schema.org Dataset, Dublin Core, RO-Crate, Frictionless Data Package are not seriously considered.
- ROR, GLEIF/LEI, IATI organization identifiers and Wikidata are listed, but authority-control precedence and conflict resolution are not specified.
- OC4IDS, GEM, IATI and CRS are used selectively; the exact semantics of status mapping are risky.
- LinkML is dismissed because outputs have “no consumer,” but the project itself needs schema validation, documentation, and JSON/CSV contracts. That is already a consumer.

**Fix:** Add a standards-conformance section:

- For each concept, state whether the system **adopts**, **maps to**, or **intentionally diverges from** a standard.
- Use DataCite + DCAT/schema.org for release metadata.
- Use PROV internally.
- Use SKOS for controlled vocabularies and crosswalks.
- Use Frictionless/RO-Crate for package structure.
- Use ISO 3166, ISO 4217, IATI codelists, OECD CRS purpose codes, ROR/LEI/IATI org IDs with explicit precedence rules.

---

### 10. Financial semantics are not yet robust enough for promised use cases  
**Refs:** Ontology Agreement/Observation; Fusion §§5–7; Requirements F14–F19.

The spec is right that announced, signed, disbursed, reported, and expended should not be added. But the financial model remains underdeveloped for negotiators, journalists and researchers.

Concerns:

- “Agreement” is both a funder-side money object and sometimes the lender’s “operation.” This risks conflating legal agreement, project operation, financing package, tranche, activity, and transaction.
- IATI transaction types are invoked, but “pledge” is not cleanly an IATI transaction type in the same sense as commitment/disbursement/expenditure.
- “Reported” is defined as CRS/IATI comparator-reported amount, but those systems report different concepts by donor and year.
- Gross/net basis is included, but cancellation, repayment, refinancing, guarantee exposure, mobilized private finance, and co-financing are not sufficiently modeled.
- Grant element and concessionality are mentioned but not operationalized.
- Currency conversion only when a document prints a rate is conservative, but it will severely limit comparability; the spec should state that cross-currency totals may often be impossible.

**Fix:** Add a finance data model appendix:

- Distinguish envelope, estimate, legal commitment, activity/operation, transaction, disbursement, expenditure, cancellation, repayment, guarantee exposure, mobilized finance.
- Map each to IATI/CRS concepts where possible.
- Define what is excluded from each aggregate.
- Add examples for all four countries.
- Require financial aggregation tests on realistic messy cases, not just toy checks.

---

### 11. Storage contract is brittle and internally inconsistent  
**Refs:** Storage §1; Ontology §5; Extraction §§3, 5; Presentation Traceability.

The CSV-in-git design is defensible for reviewable small data, but the current contract is a tangle of committed CSVs, per-document field files, shard directories, DVC artifacts, generated SQLite, target columns, and derived-but-retained layers. Several contradictions or hazards appear:

- “No column holds a semicolon-separated list,” but the storage table includes `projects.aliases`.
- Lines are defined as “one publisher’s assertion,” but `lines` does not have a publisher field; multi-publisher documents are not resolved.
- `groups` is a single foreign key, but a line can be governed by multiple headings, footnotes, method notes, issue dates and scope notes.
- Required schema changes are deferred as “targets,” while requirements already depend on them.
- Per-document field tables make validation and downstream use difficult.
- CSV gives weak type guarantees; the actual validator is SQLite, but SQLite is not the record.
- Sharding by country/year for rows whose country is inferred from a cited line is fragile.
- GLB as a pseudo-country conflicts with the stated external-code discipline unless tightly constrained.

**Fix:** Freeze a simpler canonical schema before M2 acceptance. Either:

1. keep CSV as source but generate it from a typed schema with strict validation, or  
2. use SQLite/DuckDB/Parquet as canonical data artifacts with human-readable review reports.

Do not proceed with a citable release while required columns remain “target schema.”

---

### 12. Release reproducibility is overclaimed when source bytes cannot be redistributed  
**Refs:** Requirements Q8, F27–F32; Results §§4, 7; Operation §9.

The spec says releases are frozen and reproducible, but many source documents will not be redistributed. The release may contain only URL, hash and locator. If the publisher removes or changes the document and there is no public archive capture, a third party cannot reproduce the extraction.

Results §7 admits this: “A document with no public copy cannot be checked by a third party.” That undermines the stronger reproducibility language elsewhere.

**Fix:** Use more careful claims:

- “Internally reproducible from archived bytes held by the project.”
- “Externally inspectable where redistributed bytes or public archive captures exist.”
- “Externally non-reproducible for documents without public copies.”

Before M3b, require archive captures wherever legally and technically possible. Report the share of released statements/results backed by third-party-accessible bytes.

---

### 13. Legal, licensing, ToS and privacy risks are under-addressed  
**Refs:** Requirements F27, C6, C9, N13; Collection §§1, 8; Results §7; Extraction §3; Operation §6.

The legal model is too casual for a public dataset built from government, bank, portal and news documents.

Specific risks:

- Robots.txt and terms of use are not legal shields. Collection §1 says single known-document fetches proceed even if crawler rules disallow automated access. That may be acceptable in some contexts, but it needs legal review, not just logging.
- Free-registration portals can still have terms prohibiting redistribution, automated access, scraping, or uploading to third-party LLM vendors.
- Sending document text to LLM vendors may violate source terms or data-protection expectations, even for public documents.
- The release will redistribute verbatim labels and short excerpts. Copyright/database-right issues are not analyzed.
- Natural persons are out of scope, but Extraction §4 allows recording a person’s name as signatory in some cases. GDPR/privacy treatment is minimal.
- Takedown/withdrawal is specified technically, but not legally: who decides, what standard, what notice process?

**Fix:** Add a legal risk register and source-access policy:

- For each source class: access permission, redistribution permission, LLM-upload permission, archive permission.
- Excerpt policy: maximum length, purpose, attribution, legal basis.
- Personal-data policy: minimization, lawful basis, retention, takedown.
- Vendor data-processing policy: retention/training opt-outs, region, logging.
- Takedown and correction procedure with roles and response times.

---

### 14. Operational resilience is inadequate for a 2030 horizon  
**Refs:** Requirements C1–C4, C10; Operation §§2–3, 9–11.

The spec is candid that this is one researcher on a personal workstation. But the promised dataset horizon through 2030 is incompatible with the current resilience plan.

Problems:

- DVC remote and cache are on the same NVMe partition.
- Backup to the laptop is proposed, but the laptop is also described as not needing to hold document bytes. That distinction is technically possible but operationally fragile.
- No offsite/institutional backup is required at M2.
- No succession plan if the author is unavailable.
- No escrow for credentials, release deposits, domain names, or GitHub/Zotero/Zenodo access.
- No policy for vendor model retirement, API price shocks, or source-site access changes over years.
- Local machine-specific details such as `~/.local/bin/uv`, `ssh padme`, and a named llama service are too brittle for a long-lived operational specification.

**Fix:** Add a sustainability/runbook layer:

- Offsite object storage or institutional storage for DVC artifacts.
- Periodic restore tests from clean machines.
- Credential escrow or institutional ownership where possible.
- Bus-factor plan.
- Model/vendor deprecation policy.
- Minimal reproducible environment definition.
- Separate durable operational policy from machine-specific notes.

---

### 15. Neutrality is asserted more than engineered  
**Refs:** Requirements §1 “neutral documentary record”, Q13, Q16; Fusion §§5–7; Presentation markers.

The Observer says it does not grade partners or judge whether promises were kept. But its headline use cases are explicitly about gaps between pledged, announced, signed, reported and disbursed amounts. Those gaps will be read politically. Neutrality cannot be achieved merely by avoiding evaluative adjectives.

Risks:

- Choosing strict vs extended JETP scope is interpretive.
- Choosing which documents are “closest to event” is interpretive.
- Choosing whether a secondary harmonization is preferable is interpretive.
- Labelling something “late report,” “publisher correction,” or “ledger error” is interpretive.
- Showing “gaps” without carefully designed language may imply underperformance.

**Fix:** Add an editorial neutrality policy:

- Standard wording for gaps, non-publication, blocked access, and missing values.
- Explicit separation of documentary state from performance evaluation.
- Review checklist for evaluative language.
- Examples of prohibited and allowed language.
- Public explanation of scope decisions and their consequences.

---

### 16. Several requirements are not actually testable  
**Refs:** Requirements §§2.1, 6; Presentation; Operation.

The document says every requirement has a reviewer-decidable test. Many do not.

Examples:

- F26: “definitions a general reader follows” — no test population or readability criterion.
- Q13: “no causal or speed claim unsupported” — subjective unless a claim taxonomy exists.
- Q18: “every behaviour” governed by a written rule and test — impossible at that breadth.
- Q21: every decision reachable from what it governs — not operationalized.
- C8: every section serving no requirement moves to M4 — difficult because many sections serve broad principles.
- “Neutral wording” tests rely on reviewer judgement but do not specify criteria.

**Fix:** Convert soft tests into concrete acceptance checks:

- Use finite checklists and sampled audits.
- Define “substantive narrative claim.”
- Define what counts as a behavior needing a test.
- Use traceability IDs from requirement → rule → code/test → release artifact.
- Move aspirational principles out of release-blocking requirements unless they have measurable tests.

---

### 17. Presentation traceability for every narrative claim is overbuilt and likely to fail  
**Refs:** Presentation “Traceability to what is published”; Results §8; Requirements Q6–Q7.

The spec requires every published number, status and substantive narrative claim on the Observatory and in papers to resolve to observations/calculations, with stable block identifiers and claim registries. This is admirable but probably too heavy for one person, especially once papers and a book are included.

The danger is that this becomes performative bureaucracy: either the author will not maintain it, or the traceability will be shallow and stale.

**Fix:** Stage this:

- M3b: require full traceability for tables, figures and headline metrics in the Observatory.
- Later: require claim registries for papers that cite release results.
- Do not require every narrative sentence in external manuscripts until tooling proves it is cheap.

---

### 18. The “state of the art” discussion is shallow where it matters  
**Refs:** Requirements FAIR paragraph; Ontology “Why a new schema”; Storage §3; Fusion §1.

The spec cites FAIR, IPCC uncertainty, NUSAP, SKOS, PROV-O, ROR/GLEIF and related vocabularies, but mostly as vocabulary references. It does not yet exploit the practices that would make the dataset robust:

- FAIR: release metadata is mentioned, but no explicit FAIR self-assessment, access protocol, persistent identifier strategy, or interoperability profile.
- Provenance: PROV is deferred.
- Bibliographic modeling: no FRBR/LRM/Memento/WARC discussion.
- Entity resolution: no established ER pipeline, active learning, clerical review metrics, or cluster evaluation.
- Uncertainty: IPCC labels are used without empirical calibration.
- LLM evaluation: no acceptance sampling or benchmark methodology.
- Data packaging: no RO-Crate/Frictionless/DCAT commitment.
- Bitemporal data: home-grown as-of logic, not a clean temporal model.

**Fix:** Add a short “standards and design choices” chapter. For each major data-management concern, say: adopted standard, local adaptation, intentional divergence, and reason.

---

## Fitness for purpose

For think tanks and journalists, the Observer could be valuable if it reliably answers “where did this number come from?” It is not yet safe for “what was promised, signed and paid?” because extraction error, identity uncertainty and financial-state semantics remain too weak.

For researchers, frozen releases and append-only rows are promising, but reproducibility claims must be qualified when source bytes cannot be redistributed. The dataset will be citable only if releases are packaged and documented using ordinary repository standards, not only custom descriptors.

For negotiators, the current design may be too complicated and too uncertain unless the public presentation makes clear what is documentary, what is computed, what is unresolved, and what cannot be compared.

For AEDIST/LLM research, the dataset will only be useful as a benchmark if the human-decided subset is sampled and adjudicated rigorously. “Rows the author happened to check” is not a benchmark.

---

## Dead angles

1. **LLM vendor data handling:** source documents uploaded to vendors may be logged, retained or used in ways incompatible with source terms.  
2. **Copyright/database rights:** verbatim extracted labels, table rows and structured records may not be freely licensable by the Observer.  
3. **Free-registration portals:** “public” does not mean scrapeable, redistributable, or uploadable to third-party APIs.  
4. **Political/source drift:** portals may disappear, change history, restrict access, or alter old pages.  
5. **Single-person failure:** the whole record depends on one person’s judgement, credentials, machine, and attention.  
6. **Model drift:** LLM readers/checkers will change behavior over time; recorded outputs help, but future consistency and benchmark comparability remain exposed.  
7. **Error propagation through identity matching:** one false merge can affect many totals and timelines.  
8. **False sense of precision:** likelihood/confidence labels and two-threshold ranges may look more rigorous than they are.

---

## Overall verdict

**Not ready.**  
The specification is directionally strong but not yet release-grade. It should not be used to justify a citable dataset until the decision model, provenance model, LLM validation plan, legal policy, and implementable M2/M3b schema are tightened.

---

## Five most important changes, in priority order

1. **Define the decision and validation regime.**  
   Formalize judgement states, LLM acceptance rules, human audit sampling, error-rate reporting, and release-blocking thresholds.

2. **Replace the ad hoc provenance/time model with a standard one.**  
   Adopt PROV-style entities/activities/agents and explicit bitemporal fields before M3b.

3. **Freeze an implementable canonical schema.**  
   Remove “target schema” dependencies from M2/M3b. Resolve publisher attribution, group relations, judgement rows, and no-list contradictions.

4. **Add a legal and access policy.**  
   Cover ToS, robots, free-login portals, LLM uploads, copyright/database rights, personal data, redistribution, excerpts, archiving and takedown.

5. **Produce a workload/cost/review feasibility model.**  
   Estimate expected documents, statements, candidate matches, disagreements, human minutes, LLM costs and scope cuts. Do not rely on vague “bounded attention.”

---

## What is excellent and should be kept

- The insistence on **frozen, citable releases** rather than a mutable dashboard.
- The separation between **publisher statements** and **Observer calculations**.
- The append-only treatment of statements, snapshots, judgements and corrections.
- The explicit distinction between **unknown**, **zero**, **blocked**, **not published**, and **not sought**.
- The recognition that CRS/IATI are comparator channels, not authoritative overrides.
- The plan to keep machine readings and human decisions side by side.
- The effort to make uncertainty visible rather than silently resolving it away.

---

## The three things that most threaten the central claim

1. **The LLM/human review design does not yet establish trustworthy extraction and judgement error bounds.**  
   Without a rigorous audit and sampling plan, the dataset may be traceable but still wrong.

2. **The provenance, bitemporal and document models are not yet strong enough to support reproducible citable releases.**  
   The system needs standard provenance and cleaner document/version semantics before release claims are credible.

3. **The one-person operational and legal risk profile is too fragile for a public dataset maintained to 2030.**  
   Source access, ToS, backups, credentials, model drift and author availability are all single points of failure.
