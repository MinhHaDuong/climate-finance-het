# Peer review — mistralai/mistral-large-2512, persona: student

This is a **strong, well-documented, and highly reusable** data paper that addresses a critical gap in climate finance research: the fragmentation of literature across languages, sources, and institutional vs. academic divides. The **multilingual, multi-source corpus** (33,344 works) is a major contribution, enabling analyses that were previously infeasible (e.g., non-English scholarship, institutional reports, citation networks). The **reproducible pipeline**, **detailed metadata**, and **transparent filtering** set a high standard for data papers. Below, I focus on **sharp questions and constructive critiques** to strengthen the work.

---

### **Strengths**
1. **Novelty**: The **multilingual retrieval** (8 languages) and **institutional layer** (UNFCCC, OECD, etc.) are genuinely novel. Prior work (e.g., Carè & Weber 2023) relied on single databases and English-only queries. The **teaching canon** (syllabi) and **AI-assisted discovery** (SciSpace) are creative additions.
2. **Reusability**: The **modular pipeline** (DVC, YAML configs) and **detailed provenance tracking** (e.g., `source_count`, `flag_reason`) make it easy to subset or extend the corpus. The **embeddings** and **citation network** are ready-to-use for downstream tasks.
3. **Transparency**: The **audit trail** (Table 2), **validation of relevance scoring** (AUC=0.818), and **limitations section** (2.4) are exemplary. The **Zenodo deposit** is comprehensive.

---

### **Major Questions and Critiques**

#### **1. Scope and Definition of "Climate Finance"**
- **Section 1**: The paper defines climate finance as "North-South financial flows," but the **keyword taxonomy** (Tier 1–4) seems broader (e.g., "green finance," "sustainable finance"). How was the **boundary between climate finance and adjacent fields** (e.g., green finance, ESG) decided? The **40.1% overlap with Maria et al. (2023)** suggests scope divergence—is this a feature (inclusivity) or a bug (noise)?
  - *Suggestion*: Add a **Venn diagram** of query overlaps (e.g., Scopus vs. OpenAlex vs. this corpus) to clarify scope differences.
- **Section 2.1**: The **institutional layer** excludes national reports (e.g., central bank communications). Given that **domestic climate finance** (e.g., China’s green bonds, India’s sovereign green bonds) is a growing field, why was this choice made? The rationale ("tractability") is weak—could the pipeline accommodate future additions?

#### **2. Multilingual Retrieval and Bias**
- **Table 4**: English dominates (93.8%), and **non-English works are filtered out at twice the rate** (41.8% vs. 19.9%). The paper attributes this to the **cross-encoder’s language bias**, but:
  - **Section 2.3**: The **11.5% improvement** from translating the query suggests the model is **not language-agnostic**. Why not **translate all non-English abstracts to English** before scoring? Or use a **multilingual BERT-based scorer** (e.g., `paraphrase-multilingual-mpnet-base-v2`)?
  - **Section 2.4**: The **bibCNRS source** (non-English discourse) has **only 5% abstract coverage** (Table 3). Is this a metadata issue or a reflection of the underlying literature (e.g., news articles lacking abstracts)? If the latter, how does this affect **topic modeling**?
  - *Suggestion*: Provide a **language-stratified analysis** of the embeddings (e.g., t-SNE of `bgem3` vectors colored by language) to show whether **semantic clusters are language-specific**.

#### **3. Citation Network and Metadata Quality**
- **Figure 1**: The **citation network** (13,112 works, 39% of corpus) is a key asset, but:
  - **Section 2.3**: **20% of DOI-bearing works contribute no references** (median=29, mean=42.8). Are these **books, editorials, or grey literature**? If so, the network is **biased toward journal articles**. How does this affect **community detection** (Figure 1)?
  - **Section 2.4**: **No-DOI works (24%) are undercounted** in citations. Could **fuzzy matching** (e.g., title + year) recover some of these? The **GROBID parsing** is a good start, but **author names** (e.g., "J. Smith" vs. "John Smith") could help.
  - **Section 2.3**: The **97% citation accuracy** is impressive, but the **3% error rate** could propagate in network analyses. How sensitive are **Louvain communities** (Figure 1) to these errors? A **perturbation analysis** (e.g., randomly dropping 3% of edges) would help.
  - *Suggestion*: Add a **citation completeness metric** (e.g., % of works with ≥10 references) to the corpus metadata.

