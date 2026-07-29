# Peer review — openai/gpt-5.5, persona: student

## Peer review

### Summary and overall assessment

This data paper describes a curated corpus of 33,344 “refined” works on climate finance, assembled from eight academic, institutional, and pedagogical sources, with multilingual retrieval, deduplication, quality filtering, citation links, and precomputed embeddings. The paper’s most useful contribution is not simply the size of the corpus, but the attempt to make the boundary of “climate finance” explicit and inspectable: provenance flags, filtering flags, protection criteria, citation files, embeddings, and source catalogs are all valuable for downstream bibliometric and history-of-thought work. I also appreciate the frankness of Section 2.4: the author openly reports language imbalance, scorer bias, incomplete citation coverage, residual duplicates, and the selective nature of the institutional layer.

That said, several issues currently limit my confidence in the dataset as a reproducible “1990–2024 multilingual climate finance corpus.” The largest concerns are: (i) the stated temporal scope is violated by nearly 10% of the refined corpus; (ii) the multilingual claim is weakened by English-only scoring, English-only versions of key documents, and much higher non-English removal rates; (iii) the relevance filtering procedure is under-validated and partly irreproducible; (iv) the institutional and grey-literature layer is described as curated but not sufficiently operationalized in the main paper; and (v) some numerical and methodological claims in Tables 2–3 and Section 2.3 need clarification or correction.

I would view the paper as promising and publishable after substantial revision, especially if the author either enforces the declared corpus boundaries or explicitly reframes the dataset as a broader 1990–2026 harvest with a 1990–2024 target window and known leakage.

---

## Major strengths

1. **Useful multi-source architecture.**  
   Section 2.1’s combination of OpenAlex, ISTEX, SciSpace, teaching syllabi, bibCNRS, institutional reports, UNFCCC, and OECD is a real advance over single-database bibliometric studies. The `from_*` provenance flags and `source_count` field are particularly useful, because they let users test sensitivity to source composition.

2. **Good practice in retaining flags rather than only releasing a filtered corpus.**  
   Section 2.2 states that excluded records are retained in the deposit with flags. This is important: many bibliometric corpora silently hide filtering decisions, whereas this design allows downstream users to rebuild alternative corpora.

3. **Explicit discussion of biases.**  
   Section 2.4 is unusually candid. The admission that non-English works are removed at 41.8% versus 19.9% for English, and that own-language query translations lift non-English scores by 11.5 percentage points, is exactly the kind of diagnostic a data paper should include.

4. **Potentially valuable citation and embedding layers.**  
   The combination of `citations.csv` and multilingual embeddings could support many analyses beyond the author’s companion history-of-thought study. The distinction in Section 4 between citation communities and semantic clusters is promising, although the semantic clustering itself is deferred to another paper.

---

## Major concerns

### 1. The declared temporal scope is not actually enforced

The title, abstract, Zenodo description, and Section 2.1 all present the corpus as covering **1990–2024**. But Section 2.4 states that **3,278 refined works, or 9.8%, fall outside that range**, including **3,238 after 2024** and 40 before 1990. This is not a small edge case; nearly one in ten refined records violates the advertised temporal coverage.

This creates several downstream problems:

- The corpus cannot straightforwardly be used for trend analysis through 2024.
- Section 4’s annual growth claims are hard to interpret if post-2024 works remain in the refined corpus.
- The statement in Section 4 that “the search window is 1990–2024; the earliest works date from 1992” conflicts with Section 2.4’s statement that 40 refined works predate 1990.
- Citation counts are as of 2026, but that is acceptable; inclusion of 2025–2026 publications in a 1990–2024 corpus is not.

I understand the append-only rationale, but I do not think it is sufficient for a dataset whose title and DOI metadata specify 1990–2024. The simplest fix would be to add a final temporal filter to the refined subset, while preserving the out-of-window records in the unfiltered archive. Alternatively, the paper should be retitled and the temporal coverage revised.

### 2. The scope of “climate finance” is conceptually unstable

