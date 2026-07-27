# Peer review — mistralai/mistral-large-2512, persona: grinchy

**Peer Review Report**
**Recommendation: Major Revision**

This paper presents a curated, multilingual corpus of climate finance literature, addressing a clear gap in the field by integrating multiple sources, including grey literature and non-English works. The effort is commendable in scope, but the manuscript suffers from several critical weaknesses that undermine its claims, methodological rigor, and reusability. Below is a prioritized list of concrete objections, followed by the three most severe threats to the paper’s central claim.

---

### **Prioritized Objections**

#### **1. Overclaims and Unsupported Generalizations (Section 1, 4, 5)**
**Issue:** The paper repeatedly overstates the corpus’s representativeness and utility without sufficient evidence.
- **Claim (Section 1):** The corpus "enables broader coverage than single-source bibliometric studies" and "captures multicultural and Southern perspectives."
  - **Problem:** The corpus is 89.9% English (Table 3), with non-English works dominated by European languages (Portuguese, Spanish, German, French). "Southern perspectives" are barely represented (e.g., no mention of Arabic, Hindi, or Swahili). The grey-literature source explicitly excludes national institutions (Section 2.3), which are critical for Southern voices.
  - **Fix:** Revise claims to reflect the corpus’s actual linguistic and geographic biases. Acknowledge that "multilingual" here means "limited non-English coverage" and that "Southern perspectives" are largely absent. Justify why these omissions do not undermine the corpus’s utility for the stated goals (e.g., "this corpus is designed to study *international* climate finance discourse, not domestic perspectives").
- **Claim (Section 5):** The corpus "turns the definition of ‘climate finance’ from a hidden assumption into an object of analysis."
  - **Problem:** The definition is still implicit in the keyword taxonomy (Section 2.1), which is derived from highly cited papers (a circularity the paper acknowledges but does not resolve). The corpus’s boundaries are arbitrary (e.g., excluding "pure green finance" but including "climate-adjacent terms" with co-occurrence filters).
  - **Fix:** Provide a transparent, reproducible method for defining "climate finance" (e.g., a systematic review of how the term is used in key UNFCCC/OECD documents). Alternatively, frame the corpus as *one possible operationalization* of the term, not a definitive one.

#### **2. Methodological Holes (Section 2.2, 2.3)**
**Issue:** The filtering pipeline is opaque, and its validation is inadequate.
- **Problem (Section 2.2):** The six-flag filtering system is described, but the thresholds for flags (e.g., "semantic outlier detection" at mean + 2 SD) are arbitrary and unvalidated. The cross-encoder relevance scoring (flag 6) is validated on a *blinded sample of 100 works* (Section 2.3), but:
  - The sample size is too small for a corpus of 33,344 works.
  - The validation is not stratified by source or language (e.g., does the cross-encoder perform equally well for non-English works?).
  - The AUC of 0.818 is modest; the paper does not discuss false positives/negatives or their impact on downstream analyses.
  - **Fix:** Provide a larger, stratified validation (e.g., 1,000 works, balanced by source/language). Report precision/recall for each flag, not just AUC. Include a sensitivity analysis showing how varying thresholds (e.g., mean + 1.5 SD vs. + 2.5 SD) affects corpus size and composition.
- **Problem (Section 2.3):** The citation graph is incomplete and biased.
  - 24% of works lack DOIs, and 20.3% of DOI-bearing works contribute no references (Section 2.3). The paper acknowledges this but does not quantify its impact on network analyses (e.g., Figure 2). For example:
    - Are citation communities (Figure 2) robust to the exclusion of no-DOI works?
    - Does the "disconnected" finding of *Kouwenberg and Zheng (2023)* hold if no-DOI works are included?
  - **Fix:** Perform a sensitivity analysis for network metrics (e.g., modularity, community structure) with and without no-DOI works. Alternatively, justify why the current graph is sufficient for the claims made (e.g., "we focus on DOI-linked works because they dominate post-2015 literature").

#### **3. Missing or Shallow Related Work (Section 1, 2.1)**
**Issue:** The paper ignores key prior work on corpus construction and multilingual bibliometrics.
- **Problem (Section 1):** The paper cites three single-source studies (*Carè and Weber, 2023*; *Shang and Jin, 2023*; *Maria et al., 2023*) but ignores:
  - **Multilingual corpora:** E.g., *Waltman et al. (2020)* on multilingual bibliometrics in *Quantitative Science Studies*; *Bornmann et al. (2021)* on non-English literature in *Scientometrics*.
  - **Grey literature:** E.g., *Schöpfel and Farace (2010)* on grey literature in systematic reviews; *Paez (2017)* on grey literature in climate policy.
  - **Corpus validation:** E.g., *Arroyo-Machado et al. (2020)* on validating bibliometric corpora; *Waltman and van Eck (2012)* on citation network validation.
  - **Fix:** Add a dedicated subsection in Section 2.1 comparing the methodology to prior work on multilingual/grey literature corpora. Justify why the chosen approach improves upon or differs from these studies.
