# Peer review — mistralai/mistral-large-2512, persona: grinchy

**Peer Review Report**
**Manuscript:** *A Curated Multi-Source Corpus of Climate Finance Literature, 1990–2024: Multilingual Retrieval and Institutional Reports*
**Recommendation:** **Major Revision**

This paper presents a large, multilingual corpus of climate finance literature, assembled from eight sources and subjected to a documented pipeline of deduplication, filtering, and enrichment. The dataset is a valuable contribution to the field, particularly for its inclusion of non-English and institutional documents, and its potential reuse in bibliometric, historical, and semantic analyses. However, the paper suffers from several critical weaknesses that undermine its claims, methodological rigor, and usability. Below is a prioritized list of concrete objections, followed by the three most serious threats to the paper’s central claim.

---

### **Prioritized Objections**

#### **1. Overclaims and Unsupported Generalizations (Introduction, Section 1)**
**Issue:** The paper repeatedly overstates the novelty and comprehensiveness of the corpus while downplaying its limitations.
- **Claim:** *"The present work addresses these limitations: a climate finance corpus built from 8 complementary sources, with a documented quality-filtering pipeline, searched in eight languages, and embedded with a sentence-transformer..."*
  - **Problem:** The corpus is *not* comprehensive. It excludes national institutional reports (e.g., central bank communications, government reports), regional databases (e.g., CNKI, SciELO, Garuda), and media discourse. The "multilingual" aspect is superficial: 93.8% of the corpus is English, and non-English works are disproportionately flagged for removal (41.8% vs. 19.9% for English). The paper does not justify why these exclusions are acceptable for a "multilingual" corpus.
  - **Fix:** Rewrite the Introduction to:
    1. Clearly define the *scope* of the corpus (e.g., "focused on international climate finance governance, with limited non-English coverage").
    2. Acknowledge that the corpus is *not* representative of global scholarship or policy discourse.
    3. Remove unsupported claims about "multilingual retrieval" unless the non-English coverage is expanded or justified.

- **Claim:** *"The dataset was constructed for a history-of-economic-thought study... but its scope makes it reusable for topic modelling, citation network analysis, bibliometric mapping, and case studies..."*
  - **Problem:** The paper does not demonstrate reusability. For example:
    - The citation network excludes 24% of works (no DOIs) and 61% of works lack references (Table 3). The paper does not test whether network analyses (e.g., community detection in Figure 1) are robust to these exclusions.
    - The embeddings are confounded by language (Section 2.4: "vectors still carry the language-specific confound"). The paper does not show that the embeddings are useful for cross-lingual tasks (e.g., clustering non-English works).
  - **Fix:** Add a section demonstrating *specific* reuse cases (e.g., "Topic modeling of English vs. non-English works" or "Sensitivity of citation communities to DOI exclusions"). Without this, the claim is hand-wavy.

#### **2. Methodological Holes (Section 2.1–2.2)**
**Issue:** The retrieval and filtering pipeline has critical gaps that are not addressed or justified.
- **Keyword Taxonomy (Section 2.1):**
  - **Problem:** The taxonomy is *retrospective* (mined from highly cited papers) and thus circular: it embeds the field’s existing vocabulary, making it unsuitable for studying the *emergence* of climate finance. The paper acknowledges this ("dating the field’s turns from this corpus alone partly re-measures the taxonomy") but does not mitigate it.
  - **Fix:** Either:
    1. Use a *prospective* taxonomy (e.g., terms from UNFCCC negotiation records or policy documents) to avoid circularity, or
    2. Justify why a retrospective taxonomy is acceptable for the intended use cases (e.g., "this corpus is designed for studying established climate finance, not its origins").

- **Deduplication (Section 2.2):**
  - **Problem:** The paper admits that "some working paper / published version pairs still slip through" (344 pairs, 1.0% of works) and that "fuzzy title matching raises the upper bound to 1,329 works (4.0%)." These duplicates inflate citation counts and distort network analyses (e.g., co-citation statistics). The paper does not quantify the impact of this bias.
  - **Fix:** Add a sensitivity analysis showing how citation-based metrics (e.g., community detection in Figure 1) change when duplicates are removed. Alternatively, justify why the bias is negligible.

