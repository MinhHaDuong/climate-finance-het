# Peer review — openai/gpt-5.5, persona: grinchy

## Review

### Summary

The paper describes a curated corpus of 33,344 works on climate finance from 1990–2024, assembled from OpenAlex plus several smaller academic, grey-literature, institutional, teaching, and AI-assisted sources. It claims multilingual retrieval, broader coverage than single-source bibliometric studies, deduplication and filtering, citation-network construction, and multilingual embeddings.

The idea is potentially useful, but the paper in its current form does not provide a sufficiently reliable, transparent, or internally consistent account of the dataset. Several numerical inconsistencies, unresolved scope problems, under-specified filtering decisions, and unsupported claims about multilinguality, completeness, and citation structure undermine the central contribution. For a data paper, the dataset boundary and construction process are the paper. Here they remain too opaque and, in places, contradictory.

### Recommendation: **Reject**

A substantially revised version could be considered if the authors fully specify the search and filtering protocol, repair the inconsistencies in counts and formulas, provide proper validation of inclusion/exclusion decisions, and substantially narrow or substantiate the multilingual and grey-literature claims.

---

## Major objections

### 1. The corpus boundary is conceptually unstable and operationally under-defined  
**Sections:** 1, 2.1, 2.2, 4; Figures 1 and 3

The Introduction defines climate finance as “North-South financial flows directed at mitigating and adapting to climate change.” But the actual corpus evidently includes green bonds, sustainable finance, carbon markets, renewable energy, land use, CDM, EU ETS, climate risk, and innovation finance. Figure 3 includes “Green bonds & sustainable finance” and “Renewable energy & sustainable growth” as major clusters. The Introduction says “pure green finance” is filtered out, yet the corpus appears to retain large amounts of adjacent green-finance material.

This is not a minor definitional quibble. The paper’s central claim is that it provides a corpus of “climate finance literature.” If the operational definition is closer to “climate-related finance, policy mechanisms, carbon markets, and selected sustainable-finance topics,” then the title, abstract, and Introduction overstate the specificity of the corpus.

**What would fix it:**

- Provide an explicit inclusion/exclusion definition distinguishing:
  - international climate finance,
  - climate policy finance,
  - green finance,
  - sustainable finance,
  - carbon markets,
  - climate-risk finance,
  - development finance,
  - energy finance.
- Give the complete keyword taxonomy and co-occurrence rules in the paper or a main-table appendix, not only vaguely in the repository.
- Report validation results separately for boundary categories. For example: among sampled green-bond, EU ETS, renewable-energy, and land-use records, what proportion are genuinely “international climate finance” under the stated definition?
- Either narrow the dataset to match the definition, or retitle/reframe the dataset as a broader “climate-related finance and policy mechanisms” corpus.

---

### 2. The retrieval strategy is not reproducible from the paper  
**Sections:** 2.1, 2.2, 2.3; Table 1

The paper repeatedly refers to a “four-tier keyword taxonomy,” “eight-language keyword taxonomy,” “co-occurrence filters,” “quality filtering,” “blacklist matches,” “protection criteria,” and “cross-encoder threshold,” but does not give the actual operational details. A reader cannot reconstruct what was searched, what was excluded, or why.

Examples:

- The eight languages are never listed in Section 2.1.
- The actual Tier 1–4 keyword lists are absent.
- The co-occurrence logic for Tiers 3–4 is not specified.
- The OpenAlex query syntax, fields searched, pagination, date of query, and rate-limit handling are not described.
- The blacklist terms are only illustrated with “blockchain” and “deep learning,” but not listed.
- The cross-encoder threshold is not reported.
- The exact source-priority order for metadata merge is not given.
- The “17 curated reports” in the grey-literature source are not enumerated.
- The selection rules for “UNFCCC key documents” and “OECD DAC key documents” are not stated.

For a data paper, “the scripts are deposited” is not enough. The paper must describe the construction protocol at a level that allows methodological evaluation without reverse-engineering code.

**What would fix it:**

- Add a full retrieval table: source, query fields, exact query strings, language terms, date run, API endpoint, number returned, number retained.
- Include the full keyword taxonomy and blacklist.
- State the exact cross-encoder threshold and all other numerical thresholds.
- List the 17 grey-literature seed reports and the criteria for choosing UNFCCC/OECD “key documents.”
- Provide a flow diagram with counts at every step: harvested, deduplicated, flagged by each flag, protected, removed, retained.

