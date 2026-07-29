# Peer review — openai/gpt-5.5, persona: grinchy

## Review

### Recommendation: **Reject**

This paper describes a potentially useful bibliographic corpus, but in its present form it does not meet the standard for a reliable data paper. The central claims—1990–2024 coverage, multilingual retrieval, curated climate-finance relevance, institutional-report inclusion, and reproducible construction—are repeatedly weakened by inconsistencies, ad hoc filtering, circular validation, and insufficiently audited AI/manual components. Several limitations are acknowledged, but merely acknowledging them does not make the dataset fit for the uses claimed in the Introduction and Conclusion.

The paper should be substantially rebuilt around a narrower, defensible claim: an OpenAlex-heavy, English-dominant, keyword-retrieved bibliography with selected institutional additions and imperfect filtering. That would be less marketable, but more accurate.

---

## Major objections

### 1. The dataset does **not** match its stated temporal scope  
**Reference:** Title; Abstract; Sections 2.1, 2.4, 3, 4

The paper repeatedly presents the corpus as covering **1990–2024**, yet Section 2.4 states that **3,278 refined works, 9.8% of the corpus, fall outside that window**, including **3,238 after 2024**. This is not a small edge case; nearly one-tenth of the refined corpus violates the advertised temporal boundary.

The explanation—that year bounds were added partway through collection and the harvest pool is append-only—is not acceptable for a released dataset whose title and abstract specify a fixed period. This is especially problematic because the paper is dated 2026 and cites 2026 collection/probe dates, so the presence of post-2024 works is not a harmless metadata anomaly but a pipeline-design choice.

**What would fix it:**  
Either:

1. Rebuild and release the corpus with a hard post-merge year filter enforcing 1990–2024, and update all counts, tables, embeddings, citations, and validation accordingly; or  
2. Retitle and redescribe the dataset as “1990–2026 harvest with nominal 1990–2024 query window,” and provide a separate strictly 1990–2024 subset as the default release.

As written, the title, abstract, Sections 2.1 and 3, and the actual corpus are inconsistent.

---

### 2. The operational definition of “climate finance” is unstable and overbroad  
**Reference:** Introduction; Sections 2.1, 2.2, 2.3, 4; Figure 1

The Introduction defines climate finance as **North–South financial flows directed at mitigation and adaptation**. But the corpus appears to include much broader literatures: green finance, green bonds, carbon markets, climate policy, environmental economics, econometric methods, and likely generic finance/environment papers. Figure 1’s communities include labels such as “health, climate, finance,” “zoning,” “stock, market,” and “green, innovation,” which do not obviously correspond to the stated North–South climate-finance object.

The paper uses the contested nature of “climate finance” to justify “erring on the side of inclusion,” but this becomes a license for scope drift. A large corpus is not necessarily a better corpus if its inclusion criteria do not match its conceptual definition. The lower overlap with Maria et al. is explained as “scope,” but the paper itself seems to import substantial green-finance material.

**What would fix it:**  
Provide a formal operational definition with inclusion/exclusion rules and validate it against a manually coded benchmark. At minimum, report precision/recall for several strata:

- core climate-finance works;
- green finance / sustainable finance;
- carbon markets;
- adaptation finance;
- institutional negotiation documents;
- unrelated false positives.

The current “climate policy and financial mechanisms” reranker query is too vague to enforce the conceptual boundary.

---

### 3. The retrieval protocol is insufficiently specified in the main paper and appears circular  
**Reference:** Section 2.1; Introduction

The paper says the keyword taxonomy was informed by mining **2,644 core papers cited ≥50 times**. This risks hard-coding the vocabulary of highly cited, older, English-dominant scholarship into the retrieval protocol. That is especially damaging for a paper claiming multilingual and Southern coverage.

The main body also does not give enough detail on the actual query terms, term counts by tier, language distribution by query tier, or retrieval yield by tier. The reader is referred to deposited YAML and CSV files. Supporting files are useful, but a data paper must still expose enough of the retrieval logic for review.

The “eight-language keyword taxonomy” is central to the paper’s novelty, yet the paper does not show:

- the actual eight-language core query terms;
- who translated or validated them;
- whether terms are semantically equivalent across languages;
- how morphology, script variants, and phrase segmentation were handled;
- per-language retrieval yield before and after filtering;
- false-positive and false-negative rates by language.

**What would fix it:**  
Add a table in the main paper giving the retrieval taxonomy at least at the term-family level, with per-tier and per-language counts, raw hits, refined hits, and removal rates. Explain how translations were produced and validated. Add a small multilingual recall audit using known climate-finance works in each target language.

---

### 4. The quality-filtering procedure is ad hoc and undervalidated  
**Reference:** Sections 2.2, 2.3, 2.4; Table 2

