# R1-14 — Citation network: potential and limitations (tickets 0307 + 0286, feeds 0283)

Remarks covered: R1-14 (the referee suggests presenting a citation network
drawn from the database "to demonstrate its potential and/or limitations";
the editor softened this, ED-02).

## Response bullet — potential (global map, ticket 0307)

**R1-14 (present a network of citations to demonstrate potential and/or
limitations).** We answer both halves. *Potential*: the revised Section 3
adds a global map of the corpus citation network (new figure
`fig_global_map_direct`) --- Louvain community detection on the intra-corpus
direct-citation graph, rendered at community granularity. The major
communities (those holding at least 2% of the connected works; counts,
coverage, and modularity are drawn from the generated artifact
`global_map_direct.json`, not hand-typed) correspond to recognisable
research programmes: international climate governance, CDM and carbon
markets, North--South allocation, green bonds and sustainable finance,
financial economics of climate risk, among others. *Limitations*: the same
network is too thin before 2008 for inferential use. Our tradition-separation
analysis of the pre-2008 subgraph --- the paragraph below --- finds that
while the economic-cluster separation is significant against a
degree-preserving null (z = 8.7), the pre-2008 citer subgraph covers only
about 8% of early works, and bootstrap community assignments are stable for
just the best-connected references (93--100% for anchors). The paper states
the early-period undercount as a usage caveat; the figure demonstrates what
the network supports at full-corpus scale.

## Response paragraph — limitations (citer-limited network, ticket 0286)

Every number below traces to
`deliverables/_shared/tables/tab_network_limitations.csv`
(`make network-limitations`, script
`scripts/analysis/compute_network_limitations.py`) and the edge spot-check
to `deliverables/_shared/tables/qa_cocitation_edges_report.json`
(`make qa-cocitation-edges`). The citer-limited network itself is rendered
as a potential electronic supplement
(`deliverables/_shared/figures/fig_traditions_pre2008_citers.png`), not
embedded in the paper.

> A curated corpus earns its keep if its citation layer sustains
> substantive claims about the field's structure, not merely descriptive
> counts. We test this on the hardest case: the sparse early period
> (citing documents through 2008, fewer than 50 corpus works per year).
> Two claims about early climate finance scholarship can be established.
> First, its economic core was already divided: research on the Clean
> Development Mechanism and research on carbon pricing and international
> agreements form two well-separated co-citation communities with no
> direct edge between them — against 43% ± 5% of cross-cluster edges
> expected under degree-preserving rewiring (z = 8.7, empirical
> p < 0.01) — a division of intellectual labour that anticipates the
> later split between development and environmental framings. Second,
> the burden-sharing and equity debate, politically central in the UNFCCC
> negotiations of the period, had no scholarly co-citation identity of
> its own: of sixteen candidate anchor authors, none forms a community
> and only one enters the network at all; the economist closest to the
> question, Scott Barrett on treaty design, co-cites with the pricing
> cluster rather than with any equity pole. Both findings survive
> resampling: across 200 bootstrap draws of the citing documents, the two
> economic clusters reappear in 93–100% of draws while an equity
> community emerges in 8%. The period's sparsity bounds precision, not
> validity: the network is dense enough to separate the two economic
> traditions, and to establish that the governance tradition acquired its
> scholarly canon only after the field crystallized.

## Edge-quality spot-check

> The edges themselves check out against an independent source: for a
> random sample of 50 co-citation edges of this early-period network, we
> re-fetched a co-citing document's reference list from Crossref and
> confirmed both endpoints in 49 of 50 cases (98% concordance, 95% Wilson
> CI 90–100%; the one miss is an Energy Journal special-issue pair whose
> witness deposits no reference list in Crossref at all — counted
> conservatively as discordant).

The check is conservative: each edge is verified through a single
co-citing witness, although every edge has at least three by
construction (MIN_COCIT = 3).

## Provenance

- Corpus state: post-PR#1093 `refined_citations` (DVC checkout of
  2026-07-23).
- Parameters: `config/analysis.yaml`, section `network_limitations`
  (citer cutoff 2008, 100 rewirings, 200 bootstrap replicates, seed 42).
- Artifact mapping: cross-cluster null share and z —
  `econ_cross_share_null_mean`, `econ_within_share_z`; anchor census —
  `burden_candidates`, `burden_candidates_in_network`; bootstrap rates —
  `boot_pricing_rate` (0.925), `boot_cdm_rate` (0.995),
  `boot_burden_rate` (0.08).
