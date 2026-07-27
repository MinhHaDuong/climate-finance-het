# Peer review — openai/gpt-5.5, persona: student

## Review of “A Curated Multi-Source Corpus of Climate Finance Literature, 1990–2024: Multilingual Retrieval and Grey Literature”

### Overall assessment

This is a useful and potentially important data paper. The core contribution—a large, openly released, provenance-tracked corpus of climate finance literature that combines OpenAlex with selected grey-literature, institutional, teaching, and multilingual sources—is genuinely valuable. I especially appreciate three aspects: (i) the explicit recognition that “climate finance” is a contested and historically evolving category rather than a clean bibliometric object; (ii) the publication of audit flags and provenance columns rather than only a polished final list; and (iii) the provision of embeddings and citation-network files, which make the dataset immediately usable for downstream topic modelling and network analysis.

That said, the paper currently makes several claims that are stronger than the evidence presented in the main body supports. The main weaknesses are: internal inconsistencies in counts and versioning; insufficient reporting of the actual search/query taxonomy and filtering thresholds; possible biases introduced by the quality filter against precisely the non-English, grey-literature, early, and peripheral works the corpus aims to recover; and some ambiguity about the citation graph and reproducibility given that abstracts are not deposited. I would recommend publication only after substantial clarification and correction, because the dataset seems valuable but the current paper is not yet sufficiently auditable from the main text.

---

## Major comments

### 1. The paper’s central object—“climate finance”—needs sharper operational definition

The Introduction defines climate finance as “North-South financial flows directed at mitigating and adapting to climate change.” This is a relatively narrow international-governance definition. But later sections and figures suggest a much broader corpus including green bonds, sustainable finance, renewable energy finance, carbon markets, climate risk, innovation finance, EU ETS, and Kyoto mechanisms.

This tension matters because the paper repeatedly contrasts its corpus with “pure green finance” and says it filters that out. Yet Figure 2 includes communities labelled “green bonds” and “climate risk”; Figure 3 includes “Green bonds & sustainable finance” and “Renewable energy & sustainable growth.” These are not necessarily North-South climate-finance literatures. Some are domestic sustainable finance or market finance literatures. The corpus may still be useful if it intentionally covers the wider “finance-climate nexus,” but then the Introduction’s definition is misleading.

Concrete questions:

- Is the corpus intended to capture **international public climate finance**, **UNFCCC/OECD climate finance**, or the broader **climate-and-finance scholarship**?
- What exactly distinguishes included “green bonds & sustainable finance” works from excluded “pure green finance” works?
- Does the cross-encoder query “climate policy and financial mechanisms” operationalize the North-South definition, or a broader climate-policy/finance relation?

This is not just semantic. It affects recall, precision, comparisons to Carè and Weber, Shang and Jin, and Maria et al., and interpretation of temporal breaks in Figure 1.

---

### 2. The source-count and corpus-size numbers are internally inconsistent

Several numerical inconsistencies need correction before the paper can be trusted as a data descriptor.

#### Table 2 totals

In Table 2, the raw source counts sum to:

- OpenAlex 41,138  
- ISTEX 748  
- bibCNRS 233  
- SciSpace 663  
- Grey literature 281  
- Teaching canon 622  
- UNFCCC 232  
- OECD 35  

These sum to 43,952, not 43,179. The table note says raw records with provenance flags are counted once per source, so the “TOTAL” row should either be the sum over source rows or explicitly labelled as the deduplicated union. The same issue appears for the refined column: source rows sum to 34,107, while the table gives 33,344. That is understandable if “TOTAL” is the union, but the table currently mixes per-source counts with union counts without clearly flagging this.

#### Filtering arithmetic

Section 2.3 says:

- 43,179 raw records reduced to 33,344 refined works.
- Difference: 9,835 removals.
- 11,244 works flagged.
- 1,789 retained by protection criteria.
- Therefore net removals should be 9,455 if those numbers are direct subtraction.
- The text says “9,436 net removals,” plus 21 content duplicates, giving 9,457.
- None of these equal 9,835.

There may be a reason—e.g., duplicates removed at different stages, raw source rows versus deduplicated works, or flags computed before/after enrichment—but the pipeline accounting is currently not reproducible from the prose.

#### Six sources versus eight sources

The paper title and Table 1 describe eight sources. But the related dataset and suggested citation still say “Six Sources.” Section 3 says the raw inputs include “the six per-source catalogs,” while Table 1 has eight sources. This looks like a versioning artifact from v1.0/v1.1, but in a data paper it is a serious clarity problem.