---

### 3. The paper contains serious numerical and logical inconsistencies in the corpus counts  
**Sections:** 2.2, 2.3, 3; Tables 2 and 4

The count accounting is not coherent.

Examples:

1. Section 2.2 says DOI-based deduplication removes 833 records and title+year matching removes 159. Yet Section 2.3 and Table 2 treat 43,179 as “Raw” and also Section 3 calls `climate_finance Corpus.csv` a “complete, unfiltered corpus” with 43,179 rows and “one deduplicated work per row.” It is unclear whether 43,179 is before or after deduplication.

2. Section 2.3 says:
   - 11,244 works flagged,
   - 1,789 retained by protection criteria,
   - yielding 9,436 net removals,
   - plus 21 content-duplicates removed.
   
   But 11,244 − 1,789 = 9,455, not 9,436. Adding 21 gives 9,476. Neither reconciles with 43,179 − 33,344 = 9,835.

3. Table 2’s source-specific raw counts sum to 43,952, while the TOTAL raw count is 43,179. The table note says per-source counts may double-count multi-source records, but then the TOTAL row needs to be explicitly labelled as unique records. Similar care is needed for refined counts.

4. Section 2.2 says 738 refined works appear in multiple sources. Table 2 refined source counts sum to 34,107; 34,107 − 33,344 = 763 extra memberships. This is not impossible if some works appear in more than two sources, but it should be explained. As written, it invites suspicion that provenance counting is not fully understood.

5. Section 3 says users reproduce the refined subset with:
   - `df[-df['is_flagged'] | df['is_protected']]`
   
   Table 4 says:
   - `df[ df['is_flagged'] | df['is_protected']]`
   
   Both are problematic. The intended logic appears to be:
   - `df[(~df['is_flagged']) | (df['is_protected'])]`
   
   This is a major error because it concerns the basic definition of the advertised 33,344-work corpus.

**What would fix it:**

- Provide a single authoritative CONSORT-style flow table.
- Define exactly what “raw,” “deduplicated,” “unfiltered,” “flagged,” “protected,” “refined,” and “content duplicate” mean.
- Reconcile every count arithmetically.
- Correct the filtering expression everywhere.
- Add unit tests or reproducibility checks showing that the deposited file produces exactly 33,344 refined works.

---

### 4. The relevance-filtering validation is far too weak for the role it plays  
**Sections:** 2.2, 2.3, 2.4

The cross-encoder relevance filter is one of the largest removal mechanisms: Section 2.3 says 5,840 works are flagged by relevance scoring. Yet validation is reported only as “AUC = 0.818 and 81% accuracy” on a blinded sample of 100 works. This is inadequate.

Problems:

- No annotation protocol is described.
- No inclusion criteria are given to annotators.
- No information on number of annotators or inter-annotator agreement.
- No class balance is reported; 81% accuracy is meaningless without prevalence.
- No precision, recall, F1, false-positive rate, or false-negative rate at the chosen threshold.
- No confidence intervals are reported.
- The query, “climate policy and financial mechanisms,” is not equivalent to the paper’s stated definition of climate finance.
- The paper says halving or doubling the threshold reclassifies roughly 10% of the calibration sample, but this is not a serious threshold-sensitivity analysis.

Because this filter can remove relevant non-English, grey-literature, older, or non-standard vocabulary records, it may systematically erase precisely the material the paper claims to recover.

**What would fix it:**

- Annotate a substantially larger stratified sample, including:
  - English and non-English records,
  - grey literature,
  - early-period records,
  - OpenAlex-only records,
  - records flagged by each filter type,
  - records near the cross-encoder threshold.
- Report precision/recall at the deployed threshold.
- Provide confidence intervals.
- Report inter-annotator agreement.
- Show examples of false positives and false negatives.
- Justify the query text or compare several query formulations.

---

### 5. The multilingual claim is overstated  
**Sections:** Abstract, 1, 2.1, 2.3, 3, 5; Table 3

The paper repeatedly emphasizes multilingual retrieval and cross-lingual analysis. But Table 3 shows English accounts for 89.9% of refined works, while non-English classified works are a small minority. Moreover, the text says “the non-English layer counts 3,381 works,” but 3,381 is simply total minus English, including 1,358 “Unclassified” records. Classified non-English works are only 2,023.

