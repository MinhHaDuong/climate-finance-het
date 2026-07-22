## Clustering validity: positioning in the bibliometric literature
<!-- Split (ticket 0289, 2026-07-22): part B of the former §11 fragment,
     written 2026-03 for the technical report but never wired into any
     document (orphan — see ticket 0290). Part A (prior-mappings review)
     moved to prior-mappings.md, staged for the data paper. Author-reviewed
     2026-07-22 (PDF draft read; AI-generated marker cleared per author
     decision). -->
<!-- 0152 correction retained: "None report validity metrics" was FALSE
     (CiteSpace studies report Q + mean silhouette) — corrected below. -->
<!-- STALE CROSS-REFS: "Section 7.8" and "Section 9" below refer to the
     technical report's pre-restructure numbering; fix them when this file
     is wired into a host document. -->

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