#### Refined-subset expression is wrong

Section 3 says users can reproduce the refined subset with:

> `df[-df['is_flagged'] | df['is_protected']]`

Table 4 says:

> `df[ df['is_flagged'] | df['is_protected']]`

Both appear wrong or at least inconsistent. The intended logic, based on Section 2.2, seems to be:

> `df[(~df['is_flagged']) | df['is_protected']]`

This should be fixed in both places, because it is the most basic reproducibility instruction in the paper.

---

### 3. The search strategy is under-specified in the main text

The paper’s main methodological novelty is the multilingual, multi-tier search strategy, but Section 2.1 gives only a high-level description. For a data paper, the main body should include enough of the query design to let readers assess coverage and bias without having to inspect code.

At minimum, I would want:

- the eight target languages listed explicitly;
- examples of Tier 1, Tier 2, Tier 3, and Tier 4 terms;
- the co-occurrence filters for Tiers 3–4;
- the exact fields queried in OpenAlex and other APIs—title only, title/abstract, concepts, full text where available?;
- whether translated equivalents were manually curated, machine-translated, or mined;
- whether language-specific morphology, accents, plural forms, and phrase variants were handled;
- the source-priority order used when merging metadata;
- the threshold for the cross-encoder relevance flag;
- the semantic-outlier threshold and whether it was computed globally or within language/source/year strata.

The sentence “The taxonomy was informed by keyword mining of 2,644 core papers cited ≥50 times” is important but also worrisome. Highly cited “core” papers are likely to be older, English-language, and mainstream. If the vocabulary is mined from them, then the query may systematically miss newer, marginal, non-English, activist, or Southern framings. The paper acknowledges circularity, which is good, but does not quantify its effect.

A useful addition would be a table showing example included and excluded queries by tier, with estimated yield and precision for each tier.

---

### 4. The quality filter may remove the very records the dataset claims to add

The corpus’s stated value is that it broadens beyond English academic bibliometrics into multilingual and grey-literature sources. But several filtering rules appear likely to penalize those same records:

- **Citation isolation** removes pre-2020 works neither citing nor cited by corpus works. Grey literature, policy reports, and non-English works are less likely to have DOI-linked citation metadata.
- **Absent abstract + irrelevant title** penalizes records from sources with weak abstract coverage, such as bibCNRS, where Table 2 reports only 5% abstracts.
- **Semantic outlier detection** around a global embedding centroid may remove genuinely distinct language communities or underrepresented topics.
- **Cross-encoder relevance scoring** against one English query may under-score non-English or institutionally specific documents, depending on model performance.
- **Protection criteria**—citation count ≥50, presence in 2+ sources, within-corpus citations, teaching syllabi—again privilege highly visible English academic works and courses at institutions with public syllabi.

Section 2.3 reports a human validation of the cross-encoder with AUC = 0.818 and 81% accuracy on 100 works. That is helpful, but not enough to establish that the full six-flag pipeline preserves minority material. I would want an ablation table showing removals by:

- source;
- language;
- year/period;
- DOI presence;
- document type, if available;
- citation-count decile;
- semantic cluster.

For example, what fraction of bibCNRS, UNFCCC, OECD, and non-English records were flagged and then rescued? Which flags account for non-English removals? Are Portuguese, Spanish, Chinese, Japanese, Arabic, and French records more likely to be semantic outliers? This is central to the paper’s claims.

---

### 5. Multilingual coverage is promising but currently overstated

The multilingual ambition is one of the paper’s attractive features. However, Table 3 shows that English still accounts for 89.9% of refined records; 4.1% are unclassified; and the leading non-English languages are Portuguese, Spanish, German, and French. The paper says the search uses an eight-language taxonomy, but the main body does not list the eight languages, and the actual non-English layer seems relatively small.

The paper also says the embeddings “place all works in a shared semantic space regardless of language.” This is directionally true for multilingual sentence transformers, but it is not a validation result. Cross-lingual embedding alignment can vary by language and domain. Since the corpus claims to enable cross-lingual analysis, I would expect at least a small diagnostic:

- retrieve known translations or multilingual versions of UNFCCC/OECD documents and test nearest-neighbor alignment;
- compare topic distributions before and after machine translation for a non-English sample;
- report cross-lingual nearest-neighbor examples for Portuguese, Spanish, French, German, Chinese, and Japanese;
- evaluate whether non-English documents cluster by topic or by language.

