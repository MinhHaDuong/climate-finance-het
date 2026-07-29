# DRAFT — Cover letter to the editor, RDJ-26561 (author sign-off required before submission)

Companion to `response-letter.md` (point-by-point reply) and
`summary-of-revisions.md`. This letter carries the substance the editor
needs before reading either: what changed in the dataset, what changed in
the paper, and the choices that call for an editorial judgment.

Dear Dr Chambru,

Please find the revised version of manuscript RDJ-26561, "A Curated
Multi-Source Corpus of Climate Finance Literature, 1990–2024," together
with a summary of revisions and a point-by-point reply to your letter and
to the referee report. Every point raised has been addressed; one is
answered with a justified alternative rather than the requested change,
flagged below. Three matters deserve your attention beyond the
point-by-point reply.

**The dataset itself changed, not only the paper.** Prompted by the
referee's remark on institutional coverage (R1-06), the revision extends
the corpus with a curated layer of UNFCCC and OECD DAC key documents —
COP decisions on finance, Biennial Assessments, Rio-marker reporting
directives — as a durable pipeline source with its own provenance flags.
The corpus grows from 42,916 to 43,179 unified works (30,987 to 33,344
after filtering), the source count from six to eight, and the deposit
title drops "Six Sources" accordingly (same Zenodo concept DOI, new
version). The Zenodo package is also restructured as you requested
(ED-04): `code/`, `data/inputs/` (per-source catalogs as harvested), and
`data/products/` (final corpus files with a machine-readable, executable
data dictionary). Every statistic, table, and figure in the paper was
regenerated from the v2 corpus by the deposited pipeline; no number is
hand-typed.

**The revision strengthens the paper partly by weakening its claims.**
Rerun on the v2 corpus, the citation-link audit now reports 97.0%
confirmed (previously 99.0%), and the paper states what that audit
measures: agreement with Crossref, not ground truth, partly circular for
links harvested from Crossref or OpenAlex deposits. The revision also
quantifies a bias no one asked about: the relevance filter removes a
larger share of non-English works, and rescoring against own-language
queries shows the score partly reflects query language. Both statements
trade headline polish for accuracy; I hope the journal reads them as the
data paper's job.

**One referee suggestion is declined with an alternative** (R1-19,
restructuring the corpus CSV). The file layout stays: reshaping a
published Zenodo artifact would break every downstream consumer for a
viewer-ergonomics gain. Instead the revision documents the structure — a
generated variables table in the paper and a Frictionless
`datapackage.json` in the deposit that a reader can execute to verify the
file against its own documentation.

One placement choice is reversible at your preference: to hold the
2,500-word budget, the three literature replications requested under
ED-02 (growth break, pole disconnection, finance-journal share) are
reported in the response letter, with only the growth break retained in
the paper's Section 4. I will gladly reinstate them in the text if you
prefer.

Thank you and the referee for a report that made both the paper and the
dataset better.

Sincerely,

Minh Ha-Duong
