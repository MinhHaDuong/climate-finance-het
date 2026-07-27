::: {#tbl-variables}
```{=latex}
\begin{longtable}{@{}l l p{8.2cm}@{}}
\toprule
Variable & Type & Description \\
\midrule
\endfirsthead
\toprule
Variable & Type & Description \\
\midrule
\endhead
\texttt{source} & string & Primary source catalog for the record's metadata (highest-priority contributing source) \\
\texttt{source\_id} & string & Identifier in the primary source (e.g. OpenAlex work ID) \\
\texttt{doi} & string, nullable & Digital Object Identifier, when available \\
\midrule
\texttt{title} & string & Title of the work \\
\texttt{first\_author} & string, nullable & First author name \\
\texttt{all\_authors} & string, nullable & Full author list, separator-joined \\
\texttt{year} & integer & Publication year \\
\texttt{journal} & string, nullable & Publication venue (journal, publisher, or repository) \\
\texttt{language} & string, nullable & Language code (ISO 639-1), detected and normalised \\
\texttt{keywords} & string, nullable & Keywords, semicolon-separated \\
\texttt{categories} & string, nullable & Subject categories / concepts from the source catalog \\
\texttt{cited\_by\_count} & integer & Citation count (OpenAlex, as of the collection date) \\
\texttt{affiliations} & string, nullable & Author affiliations, when available \\
\midrule
\texttt{from\_openalex} & boolean & Provenance flag: found in OpenAlex \\
\texttt{from\_istex} & boolean & Provenance flag: found in ISTEX \\
\texttt{from\_bibcnrs} & boolean & Provenance flag: found in bibCNRS \\
\texttt{from\_scispace} & boolean & Provenance flag: found via SciSpace \\
\texttt{from\_grey} & boolean & Provenance flag: grey-literature source \\
\texttt{from\_teaching} & boolean & Provenance flag: teaching canon (syllabi) \\
\texttt{from\_unfccc} & boolean & Provenance flag: curated UNFCCC key document (absent from corpus builds predating this pipeline stage) \\
\texttt{from\_oecd} & boolean & Provenance flag: curated OECD key document (absent from corpus builds predating this pipeline stage) \\
\texttt{abstract\_provenance} & string, nullable & Provenance of the abstract text for curated key documents: \texttt{curated}, \texttt{reconstructed:lead}, or \texttt{reconstructed:exec\_summary}; empty elsewhere (absent from corpus builds predating this pipeline stage) \\
\texttt{keywords\_provenance} & string, nullable & Provenance of the keywords for curated key documents: \texttt{extracted} or \texttt{generated:lexicon}; empty elsewhere (absent from corpus builds predating this pipeline stage) \\
\texttt{source\_count} & integer & Number of sources that contributed the record (sum of the provenance flags) \\
\midrule
\texttt{abstract\_status} & string & Status of the (undistributed) abstract: \texttt{original}, \texttt{reconstructed} (from OpenAlex inverted index or ISTEX fulltext), \texttt{generated} (LLM summary of an oversized abstract), \texttt{too\_long}, or \texttt{missing} \\
\texttt{near\_duplicate\_group} & integer, nullable & Group identifier for near-identical content published under several DOIs; null for ungrouped works \\
\texttt{semantic\_outlier\_dist} & float, nullable & Distance to the corpus embedding centroid, computed for the semantic-outlier flag (absent from corpus builds predating this pipeline stage) \\
\texttt{in\_v1} & boolean & Version tracking: work present in the v1.0 submission corpus (absent from corpus builds predating this pipeline stage) \\
\texttt{is\_flagged} & boolean & Any quality flag raised; the refined subset is \texttt{df[\textasciitilde{}df[\textquotesingle{}is\_flagged\textquotesingle{}] \textbar{} df[\textquotesingle{}is\_protected\textquotesingle{}]]} \\
\texttt{flag\_reason} & string & Comma-separated list of raised quality flags (missing\_metadata, no\_abstract\_irrelevant, title\_blacklist, citation\_isolated\_old, semantic\_outlier, llm\_irrelevant); empty when unflagged \\
\texttt{is\_protected} & boolean & Protection from removal (key papers kept despite flags) \\
\texttt{protection\_reason} & string, nullable & Why the work is protected (citation count, seed list, \ldots{}) (absent from corpus builds predating this pipeline stage) \\
\bottomrule
\end{longtable}
```

Variables of `climate_finance_corpus.csv`. Horizontal rules separate the four logical groups: record identity, bibliographic metadata, provenance flags, curation metadata. Generated from the deposit column contract (`scripts/_deposit_variables.py`); per-source provenance, allowed values, and missingness are in the deposited codebook.
:::
