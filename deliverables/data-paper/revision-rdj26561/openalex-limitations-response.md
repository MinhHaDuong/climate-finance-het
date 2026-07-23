# Response-letter bullets — OpenAlex limitations (ticket 0275, feeds 0283)

Remarks covered: ED-01, R1-11 (with folded R1-07, R1-10), R1-16b.

**ED-01 / R1-11 (OpenAlex caveats; per-limitation pipeline mapping).** We
added Section 2.4, "OpenAlex limitations and pipeline responses," with a
table (`@tbl-openalex-limits`) mapping each documented OpenAlex flaw — query false
positives, duplicate records, missing abstracts, incorrect citation
assignments, contaminated abstract fields, missing full-text — to the
pipeline step that addresses it, or to an explicit "not mitigated"
statement. The section also names deduplication's residual weak point
(works sharing neither a DOI nor a normalised title+year pair, e.g. a
preprint and its retitled published version) rather than claiming the
merge passes catch everything.

**ED-01 (regional database example).** Section 2.4 now names two concrete
regional databases that could complement the corpus — SciELO for Latin
American journals and Garuda for Indonesian journals — and notes that the
provenance architecture accepts such additions without reprocessing
existing sources.

**R1-16b (full text in the abstract field; Figure 1 bias).** Section 2.4
explains the handling: a boilerplate detector (`is_boilerplate_abstract`
in the deposited code) drops stub abstracts before embedding, so affected
works are embedded from title and keywords only. For Figure 1, whose
shading matches "climate finance" in title or abstract, we state the
direction and bound of the residual bias: an over-long abstract field can
add a work to the shaded subset only when the phrase appears in the body
text but not the abstract; corpus membership and the annual totals do not
depend on abstract length.