#### **4. Filtering and False Positives/Negatives**
- **Section 2.2**: The **cross-encoder relevance scoring** (threshold=0.002) is validated at **81% accuracy**, but:
  - **False positives**: The **title blacklist** (e.g., "blockchain," "deep learning") seems arbitrary. Why not **train a classifier** on the validation set instead of hard-coded rules?
  - **False negatives**: The **non-English filtering gap** (41.8% vs. 19.9%) suggests **systematic bias**. Could the **protected status** (e.g., cited ≥50 times) be applied **language-agnostically**?
  - **Section 2.3**: The **stratified validation sample** (100 works) is small. How was the **threshold chosen**? A **precision-recall curve** would help justify it.
  - *Suggestion*: Release a **flagged-but-protected subset** (1,808 works) as a separate file for users who want to **relax filtering**.

#### **5. Institutional Layer and Grey Literature**
- **Section 2.1**: The **institutional reports** (210 works) are a highlight, but:
  - **UNFCCC/OECD documents** have **no DOIs or references** (Table 3). How were these **integrated into the citation network**? If they’re **isolated nodes**, they’re invisible to network analyses.
  - **World Bank API harvest**: How were **duplicates** (e.g., reports published in multiple series) handled? The **near-duplicate detection** (Section 2.2) seems tailored to academic papers.
  - *Suggestion*: Add a **separate citation network for grey literature** (e.g., using report titles + years) to avoid mixing apples (DOI-based) and oranges (non-DOI).

#### **6. Temporal Trends and Structural Breaks**
- **Section 4**: The **2015 structural break** (17% annual growth) is intriguing. Is this driven by:
  - **Policy events** (e.g., Paris Agreement, 2015)?
  - **Keyword adoption** (e.g., "climate finance" spreading post-2009)?
  - **Database coverage** (e.g., OpenAlex indexing more working papers post-2015)?
  - *Suggestion*: Add a **keyword timeline** (e.g., % of works using "climate finance" vs. "green finance" over time) to disentangle **terminology shifts** from **real growth**.

