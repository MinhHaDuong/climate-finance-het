# Response-letter bullets — citation data quality (ticket 0277, feeds 0283)

Remarks covered: R1-13. R1-14 is answered separately (tickets 0286/0307).

**R1-13 (incorrect citation assignments; reference counts; GROBID).** Yes,
we recorded the number of references each document contributes to the
citation graph, and the revised Section 2.3 now reports the distribution:
among DOI-bearing works, the median reference count is 31 (mean 43.7, 95th
percentile 127, maximum 1,536), and 22.1% (5,152 works) contribute no
reference at all — a gap concentrated in books, book reviews, editorials,
and grey literature, where indexers hold the record but not its reference
list. The revision flags both tails as screening variables for users:
zero-reference works measure indexing rather than scholarly isolation, and
counts in the hundreds mark reviews and a few aberrant lists. (Numbers are
generated from `tab_reference_counts.csv`, shipped with the deposit
pipeline, and injected into the paper as Quarto variables.)

On GROBID: we agree it is necessary, and it is now implemented — at the
reference-string level, over the whole corpus. The pipeline script
`corpus_parse_citations_grobid.py` sends the free-text citation strings
that Crossref and OpenAlex return unresolved to GROBID's citation parser,
recovering title, first author, and year, which a fuzzy-matching step then
resolves against corpus works. What we do not do — and the revised
Section 3 states this explicitly — is full-text reference extraction from
PDFs: we do not hold the full texts of the corpus's academic works, so
parsing PDFs of the entire corpus is not feasible under current access
conditions. The "Missing full-text" row of Table `tbl-openalex-limits`
keeps this limitation as explicitly not mitigated.

On incorrect assignments generally: the existing 300-link audit against
Crossref (99.0% confirmed, 95% CI [97.1%, 99.7%]) addresses link accuracy;
the new reference-count reporting addresses list completeness — the
"empty or aberrant" failure mode the referee describes.

**R1-14 (citation-network demonstration).** Addressed separately: see the
response bullet produced by tickets 0286/0307 (global co-citation
community map).
