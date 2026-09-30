# Peer review — mistralai/mistral-large-2512, persona: student

### Review of the JETP Observer System Specification

---

#### **What is genuinely novel or useful?**
This is a meticulously designed system for creating a **documentary dataset** on Just Energy Transition Partnerships (JETPs) using a combination of human and LLM-assisted workflows. The most novel and useful aspects include:

1. **Provenance-first design**: Every statement, judgement, and result is traceable back to its source document, snapshot, and locator. This is a gold standard for documentary datasets, especially in contested domains like climate finance.
2. **Incremental, milestone-driven development**: The system is built to work first (M2, M3) and polished later (M4). This is pragmatic and ensures that the dataset is usable early, even if not perfect.
3. **LLM-as-judge with human oversight**: The use of diverse LLM vendors for extraction and judgement, with human review of disagreements and random samples, is a robust way to scale while maintaining quality.
4. **Bitemporal data model**: The distinction between "world time" (when an event happened) and "knowledge time" (when the ledger knew about it) is critical for reproducibility and accountability.
5. **FAIR compliance by design**: The system is built to be Findable, Accessible, Interoperable, and Reusable (FAIR) from the ground up, with persistent identifiers, rich metadata, and open licences.

---

### **Sharp, incisive questions**

#### **1. Internal coherence: contradictions, undefined terms, untestable rules**

##### **a. Undefined or ambiguous terms**
- **Section 4.2 (Statements and traceability), F1**: "Every statement names where it was extracted." The term "locator" is defined in the ontology, but its syntax and resolution are deferred to the storage contract and extraction. This creates a circular dependency: the extraction spec relies on the locator, but the locator's meaning is defined in extraction. **Suggestion**: Define the locator's syntax and resolution rules in the language document, not in the storage contract.
- **Section 4.3 (Identities and judgements), F11**: "Referents by decision, counted at a declared match threshold." The term "referent" is defined in the ontology, but the fusion spec does not clearly state how a referent is minted or attached to a statement. **Suggestion**: Add a rule in fusion that explicitly states that a referent is minted only by a line-referents row with a basis.
- **Section 4.4 (Observations, accounts and results), F10**: "Results at a knowledge cutoff." The term "knowledge cutoff" is used throughout but is not defined in the language document. **Suggestion**: Define it in the language document as "the date up to which statements and judgements are admitted for a result."

##### **b. Contradictions**
- **Section 4.2 (Statements and traceability), F4**: "Living documents append, never overwrite." This is contradicted by the snapshot rules in extraction (section 8), which state that a new snapshot with identical text is treated as persistence, not a new statement. **Clarification needed**: Is persistence a form of overwriting? If not, how is it distinct?
- **Section 4.3 (Identities and judgements), F12**: "Organisations under authority control." The ontology states that parties are under authority control, but the fusion spec does not explain how this is enforced. **Suggestion**: Add a rule in fusion that external identifiers (e.g., ROR, LEI) decide party identity where they exist.
- **Section 4.5 (Releases and reuse), F28**: "Persistent identifier." The spec states that each release is deposited in a public data repository, but the operation spec does not mention how this is automated or who is responsible. **Suggestion**: Add a rule in operation that the author or an agent deposits the release and records the persistent identifier in the descriptor.

##### **c. Untestable rules**
- **Section 6.1 (Correctness and reproducibility), Q1**: "Replay. The pipeline reproduces the statements of the 254 documents already extracted, byte for byte, or every difference is explained." This is untestable for LLM-extracted statements, as replay only checks locators and text, not the extraction itself. **Suggestion**: Clarify that replay is a partial oracle and state its limits explicitly in the quality requirements.
- **Section 6.2 (Judgement and uncertainty), Q5**: "Machine judgements are automated, diverse and recorded." The spec does not state how diversity is measured or enforced. **Suggestion**: Add a rule that the panel must include at least two vendors, and that a reader that misses a positive control is weighted out.
- **Section 6.4 (Maintainability and operation), Q18**: "Maintainable by agents and one researcher." This is untestable without a concrete definition of "maintainable." **Suggestion**: Define it as "every behaviour is governed by a rule, implemented in code, and guarded by a test that an agent can run without the author's intervention."

---

#### **2. Fitness for purpose: will this produce a trustworthy, citable dataset?**