The problem is not merely imbalance; it is that the paper uses the imbalance inconsistently. It acknowledges non-English coverage is limited, but the Abstract and Conclusion still claim the dataset supports “multilingual retrieval,” “cross-lingual analysis,” and “comparing how the category travelled across languages.” Those claims are not demonstrated.

Additional issues:

- The eight target languages are not listed.
- UNFCCC and OECD multilingual documents are indexed only in English.
- Grey literature is 0% non-English in Table 2.
- bibCNRS contributes only 219 refined works, with 7% non-English according to Table 2, which is surprisingly small given its stated purpose as a non-English discourse source.
- Language detection methodology is not described.
- The “Other (40 languages)” category is opaque.
- No retrieval evaluation is reported by language.
- No evidence is provided that the embeddings actually align climate-finance concepts across the languages represented in the corpus.

**What would fix it:**

- Tone down the multilingual claims unless directly validated.
- List target languages and translated terms.
- Report recall/precision by language using hand-labeled samples.
- Separate “classified non-English” from “unclassified.”
- Provide language-detection accuracy checks.
- Include examples of cross-lingual retrieval performance, e.g., nearest-neighbor queries across English/French/Spanish/Portuguese/German/Chinese/Japanese.
- Do not claim balanced or robust cross-language comparison unless the dataset supports it.

---

### 6. The grey-literature component is too small and too selectively curated to support the paper’s claims  
**Sections:** Abstract, 1, 2.1, 2.3, 5; Tables 1 and 2

The Abstract claims the dataset combines academic databases, institutional repositories, and grey literature, “enabling broader coverage than single-source bibliometric studies.” That is true in a trivial sense, but the actual grey-literature contribution is tiny: Table 2 reports 210 refined “Grey literature” records, 230 UNFCCC key documents, and 33 OECD DAC key documents. Together these are less than 1.5% of the corpus.

The “Grey literature” source is described as “17 curated reports + World Bank repository.” That is not a systematic grey-literature harvest. It excludes national institutions, central banks, regional development banks, NGOs, foundations, research institutes, and non-English institutional publications. Section 2.3 acknowledges some of this, but the Abstract and Conclusion still present grey-literature coverage as a central feature.

The “key documents” language is especially concerning: key according to whom? selected how? with what reproducibility?

**What would fix it:**

- Rename this component as “selected institutional documents” unless a systematic grey-literature retrieval is actually performed.
- Provide selection criteria and full document lists.
- Add major missing sources or justify their exclusion:
  - Green Climate Fund,
  - Global Environment Facility,
  - Adaptation Fund,
  - multilateral development banks,
  - IMF,
  - regional development banks,
  - central-bank climate-finance publications,
  - national climate-finance reports,
  - NGO and think-tank repositories.
- Report the marginal contribution of grey literature to topics, periods, and citation/network structure.
- Remove or soften broad claims about grey-literature coverage.

---

### 7. Deduplication is acknowledged to be incomplete but not adequately controlled  
**Sections:** 2.2, 2.4; Table 4

The deduplication method relies on DOI matching and title+year matching. Section 2.4 concedes that working paper/published version pairs remain, and that fuzzy title matching raises the upper bound to 1,329 works, or 4.0% of the corpus. It also states that surviving version pairs “double-count citations, inflating co-citation and community-size statistics.”

That is a serious problem, not a footnote. The corpus is explicitly advertised for citation network analysis and bibliometric mapping. If 1–4% of records may be version duplicates, and these duplicates are concentrated in high-citation working-paper/report/article pipelines, they may disproportionately distort network results.

The paper also says author metadata is noisy and author-normalized deduplication is left to a future release. That is not reassuring.

**What would fix it:**

- Perform version-clustering for working papers, preprints, reports, and published articles before release, or at least provide a conservative version-collapsed view.
- Quantify the effect of suspected duplicates on:
  - annual counts,
  - citation counts,
  - community detection,
  - semantic clustering.
- Provide manual validation of a sample of candidate duplicate pairs.
- Make the near-duplicate and version-pair fields central dataset variables, not afterthoughts.

---

### 8. The citation-network construction and validation are insufficient for the claims made  
**Sections:** 1, 2.3, 2.4, 3, 4; Figure 2

The paper makes several network claims, including replication of prior findings and detection of disconnected “public-finance” and “market-finance” poles. But the citation graph is DOI-based and therefore excludes or undercounts the 24% of works without DOIs, with especially poor coverage for grey literature, books, older works, UNFCCC/OECD documents, and non-English material.

