# Peer review — mistralai/mistral-large-2512, persona: student

This is a **strong, well-documented data paper** that makes a clear contribution to the study of climate finance. The **novelty and utility** lie in:
- **Multilingual, multi-source integration** (8 sources, 8 languages), going beyond prior single-database, English-only studies.
- **Reproducible, auditable pipeline** with quality flags, deduplication, and provenance tracking—rare in bibliometric work.
- **Grey literature inclusion** (UNFCCC, OECD, teaching syllabi), capturing institutional and pedagogical perspectives often missing from academic databases.
- **Pre-computed embeddings and citation networks**, enabling immediate reuse for topic modeling, network analysis, and cross-lingual studies.

The paper is **transparent about limitations** (e.g., OpenAlex metadata gaps, non-English underrepresentation) and **explicit about biases** (e.g., exclusion of national grey literature). The **companion technical report** and **Zenodo deposit** are models of reproducibility.

---

### **Sharp Questions and Critiques**

#### **1. Methodological Rigor and Pipeline Design**
**Section 2.1–2.2: Keyword Taxonomy and Circularity**
- The **four-tier keyword taxonomy** is built from "core papers" (cited ≥50 times), which risks **circularity**: the corpus may reflect the vocabulary of highly cited works, not the field’s full diversity. How would the corpus change if the taxonomy were built from a random sample or from non-English sources?
- The **retrospective design** ("mined from the vocabulary the field settled on") embeds the negotiation calendar into the harvest. This is acknowledged (p. 4), but the **implications for temporal analysis** are underexplored. For example:
  - Does the **2015 structural break** (Fig. 1) reflect a real shift in the field, or is it an artifact of the taxonomy’s alignment with the Paris Agreement?
  - Could the **pre-2007 underrepresentation** (Fig. 1) stem from the taxonomy’s lack of early climate finance terms (e.g., "environmental finance" or "development aid")?

**Suggested ablation**: Run the pipeline with a **prospective taxonomy** (e.g., terms from UNFCCC glossaries or early climate finance reports) and compare the temporal distribution.

---

**Section 2.2: Quality Filtering and Protection Criteria**
- The **six-flag filtering pipeline** is innovative, but the **protection criteria** (citation count ≥50, multi-source presence, etc.) may **bias the corpus toward established works**. For example:
  - **Citation isolation (flag 4)** removes pre-2020 works with no corpus citations, which could **erase early or niche contributions** (e.g., foundational but uncited policy reports).
  - **Cross-encoder relevance scoring (flag 6)** uses a fixed threshold, but the **calibration sample (100 works)** is small. How sensitive are the results to threshold choice? The paper notes that halving/doubling the threshold reclassifies ~10% of the sample, but this could have **large downstream effects** (e.g., on topic modeling or citation networks).
- The **teaching canon** is a creative inclusion, but its **LLM extraction step** is unaudited. How many syllabi were scraped? What was the precision/recall of the LLM extraction? Could this introduce **institutional bias** (e.g., overrepresenting Western universities)?

**Suggested experiment**: Release a **flagged-but-protected subset** (e.g., works with citation isolation but high relevance scores) for users to audit.

---

**Section 2.3: Deduplication and Citation Network**
- **DOI-based deduplication** is standard, but **title+year matching** (for works without DOIs) is error-prone. The paper acknowledges **38 DOI groups with unrelated titles** and **18 over-merged empty-year works** (p. 8). These errors could **distort citation networks** (e.g., merging distinct works) or **temporal trends** (e.g., misdating works).
- The **citation network** relies on **DOI matching**, but **24% of works lack DOIs** (Table 2). This creates a **systematic bias** against:
  - **Early works** (pre-2000s, when DOIs were rare).
  - **Grey literature** (e.g., UNFCCC/OECD reports, which often lack DOIs).
  - **Non-English works** (Table 3 shows lower DOI coverage for non-English sources).
- The **GROBID parsing** of reference strings is a clever workaround, but it operates on **deposited reference strings**, not full texts. This means:
  - **Missing references**: If a work’s references aren’t deposited in Crossref/OpenAlex, they’re lost.
  - **Noisy references**: GROBID may misparse free-text references (e.g., "Smith (2010)" without a DOI).

**Suggested ablation**: Compare the **citation network** with and without **DOI-less works** to quantify the bias.

---

#### **2. Representation and Bias**
**Section 2.1: Source Coverage and Gaps**
- **OpenAlex dominates** (94.6% of refined works; Table 2), raising questions about **source complementarity**:
  - The **bibCNRS** source (non-English discourse) contributes only **219 works** (0.7% of the corpus). Is this sufficient for **cross-lingual analysis**, or is it a token inclusion?
  - The **grey literature** source excludes **national institutions** (e.g., central banks, government reports), which are **critical for Southern perspectives**. The paper justifies this as a **tractability choice** (p. 7), but the **trade-off** (exclusion of multicultural coverage) is not quantified. How many works would be added by including, e.g., **CNKI (China) or SciELO (Latin America)**?