- **Problem (Section 2.1):** The keyword taxonomy is derived from highly cited papers, which introduces circularity.
  - The paper acknowledges this (Section 2.1: "a circularity to keep in mind") but does not address it. Highly cited papers may reflect *mainstream* (e.g., Global North) perspectives, excluding marginalized voices.
  - **Fix:** Validate the taxonomy against an independent source (e.g., UNFCCC/OECD glossaries, or a systematic review of climate finance definitions). Alternatively, frame the taxonomy as *one possible definition* and discuss its limitations.

#### **4. Statistical Weaknesses (Section 2.3, 4)**
**Issue:** Key statistical claims are unsupported or misleading.
- **Problem (Section 2.3):** The citation graph verification reports 97.0% accuracy (95% CI [94.4%, 98.4%]) for a *sample of 300 links*.
  - The sample size is too small for a corpus with 1.3M citation pairs. The CI is likely optimistic due to clustering (e.g., citations from the same paper may not be independent).
  - **Fix:** Increase the sample size (e.g., 1,000 links) and use a clustered sampling design (e.g., sample by citing paper). Report the intraclass correlation coefficient (ICC) to justify the CI.
- **Problem (Section 4):** The Chow test for structural breaks (F = 10, p = 0.0004) is applied to *log annual counts*, but:
  - The test assumes homoskedasticity and no autocorrelation, which are likely violated for time-series publication data.
  - The paper does not report the break date or the model used (e.g., linear vs. Poisson regression).
  - **Fix:** Use a more appropriate model (e.g., negative binomial regression for count data) and report robust standard errors. Alternatively, use a nonparametric test (e.g., Pettitt’s test) that does not assume a linear trend.
- **Problem (Figure 1):** The phrase "climate finance" in titles/abstracts is used to track the field’s growth, but:
  - The phrase is absent before 2009 (Figure 1), yet the corpus includes pre-2009 works. This suggests the corpus is capturing *retrospective* uses of the term, not its emergence.
  - **Fix:** Clarify whether the corpus is designed to study the *history* of climate finance (as claimed in Section 1) or its *current* discourse. If the former, justify why pre-2009 works are included despite the term’s absence.

#### **5. Figures/Tables That Do Not Earn Their Space (Figures 1–3, Table 2)**
**Issue:** Several visualizations are redundant or uninformative.
- **Problem (Figure 1):**
  - The "climate finance" phrase subset (dark bars) is nearly identical to the full corpus (light bars) post-2009, making the distinction visually meaningless.
  - The background bands ("Before," "Crystallisation," "Established field") are arbitrary and not justified (e.g., why 2007 and 2015?).
  - **Fix:** Remove the dark bars or replace them with a ratio (e.g., % of works with "climate finance" in title/abstract). Justify the periodization (e.g., "2007 marks the Bali Action Plan, which first formalized climate finance as a negotiation stream").
- **Problem (Figure 2):**
  - The force-directed layout is visually appealing but uninformative. Edge widths are not labeled, and community labels (e.g., "carbon markets & EU ETS") are too small to read.
  - The figure does not show the *temporal evolution* of communities, which is critical for a historical study.
  - **Fix:** Replace with a Sankey diagram showing community evolution over time, or a matrix of inter-community citations. Label edges with citation counts.
- **Problem (Figure 3):**
  - The thematic composition shifts are interesting but lack statistical validation. Are the differences between periods significant?
  - The clusters are labeled with TF-IDF terms, but the paper does not explain how these were derived (e.g., pre-processing, stopwords).
  - **Fix:** Add a statistical test (e.g., chi-square) for differences between periods. Include a table of top TF-IDF terms for each cluster.
- **Problem (Table 2):**
  - The "%Refs" column is misleading. It reports the share of works with *at least one reference*, but the median reference count is 29 (Section 2.3). This obscures the skew in reference counts.
  - **Fix:** Replace with a histogram or boxplot of reference counts per work, stratified by source.

#### **6. Vague or Hand-Wavy Passages (Section 2.4, 3)**
**Issue:** Key methodological details are glossed over.
- **Problem (Section 2.4):** The near-duplicate detection is described as a "two-pass approach" but lacks specifics.
  - How are "abstract prefix clustering" and "title clustering" implemented? What similarity thresholds are used?
  - The paper mentions 344 candidate version pairs (1.0% of works), but how many are *true* duplicates vs. false positives?
  - **Fix:** Provide pseudocode or a flowchart for the near-duplicate detection. Report precision/recall for this step (e.g., manually validate a sample of 100 pairs).