Specific problems:

- Section 3 says works without DOIs cannot be matched as citing sources, yet Section 2.3 reports “1,087,209 corpus-internal citation pairs” and Section 4 maps only 13,112 connected works. This means most of the corpus does not participate meaningfully in the citation network.
- Figure 2 is described as “full-corpus scale,” but it covers 10 communities holding 84% of 13,112 connected works, i.e. roughly one-third of the 33,344-work refined corpus.
- The citation validation checks only links present in the data against Crossref. It does not evaluate missing links, which are arguably more consequential.
- The reported 97.0% confirmation rate from 300 links is fine as a spot check, but insufficient to validate network completeness or suitability for community detection.
- In the Introduction, the reported rewiring result is suspect: “z = 76, p = 0.0099.” A z-score of 76 would imply an astronomically small p-value, not 0.0099. This suggests either a reporting error or a misunderstanding of the null model.

**What would fix it:**

- Clearly distinguish citation-link precision from citation-link recall.
- Report network coverage by source, year, document type, language, DOI status, and grey/academic classification.
- Provide sensitivity analyses excluding low-reference-count works and suspected version duplicates.
- Recompute community detection under alternative graph constructions.
- Correct or remove the z-score/p-value claim.
- Rename Figure 2 to reflect that it maps the DOI-linked connected subgraph, not the full corpus.

---

### 9. The descriptive analyses are under-methodologized and risk laundering corpus-construction artifacts as field history  
**Sections:** 1, 2.1, 4; Figures 1 and 3

The paper uses the corpus to make historical claims: a 2015 structural break, post-2015 annual growth of 17%, disconnected research poles, and thematic shifts across periods. But Section 2.1 itself admits the keyword taxonomy is retrospective and “embeds the negotiation calendar in the harvest itself.” That is exactly the kind of circularity that makes historical trend claims fragile.

Figure 1 is particularly vulnerable. Annual publication growth may reflect:

- expansion of OpenAlex coverage,
- DOI adoption,
- changes in indexing of working papers,
- changes in English terminology,
- publication lag,
- post-2015 keyword choices,
- inclusion of adjacent green-finance literature,
- incomplete/uneven retrieval of early grey literature.

Similarly, Figure 3’s thematic shifts may partly reflect search-query expansion and vocabulary drift rather than genuine shifts in the field.

**What would fix it:**

- Separate dataset description from substantive historical claims unless the latter are rigorously supported.
- Add sensitivity analyses using:
  - core-only terms,
  - “climate finance” phrase-only subset,
  - non-OpenAlex sources excluded,
  - DOI-only records,
  - English-only and non-English subsets,
  - fixed vocabulary searches across periods.
- Report annual source composition and language composition.
- Avoid terms like “take-off,” “crystallisation,” and “established field” unless they are analytically justified rather than imposed by UNFCCC milestones.

---

### 10. Comparison with prior bibliometric studies is not valid as presented  
**Section:** 1

The paper claims to subsume 89.3% of the works retrieved for Carè and Weber’s query, 91.0% for Shang and Jin’s query, and 40.1% for Maria et al.’s query. But the comparison is made by “queries replicated against OpenAlex,” whereas the cited studies used Scopus or Web of Science. Replicating their query in OpenAlex is not the same as comparing against their actual retrieved corpus.

The result may reflect database coverage, query translation, DOI availability, title matching, or year constraints—not corpus superiority or coverage of the prior studies’ datasets.

**What would fix it:**

- Obtain or reconstruct the actual bibliographic records from the prior studies if possible.
- If not possible, state explicitly that this is only a query-level OpenAlex approximation.
- Report matching rules, false-match checks, and unmatched examples.
- Remove “subsumes” unless actual prior corpora are compared.

---

### 11. The AI-assisted sources are not reproducible or auditable enough  
**Sections:** 2.1, 2.2, 2.3; Table 1

Several sources are described with vague AI language:

- “Teaching canon — AI-assisted”
- “SciSpace — AI-collected, hand-exported”
- “UNFCCC — AI-collected”
- “LLM-assisted extraction”
- generated abstracts or keywords for curated documents

This is not acceptable without a precise protocol. LLM use can introduce hallucinated references, biased extraction, inconsistent parsing, and non-reproducible outputs unless model versions, prompts, sampling settings, and validation are documented.

The paper says the teaching canon’s
