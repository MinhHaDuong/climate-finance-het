# Peer review — z-ai/glm-5.3, persona: grinchy

## Review of JETP Observer System Specification v0.2

---

### Overall Assessment

This is an ambitious, intellectually serious specification for a documentary dataset that has no real precedent in the JETP monitoring space. The author has clearly thought deeply about provenance, uncertainty, and neutrality. The append-only model, the bitemporal discipline, and the refusal to manufacture preferred figures are genuine contributions to the practice of document-based climate-finance tracking.

However, the specification suffers from three systemic problems: (1) it has removed human judgment from quality assurance at precisely the point where the dataset's credibility depends on it; (2) it has built a conceptual apparatus so elaborate that its own maintenance will consume the one researcher it is designed for; and (3) it defers legal decisions that must be resolved before the system architecture is finalized, not after. These are not polish items—they threaten the dataset's fitness for its stated users.

---

### 1. Internal Coherence

**1.1 The reconciliation table in DA2 does not add up.** "91: 81 CRS extracts and 6 World Bank and ledger export" is 87, not 91. Either the text is wrong or the table is. A dataset specification whose own holdings table fails its own reconciliation test is a poor omen. (Requirements §5, DA2.)

*Fix:* Correct the table and add a checksum test that validates the reconciliation automatically.

**1.2 The "terms retired" list in the Language document is violated throughout.** "Source" is retired in favour of "publisher," but the legal note, collection document, and results document use "source" freely (e.g., "source's terms," "source's position," "public-sector information" uses "source" in its legal sense). "Reconciliation" is retired in favour of "matching," yet DA2's table is titled "The counts reconcile as follows." "Evidence" is retired for documentary support, yet the ODEM frame uses "Evidence" as a technical term. The language document says it "governs the design documents and the schema"—but it does not. (Language, "Terms retired or restricted.")

*Fix:* Either enforce the term list rigorously or acknowledge that the retired terms survive in legal and operational contexts and narrow the scope of the language document's authority.

**1.3 The milestone-tagging system creates circular dependencies.** Section 2.2 states: "A requirement is not met at a milestone while a table or column its rules need is still a target of the storage contract." The target schema in Storage §1 lists roughly 25 unimplemented changes, many needed by M2 rules (e.g., `line-referents` gains `stance, likelihood and basis`; `adjudications` gains `method, method_version, stance, likelihood`). By the specification's own logic, no M2 requirement that depends on these columns is met. Yet the spec claims M2 delivers "an extraction pipeline that works on every document held." This is a formal contradiction. (Requirements §2.2; Storage §1.)

*Fix:* Declare which target columns are prerequisites for which milestones and be honest about what "met" means while targets are pending.

**1.4 Q16 and Q13 are not testable in the form stated.** Q16's test reads: "no rule in any specification document makes the Observer assert a finding outside these three kinds"—this is a review of the specification text, not of the running system. Q13's test says "the integration review finds no causal or speed claim"—what integration review? Who runs it? When? These are not tests; they are aspirations. (Requirements §6.2–6.3.)

*Fix:* Define the review as a concrete procedure with a named actor, a trigger, and a pass/fail criterion, or reclassify these as principles.

**1.5 The "two match thresholds" default is internally inconsistent.** Results §3 says the cautious threshold is "likely or more, medium confidence or more" and the inclusive is "about as likely as not or more, low confidence or more." But Fusion §3 says "The default inclusive threshold requires low confidence or more, so a judgement made on no evidence never counts." If the inclusive threshold includes "about as likely as not" likelihood, which is 33–66%, then a judgment at 40% likelihood with low confidence counts at the inclusive threshold—yet the stated intent is to exclude judgments made on no evidence. The tension between "include weak evidence" and "exclude no evidence" is not resolved by the conjunction of likelihood and confidence. (Results §3; Fusion §3.)

*Fix:* Define what "no evidence" means operationally (e.g., a confidence floor that is distinct from the likelihood floor) and state why the current conjunction achieves it.

**1.6 "Operation" is overloaded.** The Language document notes that "operation" means both a funder's lending unit (the domain sense) and running the Observer (the systems sense). The disambiguation is stated but the collision is not resolved—it pervades the Operation document, where "operation histories" (SP-3) could be misread by someone encountering the term in context. This is a minor annoyance that a simple renaming would eliminate. (Language; Ontology §2; Operation §passim.)

