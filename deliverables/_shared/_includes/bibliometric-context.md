## 11. Bibliometric Context: Positioning in the Literature
<!-- WARNING: AI-generated, not human-reviewed -->
<!-- Factual claims verified sur pièce 2026-07-22 (ticket 0289, local PDFs + empirical overlap probe):
     Reis Maria et al. 2023 use SCOPUS (not RePEc as previously stated) — query TITLE-ABS-KEY((finance OR financial) W/3 (green OR climate OR carbon OR sustainable)), 3,663 retrieved, 3,275 after giant-component filtering;
     Carè & Weber 2023 use Scopus TITLE-ABS-KEY("climate finance"), not WoS;
     coverage numbers below from deliverables/data-paper/revision-rdj26561/prior-mappings-overlap.csv (probe_prior_mappings_overlap.py). -->
<!-- Literature attributions verified & corrected 2026-07-10 (ticket 0152, web-verified DOIs + local PDFs):
     Deb -> Deb & Chen 2024 JSFI 15(1) doi:10.1080/20430795.2024.2441195 (paywalled);
     "Baran et al. 2024" was a phantom -> real paper is Rusydiana 2023, Text Analytics in Economics 1(1), doi:10.58968/tae.v1i1.451 (OA, PDF held);
     Alonso-Robisco: published version has 5 authors + different title, JSFI 15(2) doi:10.1080/20430795.2024.2370325 (green OA, PDF held);
     Singhania et al. 2023 ESPR doi:10.1007/s11356-023-27828-y confirmed real & distinct from Shang & Jin 2023 ESPR doi:10.1007/s11356-023-31006-5 (2,311 WoS papers), which this section previously omitted;
     "None report validity metrics" was FALSE (CiteSpace studies report Q + mean silhouette) — corrected below. -->

### Prior bibliometric studies of climate finance

Several studies have mapped the climate finance literature bibliometrically. Our study differs from these in scope, methods, and — crucially — in reporting cluster validity.

**Direct climate finance bibliometrics.** Carè and Weber (2023, *Research in International Business and Finance*) analyze 315 papers (2004--2021) using co-word analysis and VOSviewer, identifying 7 clusters and finding the field "not finance-based" — top finance journals are largely absent. Deb and Chen (2024, *Journal of Sustainable Finance & Investment* 15(1)) apply co-citation and bibliographic coupling to 621 Web of Science papers, finding research took off around 2010 with China, US, and UK dominant. Shang and Jin (2023, *Environmental Science and Pollution Research*) run CiteSpace on 2,311 WoS papers, 2001--2022. Singhania et al. (2023, also *Environmental Science and Pollution Research*, a distinct study on climate-change research in finance and accounting) map 657 WoS papers (1995--2020) with CiteSpace. Rusydiana (2023, *Text Analytics in Economics* 1(1)) classifies 1,051 Scopus articles into 5 clusters: economic effects, governance, implementation, financing issues, and city-level finance. Validity reporting is thin: the CiteSpace studies carry the toolchain's default indicators computed on the cited-reference network (Shang and Jin: Q = 0.392, mean silhouette S = 0.74); the others present cluster visualizations without validity metrics. None asks whether the document population itself separates.

**Topic modeling on adjacent fields.** Alonso-Robisco, Bas, Carbó, de Juan and Marqués (2024, *Journal of Sustainable Finance & Investment* 15(2), "Where and how machine learning plays a role in climate finance research") apply LDA to 217 ML-for-climate-finance papers, extracting 7 topics (natural hazards, carbon markets, ESG, energy economics, etc.). Reis Maria, Ballini, and Fraga Souza (2023, *Sustainability*) use Structural Topic Modeling on 3,275 Scopus articles, finding 3 groups (international/UNFCCC framing, climate risk/green bonds, energy-emissions-economics models) with a temporal shift from international to national framing. This is methodologically the closest to our approach.

**Corpus sizes in context.** Our corpus of ~31,000 works is 10--100× larger than any previous climate finance bibliometric study (315--3,275 papers). This matters: small corpora may produce artificially well-separated clusters by undersampling the boundary-spanning works that create continuity.

