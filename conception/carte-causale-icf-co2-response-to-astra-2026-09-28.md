# Response to Astra review of the ICF–CO₂ causal map

28 September 2026. This response records the changes made in v0.5 of
[`carte-causale-icf-co2.md`](carte-causale-icf-co2.md) after the independent
[`Astra review`](carte-causale-icf-co2-review-astra-2026-09-28.md). The review
remains a separate, unedited record. The revised note is still a hypothesis
map, not a validated synthesis of the literature.

| Review finding | Disposition in v0.5 | Remaining empirical work |
|---|---|---|
| 1. Outcome overlap and accounting boundary | Y1–Y4 now denote mutually exclusive territorial inventory categories; construction can affect both Y2 and Y3 without combining them; apparent cement consumption is rejected as a direct territorial process measure. | Verify data products' boundaries and cement/clinker methods when calculating outcomes. |
| 2. Associations coded as arrows | Section 9 separates ontology, data, evidence and models; records claimed versus supported estimands; allows no applicable DAG path. | Code read works and test the categories. |
| 3. Identification designs over-ranked | Section 7.3 now lists candidate designs and required assumptions, without a universal rank; tranche comparisons are descriptive unless a counterfactual is justified. | Examine actual published designs and their first stages, exclusions and alternatives. |
| 4. Universal negative controls | Section 7.4 recasts leads, adaptation and cross-module tests as conditional diagnostics. | Specify controls for each empirical intervention and horizon. |
| 5. G-methods despite latent governance | Sections 7.1–7.2 distinguish treatment–confounder feedback from unmeasured confounding and name exchangeability, positivity and consistency. | Draw a fully timed DAG for a particular study. |
| 6. NLP as real finance | Sections 3.1–3.2 and 8.1 distinguish operational recoding from expenditure, valuation, climate share and additionality. | Validate against reviewed projects and quantify uncertainty. |
| 7. Budget interventions | Section 3.2 distinguishes expansion, reallocation, O fixed, and normative accounting references. | Estimate any substitution response under a specified intervention. |
| 8. Physical time and units | Section 4 gives annual MWh units, defines the stylized J-curve, puts construction before installed capacity in module B and the dagitty annex, and separates territorial from lifecycle measures. | Check illustrative factors and technology-specific delays before citation. |
| 9. Direction and magnitude claims | Sections 3, 4, 7 and 10 qualify credit use, WACC effects, omitted-variable bias and global learning; unsupported order-of-magnitude comparison was removed. | Verify remaining numerical examples and bibliographic claims. |
| 10. Search saturation | Section 11 anchors coding to a frozen REL corpus, adds searches independent of DAG arrows, records out-of-map works, and limits absence claims to the coded sample. | Execute the search, full-text review and PRISMA accounting. |

## Mechanical checks

- The revised dagitty block has 56 nodes and 126 distinct arcs and is acyclic
  under a NetworkX parse of its arrow list.
- The original review described v0.4 (56 nodes, 122 arcs); its count should not
  be read as the count for v0.5.

No claim of literature coverage, identification or numerical validity follows
from these mechanical checks.

## Second review round

Astra's final check found no new high-severity contradiction. It requested
three precision edits. The sectoral-budget consequence already distinguished
expansion from reallocation in the current v0.5 text. The remaining two were
applied: section 7.4 now requires absence of **direct and mediated** causal
effects for a negative control; the CO₂-only return-time table no longer
includes reservoir methane, and the bridge labels CH₄ as outside this map's
CO₂ perimeter rather than outside inventories. This closes the two review
rounds; the empirical and bibliographic work listed above remained open at
that point.

## Source and number audit after the review

The later v0.6 audit checked the note's explicit figures, source-dependent
claims and bibliographic metadata. Its [verification ledger](carte-causale-icf-co2-verification-2026-09-28.md)
records each finding and correction. This resolves the numerical and citation
checks requested in findings 8–9. The empirical literature coverage and causal
validity questions remain for the REL reading and coding pass.