The filtering step removes **9,436 records** after applying flags and protection criteria. This is a decisive stage of corpus construction, yet the validation is weak.

The cross-encoder filter is especially problematic:

- It uses a single English query: **“climate policy and financial mechanisms.”**
- The deployed threshold is arbitrary and unstable: halving or doubling it reclassifies about **10%** of the calibration sample.
- Validation uses only **100 works**, stratified by score quintile.
- Per-work grades from this validation were **not retained**, so the main validation cannot be independently audited.
- The model is known to penalize non-English works: Section 2.4 reports that translating the query raises non-English threshold crossing by **11.5 percentage points**.
- At the threshold, reported performance is only **81% accuracy, 74% precision, 76% recall**, which is not strong enough for removing thousands of records without a careful error analysis.

The paper acknowledges some of this, but still uses the filter in the default refined corpus. That is not defensible for a corpus advertised as multilingual.

The protection criteria also introduce citation and source-count bias. Highly cited works, works with within-corpus citations, and works found in multiple sources are protected, while peripheral, recent, non-English, or grey-literature works are more likely to be removed. This directly undermines the claimed purpose of recovering fragmented and multilingual scholarship.

**What would fix it:**  
Make the unfiltered deduplicated corpus the primary dataset and present the refined set as one possible filter. If a refined corpus is retained, build a proper validation set:

- several hundred to several thousand manually labeled records;
- labels retained and deposited;
- stratification by language, source, year, document type, and query tier;
- inter-annotator agreement;
- precision/recall by stratum;
- comparison against simpler baselines.

The cross-encoder should be queried in each work’s language or with multilingual prompts, not only in English.

---

### 5. The multilingual claim is overstated  
**Reference:** Abstract; Introduction; Sections 2.1, 2.4; Table 4; Conclusion

The paper repeatedly emphasizes multilingual retrieval, but the refined corpus is **93.8% English**. The non-English component is only about **6.2%**, and Section 2.4 admits that **41.8% of non-English works are removed**, versus **19.9% of English works**. The cross-encoder contributes substantially to that disparity.

The sources also do not support a serious claim of broad multilingual coverage. There is no CNKI, SciELO, Redalyc, Cairn, Persée, HAL, Dialnet, Latindex, J-STAGE, KCI, Garuda, or other major regional/national infrastructure. bibCNRS contributes only **219 refined records**, with **8% non-English** according to Table 3, which is surprisingly low for the role assigned to it. Institutional UNFCCC/OECD multilingual documents are indexed **only in English**.

The Conclusion says the eight-language retrieval “adds a non-English layer that the English-only queries of prior mappings cannot reach.” That is technically true but too weak to support the paper’s broader multilingual framing.

**What would fix it:**  
Reframe the dataset as English-dominant with limited non-English retrieval. Alternatively, substantially expand multilingual sources and validate recall in each language. Provide language-specific retrieval, filtering, and error statistics. Do not claim meaningful multicultural or Southern coverage without regionally appropriate databases.

---

### 6. The institutional-report layer is too small and too selectively constructed for the claims made  
**Reference:** Abstract; Sections 2.1, 2.4; Table 3; Conclusion

The Abstract emphasizes institutional reports and negotiation records, but Table 3 shows the institutional components are tiny:

- Institutional reports: **210 refined works**
- UNFCCC key documents: **230**
- OECD DAC key documents: **33**

Together this is a small fraction of the corpus. The Abstract says institutional reports and key documents are **1.4%** of the corpus. That is not enough to justify the prominence given to them unless their selection is exhaustive or theoretically central. It is neither.

Section 2.1 says the UNFCCC/OECD classes were fixed empirically by crossing a companion history-of-thought study’s bibliography against the first corpus version and keeping classes cited by that study but missing from the corpus. This is circular: the dataset is partly shaped by the needs and citations of another paper by the same author, then presented as reusable infrastructure.

Section 2.4 further admits that national institutions, central banks, domestic policy bodies, and regional sources are excluded. This is a major omission for climate finance, especially given the claim about multicultural and Southern perspectives.

**What would fix it:**  
Either make the institutional layer a clearly labeled, selective convenience sample, or build a systematic institutional corpus with explicit inclusion criteria, document universe, completeness estimates, and exclusions. The current wording should not imply broad coverage of institutional climate-finance discourse.

---

### 7. Reproducibility is compromised by manual, restricted, proprietary, and AI-assisted components  
**Reference:** Sections 2.1, 3; Table 1

The paper distinguishes automated, hybrid, hand-harvested, AI-collected, and AI-assisted sources. Several are not reproducible in any conventional sense:

- bibCNRS requires CNRS credentials.
- SciSpace is proprietary and “AI-collected, hand-exported.”
- Teaching canon extraction uses scraping plus LLM-assisted extraction.
- UNFCCC is “AI-collected.”
- OECD is hand-harvested.
- The companion technical report, not the main paper, apparently contains key details.