The Introduction defines climate finance as “North-South financial flows directed at mitigating and adapting to climate change.” That is a relatively narrow UNFCCC-oriented definition. But the corpus clearly includes broader literatures: green bonds, ESG, carbon markets, corporate finance, environmental economics, and “green finance” adjacency appear in Figure 1 and throughout the method.

This is not necessarily wrong; climate finance is indeed a contested category. But the paper oscillates between a narrow institutional definition and a broad bibliometric retrieval domain. This matters because:

- The lower overlap with Maria, Ballini, and Souza (2023) is explained as “green finance at large,” but the corpus itself seems to include substantial green-finance material.
- Tier 3 and Tier 4 “climate-adjacent” retrieval terms could pull in broad environmental finance or development finance literature.
- The cross-encoder query “climate policy and financial mechanisms” is broader and more policy-oriented than the Introduction’s North-South flow definition.

I would like the paper to distinguish more clearly among at least three possible objects:  
1. UNFCCC/OECD climate finance as international transfers and accounting;  
2. academic climate-finance scholarship broadly construed;  
3. adjacent sustainable/green finance literatures that cite or use similar vocabulary.

Right now the corpus likely mixes all three, but the paper does not give users enough guidance on how to separate them.

### 3. The multilingual claim is undercut by filtering and source choices

The paper’s title and abstract foreground multilingual retrieval, but Table 4 shows that English accounts for **93.8%** of refined works. That alone is not disqualifying; it may reflect the field. The more serious issue is that the pipeline appears to remove non-English works disproportionately.

Section 2.4 reports:

- 41.8% of non-English works are removed, versus 19.9% of English works.
- The cross-encoder flag accounts for 58.9% of non-English removals.
- Translating the query into the work’s language lifts the share crossing the threshold by 11.5 percentage points.

This is a major methodological finding, but it is treated as a limitation rather than fixed. If the purpose is to publish a multilingual corpus, why not deploy multilingual or language-specific scoring at build time? At minimum, I would expect:

- relevance validation stratified by language;
- per-language precision/recall or at least manual checks for the main non-English languages in Table 4;
- a version of the refined corpus with a language-aware threshold;
- a clear recommendation that multilingual studies should not use the default refined subset.

The decision in Section 2.1 to index only English versions of multilingual UNFCCC and OECD documents also weakens the claim that the corpus captures multilingual institutional discourse. That may be pragmatic, but it should be framed as English-language representation of multilingual institutions, not multilingual institutional coverage.

### 4. Relevance filtering is too fragile for the role it plays

Section 2.3 says the cross-encoder relevance score is a major filter: 5,840 works are flagged below a threshold. Yet the validation evidence is thin and partly unrecoverable.

Specific concerns:

- The validation sample has only 100 works, stratified by score quintile. This is useful for a diagnostic, but not enough to justify filtering thousands of records across languages, sources, years, and document types.
- The per-work grades for the main stratified sample “were not retained.” That is a reproducibility problem. A data paper should not rely on vanished manual annotations, especially for the central relevance filter.
- The claim that monotonic quintile relevance rates “alone fix the discrimination of the scores at AUC = 0.818” seems too strong. With grouped quintile rates one can estimate an AUC under assumptions about ordering and within-bin ties, but the exact AUC depends on per-work labels and score distributions within bins.
- Accuracy, precision, and recall at the deployed threshold are reported, but because the sample is stratified by score quintile, these metrics need weighting to the actual score distribution if they are meant to describe deployed performance.
- The threshold appears arbitrary: halving or doubling it reclassifies roughly 10% of the calibration sample. That is a large sensitivity for a binary inclusion decision.

The paper would be much stronger if the relevance filter were presented as an optional flag rather than as a decisive component of the default refined corpus, or if it were validated with a larger, retained, stratified sample covering English/non-English, academic/grey, and high/low citation records.

### 5. Protection criteria may preserve influential false positives

Section 2.2 says flagged works are retained if protected by citation count ≥ 50, presence in two or more sources, within-corpus citations, or teaching-syllabus appearance. This is understandable for recall, but it creates a subtle bias: highly cited adjacent-literature works may survive even if topically marginal, while non-English or low-citation works are removed.