#### **7. Missing Related Work**
- **Section 1**: The paper cites **three prior bibliometric studies**, but misses:
  - **Climate finance systematic reviews** (e.g., [Atteridge & Fonta 2017](https://doi.org/10.1016/j.gloenvcha.2017.06.004) on North-South flows).
  - **Multilingual corpora in other fields** (e.g., [Claveau & Gingras 2021](https://doi.org/10.1007/s11192-020-03710-3) on economics, [Singh et al. 2021](https://doi.org/10.1162/qss_a_00137) on COVID-19).
  - **Grey literature databases** (e.g., [Overton](https://www.overton.io/), [OpenGrey](http://www.opengrey.eu/)).
  - *Suggestion*: Add a **comparison table** of this corpus vs. prior work (e.g., coverage, languages, institutional sources).

---

### **Minor Issues**
- **Table 1**: The **automation level** for "Institutional reports" is listed as "Hybrid," but the description mentions **manual curation** (e.g., "17 selected reports"). Clarify.
- **Section 2.1**: The **teaching canon** is built from **publicly accessible syllabi**. How was **bias toward Global North institutions** addressed? A **geographic breakdown** of syllabi sources would help.
- **Section 2.4**: The **pre-1990 works** (40) are dismissed as metadata errors, but some may be **classics** (e.g., early environmental economics). Could these be **manually reviewed**?
- **Figure 1**: The **community labels** (e.g., "carbon market," "green bonds") are useful, but the **TF-IDF terms** are noisy (e.g., "financial," "climate"). Could **LDA or BERTopic** provide cleaner labels?

---

### **Suggested Experiments/Ablations**
1. **Language bias in embeddings**:
   - Train a **language classifier** on the `bgem3` embeddings. If language is a **confounding factor**, the classifier will achieve high accuracy, suggesting the need for **language-neutral embeddings** (e.g., [LASER](https://github.com/facebookresearch/LASER)).
2. **Citation network robustness**:
   - Randomly **drop 3% of edges** (to simulate citation errors) and rerun **Louvain community detection**. If communities are **stable**, the network is robust.
3. **Filtering sensitivity**:
   - Vary the **cross-encoder threshold** and measure **precision/recall** on a larger validation set (e.g., 500 works). Does the **optimal threshold** differ by language?
4. **Institutional layer integration**:
   - Create a **separate citation network for grey literature** (using report titles + years) and compare its **community structure** to Figure 1.

---

### **Questions for the Authors**
1. **Scope**: How was the **boundary between climate finance and adjacent fields** (e.g., green finance, ESG) decided? Could the **keyword taxonomy** (Tier 1–4) be released as a **dynamic tool** (e.g., interactive visualization) for users to explore?
2. **Multilingual bias**: Why not **translate non-English abstracts to English** before relevance scoring? Would this reduce the **filtering gap** (41.8% vs. 19.9%)?
3. **Citation network**: How sensitive are the **Louvain communities** (Figure 1) to **citation errors** (3%) or **missing references** (20% of works)? Could **fuzzy matching** (e.g., title + year) recover some no-DOI citations?
4. **Institutional layer**: How were **UNFCCC/OECD documents** integrated into the citation network? If they’re **isolated nodes**, how can users analyze them alongside academic literature?
5. **Temporal trends**: What drives the **2015 structural break**? Is it **policy events**, **keyword adoption**, or **database coverage**? Could a **keyword timeline** disentangle these?
6. **Filtering**: Why not **train a classifier** on the validation set instead of using **hard-coded rules** (e.g., title blacklist)? Could the **protected status** (e.g., cited ≥50 times) be applied **language-agnostically**?
7. **Grey literature**: How were **duplicates** in the **World Bank API harvest** handled? Could the **near-duplicate detection** be adapted for reports?
8. **Related work**: Why were **grey literature databases** (e.g., Overton, OpenGrey) not included? Could they be added in a future version?
9. **Reproducibility**: The **abstracts are not included** in the deposit due to **publisher restrictions**. Could a **script** be provided to **fetch abstracts** from OpenAlex/ISTEX at runtime?
10. **Future work**: The paper mentions **OpenAlex bulk download** as a future improvement. How would this change the **query strategy** (e.g., would it enable **full-text search**)?

---

### **One Experiment I Would Run Next**
**Title**: *"Does the citation network reflect language bias?"*
**Design**:
1. Extract the **citation network** (Figure 1) and **language metadata** for each work.
2. Compute **language homophily** (e.g., % of citations within vs. across languages) for each community.
3. Compare to a **null model** (randomized citations). If **homophily is higher than expected**, the network is **language-segregated**.
4. Repeat for **institutional vs. academic works** to test if the **grey literature layer** is isolated.
**Why**: This would quantify whether **multilingual retrieval** actually **integrates** non-English scholarship or just **juxtaposes** it.

---

### **Summary**
This is a **high-impact, reusable dataset** that advances climate finance research by **bridging academic and institutional sources** and **enabling multilingual analysis**. The **transparency** and **reproducibility** are exemplary. The **main limitations**—**language bias in filtering**, **citation network gaps**, and **institutional layer integration**—are **addressable** with the suggested experiments. With minor revisions (e.g., **language-stratified analysis**, **citation robustness checks**), this could become a **benchmark corpus** for climate finance.
