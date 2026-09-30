# Peer review — mistralai/mistral-large-2512, persona: grinchy

### Overall Verdict: **Major Revision**

This is a meticulously designed system specification with a clear focus on reproducibility, traceability, and incremental delivery. The author has clearly thought deeply about the challenges of building a documentary dataset from heterogeneous sources, and the specification reflects a strong grasp of data provenance, uncertainty communication, and FAIR principles. However, the system as specified has several critical gaps, contradictions, and overclaims that threaten its central claim of producing a "trustworthy, citable dataset" for the stated users. Below is a prioritized list of concrete objections, followed by the three most significant threats to the paper's central claim.

---

### Prioritized Objections

#### 1. **Overclaims about LLM-as-judge reliability (Extraction §6.3, Fusion §3, Operation §5)**
   - **Issue**: The specification relies heavily on LLM readers for extraction and fusion judgements, with minimal human oversight (e.g., the author reviews only disagreements and a random sample). While the use of diverse vendors and calibrated likelihood/confidence scales is a step forward, there is no evidence that this approach is sufficiently reliable for the stated purpose. The specification assumes that LLM disagreements will surface errors, but this has not been empirically validated for this domain. The risk of systematic bias or hallucination in LLM judgements is not addressed.
   - **Section/Figure**: Extraction §6.3, Fusion §3, Operation §5, Q5, Q17.
   - **Fix**:
     - Add a requirement for a benchmark evaluation of LLM-as-judge performance on a held-out set of human-annotated documents, with metrics for precision, recall, and agreement with human judgements. This should be a prerequisite for M3b.
     - Explicitly state the limitations of LLM-as-judge in the "Assumptions and risks" section of the requirements document, including the possibility of systematic errors that may not be caught by the checking rule.
     - Require that the M3b release include a disclaimer about the reliance on LLM judgements and the potential for undetected errors.

#### 2. **Inadequate handling of temporal uncertainty (Extraction §11, Fusion §7, Results §2)**
   - **Issue**: The specification treats dates as intervals with precision (e.g., "Q1 2026" as a quarterly interval), but it does not adequately address the problem of temporal uncertainty in financial and physical states. For example:
     - A "disbursement to date" figure may be cumulative over an unknown period, but the specification does not require that the interval be explicitly bounded or that the uncertainty be propagated into results.
     - The rules for reconstructing accounts (Fusion §7) assume that movements can be cleanly assigned to intervals, but this is often impossible in practice (e.g., overlapping quarterly totals with no decomposition).
   - **Section/Figure**: Extraction §11, Fusion §7, Results §2, F16.
   - **Fix**:
     - Revise the rules for reconstructing accounts to explicitly state when a residual or gap is due to temporal uncertainty (e.g., "residual due to overlapping intervals with no supported decomposition").
     - Require that all cumulative or "to date" figures be treated as closing positions with an open lower bound, and that this uncertainty be propagated into results (e.g., as a range or a disclaimer).
     - Add a requirement for a sensitivity analysis of results to temporal uncertainty, to be included in the M3b release.

#### 3. **Contradictions in the handling of duplicates and restatements (Extraction §2, §8, Fusion §2)**
   - **Issue**: The specification is inconsistent in how it handles duplicates and restatements:
     - Extraction §2 states that "a document that is a later edition of one already extracted is its own document, related by edition_of," but Extraction §8 treats restatements as persistence rather than corroboration, even though they may represent the same logical content.
     - The rules for pairing statements across snapshots (Extraction §8) assume that content can be compared field-by-field, but this is not always possible (e.g., when a publisher changes the structure of a table or the wording of a label).
     - The specification does not distinguish between a restatement (same content, later date) and a correction (different content, later date), which are fundamentally different.
   - **Section/Figure**: Extraction §2, §8, Fusion §2, F4.
   - **Fix**:
     - Clarify the distinction between editions (new documents) and restatements (new snapshots of the same document). Restatements should be treated as persistence only if the content is byte-identical or text-identical under a declared normalisation rule.
     - Revise the rules for pairing statements across snapshots to require a human judgement when the content is not directly comparable (e.g., due to structural changes).
     - Add a requirement for a disclaimer in the M3b release about the limitations of automatic pairing of statements across snapshots.