The criterion “within-corpus citations” is especially broad. If a false-positive cluster enters via keyword noise and cites itself internally, it can become protected. Similarly, “presence in two or more sources” may reflect database overlap rather than topical validity.

I would like to see an ablation table showing how many protected-but-flagged works survive by protection reason, and a manual relevance audit of those protected flagged works. The current statement that 1,808 flagged works survive is useful but not enough.

### 6. Institutional and grey-literature coverage is important but underspecified

The institutional layer is one of the paper’s most distinctive contributions, but it remains hard to evaluate from the main text.

Section 2.1 states that institutional reports include 17 selected reports plus a World Bank repository harvest, and that UNFCCC/OECD documents enter through a curated inclusion rule. Later, Section 2.4 says the layer deliberately excludes national institutions and samples rather than surveys institutional writing.

The concern is not that the layer is selective; selectivity is unavoidable. The concern is that the selection process is circular and not sufficiently auditable from the paper itself. The UNFCCC/OECD classes were “fixed empirically” by crossing a companion study’s bibliography against the first corpus version and keeping classes of documents it cited but the corpus lacked. This risks tailoring the corpus to the author’s companion argument.

At minimum, the main paper should report:

- counts by institutional subsource, not only aggregate “Institutional reports,” “UNFCCC,” and “OECD” rows;
- the number of documents per document class;
- how many were added because of the companion study;
- which classes were considered but excluded;
- whether a user can reconstruct the selection without reading the companion study.

The institutional layer is only about 1.4% of the corpus, yet it is central to the paper’s novelty. It deserves a more transparent sampling frame.

### 7. Citation-network quality claims need clearer denominators and less circularity

Section 2.3 reports a 97.0% confirmation rate for sampled DOI-to-DOI links against Crossref reference lists, and 98.3% capture of Crossref reference DOIs. This is helpful, but several aspects are unclear.

First, the audit is partly circular, as the author notes: links harvested from Crossref/OpenAlex are being validated against Crossref. That does not invalidate the audit, but it means the result should be framed as internal consistency with deposited metadata, not citation accuracy.

Second, the reverse direction is confusing: “the corpus captures 98.3% of the reference DOIs Crossref does hold (6,016 of 6,119).” Does this mean, for sampled citing works, the citation extraction pipeline recovered 6,016 Crossref-deposited references? Or does it mean 6,016 of those references appear in `citations.csv`? Are these references to any DOI or only to corpus works? The denominator needs to be made explicit.

Third, the text gives several citation counts that are difficult to reconcile:

- `citations.csv` has 1,375,310 rows in Section 3.
- Section 2.3 says refined works yield 1,087,209 outgoing citation pairs where the cited work may lie outside the corpus.
- Figure 1 uses the corpus-internal graph with 13,112 connected works.

I assume the difference is that `citations.csv` includes unrefined works as citing sources, but the paper should say this directly.

Finally, because the graph is DOI-based, no-DOI works—including UNFCCC/OECD documents—are structurally excluded from citation analyses. Section 2.4 acknowledges this, but Figure 1 and Section 4 should repeat the caveat more prominently: the “global map of climate finance scholarship” is a map of DOI-bearing academic citation relations, not of the full corpus.

### 8. Deduplication and source-overlap statistics require clarification

Table 3 says the TOTAL row has 33,344 refined works and 32,606 unique works, implying 738 works appear in multiple sources. But the note says “Refined less Unique = 738 works appearing in two or more sources,” while the source rows’ refined-minus-unique differences sum to more than 738 because multi-source works are counted in several rows. This is technically explainable, but the wording is confusing.

More importantly, only **2.2%** of refined works appear in multiple sources. Given that OpenAlex is broad and SciSpace/ISTEX/teaching canon likely overlap with academic metadata, this seems surprisingly low. It may reflect weak cross-source matching, missing DOIs, title variants, or source-specific exports. The paper should discuss whether low overlap is a substantive finding or an artifact of deduplication limits.

The deduplication order also raises a question: Table 2 applies quality filtering before the final duplicate-DOI pass after enrichment. If enrichment reveals duplicates after filtering, then duplicate records may have affected source_count, protection status, citation isolation, and quality flags. Why not enrich before all deduplication and filtering?

