# DRAFT — Supplementary note 2: reply to the referee report (RDJ-26561)

> *"[…] the corpus does not include in the grey literature documents from
> national institutions: government or parliamentary reports […] central
> bank communications. Why is that?"*

This remark pushed the revision to extend the dataset, and I thank the
referee for it: a curated UNFCCC and OECD DAC key-document layer (230 and 33
works after deduplication) now enters the corpus as a durable pipeline
source with its own provenance flags. On national institutions, Section 2.4
states and justifies the boundary: the corpus traces climate finance as a
category of *international* economic governance. The point stands — some national positions do constitute international policy, as a
United States exit from climate finance mechanisms would shift the
negotiation itself — so the boundary does cost relevant documents.
Tractability decided it: each national document family is a corpus-scale
universe of its own. Central-bank communications alone hold 35,487 speeches
in the dataset of Campiglio, Deyris, Romelli and Scalisi (2025), which the
report kindly points to. The revised text names national sources as the
natural extension path and cites Campiglio et al. as the first curated open
dataset to plug in.

> *"There are numerous inconsistencies in the metadata: incorrect citation
> assignments, missing abstracts, duplicates, and sometimes missing
> full-text […]"*

Answered with the editor's first remark: Section 2.4 pairs each documented
limitation with the pipeline step that addresses it, or an explicit "not
mitigated" entry.

> *"The DOI-based deduplication […] does not always work, as the DOIs (if
> any) differ between the working paper version and the published version
> […]"*

What counts as a duplicate depends on usage — a citation analysis wants a
working paper merged with its published version, while a history of the
record wants both kept — so the pipeline's answer is transparency and open
code rather than a rigid stance: every pass is counted, the residual classes
are measured, and users can redraw the line. Section 2.2 now counts what
each pass removes — 833 records on DOI, 159 on title+year, and 399 in a
third DOI pass after enrichment that the submitted version omitted — and
Table 2 reconciles the 44,174 pooled records to the 33,344 refined works
with no residue. Section 2.4 quantifies the residual
class the report predicted: 344 exact-title, same-first-author candidate
pairs (1.0% of works), a fuzzy-title upper bound of 1,329 works (4.0%), and
the over-merge side (38 DOI collision groups, 7 degenerate empty-year
groups), all from a deposited audit script. Author-normalised deduplication
is deferred to a future release: the audit found name order swapped across
sources, so a merge pass on today's names would over-merge.

> *"OpenAlex contains a huge number of incorrect citation assignments […]
> Did the author take note of the number of references cited by each
> document in the corpus?"*

Yes: Section 2.3 reports the distribution (median 29 references among
DOI-bearing works; 20.3% contribute none, a gap concentrated in books,
reviews, editorials, and grey literature) and flags both tails as screening
variables. GROBID, which the report recommends, is implemented at the
reference-string level (`corpus_parse_citations_grobid.py` in the deposited
code); full-text PDF extraction remains explicitly not mitigated, since I do
not hold the corpus's full texts. Two 300-sample audits bound the failure
modes: 97.0% of sampled links are confirmed against Crossref reference
lists, and 98.3% of the reference DOIs Crossref holds are captured — with
Section 2.3 stating what these audits measure: agreement with Crossref, not
ground truth.

> *"The article would benefit from presenting a network of citations drawn
> from this database at this stage, in order to demonstrate its potential
> and/or limitations."*

Both halves are answered in Section 4. *Potential*: a new figure maps the
intra-corpus citation network at community granularity (Louvain detection);
the major communities correspond to recognisable research programmes, from
carbon markets to green bonds. *Limitations*: the same network is too thin
before 2008 for inferential use — the pre-2008 citer subgraph covers about
8% of early works — and the paper states this undercount as a usage caveat.

> *"[OpenAlex] also indexes many other working paper series in economics
> (NBER, MPRA…)."*

Section 2.1 now says so: "OpenAlex indexes economics working papers from
RePEc, NBER, MPRA, and other repositories, so no separate harvest is
needed."

> *"OpenAlex sometimes records full-text content in the abstracts […]
> Consequently, Figure 1 is potentially biased."*

Full text recorded in the abstract field is caught by a size limit: fields
over 1,000 tokens are replaced by an LLM summary of ordinary abstract
length, or flagged oversized where no summary is available, and the
`abstract_status` column discloses each case. At the other end, a
boilerplate detector drops stub abstracts, and affected works are embedded
from title and keywords only (Section 3). The submitted Figure 1 — the
exposure the report identified — has left the paper.

> *"The author writes that 'the five smaller sources add non-English […]
> coverage that OpenAlex alone does not provide.' However, OpenAlex does
> include non-English sources."*

The report is right: OpenAlex indexes non-English sources, and the earlier
sentence overstated. Section 2.3 now claims only what Table 3 measures: 6%
of OpenAlex's refined works are non-English, and the smaller sources add
incremental non-English, institutional, and pedagogical coverage.

The revision also measures a language bias the submitted version missed.
The relevance filter removes 41.8% of non-English works but only 19.9% of
English ones. The cause is the query, not the content: rescoring the
flagged non-English works against an own-language translation of the query
lifts the pass rate by 11.5 percentage points. Section 2.4 discloses the
bias and its direction, and users can rebuild from the deposited flags
under their own filter policy.

> *"[…] I find it extremely difficult to assess the potential of this
> dataset for conducting research on the history of economic thought […]"*

The potential is best assessed on use rather than promise: the companion
history-of-thought study under review at Œconomia, cited in the revised
introduction, is built on this corpus, and I enclose its draft with this
resubmission. Its results show what the dataset supports — from simple
counts (Negishi absent from the pre-2007 canon, Barrett co-cited with the
carbon-pricing literature) to the corroboration of a three-act documentary
periodization.

> *"The organization of the Climate_Finance_Corpus […] makes manual check
> of the corpus rather unpleasant for someone who wishes to explore it
> manually."*

I kept the file layout — a standard rectangular CSV whose columns follow
four logical groups in a fixed order; reshaping a published Zenodo artifact
would break its consumers for a viewer-ergonomics gain. The revision makes
the structure explicit instead: Table 5 shows each column's group, and the
deposit ships a formal, machine-readable data dictionary
(`datapackage.json`, a Frictionless Table Schema with per-column types,
allowed values, ranges, and measured missingness). The dictionary is executable: anyone who downloads the
deposit can run `frictionless validate datapackage.json` and have the
corpus CSV checked, column by column, against its own documentation.