**Coverage of the prior mappings' source populations.** The size comparison understates the relationship: our corpus contains most of what the prior mappings mapped. Replicating each study's published search query against OpenAlex and matching the retrieved works into the refined corpus by DOI, with a year-constrained title fallback, coverage is 89.3% for Carè and Weber's query (758 of 849 works), 91.0% for Shang and Jin's (975 of 1,072), and 91.1% for Rusydiana's (1,152 of 1,264). Before quality filtering, our sources capture over 99% of each of these populations; the residual gap is curation, and the works our policy removes are marginal (median 1 citation, none at 50 or more). Reis Maria et al. map green finance at large, a deliberately broader object of which climate finance is one strand; our corpus covers 40.1% of their query's population (1,618 of 4,034), consistent with its boundary. The replication approximates each query's surface, not its manually pruned final corpus (WoS topic search also scans Keywords Plus; Scopus subject-area limits have no OpenAlex equivalent). Method, per-study results, and miss decomposition: `deliverables/data-paper/revision-rdj26561/prior-mappings-overlap.{md,csv}` and `prior-mappings-misses.csv` (ticket 0289).

### How our approach differs

Our study is, to our knowledge, the first to:

1. **Compare clustering across multiple representation spaces** (semantic embeddings, lexical TF-IDF, bibliographic coupling). Previous bibliometric studies typically use a single representation. The hybrid approach has precedent in general bibliometrics: Yu et al. (2017, *PLoS One*) combine citation and text signals for 7,303 papers, finding optimal weights of α=0.55 (citation) and β=0.45 (text). Our contribution is to compare the spaces rather than fuse them, revealing their independence (ARI 0.06--0.22).

2. **Report document-population silhouette scores.** The near-zero values we find (0.025--0.108) are without counterpart in the climate finance bibliometric literature, where cluster visualizations are presented without validity metrics or with the toolchain's defaults computed on the cited-reference network (Shang and Jin 2023: Q = 0.392, S = 0.74); no study reports whether the documents themselves separate. Silhouette analysis is well-established in the topic modeling literature — Mäntylä, Claes, and Farooq (2018, ACM ESEM) show that single-run LDA is "dangerous" and recommend stability metrics including silhouette. Krasnov et al. use silhouette-based cluster quality to select the number of topics rather than perplexity alone.

3. **Test whether UNFCCC categories are natural clusters** (negative silhouette = anti-clustered). No previous study has tested whether the field's conventional categories correspond to empirical structure.

4. **Apply formal change-point detection** to structural properties of the field, as opposed to counting publications over time.

### Contextualizing near-zero silhouette scores

Are near-zero silhouette scores typical or exceptional?

**In bibliometrics.** Bascur, Verberne, van Eck, and Waltman (2024, *Scientometrics*) provide the most relevant benchmark. Analyzing 2.94 million PubMed documents with Leiden clustering on both citation and text networks, they find that **cross-disciplinary and methodological topics cluster poorly** in both networks, while diseases, psychology, and anatomy cluster well. Climate finance — spanning environmental science, economics, political science, and finance — is precisely the kind of boundary-spanning field that resists clean clustering. Our low silhouette scores are consistent with this finding.

**In machine learning.** Rousseeuw (1987) interprets silhouette scores below 0.25 as "no substantial structure." Our semantic-space scores (0.025--0.038) fall far below this threshold.

**In clustering method comparisons.** Šubelj, van Eck, and Waltman (2016, *PLoS One*) compare 30 clustering methods on WoS networks, finding that spectral methods are the least stable (instability ~0.4) and Infomap/map-equation methods perform best. This corroborates our finding that Spectral clustering is the least stable method in our comparison.

**Interpretation.** The near-zero silhouette is not an artifact but a genuine property of the field. It places climate finance among the "boundary-spanning" domains identified by Bascur et al. (2024) that inherently resist bibliometric clustering. This is itself a finding about the field's intellectual structure.

### Methodological contributions

Our multi-space temporal analysis contributes three methodological insights:

**1. Representation space matters more than clustering method.** The choice between KMeans, HDBSCAN, and Spectral matters less than the choice between semantic, lexical, and citation representations (Section 7.8). Yu et al. (2017) show that hybrid citation+text outperforms either alone; we extend this by showing that the spaces are largely independent and capture different structural dimensions.

**2. Silhouette scores should be standard in bibliometrics.** VOSviewer and CiteSpace produce compelling cluster visualizations that always appear well-structured due to force-directed layouts. Reporting silhouette scores alongside visualizations would reveal which clusters are genuine and which are artifacts of the layout algorithm. The Mäntylä et al. (2018) stability framework for LDA should be extended to embedding-based methods.

**3. Temporal silhouette analysis detects structural transitions.** Our change-point detection on annual silhouette series (Section 9) identifies when a field transitions from structured to diffuse — a contribution beyond publication-count trends or keyword-frequency tracking, which are the standard temporal methods in the climate finance bibliometric literature.