- **Language distribution** (Table 3) shows **89.9% English**, despite targeting 8 languages. This reflects **structural biases in indexing**, but the paper could **probe deeper**:
  - Are **non-English works** concentrated in specific sources (e.g., bibCNRS) or topics (e.g., regional case studies)?
  - Do **multilingual embeddings** (Fig. 3) cluster works by **language or topic**? The paper claims the embeddings "group works by topic rather than language" (p. 9), but this is not tested. A **language-topic heatmap** would clarify.

**Suggested experiment**: Run **topic modeling separately for English vs. non-English works** to check for **topic-language alignment**.

---

**Section 2.4: OpenAlex Limitations**
- The paper **thoroughly documents OpenAlex’s flaws** (e.g., missing abstracts, noisy citations) and the pipeline’s responses, but **some gaps remain**:
  - **Working paper/version pairs**: The pipeline identifies **344 candidate pairs** (1% of works), but **fuzzy matching raises this to 1,329 (4%)**. These could **inflate citation counts** (double-counting) or **distort co-citation networks**. How would **removing these pairs** affect the **citation communities** (Fig. 2)?
  - **Author metadata noise**: The paper notes that **author-normalized deduplication** is left to future work (p. 8). This could **bias co-authorship networks** (e.g., splitting a single author into multiple nodes).

**Suggested ablation**: Compare **citation networks** with and without **fuzzy-matched version pairs**.

---

#### **3. Descriptive Statistics and Validation**
**Section 4: Temporal Trends (Fig. 1)**
- The **structural break in 2015** (Chow test, p. 3) is compelling, but the **dark segments** ("climate finance" in title/abstract) suggest a **vocabulary shift**. Could this reflect:
  - **Terminology adoption** (e.g., "climate finance" replacing "environmental finance")?
  - **Indexing bias** (e.g., OpenAlex adding more grey literature post-2015)?
- The **three periods** (Before, Crystallisation, Established) are **plausible but arbitrary**. Why these cutoffs? The paper cites **UNFCCC milestones** (Rio, Bali, Paris), but:
  - **Bali (2007)** is less prominent in climate finance than, e.g., **Copenhagen (2009)** or the **Green Climate Fund (2010)**.
  - The **pre-2007 period** is labeled "Before," but it includes **Kyoto (1997)** and early carbon markets.

**Suggested analysis**: Test **alternative periodizations** (e.g., 1990–2005, 2006–2012, 2013–2024) to check robustness.

---

**Section 4: Citation Communities (Fig. 2)**
- The **Louvain communities** are **intuitive** (e.g., "carbon markets," "green bonds"), but:
  - The **layout is force-directed**, so **distances are uninformative**. Why not use a **temporal layout** (e.g., works positioned by year) to show **community evolution**?
  - The **edge weights** (citation counts) are not normalized, so **older communities** (e.g., "carbon markets") may appear larger due to **cumulative citations**.
  - The **16% of unconnected works** are excluded from the map. Are these **grey literature** or **non-English works**? Their exclusion could **bias the narrative**.

**Suggested visualization**: A **Sankey diagram** showing **community shifts over time**.

---

**Section 4: Thematic Clusters (Fig. 3)**
- The **k-means clusters** (k=6) recover **five of six themes** from the companion study, but:
  - The **land-use cluster** replaces the **$100bn/fund-flows theme**. Is this a **real shift** (e.g., land-use finance gaining prominence) or an **artifact of the embedding model**?
  - The **stability metric** (adjusted Rand index ≥0.838) is high, but **k=6 is arbitrary**. How do the clusters change for **k=5 or k=7**?
  - The **exclusion of boilerplate abstracts** (p. 11) could **bias the clusters** toward academic works (which have cleaner abstracts).

**Suggested ablation**: Compare clusters **with and without boilerplate abstracts**.

---

#### **4. Reusability and Future Work**
**Section 3: Data Description**
- The **Zenodo deposit** is **well-structured**, but:
  - **Abstracts are not included** due to "publisher redistribution restrictions" (p. 9). This is understandable, but it **limits reuse** (e.g., users must re-fetch abstracts from OpenAlex, which may drift over time). Could the authors **negotiate with publishers** for a **restricted-access version**?
  - The **citation network** (citations.csv) is **DOI-based**, so **24% of works are excluded**. Could the authors **release a version with GROBID-parsed references** (even if noisy) to improve coverage?
- The **multilingual embeddings** are a **major asset**, but:
  - The **model (BAAI/bgem3)** is **English-centric** (despite supporting 5 languages). How well does it handle **low-resource languages** (e.g., Indonesian, Arabic)?
  - The **embeddings are L2-normalized**, which is standard, but **cosine similarity** may not be the best metric for **cross-lingual comparison**. Have the authors tested **alternative metrics** (e.g., cross-lingual retrieval performance)?

