# Notes accompanying tab_dedup_error_estimates.csv (data/products/, ed04 kit)

Displaced from data-paper.qmd §2.4 by cut-plan v2 condensation #1
(ticket-ref 0274). Mechanism detail behind the audit counts kept in the paper.

- False-negative mechanism: a working paper and its published version rarely
  share either merge key — their DOIs differ or are absent, and the year,
  sometimes the title, changes at publication, so such pairs escape both the
  DOI-based and the title+year deduplication passes.
- Exact-tier inspection attributes about half of the candidate pairs to
  coordinated multi-journal editorials already flagged in
  `near_duplicate_group`, the other half to genuine version pairs of the
  working-paper kind.
- The fuzzy-title upper-bound tier is dominated by report series and
  successive editions that are distinct works, not duplicates.
- False-positive mechanisms: OpenAlex occasionally assigns one DOI to several
  works (DOI-collision groups joining unrelated titles), and the title+year
  key degrades when the year field is empty, merging generically titled works.
- Author matching is the natural refinement targeting the version pairs, but
  author metadata is noisy across sources (given and family names swap
  order), so author-normalised deduplication is left to a future release.
