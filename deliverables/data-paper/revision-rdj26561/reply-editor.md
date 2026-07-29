# DRAFT — Supplementary note 1: reply to the editor's letter (RDJ-26561)

> *"Please address the caveats of using OpenAlex for scientometrics, in
> particular the difficulties related to paper deduplication […]"*

The new Section 2.4, "Limitations and Biases," maps each documented OpenAlex
flaw to the pipeline step that addresses it, or to an explicit "not
mitigated" statement, and names SciELO and Garuda as regional databases the
provenance architecture can absorb without reprocessing existing sources.
Deduplication is answered in the reply to the referee's remark on
duplicates (supplementary note 2).

> *"What is the added value of this new dataset? […] networks of
> institutions and/or co-authors are also possibilities […] text analysis
> and content classification […]"*

The conclusion now maps the research directions the dataset enables by
method family, naming the ones you suggest. To demonstrate added value
directly, I re-tested three published results on the corpus, each with one
explicit statistical test: the post-2015 growth take-off of Kouwenberg and
Zheng (2023) — a structural break in log annual counts at 2015 (Chow
F = 10, p = 0.0004), kept in Section 4; their observation that the
financial–economic cluster is "quite disconnected" — cross-pole edges are
0.4% of edges against 12.8% expected under degree-preserving rewiring
(z = 76, p < 0.01); and the near-absence of climate finance from top finance
journals reported by Diaz-Rainey et al. (2017) — the finance-journal share
rises from 0.01% before 2015 to 0.28% after. A query-replication probe in
Section 1 bounds coverage of the prior mappings: the corpus contains 89.3%
of the works retrieved by Carè and Weber's query and 91.0% for Shang and
Jin's, against 40.1% for Reis Maria et al.'s broader green-finance query.

> *"[…] introduce a table describing the variables contained in your main
> dataset, 'climate_finance_corpus.csv' […]"*

Done: Table 5 in Section 3, generated from the deposit's declared column
contract so it cannot drift from the file. The machine-readable
`datapackage.json` beside the data carries each column's storage type,
allowed values, range, and measured missingness.

> *"It would also be beneficial to introduce a bit more structure to your
> Zenodo package […]"*

The package is restructured into `code/` (pipeline source), `data/inputs/`
(per-source catalogs as harvested), and `data/products/` (the paper's
outputs). The layout is produced by a build script, described identically in
the archive README and Section 3, and the new version is uploaded with this
resubmission.