Also, Section 2.1 says that for UNFCCC and OECD documents available in multiple languages, only the English version is indexed. That is understandable for avoiding duplicates, but it weakens the multilingual claim for precisely the institutional sources where official translations would be available and valuable.

---

### 6. The citation-network description is useful but ambiguous

The citation network is a major data product, but several details are confusing.

Section 2.3 says there are 1,087,209 corpus-internal citation pairs covering 80% of corpus DOIs. Section 4 says Figure 2 maps the intra-corpus citation graph with 13,112 connected works. Since the refined corpus has 33,344 works and 25,411 DOI-bearing works, I need more clarity on what “covering 80% of corpus DOIs” means. Does it mean 80% of DOI-bearing corpus works appear either as citing or cited nodes? If so, why are only 13,112 works connected in Figure 2? Are isolates excluded? Are weak components removed? Is the graph directed or symmetrized before Louvain?

Section 3 says `citations.csv` has `source_doi` and `ref_doi`, and works without DOIs cannot be matched as citing sources. But the same paragraph says GROBID parses unresolved reference strings and a fuzzy-matching step resolves them against corpus works. If a cited corpus work lacks a DOI but is resolved by title/author/year, does it enter the citation network? The CSV schema suggests no. If not, then the graph systematically excludes no-DOI grey literature and older works as cited targets too, not just citing sources.

The validation also needs clarification. Section 2.3 says a sample of 300 links was verified against Crossref metadata, with 97% confirmed. But if many links originate from Crossref/OpenAlex deposits, verification against Crossref risks being partly circular. Conversely, the nine “unconfirmed” links might be correct but absent from Crossref. The paper should explain what the ground truth is and how sampled links were stratified.

For Figure 2, I would also like a table listing the 10 Louvain communities, sizes, top terms, representative highly cited works, and perhaps within/between citation density. The current force-directed map is visually useful but hard to interpret quantitatively.

---

### 7. The descriptive statistics sometimes look like findings from a separate research article rather than dataset validation

Section 4 is interesting, but some claims need either more support or clearer framing as illustrative.

Figure 1’s temporal pattern is compelling, especially the distinction between total corpus growth and the subset explicitly using “climate finance.” However, the Introduction also reports a Chow test at 2015 and 17% annual growth since 2015. The paper should state whether this is based on refined corpus counts, phrase-matching counts, or another subset, and whether it adjusts for OpenAlex coverage growth over time.

Figure 3 is potentially useful, but I was confused by several things:

- The caption says the periods are “Before,” “Crystallisation,” and “Disputes,” while Figure 1 uses “Established field” for 2015–2024.
- The “Kyoto mechanisms & CDM” cluster appears to grow from 2% before 2007 to 20% after 2015, which is counterintuitive if it is really Kyoto/CDM. Perhaps the top TF-IDF terms or cluster label are misleading.
- The text says k-means recovers five of six themes from the companion study, with “land-use” replacing the “$100bn/fund-flows theme.” But a data paper should not require an under-review companion study to interpret the clustering.
- The adjusted Rand index is reported “over 8,315 works,” but it is not clear why only 8,315 works are used when embeddings exist for 38,736 works and the refined corpus has 33,344.

These are fixable, but the current section reads as if important clustering choices are deferred elsewhere.

---

### 8. Reproducibility is good in spirit but incomplete in practice

The Zenodo/code/DVC setup is a major strength. Still, the paper should be more candid and precise about which parts are reproducible exactly and which are not.

Important issues:

- Abstracts are not deposited, yet embeddings, semantic outlier detection, and cross-encoder relevance scores depend on abstracts. Users can re-fetch abstracts from OpenAlex, but the paper notes that live indexes drift. This means the central semantic products are not exactly reproducible from the deposited corpus alone.
- LLM-assisted extraction is used for the teaching canon, and possibly generated abstracts/keywords. The paper should report the model, version, prompt, date, temperature/settings, and validation procedure.
- “AI-collected” SciSpace and UNFCCC sources are not sufficiently described. Was an LLM used to search, screen, extract metadata, or classify documents? How were hallucinations or omissions checked?
- The paper says three restricted sources have raw exports included in Zenodo. Are there licensing or redistribution constraints for bibCNRS/SciSpace/OECD exports? If redistribution is allowed under CC BY 4.0, that should be explicitly stated.

I do not think every detail must be in the main text, but the main text should distinguish deterministic, scripted, API-based steps from manual/LLM-assisted curation steps.

---

## Minor and editorial comments