- **Relevance Filtering (Section 2.2–2.3):**
  - **Problem:** The cross-encoder relevance filter is validated on a *stratified* sample (by score quintile), but the stratification is not independent of the filter itself. The reported AUC (0.818) is likely optimistic because:
    1. The validation sample is small (n=100) and not representative of the full corpus (e.g., non-English works are underrepresented).
    2. The "human-relevant" labels are not retained (only per-quintile rates are reported), so the validation cannot be replicated.
    3. The filter disproportionately removes non-English works (58.9% of non-English removals are due to the cross-encoder flag). The paper attributes this to "query language rather than topical relevance" but does not test whether the filter is biased against non-English works.
  - **Fix:**
    1. Release the per-work human relevance labels for the validation sample.
    2. Test the filter on a *random* sample (not stratified by score) to estimate unbiased accuracy.
    3. Report precision/recall separately for English and non-English works.

#### **3. Missing or Shallow Related Work (Introduction, Section 1)**
**Issue:** The paper cites only three prior bibliometric studies (*Carè and Weber, 2023; Shang and Jin, 2023; Maria et al., 2023*) and ignores broader literature on:
- Multilingual corpora (e.g., *Singh et al., 2022* on cross-lingual bibliometrics).
- Institutional document retrieval (e.g., *Hajjem et al., 2014* on grey literature in climate policy).
- Corpus construction methodologies (e.g., *Waltman et al., 2012* on deduplication; *Boyack et al., 2018* on citation network validation).
- **Fix:** Add a dedicated "Related Work" subsection comparing the corpus to:
  1. Other multilingual corpora (e.g., *OpenAlex’s* language coverage, *Microsoft Academic Graph’s* non-English retrieval).
  2. Institutional document collections (e.g., *Overton* for policy documents, *UN iLibrary* for UNFCCC/OECD reports).
  3. Methodological best practices (e.g., *Waltman and van Eck, 2012* on citation network validation).

#### **4. Statistical Weaknesses and Confounds (Section 2.3–2.4)**
**Issue:** The paper reports statistics without addressing key confounds or testing robustness.
- **Citation Network Validation (Section 2.3):**
  - **Problem:** The citation network is validated against Crossref, but Crossref is itself incomplete (especially for books, chapters, and older articles). The paper does not test whether the network is robust to:
    1. Missing references (20% of DOI-bearing works contribute no outgoing edges).
    2. No-DOI works (24% of the corpus is excluded from the network).
  - **Fix:** Add a sensitivity analysis showing how network metrics (e.g., community structure in Figure 1) change when:
    1. No-DOI works are included (via fuzzy matching of titles/authors).
    2. Works with no outgoing edges are excluded.

- **Language Bias (Section 2.4):**
  - **Problem:** The paper acknowledges that the cross-encoder filter is biased against non-English works but does not quantify the impact. For example:
    - Are non-English works systematically scored lower, or are they just less likely to match the English query?
    - Does the bias affect downstream analyses (e.g., topic modeling)?
  - **Fix:** Add a table comparing the distribution of relevance scores for English vs. non-English works, and test whether the bias persists when non-English works are scored against translated queries.

- **Temporal Bias (Section 2.4):**
  - **Problem:** The corpus includes 3,278 works (9.8%) outside the 1990–2024 window, including metadata errors (e.g., placeholder year 1970). The paper does not test whether these errors affect temporal analyses (e.g., the "structural break" in 2015).
  - **Fix:** Re-run the Chow test (Section 4) after excluding works outside the 1990–2024 window and report whether the break persists.

#### **5. Figures/Tables That Do Not Earn Their Space (Section 3–4)**
**Issue:** Several figures and tables are redundant, poorly labeled, or lack context.
- **Figure 1 (Citation Network Communities):**
  - **Problem:** The figure is visually cluttered and lacks interpretability. Specific issues:
    1. The community labels (e.g., "institutions, financing, tr=1.4239") are opaque. What do "tr" and the numeric values mean?
    2. The layout is "indicative" (distances carry no meaning), but the figure does not explain this clearly.
    3. The figure does not show how the communities relate to the corpus’s sources (e.g., are UNFCCC/OECD documents clustered separately?).
  - **Fix:**
    1. Replace the TF-IDF labels with interpretable names (e.g., "Carbon Markets" instead of "emissions, trading, carbon").
    2. Add a legend explaining "tr" and the numeric values.
    3. Add a panel showing the distribution of sources across communities.

- **Table 3 (Corpus Sources):**
  - **Problem:** The table is dense and hard to interpret. Key issues:
    1. The "Unique" column is misleading: it counts works *only* in that source, but the "TOTAL" row is the deduplicated union. This makes it seem like OpenAlex contributes 30,815 unique works, but the actual number of unique works is 32,606.
    2. The "%non-EN" column is not explained in the caption (e.g., is it the share of non-English works *among that source’s refined works*?).
  - **Fix:**
    1. Clarify the "Unique" column (e.g., "Works found only in this source").
    2. Add a column showing the *share* of each source’s refined works that are unique (e.g., 30,815/31,544 = 97.7% for OpenAlex).
    3. Explain "%non-EN" in the caption.