##### **a. Missing or over-built components**
- **Missing**:
  - **Legal exposure**: The spec does not address potential legal risks, such as copyright infringement for redistributed documents or defamation for attributed statements. **Suggestion**: Add a non-requirement (N14) stating that legal review is out of scope, and document the process for handling takedown requests.
  - **Drift over time**: The spec assumes that the partnerships will continue, but does not address how the system will handle a partner withdrawing or a partnership lapsing. **Suggestion**: Add a rule in fusion that a withdrawn partner's statements are kept but marked as such, and that a lapsed partnership is documented as a development.
  - **Uncertainty communication**: The spec states that uncertainty is never hidden, but does not specify how ranges, intervals, and unresolved disagreements are presented to users. **Suggestion**: Add a rule in presentation that ranges and intervals are shown with their bounds, and that unresolved disagreements are marked as such with a link to the conflicting statements.
- **Over-built**:
  - **SKOS export (ontology section 5)**: This is a nice-to-have for external consumers but is not required for the Observer's core purpose. **Suggestion**: Move it to "later" and state that it will be built only if a consumer asks for it.
  - **Derived translations and summaries (storage section 5)**: These are not required for the dataset's core purpose and add complexity. **Suggestion**: Move them to "later" and state that they will be built only if a reader needs them.

##### **b. Human review load**
- The spec bounds the author's review to 100 items per run and 3 hours per week (operation section 7.2). However, the M2 assisted pass over 115 documents could present up to 11,500 disagreements (100 per document), which would exceed the budget. **Suggestion**: Add a rule in extraction that the random sample shown to the author is capped at 10% of the agreements, with a floor of 10 items per document.
- The spec does not state how the author's review time is logged or attributed. **Suggestion**: Add a rule in operation that the author records start and end times for each sitting, and that minutes are attributed per run and per document.

##### **c. Cost explosion**
- The spec budgets USD 3 per document for LLM spend (operation section 7.2), but the M2 pilot measured USD 0.03 to 0.08 per document. **Suggestion**: Revise the budget to USD 0.50 per document and state that it is a ceiling, not a target.
- The spec does not address how the budget for paid web search (USD 25 per campaign) will scale with additional countries or deeper searches. **Suggestion**: Add a rule in collection that the budget is per country and per language, and that deeper searches are deferred to later work.

---

#### **3. State of the art: where does this reinvent, contradict, or ignore established practice?**

##### **a. Provenance models**
- The spec uses a custom provenance model (ODEM) instead of adopting PROV-O or W3C PROV. This reinvents the wheel and limits interoperability. **Suggestion**: Map the ODEM steps (D1-D4) to PROV-O classes and relations, and export the ledger as PROV-O for external consumers.
- The spec does not address how provenance is communicated to users. **Suggestion**: Add a rule in presentation that every number links to its provenance trail, and that the trail is shown in a standard format (e.g., PROV-N or a custom visualisation).

##### **b. Vocabularies and bibliographic models**
- The spec uses a custom ontology instead of reusing existing vocabularies like schema.org, Dublin Core, or the Open Energy Ontology. This limits interoperability. **Suggestion**: Map the ontology's classes and relations to existing vocabularies where possible, and document the gaps.
- The spec does not address how documents are cited in the ledger. **Suggestion**: Add a rule in the ontology that every document carries a citation string (e.g., "JETP Indonesia Secretariat (2026). Investment Plan 2026. Jakarta."), and that the citation is shown on the document's page.

##### **c. Bitemporal data**
- The spec distinguishes between "world time" and "knowledge time," but does not explain how these are implemented in the storage contract. **Suggestion**: Add a rule in storage that every row carries a recorded_at timestamp, and that the as-of state at cutoff K is computed from the recorded_at and the in-force rule.
- The spec does not address how bitemporal queries are performed. **Suggestion**: Add a rule in storage that the build engine supports as-of queries, and that the Observatory's API exposes them.

##### **d. Record linkage and entity resolution**
- The spec uses a custom matching pipeline (tiers 1-5) instead of adopting established record linkage tools like OpenRefine or Dedupe. This reinvents the wheel. **Suggestion**: Evaluate whether existing tools can handle the proposers' tiers 1-3, and document the gaps.
- The spec does not address how matching uncertainty is propagated to results. **Suggestion**: Add a rule in fusion that a result computed at two match thresholds carries both values and the candidate matches between them.

##### **e. Uncertainty communication**
- The spec uses the IPCC's likelihood and confidence scales, but does not explain how these are communicated to users. **Suggestion**: Add a rule in presentation that likelihood and confidence are shown as text (e.g., "likely, medium confidence") and that the scales are explained in the glossary.
- The spec does not address how ranges and intervals are presented. **Suggestion**: Add a rule in presentation that ranges are shown with their bounds (e.g., "USD 10–12 million"), and that intervals are shown with their precision (e.g., "2026 (year)").