### 9. Reproducibility is limited by undistributed abstracts and index drift

Section 3 says abstracts are not included due to publisher redistribution restrictions, yet embeddings and relevance scores were computed from abstracts fetched at build time. Re-fetching may not reproduce the same text because OpenAlex/Crossref/ISTEX change over time.

This is understandable legally, but the paper should separate “pipeline reproducibility” from “bitwise data-product reproducibility.” If users cannot reconstruct the same embeddings or reranker scores, then those products are artifacts of a particular metadata snapshot. Possible mitigations include:

- storing hashes of the text strings used for embedding/scoring;
- storing abstract length/status/model input length;
- storing the exact OpenAlex snapshot date or using OpenAlex bulk snapshots;
- distributing derived non-infringing features sufficient to audit scoring;
- preserving manual labels used for validation.

The Conclusion mentions that a future iteration would use OpenAlex bulk download; I think that is not just future convenience but central to reproducibility.

---

## Comments by section

### Introduction

The comparison with Carè and Weber (2023), Shang and Jin (2023), and Maria et al. (2023) is useful, but the overlap probe is not fully convincing. The paper says it replicated each published query against OpenAlex and matched by DOI and year-constrained title. But those studies searched Scopus and Web of Science. Therefore the reported 89.3% and 91.0% are not really overlap with the prior authors’ analyzed records; they are overlap with an OpenAlex translation of their queries. The paper partly acknowledges this, but the sentence “they approximate the overlap with the records those authors analysed” still feels too strong.

Also, more related work is needed. Besides the three bibliometric articles, the paper should situate itself among:

- systematic-review corpus construction practices;
- OpenAlex versus Scopus/WoS coverage studies;
- grey-literature evidence synthesis;
- multilingual information retrieval and cross-lingual bibliometrics;
- climate policy / sustainable finance / green finance bibliometric mappings beyond the three cited papers.

### Section 2.1: Sources and ingestion

The source table is informative but mixes very different categories: academic indexes, restricted portals, AI-collected exports, curated key documents, and teaching syllabi. I would like clearer operational definitions for “AI-collected,” “AI-assisted,” and “hand-harvested.” In particular:

- What model or tool was used for LLM extraction from syllabi?
- How were hallucinated or malformed references detected?
- What does “SciSpace systematic review tool exports” mean methodologically?
- Are raw exports from restricted platforms redistributable under CC BY 4.0?
- What is the exact World Bank repository query?

The four-tier keyword taxonomy is central but only summarized. Since the main paper need not list every term, it should at least report the number of terms per language and tier, and give representative examples. The phrase “default.search field” in OpenAlex is also important: because it searches indexed full text where available, retrieval may be biased toward publishers and works with richer indexing.

### Section 2.2: Deduplication and refinement

The flagging logic is clear at a high level, but I had difficulty reconstructing exactly how inclusion decisions are made. The expression in Section 3, `df[-df['is_flagged'] | df['is_protected']]`, also appears to use Python/pandas syntax incorrectly or at least confusingly: `~df['is_flagged']` would be standard, not `-df['is_flagged']`.

The near-duplicate grouping rule is interesting, but the thresholds—first 200 abstract characters, at least five members, title group qualifying only when 50% share an abstract prefix—feel ad hoc. Why five members? This will miss two-paper working-paper/article duplicates, which Section 2.4 later admits are a problem. Since working-paper/published-version duplicates are likely more important bibliometrically than mass duplicated abstracts, they deserve a dedicated method.

### Section 2.3: Quality and completeness

Table 3 is useful, but I would add columns for median year, share outside 1990–2024, and maybe share flagged/protected by source. The source-specific refined rates are revealing—for example, OpenAlex drops from 41,138 to 31,544, while teaching canon barely drops—but the paper does not interpret these differences.

The reranker validation paragraph needs revision for statistical precision and reproducibility, as discussed above. The fact that “per-work grades were not retained” should be treated as a serious limitation, not a minor archival detail.

### Section 2.4: Limitations and biases

This is one of the strongest sections, but several limitations are so consequential that they should trigger changes to the dataset or abstract, not merely be acknowledged.