- **Table 4 (Language Distribution):**
  - **Problem:** The table is redundant with Table 3 and does not add value. It also does not show how language distribution varies by source (e.g., are non-English works concentrated in bibCNRS?).
  - **Fix:** Either:
    1. Remove the table and reference Table 3, or
    2. Replace it with a table showing language distribution *by source* (e.g., "%non-EN" for each source’s refined works).

#### **6. Vague or Hand-Wavy Passages (Section 2.4, 4, 5)**
**Issue:** Several sections lack specificity or defer critical details to external files.
- **Institutional Reports (Section 2.1):**
  - **Problem:** The paper states that the institutional-reports source "samples rather than surveys institutional writing" but does not justify the sampling criteria. Why were 17 reports selected? Why exclude national institutions?
  - **Fix:** Add a table listing the 17 reports and the inclusion criteria (e.g., "documents cited in [Ha-Duong, under review]").

- **Embeddings (Section 3):**
  - **Problem:** The paper claims the embeddings "feed topic models and content classification" but does not demonstrate this. The embeddings are confounded by language, and the paper does not show that they are useful for cross-lingual tasks.
  - **Fix:** Add a brief analysis showing:
    1. Whether the embeddings cluster works by topic *across languages* (e.g., do Portuguese and English works on "green bonds" cluster together?).
    2. How the embeddings compare to a monolingual baseline (e.g., English-only embeddings).

- **Temporal Analysis (Section 4):**
  - **Problem:** The paper mentions a "structural break in 2015" but does not show the data or the Chow test results. The companion paper is cited, but the figure should be included here.
  - **Fix:** Add a figure showing the annual publication volume with the structural break highlighted.

#### **7. Gap Between Claims and Evidence (Throughout)**
**Issue:** The paper claims the corpus is reusable for specific tasks (e.g., topic modeling, citation analysis) but does not demonstrate this.
- **Example 1:** The paper claims the corpus is useful for "case studies of scholarship published outside English" (Section 1), but:
  - Non-English works are only 6.2% of the corpus.
  - 41.8% of non-English works are removed by the filter.
  - The embeddings are confounded by language.
  - **Fix:** Add a case study showing how the corpus can be used for non-English analysis (e.g., "Topic modeling of Portuguese works on climate finance").

- **Example 2:** The paper claims the citation network is useful for "bibliometric mapping" (Section 1), but:
  - 24% of works are excluded from the network (no DOIs).
  - 61% of works lack references (Table 3).
  - The network is validated against Crossref, which is itself incomplete.
  - **Fix:** Add a sensitivity analysis showing how network metrics (e.g., community structure) change when no-DOI works are included.

---

### **Three Most Serious Threats to the Central Claim**
The central claim of the paper is that this corpus is a *reusable, multilingual, and comprehensive* resource for studying climate finance. The three biggest threats to this claim are:

1. **Language Bias Undermines "Multilingual" Claim**
   - The corpus is 93.8% English, and non-English works are disproportionately removed by the relevance filter. The paper does not show that the remaining non-English works are sufficient for cross-lingual analysis or that the embeddings are useful for multilingual tasks. Without addressing this, the "multilingual" label is misleading.

2. **Circular Taxonomy Limits Historical Analysis**
   - The keyword taxonomy is mined from highly cited papers, making it unsuitable for studying the *emergence* of climate finance. This undermines the paper’s claim that the corpus is useful for "history-of-economic-thought" studies. The paper must either use a prospective taxonomy or justify why a retrospective one is acceptable.

3. **Citation Network Exclusions Distort Bibliometric Analyses**
   - The citation network excludes 24% of works (no DOIs) and 61% of works lack references. The paper does not test whether network analyses (e.g., community detection) are robust to these exclusions. Without this, the claim that the corpus is useful for "citation network analysis" is unsupported.

---

### **Final Recommendation**
**Major Revision.** The paper has the potential to be a valuable resource, but its current version suffers from overclaims, methodological gaps, and insufficient validation. The authors must:
1. Clearly define the scope and limitations of the corpus (e.g., "focused on international climate finance governance, with limited non-English coverage").
2. Address the language bias (e.g., validate the embeddings for cross-lingual tasks, test the relevance filter on non-English works).
3. Demonstrate the reusability of the corpus for specific tasks (e.g., topic modeling, citation analysis).
4. Fix the methodological holes (e.g., deduplication, citation network validation).
5. Improve the clarity and interpretability of figures/tables.

Without these changes, the paper’s central claim—that this corpus is a reusable, multilingual resource—is not supported by the evidence.