*Fix:* Rename the systems sense to "running" or "operations and maintenance" throughout the Operation document, or rename the domain sense to "financing operation" in the ontology.

**1.7 Undefined terms and references.** "M1b catalogue" is cited as the source of calibration reference answers for matching (Fusion §3) but is never defined in this specification—it appears to be an internal artifact from a previous iteration. "B-cubed precision and recall" is used without definition (Fusion §3). "NUSAP" is cited in Fusion §1 without explanation. "AEDIST" and "AIRLET" are introduced as the same thing in different places (§3.7, and §1 mentions "AEDIST (also referred to as AIRLET)") but the relationship is never clarified for a reader who does not know the author's other projects. (Multiple documents.)

*Fix:* Add a brief glossary of external references and internal artifacts, or remove references to items not defined within the specification set.

---

### 2. Fitness for Purpose

**2.1 The most serious issue: human quality assurance has been designed out of the system.** The specification states (Q5): "No person reviews high-impact items one by one: the held-out reference answers are the only human check." This is the central trust problem. For a dataset that think tanks, journalists, and negotiators will cite, the quality of individual high-impact figures (country totals, key disbursement amounts) cannot rest solely on calibration against held-out answers. Calibration measures aggregate performance; it does not guarantee that any specific released figure is correct. If a journalist cites a country total that turns out to be wrong because both LLM readers agreed on a misreading, the dataset's credibility is destroyed, and "the agree-but-wrong rate was published" is not a defence.

The author's constraint C1 ("one researcher's attention") is real, but the response—eliminating all item-level human review—throws out the baby with the bathwater. A tiered review (100% of figures above a materiality threshold, 10% random sample of the rest) would add perhaps 2–4 hours per release cycle and would transform the dataset's trustworthiness. (Q5; C1; Extraction §6.3.)

*Fix:* Reinstate a bounded, prioritized human review pass for released results: all figures above a declared materiality threshold, plus a random sample of statements by country and method, with the sample size and seed recorded.

**2.2 The recall methodology is too weak to support the coverage claims.** The known-item list of 40 items, drawn from "reference lists of academic and grey literature" and "documents named by the author or by people who know the field," is a biased sample of highly visible documents. The spec acknowledges this ("known items are more visible than the average document... so known-item recall tends to overstate recall") but the stopping rule uses the point estimate (90%), not the lower bound. For a dataset whose value proposition is comprehensiveness—"what was sought and not found"—this is inadequate. The spec mentions capture-recapture as "later work" but this is exactly the kind of thing that should be in the first release to support the coverage claims. (Collection §5–6; Q10.)

*Fix:* Implement a simple capture-recapture estimate using two independent search channel classes at M3a, or lower the recall threshold to the Wilson lower bound, and prominently label the recall estimate as "known-item recovery, an upper bound on recall" in every release.

**2.3 The Observatory is over-built for M3b and under-built for researchers.** The presentation specification devotes enormous detail to navigation patterns (dropdowns, sub-bars, breadcrumbs, country chips, aria attributes) while providing no API specification, no bulk download mechanism, no RDF/JSON-LD output for semantic-web consumers, and no export in standard formats (beyond CSV/JSON). Researchers who want to analyze the data programmatically are better served by a simple data dictionary and a machine-readable dump than by a carefully crafted navigation hierarchy. (Presentation §passim; Results §4–6.)

*Fix:* Defer the fine-grained presentation specification to M4 and prioritize: (a) a data dictionary that a researcher can read in 10 minutes; (b) a single-download archive of the release; (c) a REST endpoint or at minimum a well-documented JSON schema.

**2.4 The ODEM frame is personal conceptual overhead.** The Ontology-Data-Evidence-Models frame appears to be the author's own framework, imported from a design note on interactive causal inquiry. It is not a standard, it has no community adoption, and it introduces terminology (D1–D4, O/D/E/M) that every reader—including the development agents and future maintainers—must learn. The spec says the ODEM letters "appear in code, data attributes and these documents, not in page copy," but they pervade the specification's own structure. A simpler vocabulary (register, statements, observations, referents, results) is already used throughout and would serve better. (Language; Ontology §0; multiple documents.)

