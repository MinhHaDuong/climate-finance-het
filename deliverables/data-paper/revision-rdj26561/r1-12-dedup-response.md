# Response-letter bullet — deduplication counts and weaknesses (ticket 0276, feeds 0283)

Remarks covered: R1-12; ED-01 (deduplication part).

**R1-12 (per-procedure duplicate counts; WP-vs-published pairs; author
variable).** Section 2.2 now states how many duplicates each procedure
removes: the DOI-based pass and the title+year pass, with counts drawn from
the pipeline's merge run report (`catalog_merge` run report; on the deposited
corpus, 833 and 154 records respectively). Section 2.4 adds a quantified
discussion of the residual weakness the referee identifies. An audit of the
refined corpus (script and output `tab_dedup_error_estimates.csv` in the
deposited code) screens for exact-title, same-first-author pairs published up
to five years apart: 329 candidate pairs (1.1% of works), of which about half
are coordinated multi-journal editorials already flagged in
`near_duplicate_group` and half are genuine working-paper/published version
pairs — the class the referee predicted, roughly 0.5% of the corpus. A fuzzy
title match raises the upper bound to 1,064 works (3.4%), though that tier is
dominated by report series and successive editions that are distinct works.
The audit also quantifies over-merging: 38 DOI groups joining unrelated works
(OpenAlex DOI collisions) and 7 degenerate empty-year groups merging 18
generically titled works.

On the author variable: we agree it is the natural refinement and the audit
uses it as a screen. Implementing it as a merge pass requires author-name
normalisation first — the audit found given/family name order swapped across
sources — so we state in the text that author-normalised deduplication is
left to a future release rather than shipping a pass that would over-merge on
noisy names.

Numbers above are quoted from the archived artifacts (ticket 0284 run report,
md5-verified inputs; ticket 0301 audit table) for the editor's convenience;
the manuscript itself injects them from the pipeline via Quarto variables.