Raw exports are said to be deposited, but reproducibility of the collection process is still limited. More importantly, the AI-assisted components are not independently audited. For example, the teaching canon contributes **618 refined works**, **549 unique**, yet the LLM extraction has “not been independently audited” according to Section 2.4.

**What would fix it:**  
For each non-automated source, provide:

- exact selection protocol;
- date of access;
- complete seed URLs or export criteria;
- extraction prompts if LLMs were used;
- manual validation sample and error rates;
- reproducibility status.

Do not present the pipeline as reproducible without clearly separating reproducible, archived-but-not-reproducible, and non-reproducible components.

---

### 8. The citation graph is overinterpreted and heavily biased toward DOI-bearing academic works  
**Reference:** Sections 2.3, 2.4, 3, 4; Figure 1

The citation network is DOI-based. Yet **24%** of refined works lack DOIs, and the institutional layers have almost no DOI/reference coverage. Table 3 reports **0% references** for UNFCCC and **6%** for OECD. Section 2.4 admits that curated key documents “stay outside the citation network.” Thus, the citation network largely excludes precisely the institutional material the paper claims to add.

The validation is also partly circular. Section 2.3 audits links against Crossref reference lists, but many links were harvested from Crossref/OpenAlex in the first place. The paper acknowledges this but still reports high confirmation figures prominently. Agreement with Crossref is not ground-truth citation accuracy.

The internal citation graph connects only **13,112 works**, **39% of the corpus**. Figure 1 therefore visualizes a minority, DOI-heavy, academic subset, not the corpus as a whole. Its use as a “global map of climate finance scholarship” is misleading.

**What would fix it:**  
Rename the network as a DOI-resolved academic citation subgraph. Provide coverage by document type, language, year, and source. Do not use Figure 1 as evidence of the structure of the full corpus. If institutional documents matter, add non-DOI citation/reference extraction or avoid claims about their network role.

---

### 9. The comparison to prior bibliometric studies is not a valid coverage benchmark  
**Reference:** Introduction

The Introduction reports that the corpus contains **89.3%** of works retrieved by Carè and Weber’s query and **91.0%** for Shang and Jin’s query, based on replicating their published queries against OpenAlex. But those studies used Scopus and Web of Science. The paper admits that the comparison absorbs OpenAlex coverage gaps and query-translation drift, then nevertheless treats the results as approximating overlap with the records those authors analyzed.

This is too loose. It is not a benchmark against the original study datasets; it is a benchmark against OpenAlex’s interpretation of their query strings. It says little about coverage of Scopus/WoS records, especially for non-English and grey literature.

**What would fix it:**  
Either obtain or reconstruct the actual bibliographies from the prior papers and compare directly, or present this as a limited query-probe without implying recall against prior datasets. Also report false positives, not just overlap.

---

### 10. Deduplication is fragile and its known errors are not adequately handled  
**Reference:** Sections 2.2, 2.4; Tables 2 and 3

The deduplication pipeline uses DOI matching and title+year matching. Later, enrichment reveals additional duplicate DOIs, and **399** are removed after quality filtering. This ordering is odd: duplicate handling after filtering can change which metadata survives and which records are protected or flagged.

Section 2.4 admits surviving working-paper/published-version pairs, over-merges, unrelated DOI groups, and noisy author metadata. Fuzzy title matching raises candidate duplicate/version pairs to **1,329 works**, or **4.0%** of the corpus. That is not negligible for bibliometric analysis.

The paper says near-duplicate publications are kept because they are “real publications.” That may be true, but users need clear guidance because these records can distort publication counts, citation counts, co-citation, and community detection.

**What would fix it:**  
Reorder the pipeline so enrichment and all DOI normalization occur before filtering. Provide canonical-work clusters distinct from publication records. Include recommended deduplicated views for bibliometrics, citation analysis, and textual analysis. Quantify how dedup choices affect the headline counts and Figure 1 communities.

---

### 11. The paper claims readiness for downstream tasks that the data do not robustly support  
**Reference:** Introduction; Sections 3, 5

The Introduction and Conclusion advertise uses for topic modelling, citation network analysis, bibliometric mapping, institutional/co-author networks, and non-English case studies. Several of these claims are premature:

- Topic modeling from embeddings computed using abstracts that are **not deposited** is not fully reproducible.
- Citation network analysis excludes no-DOI works and institutional documents.
- Co-author/institutional networks rely on noisy metadata, with no validation reported.
- Non-English analysis is compromised by language imbalance and biased filtering.
- Institutional analysis is based on a small selected sample.

A data paper should not merely list attractive downstream uses. It should establish that the dataset is fit for them.

**What would fix it:**  
For each claimed use case, state the appropriate subset and limitations. Add validation of affiliations/authors if institutional networks are advertised. Provide reproducibility guidance for embeddings given abstract redistribution restrictions and index drift.