*Fix:* Retire ODEM as the organizing frame for the specification; keep the four-step pipeline (D1–D4) under plain names (register, lines, observations, referents) and eliminate the O/D/E/M vocabulary from the specification set.

---

### 3. State of the Art

**3.1 Entity resolution ignores established practice.** The spec's "proposers" hierarchy (exact identifier → normalised label → named entities → LLM reading → arbiter) is a reasonable pipeline, but it does not engage with the fifty-year literature on probabilistic record linkage (Fellegi-Sunter), blocking strategies, or clustering algorithms. The depth-one restriction on same_as chains (Fusion §3: "the source of an accepted same_as is never the target of another") is a novel constraint that contradicts standard practice, where transitive closure with conflict detection is the norm. The spec's justification ("likelihoods do not compose along a chain") is mathematically fair but practically crippling—see Dead Angles below. (Fusion §3.)

*Fix:* Replace the depth-one restriction with a declared clustering algorithm (e.g., connected components at the threshold, with conflict detection for rejected same_as edges within a component) and cite the record-linkage literature that motivates it.

**3.2 The bitemporal model is correct but nonstandard in expression.** The spec's "Two times" (fusion §1, §8) and "knowledge cutoff" map cleanly to the standard bitemporal distinction between valid time (when the event occurred) and transaction time (when the system learned it). Using standard terminology would make the design more accessible to database engineers and would connect to established bitemporal database practice (e.g., Snodgrass, "Developing Time-Oriented Database Applications"). (Fusion §1, §8; Storage §1 "Times per table.")

*Fix:* Not a blocker, but using "valid time" and "transaction time" (or "system time") in at least one place would signal awareness of the standard literature.

**3.3 No engagement with schema.org, JSON-LD, or linked open data.** The Observatory publishes static pages with no structured data markup. For a dataset that wants to be cited by researchers and referenced by journalists, JSON-LD with schema.org/Dataset markup on every page would make the data discoverable by search engines and interoperable with the growing linked-data ecosystem. The spec's SKOS export covers only value lists and is deferred to M4. (Ontology §5; Presentation.)

*Fix:* Add JSON-LD Dataset markup to the Observatory pages at M3b; it costs one script.