- **Problem (Section 3):** The embeddings are described as "L2-normalised (unit-length) 1024-dimensional vectors," but:
  - The paper does not justify why *BAAI/bgem3* was chosen over other multilingual models (e.g., *paraphrase-multilingual-MiniLM-L12-v2*).
  - The embeddings are computed from titles, abstracts, and keywords, but the paper does not discuss how missing abstracts (13% of works, Table 2) affect performance.
  - **Fix:** Compare *BAAI/bgem3* to at least one other model (e.g., *sentence-transformers/multi-qa-mpnet-base-dot-v1*) on a downstream task (e.g., clustering). Report embedding quality for works with vs. without abstracts.

#### **7. Gap Between Claims and Evidence (Section 1, 4)**
**Issue:** The paper claims the corpus is reusable for "topic modelling, citation network analysis, bibliometric mapping, and cross-lingual studies" (Section 1), but:
- **Topic modelling:** The embeddings are validated only for *k-means clustering* (Section 4), not for other methods (e.g., BERTopic, LDA). The paper does not show that the embeddings capture meaningful semantic differences (e.g., via a qualitative analysis of clusters).
- **Citation network analysis:** The network is incomplete (24% no-DOI works, 20% no references), but the paper does not discuss how this affects analyses (e.g., centrality measures).
- **Cross-lingual studies:** The paper claims the embeddings "support cross-lingual analysis" (Section 1), but:
  - The embeddings are not validated for cross-lingual tasks (e.g., translation retrieval, cross-lingual clustering).
  - The corpus is 89.9% English, so cross-lingual comparisons are limited.
  - **Fix:** For each claimed use case, provide a concrete example (e.g., "we replicated *Kouwenberg and Zheng (2023)*’s finding that finance and public-finance clusters are disconnected, even when including no-DOI works"). Alternatively, tone down the claims (e.g., "the corpus *may* support topic modelling, but users should validate results for their specific task").

---

### **Three Most Severe Threats to the Central Claim**
The central claim is that this corpus "assembles climate finance scholarship into a single, cross-lingual bibliographic object" that is "reusable for topic modelling, citation network analysis, bibliometric mapping, and cross-lingual studies" (Section 1). The three biggest threats to this claim are:

1. **Linguistic and Geographic Bias (Section 2.3, Table 3):**
   - The corpus is 89.9% English and dominated by Global North sources (e.g., OECD, UNFCCC). Non-English works are limited to European languages, and "Southern perspectives" are largely excluded. This undermines claims of "multilingual" and "multicultural" coverage.
   - **Impact:** The corpus cannot support cross-lingual studies or analyses of Southern climate finance discourse. Users may draw misleading conclusions about the field’s diversity.

2. **Incomplete and Biased Citation Network (Section 2.3, 2.4):**
   - 24% of works lack DOIs, and 20% of DOI-bearing works contribute no references. The citation graph is thus incomplete, particularly for early and grey-literature works.
   - **Impact:** Network analyses (e.g., community detection, centrality measures) are biased toward post-2015, DOI-linked works. Findings may not generalize to the full corpus.

3. **Unvalidated Filtering Pipeline (Section 2.2, 2.3):**
   - The six-flag filtering system is validated on a small, unstratified sample (100 works). Thresholds (e.g., mean + 2 SD for semantic outliers) are arbitrary and may exclude relevant works or include irrelevant ones.
   - **Impact:** The corpus’s boundaries are unreliable. Users cannot trust that the included works are truly "about climate finance" or that excluded works are not. This undermines all downstream analyses.

---

### **Summary of Required Revisions**
To address these issues, the authors must:
1. **Revise claims** to reflect the corpus’s actual linguistic, geographic, and methodological limitations (Sections 1, 4, 5).
2. **Validate the filtering pipeline** with a larger, stratified sample and report precision/recall for each flag (Section 2.2).
3. **Address citation graph incompleteness** with a sensitivity analysis for network metrics (Section 2.3).
4. **Compare the corpus to prior work** on multilingual/grey literature corpora (Section 2.1).
5. **Improve statistical rigor** for time-series and network analyses (Sections 2.3, 4).
6. **Redesign or justify figures/tables** to ensure they earn their space (Figures 1–3, Table 2).
7. **Provide concrete examples** of the corpus’s reusability for each claimed use case (Section 1).

Without these revisions, the paper’s central claim—that this corpus is a reusable, cross-lingual resource for climate finance research—is not supported by the evidence. **Major revision is required.**