##### **f. LLM-as-judge practice**
- The spec uses LLM readers for extraction and judgement, but does not address how their performance is monitored over time. **Suggestion**: Add a rule in operation that the monthly tally includes the agreement rate between readers, and that a reader that falls below a threshold is replaced.
- The spec does not address how LLM biases are mitigated. **Suggestion**: Add a rule in extraction that the panel includes at least two vendors, and that the author reviews a random sample of agreements to check for systematic biases.

##### **g. FAIR principles**
- The spec states that the FAIR principles apply to the released datasets, but does not explain how they are enforced. **Suggestion**: Add a rule in results that the build checks for FAIR compliance before publication, and that the validation report includes a FAIR assessment.

---

#### **4. Implementation realism for one person with a workstation and API budgets**

##### **a. Human review load**
- The spec bounds the author's review to 100 items per run and 3 hours per week, but the M2 assisted pass could present up to 11,500 disagreements. **Suggestion**: Add a rule in extraction that the random sample shown to the author is capped at 10% of the agreements, with a floor of 10 items per document.
- The spec does not state how the author's review time is logged or attributed. **Suggestion**: Add a rule in operation that the author records start and end times for each sitting, and that minutes are attributed per run and per document.

##### **b. Cost realism**
- The spec budgets USD 3 per document for LLM spend, but the M2 pilot measured USD 0.03 to 0.08 per document. **Suggestion**: Revise the budget to USD 0.50 per document and state that it is a ceiling, not a target.
- The spec does not address how the budget for paid web search (USD 25 per campaign) will scale with additional countries or deeper searches. **Suggestion**: Add a rule in collection that the budget is per country and per language, and that deeper searches are deferred to later work.

##### **c. Single points of failure**
- The spec relies on padme for all jobs that read bytes or run LLMs, but does not address how the system will handle padme's failure. **Suggestion**: Add a rule in operation that doudou can launch a deferred run when padme is unreachable, and that the deferral is recorded in the run report.
- The spec does not address how the system will handle the author's unavailability. **Suggestion**: Add a rule in operation that the author designates a backup reviewer for each milestone, and that the backup's decisions are recorded in the ledger.

---

#### **5. Dead angles: failure modes, legal exposure, drift over time**

##### **a. Failure modes**
- **Document store loss**: The spec states that document bytes are backed up on doudou, but this is not automated. **Suggestion**: Add a rule in operation that doudou pulls the DVC cache after every push, and that the author verifies the backup monthly.
- **LLM service failure**: The spec states that a failed LLM service is retried with backoff, but does not address how the system will handle a prolonged outage. **Suggestion**: Add a rule in operation that a run defers documents that cannot be read due to a service failure, and that the deferral is recorded in the run report.
- **Legal exposure**: The spec does not address potential legal risks, such as copyright infringement for redistributed documents or defamation for attributed statements. **Suggestion**: Add a non-requirement (N14) stating that legal review is out of scope, and document the process for handling takedown requests.

##### **b. Legal exposure**
- The spec states that the Observer is an open-source intelligence instrument and that it collects only public documents, but does not address how it will handle takedown requests or legal challenges. **Suggestion**: Add a rule in operation that the author maintains a process for handling takedown requests, and that the process is documented in the repository.
- The spec does not address how the system will handle documents that are later found to be non-public or leaked. **Suggestion**: Add a rule in collection that a document found to be non-public is removed from the ledger, and that the removal is recorded as a disposition.

##### **c. Drift over time**
- The spec assumes that the partnerships will continue, but does not address how the system will handle a partner withdrawing or a partnership lapsing. **Suggestion**: Add a rule in fusion that a withdrawn partner's statements are kept but marked as such, and that a lapsed partnership is documented as a development.
- The spec does not address how the system will handle changes in the partnerships' disclosure practices, such as a shift to closed reporting. **Suggestion**: Add a rule in collection that a change in disclosure practices is recorded as a development, and that the change is documented in the collection report.

---

### **Overall verdict**
**Major revision**. The specification is well-structured and addresses many critical aspects of building a documentary dataset, but it has gaps in internal coherence, fitness for purpose, and implementation realism that need to be addressed before it can be considered ready. The most pressing issues are:

1. **Undefined or ambiguous terms** (e.g., "locator," "knowledge cutoff," "referent").
2. **Contradictions** (e.g., "living documents append, never overwrite" vs. snapshot rules).
3. **Untestable rules** (e.g., replay for LLM-extracted statements, maintainability by agents).
4. **Missing components** (e.g., legal exposure, drift over time, uncertainty communication).
5. **Human review load and cost explosion** (e.g., author's review budget, LLM spend per document).

---

### **Five most important changes, in priority order**

1. **Define critical terms in the language document**:
   - Add definitions for "locator," "knowledge cutoff," "referent," and "match threshold."
   - Clarify the syntax and resolution rules for locators in the language document, not in the storage contract.

2. **Resolve contradictions and clarify rules**:
   - Clarify the snapshot rules in extraction (section 8) to distinguish between persistence and new statements.
   - Add a rule in fusion that external identifiers (e.g., ROR, LEI) decide party identity where they exist.

3. **Make untestable rules testable**:
   - Clarify that replay is a partial oracle for LLM-extracted statements, and state its limits explicitly in the quality requirements.
   - Add a rule that the panel must include at least two vendors, and that a reader that misses a positive control is weighted out.

4. **Address missing components**:
   - Add a non-requirement (N14) stating that legal review is out of scope, and document the process for handling takedown requests.
   - Add a rule in fusion that a withdrawn partner's statements are kept but marked as such, and that a lapsed partnership is documented as a development.

5. **Bound the human review load and cost**:
   - Add a rule in extraction that the random sample shown to the author is capped at 10% of the agreements, with a floor of 10 items per document.
   - Revise the LLM spend budget to USD 0.50 per document and state that it is a ceiling, not a target.

---

### **What is excellent and should be kept**
1. **Provenance-first design**: The traceability of every statement, judgement, and result back to its source document is a gold standard for documentary datasets.
2. **Incremental, milestone-driven development**: The focus on working first (M2, M3) and polishing later (M4) is pragmatic and ensures that the dataset is usable early.
3. **LLM-as-judge with human oversight**: The use of diverse LLM vendors for extraction and judgement, with human review of disagreements and random samples, is a robust way to scale while maintaining quality.
4. **Bitemporal data model**: The distinction between "world time" and "knowledge time" is critical for reproducibility and accountability.
5. **FAIR compliance by design**: The system is built to be Findable, Accessible, Interoperable, and Reusable (FAIR) from the ground up, with persistent identifiers, rich metadata, and open licences.

---

### **Questions for the authors**

1. **Locators**: How will the locator's syntax and resolution rules be defined and enforced? Can this be moved from the storage contract to the language document?
2. **Referents**: How is a referent minted or attached to a statement? Can you add a rule in fusion that explicitly states this?
3. **Knowledge cutoff**: How is the "knowledge cutoff" implemented in the storage contract? Can you add a rule that every row carries a recorded_at timestamp?
4. **Replay**: How will replay work for LLM-extracted statements, given that they are not byte-reproducible? Can you clarify that replay is a partial oracle and state its limits?
5. **Human review load**: How will the author's review load be bounded for the M2 assisted pass? Can you add a rule capping the random sample at 10% of agreements, with a floor of 10 items per document?
6. **Cost explosion**: How will the LLM spend budget be enforced per document? Can you revise the budget to USD 0.50 per document and state that it is a ceiling?
7. **Legal exposure**: How will the system handle takedown requests or legal challenges? Can you add a non-requirement stating that legal review is out of scope and document the process?
8. **Drift over time**: How will the system handle a partner withdrawing or a partnership lapsing? Can you add a rule in fusion that such developments are documented as such?
9. **Uncertainty communication**: How will ranges, intervals, and unresolved disagreements be presented to users? Can you add a rule in presentation that they are shown with their bounds and marked as such?
10. **Provenance models**: Why was PROV-O not adopted for provenance? Can you map the ODEM steps to PROV-O classes and relations?

---

### **One experiment to run next**
**Pilot the M2 assisted pass with bounded review load**:
- Run the assisted extraction pipeline on a sample of 10 held documents, with the random sample capped at 10% of agreements (floor of 10 items per document).
- Measure the author's review time per document and the agreement rate between the reader and checker.
- Compare the cost and quality of the local LLM (Qwen3.8-27B) against a paid mid-tier LLM (e.g., Anthropic Sonnet) for bulk reading.
- Use the results to revise the budgets for LLM spend and author review time, and to decide whether the local LLM is viable for bulk reading.