**3.4 The calibration methodology is novel but under-specified.** The "agree-but-wrong rate" (both readers agree but are wrong) is an interesting metric that captures correlated errors. But the spec does not specify: (a) how many held-out items are needed for the calibration to be meaningful (it says 30 per stratum, but with 4 countries × 4+ languages × 13 classifications, the strata multiply fast); (b) what happens when a stratum is uninformative (it says "reported as uninformative, not as calibrated" but doesn't say whether the method is used anyway); (c) how the calibration maps to the IPCC likelihood terms quantitatively. The mapping from "raw self-scores" to likelihood terms is described but the mapping procedure itself is not. (Extraction §6.3; Q5.)

*Fix:* Specify the mapping procedure (e.g., isotonic regression or a simple bin calibration), state a minimum total sample size (not just per stratum), and define a fallback when calibration is uninformative for a stratum (e.g., default to the arbiter only, or flag the stratum's results as uncalibrated).

**3.5 LLM-as-judge practice does not address known biases.** The two-reader protocol does not address: (a) position bias (the order in which candidates are presented affects judgment); (b) verbosity bias (longer, more detailed proposals are rated higher); (c) self-preference (a model may prefer outputs that resemble its own style). For extraction (where the two readers see the same document), these are less severe than for matching (where two candidate statements are compared side by side). The spec should at minimum randomize the order of presentation for matching candidates. (Extraction §6.3; Fusion §3.)

*Fix:* Add position-randomization for pairwise matching judgments and note the known biases in the method documentation.

**3.6 FAIR compliance is partial.** The spec says FAIR applies "fully to the released datasets" but: (a) Findable—no PIDs for individual statements or observations, only for releases; (b) Accessible—data is in CSV/JSON, fine; (c) Interoperable—no mapping to standard ontologies beyond CRS/IATI codes for the data itself (the ontology is bespoke); (d) Reusable—open licensing is well-handled. The weakest area is interoperability: a researcher wanting to combine JETP Observer data with, say, the Climate Policy Initiative's landscape data or the OECD's climate finance statistics has no shared vocabulary to do so beyond country and currency codes. (Requirements §4, "FAIR assessment"; F31.)

*Fix:* Map the ontology's core classes (project, agreement, party, asset) to at least one external vocabulary (even if only as skos:closeMatch) and include the mapping in the SKOS export.

---

### 4. Implementation Realism

**4.1 The calibration reference answers are a chicken-and-egg problem.** The spec requires calibration of readers on held-out reference answers before any unattended run. These reference answers are "lines read by hand, match judgements decided by hand." But the author hasn't yet done the matching (M3b), so where do the match reference answers come from? The "M1b catalogue" is referenced but is from a previous iteration and may not align with the new ontology. If there are fewer than 30 hand-judged matches per stratum (which is likely for a first run), the calibration is "uninformative" and the system cannot proceed with calibrated readers. This is a blocking dependency that the spec does not resolve. (Extraction §6.3; Fusion §3.)

*Fix:* State explicitly: the first M3b run proceeds with uncalibrated readers (flagged as such), the author hand-checks a minimum set (e.g., 200 matches across 4 countries), and subsequent runs are calibrated. Or: hand-label the reference answers before M3b matching begins, with a stated target and effort estimate.

**4.2 The local LLM readers are undersized for the task.** Two consumer GPUs (16 GB and 12 GB) can serve models of roughly 7B–14B parameters at reasonable quantization. For complex extraction from PDFs in four languages (Indonesian, Vietnamese, French, English), including table parsing, status classification, and amount/scale handling, these models may not be reliable enough. The spec acknowledges this by routing escalation to a hosted arbiter, but if most items escalate, the cost estimate breaks: the $3/document budget assumes most items are resolved by local readers agreeing. If the local readers can't extract reliably, the effective cost per document is the hosted arbiter cost for most items, which is not estimated. (Operation §2, §5, §7.)

*Fix:* Measure the agreement rate between the two local readers on a sample of documents at M2, and if the escalation rate exceeds a threshold (e.g., 30%), revise the budget estimate before proceeding to M3b.

**4.3 The specification itself is a maintenance burden.** Ten documents, each 5–15 pages, with cross-references, milestone tags, a retired-terms list, a requirements-to-documents map (§9), and a reverse map of sections to requirements. Every code change must cite a requirement; every requirement must be mapped to a document; every term must be in the terms table. This meta-level bookkeeping is itself a project. For one researcher with a day job (writing papers, teaching, etc.), the cost of keeping the specification synchronized with the code and the data is significant and recurring. The spec's own maintainability requirements (Q18–Q21) apply to the Observer's code, but the specification documents themselves need the same treatment and don't have it. (All documents.)

*Fix:* Consolidate the specification into fewer documents (e.g., merge Language into Ontology; merge Collection and Extraction; merge Results and Presentation), and generate the requirements map and reverse map from structured metadata rather than maintaining them by hand.

**4.4 The monthly budget of $150 for all LLM spend is likely too low.** If M3b involves extracting and matching several hundred new documents (discovery at M3a will find new items; DA11 projects 10× growth), and if the arbiter is needed for a significant fraction of items, the cost per release cycle could easily exceed $150. The spec's own estimate says a full assisted pass at mid-tier costs $42, but that's for the documents already held. New documents, matching judgments (which involve reading both candidate statements and their source pages), and correction overlays will add significant cost. (Operation §7.)

*Fix:* Recalibrate the monthly budget after the first M3b run with actual cost data, and state a contingency mechanism (e.g., defer non-critical documents to the next release when budget is exhausted).

**4.5 The CSV-in-git system of record will not scale to the stated volume.** The spec acknowledges this ("The steady state is tens of thousands of lines a year") and mentions Dolt as an M4 option. But the M2/M3 approach—CSV files sharded by country and year, with per-document field tables, validated by loading into SQLite at build time—introduces significant friction: merge conflicts on CSV files are painful to resolve manually; the sharding logic adds complexity; and the "one file is one table" principle breaks down for per-document tables. For one researcher, this overhead is real. (Storage §1, §3.)

*Fix:* Move to SQLite as the system of record at M3b (not M4), with CSV exports as derived outputs. A single SQLite file in git (or Dolt if row-level diffs are needed) is simpler to maintain than sharded CSVs.

---

### 5. Dead Angles

**5.1 The depth-one same_as restriction creates O(n²) judgments.** If the dataset grows to 1,000+ operations (plausible by 2030), and if identity matching produces a connected component of, say, 50 operations (all describing the same power plant across multiple documents), the depth-one rule requires explicit pairwise judgments for every A-C pair where A-B and B-C exist. For a cluster of 50, this is potentially hundreds of additional judgments, each requiring LLM reading or human decision. The spec does not estimate the scale of this problem. In practice, large clusters will either be left in conflict (blocking results) or the rule will be quietly violated. (Fusion §3; Storage §1.)

*Fix:* Replace depth-one with a declared clustering algorithm: at the result's threshold, compute connected components; within each component, check for rejected same_as edges; if conflicts exist, raise them as review items. This is standard practice and avoids the combinatorial blowup.

**5.2 Legal exposure on verbatim content redistribution is unresolved.** The legal note identifies the risk (§2: "the document-rows view re-serves the project table of a plan, which for a protected database is a substantial extraction") but defers the resolution to a human lawyer at go-live. If the lawyer says the four plans' tables are protected databases and cannot be re-served, the entire document-rows view—which is the core of the Observatory's paper-trail feature—must be redesigned. This should be resolved before the Observatory architecture is finalized, not after. (Legal note §2; Results §7; Presentation "The paper trail.")

*Fix:* Obtain the per-table protection assessment before M3b, not at go-live. If any table cannot be re-served, the spec must define an alternative presentation (e.g., aggregate counts with locator-only traceability) as a fallback.

**5.3 Single-person dependency with no succession plan.** The spec's C10 declares a horizon to 2030 with an extension decision in 2028. But the entire system—specification, code, ledger, Observatory—depends on one researcher. The handover note (Operation §9) mentions credentials and restore steps but does not address: who maintains the dataset if the author cannot; whether the specification is comprehensible to a successor; whether the CNRS would assume ownership. For a dataset that the spec itself says "negotiators of the next packages" will rely on, this is a public-good risk. (Operation §9; C10.)

*Fix:* Write a one-page succession plan: who at CNRS or CIRED would take over, what they would need to read first, and what the minimum viable handover looks like. Deposit it with the first release.

**5.4 Model availability and API stability over the horizon to 2030.** The spec assumes that OpenRouter, Anthropic, OpenAI, and other providers will continue to offer APIs at current prices with current data-collection policies. It also assumes that open-weight models of the right size will remain available for local deployment. Over a 3–5 year horizon, any of these could change: prices could rise, data-retention policies could tighten, or open-weight model releases could slow. The spec's method-versioning approach (each model change is a new method version) is correct, but the operational burden of recalibrating every time a model changes is not estimated. (Operation §5; Q9.)

*Fix:* Estimate the recalibration effort (hours and cost) per model change, and define a minimum viable calibration (e.g., 50 items) that can be done quickly if a model is deprecated unexpectedly.

**5.5 The correction overlay mechanism may confuse users.** A correction release (YYYY-MM-rN) keeps the knowledge cutoff K of the release it corrects but applies supersessions recorded after K. If multiple correction releases accumulate (e.g., 2026-11, 2026-11-r1, 2026-11-r2), a user citing "release 2026-11" must be told which correction state they are seeing. The spec says "the old deposit's metadata record gains a pointer to the correction," but the user experience of navigating multiple corrections to a single release is not specified. (Results §9; F25.)

*Fix:* Define a simple rule: the Observatory always shows the latest correction state of the current release; earlier release deposits show their original bytes with a prominent banner naming the correction. Test this with a real user.

**5.6 The "not published" verdict conflates discovery failure with publication absence.** Collection §3 says "not published" means "the recorded search covered the search channels where it would appear and found nothing." But if the search channels are incomplete (the frame misses a publisher, or a language is not searched), "not published" is a false finding. The spec requires "the authority's own channel is the one being tested, so a search that did not reach it cannot close the entry"—but this assumes the authority's own channel is known and searchable. If a ministry publishes only on a new portal that is not in the frame, the verdict "not published" is wrong. The recall estimate partially addresses this, but the known-item list is too small and biased to catch all such gaps. (Collection §3, §6.)

*Fix:* Add a mandatory "unknown" verdict for authorities where the search channels may be incomplete (e.g., a new portal discovered after the campaign started), and report these separately from "not published."

---

### Three Things That Most Threaten the Paper's Central Claim

The central claim is that the JETP Observer will produce a trustworthy, citable dataset that others can rely on without rebuilding the record themselves. The three greatest threats:

1. **The elimination of item-level human review for high-impact figures.** No amount of calibration against held-out answers substitutes for a human checking the twenty numbers that journalists and negotiators will actually quote. If one of those numbers is wrong and both LLM readers agreed on the error, the dataset's credibility is destroyed.

2. **The unresolved legal basis for redistributing verbatim publisher content.** If the per-table protection assessment finds that the four plans' project tables are protected databases, the core paper-trail feature cannot be published as designed, and the dataset becomes substantially less useful.

3. **The calibration reference answers do not yet exist at the required scale.** Without hand-labeled reference answers for matching, the calibration is uninformative, the likelihood terms are meaningless, and the two-threshold reporting mechanism has no foundation. The chicken-and-egg problem (can't calibrate without data, can't trust uncalibrated data) must be solved before M3b matching begins.

---

### Overall Verdict: **Major Revision**

---

### Five Most Important Changes, in Priority Order

1. **Reinstate a bounded, prioritized human review of released results.** All figures above a materiality threshold (e.g., country totals, any figure cited on the Observatory homepage) must be checked by the author before each release, plus a random sample of statements. Budget: 2–4 hours per release cycle. This single change transforms the dataset from "interesting but unverifiable" to "trustworthy."

2. **Obtain the per-table protection assessment and the GDPR controller determination before M3b architecture is frozen.** If verbatim re-serving of publisher tables is blocked, the paper-trail design must change, and this must be known before code is written. The CNRS legal service and DPO must be engaged now, not at go-live.

3. **Create the calibration reference answers as a first-class deliverable with a stated budget.** Specify: how many hand-labeled items are needed (minimum 200 matches, minimum 500 extraction readings), who creates them (the author), over what period, and what happens if calibration is uninformative for a stratum. Without this, the likelihood and confidence scales are decorative.

4. **Replace the depth-one same_as restriction with a declared clustering algorithm.** Connected components at the threshold, with conflict detection for rejected edges within a component. This is standard, it avoids the O(n²) blowup, and it can be specified in one paragraph.

5. **Consolidate the specification from ten documents to five and generate the cross-reference maps from structured metadata.** The meta-overhead of maintaining the current specification set is itself a project for one researcher. Merge Language into Ontology, merge Collection and Extraction, merge Results and Presentation. Generate the requirements map (§9) and the reverse map from a YAML or JSON file that can be validated automatically.

---

### What Is Excellent and Should Be Kept

- **The append-only, supersession-based model for all decisions.** This is genuinely best practice: nothing is edited in place, every change is a new row that names what it revises, and the full history of every judgment is retrievable. Keep this exactly as designed.

- **The bitemporal discipline ("Two times" / knowledge cutoff).** The separation between when an event occurred and when the ledger learned of it, with as-of queries and correction overlays, is sophisticated and correct. Most data projects get this wrong; this specification gets it right.

- **The refusal to manufacture preferred figures or hide disagreement.** The principle that "no preferred figure is manufactured to fill a gap" and that unresolved disagreement is carried into the result with both values is intellectually honest and rare in climate-finance tracking. Keep this as a hard constraint.

- **The snapshot-based traceability model.** Every statement cites exact bytes under a SHA-256 fingerprint, never a URL. This ensures that what was read can always be re-read, even if the publisher changes or deletes the document. This is the strongest feature of the design.

- **The cost-tracking per method (Q15, Q17).** Recording LLM spend and human minutes per document, per method, per extraction path, and publishing these with each release, is unusually transparent and will serve the AEDIST research programme well. Keep this.

- **The explicit non-requirements (N1–N13).** Knowing what the system does not do—no causal models, no closed material, no real-time monitoring, no grading of partners—is as valuable as knowing what it does. This discipline prevents scope creep and keeps the dataset honest about its limits.