#### 4. **Missing or shallow related work on provenance models and uncertainty communication (Requirements §4, Fusion §1)**
   - **Issue**: The specification reinvents several wheels without engaging with established practice:
     - The ODEM frame (Ontology, Data, Evidence, Models) is a bespoke provenance model that does not cite or align with existing provenance standards (e.g., PROV-O, W3C PROV, or the PREMIS data dictionary for preservation metadata).
     - The treatment of uncertainty (likelihood and confidence scales) is inspired by the IPCC but does not engage with the broader literature on uncertainty communication in observational datasets (e.g., the NUSAP system, probabilistic programming, or Bayesian networks).
     - The specification does not cite or compare itself to existing documentary datasets in climate finance (e.g., Climate Policy Initiative's datasets, OECD CRS, or IATI), which limits its ability to claim novelty or fitness for purpose.
   - **Section/Figure**: Requirements §4, Fusion §1, Ontology §5.
   - **Fix**:
     - Add a "Related Work" section to the requirements document that situates the Observer within the broader landscape of provenance models, uncertainty communication, and documentary datasets in climate finance.
     - Align the ODEM frame with PROV-O or another provenance standard, and explain how it differs or extends existing practice.
     - Cite and compare the Observer's uncertainty communication approach to existing systems (e.g., NUSAP, IPCC, or probabilistic databases).

#### 5. **Statistical weaknesses in recall estimation (Collection §6, §7)**
   - **Issue**: The recall estimate is based on a known-item list, which is acknowledged to overstate recall because known items are more visible than the average document. However:
     - The specification does not require a second, independent estimate of recall (e.g., via capture-recapture or a random sample of documents from a secondary source).
     - The known-item list is small (minimum 40 items across four countries), which limits the precision of the recall estimate.
     - The specification does not require that the recall estimate be stratified by document type or publisher, which may hide systematic gaps in coverage.
   - **Section/Figure**: Collection §6, §7, Q10.
   - **Fix**:
     - Require a second, independent estimate of recall (e.g., via capture-recapture) for the M3b release, and report both estimates with their intervals.
     - Increase the size of the known-item list to at least 100 items, and stratify it by document type and publisher.
     - Require that the recall estimate be reported separately for each country and document type in the M3b release.

#### 6. **Implementation realism: Human review load will explode (Extraction §6.3, Fusion §3, Operation §7.2)**
   - **Issue**: The specification assumes that the author's review load can be bounded (e.g., 100 items per run, 3 hours per week), but this is unrealistic given the scale of the problem:
     - The M2 pass already requires reviewing 115 documents, and the M3b pass will require reviewing many more (e.g., new documents, comparator records, and matches).
     - The full panel of LLM readers (M4) will generate even more disagreements, and the author's review load will scale with the number of documents and matches.
     - The specification does not account for the time required to adjudicate complex cases (e.g., conflicting values, ambiguous matches, or temporal uncertainty).
   - **Section/Figure**: Extraction §6.3, Fusion §3, Operation §7.2, Q5.
   - **Fix**:
     - Require a pilot study of the author's review load for the M2 pass, with logged review times per document type and judgement type. Use this to revise the budgets for M3b.
     - Add a requirement for a sensitivity analysis of the author's review load to the number of documents and matches, to be included in the M3b release.
     - Consider outsourcing adjudication of complex cases to domain experts (e.g., country specialists) for M4, with a clear protocol for how their judgements are recorded and integrated.

#### 7. **Dead angles: Legal exposure and terms-of-use violations (Collection §1, §8, Requirements §7)**
   - **Issue**: The specification assumes that all documents are publicly accessible and that their terms of use allow redistribution, but this is not always true:
     - Some documents may be behind paywalls or require institutional access (e.g., academic papers, proprietary datasets), which the specification explicitly excludes (N13). However, the specification does not require that the Observer check for such restrictions before fetching or redistributing documents.
     - The specification does not address the legal risks of redistributing documents without explicit permission (e.g., copyright infringement, database rights, or terms-of-use violations).
     - The specification does not require that the Observer maintain a log of terms-of-use changes or that it remove documents from the release if their terms change.
   - **Section/Figure**: Collection §1, §8, Requirements §7, C6, N13.
   - **Fix**:
     - Add a requirement for a legal review of the Observer's document collection and redistribution practices, to be completed before M3b.
     - Require that the Observer check the terms of use of every document before fetching or redistributing it, and that it maintain a log of terms-of-use changes.
     - Add a requirement for a takedown protocol for documents whose terms of use change to forbid redistribution, to be implemented by M4.

#### 8. **Single points of failure: The author's attention and the local LLM (Requirements §7, Operation §2, §5)**
   - **Issue**: The specification relies heavily on the author's attention and the local LLM, both of which are single points of failure:
     - The author is the only person who can make decisions, adjudicate complex cases, or raise budgets. If the author is unavailable (e.g., due to illness or competing priorities), the Observer cannot function.
     - The local LLM is a shared service, and its performance or availability may degrade over time (e.g., due to hardware failure, model drift, or competition from other projects).
   - **Section/Figure**: Requirements §7, Operation §2, §5, C1.
   - **Fix**:
     - Add a requirement for a deputy protocol, in which a named deputy can make decisions or adjudicate cases in the author's absence, to be implemented by M4.
     - Require that the local LLM be benchmarked regularly (e.g., monthly) to detect performance degradation, and that a fallback plan be in place for when it is unavailable.

#### 9. **Drift over the horizon: Maintenance and archiving (Results §12, Operation §11)**
   - **Issue**: The specification assumes that the Observer will be maintained through 2030, but it does not address the long-term sustainability of the system:
     - The specification does not require that the Observer be archived in a way that ensures its long-term accessibility (e.g., via a trusted digital repository or a dark archive).
     - The specification does not address the risk of technical debt (e.g., deprecated dependencies, unsupported hardware, or unmaintained code).
     - The specification does not require that the Observer's methods and data be documented in a way that allows future researchers to understand or reproduce its results.
   - **Section/Figure**: Results §12, Operation §11, C10.
   - **Fix**:
     - Add a requirement for a long-term archiving plan, to be completed by M4, that includes a trusted digital repository and a dark archive.
     - Require that the Observer's code and dependencies be documented and containerized to ensure long-term reproducibility.
     - Add a requirement for a sustainability plan that addresses technical debt, hardware replacement, and code maintenance.

#### 10. **Vague or hand-wavy passages: Matching thresholds and counting scopes (Fusion §3, §6, Results §3)**
   - **Issue**: The specification is vague about how matching thresholds and counting scopes are chosen and applied:
     - The default matching thresholds ("likely or more, medium confidence or more" for cautious; "about as likely as not or more, any confidence" for inclusive) are arbitrary and not justified by empirical evidence.
     - The specification does not require that the sensitivity of results to matching thresholds be reported, which limits the transparency of the results.
     - Counting scopes (e.g., strict JETP scope, extended scope) are defined by the analysis but not by the ontology, which creates a risk of inconsistency or ambiguity in how they are applied.
   - **Section/Figure**: Fusion §3, §6, Results §3, F11, F13.
   - **Fix**:
     - Require that the default matching thresholds be justified by empirical evidence (e.g., a benchmark evaluation on a held-out set of human-annotated matches).
     - Require that the sensitivity of results to matching thresholds be reported in the M3b release, with a disclaimer about the limitations of the chosen thresholds.
     - Add a requirement for a clear, versioned definition of counting scopes, to be included in the ontology tables.

---

### Three Most Significant Threats to the Central Claim

1. **Overreliance on LLM-as-judge without empirical validation**:
   - The central claim of the Observer is that it produces a "trustworthy, citable dataset" for researchers, journalists, and negotiators. However, the specification relies heavily on LLM readers for extraction and fusion judgements, with minimal human oversight. There is no empirical evidence that this approach is sufficiently reliable for the stated purpose, and the risk of systematic bias or hallucination in LLM judgements threatens the trustworthiness of the dataset. Without a benchmark evaluation of LLM-as-judge performance, the Observer's results cannot be considered trustworthy.

2. **Inadequate handling of temporal uncertainty**:
   - The Observer aims to provide a clear record of financial and physical states over time, but the specification does not adequately address the problem of temporal uncertainty. For example, cumulative or "to date" figures are treated as closing positions with open lower bounds, but this uncertainty is not propagated into results. This threatens the central claim by introducing ambiguity into the dataset, which may mislead users about the timing of events or the completeness of accounts.

3. **Contradictions in the handling of duplicates and restatements**:
   - The specification is inconsistent in how it handles duplicates and restatements, which threatens the central claim by introducing ambiguity into the dataset. For example, restatements are treated as persistence rather than corroboration, but this is not always justified (e.g., when a publisher changes the structure of a table or the wording of a label). Without clear rules for distinguishing between editions, restatements, and corrections, the Observer's results may be misleading or inconsistent.

---

### Excellent and Should Be Kept

1. **The ODEM frame and the separation of Data, Evidence, and Models**:
   - The ODEM frame is a clear and useful way to separate the documentary record (Data) from derived results (Evidence) and causal explanations (Models). This separation is critical for ensuring the transparency and reproducibility of the Observer's results.

2. **The focus on traceability and provenance**:
   - The specification's emphasis on traceability (e.g., every statement resolves to a snapshot and a locator, every result names its inputs and methods) is excellent and aligns with best practices in data provenance. This is essential for building trust in the dataset.

3. **The incremental delivery approach**:
   - The specification's focus on incremental delivery (e.g., M2, M3a, M3b, M4) is a strength, as it ensures that the Observer can produce usable results early and refine them over time. This is particularly important for a system built by one researcher on a personal workstation.