Most importantly, the out-of-window records should be removed from the refined 1990–2024 corpus. Also, the non-English removal bias should motivate either a language-aware default filter or a separate recommended multilingual subset.

The discussion of excluded national institutions is helpful. However, since the Introduction invokes “multicultural and Southern perspectives,” the exclusion of national institutions, CNKI, SciELO, Garuda, etc. should be surfaced earlier. Otherwise, the paper risks overclaiming Southern coverage while relying primarily on English-language international institutions and OpenAlex-indexed scholarship.

### Section 3: Data description

This section is practical and mostly clear. A few details need correction:

- `climate_finance_corpus.csv` is said to have 43,179 rows, but the abstract highlights 33,344 works. The relation is explained, but the paper should consistently call one “complete deduplicated corpus” and the other “default refined subset.”
- Table 5 has formatting/variable-name issues: `near Duplicate_group` likely should be `near_duplicate_group`; “climate_finance Corpus.csv” has inconsistent capitalization/spaces.
- `citations.csv` only contains DOI pairs, so users cannot directly join no-DOI institutional documents. That should be stated in the file description as a central limitation.
- If abstracts cannot be distributed, users need more metadata about the text used for embeddings: which fields were concatenated, whether abstract was missing/boilerplate, token counts, and hashes.

### Section 4: Data overview and Figure 1

The overview is too thin for a data paper of this scope. Figure 1 is potentially interesting, but it is hard to read and insufficiently supported.

Suggestions:

- Add a table of the 10 Louvain communities with size, top terms, top cited works, median year, and representative venues.
- Make clear that Figure 1 covers only 39% of the refined corpus.
- Report sensitivity to excluding review articles or works with huge reference lists, since Section 2.3 notes reference counts up to 1,536.
- Clarify whether Louvain is run on directed or undirected edges and whether edge weights are used.
- The phrase “global map of climate finance scholarship” is too strong for a DOI-only connected subgraph.

The structural break at 2015 is interesting, but the annual-volume figure is not in this paper. Since Section 4 discusses it, the figure should be included here or the analysis shortened.

### Conclusion

The Conclusion fairly summarizes the dataset’s ambitions, but it overstates the multilingual and institutional achievements relative to the actual composition. I would soften “multilingual retrieval adds a non-English layer” to emphasize that the layer supports targeted case studies, not balanced cross-language comparison. I would also mention the temporal leakage and abstract non-reproducibility as first-order caveats.

---

## Minor issues and editorial suggestions

- The paper date is 2026-07-29, while the corpus is described as 1990–2024 and OpenAlex data as 2026-07-24. Make the versioning chronology explicit.
- “In less Removed equals Out” in Table 2’s caption should be rephrased as “In minus Removed equals Out.”
- “dedduplication” in Section 3 should be “deduplication.”
- The spelling of “programme”/“program” should be consistent if the venue has style preferences.
- The phrase “AI-collected” may raise red flags; replace with precise tool names and human verification steps.
- The title blacklist examples “blockchain” and “deep learning” are puzzling, because those could be relevant to green finance/climate risk. Explain how “without climate-finance context” is operationalized.
- The abstract says institutional reports and key documents are 1.4% of the corpus; Table 3 implies this only if one combines institutional reports, UNFCCC, and OECD. State that explicitly.
- If the corpus includes 3,238 post-2024 records, avoid saying “temporal coverage 1990–2024” in Section 3 without qualification.

---

## Numbered questions I would ask the author

1. Why not apply a final year filter so that the released refined corpus actually covers 1990–2024, as stated in the title and abstract?

2. What is the intended conceptual boundary of “climate finance”: North-South UNFCCC finance, broad climate-related finance, or the larger green/sustainable finance literature?

3. How many records enter through each keyword tier and language, before and after filtering?

4. How many non-English records were removed solely because of the English cross-encoder query, and why not use own-language query translations in the default build?

5. Can the reranker validation be repeated with retained per-work labels, stratified by language, source, year, and document type?

6. How were the cross-encoder threshold and the protection criteria chosen, and how sensitive