---

### 12. Figure 1 does not earn its centrality and is visually/inferentially weak  
**Reference:** Section 4; Figure 1

Figure 1 is hard to read, labels are tiny, and the layout is explicitly “indicative.” It covers only the connected DOI-matched internal citation subgraph, i.e., **39% of the corpus**. It is therefore not a “global map” of climate-finance scholarship, despite the figure title.

The community labels are top TF-IDF terms, many of which are vague or uninformative. The figure gives no uncertainty, robustness check, sensitivity to missing citations, or comparison with semantic clusters. Since the corpus is a data product, a table with community size, top works, top venues, year distribution, and source/language composition would be far more useful.

**What would fix it:**  
Replace or supplement Figure 1 with a table of communities and coverage statistics. Rename it as a DOI-resolved internal citation subgraph. Provide robustness to alternative community detection seeds/resolutions and to excluding review articles or high-degree nodes.

---

## Additional issues and corrections

1. **Abstract and Section 5 overclaim “institutional vocabulary and negotiation records absent from academic indexes.”**  
   The corpus adds some such records, but only selectively and in English for multilingual UNFCCC/OECD documents. Rephrase.

2. **Section 2.1: “default.search field matches title, abstract, and indexed fulltext.”**  
   OpenAlex indexed fulltext coverage is uneven. The paper should quantify how much retrieval likely came from title/abstract versus fulltext, if possible.

3. **Section 2.2: title blacklist terms such as “blockchain” or “deep learning.”**  
   These are not inherently irrelevant to climate finance. The rule risks excluding legitimate work on climate-finance fintech, AI-based climate-risk assessment, etc. Provide examples of false removals and retained protected cases.

4. **Section 2.3: AUC derivation from quintile rates is underdescribed.**  
   Saying the quintile rates “alone fix” AUC is too glib. Report the exact calculation and confidence intervals, preferably from retained item-level labels.

5. **Section 2.4: “metadata coverage does not explain the gap, since non-English works have higher abstract coverage.”**  
   This does not rule out metadata-quality differences, abstract length differences, language detection errors, source composition, or query-tier composition. The causal statement that “the scorer itself does” needs more evidence.

6. **Section 3: abstracts are not deposited, but embeddings are.**  
   The paper needs a clearer discussion of whether embeddings derived from copyrighted abstracts are redistributable and whether they can leak text. This is a known issue for text-derived datasets.

7. **Section 3: raw exports from restricted platforms are included under CC BY 4.0.**  
   The paper should explicitly address licensing/redistribution rights for bibCNRS, SciSpace exports, and other restricted metadata.

8. **Table 5 has apparent formatting/name errors.**  
   “climate_finance Corpus.csv” and “near Duplicate_group” appear inconsistent with machine-readable variable names. Such sloppiness matters in a data paper.

9. **Section 4: structural break claim is not well supported.**  
   A Chow test on log annual counts from a constructed, evolving retrieval corpus is not strong evidence of a real field-level break. Query vocabulary, database indexing, and collection changes confound this. The figure is not even included, only said to appear in a companion study.

10. **References are too thin.**  
   For a data paper on bibliographic corpus construction, multilingual retrieval, OpenAlex coverage, deduplication, citation graph limitations, and grey-literature harvesting, five references are inadequate. The related work is shallow and mostly limited to three bibliometric climate/green-finance papers.

---

## Required revisions if resubmitted

1. Release and analyze a strictly compliant 1990–2024 corpus, or change the title/scope.  
2. Provide a transparent operational definition of climate finance and validate inclusion/exclusion decisions.  
3. Replace the current relevance-filter validation with a retained, auditable, multilingual manually labeled benchmark.  
4. Reframe the multilingual claim or expand multilingual sources substantially.  
5. Separate systematic sources from selective/curated/AI-assisted sources in all claims and tables.  
6. Rework citation-network claims around the DOI-resolved academic subset only.  
7. Add licensing and reproducibility documentation for restricted and AI-assisted components.  
8. Provide stronger related work on bibliographic database coverage, corpus construction, grey literature, multilingual scholarly retrieval, and bibliometric deduplication.

---

## The 3 things that most threaten the paper’s central claim

1. **The corpus is advertised as 1990–2024 but contains 9.8% out-of-window refined records, mostly post-2024.**  
   This directly invalidates the title, abstract, and temporal analyses.

2. **The multilingual relevance filtering is biased and weakly validated, removing non-English works at much higher rates.**  
   This undermines the claimed multilingual contribution.

3. **The scope of “climate finance” is conceptually unstable and empirically overbroad.**  
   The dataset appears to mix climate finance, green finance, carbon markets, generic environmental economics, and adjacent finance literatures without a validated boundary.