**Suggested experiment**: Evaluate the embeddings on a **cross-lingual retrieval task** (e.g., "find the French equivalent of this English paper").

---

**Section 5: Concluding Remarks**
- The paper argues that the corpus **"turns the definition of 'climate finance' from a hidden assumption into an object of analysis"** (p. 12). This is **compelling**, but the **boundaries are still fuzzy**:
  - The **exclusion of "pure green finance"** (p. 2) is justified, but the **40.1% overlap with *Maria et al. (2023)*** (which includes green finance) suggests **ambiguity**. How would the corpus change if **green finance terms** (e.g., "sustainable finance") were included?
  - The **grey literature exclusion of national institutions** (p. 7) is a **major omission**. Could the authors **release a "national grey literature" extension** (e.g., using CNKI or SciELO)?

---

### **Related Work Missing**
1. **Bibliometric studies of climate finance in non-English contexts**:
   - *Zhang et al. (2022)* on **Chinese climate finance literature** (CNKI database).
   - *SciELO-based studies* of **Latin American green finance** (e.g., *Banco Interamericano de Desarrollo, 2021*).
2. **Multilingual bibliometrics**:
   - *Glänzel et al. (2019)* on **cross-lingual citation networks**.
   - *Chavarro et al. (2017)* on **non-English science in Web of Science**.
3. **Grey literature in bibliometrics**:
   - *Schöpfel et al. (2020)* on **grey literature in OpenAlex**.
   - *Farace & Schöpfel (2010)* on **grey literature in policy research**.

---

### **One Experiment to Run Next**
**Cross-lingual topic alignment**:
- **Goal**: Test whether the **multilingual embeddings** align topics across languages.
- **Method**:
  1. Train **BERTopic** separately on **English vs. non-English works**.
  2. Compare the **topic distributions** (e.g., does "green bonds" in English align with "obligaciones verdes" in Spanish?).
  3. Use **cross-lingual retrieval** (e.g., "find the top 5 non-English papers most similar to this English paper") to evaluate alignment.
- **Why**: This would **validate the embeddings’ utility for cross-lingual analysis** and identify **language-specific gaps** (e.g., topics missing in non-English literature).

---

### **Numbered List of Questions for the Authors**
1. **Keyword taxonomy circularity**:
   - How would the corpus change if the taxonomy were built from a **random sample** or **non-English sources** instead of highly cited papers?
   - Could the **2015 structural break** (Fig. 1) be an artifact of the taxonomy’s alignment with the Paris Agreement?

2. **Quality filtering sensitivity**:
   - How sensitive are the **topic clusters** (Fig. 3) and **citation communities** (Fig. 2) to the **cross-encoder relevance threshold**? Would halving/doubling the threshold change the results meaningfully?
   - Why were **pre-2020 works with no corpus citations** (flag 4) removed? Could this erase **early or niche contributions**?

3. **Deduplication errors**:
   - How would **removing the 38 DOI groups with unrelated titles** and **18 over-merged empty-year works** affect the **citation network**?
   - Could the authors **release a version of the citation network with GROBID-parsed references** to improve coverage of DOI-less works?

4. **Non-English representation**:
   - Are **non-English works** concentrated in specific **sources** (e.g., bibCNRS) or **topics** (e.g., regional case studies)?
   - Do the **multilingual embeddings** cluster works by **language or topic**? Could the authors provide a **language-topic heatmap**?

5. **Grey literature gaps**:
   - How many works would be added by including **national grey literature** (e.g., CNKI for China, SciELO for Latin America)?
   - Could the authors **release a "national grey literature" extension** to the corpus?

6. **Temporal periodization**:
   - Why were **2007 and 2015** chosen as cutoffs? Would **alternative periodizations** (e.g., 1990–2005, 2006–2012, 2013–2024) change the **thematic shifts** (Fig. 3)?

7. **Citation network biases**:
   - How would the **citation communities** (Fig. 2) change if **DOI-less works** were included via GROBID parsing?
   - Are the **16% of unconnected works** primarily **grey literature** or **non-English works**? How does their exclusion bias the narrative?

8. **Thematic cluster robustness**:
   - Why does the **land-use cluster** replace the **$100bn/fund-flows theme** in the k-means results? Is this a **real shift** or an **artifact of the embedding model**?
   - How do the clusters change for **k=5 or k=7**? Is **k=6** the most stable choice?

9. **Reusability limitations**:
   - Could the authors **negotiate with publishers** to release a **restricted-access version** of the corpus with abstracts?
   - How well do the **multilingual embeddings** handle **low-resource languages** (e.g., Indonesian, Arabic)? Could the authors evaluate them on a **cross-lingual retrieval task**?

10. **Green finance boundary**:
    - How would the corpus change if **green finance terms** (e.g., "sustainable finance") were included? Would this **increase overlap with *Maria et al. (2023)***?
