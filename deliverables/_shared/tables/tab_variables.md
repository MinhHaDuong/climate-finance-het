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
\texttt{source} & string & Primary source catalog for the record's metadata \\
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
\texttt{from\_unfccc}† & boolean & Provenance flag: curated UNFCCC key document \\
\texttt{from\_oecd}† & boolean & Provenance flag: curated OECD key document \\
\texttt{abstract\_provenance}† & string, nullable & Provenance of the abstract text, for curated key documents only \\
\texttt{keywords\_provenance}† & string, nullable & Provenance of the keywords, for curated key documents only \\
\texttt{language\_provenance}† & string, nullable & How the language code was obtained: carried by the source catalog, backfilled from OpenAlex, or inferred from title and abstract \\
\texttt{source\_count} & integer & Number of sources that contributed the record \\
\midrule
\texttt{abstract\_status} & string & Whether the undistributed abstract was original, reconstructed from an inverted index or fulltext, LLM-summarised, oversized, or missing \\
\texttt{near\_duplicate\_group} & integer, nullable & Group identifier for near-identical content published under several DOIs \\
\texttt{semantic\_outlier\_dist}† & float, nullable & Cosine distance to the embedding centroid of the work's own language, or to the corpus centroid where a language holds too few works; diagnostic only, no work is removed on it \\
\texttt{in\_v1}† & boolean & Version tracking: work present in the v1.0 submission corpus \\
\texttt{is\_flagged} & boolean & Any quality flag raised; the refined subset is \texttt{df[\textasciitilde{}df[\textquotesingle{}is\_flagged\textquotesingle{}] \textbar{} df[\textquotesingle{}is\_protected\textquotesingle{}]]} \\
\texttt{flag\_reason} & string & Comma-separated list of raised quality flags (missing\_metadata, no\_abstract\_irrelevant, title\_blacklist, citation\_isolated\_old, llm\_irrelevant); empty when unflagged. The sixth flag, \texttt{semantic\_outlier}, is diagnostic and never raised — its distance ships as \texttt{semantic\_outlier\_dist} \\
\texttt{is\_protected} & boolean & Protection from removal (key papers kept despite flags) \\
\texttt{protection\_reason}† & string, nullable & Why the work is protected (citation count, seed list, \ldots{}) \\
\bottomrule
\end{longtable}
```

Variables of `climate_finance_corpus.csv`. Horizontal rules separate the four logical groups: record identity, bibliographic metadata, provenance flags, curation metadata. † marks a variable absent from corpus builds predating its pipeline stage. Generated from the deposit column contract (`scripts/_deposit_variables.py`); per-source provenance, allowed values, and missingness are in the deposited codebook.
:::
