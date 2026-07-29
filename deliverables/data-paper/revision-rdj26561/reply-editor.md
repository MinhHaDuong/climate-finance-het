---
format:
  pdf:
    papersize: a4
    include-in-header:
      text: |
        \pagestyle{empty}
---

**Supplementary note 1 — reply to the editor's letter (RDJ-26561)**

> *"Please address the caveats of using OpenAlex for scientometrics, in
> particular the difficulties related to paper deduplication […]"*

The new Section 2.4, "Limitations and Biases," maps each documented OpenAlex
flaw to the pipeline step that addresses it, or to an explicit "not
mitigated" statement, and names SciELO and Garuda as regional databases the
provenance architecture can absorb without reprocessing existing sources.
Deduplication now has its own accounting in Section 2.2 — each pass and its
removal count — and is answered in detail in the reply to the referee's
remark on duplicates (supplementary note 2).

> *"What is the added value of this new dataset? […] networks of
> institutions and/or co-authors are also possibilities […] text analysis
> and content classification […]"*

The added value is now argued at both ends of the paper. The introduction
grounds it in what prior mappings could not offer — each relies on a single
database, searches in English only, and publishes the query rather than a
reusable dataset — and the conclusion maps the research directions the
dataset enables by method family, naming the ones you suggest.

To demonstrate added value directly, I re-tested three published results on
the corpus, each with one explicit statistical test: the post-2015 growth
take-off of Kouwenberg and Zheng (2023) — a structural break in log annual
counts at 2015 (Chow F = 10, p = 0.0004), kept in Section 4; their
observation that the financial–economic cluster is "quite disconnected" —
cross-pole edges are 0.4% of edges against 12.8% expected under
degree-preserving rewiring (z = 76, p < 0.01); and the near-absence of
climate finance from top finance journals reported by Diaz-Rainey et
al. (2017) — the finance-journal share rises from 0.01% before 2015 to
0.28% after.

A query-replication probe in Section 1 bounds coverage of the prior
mappings: the corpus contains 89.3% of the works retrieved by Carè and
Weber's query and 91.0% for Shang and Jin's, against 40.1% for Reis Maria
et al.'s broader green-finance query.

> *"[…] introduce a table describing the variables contained in your main
> dataset, 'climate_finance_corpus.csv' […]"*

Done, at two levels: Table 5 in Section 3 describes every column for the
reader, and the deposit carries the same description in machine-readable
form (`datapackage.json`).

> *"It would also be beneficial to introduce a bit more structure to your
> Zenodo package […]"*

The package is restructured into `code/` (pipeline source), `data/inputs/`
(per-source catalogs as harvested), and `data/products/` (the paper's
outputs). The layout is produced by a build script, described identically in
the archive README and Section 3, and the new version is uploaded with this
resubmission.