1. **Author affiliation formatting:** In the Introduction, the affiliation line appears inserted into the prose: “*Directeur de recherche...@cnrs.fr sitting out of standard academic databases.” This needs correction.

2. **Reference formatting:** The references are inconsistently formatted. “Carè et al. (2023)” in the reference list appears to list only Carè and Weber. “Shang and Jin” is preceded by “- [2023]”. Priem et al. is not in the same bullet format.

3. **Data citation mismatch:** The suggested citation says “Six Sources,” while the paper title says “8 complementary sources.” This should be harmonized.

4. **Typo:** “dedduplication” in Section 3 should be “deduplication.”

5. **Typo/logic in Table 4:** The description for `is_flagged` should not say the refined subset is `df[df['is_flagged'] | df['is_protected']]`.

6. **Terminology:** The paper alternates among “refined works,” “filtered corpus,” “v1,” “v1.0,” “v1.1,” “complete unfiltered corpus,” and “raw.” A small pipeline diagram would help.

7. **Figure 2 readability:** The community labels are hard to read in the provided figure. A companion table would be more informative.

8. **Figure 3 period label:** Use one label consistently for 2015–2024: “Established field,” “Disputes,” or another term.

9. **“frsitting” typo:** The correspondence email and following sentence are concatenated.

10. **OpenAlex date:** Citation counts are reported as of 2026-07-24. Since the dataset covers 1990–2024, clarify whether records published after 2024 were excluded but citation counts were harvested in 2026.

11. **“Core papers cited ≥50 times”:** Please specify whether citations are OpenAlex citations as of 2026, and whether the 2,644 core papers came from an initial English query or an earlier version of the corpus.

12. **Near-duplicate handling:** Section 2.2 says near-duplicate same-content publications are kept, but Section 2.3 says 21 content duplicates are removed. The distinction between “near duplicates kept” and “content duplicates removed” needs definition.

13. **Language detection:** Table 3 has 1,358 unclassified works. What kinds of records are these? Missing titles? Multilingual titles? Acronyms? Institutional documents?

14. **License:** Since the corpus does not include abstracts but includes embeddings derived from abstracts, briefly discuss whether the CC BY release applies to embeddings without restriction.

15. **Comparison to prior corpora:** The Introduction’s claim that this corpus subsumes 89.3% of Carè and Weber and 91.0% of Shang and Jin is useful. Please add details: how many records were in each replicated query, how matching was performed, and what kinds of records were missed.

---

## Missing or underdeveloped related work

The paper cites several climate/green finance bibliometric studies, which is appropriate, but the literature framing could be strengthened in three directions.

First, for climate finance as an object, the paper should cite definitional and institutional literature on climate-finance accounting, UNFCCC finance mechanisms, OECD Rio markers, the $100bn goal, and North-South finance politics. This would help justify the corpus boundary.

Second, for bibliographic databases, it would be useful to cite comparisons of OpenAlex, Scopus, Web of Science, Crossref, Dimensions, Lens, and Google Scholar coverage. Since OpenAlex contributes 94.6% of refined works, the strengths and limitations of OpenAlex are central.

Third, for multilingual retrieval and systematic search reporting, the paper could engage with PRISMA-style reporting, cross-lingual information retrieval, and known biases in language detection and multilingual embeddings.

---

## Questions I would ask the authors

1. What is the intended operational scope of the corpus: North-South public climate finance, UNFCCC/OECD climate finance, or the broader climate-and-finance literature?

2. Can you provide the full eight-language keyword taxonomy, including Tier 1–4 terms, co-occurrence filters, queried fields, and per-tier yields?

3. How many records does each quality flag remove by source, language, year, and DOI status?

4. What fraction of non-English and grey-literature records are removed by citation isolation, semantic outlier detection, and cross-encoder relevance scoring?

5. What exact threshold is used for the BAAI/bge-rerankerv2-m3 relevance score, and how was it chosen?

6. Who produced the human labels for the 100-work validation sample? Was there more than one annotator, and is inter-annotator agreement available?

7. Why is the cross-encoder query “climate policy and financial mechanisms” rather than something closer to the paper’s definition, e.g. “international climate finance for mitigation and adaptation”?

8. How do you guard against the protection criteria preserving highly cited but off-topic green-finance papers while removing low-citation but relevant Southern or grey-literature records?

9. Can you reconcile the filtering counts in Section 2.3 with the difference between 43,179 raw records and 33,344 refined works?

10. Should the Table 2 “TOTAL” row be interpreted as a union rather than a sum over source rows? If so, can the table label this explicitly?

11. Why
