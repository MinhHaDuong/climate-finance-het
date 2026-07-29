---
format:
  pdf:
    papersize: a4
---

**Summary of revisions — RDJ-26561**

Manuscript RDJ-26561, submitted as "A Curated Corpus of Climate Finance
Literature, 1990–2024," retitled "A Curated Multi-Source Corpus of Climate
Finance Literature, 1990–2024: Multilingual Retrieval and Institutional
Reports" in this revision. Main revisions, July 2026 round.

1. **Corpus extended (v2).** A curated layer of UNFCCC and OECD DAC key
   documents (COP decisions on finance, Biennial Assessments, Rio-marker
   reporting directives) joins the institutional reports as a durable pipeline
   source with provenance flags. The corpus grows from 42,916 to 43,179
   unified works (30,987 to 33,344 after filtering); all statistics, tables, and figures were regenerated from
   the v2 corpus by the deposited pipeline.

2. **New Section 2.4, "Limitations and Biases."** The section
   pairs each documented OpenAlex flaw with the pipeline step that
   addresses it, or with an explicit "not mitigated" statement; it also
   names concrete regional databases (SciELO, Garuda) as complements.
  

3. **Deduplication quantified.** Section 2.2 reports per-procedure removal
   counts from the merge run report (DOI pass: 833; title+year pass: 159);
   Section 2.4 adds audited error-rate estimates for both residual
   duplicates and over-merging, and explains why author-normalised
   deduplication is deferred.

4. **Citation quality reported and improved.** Section 2.3 reports the
   per-document reference-count distribution, including the zero-reference
   share and its concentration in books, reviews, and grey literature;
   GROBID-based parsing of unresolved reference strings is now part of the
   pipeline; the 300-link Crossref audit is retained and re-run on the frozen
   v2 corpus (97.0% confirmed, 95% CI [94.4%, 98.4%]), joined by a
   completeness audit (98.3% of Crossref-held reference DOIs captured), and
   the paper now states what the audits measure: agreement with Crossref,
   not ground truth.

5. **Citation network demonstrated.** A new figure presents a global map of
   the corpus citation network (Louvain communities on the direct-citation
   graph); the early-period thinness is quantified and stated as a usage
   caveat.

6. **Added value made concrete.** The conclusion discusses the research
   directions the database enables and references the Œconomia companion
   paper; three published results are re-tested on the corpus, each with one
   explicit statistical test (reported in the reply notes; the growth break stays in Section 4); a replication of prior
   mappings' published queries shows 89–91% coverage of the climate finance
   populations they drew on.

7. **Variables table and data dictionary.** Section 3 adds a generated table
   describing every variable of `climate_finance_corpus.csv`; the Zenodo
   deposit ships a machine-readable data dictionary (`datapackage.json`, a
   Frictionless Table Schema) with per-column storage type, allowed values,
   ranges, and measured missingness. It is executable, so a reader can check
   the deposited file against it rather than trust the documentation.
  

8. **Zenodo package restructured.** The deposit (same concept DOI) now
   separates `data/inputs/` (per-source catalogs) from `data/products/`
   (final corpus, embeddings, citations, `datapackage.json`), with `code/`
   holding the pipeline.

9. **Wording fixes.** Working-paper series named beyond RePEc (NBER, MPRA);
   the non-English coverage claim reworded to incremental coverage only.
  
