# R1-14 — Citation network: demonstration of potential and limitations

**Remark (R1-14).** The referee suggests presenting a citation network drawn
from the database "to demonstrate its potential and/or limitations"; the
editor softened this (ED-02).

**Response.** The revised data paper presents the global co-citation
community map as the corpus-potential demonstration (ticket 0307). The
paragraph below is the limitations demonstration for the response letter:
what the citation layer sustains on its hardest case, the sparse early
period. Every number traces to
`deliverables/_shared/tables/tab_network_limitations.csv`
(`make network-limitations`, script
`scripts/analysis/compute_network_limitations.py`) and the edge spot-check
to `deliverables/_shared/tables/qa_cocitation_edges_report.json`
(`make qa-cocitation-edges`). The citer-limited network itself is rendered
as a potential electronic supplement
(`deliverables/_shared/figures/fig_traditions_pre2008_citers.png`), not
embedded in the paper.

## Response paragraph

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
